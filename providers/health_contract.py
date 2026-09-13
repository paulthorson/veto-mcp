#!/usr/bin/env python3
"""Provider-health contract — Initiative 09's interface to Initiative 03.

STATUS (2026-09-13, updated): Initiative 03's provider-health contract
EXISTS in-tree as ``provider_health.py`` (repo root, currently uncommitted
— the 03 team's work in progress). Per the roadmap's CONTRACT-FIRST rule,
this module is now an ADAPTER over their contract, not a parallel
definition:

* WRITE path: providers call ``provider_health.record_fetch`` /
  ``record_captcha`` (03's functions) — directly or via
  ``health_contract.record_fetch`` below, which delegates.
* READ path: the scorecard reads through ``default_store()``, which
  returns a ``ProviderHealthAdapter`` mapping 03's ``provider_status()``
  rows onto ``HealthSnapshot``. The mapping is explicit (see
  ``snapshot_from_status``); if 03 renames a field, exactly one function
  needs updating.
* FALLBACK: if ``provider_health`` cannot be imported (e.g. 03
  restructures mid-flight), ``default_store()`` degrades to the local
  ``FileHealthStore`` with a warning — the scorecard keeps working.

ASSUMPTION FLAG (for the program coordinator): the "03's contract lands
as described" assumption is now CONFIRMED with caveats — (1) 03's file is
uncommitted/in-flight, so field names could still shift before they ship;
(2) 03 tracks recovery streaks in *days* and last-success as ISO strings,
so this adapter converts; (3) 03 has no per-attempt timestamp, so
"freshness" here means time since last successful fetch.

This module never edits ``provider_health.py`` (another team's file).
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

log = logging.getLogger("job-apply-mcp.providers.health")

#: Capability labels per provider (the scorecard's fourth column).
CAPABILITY_LABELS: dict[str, str] = {
    "greenhouse": "search+details",
    "lever": "search+details",
    "ashby": "search+details",
    "adzuna": "search(key-gated)",
    "ziprecruiter": "search(scraping)",
    "glassdoor": "stub",
    "linkedin": "fill-only(browser)",
    "indeed": "search(scraping)",
}

#: 03's captcha states -> this adapter's captcha states.
_CAPTCHA_MAP = {"clear": "none", "challenged": "seen", "blocked": "blocking"}


def _provider_health_module() -> Any | None:
    """Lazy import of Initiative 03's contract (repo-root module)."""
    try:
        import provider_health  # noqa: F401

        return provider_health
    except ImportError as exc:
        log.warning("provider_health (Initiative 03) not importable: %s", exc)
        return None


def _parse_ts(value: Any) -> float:
    if not value:
        return 0.0
    try:
        dt = datetime.fromisoformat(str(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except ValueError:
        return 0.0


@dataclass
class HealthSnapshot:
    """One provider's health at a moment in time.

    The scorecard consumes these; ``snapshot_from_status`` builds them
    from 03's ``provider_status()`` rows.
    """

    provider: str
    fetched_at: float  # epoch seconds; here = last successful fetch
    success: bool
    freshness_s: float = 0.0
    error_state: str = ""
    last_success_ts: float = 0.0
    capability_label: str = ""
    budget_used: int = 0
    budget_total: int = 0
    cooldown_until: float = 0.0
    captcha_state: str = "none"  # "none" | "seen" | "blocking"
    recovery_streak: int = 0
    consecutive_failures: int = 0
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "HealthSnapshot":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in raw.items() if k in known})

    @property
    def is_fresh(self) -> bool:
        return (time.time() - self.fetched_at) < 600

    @property
    def is_cooling_down(self) -> bool:
        return self.cooldown_until > time.time()


def snapshot_from_status(provider: str, row: dict[str, Any]) -> HealthSnapshot:
    """Map one ``provider_health.provider_status()`` row onto a snapshot.

    This is the entire 03→09 field mapping. If 03 renames fields, update
    here and only here.
    """
    from providers import _contract as _contract_mod

    now = time.time()
    status = row.get("status") or "ok"
    last_success = _parse_ts(row.get("last_successful_fetch"))
    budget = row.get("budget") or {}
    daily_limit = budget.get("daily_limit")
    declared_daily, _ = _contract_mod.budget_for(provider)
    if status == "blocked":
        error_state = f"captcha:{row.get('captcha_state') or 'blocked'}"
    elif status == "cooling":
        error_state = row.get("cooldown_reason") or "cooling"
    elif status == "degraded":
        error_state = f"{row.get('consecutive_failures') or 0}x_consecutive_failures"
    else:
        error_state = ""
    return HealthSnapshot(
        provider=provider,
        fetched_at=last_success or 0.0,
        success=status == "ok",
        freshness_s=(now - last_success) if last_success else 0.0,
        error_state=error_state,
        last_success_ts=last_success,
        capability_label=CAPABILITY_LABELS.get(provider, "unknown"),
        budget_used=int(budget.get("used_today") or 0),
        budget_total=int(daily_limit) if daily_limit is not None else declared_daily,
        cooldown_until=now + float(row.get("cooldown_remaining_s") or 0),
        captcha_state=_CAPTCHA_MAP.get(
            str(row.get("captcha_state") or "clear"), "none"
        ),
        recovery_streak=int(row.get("recovery_streak_days") or 0),
        consecutive_failures=int(row.get("consecutive_failures") or 0),
        detail=str(row.get("cooldown_reason") or ""),
    )


class HealthStore(Protocol):
    """Storage protocol the scorecard reads."""

    def record(self, snapshot: HealthSnapshot) -> None: ...
    def latest(self, provider: str) -> HealthSnapshot | None: ...
    def providers(self) -> list[str]: ...


class ProviderHealthAdapter:
    """Read/write adapter over Initiative 03's ``provider_health`` module.

    Writes delegate to 03's ``record_fetch``/``record_captcha`` so there is
    exactly one write path. Reads map ``provider_status()`` rows onto
    ``HealthSnapshot`` via ``snapshot_from_status``.
    """

    def record(self, snapshot: HealthSnapshot) -> None:
        ph = _provider_health_module()
        if ph is None:
            raise RuntimeError(
                "provider_health unavailable and no fallback store configured"
            )
        if snapshot.captcha_state == "blocking":
            ph.record_captcha(snapshot.provider, "blocked")
        ph.record_fetch(
            snapshot.provider,
            snapshot.success,
            note=snapshot.detail or snapshot.error_state,
        )

    def latest(self, provider: str) -> HealthSnapshot | None:
        ph = _provider_health_module()
        if ph is None:
            return None
        store = ph.load_store()
        if provider not in store:
            return None
        return snapshot_from_status(provider, ph.provider_status(provider, store))

    def providers(self) -> list[str]:
        ph = _provider_health_module()
        if ph is None:
            return []
        return sorted(ph.load_store().keys())


class FileHealthStore:
    """Append-only JSONL health store, local-first.

    Fallback when 03's module is unavailable, and the store the unit tests
    use. One JSON object per line; ``latest()`` scans from the end. Health
    data never leaves the device.

    Streak math (last success, recovery streak, consecutive failures) is
    computed here on write, mirroring 03's semantics, so this store is
    self-consistent when used standalone.
    """

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._cache: dict[str, HealthSnapshot] = {}

    def record(self, snapshot: HealthSnapshot) -> None:
        prev = self._cache.get(snapshot.provider)
        if prev is None:
            prev = self._latest_from_file(snapshot.provider)
        now = time.time()
        if snapshot.success:
            snapshot.last_success_ts = now
            snapshot.fetched_at = now
            snapshot.recovery_streak = (prev.recovery_streak + 1) if prev else 1
            snapshot.consecutive_failures = 0
            snapshot.error_state = ""
            snapshot.captcha_state = "none"
        else:
            snapshot.last_success_ts = prev.last_success_ts if prev else 0.0
            snapshot.fetched_at = prev.fetched_at if prev else now
            snapshot.recovery_streak = 0
            snapshot.consecutive_failures = (
                prev.consecutive_failures + 1 if prev else 1
            )
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(snapshot.to_dict()) + "\n")
        except OSError as exc:
            log.warning("Could not write health snapshot: %s", exc)
            return
        self._cache[snapshot.provider] = snapshot

    def _latest_from_file(self, provider: str) -> HealthSnapshot | None:
        if not self.path.exists():
            return None
        found: HealthSnapshot | None = None
        try:
            with self.path.open(encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        raw = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if raw.get("provider") == provider:
                        found = HealthSnapshot.from_dict(raw)
        except OSError:
            return None
        return found

    def latest(self, provider: str) -> HealthSnapshot | None:
        if provider in self._cache:
            return self._cache[provider]
        found = self._latest_from_file(provider)
        if found is not None:
            self._cache[provider] = found
        return found

    def providers(self) -> list[str]:
        seen: list[str] = list(self._cache.keys())
        if not self.path.exists():
            return sorted(seen)
        try:
            with self.path.open(encoding="utf-8") as fh:
                for line in fh:
                    try:
                        raw = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    name = raw.get("provider")
                    if name and name not in seen:
                        seen.append(name)
        except OSError:
            pass
        return sorted(seen)


def record_fetch(
    store: HealthStore,
    provider: str,
    *,
    success: bool,
    capability_label: str = "",
    error_state: str = "",
    budget_used: int = 0,
    budget_total: int = 0,
    cooldown_until: float = 0.0,
    captcha_state: str = "none",
    detail: str = "",
) -> HealthSnapshot:
    """Build a snapshot and persist it through ``store``.

    Streak/last-success math is the store's job (03's ``record_fetch`` on
    the adapter path; ``FileHealthStore.record`` on the fallback path) —
    this function only supplies the attempt's facts.
    """
    snapshot = HealthSnapshot(
        provider=provider,
        fetched_at=time.time(),
        success=success,
        error_state="" if success else error_state,
        capability_label=capability_label,
        budget_used=budget_used,
        budget_total=budget_total,
        cooldown_until=cooldown_until,
        captcha_state="none" if success else captcha_state,
        detail=detail,
    )
    store.record(snapshot)
    return snapshot


def default_store() -> HealthStore:
    """The store the scorecard reads.

    Initiative 03's ``provider_health`` when importable, else the local
    JSONL fallback. If 03's contract publishes in a new location, update
    ``_provider_health_module`` — nothing downstream changes.
    """
    if _provider_health_module() is not None:
        return ProviderHealthAdapter()
    log.warning("Falling back to FileHealthStore; 03's contract unavailable")
    return FileHealthStore(
        Path(__file__).resolve().parent.parent / "provider_health_fallback.jsonl"
    )

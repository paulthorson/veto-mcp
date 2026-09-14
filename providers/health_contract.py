#!/usr/bin/env python3
"""Provider-health contract — Initiative 09's interface to Initiative 03.

STATUS (2026-09-13, reworked): Initiative 03's provider-health contract
EXISTS in-tree and is committed (``provider_health.py``, repo root). Per
the roadmap's CONTRACT-FIRST rule, this module is an ADAPTER over their
contract, not a parallel definition:

* WRITE path: providers call ``provider_health.record_fetch`` /
  ``record_captcha`` (03's functions) — directly or via
  ``health_contract.record_fetch`` / ``ProviderHealthAdapter.record``,
  which delegate.
* READ path: the scorecard reads through ``default_store()``, which
  returns a ``ProviderHealthAdapter`` mapping 03's ``provider_status()``
  rows onto ``HealthSnapshot``. The mapping is explicit (see
  ``snapshot_from_status``); if 03 renames a field, exactly one function
  needs updating.
* FALLBACK: if ``provider_health`` cannot be imported (e.g. 03
  restructures mid-flight), ``default_store()`` degrades to the local
  ``FileHealthStore`` — loudly (stderr + log error, not a silent log
  warning) — and the scorecard keeps working on an i09-owned store with
  03-mirroring semantics.

FAIL-SAFE ON SCHEMA DRIFT (Rule 1 hardening): ``snapshot_from_status``
recognizes exactly 03's documented statuses (``ok``/``cooling``/
``degraded``/``blocked``). An absent or unrecognized ``status`` maps to
an EXPLICIT ``unknown`` state — ``success`` is ``False`` (never ``True``)
so the scoreboard can never render drift as green/healthy. ``unknown``
snapshots are also never written to 03's store on the adapter write
path: inventing a fetch we did not observe would be fabricated data.

This module never edits ``provider_health.py`` (another team's file).
"""

from __future__ import annotations

import json
import logging
import os
import sys
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

#: The only ``provider_status()`` statuses this adapter recognizes, per
#: 03's ``provider_status`` docstring ("ok / cooling / degraded /
#: blocked"). Anything else — absent or unrecognized — is schema drift
#: and maps to an explicit ``unknown`` snapshot (never to ``ok``).
_KNOWN_STATUSES = frozenset({"ok", "cooling", "degraded", "blocked"})

#: Fallback JSONL store: append-only is bounded by compaction. Once the
#: file exceeds this many lines, the store is compacted down to the most
#: recent snapshot per provider. Retention policy: per-provider latest
#: only after compaction; no history beyond the live tail is kept.
FALLBACK_MAX_LINES = 1000


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

    ``status`` is the mapped tri-state: ``"ok"`` (observed success),
    ``"error"`` (observed failure / captcha / cooldown), or ``"unknown"``
    (03's row had no recognizable status — absent or unrecognized — so we
    know nothing; ``success`` is ``False`` and the scoreboard must not
    render green). ``status`` and ``success`` are always consistent:
    ``"ok"`` implies ``success=True``; anything else implies ``False``.

    ``recovery_streak`` is measured in CALENDAR DAYS, matching 03's
    ``recovery_streak_days`` exactly: the number of distinct days on
    which this provider recovered from a failing state. It increments at
    most once per calendar day (guarded by ``last_recovery_day``) and is
    NOT per-attempt. The ``FileHealthStore`` fallback mirrors 03's day
    math so the column means the same thing on both stores.
    """

    provider: str
    fetched_at: float  # epoch seconds; here = last successful fetch
    success: bool
    status: str = "ok"  # "ok" | "error" | "unknown"
    freshness_s: float = 0.0
    error_state: str = ""
    last_success_ts: float = 0.0
    capability_label: str = ""
    budget_used: int = 0
    budget_total: int = 0
    cooldown_until: float = 0.0
    captcha_state: str = "none"  # "none" | "seen" | "blocking"
    recovery_streak: int = 0  # calendar DAYS (see docstring), not attempts
    last_recovery_day: str = ""  # ISO date (UTC) of last streak increment
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

    Rule 1 fail-safe: only 03's documented statuses are recognized. An
    absent or unrecognized ``status`` yields an explicit ``unknown``
    snapshot with ``success=False`` — schema drift is never coerced to
    healthy.
    """
    from providers import _contract as _contract_mod

    now = time.time()
    raw_status = row.get("status")
    if raw_status in _KNOWN_STATUSES:
        status = "ok" if raw_status == "ok" else "error"
        success = raw_status == "ok"
        error_state: str | None = None
    else:
        status = "unknown"
        success = False
        error_state = f"unknown:status={raw_status!r}"
        log.warning(
            "provider_health row for %s has unrecognized status %r; "
            "surfacing as UNKNOWN (never healthy)",
            provider,
            raw_status,
        )
    last_success = _parse_ts(row.get("last_successful_fetch"))
    budget = row.get("budget") or {}
    daily_limit = budget.get("daily_limit")
    declared_daily, _ = _contract_mod.budget_for(provider)
    if error_state is None:
        if raw_status == "blocked":
            error_state = f"captcha:{row.get('captcha_state') or 'blocked'}"
        elif raw_status == "cooling":
            error_state = row.get("cooldown_reason") or "cooling"
        elif raw_status == "degraded":
            error_state = (
                f"{row.get('consecutive_failures') or 0}x_consecutive_failures"
            )
        else:
            error_state = ""
    return HealthSnapshot(
        provider=provider,
        fetched_at=last_success or 0.0,
        success=success,
        status=status,
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

    Writes delegate to 03's ``record_fetch``/``record_captcha``/
    ``set_budget``/``cooldown`` so there is exactly one write path. Reads
    map ``provider_status()`` rows onto ``HealthSnapshot`` via
    ``snapshot_from_status``.

    Write-path field coverage (what is NOT dropped):

    * ``success``/``detail``/``error_state`` → ``record_fetch(ok, note)``.
      03 counts the attempt itself (``used_today``/``total_fetches`` +1).
    * ``budget_total`` → ``set_budget(daily_limit)`` when > 0.
    * ``cooldown_until`` → remaining seconds passed to
      ``record_captcha(..., cooldown_seconds=...)`` for a block, or to
      ``cooldown(seconds, reason)`` for a captcha-free cooldown.
    * ``captcha_state`` → ``record_captcha`` ("seen"→"challenged",
      "blocking"→"blocked"). A successful fetch already clears a
      transient challenge inside 03's ``record_fetch``.
    * ``status == "unknown"`` → NOTHING is written. An unknown snapshot
      is not an observed outcome; writing it to 03's store would invent a
      fetch that never happened.

    What is still lost, and why (03's contract has no counterpart):

    * ``budget_used`` (absolute): 03 owns budget counters internally;
      there is no setter for ``used_today``. The attempt just recorded is
      counted (+1), so 03's ``used_today`` stays truthful on its own
      terms — but an absolute ``budget_used`` carried on the snapshot
      cannot be imposed.
    * ``capability_label``: a display label defined by i09
      (``CAPABILITY_LABELS``); 03's contract has no capability concept, so
      it stays on the ``HealthSnapshot`` for the scorecard column only.
    * ``fetched_at``/``last_success_ts``/``recovery_streak``/
      ``consecutive_failures``: 03 derives all of these from its own
      write history; they are read back via ``provider_status()``.
    """

    def record(self, snapshot: HealthSnapshot) -> None:
        ph = _provider_health_module()
        if ph is None:
            raise RuntimeError(
                "provider_health unavailable and no fallback store configured"
            )
        if snapshot.status == "unknown":
            log.warning(
                "refusing to write UNKNOWN snapshot for %s to "
                "provider_health: no observed outcome",
                snapshot.provider,
            )
            return
        now = time.time()
        if snapshot.captcha_state == "blocking":
            remaining = snapshot.cooldown_until - now
            ph.record_captcha(
                snapshot.provider,
                "blocked",
                cooldown_seconds=(
                    max(1, int(remaining)) if remaining > 0 else 3600
                ),
            )
        elif snapshot.captcha_state == "seen":
            remaining = snapshot.cooldown_until - now
            ph.record_captcha(
                snapshot.provider,
                "challenged",
                cooldown_seconds=(
                    max(1, int(remaining)) if remaining > 0 else 3600
                ),
            )
        elif snapshot.cooldown_until > now:
            ph.cooldown(
                snapshot.provider,
                int(snapshot.cooldown_until - now),
                reason=snapshot.error_state or snapshot.detail,
            )
        if snapshot.budget_total > 0:
            ph.set_budget(snapshot.provider, snapshot.budget_total)
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

    Streak math mirrors 03 exactly: ``recovery_streak`` counts distinct
    CALENDAR DAYS on which a failing provider recovered (at most one
    increment per day, guarded by ``last_recovery_day``) — it is NOT
    per-attempt. A snapshot whose ``status`` is ``"unknown"`` carries no
    observed outcome, so all counters carry forward untouched (an unknown
    is neither a success nor a failure).

    RETENTION (bounded growth): the file is compacted to the most recent
    snapshot per provider once it exceeds ``FALLBACK_MAX_LINES`` lines
    (checked every 100 records). The store therefore cannot grow
    unboundedly in the working tree.
    """

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._cache: dict[str, HealthSnapshot] = {}
        self._writes_since_check = 0

    def record(self, snapshot: HealthSnapshot) -> None:
        prev = self._cache.get(snapshot.provider)
        if prev is None:
            prev = self._latest_from_file(snapshot.provider)
        now = time.time()
        today = datetime.now(timezone.utc).date().isoformat()
        if snapshot.status == "unknown":
            # No observed outcome: counters stay exactly as the previous
            # snapshot left them. Unknown is unknown, not a failure.
            snapshot.last_success_ts = prev.last_success_ts if prev else 0.0
            snapshot.fetched_at = prev.fetched_at if prev else now
            snapshot.recovery_streak = prev.recovery_streak if prev else 0
            snapshot.last_recovery_day = (
                prev.last_recovery_day if prev else ""
            )
            snapshot.consecutive_failures = (
                prev.consecutive_failures if prev else 0
            )
        elif snapshot.success:
            was_failing = (prev.consecutive_failures if prev else 0) > 0
            snapshot.last_success_ts = now
            snapshot.fetched_at = now
            snapshot.consecutive_failures = 0
            snapshot.error_state = ""
            snapshot.captcha_state = "none"
            if was_failing:
                # One increment per calendar day at most (03's day math).
                if (prev.last_recovery_day if prev else "") != today:
                    snapshot.recovery_streak = (
                        prev.recovery_streak if prev else 0
                    ) + 1
                    snapshot.last_recovery_day = today
                else:
                    snapshot.recovery_streak = (
                        prev.recovery_streak if prev else 0
                    )
                    snapshot.last_recovery_day = (
                        prev.last_recovery_day if prev else ""
                    )
            else:
                snapshot.recovery_streak = prev.recovery_streak if prev else 0
                snapshot.last_recovery_day = (
                    prev.last_recovery_day if prev else ""
                )
        else:
            snapshot.last_success_ts = prev.last_success_ts if prev else 0.0
            snapshot.fetched_at = prev.fetched_at if prev else now
            snapshot.recovery_streak = prev.recovery_streak if prev else 0
            snapshot.last_recovery_day = (
                prev.last_recovery_day if prev else ""
            )
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
        self._writes_since_check += 1
        if self._writes_since_check >= 100:
            self._writes_since_check = 0
            self._compact_if_needed()

    def _compact_if_needed(self) -> None:
        """Bound the append-only file: keep the latest line per provider."""
        if not self.path.exists():
            return
        try:
            with self.path.open(encoding="utf-8") as fh:
                lines = fh.readlines()
        except OSError:
            return
        if len(lines) <= FALLBACK_MAX_LINES:
            return
        latest: dict[str, str] = {}
        for line in lines:
            try:
                name = json.loads(line).get("provider")
            except (json.JSONDecodeError, AttributeError):
                continue
            if name:
                latest[name] = line
        try:
            with self.path.open("w", encoding="utf-8") as fh:
                fh.writelines(latest.values())
        except OSError as exc:
            log.warning("Could not compact health store: %s", exc)
            return
        log.info(
            "Compacted %s: %d lines -> %d providers",
            self.path,
            len(lines),
            len(latest),
        )

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
    this function only supplies the attempt's facts. ``success`` is an
    observed outcome, never inferred: the snapshot's ``status`` is
    derived from it (``"ok"``/``"error"``).
    """
    snapshot = HealthSnapshot(
        provider=provider,
        fetched_at=time.time(),
        success=success,
        status="ok" if success else "error",
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


def _fallback_path() -> Path:
    """Fallback store location: OUT of the repo tree.

    Local-first device data belongs in the user's data dir, not the git
    working tree (bounded by ``FileHealthStore`` compaction regardless).
    """
    base = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
    return base / "veto" / "provider_health_fallback.jsonl"


def default_store() -> HealthStore:
    """The store the scorecard reads.

    Initiative 03's ``provider_health`` when importable, else the local
    JSONL fallback. The fallback switch is LOUD (stderr + error log —
    the two stores have different semantics: 03's live contract vs i09's
    day-unit approximation) because it changes what the scoreboard means.
    If 03's contract publishes in a new location, update
    ``_provider_health_module`` — nothing downstream changes.
    """
    if _provider_health_module() is not None:
        return ProviderHealthAdapter()
    path = _fallback_path()
    msg = (
        "health_contract: Initiative 03's provider_health is unavailable — "
        f"using LOCAL JSONL FALLBACK at {path}. Recovery streaks on this "
        "store are i09's day-unit approximation and 03's budget counters "
        "are not shared. The scoreboard's meaning changes on this path."
    )
    log.error(msg)
    print(msg, file=sys.stderr)
    return FileHealthStore(path)

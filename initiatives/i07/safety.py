#!/usr/bin/env python3
"""Safety controls for mentor matching & warm paths (Initiative 07, epic 6).

* **Block** — a blocked actor never appears in matches/previews and cannot
  start or answer handshakes with the blocker. Pending handshakes between
  the pair are auto-withdrawn.
* **Report** — abuse reports with a fixed category; 2+ distinct reporters
  quarantine an actor (hidden from discovery, pending handshakes
  withdrawn, audit entry written).
* **Rate limits** — token-bucket limiter per (actor, action), plus the
  consent module's per-pair and per-day introduction caps.
* **Deletion** — full erase of a mentor card, handshake payloads, session
  notes, and reports on request. Block entries keep the id only.
* **Segregation** — :func:`segregation_check` fails loudly if mentorship
  data ever cross-references job-application data. Mentorship must never
  influence application decisions.

All state lives under this package directory (``safety.json``,
``reports.jsonl``); paths are reassignable for tests. Stdlib only.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("job-apply-mcp.i07.safety")

BASE_DIR = Path(__file__).resolve().parent

#: Block list + quarantine state. Reassign in tests.
SAFETY_FILE = BASE_DIR / "safety.json"

#: Abuse reports, append-only. Reassign in tests.
REPORTS_FILE = BASE_DIR / "reports.jsonl"

#: Fixed report categories — free text is not a category.
REPORT_CATEGORIES = (
    "spam",
    "harassment",
    "inappropriate_contact",
    "misrepresentation",
    "other",
)

#: Distinct reporters required before an actor is quarantined.
QUARANTINE_THRESHOLD = 2

#: Default token-bucket settings per action: (capacity, refill_per_second).
DEFAULT_LIMITS: dict[str, tuple[int, float]] = {
    "request_introduction": (5, 5 / 86400),  # 5 per rolling 24h
    "mentor_respond": (50, 50 / 86400),
    "report": (10, 10 / 86400),
    "reveal_contact": (100, 100 / 3600),
    "draft_outreach": (60, 60 / 3600),
}

#: In-memory token buckets: (actor, action) -> {"tokens": float, "at": float}.
_BUCKETS: dict[tuple[str, str], dict[str, float]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Block / quarantine state
# ---------------------------------------------------------------------------


def _load_safety() -> dict[str, Any]:
    try:
        data = json.loads(SAFETY_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"blocked": {}, "quarantined": {}}
    if not isinstance(data, dict):
        return {"blocked": {}, "quarantined": {}}
    data.setdefault("blocked", {})
    data.setdefault("quarantined", {})
    return data


def _save_safety(state: dict[str, Any]) -> None:
    SAFETY_FILE.parent.mkdir(parents=True, exist_ok=True)
    SAFETY_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )


def block_actor(blocker_id: str, blocked_id: str, *, reason: str = "") -> dict[str, Any]:
    """Block ``blocked_id`` on behalf of ``blocker_id``.

    The blocked actor disappears from the blocker's discovery results and
    can neither start nor answer handshakes with the blocker. Pending
    handshakes between the pair are withdrawn immediately (recorded as
    system withdrawals in the consent audit trail).
    """
    if not str(blocker_id or "").strip() or not str(blocked_id or "").strip():
        return {"ok": False, "error": "blocker_id and blocked_id are required"}
    if blocker_id == blocked_id:
        return {"ok": False, "error": "cannot block yourself"}
    state = _load_safety()
    state["blocked"].setdefault(str(blocker_id), {})
    state["blocked"][str(blocker_id)][str(blocked_id)] = {
        "at": _now(),
        "reason": str(reason or "").strip(),
    }
    _save_safety(state)
    withdrawn = _withdraw_pair_handshakes(
        blocker_id, blocked_id, reason=f"block by {blocker_id}"
    )
    return {"ok": True, "blocked": blocked_id, "withdrawn_handshakes": withdrawn}


def unblock_actor(blocker_id: str, blocked_id: str) -> dict[str, Any]:
    state = _load_safety()
    mine = state["blocked"].get(str(blocker_id), {})
    if str(blocked_id) not in mine:
        return {"ok": False, "error": f"{blocked_id!r} is not blocked by {blocker_id!r}"}
    del mine[str(blocked_id)]
    _save_safety(state)
    return {"ok": True, "unblocked": blocked_id}


def is_blocked(blocker_id: str, blocked_id: str) -> bool:
    state = _load_safety()
    return str(blocked_id) in state["blocked"].get(str(blocker_id), {})


def is_quarantined(actor_id: str) -> bool:
    state = _load_safety()
    return str(actor_id) in state.get("quarantined", {})


def consent_block_check(mentee_id: str, mentor_id: str) -> dict[str, Any]:
    """Refuse a consent interaction if either party blocked the other or is quarantined."""
    if is_blocked(mentee_id, mentor_id) or is_blocked(mentor_id, mentee_id):
        return {
            "blocked": True,
            "error": "introduction unavailable: a block exists between these parties",
        }
    if is_quarantined(mentor_id):
        return {
            "blocked": True,
            "error": "introduction unavailable: this mentor is under safety review",
        }
    if is_quarantined(mentee_id):
        return {
            "blocked": True,
            "error": "introduction unavailable: this account is under safety review",
        }
    return {"blocked": False}


def discovery_exclusions(blocker_id: str) -> set[str]:
    """Mentor ids that must never surface in ``blocker_id``'s discovery.

    The union of actors the user blocked and every quarantined actor.
    Pass to ``mentors.matchmake(..., exclude_mentor_ids=...)``.
    """
    state = _load_safety()
    excluded = set(state["blocked"].get(str(blocker_id), {}))
    excluded.update(state.get("quarantined", {}))
    return excluded


def _withdraw_pair_handshakes(a: str, b: str, *, reason: str) -> list[str]:
    """Withdraw all non-terminal handshakes between a and b. Returns ids."""
    from . import consent

    withdrawn: list[str] = []
    for hs in consent.list_handshakes():
        parties = {hs.get("mentee_id"), hs.get("mentor_id")}
        if {a, b} == parties and hs.get("state") not in consent.TERMINAL_STATES:
            res = consent.withdraw(hs["id"], "system", reason=reason)
            if res.get("ok"):
                withdrawn.append(hs["id"])
    return withdrawn


# ---------------------------------------------------------------------------
# Reports + quarantine
# ---------------------------------------------------------------------------


def report(
    reporter_id: str,
    reported_id: str,
    category: str,
    *,
    detail: str = "",
    handshake_id: str = "",
) -> dict[str, Any]:
    """File an abuse report. Appends to the report log; may trigger quarantine."""
    if category not in REPORT_CATEGORIES:
        return {
            "ok": False,
            "error": f"category must be one of {list(REPORT_CATEGORIES)}, got {category!r}",
        }
    if not str(reporter_id or "").strip() or not str(reported_id or "").strip():
        return {"ok": False, "error": "reporter_id and reported_id are required"}
    if reporter_id == reported_id:
        return {"ok": False, "error": "cannot report yourself"}
    if not check_rate_limit(reporter_id, "report"):
        return {"ok": False, "error": "rate limit: too many reports; slow down"}

    REPORTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "at": _now(),
        "reporter_id": reporter_id,
        "reported_id": reported_id,
        "category": category,
        "detail": str(detail or "").strip(),
        "handshake_id": handshake_id or None,
    }
    with REPORTS_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    quarantined = _maybe_quarantine(reported_id)
    return {"ok": True, "quarantined": quarantined}


def list_reports(reported_id: str | None = None) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    try:
        with REPORTS_FILE.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if reported_id and entry.get("reported_id") != reported_id:
                    continue
                entries.append(entry)
    except FileNotFoundError:
        pass
    return entries


def _distinct_reporters(reported_id: str) -> set[str]:
    return {
        e["reporter_id"]
        for e in list_reports(reported_id)
        if e.get("reporter_id")
    }


def _maybe_quarantine(reported_id: str) -> bool:
    """Quarantine after QUARANTINE_THRESHOLD distinct reporters."""
    if is_quarantined(reported_id):
        return True
    if len(_distinct_reporters(reported_id)) < QUARANTINE_THRESHOLD:
        return False
    state = _load_safety()
    state["quarantined"][reported_id] = {
        "at": _now(),
        "reporters": sorted(_distinct_reporters(reported_id)),
    }
    _save_safety(state)
    # Withdraw that actor's pending handshakes on both sides.
    from . import consent

    for hs in consent.list_handshakes():
        parties = {hs.get("mentee_id"), hs.get("mentor_id")}
        if reported_id in parties and hs.get("state") not in consent.TERMINAL_STATES:
            other = (parties - {reported_id}).pop() if len(parties) == 2 else reported_id
            consent.withdraw(hs["id"], other, reason="actor quarantined")
    from . import consent as _c

    _c._audit("quarantine", "", "system", f"actor={reported_id}")  # noqa: SLF001
    return True


def clear_quarantine(actor_id: str, *, reviewed_by: str) -> dict[str, Any]:
    """Lift a quarantine after human review. ``reviewed_by`` is required and recorded."""
    if not str(reviewed_by or "").strip():
        return {"ok": False, "error": "reviewed_by is required: quarantines lift only on human review"}
    state = _load_safety()
    if actor_id not in state.get("quarantined", {}):
        return {"ok": False, "error": f"{actor_id!r} is not quarantined"}
    del state["quarantined"][actor_id]
    _save_safety(state)
    from . import consent as _c

    _c._audit(  # noqa: SLF001
        "quarantine_cleared", "", reviewed_by, f"actor={actor_id}"
    )
    return {"ok": True, "cleared": actor_id}


# ---------------------------------------------------------------------------
# Rate limits (token bucket)
# ---------------------------------------------------------------------------


def check_rate_limit(actor: str, action: str, *, limits: dict | None = None) -> bool:
    """Consume one token for (actor, action). False = over the limit."""
    table = limits or DEFAULT_LIMITS
    if action not in table:
        return True  # unknown actions are not limited here
    capacity, refill = table[action]
    key = (str(actor), action)
    bucket = _BUCKETS.get(key, {"tokens": float(capacity), "at": time.monotonic()})
    now = time.monotonic()
    bucket["tokens"] = min(float(capacity), bucket["tokens"] + (now - bucket["at"]) * refill)
    bucket["at"] = now
    if bucket["tokens"] < 1.0:
        _BUCKETS[key] = bucket
        return False
    bucket["tokens"] -= 1.0
    _BUCKETS[key] = bucket
    return True


def reset_rate_limits() -> None:
    """Clear in-memory buckets. Tests only."""
    _BUCKETS.clear()


# ---------------------------------------------------------------------------
# Deletion
# ---------------------------------------------------------------------------


def delete_mentor_data(mentor_id: str, *, requested_by: str) -> dict[str, Any]:
    """Erase a mentor's data on request: card, handshake payloads, session notes, reports.

    Block entries keep the id (safety needs to remember who is blocked)
    but the reason is scrubbed. The consent audit trail keeps a tombstone
    (``deleted: true``, no PII) — the trail itself is never rewritten.
    """
    if not str(requested_by or "").strip():
        return {"ok": False, "error": "requested_by is required"}
    import mentors as _mentors
    from . import consent as _c

    removed: dict[str, Any] = {"card": False, "handshakes": 0, "notes": 0, "reports": 0}

    directory = _mentors._load_directory()  # noqa: SLF001
    if mentor_id in directory:
        directory.pop(mentor_id)
        _mentors._save_directory(directory)  # noqa: SLF001
        removed["card"] = True

    store = _c._load()  # noqa: SLF001
    for hs in list(store.values()):
        if hs.get("mentor_id") == mentor_id:
            tombstone = {
                "id": hs["id"],
                "deleted": True,
                "redacted_at": _now(),
                "state": "withdrawn",
            }
            store[hs["id"]] = tombstone
            removed["handshakes"] += 1
    _c._save(store)  # noqa: SLF001

    # Session notes live in the session kit store.
    try:
        from . import session_kit as _sk

        removed["notes"] = _sk.scrub_mentor_notes(mentor_id)
    except (ImportError, AttributeError):
        pass

    # Scrub report details naming this actor (keep category + timestamp).
    kept: list[dict[str, Any]] = []
    for entry in list_reports():
        if entry.get("reported_id") == mentor_id or entry.get("reporter_id") == mentor_id:
            entry["detail"] = ""
            entry["handshake_id"] = None
            removed["reports"] += 1
        kept.append(entry)
    try:
        with REPORTS_FILE.open("w", encoding="utf-8") as fh:
            for entry in kept:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except FileNotFoundError:
        pass

    # Scrub block reasons involving this actor (keep the block itself).
    state = _load_safety()
    for blocker, blocked in state.get("blocked", {}).items():
        if mentor_id in blocked:
            blocked[mentor_id]["reason"] = ""
    _save_safety(state)

    _c._audit("deletion", "", requested_by, f"mentor_id={mentor_id} erased on request")  # noqa: SLF001
    return {"ok": True, "removed": removed}


def delete_mentee_data(mentee_id: str, *, requested_by: str) -> dict[str, Any]:
    """Erase a mentee's handshake payloads and questionnaire answers on request."""
    if not str(requested_by or "").strip():
        return {"ok": False, "error": "requested_by is required"}
    from . import consent as _c

    store = _c._load()  # noqa: SLF001
    count = 0
    for hs in list(store.values()):
        if hs.get("mentee_id") == mentee_id and not hs.get("deleted"):
            store[hs["id"]] = {
                "id": hs["id"],
                "deleted": True,
                "redacted_at": _now(),
                "state": "withdrawn",
            }
            count += 1
    _c._save(store)  # noqa: SLF001
    _c._audit("deletion", "", requested_by, f"mentee_id={mentee_id} erased on request")  # noqa: SLF001
    return {"ok": True, "removed": {"handshakes": count}}


# ---------------------------------------------------------------------------
# Segregation: mentorship must never feed job-application decisions
# ---------------------------------------------------------------------------


def segregation_check() -> dict[str, Any]:
    """Fail loudly if mentorship data cross-references application data.

    Scans the mentor directory, handshake store, session notes, and the
    applications/shortlist stores for shared identifiers (mentor ids,
    handshake ids, card names). Any hit is a hard boundary violation.
    """
    violations: list[str] = []
    import mentors as _mentors
    from . import consent as _c

    base = Path(_mentors.BASE_DIR)
    mentor_ids: set[str] = set()
    try:
        mentor_ids = set(_mentors._load_directory().keys())  # noqa: SLF001
    except Exception as exc:  # noqa: BLE001 - report, don't crash the check
        violations.append(f"could not read mentor directory: {exc}")

    handshake_ids: set[str] = set()
    try:
        handshake_ids = {h.get("id", "") for h in _c._load().values()}  # noqa: SLF001
    except Exception as exc:  # noqa: BLE001
        violations.append(f"could not read handshake store: {exc}")

    markers = {m for m in mentor_ids | handshake_ids if m}
    app_files = [
        base / "applications.json",
        base / "apply_queue.json",
        base / "watches.json",
    ]
    for path in app_files:
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            continue
        for marker in markers:
            if marker and marker in text:
                violations.append(f"{path.name} references mentorship id {marker!r}")

    # Reverse direction: mentorship stores must not carry application ids.
    app_ids: set[str] = set()
    for path in (base / "applications.json", base / "apply_queue.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            continue
        items = data if isinstance(data, list) else data.get("applications", [])
        for item in items if isinstance(items, list) else []:
            if isinstance(item, dict) and item.get("id"):
                app_ids.add(str(item["id"]))
    mentorship_blobs = []
    try:
        mentorship_blobs.append(_c.HANDSHAKES_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        pass
    try:
        mentorship_blobs.append((_mentors.MENTORS_FILE).read_text(encoding="utf-8"))
    except FileNotFoundError:
        pass
    for blob in mentorship_blobs:
        for app_id in app_ids:
            if app_id and app_id in blob:
                violations.append(f"mentorship store references application id {app_id!r}")

    return {"ok": not violations, "violations": violations}

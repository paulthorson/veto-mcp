"""Initiative 08 — quarantine lock (the hard contract).

If any scrub test or runtime check detects personal/secret data escaping
into a contribution pipeline:

  1. the payload is quarantined (moved to an opaque, unreadable blob),
  2. contribution sending is GLOBALLY disabled — for every purpose,
  3. the lock stays until a named contracted security/privacy specialist
     writes a clearing entry naming themselves and the reason,
  4. an independent framework reviewer verifies the clearing, and
  5. Paul's veto still blocks any unlock.

The lock lives in the quarantine directory (persisted across processes),
NOT in the user settings file, so flipping "contributions enabled" in
settings can neither cause nor clear it. It survives restarts by design.

Payloads are stored opaquely: the quarantined bytes are written with the
sensitive content replaced by [QUARANTINED] markers so the incident log
can never become a second copy of the leak.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

STATE_FILENAME = "state.json"
INCIDENT_LOG_FILENAME = "incidents.jsonl"
PAYLOAD_PREFIX = "payload-"

#: Roles permitted to author a quarantine clearing entry (the named
#: contracted security/privacy specialist). Published in contracts.py.
CLEARING_ROLES = frozenset({
    "security_engineer", "privacy_engineer", "security_specialist",
    "privacy_specialist", "contracted_security", "contracted_privacy",
})

# Module-level cache of loaded state (keyed by quarantine dir).
_STATE_CACHE: dict[str, dict[str, Any]] = {}

# Compat alias for the older test helper name.
_QUARANTINE_STATE = None


def quarantine_dir(base_dir: Optional[Path] = None) -> Path:
    """Directory holding the quarantine state, payloads, and incident log.

    ``base_dir`` follows the Initiative 08 convention: the directory that
    *contains* ``contributions/`` (i.e. ``contribute.CONTRIB_DIR.parent``).
    With ``base_dir=None`` the live ``contribute.CONTRIB_DIR`` is used.
    """
    if base_dir is not None:
        root = Path(base_dir) / "contributions"
    else:
        import contribute
        root = Path(contribute.CONTRIB_DIR)
    qdir = root / "quarantine"
    qdir.mkdir(parents=True, exist_ok=True)
    return qdir


def _state_path(base_dir: Optional[Path] = None) -> Path:
    return quarantine_dir(base_dir) / STATE_FILENAME


def _fresh_state() -> dict[str, Any]:
    return {
        "locked": False,
        "incident_id": None,
        "trigger": None,
        "locked_at": None,
        "specialist_clearing": None,
        "reviewer_verification": None,
        "paul_veto": None,
        "unlock_events": [],
    }


def _load_state(base_dir: Optional[Path] = None) -> dict[str, Any]:
    key = str(_state_path(base_dir))
    if key in _STATE_CACHE:
        return _STATE_CACHE[key]
    path = _state_path(base_dir)
    if path.exists():
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            state = _fresh_state()
    else:
        state = _fresh_state()
    _STATE_CACHE[key] = state
    return state


def _save_state(state: dict[str, Any],
               base_dir: Optional[Path] = None) -> None:
    path = _state_path(base_dir)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    _STATE_CACHE[str(path)] = state
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Incident log (append-only)
# ---------------------------------------------------------------------------

def _append_incident(event: dict[str, Any],
                    base_dir: Optional[Path] = None) -> dict[str, Any]:
    log_path = quarantine_dir(base_dir) / INCIDENT_LOG_FILENAME
    entry = dict(event)
    entry.setdefault("recorded_at", _now())
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    try:
        os.chmod(log_path, 0o600)
    except OSError:
        pass
    return entry


def read_incident_log(base_dir: Optional[Path] = None) -> list[dict[str, Any]]:
    """Read the append-only incident log (newest last)."""
    log_path = quarantine_dir(base_dir) / INCIDENT_LOG_FILENAME
    entries: list[dict[str, Any]] = []
    if not log_path.exists():
        return entries
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


# ---------------------------------------------------------------------------
# Raising the lock
# ---------------------------------------------------------------------------

def raise_quarantine(
    trigger: str,
    purpose: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
    payload_bytes: Optional[bytes] = None,
    base_dir: Optional[Path] = None,
) -> dict[str, Any]:
    """Raise the global quarantine lock.

    Quarantines the payload (opaque blob), appends a
    ``quarantine_raised`` entry to the incident log, and locks ALL
    contribution purposes until the ordered clearing evidence exists.
    """
    if not trigger or not trigger.strip():
        raise ValueError("trigger is required to raise quarantine")
    qdir = quarantine_dir(base_dir)
    incident_id = hashlib.sha256(
        f"{_now()}:{trigger}:{os.urandom(8).hex()}".encode()
    ).hexdigest()[:16]

    payload_ref = None
    if payload_bytes is not None:
        payload_ref = quarantine_payload(payload_bytes, incident_id, qdir)

    state = _load_state(base_dir)
    state["locked"] = True
    state["incident_id"] = incident_id
    state["trigger"] = trigger
    state["locked_at"] = _now()
    state["specialist_clearing"] = None
    state["reviewer_verification"] = None
    # A veto is per-incident: a new incident clears a stale veto so the
    # review chain starts fresh. The veto itself is recorded in the log.
    state["paul_veto"] = None
    _save_state(state, base_dir)

    _append_incident({
        "event": "quarantine_raised",
        "incident_id": incident_id,
        "trigger": trigger,
        "purpose": purpose,
        "details": details or {},
        "payload_ref": payload_ref,
    }, base_dir=base_dir)

    return {
        "incident_id": incident_id,
        "status": "locked",
        "trigger": trigger,
        "purpose": purpose,
        "payload_ref": payload_ref,
    }


def quarantine_payload(payload_bytes: bytes, incident_id: str,
                       qdir: Path) -> str:
    """Store a payload opaquely: content replaced, only shape kept."""
    digest = hashlib.sha256(payload_bytes).hexdigest()
    blob = (b"[QUARANTINED PAYLOAD]\n"
            b"incident: " + incident_id.encode() + b"\n"
            b"sha256: " + digest.encode() + b"\n"
            b"bytes: " + str(len(payload_bytes)).encode() + b"\n")
    ref = f"{PAYLOAD_PREFIX}{incident_id}.bin"
    path = qdir / ref
    path.write_bytes(blob)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return ref


def is_quarantined(base_dir: Optional[Path] = None) -> bool:
    """True while the global quarantine lock is active."""
    return bool(_load_state(base_dir).get("locked"))


def can_send(purpose: str, base_dir: Optional[Path] = None) -> bool:
    """Whether a contribution may be sent for ``purpose`` right now."""
    return not is_quarantined(base_dir)


# Compat: contribute.py's settings gate consults this.
def is_locked(base_dir: Optional[Path] = None) -> bool:
    return is_quarantined(base_dir)


# ---------------------------------------------------------------------------
# Settings toggles — explicitly CANNOT clear quarantine
# ---------------------------------------------------------------------------

def _settings_path(base_dir: Optional[Path] = None) -> Path:
    if base_dir is not None:
        return Path(base_dir) / "contributions" / "settings.json"
    import contribute
    return Path(contribute.CONTRIB_DIR) / "settings.json"


def _load_settings(base_dir: Optional[Path] = None) -> dict[str, Any]:
    path = _settings_path(base_dir)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def set_contributions_enabled(enabled: bool,
                              base_dir: Optional[Path] = None) -> dict:
    """Flip the user settings toggle.

    NOTE: this can never clear a quarantine lock. The lock is a separate
    mechanism by design — a settings toggle is not clearing evidence.
    """
    path = _settings_path(base_dir)
    settings = _load_settings(base_dir)
    settings["enabled"] = bool(enabled)
    settings["updated_at"] = _now()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    _append_incident({
        "event": "settings_toggle",
        "enabled": bool(enabled),
        "quarantine_still_locked": is_quarantined(base_dir),
    }, base_dir=base_dir)
    return {
        "enabled": bool(enabled),
        "quarantine_locked": is_quarantined(base_dir),
        "note": ("Settings toggles cannot clear quarantine. "
                 "Clearing requires specialist + reviewer evidence."),
    }


# ---------------------------------------------------------------------------
# Clearing evidence: specialist -> reviewer -> (no Paul veto) -> unlock
# ---------------------------------------------------------------------------

_NAME_RE = re.compile(r"[A-Za-z][A-Za-z .'\-]{1,60}")


def _require_named(value: str, field: str) -> str:
    value = (value or "").strip()
    if len(value) < 3 or not _NAME_RE.fullmatch(value):
        raise ValueError(f"{field} must name a real person/role, "
                         f"not {value!r}")
    return value


def record_specialist_clearing(
    name: str,
    role: str,
    organization: str,
    reason: str,
    base_dir: Optional[Path] = None,
) -> dict[str, Any]:
    """Record the contracted specialist's clearing entry.

    A vague entry is rejected. A valid entry does NOT unlock — the
    independent reviewer must still verify.
    """
    state = _load_state(base_dir)
    if not state.get("locked"):
        raise ValueError("no active quarantine to clear")
    name = _require_named(name, "name")
    role = _require_named(role, "role")
    organization = _require_named(organization, "organization")
    reason = (reason or "").strip()
    if len(reason) < 40 or not re.search(r"[.;:]", reason):
        raise ValueError(
            "reason must be substantive (what was found, what was fixed, "
            "what evidence proves it) — a vague entry is rejected")
    entry = {
        "name": name,
        "role": role,
        "organization": organization,
        "reason": reason,
        "recorded_at": _now(),
        "incident_id": state.get("incident_id"),
    }
    state["specialist_clearing"] = entry
    _save_state(state, base_dir)
    _append_incident({"event": "specialist_clearing", **entry},
                     base_dir=base_dir)
    return {**entry, "status": "locked",
            "note": "Specialist clearing recorded. Quarantine remains "
                    "locked until independent reviewer verification."}


def record_reviewer_verification(
    reviewer_name: str,
    reviewer_role: str,
    verdict: str,
    notes: str,
    base_dir: Optional[Path] = None,
) -> dict[str, Any]:
    """Record the independent framework reviewer's verification.

    ALLOW (with specialist clearing present and no Paul veto) unlocks.
    KICK_BACK, or an active Paul veto, keeps the lock.
    """
    state = _load_state(base_dir)
    if not state.get("locked"):
        raise ValueError("no active quarantine to verify")
    if not state.get("specialist_clearing"):
        raise ValueError(
            "reviewer verification requires a specialist clearing entry first")
    reviewer_name = _require_named(reviewer_name, "reviewer_name")
    verdict = (verdict or "").strip().upper()
    if verdict not in ("ALLOW", "KICK_BACK"):
        raise ValueError("verdict must be ALLOW or KICK_BACK")
    entry = {
        "reviewer_name": reviewer_name,
        "reviewer_role": (reviewer_role or "").strip(),
        "verdict": verdict,
        "notes": (notes or "").strip(),
        "recorded_at": _now(),
        "incident_id": state.get("incident_id"),
    }
    state["reviewer_verification"] = entry
    _append_incident({"event": "reviewer_verification", **entry},
                     base_dir=base_dir)

    veto = state.get("paul_veto")
    veto_active = bool(veto and veto.get("active"))
    if verdict == "ALLOW" and not veto_active:
        state["locked"] = False
        state["unlock_events"].append({
            "unlocked_at": _now(),
            "incident_id": state.get("incident_id"),
            "by": "reviewer_verification",
        })
        _save_state(state, base_dir)
        _append_incident({
            "event": "quarantine_unlocked",
            "incident_id": state.get("incident_id"),
            "unlocked_at": _now(),
        }, base_dir=base_dir)
        return {**entry, "status": "unlocked"}
    _save_state(state, base_dir)
    reason = ("KICK_BACK" if verdict != "ALLOW" else "paul_veto_active")
    return {**entry, "status": "locked", "locked_reason": reason,
            "paul_veto_active": veto_active}


def record_paul_veto(reason: str,
                     base_dir: Optional[Path] = None) -> dict[str, Any]:
    """Paul vetoes the unlock. Only Paul can lift it."""
    state = _load_state(base_dir)
    if not state.get("locked"):
        raise ValueError("no active quarantine to veto")
    reason = (reason or "").strip()
    if len(reason) < 10:
        raise ValueError("veto reason is required")
    veto = {"by": "Paul", "reason": reason, "recorded_at": _now(),
            "incident_id": state.get("incident_id"), "active": True}
    state["paul_veto"] = veto
    _save_state(state, base_dir)
    _append_incident({"event": "paul_veto", **veto}, base_dir=base_dir)
    return {**veto, "status": "locked",
            "note": "Paul veto recorded. Only Paul can withdraw it."}


def withdraw_paul_veto(withdrawn_by: str,
                       base_dir: Optional[Path] = None) -> dict[str, Any]:
    """Withdraw Paul's veto. Only Paul may do this."""
    state = _load_state(base_dir)
    veto = state.get("paul_veto")
    if not veto or not veto.get("active"):
        raise ValueError("no active Paul veto to withdraw")
    if (withdrawn_by or "").strip().lower() != "paul":
        raise ValueError("only Paul can withdraw Paul's veto")
    veto["active"] = False
    veto["withdrawn_at"] = _now()
    state["paul_veto"] = veto
    _save_state(state, base_dir)
    _append_incident({"event": "paul_veto_withdrawn",
                      "incident_id": state.get("incident_id"),
                      "withdrawn_at": veto["withdrawn_at"]},
                     base_dir=base_dir)
    return {"status": "locked", "paul_veto_active": False,
            "note": "Veto withdrawn by Paul. Reviewer verification may "
                    "now unlock the quarantine."}


def get_state(base_dir: Optional[Path] = None) -> dict[str, Any]:
    """Current quarantine state (for status tooling)."""
    state = dict(_load_state(base_dir))
    state["locked"] = bool(state.get("locked"))
    return state


def incident_summary(base_dir: Optional[Path] = None) -> dict[str, Any]:
    """Sanitized incident summary: counts and check classes only.

    No payload content, no contributor-identifying information. Safe for
    the public methodology document.
    """
    log = read_incident_log(base_dir)
    by_check: dict[str, int] = {}
    total = 0
    for entry in log:
        if entry.get("event") == "quarantine_raised":
            total += 1
            check = entry.get("trigger", "unknown")
            by_check[check] = by_check.get(check, 0) + 1
    state = _load_state(base_dir)
    return {
        "total_quarantined": total,
        "open": 1 if state.get("locked") else 0,
        "closed": len(state.get("unlock_events", [])),
        "sending_locked": bool(state.get("locked")),
        "by_check": by_check,
    }

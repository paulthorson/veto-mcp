#!/usr/bin/env python3
"""Two-sided consent handshake for mentor introductions (Initiative 07, epic 3).

The proof of value for this initiative: **a match cannot become an
introduction without explicit consent from both people, and either person
can withdraw at any time.**

Handshake lifecycle
-------------------
``awaiting_mentor`` (mentee requested = mentee's consent recorded)
  -> ``mutual``      (mentor approved; contact details unsealed)
  -> ``declined``    (mentor declined; cooldown before re-request)
  -> ``withdrawn``   (either party withdrew, at ANY stage)
  -> ``expired``     (no mentor answer within TTL; re-request allowed)

Revelation rule
---------------
Neither the mentor's contact detail nor the mentee's chosen contact path
is revealed to the other side until the handshake is ``mutual``.
Redacted previews (name/initials, industry, role, seniority, topics,
ratings, match reasons) are visible before consent; everything that can
identify how to reach someone is sealed.

Local-first honesty contract
----------------------------
Veto is local-first: it never transmits on anyone's behalf. The handshake
record is a *receipt book*, not a messaging channel. ``request_introduction``
records YOUR consent (the mentee act). The mentor's side is recorded via
``mentor_respond`` when you log their out-of-band reply — the function
requires an explicit ``channel`` (how the mentor communicated the
decision) and refuses to fabricate consent. There is deliberately no API
that "approves on behalf of" the other party without that record.

Audit
-----
Every state transition appends one line to ``consent_audit.jsonl``. There
is no API to edit or delete audit entries; deletion requests (see
:mod:`initiatives.i07.safety`) redact handshake payloads but keep a
tombstone in the audit trail.

Synthetic fixtures are always labeled: any test or demo handshake id
starts with ``SYNTHETIC-``. The module never invents mentors, people, or
sessions.

Stdlib only.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("job-apply-mcp.i07.consent")

BASE_DIR = Path(__file__).resolve().parent

#: Handshake records. Reassign in tests to redirect storage.
HANDSHAKES_FILE = BASE_DIR / "handshakes.json"

#: Append-only audit log. Reassign in tests.
AUDIT_FILE = BASE_DIR / "consent_audit.jsonl"

#: Pending requests expire after this long without a mentor answer.
REQUEST_TTL = timedelta(days=7)

#: After a decline, the mentee must wait this long before re-requesting
#: the same mentor.
DECLINE_COOLDOWN = timedelta(days=30)

#: Max new introduction requests per mentee per rolling 24h.
MAX_REQUESTS_PER_DAY = 5

#: Terminal states: no further transitions except re-request (new record).
TERMINAL_STATES = ("mutual", "declined", "withdrawn", "expired")

#: Fields that may appear in a pre-consent preview of a mentor card.
PREVIEW_FIELDS = (
    "id",
    "name",
    "industry",
    "role",
    "seniority",
    "topics",
    "bio",
    "availability",
    "remaining_capacity",
    "rating_summary",
    "reasons",
    "score",
)

#: Contact fields: sealed until mutual consent.
CONTACT_FIELDS = ("linkedin_url", "email", "phone")


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load() -> dict[str, dict[str, Any]]:
    try:
        data = json.loads(HANDSHAKES_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save(store: dict[str, dict[str, Any]]) -> None:
    HANDSHAKES_FILE.parent.mkdir(parents=True, exist_ok=True)
    HANDSHAKES_FILE.write_text(
        json.dumps(store, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )


def _audit(event: str, handshake_id: str, actor: str, detail: str = "") -> None:
    """Append one audit line. There is no API to edit or delete these."""
    AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "at": _now(),
        "event": event,
        "handshake_id": handshake_id,
        "actor": actor,
        "detail": detail,
    }
    with AUDIT_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _new_id(synthetic: bool = False) -> str:
    return ("SYNTHETIC-" if synthetic else "hs-") + uuid.uuid4().hex[:12]


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------


def _get_mentor_card(mentor_id: str) -> dict[str, Any] | None:
    """Read-only lookup of a mentor card from the local directory."""
    import mentors as _mentors

    directory = _mentors._load_directory()  # noqa: SLF001 - same-project read
    card = directory.get(mentor_id)
    return dict(card) if card else None


def _pair_key(mentor_id: str, mentee_id: str) -> str:
    return f"{mentor_id}::{mentee_id}"


def _apply_expiry(store: dict[str, dict[str, Any]]) -> bool:
    """Move past-TTL ``awaiting_mentor`` handshakes to ``expired``.

    Called lazily on every read so the TTL is enforced even though no
    background sweeper exists in the local-first deployment. Returns True
    if anything changed (caller persists).
    """
    now = datetime.now(timezone.utc)
    changed = False
    for hs in store.values():
        if hs.get("state") != "awaiting_mentor":
            continue
        try:
            if datetime.fromisoformat(hs.get("expires_at", "")) <= now:
                hs["state"] = "expired"
                hs["updated_at"] = _now()
                changed = True
                _audit("expire", hs["id"], "system", "request TTL elapsed")
        except ValueError:
            continue
    return changed


def _pending_for_pair(
    store: dict[str, dict[str, Any]], mentor_id: str, mentee_id: str
) -> dict[str, Any] | None:
    for hs in store.values():
        if (
            hs.get("mentor_id") == mentor_id
            and hs.get("mentee_id") == mentee_id
            and hs.get("state") == "awaiting_mentor"
        ):
            return hs
    return None


def _last_terminal_for_pair(
    store: dict[str, dict[str, Any]], mentor_id: str, mentee_id: str
) -> dict[str, Any] | None:
    cands = [
        hs
        for hs in store.values()
        if hs.get("mentor_id") == mentor_id
        and hs.get("mentee_id") == mentee_id
        and hs.get("state") in TERMINAL_STATES
    ]
    if not cands:
        return None
    return max(cands, key=lambda h: h.get("updated_at", ""))


# ---------------------------------------------------------------------------
# Mentee side
# ---------------------------------------------------------------------------


def request_introduction(
    mentor_id: str,
    mentee_id: str,
    mentee_label: str,
    goal: str,
    *,
    context: str = "",
    urgency: str = "exploring",
    expected_outcome: str = "",
    contact_path: str = "",
    synthetic: bool = False,
) -> dict[str, Any]:
    """Record the mentee's consent: request an introduction to a mentor.

    This creates the handshake in ``awaiting_mentor`` — it does NOT contact
    the mentor. The request itself is the mentee's explicit consent.

    Guardrails (all enforced, all returning ``{"ok": False}`` on breach):
      * unknown mentor, or mentor with no remaining capacity
      * either party has blocked the other (:mod:`initiatives.i07.safety`)
      * an ``awaiting_mentor`` handshake already exists for this pair
      * a ``declined`` handshake exists and the cooldown has not elapsed
      * more than MAX_REQUESTS_PER_DAY new requests in the last 24h
      * missing goal or mentee label (a request without a stated goal is
        not a consent-bearing request)
    """
    from . import safety

    if not str(mentor_id or "").strip():
        return {"ok": False, "error": "mentor_id is required"}
    if not str(mentee_id or "").strip():
        return {"ok": False, "error": "mentee_id is required"}
    if not str(mentee_label or "").strip():
        return {"ok": False, "error": "mentee_label is required (name or initials)"}
    if not str(goal or "").strip():
        return {"ok": False, "error": "goal is required: a request without a stated goal is not consent"}

    card = _get_mentor_card(mentor_id)
    if card is None:
        return {"ok": False, "error": f"unknown mentor id {mentor_id!r}"}
    import mentors as _mentors

    if _mentors.remaining_capacity(card) <= 0:
        return {"ok": False, "error": "mentor has no remaining capacity"}

    block = safety.consent_block_check(mentee_id, mentor_id)
    if block.get("blocked"):
        return {"ok": False, "error": block["error"]}

    store = _load()
    _apply_expiry(store)  # TTL is enforced lazily; no background sweeper.
    _save(store)
    if _pending_for_pair(store, mentor_id, mentee_id):
        return {
            "ok": False,
            "error": "an introduction request to this mentor is already pending; withdraw it first to re-request",
        }
    last = _last_terminal_for_pair(store, mentor_id, mentee_id)
    if last and last.get("state") == "declined":
        declined_at = last.get("updated_at", "")
        try:
            dt = datetime.fromisoformat(declined_at)
            if datetime.now(timezone.utc) - dt < DECLINE_COOLDOWN:
                return {
                    "ok": False,
                    "error": "this mentor declined recently; the cooldown has not elapsed",
                }
        except ValueError:
            pass

    day_ago = datetime.now(timezone.utc) - timedelta(hours=24)
    recent = 0
    for hs in store.values():
        if hs.get("mentee_id") == mentee_id:
            try:
                if datetime.fromisoformat(hs.get("created_at", "")) >= day_ago:
                    recent += 1
            except ValueError:
                continue
    if recent >= MAX_REQUESTS_PER_DAY:
        return {
            "ok": False,
            "error": f"rate limit: at most {MAX_REQUESTS_PER_DAY} new introduction requests per 24h",
        }

    now = _now()
    handshake_id = _new_id(synthetic=synthetic)
    hs = {
        "id": handshake_id,
        "mentor_id": mentor_id,
        "mentee_id": mentee_id,
        "mentee_label": str(mentee_label).strip(),
        "goal": str(goal).strip(),
        "context": str(context or "").strip(),
        "urgency": str(urgency or "exploring").strip(),
        "expected_outcome": str(expected_outcome or "").strip(),
        "mentee_contact_path": str(contact_path or "").strip(),
        "state": "awaiting_mentor",
        "mentee_consented_at": now,
        "mentor_consented_at": None,
        "mentor_decision_channel": None,
        "created_at": now,
        "updated_at": now,
        "expires_at": (datetime.now(timezone.utc) + REQUEST_TTL).isoformat(timespec="seconds"),
        "synthetic": bool(synthetic),
        "version": 1,
    }
    store[handshake_id] = hs
    _save(store)
    _audit("request", handshake_id, mentee_id, f"goal={hs['goal'][:80]}")
    return {
        "ok": True,
        "handshake": _public_view(hs, mentee_id),
        "sent": False,
        "note": (
            "Your consent is recorded. Nothing was sent to the mentor — "
            "deliver the request yourself (LinkedIn, email), then record "
            "their reply with mentor_respond."
        ),
    }


# ---------------------------------------------------------------------------
# Mentor side (recorded by the local user from the mentor's out-of-band reply)
# ---------------------------------------------------------------------------


def mentor_respond(
    handshake_id: str,
    decision: str,
    *,
    channel: str,
    note: str = "",
    synthetic: bool = False,
) -> dict[str, Any]:
    """Record the mentor's decision from their out-of-band reply.

    ``decision`` is "approve" or "decline". ``channel`` names HOW the
    mentor communicated it (e.g. "linkedin_dm", "email", "in_person") and
    is REQUIRED — consent is never recorded without provenance, and it is
    never fabricated: there is no code path that approves on the mentor's
    behalf without this explicit record.

    Approve -> state ``mutual``: both consents are now on record and
    contact details may be revealed (see :func:`reveal_contact`).
    Decline -> state ``declined``: starts the re-request cooldown.
    """
    if decision not in ("approve", "decline"):
        return {"ok": False, "error": "decision must be 'approve' or 'decline'"}
    if not str(channel or "").strip():
        return {
            "ok": False,
            "error": "channel is required: consent needs provenance (how the mentor replied)",
        }
    store = _load()
    hs = store.get(handshake_id)
    if hs is None:
        return {"ok": False, "error": f"unknown handshake id {handshake_id!r}"}
    if _apply_expiry(store):
        _save(store)
        hs = store.get(handshake_id)
    if hs.get("state") != "awaiting_mentor":
        return {
            "ok": False,
            "error": f"handshake is {hs.get('state')!r}; only 'awaiting_mentor' can be answered",
        }
    now = _now()
    hs["mentor_decision_channel"] = str(channel).strip()
    hs["mentor_decision_note"] = str(note or "").strip()
    hs["updated_at"] = now
    if decision == "approve":
        # Re-check capacity at approve time: the directory may have filled
        # while the request was pending. Approving consumes one spot so the
        # directory stays honest (mirrors record_outreach on the cold path).
        import mentors as _mentors

        card = _get_mentor_card(hs["mentor_id"])
        if card is None or _mentors.remaining_capacity(card) <= 0:
            hs["state"] = "expired"
            hs["updated_at"] = now
            _save(store)
            _audit("approve_refused", handshake_id, hs["mentor_id"], "no remaining capacity")
            return {"ok": False, "error": "mentor has no remaining capacity; request closed"}
        directory = _mentors._load_directory()  # noqa: SLF001
        live = directory.get(hs["mentor_id"])
        if live is not None:
            live["mentee_count"] = int(live.get("mentee_count", 0)) + 1
            _mentors._save_directory(directory)  # noqa: SLF001
        hs["state"] = "mutual"
        hs["mentor_consented_at"] = now
        _audit("mentor_approve", handshake_id, hs["mentor_id"], f"channel={channel}")
    else:
        hs["state"] = "declined"
        _audit("mentor_decline", handshake_id, hs["mentor_id"], f"channel={channel}")
    _save(store)
    return {"ok": True, "handshake": _public_view(hs, hs["mentee_id"])}


# ---------------------------------------------------------------------------
# Withdrawal — either party, any stage
# ---------------------------------------------------------------------------


def withdraw(handshake_id: str, actor: str, *, reason: str = "") -> dict[str, Any]:
    """Withdraw from a handshake. Either party, at any stage.

    Withdrawal is immediate and final: the handshake moves to
    ``withdrawn`` and sealed contact details can no longer be revealed
    through this handshake (see :func:`reveal_contact`). Withdrawing after
    mutual consent cannot un-see already-shared details — the audit log
    records the revocation so both sides have a receipt.

    ``actor`` is normally one of the two parties. The reserved actor
    ``"system"`` is accepted for safety automation (block/quarantine);
    such withdrawals are audited as system actions with the reason given.
    """
    store = _load()
    hs = store.get(handshake_id)
    if hs is None:
        return {"ok": False, "error": f"unknown handshake id {handshake_id!r}"}
    if actor != "system" and actor not in (hs.get("mentee_id"), hs.get("mentor_id")):
        return {"ok": False, "error": "actor is not a party to this handshake"}
    if hs.get("state") in ("withdrawn",):
        return {"ok": False, "error": "handshake is already withdrawn"}
    if hs.get("state") in ("declined", "expired"):
        return {
            "ok": False,
            "error": f"handshake already ended as {hs.get('state')!r}; nothing to withdraw",
        }
    was_mutual = hs.get("state") == "mutual"
    hs["state"] = "withdrawn"
    hs["withdrawn_by"] = actor
    hs["withdraw_reason"] = str(reason or "").strip()
    hs["updated_at"] = _now()
    _save(store)
    _audit(
        "withdraw",
        handshake_id,
        actor,
        f"was_mutual={was_mutual}" + (f" reason={reason[:80]}" if reason else ""),
    )
    return {"ok": True, "handshake": _public_view(hs, actor)}


# ---------------------------------------------------------------------------
# Revelation — sealed until mutual
# ---------------------------------------------------------------------------


def reveal_contact(handshake_id: str, actor: str) -> dict[str, Any]:
    """Reveal contact details to a party — ONLY in ``mutual`` state.

    Returns the mentor's contact detail to the mentee and the mentee's
    chosen contact path to the mentor. Any other state (including
    ``withdrawn`` after a mutual) refuses. Block status is re-checked at
    reveal time.
    """
    from . import safety

    store = _load()
    hs = store.get(handshake_id)
    if hs is None:
        return {"ok": False, "error": f"unknown handshake id {handshake_id!r}"}
    if actor not in (hs.get("mentee_id"), hs.get("mentor_id")):
        return {"ok": False, "error": "actor is not a party to this handshake"}
    if hs.get("state") != "mutual":
        return {
            "ok": False,
            "error": (
                "contact details are sealed: this handshake is "
                f"{hs.get('state')!r}, not 'mutual'. Both parties must approve first."
            ),
        }
    block = safety.consent_block_check(hs["mentee_id"], hs["mentor_id"])
    if block.get("blocked"):
        return {"ok": False, "error": block["error"]}

    card = _get_mentor_card(hs["mentor_id"]) or {}
    mentor_contact = {f: card.get(f) for f in CONTACT_FIELDS if card.get(f)}
    mentee_contact = {"mentee_contact_path": hs.get("mentee_contact_path") or "(not provided)"}
    _audit("reveal", handshake_id, actor, "contact details revealed post-mutual-consent")
    if actor == hs["mentee_id"]:
        return {"ok": True, "mentor_contact": mentor_contact}
    return {"ok": True, "mentee_contact": mentee_contact}


def redacted_preview(card: dict[str, Any]) -> dict[str, Any]:
    """Pre-consent view of a mentor card: discovery fields only, no contact."""
    preview = {k: card.get(k) for k in PREVIEW_FIELDS if k in card}
    if card.get("preferred_contact") == "linkedin_public" and card.get("linkedin_url"):
        preview["linkedin_url"] = card["linkedin_url"]
    return preview


# ---------------------------------------------------------------------------
# Views, listing, expiry
# ---------------------------------------------------------------------------


def _public_view(hs: dict[str, Any], actor: str) -> dict[str, Any]:
    """Handshake as seen by ``actor``: full detail for parties, sealed contact."""
    view = dict(hs)
    # Never leak the other party's raw contact path beyond what consent allows.
    if hs.get("state") != "mutual" or actor not in (hs.get("mentee_id"), hs.get("mentor_id")):
        view.pop("mentee_contact_path", None)
    return view


def get_handshake(handshake_id: str, actor: str) -> dict[str, Any]:
    store = _load()
    if _apply_expiry(store):
        _save(store)
    hs = store.get(handshake_id)
    if hs is None:
        return {"ok": False, "error": f"unknown handshake id {handshake_id!r}"}
    if actor not in (hs.get("mentee_id"), hs.get("mentor_id"), "owner"):
        return {"ok": False, "error": "actor is not a party to this handshake"}
    return {"ok": True, "handshake": _public_view(hs, actor)}


def list_handshakes(
    actor: str | None = None, state: str | None = None
) -> list[dict[str, Any]]:
    """List handshakes, optionally filtered by party and/or state."""
    store = _load()
    if _apply_expiry(store):
        _save(store)
    out = []
    for hs in store.values():
        if actor and actor not in (hs.get("mentee_id"), hs.get("mentor_id")):
            continue
        if state and hs.get("state") != state:
            continue
        out.append(_public_view(hs, actor or "owner"))
    out.sort(key=lambda h: h.get("updated_at", ""), reverse=True)
    return out


def expire_stale(now: datetime | None = None) -> dict[str, Any]:
    """Move ``awaiting_mentor`` handshakes past their TTL to ``expired``.

    Explicit sweep entry point; the same enforcement also runs lazily on
    every read (see :func:`_apply_expiry`), so the TTL holds with no
    background process. ``now`` is injectable for tests.
    """
    store = _load()
    before = {hid for hid, hs in store.items() if hs.get("state") == "awaiting_mentor"}
    # _apply_expiry uses wall-clock; for an injected ``now`` do it inline.
    expired: list[str] = []
    moment = now or datetime.now(timezone.utc)
    for hs in store.values():
        if hs.get("state") != "awaiting_mentor" or hs["id"] not in before:
            continue
        try:
            if datetime.fromisoformat(hs.get("expires_at", "")) <= moment:
                hs["state"] = "expired"
                hs["updated_at"] = _now()
                expired.append(hs["id"])
                _audit("expire", hs["id"], "system", "request TTL elapsed")
        except ValueError:
            continue
    if expired:
        _save(store)
    return {"ok": True, "expired": expired}


def audit_trail(handshake_id: str | None = None) -> list[dict[str, Any]]:
    """Read the append-only audit trail, optionally for one handshake."""
    entries: list[dict[str, Any]] = []
    try:
        with AUDIT_FILE.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if handshake_id and entry.get("handshake_id") != handshake_id:
                    continue
                entries.append(entry)
    except FileNotFoundError:
        pass
    return entries

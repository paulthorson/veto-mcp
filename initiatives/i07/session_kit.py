#!/usr/bin/env python3
"""Session kit for mentor introductions (Initiative 07, epic 4).

* **Agenda** — a first-session plan (extends ``mentors.session_agenda``).
* **Context packet** — the full mentor profile + the mentee's
  questionnaire answers + rating history, assembled ONLY after mutual
  two-sided consent. Assembling it earlier is refused.
* **Question builder** — concrete questions per topic and goal.
* **Notes** — append-only session notes, per handshake.
* **Follow-up** — a next-steps plan after the session.
* **Feedback** — lightweight usefulness rating that feeds the mentor's
  two-sided rating history (consent-gated: only for handshakes that
  reached ``mutual``).

Notes and packets never leave the device; there is no send path anywhere
in this module. Synthetic fixtures are labeled ``SYNTHETIC-``. Stdlib only.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("job-apply-mcp.i07.session_kit")

BASE_DIR = Path(__file__).resolve().parent

#: Session artifacts (notes, packets, feedback) per handshake. Reassignable.
SESSIONS_FILE = BASE_DIR / "sessions.json"

#: Question packs per topic: concrete, open-ended, session-ready.
QUESTION_PACKS: dict[str, list[str]] = {
    "interviewing": [
        "What is the single most common reason strong candidates fail your interview loop?",
        "How should I structure answers for behavioral rounds at your level?",
        "What does 'hiring bar' concretely mean on your team?",
        "Which of my stories is weakest, and how would you rebuild it?",
    ],
    "salary_negotiation": [
        "What information do you wish candidates had before the compensation call?",
        "How do you frame a counter without anchoring too low or alienating the recruiter?",
        "What non-salary levers have you seen work at your company?",
    ],
    "career_switch": [
        "What convinced you (or your team) to bet on a career switcher before?",
        "Which of my transferable skills would you lead with, and which would you downplay?",
        "What is the credible 90-day ramp story for someone from my background?",
    ],
    "leadership": [
        "What distinguishes a senior IC's influence from a manager's at your org?",
        "Tell me about a time you had to deliver hard feedback upward.",
        "How do you build trust with a new team in the first month?",
    ],
    "executive_presence": [
        "What reads as 'executive presence' in your culture, concretely?",
        "How do you prepare differently for an exec-level conversation?",
        "What is a presence mistake you see smart people make repeatedly?",
    ],
    "ai_skills": [
        "Which AI workflows actually save your team time versus just demoing well?",
        "How do you evaluate whether someone uses AI well in an interview?",
        "What is one AI failure mode I should be able to discuss fluently?",
    ],
    "networking": [
        "How do you ask for introductions without burning social capital?",
        "What follow-up cadence has worked for you with senior contacts?",
        "How do you turn a cold conversation warm in one message?",
    ],
    "resume_craft": [
        "What makes you stop reading a resume in the first ten seconds?",
        "How would you reframe my most recent role for the roles I want?",
        "Which metrics on my resume are noise, and which are signal?",
    ],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load() -> dict[str, dict[str, Any]]:
    try:
        data = json.loads(SESSIONS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save(store: dict[str, dict[str, Any]]) -> None:
    SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSIONS_FILE.write_text(
        json.dumps(store, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )


def _get_session(store: dict[str, dict[str, Any]], handshake_id: str) -> dict[str, Any]:
    return store.setdefault(
        handshake_id,
        {
            "handshake_id": handshake_id,
            "notes": [],
            "feedback": [],
            "followups": [],
            "created_at": _now(),
        },
    )


def _mutual_handshake(handshake_id: str, actor: str) -> dict[str, Any]:
    """Return the handshake iff it is mutual and actor is a party."""
    from . import consent

    got = consent.get_handshake(handshake_id, actor)
    if not got.get("ok"):
        return {"ok": False, "error": got.get("error")}
    hs = got["handshake"]
    if hs.get("state") != "mutual":
        return {
            "ok": False,
            "error": (
                "the session kit unlocks only after mutual consent; this "
                f"handshake is {hs.get('state')!r}"
            ),
        }
    return {"ok": True, "handshake": hs}


# ---------------------------------------------------------------------------
# Agenda
# ---------------------------------------------------------------------------


def build_agenda(handshake_id: str, actor: str) -> dict[str, Any]:
    """Build a first-session agenda. Requires mutual consent."""
    import mentors as _mentors

    chk = _mutual_handshake(handshake_id, actor)
    if not chk.get("ok"):
        return chk
    hs = chk["handshake"]
    base = _mentors.session_agenda(hs["mentor_id"], hs.get("goal", ""))
    if not base.get("ok"):
        return base
    agenda = base.get("agenda", "")
    expected = hs.get("expected_outcome", "").strip()
    if expected:
        agenda += f"\n\n## What a useful session produces\n\n{expected}\n"
    urgency = hs.get("urgency", "exploring")
    if urgency == "this_week":
        agenda += (
            "\n> Urgency: this week. Open with the time constraint and agree "
            "on one concrete next step before the call ends.\n"
        )
    return {"ok": True, "agenda": agenda, "handshake_id": handshake_id}


# ---------------------------------------------------------------------------
# Context packet (consent-gated)
# ---------------------------------------------------------------------------


def context_packet(handshake_id: str, actor: str) -> dict[str, Any]:
    """Assemble the full context packet for a session.

    Includes the mentor's full profile (contact included — both parties
    consented), the mentee's questionnaire answers, and rating history.
    REFUSED unless the handshake is mutual.
    """
    import mentors as _mentors

    chk = _mutual_handshake(handshake_id, actor)
    if not chk.get("ok"):
        return chk
    hs = chk["handshake"]
    card = dict(_mentors._load_directory().get(hs["mentor_id"], {}))  # noqa: SLF001
    card["rating_summary"] = _mentors._rating_summary(card)  # noqa: SLF001
    packet = {
        "handshake_id": handshake_id,
        "generated_at": _now(),
        "mentor": card,
        "mentee": {
            "label": hs.get("mentee_label"),
            "goal": hs.get("goal"),
            "context": hs.get("context"),
            "urgency": hs.get("urgency"),
            "expected_outcome": hs.get("expected_outcome"),
        },
        "consent_receipt": {
            "mentee_consented_at": hs.get("mentee_consented_at"),
            "mentor_consented_at": hs.get("mentor_consented_at"),
            "mentor_decision_channel": hs.get("mentor_decision_channel"),
        },
    }
    return {"ok": True, "packet": packet}


# ---------------------------------------------------------------------------
# Question builder
# ---------------------------------------------------------------------------


def question_builder(
    topics: list[str] | None, goal: str = "", n: int = 4
) -> dict[str, Any]:
    """Suggest concrete session questions from topic packs.

    Pure content helper — no consent needed (no personal data involved).
    """
    topics = [t for t in (topics or []) if t in QUESTION_PACKS]
    if not topics:
        return {
            "ok": False,
            "error": f"choose topics from {sorted(QUESTION_PACKS)}",
        }
    questions: list[dict[str, str]] = []
    per = max(1, n // max(1, len(topics)))
    for topic in topics:
        for q in QUESTION_PACKS[topic][:per]:
            questions.append({"topic": topic, "question": q})
    if goal.strip():
        questions.insert(
            0,
            {
                "topic": "goal",
                "question": (
                    f"My goal is: {goal.strip()} — where should I start, "
                    "and what am I likely underestimating?"
                ),
            },
        )
    return {"ok": True, "questions": questions[: max(n, 1)]}


# ---------------------------------------------------------------------------
# Notes (append-only)
# ---------------------------------------------------------------------------


def add_note(
    handshake_id: str, actor: str, text: str, *, kind: str = "note"
) -> dict[str, Any]:
    """Append a session note. Requires mutual consent; notes are append-only."""
    if kind not in ("note", "takeaway", "action"):
        return {"ok": False, "error": "kind must be 'note', 'takeaway', or 'action'"}
    if not str(text or "").strip():
        return {"ok": False, "error": "note text is required"}
    chk = _mutual_handshake(handshake_id, actor)
    if not chk.get("ok"):
        return chk
    store = _load()
    session = _get_session(store, handshake_id)
    session["notes"].append(
        {"at": _now(), "by": actor, "kind": kind, "text": str(text).strip()}
    )
    _save(store)
    return {"ok": True, "note_count": len(session["notes"])}


def get_notes(handshake_id: str, actor: str) -> dict[str, Any]:
    chk = _mutual_handshake(handshake_id, actor)
    if not chk.get("ok"):
        return chk
    session = _load().get(handshake_id, {})
    return {"ok": True, "notes": list(session.get("notes", []))}


def scrub_mentor_notes(mentor_id: str) -> int:
    """Remove session notes for handshakes with this mentor. Used by deletion."""
    from . import consent

    count = 0
    store = _load()
    for hs in consent.list_handshakes():
        if hs.get("mentor_id") == mentor_id and hs["id"] in store:
            count += len(store[hs["id"]].get("notes", []))
            del store[hs["id"]]
    if count:
        _save(store)
    return count


# ---------------------------------------------------------------------------
# Follow-up
# ---------------------------------------------------------------------------


def followup_plan(handshake_id: str, actor: str) -> dict[str, Any]:
    """Draft a follow-up plan from takeaways and actions. Mutual consent required."""
    chk = _mutual_handshake(handshake_id, actor)
    if not chk.get("ok"):
        return chk
    hs = chk["handshake"]
    session = _load().get(handshake_id, {})
    actions = [n for n in session.get("notes", []) if n.get("kind") == "action"]
    takeaways = [n for n in session.get("notes", []) if n.get("kind") == "takeaway"]
    lines = ["# Follow-up plan", ""]
    lines.append("## Thank the mentor")
    lines.append(
        "- Send one short thank-you within 24h naming the single most useful point."
    )
    if takeaways:
        lines.append("")
        lines.append("## Your takeaways")
        lines.extend(f"- {t['text']}" for t in takeaways)
    if actions:
        lines.append("")
        lines.append("## Committed actions")
        lines.extend(f"- [ ] {a['text']}" for a in actions)
    else:
        lines.append("")
        lines.append("## Committed actions")
        lines.append("- [ ] Write down the one action this session produced.")
    lines += [
        "",
        "## Keep the door open",
        "- Share the outcome once you act on the advice — mentors invest "
        "where they see momentum.",
    ]
    store = _load()
    sess = _get_session(store, handshake_id)
    plan = "\n".join(lines)
    sess["followups"].append({"at": _now(), "by": actor, "plan": plan})
    _save(store)
    return {"ok": True, "plan": plan}


# ---------------------------------------------------------------------------
# Lightweight feedback (consent-gated)
# ---------------------------------------------------------------------------


def session_feedback(
    handshake_id: str,
    actor: str,
    useful_1_5: int,
    *,
    note: str = "",
) -> dict[str, Any]:
    """Rate session usefulness 1–5. Only for mutual handshakes.

    Feeds the mentor card's two-sided rating history via
    ``mentors.rate_mentorship`` (``by="mentee"`` or ``by="mentor"``),
    keeping one consistent rating store.
    """
    import mentors as _mentors

    if (
        not isinstance(useful_1_5, int)
        or isinstance(useful_1_5, bool)
        or not 1 <= useful_1_5 <= 5
    ):
        return {"ok": False, "error": "useful_1_5 must be an integer from 1 to 5"}
    chk = _mutual_handshake(handshake_id, actor)
    if not chk.get("ok"):
        return chk
    hs = chk["handshake"]
    side = "mentee" if actor == hs.get("mentee_id") else "mentor"
    rated = _mentors.rate_mentorship(
        hs["mentor_id"], useful_1_5, note=note, by=side
    )
    if not rated.get("ok"):
        return rated
    store = _load()
    session = _get_session(store, handshake_id)
    session["feedback"].append(
        {
            "at": _now(),
            "by": actor,
            "side": side,
            "useful_1_5": useful_1_5,
            "note": str(note or "").strip(),
        }
    )
    _save(store)
    return {
        "ok": True,
        "side": side,
        "useful_1_5": useful_1_5,
        "rating_summary": rated.get("rating_summary"),
    }

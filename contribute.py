#!/usr/bin/env python3
"""Opt-in training-data contributions for the job-apply MCP server.

Users can **voluntarily** send back anonymized training data (mock
interview sessions, soft-skill drills, negotiation-sim rounds,
AI-proficiency exercises) so maintainers can build better AI personas
(interviewer / adversary characters).

Strictly opt-in, never automatic, never silent:

1. ``rate_persona(session_id, stars, note="")`` — rate a completed
   training session 1-5 stars. Ratings are the highest-value training
   signal; rating is frictionless and stays local.
2. ``list_contributable()`` — list completed training sessions that
   could be contributed (summaries only, no transcript content).
3. ``preview_contribution(session_ids)`` — build the exact bundle that
   would be sent: scrubbed transcript excerpts plus the full,
   human-readable PII scrub rule set. Records the bundle hash as
   "previewed".
4. ``submit_contribution(session_ids, confirmed=True)`` — refuses
   unless the bundle was previewed first. Writes the bundle to
   ``contributions/outbox/<uuid>.json`` and appends an append-only
   record to ``contributions/consent.json``. Prints next steps for
   getting it to the repo (``gh`` PR instructions). **Never pushes,
   uploads, or transmits anything itself.**

Privacy rules (non-negotiable):

- No PII ever leaves the machine without explicit per-bundle
  confirmation (preview + ``confirmed=True``).
- Preview is mandatory before submit.
- The consent log is append-only.
- A global kill-switch in ``contributions/settings.json``
  (``contributions_enabled``, default ``true``) is respected by
  ``submit_contribution`` — when off, submitting is refused. Rating
  and previewing are unaffected; they never transmit anything.

Impact loop (the viral flywheel):

5. ``record_impact(version, persona, change_summary, bundle_ids)`` —
   maintainer-curated changelog entry: which anonymized bundles
   informed a persona improvement. Append-only list in
   ``contributions/impact.json``. Bundle ids are validated against
   real outbox files (warns on missing, never fails).
6. ``impact_log()`` — changelog, newest first, human-readable.
7. ``my_impact()`` — scans THIS machine's ``contributions/outbox`` and
   links your bundle UUIDs to impact entries that cite them. Only
   links bundles actually cited; never invents attribution. If none
   are cited yet, it says so plainly and shows the full log.

Stdlib only. All session-store paths are read from the sibling modules
at call time (``mock_interview.SESSIONS_FILE``,
``soft_skills.SESSIONS_PATH``, ``ai_proficiency.STORE_PATH``), so tests
can redirect them by patching those attributes.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("job-apply-mcp.contribute")

BASE_DIR = Path(__file__).resolve().parent

CONTRIB_DIR = BASE_DIR / "contributions"
OUTBOX_DIR = CONTRIB_DIR / "outbox"
CONSENT_PATH = CONTRIB_DIR / "consent.json"
SETTINGS_PATH = CONTRIB_DIR / "settings.json"
PREVIEWED_PATH = CONTRIB_DIR / "previewed.json"
IMPACT_PATH = CONTRIB_DIR / "impact.json"

_BUNDLE_SCHEMA = "veto-contribution/1"


# ---------------------------------------------------------------------------
# PII scrubber (deterministic, stdlib-only)
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_HANDLE_RE = re.compile(r"(?<!\w)@[\w.]{2,}")
_NAME_RE = re.compile(r"\b([A-Z][a-z]{1,}(?:\s+[A-Z][a-z]{1,}){1,2})\b")
_DIGIT_RUN_RE = re.compile(r"\+?\d[\d\s\-.()]*\d")

#: Words that may start or appear inside capitalized sequences but are not
#: person names: months, weekdays, sentence starters, and role/industry
#: title words. Role titles and industries are intentionally KEPT — they
#: are useful persona signal and not identifying.
_NAME_ALLOWLIST = frozenset(
    """
    i ii iii iv v vi vii viii ix x
    january february march april may june july august september october
    november december monday tuesday wednesday thursday friday saturday sunday
    the a an as at in on for with during after before of to and or but so
    my our your their his her its this that these those there here then than
    what when where why how which who whom whose can could would should do
    does did will have has had are is was were be been being get got getting
    give take tell me tell me about good bad new best worst first last next
    black white red blue green senior junior lead staff principal distinguished
    backend frontend full stack software data product design engineering
    engineer developer manager director designer analyst scientist architect
    marketing sales support success operations research machine learning devops
    platform mobile web cloud security growth content brand copywriter writer
    editor recruiter account executive chief officer president founder partner
    associate specialist coordinator strategist administrator consultant
    customer service human resources finance legal accounting team company
    startup enterprise fintech healthtech edtech saas api llm rag
    """.split()
)


def _phone_repl(match: re.Match) -> str:
    digits = re.sub(r"\D", "", match.group(0))
    if len(digits) >= 7:
        return "[REDACTED]"
    return match.group(0)


def _name_repl(match: re.Match) -> str:
    phrase = match.group(0)
    words = phrase.split()
    if any(w.lower() in _NAME_ALLOWLIST for w in words):
        return phrase  # common word / role title — keep it
    return "[NAME]"


#: The exact scrub rule set. Shown verbatim in preview output so the user
#: sees precisely what was redacted and why. Order matters: emails and
#: URLs are redacted before handles (so ``user@host`` inside a URL does
#: not leak), and known company names before the name heuristic.
SCRUB_RULES: list[dict[str, str]] = [
    {
        "rule": "email",
        "description": (
            "Email addresses (anything@domain.tld) -> [REDACTED]. "
            "Applied first so addresses inside URLs are not partially kept."
        ),
    },
    {
        "rule": "url",
        "description": (
            "URLs (http(s)://... and www....) -> [REDACTED]. Profile links, "
            "portfolio links, and any pasted links are removed whole."
        ),
    },
    {
        "rule": "phone",
        "description": (
            "Phone numbers: digit runs with separators, optional leading +, "
            "7 or more digits -> [REDACTED]. Short numbers (years, small "
            "counts) are kept."
        ),
    },
    {
        "rule": "handle",
        "description": (
            "@handles -> [REDACTED]. Social/LinkedIn handles are removed."
        ),
    },
    {
        "rule": "company",
        "description": (
            "Known company names (taken from the session's own metadata, "
            "e.g. the company you practiced interviewing at) -> [COMPANY]. "
            "Role titles and industries are KEPT — they are useful persona "
            "signal and not identifying."
        ),
    },
    {
        "rule": "name",
        "description": (
            "HEURISTIC: 2-3 capitalized words with none of them in the "
            "common-words/role-title allowlist -> [NAME]. Best-effort: it "
            "can miss unusual names and can over-redact. Check the preview "
            "before confirming."
        ),
    },
]


def scrub_rules_report() -> list[dict[str, str]]:
    """Return the human-readable scrub rule set (shown in every preview)."""
    return [dict(r) for r in SCRUB_RULES]


def scrub_text(
    text: str, known_companies: tuple[str, ...] = ()
) -> tuple[str, list[dict[str, Any]]]:
    """Scrub PII from ``text``.

    Returns ``(scrubbed_text, report)`` where ``report`` is a per-rule
    ``{"rule": ..., "redactions": n}`` list in SCRUB_RULES order.
    """
    original = text or ""
    out = original
    counts: dict[str, int] = {}

    # 1. emails
    n0 = out.count("[REDACTED]")
    out = _EMAIL_RE.sub("[REDACTED]", out)
    counts["email"] = out.count("[REDACTED]") - n0
    # 2. urls
    n0 = out.count("[REDACTED]")
    out = _URL_RE.sub("[REDACTED]", out)
    counts["url"] = out.count("[REDACTED]") - n0
    # 3. phones
    out = _DIGIT_RUN_RE.sub(_phone_repl, out)
    counts["phone"] = len(
        re.findall(r"\[REDACTED\]", out)
    ) - (counts["email"] + counts["url"])
    # 4. handles
    n0 = out.count("[REDACTED]")
    out = _HANDLE_RE.sub("[REDACTED]", out)
    counts["handle"] = out.count("[REDACTED]") - n0
    # 5. known companies
    n_comp = 0
    for company in known_companies:
        company = (company or "").strip()
        if not company:
            continue
        pattern = re.compile(re.escape(company), re.IGNORECASE)
        out, n = pattern.subn("[COMPANY]", out)
        n_comp += n
    counts["company"] = n_comp
    # 6. name heuristic
    n0 = len(re.findall(r"\[NAME\]", out))
    out = _NAME_RE.sub(_name_repl, out)
    counts["name"] = len(re.findall(r"\[NAME\]", out)) - n0

    report = [
        {"rule": r["rule"], "redactions": counts.get(r["rule"], 0)}
        for r in SCRUB_RULES
    ]
    return out, report


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _settings() -> dict[str, Any]:
    """Global contribution settings (kill-switch lives here)."""
    settings = _load_json(SETTINGS_PATH, {})
    if not isinstance(settings, dict):
        settings = {}
    settings.setdefault("contributions_enabled", True)
    return settings


def set_contributions_enabled(enabled: bool) -> dict[str, Any]:
    """Flip the global kill-switch. When False, submit is refused."""
    settings = _settings()
    settings["contributions_enabled"] = bool(enabled)
    _atomic_write_json(SETTINGS_PATH, settings)
    return {"contributions_enabled": settings["contributions_enabled"]}


def _previewed_records() -> dict[str, Any]:
    records = _load_json(PREVIEWED_PATH, {})
    return records if isinstance(records, dict) else {}


def _record_preview(bundle_hash: str, session_ids: list[str]) -> None:
    records = _previewed_records()
    records[bundle_hash] = {
        "previewed_at": _utcnow(),
        "session_ids": list(session_ids),
    }
    _atomic_write_json(PREVIEWED_PATH, records)


# ---------------------------------------------------------------------------
# Session-store access (sibling modules own their stores)
# ---------------------------------------------------------------------------


def _source_paths() -> dict[str, Path]:
    """Session-store paths, read from sibling modules at call time so
    tests can redirect them by patching the module attributes."""
    import ai_proficiency
    import mock_interview
    import soft_skills

    return {
        "mock_interview": Path(mock_interview.SESSIONS_FILE),
        "soft_skills": Path(soft_skills.SESSIONS_PATH),
        "ai_proficiency": Path(ai_proficiency.STORE_PATH),
    }


def _load_store(source: str) -> dict[str, Any]:
    path = _source_paths()[source]
    data = _load_json(path, {})
    if source == "ai_proficiency":
        sessions = data.get("sessions", {}) if isinstance(data, dict) else {}
    else:
        sessions = data if isinstance(data, dict) else {}
    return sessions if isinstance(sessions, dict) else {}


def _save_store(source: str, sessions: dict[str, Any]) -> None:
    path = _source_paths()[source]
    if source == "ai_proficiency":
        data = _load_json(path, {})
        if not isinstance(data, dict):
            data = {}
        data["sessions"] = sessions
        _atomic_write_json(path, data)
    else:
        _atomic_write_json(path, sessions)


def _find_session(session_id: str) -> tuple[str | None, dict[str, Any] | None]:
    for source in ("mock_interview", "soft_skills", "ai_proficiency"):
        sessions = _load_store(source)
        session = sessions.get(session_id)
        if isinstance(session, dict):
            return source, session
    return None, None


# ---------------------------------------------------------------------------
# Completion + summaries
# ---------------------------------------------------------------------------


def _session_complete(source: str, session: dict[str, Any]) -> bool:
    if source == "mock_interview":
        return bool(session.get("complete"))
    if source == "soft_skills":
        return bool(session.get("done"))
    if source == "ai_proficiency":
        return bool(session.get("submitted"))
    return False


def _session_score(source: str, session: dict[str, Any]) -> float | None:
    try:
        if source == "mock_interview":
            answers = session.get("answers", {})
            scores = [
                a.get("overall")
                for a in answers.values()
                if isinstance(a, dict) and a.get("overall") is not None
            ]
            return round(sum(scores) / len(scores), 1) if scores else None
        if source == "soft_skills":
            history = session.get("history", [])
            scores = [
                h.get("score")
                for h in history
                if isinstance(h, dict) and h.get("score") is not None
            ]
            return round(sum(scores) / len(scores), 1) if scores else None
        if source == "ai_proficiency":
            score = session.get("score")
            return round(float(score), 2) if score is not None else None
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    return None


def _session_persona(source: str, session: dict[str, Any]) -> str:
    if source == "mock_interview":
        return "mock_interviewer"
    if source == "soft_skills":
        stype = session.get("type")
        if stype == "negotiation":
            return "hiring_manager_adversary"
        mode = session.get("mode", "coach")
        return f"interview_drill_{mode}"
    if source == "ai_proficiency":
        return "exercise_checker"
    return "unknown"


def _session_type(source: str, session: dict[str, Any]) -> str:
    if source == "mock_interview":
        return "mock_interview"
    if source == "soft_skills":
        return f"soft_skill_{session.get('type', 'drill')}"
    if source == "ai_proficiency":
        return "ai_proficiency_exercise"
    return "unknown"


def _session_difficulty(source: str, session: dict[str, Any]) -> str | None:
    if source == "soft_skills":
        return session.get("difficulty")
    return None


def _session_completed_at(
    source: str, session: dict[str, Any]
) -> str | None:
    for key in ("completed_at", "finished_at", "created_at", "created",
                "started_at"):
        value = session.get(key)
        if value:
            return str(value)
    return None


def _summary(source: str, session_id: str, session: dict[str, Any]) -> dict[str, Any]:
    """Bundle summary — metadata only, NO transcript content."""
    rating = session.get("persona_rating") or {}
    return {
        "session_id": session_id,
        "source": source,
        "session_type": _session_type(source, session),
        "persona": _session_persona(source, session),
        "difficulty": _session_difficulty(source, session),
        "score": _session_score(source, session),
        "rating_stars": rating.get("stars"),
        "completed_at": _session_completed_at(source, session),
    }


def list_contributable() -> dict[str, Any]:
    """List completed training sessions eligible for contribution.

    Returns summaries (session type, persona, difficulty, score, rating)
    WITHOUT any transcript content.
    """
    items: list[dict[str, Any]] = []
    for source in ("mock_interview", "soft_skills", "ai_proficiency"):
        for session_id, session in _load_store(source).items():
            if isinstance(session, dict) and _session_complete(source, session):
                items.append(_summary(source, session_id, session))
    items.sort(key=lambda i: str(i.get("completed_at") or ""))
    return {
        "contributable": items,
        "count": len(items),
        "note": (
            "Summaries only — no transcript content. Use "
            "preview_contribution(session_ids) to see exactly what would be "
            "sent, scrubbed, before anything leaves this machine."
        ),
    }


# ---------------------------------------------------------------------------
# Ratings (frictionless, stored locally with the session)
# ---------------------------------------------------------------------------


def rate_persona(
    session_id: str, stars: int, note: str = ""
) -> dict[str, Any]:
    """Rate the AI persona of a completed training session, 1-5 stars.

    Stored alongside the session in its own store file; never transmitted.
    Ratings are the highest-value training signal — make them frictionless.
    """
    try:
        stars_int = int(stars)
    except (TypeError, ValueError):
        return {"error": "stars must be an integer 1-5."}
    if not 1 <= stars_int <= 5:
        return {"error": "stars must be an integer 1-5."}
    source, session = _find_session(session_id)
    if source is None or session is None:
        return {"error": f"Unknown session {session_id!r}."}
    if not _session_complete(source, session):
        return {
            "error": f"Session {session_id!r} is not complete yet — finish it before rating."
        }
    rating = {
        "stars": stars_int,
        "note": str(note or ""),
        "rated_at": _utcnow(),
    }
    session["persona_rating"] = rating
    sessions = _load_store(source)
    sessions[session_id] = session
    _save_store(source, sessions)
    log.info("rated session %s: %d stars", session_id, stars_int)
    return {"session_id": session_id, "source": source, **rating}


# ---------------------------------------------------------------------------
# Bundle building (scrubbed transcripts + rule visibility)
# ---------------------------------------------------------------------------


def _ai_exercise_prompt(track: str, lesson_id: str) -> str:
    try:
        import ai_proficiency

        lessons = ai_proficiency.TRACKS.get(track, {}).get("lessons", [])
        for lesson in lessons:
            if lesson.get("id") == lesson_id:
                return str(lesson.get("exercise", {}).get("prompt", ""))
    except Exception:  # noqa: BLE001 - defensive; excerpt stays empty
        pass
    return ""


def _transcript_excerpts(
    source: str, session: dict[str, Any]
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    """Return (scrubbed turns, aggregate scrub report) for a session.

    Turns are ``{"role": "ai"|"user", "text": <scrubbed>}``. Company
    names come from the session's own metadata.
    """
    known_companies: tuple[str, ...] = ()
    raw_turns: list[tuple[str, str]] = []

    if source == "mock_interview":
        company = str(session.get("company") or "")
        if company:
            known_companies = (company,)
        questions = {q["id"]: q for q in session.get("questions", []) if "id" in q}
        for qid, answer in (session.get("answers") or {}).items():
            q = questions.get(qid, {})
            raw_turns.append(("ai", str(q.get("question", ""))))
            raw_turns.append(("user", str(answer.get("answer", ""))))
    elif source == "soft_skills":
        stype = session.get("type")
        if stype == "negotiation":
            for event in session.get("history", []):
                role = "ai" if event.get("role") == "adversary" else "user"
                raw_turns.append((role, str(event.get("text", ""))))
        else:
            raw_turns.append(("ai", str(session.get("prompt", ""))))
            for event in session.get("history", []):
                raw_turns.append(("user", str(event.get("answer", ""))))
                feedback = event.get("feedback")
                if feedback:
                    raw_turns.append(
                        ("ai", str(feedback) if isinstance(feedback, str)
                         else json.dumps(feedback))
                    )
    elif source == "ai_proficiency":
        prompt = _ai_exercise_prompt(
            str(session.get("track", "")), str(session.get("lesson_id", ""))
        )
        if prompt:
            raw_turns.append(("ai", prompt))
        raw_turns.append(
            ("user",
             "[response text is not retained locally; only the deterministic "
             "score and feedback were kept]")
        )

    turns: list[dict[str, str]] = []
    aggregate: dict[str, int] = {r["rule"]: 0 for r in SCRUB_RULES}
    for role, text in raw_turns:
        scrubbed, report = scrub_text(text, known_companies=known_companies)
        for entry in report:
            aggregate[entry["rule"]] += entry["redactions"]
        turns.append({"role": role, "text": scrubbed})
    scrub_report = [
        {"rule": r["rule"], "redactions": aggregate[r["rule"]]}
        for r in SCRUB_RULES
    ]
    return turns, scrub_report


def _build_bundle(session_ids: list[str]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Build the contribution bundle, or return (None, error_dict)."""
    if not session_ids:
        return None, {"error": "No session_ids given."}
    seen: set[str] = set()
    ordered: list[str] = []
    for sid in session_ids:
        sid = str(sid or "").strip()
        if sid and sid not in seen:
            seen.add(sid)
            ordered.append(sid)
    if not ordered:
        return None, {"error": "No session_ids given."}
    entries: list[dict[str, Any]] = []
    aggregate = {r["rule"]: 0 for r in SCRUB_RULES}
    for session_id in ordered:
        source, session = _find_session(session_id)
        if source is None or session is None:
            return None, {"error": f"Unknown session {session_id!r}."}
        if not _session_complete(source, session):
            return None, {
                "error": (
                    f"Session {session_id!r} is not complete and cannot be "
                    "contributed. Finish or rate it first."
                )
            }
        turns, report = _transcript_excerpts(source, session)
        for entry in report:
            aggregate[entry["rule"]] += entry["redactions"]
        summary = _summary(source, session_id, session)
        rating = session.get("persona_rating") or {}
        entries.append(
            {
                "session_id": session_id,
                "source": summary["source"],
                "session_type": summary["session_type"],
                "persona": summary["persona"],
                "difficulty": summary["difficulty"],
                "score": summary["score"],
                "rating_stars": rating.get("stars"),
                "rating_note": rating.get("note", ""),
                "completed_at": summary["completed_at"],
                "transcript": turns,
            }
        )
    bundle = {
        "schema": _BUNDLE_SCHEMA,
        "created_at": _utcnow(),
        "purpose": (
            "Voluntary, anonymized training data for improving Veto's AI "
            "personas (interviewer / adversary characters). PII scrubbed "
            "per the rules listed in scrub_rules."
        ),
        "sessions": entries,
        "scrub_summary": [
            {"rule": r["rule"], "redactions": aggregate[r["rule"]]}
            for r in SCRUB_RULES
        ],
    }
    return bundle, {}


def _bundle_hash(bundle: dict[str, Any]) -> str:
    """Hash the bundle's stable content.

    ``created_at`` is excluded: the bundle is rebuilt from the same
    session ids at preview and at submit time, and the hash must match
    across both builds to prove the exact same sessions (with the same
    scrubbed content) were reviewed.
    """
    stable = {k: v for k, v in bundle.items() if k != "created_at"}
    canonical = json.dumps(stable, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def preview_contribution(session_ids: list[str]) -> dict[str, Any]:
    """Build the exact bundle that would be sent and return it for review.

    Records the bundle hash as "previewed" so ``submit_contribution``
    can verify this exact bundle was reviewed. Nothing is transmitted.
    """
    bundle, error = _build_bundle(list(session_ids or []))
    if bundle is None:
        return error
    bundle_hash = _bundle_hash(bundle)
    _record_preview(bundle_hash, [e["session_id"] for e in bundle["sessions"]])
    return {
        "bundle": bundle,
        "bundle_hash": bundle_hash,
        "scrub_rules": scrub_rules_report(),
        "next": (
            "Review the bundle above. If it looks right, call "
            "submit_contribution(session_ids, confirmed=True) with the same "
            "session ids. Nothing has been sent."
        ),
    }


# ---------------------------------------------------------------------------
# Submit (gated, local-only, append-only consent)
# ---------------------------------------------------------------------------

NEXT_STEPS = """\
Your anonymized bundle is staged locally at {outbox} — nothing has been
uploaded or transmitted.

To send it to the Veto repo so maintainers can train better personas:

  1. Fork the repo (once):  gh repo fork <veto-repo-url> --clone=false
  2. Create a branch and add your bundle:
       gh repo clone <your-fork-url> /tmp/veto-contrib
       cp {outbox} /tmp/veto-contrib/data/contributions/
       cd /tmp/veto-contrib && git add data/contributions && \\
         git commit -m "contrib: anonymized training sessions" && git push -u origin contrib/training-data
  3. Open the PR:  gh pr create --title "contrib: training data" \\
       --body "Opt-in anonymized training sessions. Scrubbed per contribute.py rules; consent recorded locally."

Prefer not to use git? Attach {outbox} to a GitHub issue on the Veto repo
titled "training data contribution" instead.
""".strip()


def submit_contribution(
    session_ids: list[str], confirmed: bool = False
) -> dict[str, Any]:
    """Stage a reviewed contribution bundle for manual delivery.

    Gated: refuses unless ``confirmed=True`` AND the exact bundle was
    previously previewed. Respects the global kill-switch. Writes the
    bundle to ``contributions/outbox/<uuid>.json`` and appends an
    append-only record to ``contributions/consent.json``. Never pushes,
    uploads, or transmits anything itself.
    """
    if not _settings().get("contributions_enabled", True):
        return {
            "error": (
                "Contributions are disabled by the kill-switch "
                "(contributions/settings.json: contributions_enabled=false). "
                "Nothing was staged."
            )
        }
    if not confirmed:
        return {
            "error": (
                "Not confirmed. Review the bundle with "
                "preview_contribution(session_ids) first, then call "
                "submit_contribution(session_ids, confirmed=True)."
            )
        }
    bundle, error = _build_bundle(list(session_ids or []))
    if bundle is None:
        return error
    bundle_hash = _bundle_hash(bundle)
    if bundle_hash not in _previewed_records():
        return {
            "error": (
                "This exact bundle was never previewed. Call "
                "preview_contribution(session_ids) first so you can review "
                "every scrubbed transcript before confirming."
            )
        }

    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    outbox_name = f"{uuid.uuid4().hex}.json"
    outbox_path = OUTBOX_DIR / outbox_name
    _atomic_write_json(outbox_path, bundle)

    consent = _load_json(CONSENT_PATH, [])
    if not isinstance(consent, list):
        consent = []
    consent.append(
        {
            "consented_at": _utcnow(),
            "session_ids": [e["session_id"] for e in bundle["sessions"]],
            "bundle_hash": bundle_hash,
            "outbox_file": outbox_name,
            "consented_to": (
                "Voluntary contribution of anonymized, PII-scrubbed training "
                "sessions (per the scrub rules shown at preview) to the Veto "
                "project for persona improvement. No PII."
            ),
            "delivery": "manual — user delivers the staged file themselves",
        }
    )
    _atomic_write_json(CONSENT_PATH, consent)

    next_steps = NEXT_STEPS.format(outbox=outbox_path.name)
    print(next_steps)
    log.info("contribution staged: %s (%d sessions)", outbox_name, len(bundle["sessions"]))
    return {
        "staged": True,
        "outbox": str(outbox_path),
        "bundle_hash": bundle_hash,
        "session_count": len(bundle["sessions"]),
        "consent_recorded": True,
        "transmitted": False,
        "next_steps": next_steps,
    }


# ---------------------------------------------------------------------------
# Impact loop: contributors see what their data actually improved
# ---------------------------------------------------------------------------


def _impact_entries() -> list[dict[str, Any]]:
    """Append-only maintainer-curated changelog (oldest first on disk)."""
    entries = _load_json(IMPACT_PATH, [])
    return entries if isinstance(entries, list) else []


def record_impact(
    version: str,
    persona: str,
    change_summary: str,
    bundle_ids: list[str] | str,
) -> dict[str, Any]:
    """Record a maintainer-curated persona-improvement changelog entry.

    Args:
        version: Persona version, e.g. ``"1.3"``.
        persona: Persona id, e.g. ``"hardball_negotiator"``.
        change_summary: What changed, e.g. ``"now pushes on equity,
            not just base"``.
        bundle_ids: Outbox bundle UUIDs whose anonymized data informed
            the change. Validated against real outbox files — missing
            ids produce a warning, never a failure.

    Returns:
        The recorded entry (plus ``warnings`` if any bundle id was not
        found in ``contributions/outbox``).
    """
    version = str(version or "").strip()
    persona = str(persona or "").strip()
    change = str(change_summary or "").strip()
    if not version:
        return {"error": "version is required (e.g. '1.3')."}
    if not persona:
        return {"error": "persona is required (e.g. 'hardball_negotiator')."}
    if not change:
        return {
            "error": (
                "change_summary is required — describe what the data "
                "changed about the persona."
            )
        }
    if isinstance(bundle_ids, str):
        bundle_ids = [b for b in bundle_ids.split(",") if b.strip()]
    cited = [str(b).strip() for b in (bundle_ids or []) if str(b).strip()]
    if not cited:
        return {
            "error": (
                "bundle_ids is required — cite at least one outbox bundle "
                "UUID whose anonymized data informed this change. "
                "Impact is only attributed to data that was actually used."
            )
        }

    warnings: list[str] = []
    known = (
        {p.stem for p in OUTBOX_DIR.glob("*.json")}
        if OUTBOX_DIR.is_dir()
        else set()
    )
    for bid in cited:
        if bid not in known:
            warnings.append(
                f"Bundle id {bid!r} not found in contributions/outbox — "
                "cited anyway; double-check the id."
            )
            log.warning("record_impact: unknown bundle id %s", bid)

    entry = {
        "version": version,
        "persona": persona,
        "change": change,
        "bundle_ids": cited,
        "recorded_at": _utcnow(),
    }
    entries = _impact_entries()
    entries.append(entry)
    _atomic_write_json(IMPACT_PATH, entries)
    log.info("recorded impact: %s v%s (%d bundle(s))", persona, version,
             len(cited))
    result: dict[str, Any] = {"recorded": True, "entry": entry}
    if warnings:
        result["warnings"] = warnings
    return result


def impact_log() -> dict[str, Any]:
    """Return the persona-improvement changelog, newest first."""
    entries = _impact_entries()
    ordered = list(reversed(entries))
    lines: list[str] = []
    for entry in ordered:
        n = len(entry.get("bundle_ids") or [])
        lines.append(
            f"- {entry.get('persona')} v{entry.get('version')} — "
            f"{entry.get('change')} "
            f"(informed by {n} contributed bundle{'s' if n != 1 else ''})"
        )
    return {
        "impacts": ordered,
        "count": len(ordered),
        "rendered": (
            "\n".join(lines)
            if lines
            else "No persona improvements recorded yet — be the first "
                 "contributor whose data ships a better persona."
        ),
    }


def _plural(n: int, singular: str, plural: str | None = None) -> str:
    return f"{n} {singular if n == 1 else (plural or singular + 's')}"


def my_impact() -> dict[str, Any]:
    """Link THIS machine's contributed bundles to persona improvements.

    Scans ``contributions/outbox`` for bundles staged on this machine
    and links each to impact entries that cite it. Only bundles actually
    cited are attributed — never invented. If none are cited yet, says
    so plainly and shows the full log.
    """
    local_bundles: list[str] = []
    if OUTBOX_DIR.is_dir():
        local_bundles = sorted(p.stem for p in OUTBOX_DIR.glob("*.json"))
    local_set = set(local_bundles)
    entries = _impact_entries()

    # (persona, version) -> {"persona", "version", "change", "your_bundles"}
    per_persona: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in entries:
        cited = entry.get("bundle_ids") or []
        mine = [b for b in cited if b in local_set]
        if not mine:
            continue
        key = (str(entry.get("persona") or ""), str(entry.get("version") or ""))
        agg = per_persona.setdefault(
            key,
            {
                "persona": entry.get("persona"),
                "version": entry.get("version"),
                "change": entry.get("change"),
                "your_bundles": [],
            },
        )
        for bid in mine:
            if bid not in agg["your_bundles"]:
                agg["your_bundles"].append(bid)

    improvements = sorted(
        per_persona.values(),
        key=lambda i: (str(i["persona"]), str(i["version"])),
    )
    n_local = len(local_bundles)

    if not local_bundles:
        return {
            "contributed_bundles": 0,
            "improvements": [],
            "headline": (
                "You have not staged any contribution bundles on this "
                "machine yet. Complete a training session, preview and "
                "submit it, and this is where you'll see what it improved."
            ),
            "rendered": (
                "No contributed bundles on this machine yet.\n\n"
                + impact_log()["rendered"]
            ),
            "impact_log": impact_log(),
        }

    if not improvements:
        rendered_lines = [
            f"Your {_plural(n_local, 'contributed bundle')} "
            f"{'has' if n_local == 1 else 'have'} not been cited in a "
            "persona improvement yet.",
            "",
            "Maintainers credit contributions in the impact log when a "
            "better persona ships — check back after the next release.",
            "",
            "Full impact log:",
            impact_log()["rendered"],
        ]
        return {
            "contributed_bundles": n_local,
            "improvements": [],
            "headline": (
                f"Your {_plural(n_local, 'contributed bundle')} "
                f"{'has' if n_local == 1 else 'have'} not been cited yet — "
                "the next persona release could change that."
            ),
            "rendered": "\n".join(rendered_lines),
            "impact_log": impact_log(),
        }

    your_cited = sorted({b for i in improvements for b in i["your_bundles"]})
    phrases = [
        f"{i['persona']} v{i['version']} — {i['change']}" for i in improvements
    ]
    headline = (
        f"Your {_plural(len(your_cited), 'contributed bundle')} helped "
        f"improve {_plural(len(improvements), 'persona')}: "
        + "; ".join(phrases)
        + "."
    )
    rendered_lines = [headline, ""]
    for i in improvements:
        rendered_lines.append(
            f"- {i['persona']} v{i['version']} — {i['change']} "
            f"(your cited bundles: {len(i['your_bundles'])})"
        )
    uncited = [b for b in local_bundles if b not in your_cited]
    if uncited:
        rendered_lines += [
            "",
            f"{_plural(len(uncited), 'more bundle')} on this machine "
            "hasn't been cited yet.",
        ]
    return {
        "contributed_bundles": n_local,
        "cited_bundles": len(your_cited),
        "improvements": improvements,
        "headline": headline,
        "rendered": "\n".join(rendered_lines),
    }


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------


def register_tools(mcp: Any) -> None:
    """Register the contribution MCP tools on an MCP server instance."""
    _impl_rate = globals()["rate_persona"]
    _impl_list = globals()["list_contributable"]
    _impl_preview = globals()["preview_contribution"]
    _impl_submit = globals()["submit_contribution"]
    _impl_rules = globals()["scrub_rules_report"]
    _impl_record_impact = globals()["record_impact"]
    _impl_impact_log = globals()["impact_log"]
    _impl_my_impact = globals()["my_impact"]

    @mcp.tool()
    def rate_persona(session_id: str, stars: int, note: str = "") -> dict:
        """Rate an AI persona after a completed training session (1-5 stars).

        Args:
            session_id: A completed mock interview / soft-skill drill /
                negotiation sim / AI-proficiency exercise session.
            stars: 1-5. The highest-value training signal — frictionless.
            note: Optional free-text note about the persona.

        Returns:
            The stored rating. Ratings stay on this machine; nothing is
            transmitted.
        """
        return _impl_rate(session_id, stars, note)

    @mcp.tool()
    def list_contributable() -> dict:
        """List completed training sessions eligible for contribution.

        Returns:
            Summaries (session type, persona, difficulty, score, rating)
            WITHOUT transcript content.
        """
        return _impl_list()

    @mcp.tool()
    def preview_contribution(session_ids: list) -> dict:
        """Preview the exact contribution bundle before anything is sent.

        Args:
            session_ids: Completed session ids from list_contributable.

        Returns:
            The full bundle with SCRUBBED transcript excerpts, the bundle
            hash, and the human-readable scrub rule set. Nothing is sent;
            the hash is recorded as "previewed".
        """
        return _impl_preview(list(session_ids or []))

    @mcp.tool()
    def submit_contribution(session_ids: list, confirmed: bool = False) -> dict:
        """Stage a reviewed contribution bundle for manual delivery.

        Args:
            session_ids: The same session ids passed to
                preview_contribution.
            confirmed: Must be True. The bundle must also have been
                previewed first — otherwise this refuses.

        Returns:
            Staging info: outbox file path, consent record, and next steps
            for getting the file to the repo yourself (gh PR instructions).
            This tool NEVER pushes, uploads, or transmits anything.
        """
        return _impl_submit(list(session_ids or []), confirmed=confirmed)

    @mcp.tool()
    def scrub_rules() -> dict:
        """Show the PII scrub rule set used on contribution bundles.

        Returns:
            The exact rules (emails, urls, phones, handles, company names,
            name heuristic) applied to every transcript excerpt.
        """
        return {"scrub_rules": _impl_rules()}

    @mcp.tool()
    def record_impact(version: str, persona: str, change_summary: str,
                      bundle_ids: list) -> dict:
        """Record a persona-improvement changelog entry (maintainer).

        Args:
            version: Persona version, e.g. "1.3".
            persona: Persona id, e.g. "hardball_negotiator".
            change_summary: What changed, e.g. "now pushes on equity,
                not just base".
            bundle_ids: Outbox bundle UUIDs whose anonymized data
                informed the change. Missing ids warn, never fail.

        Returns:
            The recorded append-only entry (plus warnings for ids not
            found in contributions/outbox).
        """
        return _impl_record_impact(version, persona, change_summary,
                                   list(bundle_ids or []))

    @mcp.tool()
    def impact_log() -> dict:
        """Show the persona-improvement changelog, newest first.

        Returns:
            Entries (persona, version, change, cited bundles,
            recorded_at) plus a human-readable rendering.
        """
        return _impl_impact_log()

    @mcp.tool()
    def my_impact() -> dict:
        """Show what THIS machine's contributions actually improved.

        Returns:
            Your contributed bundles linked to the impact entries that
            cite them — e.g. "your 3 sessions helped improve:
            hardball_negotiator v1.3 (equity pushback)". Only bundles
            actually cited are attributed; if none are cited yet, says
            so plainly and shows the full log.
        """
        return _impl_my_impact()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _print_result(result: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_contribute(args: Any) -> int:
    """CLI handler for `contribute`."""
    as_json = getattr(args, "json", False)
    action = args.action
    if action == "rate":
        result = rate_persona(args.session_id, args.stars, args.note or "")
    elif action == "list":
        result = list_contributable()
    elif action == "preview":
        ids = [s.strip() for s in (args.session_ids or "").split(",") if s.strip()]
        result = preview_contribution(ids)
    elif action == "submit":
        ids = [s.strip() for s in (args.session_ids or "").split(",") if s.strip()]
        result = submit_contribution(ids, confirmed=args.confirm)
    elif action == "rules":
        result = {"scrub_rules": scrub_rules_report()}
    elif action == "record-impact":
        ids = [s.strip() for s in (args.bundle_ids or "").split(",") if s.strip()]
        result = record_impact(args.version, args.persona, args.change, ids)
    elif action == "impact-log":
        result = impact_log()
    elif action == "my-impact":
        result = my_impact()
    elif action == "on":
        result = set_contributions_enabled(True)
    elif action == "off":
        result = set_contributions_enabled(False)
    else:
        result = {"error": f"Unknown action {action!r}."}
    _print_result(result, as_json)
    return 0 if "error" not in result else 1


def register_cli(subparsers: Any) -> dict[str, Any]:
    """Add `contribute` to an argparse subparsers.

    Returns a {command: handler} mapping the caller can merge into its
    own dispatch table (cli.py-style).
    """
    parser = subparsers.add_parser(
        "contribute",
        help="Opt-in: rate personas and contribute anonymized training data.",
    )
    parser.add_argument(
        "action",
        choices=["rate", "list", "preview", "submit", "rules",
                 "record-impact", "impact-log", "my-impact", "on", "off"],
        help=(
            "rate: star-rate a persona. list: show contributable sessions. "
            "preview: review the exact scrubbed bundle. submit: stage it for "
            "manual delivery (needs --confirm). rules: show the PII scrub "
            "rules. record-impact: maintainer logs a persona improvement "
            "(needs --version/--persona/--change/--bundle-ids). impact-log: "
            "show the changelog. my-impact: see what your contributions "
            "improved. on/off: global contribution kill-switch."
        ),
    )
    parser.add_argument("--session-id", help="Session id (for rate).")
    parser.add_argument(
        "--session-ids",
        help="Comma-separated session ids (for preview/submit).",
    )
    parser.add_argument("--stars", type=int, help="1-5 (for rate).")
    parser.add_argument("--note", default="", help="Rating note (for rate).")
    parser.add_argument("--version", help="Persona version (record-impact).")
    parser.add_argument("--persona", help="Persona id (record-impact).")
    parser.add_argument("--change", help="What changed (record-impact).")
    parser.add_argument(
        "--bundle-ids",
        help="Comma-separated outbox bundle UUIDs (record-impact).",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required for submit: confirms the previewed bundle.",
    )
    parser.add_argument(
        "--json", action="store_true", help="Machine-readable JSON output."
    )
    return {"contribute": cmd_contribute}

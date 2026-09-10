#!/usr/bin/env python3
"""Gmail integration for job-apply-mcp.

Two capabilities, both read-safe by default:

* **Recruiter-mail scan** (:func:`scan_recruiter_emails`): searches Gmail for
  recruiter-like mail, classifies it with keyword heuristics, fuzzy-matches
  it against ``applications.json``, and either *proposes* stage updates
  (default) or *applies* them (``apply_updates=True``) — but only when the
  match is unambiguous and classification confidence is high. Never guesses.

* **Follow-up drafts** (:func:`draft_followup` / :func:`send_followup`):
  builds a short professional follow-up from the application record and the
  saved profile. Nothing is sent unless ``confirm=True``.

All Gmail access goes through the Gmail skill's CLI
(``hatch_gws_cli gmail ...``); see ``/opt/hatch/skills/gmail/SKILL.md``.
No credentials are stored here, and raw email bodies are never written to
logs — only counts and truncated subjects.

Wiring contract (server.py / cli.py call these; this module is new-file
only, it does not edit them):

* ``register_tools(mcp)`` — registers the ``scan_recruiter_emails`` and
  ``draft_followup_email`` MCP tools.
* ``register_cli(subparsers)`` — adds the ``email-scan`` and
  ``email-followup`` CLI commands.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Any

import lifecycle

log = logging.getLogger("job-apply-mcp.email_sync")

BASE_DIR = Path(__file__).resolve().parent
APPLICATIONS_FILE = BASE_DIR / "applications.json"

GMAIL_CLI = "hatch_gws_cli"
_CLI_TIMEOUT_S = 90

#: Minimum classifier confidence before a stage update may be auto-applied.
AUTO_APPLY_MIN_CONFIDENCE = 0.8

# ---------------------------------------------------------------------------
# Gmail CLI layer (mock this in tests: email_sync._run_gmail_cli)
# ---------------------------------------------------------------------------


def _run_gmail_cli(*args: str) -> Any:
    """Run ``hatch_gws_cli gmail ...`` and return the parsed JSON output.

    Raises RuntimeError with a PII-free message when the CLI fails.
    """
    cmd = [GMAIL_CLI, "gmail", *args]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=_CLI_TIMEOUT_S
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Gmail CLI (hatch_gws_cli) is not installed or not on PATH."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Gmail CLI timed out.") from exc
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        raise RuntimeError(
            "Gmail CLI failed: " + (detail[0][:200] if detail else "unknown error")
        )
    try:
        return json.loads(proc.stdout or "null")
    except json.JSONDecodeError as exc:
        raise RuntimeError("Gmail CLI returned non-JSON output.") from exc


def _gmail_connected() -> bool:
    """True when the Gmail skill reports a connected account."""
    try:
        status = _run_gmail_cli("status")
    except RuntimeError as exc:
        log.warning("Gmail status check failed: %s", exc)
        return False
    if isinstance(status, dict):
        return status.get("status") == "connected"
    return False


def _gmail_triage(query: str, max_n: int = 50) -> list[dict[str, Any]]:
    """List candidate messages (sender/subject/date/snippet) for a query."""
    out = _run_gmail_cli(
        "+triage", "--query", query, "--max", str(max_n), "--format", "json"
    )
    if isinstance(out, dict) and isinstance(out.get("messages"), list):
        return out["messages"]
    if isinstance(out, list):
        return [m for m in out if isinstance(m, dict)]
    return []


def _gmail_read(message_id: str) -> dict[str, Any]:
    """Read one message; returns a dict (may include body/snippet)."""
    out = _run_gmail_cli("+read", "--id", message_id, "--headers", "--format", "json")
    return out if isinstance(out, dict) else {}


def _gmail_send(to: str, subject: str, body: str) -> dict[str, Any]:
    """Send a message via the connected Gmail account."""
    out = _run_gmail_cli(
        "+send", "--to", to, "--subject", subject, "--body", body, "--format", "json"
    )
    return out if isinstance(out, dict) else {"ok": True}


def _message_text(msg: dict[str, Any]) -> tuple[str, str, str, str]:
    """Tolerantly extract (message_id, sender, subject, text) from a message."""
    mid = str(msg.get("id") or msg.get("message_id") or "")
    sender = str(msg.get("from") or msg.get("sender") or msg.get("From") or "")
    subject = str(msg.get("subject") or msg.get("Subject") or "")
    text = " ".join(
        str(msg.get(k) or "")
        for k in ("body", "snippet", "body_text", "Body")
        if msg.get(k)
    )
    return mid, sender, subject, text


# ---------------------------------------------------------------------------
# Recruiter-mail classifier (heuristics only)
# ---------------------------------------------------------------------------

_CLASS_PHRASES: dict[str, tuple[str, ...]] = {
    "interview_invite": (
        "interview", "phone screen", "video call", "meet the team",
        "schedule a time to speak", "schedule some time", "onsite interview",
        "technical assessment", "coding challenge", "take-home",
        "next round", "final round", "interview loop",
    ),
    "rejection": (
        "not moving forward", "moving forward with other candidates",
        "decided to pursue other", "decided to move forward with",
        "unfortunately", "regret to inform", "not selected",
        "will not be proceeding", "not be proceeding",
    ),
    "offer": (
        "offer letter", "pleased to offer", "offer of employment",
        "formal offer", "we would like to offer you", "extend an offer",
        "compensation package",
    ),
    "followup_needed": (
        "following up", "just following up", "checking in",
        "just checking", "touching base", "circling back",
        "bumping this", "wanted to follow up",
    ),
    "recruiter_outreach": (
        "came across your profile", "impressed by your background",
        "opportunity that might", "reaching out about",
        "we're hiring", "we are hiring", "i'm hiring",
        "would you be open to", "open to a conversation",
    ),
}

#: Mail that is never a recruiter signal on its own.
_NOISE_PHRASES = (
    "job alert", "new jobs for you", "jobs you may like", "recommended jobs",
    "unsubscribe", "application received", "we received your application",
    "thank you for applying", "thanks for applying", "confirming receipt",
    "newsletter", "daily digest",
)

#: Sender domains that belong to recruiting infrastructure, not employers.
_ATS_DOMAINS = {
    "greenhouse.io", "lever.co", "ashbyhq.com", "workday.com",
    "myworkdayjobs.com", "taleo.net", "icims.com", "smartrecruiters.com",
    "jobvite.com", "workable.com", "breezy.hr", "jazz.co", "jazzhr.com",
    "recruitee.com", "eightfold.ai", "phenom.com",
}

#: interview_invite/rejection/offer move the pipeline; the rest are FYI only.
_STAGE_FOR_CLASS = {
    "interview_invite": "interviewing",
    "rejection": "rejected",
    "offer": "offer",
}


def _classify(subject: str, body: str, sender: str) -> tuple[str | None, float]:
    """Return (label, confidence). Heuristics only — no ML."""
    haystack = f"{subject}\n{body}".lower()
    sender_l = sender.lower()

    scores: dict[str, int] = {}
    for label, phrases in _CLASS_PHRASES.items():
        scores[label] = sum(1 for p in phrases if p in haystack)

    noise_hits = sum(1 for p in _NOISE_PHRASES if p in haystack)
    is_noreply = "noreply" in sender_l or "no-reply" in sender_l

    # Noise with no strong recruiter signal (or from a noreply address with
    # only weak signal) is not classified.
    best = max(scores, key=lambda k: scores[k])
    best_score = scores[best]
    if best_score == 0:
        return None, 0.0
    if noise_hits and best_score < 2:
        return None, 0.0
    if is_noreply and best_score < 2 and best != "rejection":
        return None, 0.0

    # Ties are ambiguous: never guess.
    runners_up = [k for k, v in scores.items() if v == best_score and k != best]
    if runners_up:
        return None, 0.0

    confidence = min(0.95, 0.60 + 0.12 * (best_score - 1))
    domain = sender_l.rsplit("@", 1)[-1].strip(" >") if "@" in sender_l else ""
    if domain in _ATS_DOMAINS and best in _STAGE_FOR_CLASS:
        confidence = min(0.95, confidence + 0.05)
    return best, round(confidence, 2)


def classify_recruiter_email(
    subject: str, body: str, sender: str
) -> str | None:
    """Classify a recruiter email.

    Returns one of ``"interview_invite"``, ``"rejection"``, ``"offer"``,
    ``"followup_needed"``, ``"recruiter_outreach"``, or ``None`` when the
    mail is not a confident recruiter signal (newsletters, job alerts,
    application confirmations, ambiguous mail).
    """
    label, _ = _classify(subject or "", body or "", sender or "")
    return label


# ---------------------------------------------------------------------------
# Fuzzy matching against applications.json
# ---------------------------------------------------------------------------

_COMPANY_SUFFIXES = {
    "inc", "incorporated", "llc", "corp", "corporation", "co", "company",
    "ltd", "limited", "technologies", "technology", "tech", "labs",
    "group", "holdings", "plc", "gmbh", "sas", "sa", "ab",
}


def _normalize_company(name: str) -> str:
    words = re.sub(r"[^a-z0-9 ]", " ", (name or "").lower()).split()
    words = [w for w in words if w not in _COMPANY_SUFFIXES]
    return " ".join(words)


def _company_from_sender(sender: str) -> str | None:
    """Best-effort employer name from the sender's email domain."""
    m = re.search(r"@([A-Za-z0-9.-]+)", sender or "")
    if not m:
        return None
    domain = m.group(1).lower()
    if domain in _ATS_DOMAINS:
        return None  # recruiting infrastructure, not the employer
    labels = domain.split(".")
    core = labels[-2] if len(labels) >= 2 else labels[0]
    core = _normalize_company(core.replace("-", " "))
    return core or None


def _companies_match(a: str, b: str) -> bool:
    if not a or not b:
        return False
    if a == b:
        return True
    # Substring match only for names long enough to be meaningful.
    return (len(a) >= 4 and a in b) or (len(b) >= 4 and b in a)


def match_to_application(
    email_meta: dict[str, Any], applications: list[dict[str, Any]]
) -> str | None:
    """Fuzzy-match an email to one application; None when ambiguous.

    Matches on employer name — from the sender's domain and from company
    mentions in the subject/body. Returns the application's ``job_id`` only
    when exactly one application matches; returns None for zero or
    multiple matches (never guesses).
    """
    sender = str(email_meta.get("sender") or email_meta.get("from") or "")
    subject = str(email_meta.get("subject") or "")
    body = str(email_meta.get("body") or email_meta.get("snippet") or "")
    sender_company = _company_from_sender(sender)
    text = _normalize_company(f"{subject} {body}")

    hits: list[dict[str, Any]] = []
    for app in applications:
        if not isinstance(app, dict):
            continue
        company = _normalize_company(str(app.get("company") or ""))
        if not company:
            continue
        matched = _companies_match(sender_company or "", company)
        if not matched and len(company) >= 4 and company in text:
            matched = True
        if matched and app not in hits:
            hits.append(app)

    if len(hits) == 1:
        return str(hits[0].get("job_id") or "")
    return None


# ---------------------------------------------------------------------------
# Scan: propose or apply stage updates
# ---------------------------------------------------------------------------

_SCAN_QUERY = (
    'subject:(interview OR offer OR application OR "phone screen") '
    "-category:promotions -category:social"
)


def _load_profile() -> dict[str, Any]:
    """Load the wizard-saved profile, the same way server.py does (lazily)."""
    try:
        from server import _load_saved_profile  # lazy: avoid import cycles

        profile = _load_saved_profile()
        if isinstance(profile, dict):
            return profile
    except Exception:  # pragma: no cover - defensive
        log.debug("server profile helper unavailable", exc_info=True)
    try:
        from profiles import load_profile  # fallback

        profile = load_profile()
        return profile if isinstance(profile, dict) else {}
    except Exception:  # pragma: no cover - defensive
        return {}


def _find_application(
    entries: list[dict[str, Any]], application_id: str
) -> dict[str, Any]:
    key = str(application_id)
    for entry in entries:
        if str(entry.get("job_id")) == key:
            return entry
    try:
        idx = int(key)
        if 0 <= idx < len(entries):
            return entries[idx]
    except ValueError:
        pass
    raise KeyError(f"No application found for {application_id!r}")


def scan_recruiter_emails(
    days: int = 14, apply_updates: bool = False
) -> dict[str, Any]:
    """Scan Gmail for recruiter mail and reconcile with applications.

    Default (``apply_updates=False``) only *proposes* stage updates.
    With ``apply_updates=True``, updates are applied via
    ``lifecycle.update_stage`` — but only when the application match is
    unambiguous, the classification confidence is high (>= 0.8), and the
    classification maps to a pipeline stage. Outreach and follow-up mail
    never change stages. Raw email bodies are never logged.
    """
    result: dict[str, Any] = {
        "scanned": 0,
        "matched": 0,
        "proposed_updates": [],
        "applied_updates": [],
    }
    if not _gmail_connected():
        result["error"] = "gmail_not_connected"
        result["message"] = (
            "Gmail is not connected. Connect it (Connectors settings in the "
            "app), then retry the scan."
        )
        return result

    query = f"{_SCAN_QUERY} newer_than:{max(1, int(days))}d"
    try:
        candidates = _gmail_triage(query)
    except RuntimeError as exc:
        result["error"] = "gmail_search_failed"
        result["message"] = str(exc)
        return result

    entries = lifecycle.load_entries(APPLICATIONS_FILE)
    result["scanned"] = len(candidates)

    for cand in candidates:
        mid, sender, subject, text = _message_text(cand)
        # Snippets are truncated; pull the full message when the first
        # pass is uncertain so weak signals aren't missed.
        label, confidence = _classify(subject, text, sender)
        if label is None and text:
            try:
                full = _gmail_read(mid) if mid else {}
                _, _, subject2, text2 = _message_text(full)
                label, confidence = _classify(
                    subject2 or subject, text2 or text, sender
                )
            except RuntimeError:
                log.warning("Could not read one candidate message; skipping it")
                continue
        if label is None:
            continue

        app_id = match_to_application(
            {"sender": sender, "subject": subject, "body": text}, entries
        )
        if app_id is None:
            continue
        result["matched"] += 1

        try:
            entry = _find_application(entries, app_id)
        except KeyError:
            continue
        current_stage = str(entry.get("stage") or "applied")
        proposed_stage = _STAGE_FOR_CLASS.get(label)

        proposal: dict[str, Any] = {
            "message_id": mid,
            "subject": subject[:80],
            "classification": label,
            "confidence": confidence,
            "application_id": app_id,
            "company": entry.get("company"),
            "title": entry.get("title"),
            "current_stage": current_stage,
            "proposed_stage": proposed_stage,
            "action": "none",
        }

        if proposed_stage is None:
            # Outreach / follow-up mail: informational only, never a stage.
            proposal["action"] = "review"
            proposal["note"] = (
                "No stage change proposed for this mail type; "
                "review it yourself."
            )
        elif proposed_stage == current_stage:
            proposal["action"] = "already_at_stage"
        elif (
            apply_updates
            and confidence >= AUTO_APPLY_MIN_CONFIDENCE
        ):
            try:
                lifecycle.update_stage(
                    APPLICATIONS_FILE,
                    app_id,
                    proposed_stage,
                    note=(
                        f"auto email-sync: classified as {label} "
                        f"(confidence {confidence})"
                    ),
                )
                proposal["action"] = "applied"
                result["applied_updates"].append(proposal)
                log.info(
                    "Email-sync moved application %s to %s", app_id, proposed_stage
                )
                continue  # already recorded in applied_updates
            except (ValueError, KeyError) as exc:
                proposal["action"] = "apply_failed"
                proposal["note"] = str(exc)
        else:
            proposal["action"] = "proposed"
            if apply_updates:
                proposal["note"] = (
                    "Not auto-applied: confidence below threshold "
                    f"({confidence} < {AUTO_APPLY_MIN_CONFIDENCE})."
                )
        result["proposed_updates"].append(proposal)

    return result


# ---------------------------------------------------------------------------
# Follow-up drafts
# ---------------------------------------------------------------------------

_FOLLOWUP_KINDS = ("check_in", "thank_you", "nudge")


def _draft_body(kind: str, profile: dict[str, Any], entry: dict[str, Any]) -> str:
    name = profile.get("full_name") or "Applicant"
    first = profile.get("first_name") or str(name).split()[0]
    company = entry.get("company") or "your team"
    title = entry.get("title") or "the role"
    skills = [s for s in (profile.get("skills") or []) if s][:4]
    skill_str = ", ".join(skills)
    phone = profile.get("phone") or ""

    if kind == "thank_you":
        return (
            f"Hi,\n\nThank you for taking the time to speak with me about "
            f"the {title} role at {company}. I enjoyed learning more about "
            f"the team and the challenges ahead"
            + (f", and I'm excited about how my experience with {skill_str} "
               if skill_str else "")
            + "could contribute.\n\nPlease let me know if there's anything "
            "else I can provide as you make your decision.\n\n"
            f"Best regards,\n{name}"
            + (f"\n{phone}" if phone else "")
        )
    if kind == "nudge":
        return (
            f"Hi,\n\nI wanted to briefly follow up on my application for "
            f"the {title} position at {company}. I'm very interested in the "
            "role and would welcome the chance to discuss next steps.\n\n"
            f"Best,\n{first}"
            + (f"\n{phone}" if phone else "")
        )
    # check_in (default)
    return (
        f"Hi,\n\nI'm writing to follow up on my application for the {title} "
        f"role at {company}. I'm enthusiastic about the opportunity"
        + (f" — my background in {skill_str} seems like a strong fit"
           if skill_str else "")
        + " — and I'd love to hear about the timeline for next steps.\n\n"
        f"Thank you for your consideration.\n\nBest regards,\n{name}"
        + (f"\n{phone}" if phone else "")
    )


def draft_followup(
    application_id: str, kind: str = "check_in"
) -> dict[str, Any]:
    """Build a follow-up email draft for an application. Does NOT send.

    Returns ``{"application_id", "kind", "to", "subject", "body", "note"}``.
    ``to`` is empty unless the application record carries a recruiter
    contact address — set it before sending.
    """
    kind = (kind or "check_in").strip().lower()
    if kind not in _FOLLOWUP_KINDS:
        raise ValueError(
            f"Unknown follow-up kind {kind!r}. "
            f"Choose from: {', '.join(_FOLLOWUP_KINDS)}"
        )
    entries = lifecycle.load_entries(APPLICATIONS_FILE)
    entry = _find_application(entries, application_id)
    profile = _load_profile()

    company = entry.get("company") or "the company"
    title = entry.get("title") or "the role"
    subjects = {
        "check_in": f"Following up — {title} application",
        "thank_you": f"Thank you — {title} interview",
        "nudge": f"Checking in — {title} at {company}",
    }
    to = str(
        entry.get("recruiter_email")
        or entry.get("contact_email")
        or entry.get("hiring_manager_email")
        or ""
    ).strip()

    return {
        "application_id": str(entry.get("job_id")),
        "kind": kind,
        "to": to,
        "subject": subjects[kind],
        "body": _draft_body(kind, profile, entry),
        "note": (
            "Draft only — not sent. "
            + (
                "Set the recipient address before sending."
                if not to
                else "Review the text, then send with confirm=True."
            )
        ),
    }


def send_followup(
    draft: dict[str, Any], confirm: bool = False
) -> dict[str, Any]:
    """Send a follow-up draft via Gmail — only when ``confirm=True``.

    Without confirmation this returns the draft untouched, with
    instructions, and performs no Gmail call.
    """
    if not confirm:
        return {
            "sent": False,
            "draft": draft,
            "instructions": (
                "Review the draft above carefully. To send it through your "
                "connected Gmail account, call send_followup again with "
                "confirm=True (or run: email-followup <id> --send --confirm "
                "--to <address>)."
            ),
        }
    to = str(draft.get("to") or "").strip()
    subject = str(draft.get("subject") or "").strip()
    body = str(draft.get("body") or "").strip()
    if not to or "@" not in to:
        return {
            "sent": False,
            "draft": draft,
            "error": "no_recipient",
            "instructions": (
                "No recipient address on the draft. Set 'to' to the "
                "recruiter's email address, then confirm again."
            ),
        }
    if not subject or not body:
        return {
            "sent": False,
            "draft": draft,
            "error": "empty_draft",
            "instructions": "Draft is missing a subject or body; not sent.",
        }
    if not _gmail_connected():
        return {
            "sent": False,
            "draft": draft,
            "error": "gmail_not_connected",
            "instructions": "Gmail is not connected; connect it and retry.",
        }
    try:
        sent = _gmail_send(to, subject, body)
    except RuntimeError as exc:
        return {"sent": False, "draft": draft, "error": "gmail_send_failed",
                "instructions": str(exc)}
    log.info("Sent follow-up email (subject %.40s)", subject)
    return {"sent": True, "to": to, "subject": subject, "result": sent}


# ---------------------------------------------------------------------------
# Wiring contract: MCP tools + CLI (server.py / cli.py call these)
# ---------------------------------------------------------------------------


def register_tools(mcp):  # noqa: ANN001, ANN202 - duck-typed FastMCP
    """Register the Gmail tools on a FastMCP instance."""
    # Capture the module-level cores first: the tool wrappers below reuse
    # the same names, which would otherwise shadow the globals.
    _core_scan = globals()["scan_recruiter_emails"]
    _core_draft = globals()["draft_followup"]
    _core_send = globals()["send_followup"]

    @mcp.tool()
    def scan_recruiter_emails(  # noqa: F811 - intentional tool wrapper
        days: int = 14, apply_updates: bool = False
    ) -> dict:
        """Scan Gmail for recruiter mail and reconcile application stages.

        Searches recent mail for interview invites, rejections, and offers,
        classifies each message, and fuzzy-matches it to applications.json.

        Args:
            days: How far back to search (default 14).
            apply_updates: When false (default), only proposes stage
                updates. When true, applies them — but only for
                unambiguous matches with high classification confidence.
                Outreach and follow-up mail never change stages.
        """
        return _core_scan(days=days, apply_updates=apply_updates)

    @mcp.tool()
    def draft_followup_email(  # noqa: ANN202
        application_id: str,
        kind: str = "check_in",
        send: bool = False,
        confirm: bool = False,
    ) -> dict:
        """Draft a follow-up email for a job application.

        Args:
            application_id: The job_id of the application.
            kind: One of "check_in", "thank_you", "nudge".
            send: Also send the draft via Gmail (requires confirm=True).
            confirm: Explicit user confirmation to send. Without it the
                draft is returned unsent with instructions.
        """
        draft = _core_draft(application_id, kind=kind)
        if send:
            return _core_send(draft, confirm=confirm)
        return draft

    return mcp


def _cli_email_scan(args) -> int:  # noqa: ANN001 - argparse namespace
    result = scan_recruiter_emails(days=args.days, apply_updates=args.apply)
    if getattr(args, "json", False):
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    if result.get("error"):
        print(f"Error: {result.get('message')}")
        return 1
    print(
        f"Scanned {result['scanned']} message(s), "
        f"matched {result['matched']} to applications."
    )
    for upd in result["proposed_updates"]:
        print(
            f"  [{upd['action']}] {upd['company']} — {upd['title']}: "
            f"{upd['current_stage']} -> {upd['proposed_stage']} "
            f"({upd['classification']}, confidence {upd['confidence']})"
        )
        if upd.get("note"):
            print(f"      {upd['note']}")
    for upd in result["applied_updates"]:
        print(
            f"  [applied] {upd['company']} — {upd['title']}: "
            f"{upd['current_stage']} -> {upd['proposed_stage']}"
        )
    return 0


def _cli_email_followup(args) -> int:  # noqa: ANN001 - argparse namespace
    try:
        draft = draft_followup(args.application_id, kind=args.kind)
    except (KeyError, ValueError) as exc:
        print(f"Error: {exc}")
        return 1
    if args.to:
        draft["to"] = args.to
    if getattr(args, "json", False):
        out = draft if not args.send else send_followup(draft, confirm=args.confirm)
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0
    if args.send:
        result = send_followup(draft, confirm=args.confirm)
        if result.get("sent"):
            print(f"Sent to {result['to']}: {result['subject']}")
            return 0
        print(f"Not sent: {result.get('error', 'confirmation required')}")
        print(result.get("instructions", ""))
        if not args.confirm:
            print("\n--- Draft ---\n" + draft["body"])
        return 1
    print(f"To: {draft['to'] or '(no recipient on file — use --to)'}")
    print(f"Subject: {draft['subject']}")
    print("\n" + draft["body"])
    print(f"\n({draft['note']})")
    return 0


def register_cli(subparsers) -> None:  # noqa: ANN001 - argparse subparsers
    """Add the ``email-scan`` and ``email-followup`` CLI commands."""
    p_scan = subparsers.add_parser(
        "email-scan",
        help="Scan Gmail for recruiter mail; propose application stage updates.",
    )
    p_scan.add_argument("--days", type=int, default=14,
                        help="How far back to search (default: 14).")
    p_scan.add_argument("--apply", action="store_true",
                        help="Apply confident stage updates (default: propose only).")
    p_scan.add_argument("--json", action="store_true", help="Print raw JSON.")
    p_scan.set_defaults(func=_cli_email_scan)

    p_follow = subparsers.add_parser(
        "email-followup",
        help="Draft (or send) a follow-up email for an application.",
    )
    p_follow.add_argument("application_id", help="job_id of the application.")
    p_follow.add_argument("--kind", default="check_in",
                          choices=list(_FOLLOWUP_KINDS),
                          help="Draft kind (default: check_in).")
    p_follow.add_argument("--to", default="",
                          help="Recipient address (required to send).")
    p_follow.add_argument("--send", action="store_true",
                          help="Send via Gmail (needs --confirm).")
    p_follow.add_argument("--confirm", action="store_true",
                          help="Confirm sending the exact draft shown.")
    p_follow.add_argument("--json", action="store_true", help="Print raw JSON.")
    p_follow.set_defaults(func=_cli_email_followup)

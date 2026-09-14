#!/usr/bin/env python3
"""Session rescue — Initiative 09, epic 5.

Pause browser-assisted fills on CAPTCHA, auth loss, or field ambiguity and
hand control to the user.

THE CORE RULE — CAPTCHA IS NEVER BYPASSED. There is deliberately no code
path in this module (or anywhere in Veto) that solves, clicks through, or
otherwise defeats a CAPTCHA. When one is detected, automation STOPS, a
screenshot is taken, and a handoff bundle is produced so the human can take
over in their own browser. The pause-and-hand-off IS the feature; any
bypass attempt is never made and would be a program-level incident.

Detection runs at three points in a fill:
  1. After navigation / page load (CAPTCHA, auth loss).
  2. After field extraction (field ambiguity).
  3. At the review step of multi-step flows, and immediately before the
     submit click in single-page flows (CAPTCHA, auth loss re-check).

The ``page`` argument is duck-typed: any object exposing ``query_selector``,
``url``, and ``content()`` works (Playwright pages and test fakes alike).

Decision log (Rule 2):
  D1 — fail-open on detector failure.
    Option: if any detector raises, ``check()`` logs a warning and
      returns None (no rescue) instead of pausing the fill.
    Trades away: a broken safety net fails silently. A genuinely broken
      detector lets automation continue past a real CAPTCHA with no
      signal beyond a log line — detector failure is silent-by-design
      (log.warning only).
    To get: a broken detector must never block a working fill. Detector
      code runs against hostile, unpredictable page DOMs, and the blast
      radius of a detector crash that hard-fails is EVERY fill on every
      board, while the blast radius of one missed CAPTCHA is one
      abandoned attempt that the existing no-pause path already
      surfaces.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger("job-apply-mcp.session_rescue")

# ---------------------------------------------------------------------------
# Detectors
# ---------------------------------------------------------------------------

#: CSS selectors that indicate a CAPTCHA widget is present. Kept as data so
#: the policy test can assert every known family is covered — and so a
#: reviewer can see exactly what "CAPTCHA detected" means.
CAPTCHA_SELECTORS: tuple[str, ...] = (
    'iframe[src*="recaptcha"]',  # Google reCAPTCHA
    'iframe[src*="recaptcha.net"]',
    ".g-recaptcha",
    "[data-sitekey]",  # reCAPTCHA / hCaptcha site key marker
    'iframe[src*="hcaptcha.com"]',  # hCaptcha
    ".h-captcha",
    'iframe[src*="challenges.cloudflare.com"]',  # Cloudflare Turnstile
    ".cf-turnstile",
    "#captcha",
    ".captcha",
    'img[src*="captcha"]',
    'input[name*="captcha"]',
)

#: Text markers (lowercased) that indicate a CAPTCHA when selectors miss.
CAPTCHA_TEXT_MARKERS: tuple[str, ...] = (
    "verify you are human",
    "i'm not a robot",
    "i am not a robot",
    "complete the security check",
    "unusual traffic",
    "automated access",
)

#: URL fragments that indicate the session was bounced to a login wall.
AUTH_LOSS_URL_MARKERS: tuple[str, ...] = (
    "/login",
    "/signin",
    "/sign-in",
    "login.",
    "authwall",
    "checkpoint",
)

#: Page-text markers (lowercased) for a lost/expired session.
AUTH_LOSS_TEXT_MARKERS: tuple[str, ...] = (
    "session expired",
    "please log in",
    "please sign in",
    "log in to continue",
    "sign in to continue",
    "your session has expired",
)


def _page_text(page: Any) -> str:
    try:
        content = page.content()
    except Exception:
        return ""
    return re.sub(r"<[^>]+>", " ", str(content)).lower()


def detect_captcha(page: Any) -> dict[str, Any] | None:
    """Return evidence dict when a CAPTCHA is present, else None."""
    for selector in CAPTCHA_SELECTORS:
        try:
            if page.query_selector(selector):
                log.warning("Session rescue: CAPTCHA selector matched: %s", selector)
                return {"reason": "captcha", "evidence": f"selector:{selector}"}
        except Exception:
            continue
    text = _page_text(page)
    for marker in CAPTCHA_TEXT_MARKERS:
        if marker in text:
            log.warning("Session rescue: CAPTCHA text marker matched: %r", marker)
            return {"reason": "captcha", "evidence": f"text:{marker}"}
    return None


def detect_auth_loss(page: Any, board: str | None = None) -> dict[str, Any] | None:
    """Return evidence dict when the session hit a login wall, else None."""
    url = ""
    try:
        url = str(page.url or "").lower()
    except Exception:
        pass
    for marker in AUTH_LOSS_URL_MARKERS:
        if marker in url:
            log.warning("Session rescue: auth-loss URL marker %r in %s", marker, url)
            return {"reason": "auth_loss", "evidence": f"url:{marker}"}
    text = _page_text(page)
    for marker in AUTH_LOSS_TEXT_MARKERS:
        if marker in text:
            log.warning("Session rescue: auth-loss text marker %r", marker)
            return {"reason": "auth_loss", "evidence": f"text:{marker}"}
    return None


def assess_field_ambiguity(fields: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return evidence dict when fields can't be mapped confidently.

    Two triggers:
    * A visible field whose name is a synthesized numeric fallback
      (``field_N`` — digits only, so real names like ``field_of_study``
      do NOT false-positive) and which has no label, placeholder,
      aria-label, or name — Veto would be guessing what it is.
    * Two or more text-like fields (text, textbox, email, password)
      sharing the same normalized label — Veto can't tell which one
      the profile value belongs in.
    """
    if not fields:
        return None
    unlabeled: list[str] = []
    seen: dict[str, list[str]] = {}
    for f in fields:
        name = str(f.get("name") or "")
        label = str(f.get("label") or "").strip()
        ftype = str(f.get("type") or "").lower()
        if re.fullmatch(r"field_\d+", name) and not label:
            unlabeled.append(f.get("selector") or name)
        if ftype in ("text", "textbox", "email", "password", "") and label:
            key = re.sub(r"\s+", " ", label).lower()
            seen.setdefault(key, []).append(name)
    dupes = {k: v for k, v in seen.items() if len(v) > 1}
    if unlabeled or dupes:
        parts = []
        if unlabeled:
            parts.append(f"{len(unlabeled)} unlabeled field(s): {unlabeled[:3]}")
        if dupes:
            parts.append(
                "duplicate labels: "
                + ", ".join(f"{k!r} x{len(v)}" for k, v in list(dupes.items())[:3])
            )
        return {"reason": "field_ambiguity", "evidence": "; ".join(parts)}
    return None


# ---------------------------------------------------------------------------
# Handoff bundle
# ---------------------------------------------------------------------------


@dataclass
class RescueHandoff:
    """What the user receives when automation pauses.

    The ``resume_token`` is a short correlation key (``uuid4``-derived),
    not a credential and not a resumption mechanism. Its intended
    consumer is the human-facing surface that displays the handoff —
    today the result dict's ``"rescue"`` bundle read by the server's
    caller and any dashboard/alert UI built on top: the token lets a
    human (or support tooling) match a screenshot file, a log line, and
    the paused-attempt record to each other when the user re-runs the
    fill. It is deliberately NOT consumed by any automated code path:
    no component resumes automation on the strength of this token, and
    any resume always goes through the normal confirm-gated path with
    the human in control. Do not invent consumers for it — if a future
    integration starts treating it as a machine-resume key, that
    integration must go through adversarial review first.
    """

    reason: str  # "captcha" | "auth_loss" | "field_ambiguity"
    detected_at: str
    page_url: str
    board: str | None
    evidence: str
    screenshot_path: str | None
    fields_summary: list[str] = field(default_factory=list)
    resume_token: str = ""
    what_user_should_do: str = ""

    def __post_init__(self) -> None:
        if not self.resume_token:
            self.resume_token = uuid.uuid4().hex[:12]
        if not self.what_user_should_do:
            self.what_user_should_do = _GUIDANCE.get(self.reason, _GUIDANCE["default"])

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_GUIDANCE = {
    "captcha": (
        "A CAPTCHA is showing. Veto will never solve it for you — open the "
        "page in your own browser (headed mode keeps it open for you), "
        "complete the challenge yourself, then re-run the fill. Your "
        "profile data and screenshot are saved under the resume token."
    ),
    "auth_loss": (
        "The site bounced to a login wall — the saved session expired or "
        "was rejected. Log in manually in a headed browser "
        "(browser_apply.login_session), then re-run the fill. Veto never "
        "types your passwords."
    ),
    "field_ambiguity": (
        "Some form fields couldn't be mapped to your profile confidently. "
        "Review the screenshot and the field list in the handoff bundle, "
        "then fill those fields by hand in a headed browser. Veto would "
        "rather stop than guess."
    ),
    "default": (
        "Automation paused and control was handed to you. Review the "
        "screenshot, finish the step in your own browser, then continue."
    ),
}


def check(
    page: Any,
    *,
    board: str | None = None,
    fields: list[dict[str, Any]] | None = None,
    screenshot_path: str | None = None,
) -> RescueHandoff | None:
    """Run the rescue detectors in priority order.

    Priority: CAPTCHA > auth loss > field ambiguity. Returns a
    ``RescueHandoff`` on the first trigger, else None. Never raises —
    detection failures degrade to "no rescue" and are logged, because a
    broken detector must not block a working fill. This is the D1
    decision recorded in the module docstring: fail-open, silent
    (log.warning only) by design.
    """
    try:
        hit = detect_captcha(page)
        if hit is None:
            hit = detect_auth_loss(page, board)
        if hit is None and fields is not None:
            hit = assess_field_ambiguity(fields)
        if hit is None:
            return None
        try:
            page_url = str(page.url or "")
        except Exception:
            page_url = ""
        return RescueHandoff(
            reason=hit["reason"],
            detected_at=datetime.now(timezone.utc).isoformat(),
            page_url=page_url,
            board=board,
            evidence=hit["evidence"],
            screenshot_path=screenshot_path,
            fields_summary=[
                f"{f.get('label') or f.get('name')} [{f.get('type')}]"
                for f in (fields or [])[:12]
            ],
        )
    except Exception as exc:  # detector failure: log, don't block
        log.warning("Session rescue check failed: %s", exc)
        return None


def refusal_note() -> str:
    """The policy, in one place, for UI copy and audits."""
    return (
        "Veto never bypasses CAPTCHAs. When one is detected, automation "
        "pauses, a screenshot is saved, and control is handed to you. "
        "This pause-and-hand-off IS the feature."
    )

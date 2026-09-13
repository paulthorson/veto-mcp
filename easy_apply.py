#!/usr/bin/env python3
"""LinkedIn Easy Apply — FILL-ONLY handler (Playwright, sync API).

MITIGATION / FILL-ONLY CONTRACT
===============================
LinkedIn is a **scraping-tier** board (see compliance.py): scraping it can
violate its Terms of Service and trigger HTTP 403/429, CAPTCHAs, IP
rate-limiting, or account restrictions on logged-in flows. This module
mitigates that risk with a strict **fill-only** guarantee:

* ``fill_easy_apply(..., confirm=False)`` (the default) performs ZERO
  browser activity and returns a preview only.
* With ``confirm=True`` it opens the job posting, clicks "Easy Apply",
  steps through the multi-step modal (bounded: at most ``MAX_MODAL_STEPS``
  steps), fills visible text inputs/selects from the profile, uploads the
  resume on file inputs, and screenshots every step.
* It then **STOPS on the review step and NEVER clicks the final Submit
  button**. The headed browser is handed to the user, who reviews the
  filled form and clicks Submit themselves (or presses Enter to close).
* The guarantee is enforced structurally in code: the only buttons this
  module ever clicks are those whose label matches ``_NEXT_LABEL_RE``
  (Next / Continue / Review your application). ``_click_labeled_button``
  raises ``AssertionError`` if a label containing "submit" is ever passed
  to it — a submit click cannot happen by selector drift. The module never
  calls ``browser_apply.find_submit_button``.

Other mitigations: no credential storage (the user logs in manually via a
saved session created by ``browser_apply.login_session("linkedin")``),
one application per call, compliance daily apply-cap gating via
``compliance.check_apply_allowed()`` / ``record_application()``, and the
ToS disclosure (``compliance.apply_disclosure("linkedin")``) in every
preview.

Profile schema: same as ``browser_apply`` (full_name/first_name/last_name,
email, phone, location, linkedin_url, website, cover_letter — all optional).
"""

from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path
from typing import Any

import browser_apply
import compliance
from providers import session_rescue

log = logging.getLogger("job-apply-mcp.easy_apply")

BASE_DIR = Path(__file__).resolve().parent
SCREENSHOTS_DIR = browser_apply.SCREENSHOTS_DIR

#: Upper bound on Easy Apply modal steps before we stop regardless.
MAX_MODAL_STEPS = 6

#: Labels we are willing to click to advance the modal. Deliberately does
#: NOT include any submit wording — see the fill-only contract above.
_NEXT_LABEL_RE = re.compile(r"^(next|continue|review your application)$", re.I)

#: Any label containing these words must NEVER be clicked by this module.
_SUBMIT_WORD_RE = re.compile(r"submit", re.I)

_BUTTON_LABELS_JS = """() => [...document.querySelectorAll('button')]
  .filter(b => { const r = b.getBoundingClientRect(); return r.width && r.height; })
  .map(b => (b.innerText || '').trim())
  .filter(t => t.length > 0);"""

_MODAL_SELECTOR = ".jobs-easy-apply-modal, div.jobs-easy-apply-content, div[role='dialog']"


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _resolve_job_url(job_id_or_url: str) -> tuple[str, str]:
    """Return ``(board, job_url)`` for a URL or an encoded job id.

    Raises:
        ValueError: If the input is neither a URL nor a decodable
            ``<board>:<token>`` job id.
    """
    raw = (job_id_or_url or "").strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        return "linkedin", raw
    board, sep, token = raw.partition(":")
    if not sep or not board or not token:
        raise ValueError(f"Malformed job_id: {job_id_or_url!r}")
    try:
        from providers._common import decode_payload
        url = decode_payload(token)
    except Exception as exc:
        raise ValueError(f"Malformed job_id: {job_id_or_url!r}") from exc
    return board.lower(), url


def _resolve_resume(resume_path: str | None) -> Path | None:
    """Pick the resume file: explicit path, else repo defaults, else None."""
    if resume_path:
        p = Path(os.path.expanduser(resume_path)).expanduser()
        return p if p.is_file() else None
    for candidate in (
        BASE_DIR / "profiles" / "resume.pdf",
        BASE_DIR / "profiles" / "resume.docx",
        BASE_DIR / "profiles" / "resume.doc",
    ):
        if candidate.is_file():
            return candidate
    return None


def _visible_button_labels(page: Any) -> list[str]:
    """Labels of visible buttons on the page (best effort)."""
    try:
        return list(page.evaluate(_BUTTON_LABELS_JS) or [])
    except Exception:
        return []


def _click_labeled_button(page: Any, label: str) -> None:
    """Click a button by exact visible label.

    Structural fill-only enforcement: raises AssertionError if ``label``
    contains submit wording. No code path in this module may click a
    submit button.
    """
    if _SUBMIT_WORD_RE.search(label):
        raise AssertionError(
            f"FILL-ONLY VIOLATION: refusing to click submit-labelled button {label!r}"
        )
    page.locator("button").filter(has_text=label).first.click(timeout=8000)


def _click_next(page: Any) -> str | None:
    """Click the modal's Next/Continue/Review button. Returns its label."""
    for label in _visible_button_labels(page):
        if _NEXT_LABEL_RE.match(label):
            _click_labeled_button(page, label)  # raises on submit wording
            return label
    return None


def _is_review_step(page: Any) -> bool:
    """True when the modal is showing the review/submit step."""
    labels = [lbl.lower() for lbl in _visible_button_labels(page)]
    return any("submit application" in lbl or lbl == "submit" for lbl in labels)


def _click_easy_apply(page: Any) -> bool:
    """Click the job page's Easy Apply button. Returns True if clicked."""
    try:
        loc = page.locator(
            "button.jobs-apply-button, button:has-text('Easy Apply')"
        )
        if loc.count() and loc.first.is_visible():
            loc.first.click(timeout=10000)
            return True
    except Exception as exc:
        log.debug("Easy Apply click failed: %s", exc)
    return False


def _already_applied(page: Any) -> bool:
    """True when the posting already shows an 'Applied' state."""
    labels = [lbl.lower() for lbl in _visible_button_labels(page)]
    return any(lbl == "applied" for lbl in labels) and not any(
        "easy apply" in lbl for lbl in labels
    )


def _modal_open(page: Any) -> bool:
    try:
        return page.locator(_MODAL_SELECTOR).count() > 0
    except Exception:
        return False


def _preview_field_names(profile: dict[str, Any], resume: Path | None) -> list[str]:
    """Field names (only) the fill would target — no values in previews."""
    names = []
    for key in (
        "email", "phone", "first_name", "last_name", "full_name",
        "location", "linkedin_url", "website", "cover_letter",
    ):
        if str(profile.get(key, "") or "").strip():
            names.append(key)
    if resume is not None:
        names.append("resume_upload")
    return names


# ---------------------------------------------------------------------------
# Preview (zero browser activity)
# ---------------------------------------------------------------------------


def preview_easy_apply(
    job_id_or_url: str, profile: dict[str, Any], resume_path: str | None
) -> dict[str, Any]:
    """Return the fill plan without touching a browser.

    Never launches Playwright. Field values are never echoed — names only.
    """
    try:
        board, url = _resolve_job_url(job_id_or_url)
    except ValueError as exc:
        return {"status": "error", "error": str(exc)}
    resume = _resolve_resume(resume_path)
    return {
        "status": "preview",
        "board": board,
        "job_url": url,
        "fill_only": True,
        "disclosure": compliance.apply_disclosure("linkedin"),
        "risk_acknowledged": compliance.is_risk_acknowledged(),
        "profile_loaded": bool(profile),
        "resume": str(resume) if resume else None,
        "resume_found": resume is not None,
        "steps": [
            "Open the LinkedIn job posting in a headed browser.",
            'Click the "Easy Apply" button.',
            f"Step through the Easy Apply modal (at most {MAX_MODAL_STEPS} steps): "
            "fill visible text fields from the profile, upload the resume on "
            "file inputs, click only Next / Continue / Review buttons.",
            "STOP at the review step. The final Submit button is NEVER clicked "
            "by this automation.",
            "Save a screenshot of every step, then hand the browser to you: "
            "review the filled form and click Submit yourself (or press Enter "
            "to close without submitting).",
        ],
        "fields_would_fill": _preview_field_names(profile, resume),
        "guarantee": (
            "Fill-only: this module cannot click Submit. The click path only "
            "accepts Next/Continue/Review labels and raises on any submit "
            "wording."
        ),
        "note": (
            "Pass confirm=True to run. The final Submit click is always yours. "
            "LinkedIn is scraping-tier: automation may trigger CAPTCHAs, "
            "throttles, or account restrictions — apply at a human pace."
        ),
    }


# ---------------------------------------------------------------------------
# Confirmed run (fill-only)
# ---------------------------------------------------------------------------


def _launch_context(p: Any, headless: bool) -> tuple[Any, Any, Any]:
    """Launch Chromium, reusing the saved LinkedIn login session if present."""
    storage_state = None
    if browser_apply.has_saved_session("linkedin"):
        storage_state = str(browser_apply.session_path("linkedin"))
        log.info("Using saved LinkedIn login session")
    browser = p.chromium.launch(
        headless=headless,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
    )
    kwargs: dict[str, Any] = {
        "viewport": {"width": 1366, "height": 900},
        "user_agent": (
            "VETO-REDACTED-UA"
            ""
            ""
        ),
    }
    if storage_state:
        kwargs["storage_state"] = storage_state
    context = browser.new_context(**kwargs)
    return browser, context, context.new_page()


def fill_easy_apply(
    job_id_or_url: str,
    profile: dict,
    resume_path: str | None,
    confirm: bool = False,
    headed: bool = True,
    keep_open: bool = True,
) -> dict:
    """Fill a LinkedIn Easy Apply form — fill-only, never submits.

    Args:
        job_id_or_url: LinkedIn job id (``linkedin:<token>``) or job URL.
        profile: Applicant details (see module docstring).
        resume_path: Resume file to upload; repo defaults tried when None.
        confirm: MUST be True to launch the browser. Default False returns
            a zero-browser-activity preview.
        headed: Run the browser headed (default True) so the user can take
            over for the final Submit click.
        keep_open: After stopping at the review step, wait for the user to
            press Enter (or Ctrl+C) before closing the browser. In
            non-interactive contexts stdin is EOF and it closes at once.

    Returns:
        Preview dict (confirm=False), or a run dict with one of the
        statuses: ``awaiting_user_submit`` (filled, handed to the user —
        recorded via ``compliance.record_application()``),
        ``already_applied``, ``no_easy_apply``, ``stuck``,
        ``step_limit_reached``, ``blocked`` or ``error``.
        The final Submit click is ALWAYS the user's.
    """
    profile = dict(profile or {})
    if not confirm:
        return preview_easy_apply(job_id_or_url, profile, resume_path)

    result: dict[str, Any] = {
        "status": "error",
        "board": "linkedin",
        "fill_only": True,
        "submitted_by_automation": False,  # invariant: always False
        "screenshots": [],
        "filled_fields": [],
        "steps_taken": 0,
        "error": None,
    }

    try:
        board, url = _resolve_job_url(job_id_or_url)
    except ValueError as exc:
        result["error"] = str(exc)
        return result
    result["job_url"] = url
    if board != "linkedin":
        result["error"] = (
            f"easy_apply only supports LinkedIn postings, got board {board!r}"
        )
        return result

    allowed, reason = compliance.is_board_allowed("linkedin")
    if not allowed:
        result["status"] = "blocked"
        result["error"] = reason
        return result
    allowed, reason = compliance.check_apply_allowed()
    if not allowed:
        result["status"] = "blocked"
        result["error"] = reason
        return result

    resume = _resolve_resume(resume_path)
    result["resume"] = str(resume) if resume else None

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        result["error"] = (
            "Playwright is not installed. Run: pip install playwright && "
            "python -m playwright install chromium"
        )
        return result

    browser = None
    try:
        with sync_playwright() as p:
            browser, _context, page = _launch_context(p, headless=not headed)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
            except Exception as exc:
                result["error"] = f"Navigation to job posting failed: {exc}"
                return result
            result["final_url"] = page.url

            browser_apply.dismiss_consent_banners(page)
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass

            # --- Session rescue (Initiative 09, epic 5): pause on CAPTCHA
            # or auth loss before touching the Easy Apply flow. CAPTCHA is
            # NEVER bypassed — the pause-and-hand-off IS the feature.
            rescue = session_rescue.check(page, board="linkedin")
            if rescue is not None:
                shot = browser_apply._take_screenshot(
                    page, f"easy-apply-rescue-{rescue.reason}"
                )
                rescue.screenshot_path = str(shot) if shot else None
                result["screenshots"].append(rescue.screenshot_path or "")
                result["status"] = "rescue_paused"
                result["rescue"] = rescue.to_dict()
                result["error"] = (
                    f"Paused: {rescue.reason} detected — control handed to "
                    f"the user. {rescue.what_user_should_do}"
                )
                return result

            if _already_applied(page):
                result["status"] = "already_applied"
                result["note"] = (
                    "This posting already shows an 'Applied' state — "
                    "nothing was filled or recorded."
                )
                return result

            if not _click_easy_apply(page):
                shot = browser_apply._take_screenshot(page, "easy-apply-no-button")
                if shot:
                    result["screenshots"].append(str(shot))
                result["status"] = "no_easy_apply"
                result["error"] = (
                    "No Easy Apply button found on this posting — it may be "
                    "an external apply, already closed, or behind a login "
                    "wall. Run browser_apply.login_session('linkedin') first "
                    "if you are not logged in."
                )
                return result

            # --- bounded modal walk -------------------------------------
            for step in range(1, MAX_MODAL_STEPS + 1):
                time.sleep(0.8)
                if not _modal_open(page):
                    break
                shot = browser_apply._take_screenshot(
                    page, f"easy-apply-step-{step}"
                )
                if shot:
                    result["screenshots"].append(str(shot))

                if _is_review_step(page):
                    # Rescue re-check at the review step: a CAPTCHA or auth
                    # wall may have appeared mid-flow. Still never bypassed.
                    rescue = session_rescue.check(page, board="linkedin")
                    if rescue is not None:
                        shot = browser_apply._take_screenshot(
                            page, f"easy-apply-rescue-{rescue.reason}"
                        )
                        rescue.screenshot_path = str(shot) if shot else None
                        result["screenshots"].append(rescue.screenshot_path or "")
                        result["status"] = "rescue_paused"
                        result["rescue"] = rescue.to_dict()
                        result["steps_taken"] = step
                        result["error"] = (
                            f"Paused: {rescue.reason} detected — control "
                            f"handed to the user. {rescue.what_user_should_do}"
                        )
                        break
                    # REVIEW STEP: stop. Never click Submit — hand over.
                    result["status"] = "awaiting_user_submit"
                    result["steps_taken"] = step
                    break

                filled = browser_apply.fill_application(
                    page, profile, str(resume) if resume else None
                )
                for name in filled:
                    if name not in result["filled_fields"]:
                        result["filled_fields"].append(name)

                label = _click_next(page)
                result["steps_taken"] = step
                if label is None:
                    result["status"] = "stuck"
                    result["error"] = (
                        "Modal did not show a Next/Continue/Review button and "
                        "is not on the review step — stopping to avoid "
                        "clicking anything unexpected. Review the screenshots."
                    )
                    break
            else:
                result["status"] = "step_limit_reached"
                result["error"] = (
                    f"Modal walk hit the {MAX_MODAL_STEPS}-step bound without "
                    "reaching the review step — stopping. Review the "
                    "screenshots; finish manually if the form looks complete."
                )

            if result["status"] in {"awaiting_user_submit", "step_limit_reached"}:
                final_shot = browser_apply._take_screenshot(page, "easy-apply-handoff")
                if final_shot:
                    result["screenshots"].append(str(final_shot))
                result["note"] = (
                    "FILL-ONLY: the form was filled but NOT submitted. Review "
                    "the screenshots, then click Submit yourself in the open "
                    "browser window (or press Enter here to close it without "
                    "submitting)."
                )
                # The user is being handed a filled form: count the application
                # against the human-paced daily cap.
                compliance.record_application()
                if keep_open and headed:
                    print(
                        "[easy_apply] Review the filled Easy Apply form in the "
                        "browser window. Click Submit yourself when ready, "
                        "then press Enter here to close the browser."
                    )
                    try:
                        input("Press Enter to close the browser... ")
                    except (EOFError, KeyboardInterrupt):
                        pass
    except AssertionError:
        # The fill-only guard fired: a submit-labelled button was about to
        # be clicked. Re-raise — this is a bug, not a runtime condition.
        raise
    except Exception as exc:  # never let the tool crash
        result["error"] = f"Easy Apply automation failed: {exc}"
    finally:
        try:
            if browser is not None:
                browser.close()
        except Exception:
            pass
    return result


# ---------------------------------------------------------------------------
# Wiring contract (server.py / cli.py import these; this module is new-only)
# ---------------------------------------------------------------------------


def register_tools(mcp: Any) -> None:
    """Register the ``easy_apply_fill`` MCP tool on ``mcp``.

    server.py imports this lazily and calls ``register_tools(mcp)``; the
    profile/resume helpers are imported from server.py lazily to avoid a
    circular import.
    """

    @mcp.tool()
    def easy_apply_fill(job_id: str, confirm: bool = False) -> dict:
        """Fill a LinkedIn Easy Apply form — FILL-ONLY, never submits.

        LinkedIn is scraping-tier (ToS risk: CAPTCHAs, throttles, account
        restrictions). This tool fills the Easy Apply modal from your saved
        profile and uploads your resume, then STOPS at the review step and
        hands the headed browser to you. The final Submit click is always
        yours — the automation structurally cannot click it.

        Args:
            job_id: LinkedIn job id from search_jobs (``linkedin:<token>``).
            confirm: MUST be True to launch the browser. Default False
                returns a zero-browser-activity preview that includes the
                ToS disclosure and the exact steps the run would take.

        Returns:
            Preview dict, or a run dict. On success the status is
            ``awaiting_user_submit`` with screenshots for your review.
            ``submitted_by_automation`` is always False.
        """
        from server import _decode_job_id, _load_saved_profile

        try:
            board, _url = _decode_job_id(job_id)
        except ValueError as exc:
            return {"status": "error", "error": str(exc)}
        if board != "linkedin":
            return {
                "status": "error",
                "error": (
                    f"easy_apply_fill only supports LinkedIn job ids, "
                    f"got board {board!r}"
                ),
            }
        profile = _load_saved_profile()
        if not profile:
            return {
                "status": "error",
                "error": (
                    "No saved profile. Run `python3 wizard.py` first, or use "
                    "apply_to_job with an explicit profile dict."
                ),
            }
        return fill_easy_apply(
            job_id, profile=profile, resume_path=None,
            confirm=confirm, headed=True, keep_open=True,
        )


def register_cli(subparsers: Any) -> dict[str, Any]:
    """Add the ``easy-apply`` command to an argparse subparsers object.

    Returns a {command: handler} mapping the caller merges into its
    own dispatch table (cli.py-style). The parser also gets ``func``
    set so a caller can dispatch ``args.func(args)``.
    """
    p = subparsers.add_parser(
        "easy-apply",
        help="Fill a LinkedIn Easy Apply form (fill-only; never submits).",
        description=(
            "Fill-only LinkedIn Easy Apply: opens the posting, fills the "
            "modal from your saved profile, uploads your resume, screenshots "
            "every step, then STOPS at the review step for you to click "
            "Submit yourself."
        ),
    )
    p.add_argument("--job-id", required=True,
                   help="LinkedIn job id from search output, or the job URL.")
    p.add_argument("--resume", default="",
                   help="Resume file to upload (default: profiles/resume.pdf).")
    p.add_argument("--confirm", action="store_true",
                   help="Launch the browser and fill. Without it, prints a "
                   "preview with zero browser activity.")
    p.add_argument("--headless", action="store_true",
                   help="Run headless (default is headed so you can click "
                   "Submit yourself).")
    p.set_defaults(func=cmd_easy_apply)
    return {"easy-apply": cmd_easy_apply}


def cmd_easy_apply(args: Any) -> int:
    """CLI handler for ``easy-apply``. Returns a process exit code."""
    import json as _json

    from profiles import load_profile

    profile = load_profile()
    if not profile:
        print("No saved profile. Run `python3 wizard.py` first.")
        return 1
    result = fill_easy_apply(
        args.job_id,
        profile=profile,
        resume_path=args.resume or None,
        confirm=args.confirm,
        headed=not args.headless,
    )
    if getattr(args, "json", False):
        print(_json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("status") not in {"error", "blocked"} else 1
    status = result.get("status")
    print(f"status: {status}")
    if result.get("disclosure"):
        print(f"disclosure: {result['disclosure']}")
    if result.get("note"):
        print(f"note: {result['note']}")
    if result.get("error"):
        print(f"error: {result['error']}")
    if result.get("filled_fields"):
        print("filled fields: " + ", ".join(result["filled_fields"]))
    for shot in result.get("screenshots", []):
        print(f"screenshot: {shot}")
    if not result.get("submitted_by_automation", True):
        print("submitted by automation: False (fill-only — Submit is yours)")
    return 0 if status not in {"error", "blocked"} else 1


if __name__ == "__main__":  # pragma: no cover - manual smoke entry
    import sys as _sys

    _sys.exit("Use `python cli.py easy-apply --job-id ...` (after wiring) "
             "or import fill_easy_apply from Python.")

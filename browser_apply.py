#!/usr/bin/env python3
"""Phase 2: browser-automation apply hook (Playwright, sync API).

This module powers the optional browser auto-fill mode of the job-apply
MCP server. It opens an application's ``apply_url`` in headless Chromium,
extracts the visible form fields, fills them from a user ``profile`` dict,
attaches the resume file, and screenshots the result.

Safety contract:
  * ``apply_via_browser`` NEVER clicks a submit/apply button unless
    ``confirm=True``. With ``confirm=False`` it fills fields, screenshots,
    and returns ``submitted=False`` as a preview.
  * No credentials are stored or used here. For boards that require login
    (LinkedIn Easy Apply, Workday, etc.), the user logs in manually in a
    headed session; this module never types passwords.
  * Automated applying may violate a job board's Terms of Service and can
    trigger anti-bot measures (CAPTCHAs, IP throttles, account limits).
    Use at a human pace and keep a person in the loop.

Profile schema (all keys optional)::

    {
        "full_name": "Ada Lovelace",   # split into first/last when asked
        "first_name": "Ada",           # explicit overrides win over split
        "last_name": "Lovelace",
        "email": "ada@example.com",
        "phone": "+1 555-0100",
        "location": "New York, NY",
        "linkedin_url": "https://www.linkedin.com/in/adalovelace",
        "website": "https://adalovelace.dev",
        "cover_letter": "Dear hiring team, ...",
    }
"""

from __future__ import annotations

import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from providers import session_rescue

log = logging.getLogger("job-apply-mcp.browser")

BASE_DIR = Path(__file__).resolve().parent
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
SESSIONS_DIR = BASE_DIR / "sessions"  # gitignored: saved login sessions

# Where a human logs in manually per board. Boards without a generic
# login page (Greenhouse/Lever/Ashby are per-company) have None.
BOARD_LOGIN_URLS: dict[str, str | None] = {
    "linkedin": "https://www.linkedin.com/login",
    "indeed": "https://secure.indeed.com/account/login",
    "glassdoor": "https://www.glassdoor.com/profile/login_input.htm",
    "ziprecruiter": "https://www.ziprecruiter.com/login",
    "greenhouse": None,
    "lever": None,
    "ashby": None,
    "adzuna": None,
}

# URL fragments that indicate the browser is still on a login page.
_LOGIN_PATH_HINTS = ("login", "signin", "sign-in", "auth", "signup")


def session_path(board: str) -> Path:
    """Filesystem path of the saved login session for ``board``."""
    safe = re.sub(r"[^a-z0-9_-]", "_", board.lower())
    return SESSIONS_DIR / f"{safe}.json"


def has_saved_session(board: str) -> bool:
    """True when a login session was previously saved for ``board``."""
    return session_path(board).is_file()

# ---------------------------------------------------------------------------
# Field detection
# ---------------------------------------------------------------------------

# (profile_key, regex patterns matched against name/id/placeholder/label)
_FIELD_PATTERNS: list[tuple[str, list[str]]] = [
    ("email", [r"\be-?mail\b"]),
    ("phone", [r"\bphone\b", r"\btel\b", r"\bmobile\b", r"\bcell\b"]),
    ("first_name", [r"first[\s_-]?name", r"\bgiven\b", r"\bfname\b"]),
    ("last_name", [r"last[\s_-]?name", r"\bsurname\b", r"\bfamily\b", r"\blname\b"]),
    ("full_name", [r"full[\s_-]?name", r"\byour name\b", r"applicant[\s_-]?name"]),
    ("location", [r"\blocation\b", r"\bcity\b", r"\baddress\b"]),
    ("linkedin_url", [r"linkedin"]),
    ("website", [r"\bwebsite\b", r"\bportfolio\b", r"(?<!linked)\burl\b"]),
    ("cover_letter", [r"cover[\s_-]?letter"]),
]

_SKIP_TYPES = {"hidden", "submit", "button", "image", "reset"}


def _field_haystack(field: dict[str, Any]) -> str:
    return " ".join(
        str(field.get(k, "") or "")
        for k in ("name", "id", "placeholder", "label", "aria")
    ).lower()


def _match_profile_key(field: dict[str, Any]) -> str | None:
    haystack = _field_haystack(field)
    for key, patterns in _FIELD_PATTERNS:
        for pat in patterns:
            if re.search(pat, haystack):
                return key
    return None


def extract_form_fields(page: Any) -> list[dict[str, Any]]:
    """Return visible form fields as {name, label, type, selector}.

    Args:
        page: A Playwright ``Page`` (or any object exposing ``evaluate``).

    Only visible, non-hidden inputs/textareas/selects are returned. Each
    entry carries a best-effort CSS selector for human review.
    """
    raw = page.evaluate(
        """() => {
      const esc = (s) => (window.CSS && CSS.escape) ? CSS.escape(s) : s;
      return [...document.querySelectorAll('input, textarea, select')].map((el, i) => {
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        let label = '';
        if (el.id) {
          const lab = document.querySelector('label[for="' + esc(el.id) + '"]');
          if (lab) label = (lab.innerText || '').trim().slice(0, 160);
        }
        if (!label) {
          const wrap = el.closest('label');
          if (wrap) label = (wrap.innerText || '').trim().slice(0, 160);
        }
        return {
          index: i,
          tag: el.tagName.toLowerCase(),
          type: (el.type || '').toLowerCase(),
          name: el.name || '',
          id: el.id || '',
          placeholder: el.placeholder || '',
          label,
          aria: el.getAttribute('aria-label') || '',
          visible: !!(rect.width && rect.height)
            && style.visibility !== 'hidden' && style.display !== 'none',
        };
      });
    }"""
    )
    fields: list[dict[str, Any]] = []
    for f in raw:
        if not f.get("visible"):
            continue
        if f.get("type") in _SKIP_TYPES:
            continue
        selector = _selector_for(f)
        fields.append(
            {
                "name": f.get("name") or f.get("id") or f.get("placeholder") or f.get("label") or f"field_{f['index']}",
                "label": f.get("label") or f.get("placeholder") or f.get("aria") or f.get("name"),
                "type": f.get("type") or f.get("tag"),
                "selector": selector,
                "_index": f["index"],
                "_tag": f.get("tag"),
                "_input_type": f.get("type"),
            }
        )
    return fields


def _selector_for(f: dict[str, Any]) -> str:
    """Best-effort CSS selector for a detected field (human review only)."""
    if f.get("id"):
        return f"#{f['id']}"
    if f.get("name"):
        return f"{f.get('tag', 'input')}[name=\"{f['name']}\"]"
    return f"{f.get('tag', 'input')}:nth-of-type({f['index'] + 1})"


# ---------------------------------------------------------------------------
# Form filling
# ---------------------------------------------------------------------------


def _split_name(profile: dict[str, Any]) -> tuple[str, str]:
    first = (profile.get("first_name") or "").strip()
    last = (profile.get("last_name") or "").strip()
    if first or last:
        return first, last
    full = (profile.get("full_name") or "").strip()
    parts = full.split()
    if len(parts) >= 2:
        return parts[0], " ".join(parts[1:])
    return full, ""


def _field_locator(page: Any, field: dict[str, Any]) -> Any:
    """Locate a field positionally (robust against tricky selectors)."""
    return page.locator("input, textarea, select").nth(field["_index"])


def fill_application(
    page: Any, profile: dict[str, Any], resume_path: str | None
) -> dict[str, str]:
    """Fill detected fields from ``profile``; upload ``resume_path``.

    Returns a dict of ``field_name -> value`` actually filled. Fields with
    no matching profile data are skipped. File inputs receive the resume
    when it exists on disk. Never touches submit buttons.
    """
    filled: dict[str, str] = {}
    first_name, last_name = _split_name(profile)
    values: dict[str, str] = {
        "email": str(profile.get("email", "") or ""),
        "phone": str(profile.get("phone", "") or ""),
        "first_name": first_name,
        "last_name": last_name,
        "full_name": str(profile.get("full_name", "") or ""),
        "location": str(profile.get("location", "") or ""),
        "linkedin_url": str(profile.get("linkedin_url", "") or ""),
        "website": str(profile.get("website", "") or ""),
        "cover_letter": str(profile.get("cover_letter", "") or ""),
    }

    resume = Path(os.path.expanduser(resume_path)).expanduser() if resume_path else None
    resume_ok = bool(resume and resume.is_file())

    for field in extract_form_fields(page):
        input_type = field["_input_type"]
        tag = field["_tag"]
        try:
            if input_type == "file":
                if resume_ok:
                    _field_locator(page, field).set_input_files(str(resume))
                    filled[field["name"]] = f"<resume: {resume.name}>"
                continue
            if tag == "select":
                key = _match_profile_key(field)
                value = values.get(key or "", "")
                if value and _select_matching_option(page, field, value):
                    filled[field["name"]] = value
                continue
            if input_type in {"checkbox", "radio"}:
                continue  # Phase 2: leave attestations/EEO to the human

            key = _match_profile_key(field)
            if not key:
                continue
            # A lone "name" field gets the full name; split fields get parts.
            value = values.get(key, "")
            if key == "full_name" and not value and (first_name or last_name):
                value = f"{first_name} {last_name}".strip()
            if not value:
                continue
            _field_locator(page, field).fill(value)
            filled[field["name"]] = value
        except Exception as exc:  # one bad field must not abort the run
            log.debug("Skipping field %r: %s", field.get("name"), exc)
    return filled


def _select_matching_option(page: Any, field: dict[str, Any], value: str) -> bool:
    """Select the dropdown option whose label contains ``value``."""
    idx = page.evaluate(
        """([fieldIndex, needle]) => {
      const el = [...document.querySelectorAll('input, textarea, select')][fieldIndex];
      if (!el || el.tagName.toLowerCase() !== 'select') return -1;
      const n = needle.toLowerCase();
      return [...el.options].findIndex(o => (o.text || '').toLowerCase().includes(n));
    }""",
        [field["_index"], value],
    )
    if idx is not None and idx >= 0:
        _field_locator(page, field).select_option(index=idx)
        return True
    return False


# ---------------------------------------------------------------------------
# Consent banners, submit detection, screenshots
# ---------------------------------------------------------------------------


def dismiss_consent_banners(page: Any) -> int:
    """Best-effort click of cookie/consent accept buttons. Returns count."""
    clicked = 0
    selectors = [
        "#onetrust-accept-btn-handler",
        "button#accept-cookies",
        "[data-testid='cookie-accept']",
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel)
            if loc.count() and loc.first.is_visible():
                loc.first.click(timeout=3000)
                clicked += 1
        except Exception:
            pass
    try:
        clicked += page.evaluate(
            """() => {
          let n = 0;
          const re = /^(accept( all)?|agree|got it|allow all|ok)$/i;
          for (const b of document.querySelectorAll('button')) {
            const t = (b.innerText || '').trim();
            if (re.test(t)) {
              const r = b.getBoundingClientRect();
              if (r.width && r.height) { b.click(); n++; }
            }
            if (n >= 3) break;
          }
          return n;
        }"""
        ) or 0
    except Exception:
        pass
    return clicked


_SUBMIT_PATTERNS = [
    "button[type='submit']",
    "input[type='submit']",
    "button:has-text('Submit application')",
    "button:has-text('Submit Application')",
    "button:has-text('Apply now')",
    "button:has-text('Apply Now')",
    "button:has-text('Apply')",
]


def find_submit_button(page: Any) -> Any | None:
    """Return a locator for the form's submit/apply button, or None."""
    for sel in _SUBMIT_PATTERNS:
        try:
            loc = page.locator(sel)
            if loc.count() and loc.first.is_visible():
                return loc.first
        except Exception:
            continue
    return None


def _take_screenshot(page: Any, suffix: str = "preview") -> Path | None:
    try:
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        path = SCREENSHOTS_DIR / f"apply-{stamp}-{uuid.uuid4().hex[:8]}-{suffix}.png"
        page.screenshot(path=str(path), full_page=False)
        return path
    except Exception as exc:
        log.warning("Screenshot failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Persistent login sessions
# ---------------------------------------------------------------------------


def _looks_logged_in(page: Any, board: str) -> bool:
    """Best-effort check that the user completed a manual login.

    True when the URL has left any login path AND the page shows either
    no password field or an account-ish indicator (avatar, profile menu,
    logout link). Never conclusive — the caller treats it as a hint.
    """
    try:
        url = (page.url or "").lower()
        if any(h in url for h in _LOGIN_PATH_HINTS):
            return False
        has_password = page.locator("input[type='password']").count() > 0
        indicators = [
            "[aria-label*='profile' i]", "[aria-label*='account' i]",
            "img[class*='avatar' i]", "[data-testid*='avatar' i]",
            "a[href*='logout' i]", "button:has-text('Sign out')",
            ".global-nav__me",  # LinkedIn
        ]
        has_indicator = any(
            page.locator(sel).count() > 0 for sel in indicators
        )
        return has_indicator or not has_password
    except Exception:
        return False


def login_session(board: str, timeout_s: int = 300) -> dict[str, Any]:
    """Interactively save a login session for ``board``.

    Launches a HEADED browser on the board's login page. The user logs in
    manually (including any MFA/CAPTCHA); this function only watches for
    the login to complete, then saves ``storage_state`` to
    ``sessions/{board}.json``. Passwords are never typed or stored by this
    tool — only the resulting session cookies/localStorage.

    Args:
        board: Board key, e.g. "linkedin" or "indeed".
        timeout_s: How long to wait for the manual login (default 5 min).

    Returns:
        {"ok", "board", "session_path", "error"}. Never raises for
        automation failures.
    """
    result: dict[str, Any] = {
        "ok": False,
        "board": board,
        "session_path": None,
        "error": None,
    }
    login_url = BOARD_LOGIN_URLS.get(board.lower())
    if not login_url:
        result["error"] = (
            f"No generic login page known for board {board!r}. "
            "Log in on the employer's own site instead."
        )
        return result
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        result["error"] = "Playwright is not installed."
        return result

    browser = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,  # the human must see and use this window
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                viewport={"width": 1366, "height": 900},
            )
            page = context.new_page()
            page.goto(login_url, wait_until="domcontentloaded", timeout=60000)
            print(
                f"[login_session] Please log in to {board} in the opened "
                f"browser window (timeout {timeout_s}s). This window will "
                "close automatically once login is detected."
            )
            deadline = time.time() + timeout_s
            while time.time() < deadline:
                time.sleep(3)
                if _looks_logged_in(page, board):
                    break
            else:
                result["error"] = (
                    "Timed out waiting for manual login. No session saved."
                )
                return result
            SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
            path = session_path(board)
            context.storage_state(path=str(path))
            try:
                os.chmod(path, 0o600)
            except Exception:
                pass
            result["ok"] = True
            result["session_path"] = str(path)
    except Exception as exc:
        result["error"] = f"Login session failed: {exc}"
    finally:
        try:
            if browser is not None:
                browser.close()
        except Exception:
            pass
    return result


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def apply_via_browser(
    apply_url: str,
    profile: dict[str, Any] | None = None,
    resume_path: str | None = None,
    headless: bool = True,
    confirm: bool = False,
    timeout_ms: int = 60000,
    board: str | None = None,
    browser_kind: str = "chromium",
) -> dict[str, Any]:
    """Fill (and optionally submit) a job application in a real browser.

    Args:
        apply_url: Direct URL of the application form.
        profile: Dict of applicant details (see module docstring).
        resume_path: Local resume file to upload (skipped if missing).
        headless: Run Chromium headless (default True).
        confirm: MUST be True to click the submit button. With False, the
            form is filled and screenshotted, but ``submitted`` stays False.
        timeout_ms: Navigation timeout.
        board: Optional board key (e.g. "linkedin"). When a saved login
            session exists for the board (see ``login_session``), it is
            loaded into the browser context so logged-in flows
            (e.g. LinkedIn Easy Apply) work.
        browser_kind: Playwright browser to launch: "chromium" (default)
            or "firefox". The chosen browser must be installed
            (``python -m playwright install chromium firefox``).

    Returns:
        Dict with keys: ok, submitted, fields_filled, fields_detected,
        screenshot, screenshot_after_submit, final_url, error.
        Never raises on page/automation failures — errors are returned in
        the dict.
    """
    profile = dict(profile or {})
    result: dict[str, Any] = {
        "ok": False,
        "submitted": False,
        "fields_filled": {},
        "fields_detected": 0,
        "screenshot": None,
        "screenshot_after_submit": None,
        "final_url": apply_url,
        "error": None,
    }
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        result["error"] = (
            "Playwright is not installed. Run: pip install playwright && "
            "python -m playwright install chromium"
        )
        return result

    # Load a previously saved login session when one exists for the board.
    storage_state = None
    if board and has_saved_session(board):
        storage_state = str(session_path(board))
        log.info("Using saved login session for board %r", board)

    browser = None
    try:
        with sync_playwright() as p:
            launcher = getattr(p, browser_kind, None) or p.chromium
            launch_args = (
                ["--no-sandbox", "--disable-blink-features=AutomationControlled"]
                if browser_kind == "chromium"
                else ["--no-sandbox"]
            )
            browser = launcher.launch(headless=headless, args=launch_args)
            context_kwargs: dict[str, Any] = {
                "viewport": {"width": 1366, "height": 900},
                "user_agent": (
                    "VETO-REDACTED-UA"
                    ""
                    ""
                ),
            }
            if storage_state:
                context_kwargs["storage_state"] = storage_state
            context = browser.new_context(**context_kwargs)
            page = context.new_page()
            try:
                page.goto(apply_url, wait_until="domcontentloaded", timeout=timeout_ms)
            except Exception as exc:
                result["error"] = f"Navigation to apply_url failed: {exc}"
                return result

            dismiss_consent_banners(page)
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass  # some pages never settle; continue anyway

            # --- Session rescue (Initiative 09, epic 5): CAPTCHA / auth loss
            # check right after page load. CAPTCHA is NEVER bypassed — the
            # pause-and-hand-off IS the feature.
            rescue = session_rescue.check(page, board=board)
            if rescue is not None:
                shot = _take_screenshot(page, f"rescue-{rescue.reason}")
                rescue.screenshot_path = str(shot) if shot else None
                result["paused"] = True
                result["rescue"] = rescue.to_dict()
                result["final_url"] = page.url
                result["error"] = (
                    f"Paused: {rescue.reason} detected — control handed to "
                    f"the user. {rescue.what_user_should_do}"
                )
                result["ok"] = False
                return result

            fields = extract_form_fields(page)
            result["fields_detected"] = len(fields)

            # --- Session rescue: field-ambiguity check before filling.
            rescue = session_rescue.check(page, board=board, fields=fields)
            if rescue is not None:
                shot = _take_screenshot(page, f"rescue-{rescue.reason}")
                rescue.screenshot_path = str(shot) if shot else None
                result["paused"] = True
                result["rescue"] = rescue.to_dict()
                result["final_url"] = page.url
                result["error"] = (
                    f"Paused: {rescue.reason} — control handed to the user. "
                    f"{rescue.what_user_should_do}"
                )
                result["ok"] = False
                return result

            result["fields_filled"] = fill_application(page, profile, resume_path)
            # Gentle human-like pause before the screenshot/submit.
            time.sleep(1.0)

            shot = _take_screenshot(page, "preview")
            result["screenshot"] = str(shot) if shot else None
            result["final_url"] = page.url

            if confirm:
                submit = find_submit_button(page)
                if submit is None:
                    result["error"] = (
                        "No submit/apply button found — nothing was submitted. "
                        "Review the screenshot; the form may be multi-step or "
                        "require manual interaction."
                    )
                else:
                    try:
                        submit.click(timeout=10000)
                        try:
                            page.wait_for_load_state("networkidle", timeout=20000)
                        except Exception:
                            pass
                        result["submitted"] = True
                        result["final_url"] = page.url
                        shot2 = _take_screenshot(page, "submitted")
                        result["screenshot_after_submit"] = (
                            str(shot2) if shot2 else None
                        )
                    except Exception as exc:
                        result["error"] = f"Submit click failed: {exc}"
            result["ok"] = result["error"] is None
    except Exception as exc:  # never let the tool crash
        result["error"] = f"Browser automation failed: {exc}"
    finally:
        try:
            if browser is not None:
                browser.close()
        except Exception:
            pass
    return result

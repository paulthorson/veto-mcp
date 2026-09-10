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

log = logging.getLogger("job-apply-mcp.browser")

BASE_DIR = Path(__file__).resolve().parent
SCREENSHOTS_DIR = BASE_DIR / "screenshots"

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
# Main entry point
# ---------------------------------------------------------------------------


def apply_via_browser(
    apply_url: str,
    profile: dict[str, Any] | None = None,
    resume_path: str | None = None,
    headless: bool = True,
    confirm: bool = False,
    timeout_ms: int = 60000,
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

    browser = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=headless,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            context = browser.new_context(
                viewport={"width": 1366, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                ),
            )
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

            fields = extract_form_fields(page)
            result["fields_detected"] = len(fields)
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

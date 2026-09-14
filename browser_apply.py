#!/usr/bin/env python3
"""Phase 2: browser-automation apply hook (Playwright, sync API).

This module powers the optional browser auto-fill mode of the job-apply
MCP server. It opens an application's ``apply_url`` in headless Chromium,
extracts the visible form fields, fills them from a user ``profile`` dict,
attaches the resume file, and screenshots the result.

Safety contract:
  * ``apply_via_browser`` NEVER submits without a genuine interactive
    user approval bound to the EXACT filled form — the same
    approval-record mechanism the email send path uses
    (``initiatives.i09.channels.registry``: ``request_send_approval``
    presents the filled form on the terminal and the user types "send";
    ``authorize_send`` verifies nonce + content-hash + TTL + single-use;
    ``consume_approval`` burns the approval immediately before the
    submit). ``confirm=True`` is DEPRECATED and authorizes nothing.
    Without an approval the run fills fields, screenshots, and returns
    ``submit_clicked=False`` as a preview.
  * The approval binds EVERY successful form control, not just the
    fields the tool filled (MAJOR 1, round 6): the tool snapshots all
    named controls — hidden inputs, checkbox/radio checked states,
    select selections, unfilled fields — plus the submitter (R7-A: the
    submit button the approval binds — its ``formaction``,
    ``formmethod``, ``formtarget``, ``formenctype``, ``value``, and
    ``type``) and the submit destination AND method (round 9: the
    bound destination includes the method). The submission NEVER
    dispatches a click: round 9 replaced the round-8 bound-node click
    with an event-free submit — the final probe re-resolves the bound
    submitter identity in the isolated world, verifies structural node
    identity (``nodePath``), re-captures the FULL control set with the
    shared row walk, requires EXACT equality with the approved
    normalized binding (rows plus submit-time
    destination/method/target/enctype), sets the form's
    ``action``/``method``/``target``/``enctype`` EXPLICITLY to the
    approved values, and submits via
    ``HTMLFormElement.prototype.submit`` — all in ONE synchronous
    isolated-world evaluation, so there is no gap between the final
    full-control diff and the request build. No click event and no
    submit event is ever dispatched, so no page-registered
    click/submit handler can run between the final verification and
    the request build: the round-8 TOCTOU (a hostile handler swapping
    ``formaction`` or flipping ``formmethod`` after the probe's check
    passed) is structurally closed — bound == submitted by
    construction. The main-world locator is discovery-only.
    The effective destination the approval binds
    is the submitter's ``formaction`` when present (it overrides the
    form's action — the submission goes there), else the submitter's
    OWN form's ``action`` (R7-D: the form containing the button, not the
    page's first form), else the empty string — a native submit to the
    current document URL. The submit-time
    re-verification compares the full set and aborts, fail closed, on
    ANY divergence (value, checked state, added / removed / renamed
    control, changed destination — including a changed ``formaction``
    / ``formmethod`` on the submitter), naming the control.
    R7-B: the baseline snapshot is captured IMMEDIATELY before the
    approval is presented (after the pre-approval sleep, screenshot,
    submit-button search, and rescue check), and the approval's
    "will transmit" text is RENDERED FROM that same snapshot — never
    from the claimed filled-values dict — so the submit-time diff
    compares against exactly what the user saw. The re-verification
    reads the DOM through a CDP isolated world — a JS realm the page's
    own scripts cannot forge (MAJOR 2, round 6) — never through the
    page's main-world ``document.querySelectorAll`` / ``el.value``,
    which hostile page JS can override to report approved values
    while the live DOM is tampered. There is deliberately NO
    main-world fallback: on a real non-Chromium page (no CDP channel)
    or when the isolated world cannot be established, the readback
    raises and the submit is refused, fail closed — see
    ``docs/i09/decisions/communication-connectors.md``.
  * Round-9 trade-off (stated honestly): because the submission
    dispatches no events, sites whose apply flow depends on JS submit
    handlers (SPA validation, analytics beacons) will not run them —
    the submission is a native form submission to the approved
    destination using the approved method, and the submitter's own
    name=value contribution is not transmitted. Handler-immunity for
    the approved destination is
    bought with SPA-handler incompatibility; the refused alternative
    is dispatching a click and re-introducing the TOCTOU. A submit
    button outside any ``<form>`` (common in SPA apply flows) is
    refused BEFORE any approval is minted — no approval is burned on
    the doomed run.
  * Screenshots of filled forms contain PII. Retention policy: at most
    ``SCREENSHOT_MAX_COUNT`` recent screenshots are kept, and any older
    than ``SCREENSHOT_MAX_AGE_DAYS`` are deleted. ``cleanup_screenshots``
    enforces this (it also runs best-effort at the start of every
    ``apply_via_browser`` run).
  * Consent banners are dismissed privacy-safely: reject/close buttons
    only — this module NEVER clicks "Accept" on the user's behalf.
    R7-C: every button-text read that authorizes a consent click (the
    enumeration AND the submit-time re-verification) runs in the CDP
    isolated world, never the page's forgeable main world — hostile
    page JS overriding ``innerText`` can otherwise forge "Reject all"
    over an "Accept all" button. Without an unforged channel no
    consent button is clicked at all.
  * ``login_session`` saves bearer-equivalent session secrets
    (``storage_state``) protected ONLY by 0o600 file permissions — not
    encrypted. Permission-hardening failures fail LOUDLY (the captured
    file is DELETED and the session is not reported as saved), and the
    limitation is disclosed, not hidden. See
    ``docs/i09/decisions/communication-connectors.md`` for the residual
    risk record (encryption at rest is a human-accepted risk).
  * Chromium is launched with ``--no-sandbox`` (m6, disclosed here, not
    hidden in the launch args): this tool commonly runs in
    containers/VMs (Docker, headless CI/dev VMs) where the kernel user
    namespaces the Chromium sandbox requires are unavailable — without
    the flag Chromium refuses to start at all. Trade-off: this weakens
    the browser's own process isolation, so a compromised renderer has
    fewer containment boundaries. Accepted because the browser only
    ever visits the user's chosen apply URL, runs with no stored
    credentials except explicitly-saved login sessions, and never
    types passwords; the sandbox would add little while breaking the
    tool in its normal environments.
  * Chromium is launched with ``--disable-blink-features=AutomationControlled``
    (s5, disclosed here, not hidden in the launch args): this disables the
    Blink "AutomationControlled" feature — the mechanism that exposes
    automation to page JavaScript (``navigator.webdriver`` and related
    signals). In other words it makes the automated browser harder for a
    site to fingerprint as a bot, which IS bot-detection evasion, stated
    plainly. Trade-off: a board that wants to block automation loses one
    of its detection signals. Accepted because the tool only fills forms
    the user asked it to fill, never submits without a genuine
    interactive approval bound to the exact filled form, and never
    bypasses CAPTCHAs or authentication (a CAPTCHA/auth wall pauses the
    run and hands control to the user — see session rescue); without the
    flag, some apply flows refuse to serve pages to automation-flagged
    browsers at all. The flag is passed to Chromium launches only
    (``apply_via_browser`` with ``browser_kind="chromium"`` and the
    headed ``login_session`` browser); Firefox launches take
    ``--no-sandbox`` only.
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

import hashlib
import json
import logging
import os
import re
import time
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from providers import session_rescue

# NIT 6 (round 6): the approval-prompt body cap is defined ONCE, in
# email_sync (the send-path module); this import alias replaces the old
# second copy that lived here. NOTE for the integration-surfaces unit:
# initiatives.i09.channels.registry._present_draft hardcodes its own
# 4000 — a third copy, out of this unit's scope; if the cap ever
# changes, all three must be aligned.
from email_sync import _APPROVAL_PROMPT_BODY_CAP
# MINOR 3 (round 6): the overlong-body preview saver (with its
# accumulation pruning) is shared with the email path instead of
# duplicated here.
from email_sync import _save_approval_preview

log = logging.getLogger("job-apply-mcp.browser")

BASE_DIR = Path(__file__).resolve().parent
SCREENSHOTS_DIR = BASE_DIR / "screenshots"  # gitignored: filled-form PII
SESSIONS_DIR = BASE_DIR / "sessions"  # gitignored: saved login sessions

#: Screenshot retention policy (m2): screenshots of filled application
#: forms contain PII (name, email, phone, address). Keep at most this
#: many recent screenshots; delete any older than this many days.
#: ``cleanup_screenshots`` enforces it (best-effort), and it runs at the
#: start of every ``apply_via_browser`` run.
SCREENSHOT_MAX_COUNT = 50
SCREENSHOT_MAX_AGE_DAYS = 30


def cleanup_screenshots(
    max_count: int = SCREENSHOT_MAX_COUNT,
    max_age_days: int = SCREENSHOT_MAX_AGE_DAYS,
) -> dict[str, Any]:
    """Enforce the screenshot retention policy.

    Deletes ``apply-*.png`` files inside ``SCREENSHOTS_DIR`` that are
    older than ``max_age_days``, then trims the remainder to the
    ``max_count`` most recent. Only files matching ``apply-*.png`` are
    ever touched — nothing else in the directory is deleted.

    Best-effort: per-file failures are collected in the returned dict,
    never raised.

    Returns:
        ``{"deleted": [names], "kept": int, "errors": [messages]}``.
    """
    deleted: list[str] = []
    errors: list[str] = []
    try:
        files = [
            p for p in SCREENSHOTS_DIR.glob("apply-*.png") if p.is_file()
        ]
    except OSError as exc:
        return {"deleted": deleted, "kept": 0,
                "errors": [f"cannot list screenshots dir: {exc}"]}
    cutoff = time.time() - max_age_days * 86400
    survivors: list[tuple[float, Path]] = []
    for path in files:
        try:
            mtime = path.stat().st_mtime
        except OSError as exc:
            errors.append(f"{path.name}: {exc}")
            continue
        if mtime < cutoff:
            try:
                path.unlink()
                deleted.append(path.name)
            except OSError as exc:
                errors.append(f"{path.name}: {exc}")
        else:
            survivors.append((mtime, path))
    survivors.sort(key=lambda item: item[0])  # oldest first
    while len(survivors) > max_count:
        _, path = survivors.pop(0)
        try:
            path.unlink()
            deleted.append(path.name)
        except OSError as exc:
            errors.append(f"{path.name}: {exc}")
    return {"deleted": deleted, "kept": len(survivors), "errors": errors}

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


class _FilledForm(dict):
    """``field_name -> value`` filled at fill time, plus M3 identity sidecars.

    A plain ``dict[str, str]`` in every other respect (JSON-serializable,
    ``.items()``, equality with plain dicts), so existing consumers
    (``easy_apply``, the result dict) and test doubles are unaffected.
    For ``<select>`` fields the dict value is the approved profile value
    used as the match needle — i.e. what the approval prompt shows; the
    TRANSMITTED bytes live in ``select_bindings``.

    Sidecars (absent/None on plain-dict test doubles, where the
    submit-time re-verification falls back to the name-keyed comparison
    and the S1/S3 hardening below is a documented residual):

    * ``indices``: ``field_name ->`` fill-time positional index in
      ``querySelectorAll('input, textarea, select')`` order — the same
      order ``_field_locator`` fills by and the snapshot readback
      re-reads by.
      S3 (round 5): readback keys are derived from page-controlled
      attributes (name/id/placeholder), so a hostile page can rename a
      filled field away from its key and rename a different field onto
      the filled key with the approved value. The submit-time
      re-verification therefore binds by index and aborts when the
      element at the fill-time index no longer carries the filled key
      (rename/replace) — the spoofed field is never consulted.
    * ``select_bindings``: ``field_name -> {"label", "value"}`` — the
      matched option's visible label and VALUE ATTRIBUTE (the actual
      transmitted bytes), captured in the same evaluate that matched
      the option. S1 (round 5): the submit-time comparison is exact
      equality on this pair — never containment of the profile value
      in the label, never sanitized display text.
    * ``field_count``: number of ``input``/``textarea``/``select``
      elements at fill time (None when unreadable, e.g. old test
      doubles). A changed count at submit time means fields were added
      or removed after the approval — abort. This also defeats the
      insert-shift decoy (a same-named decoy inserted at the fill-time
      index while the real field shifts away) and any brand-new field
      smuggled into the form after approval (the submission would transmit
      it, but the approval never bound it).
    * ``control_snapshot``: MAJOR 1 (round 6) — the normalized unforged
      full-form snapshot (``{"rows", "submit"}``; see
      ``_normalize_snapshot``). The submit-time re-verification compares
      EVERY bound control — hidden inputs (name+value), checkbox/radio
      checked states (name+value+checked), all selects (selected
      options), all inputs' values — not just the filled subset, plus
      the submit destination binding. Divergence in ANY bound control
      aborts, fail closed, naming the control. R7-A: the located submit
      button's row is rebound with its submission overrides
      (``formaction``/``formmethod``/``formtarget``/``value``), and the
      submit destination resolves as submitter formaction > the
      submitter's form's action > empty (native submit to the current
      document URL). R7-B: the fill-time
      snapshot is SUPERSEDED — ``_attempt_authorized_submit``
      re-captures the baseline immediately before presenting the
      approval, and the approval display plus the submit-time diff bind
      THAT pre-approval snapshot, not the fill-time one. None when the
      snapshot could not be captured (the submit-time check then fails
      closed — the approval claimed to bind every control, and without
      the baseline there is nothing to verify against) or on plain-dict
      test doubles, which never set it.
    * ``submitter_identity``: R7-A — the isolated-world submitter
      identity dict (``css``/``text``/``formIndex``/``indexInForm``/
      ``nodePath``/``name``/``value``/``type``) recorded immediately
      before the approval is presented. The approval-time snapshot
      and the submit-time re-read both re-match the submitter from
      this identity, and the final submit probe verifies the
      structural ``nodePath`` — never the match pattern — as part of
      the event-free submit (round 9), so the bound
      ``formaction``/``formmethod`` and the effective destination
      always describe the bound button's form. None when no
      submit button was located (destination falls back to the
      labelled first-form fallback) or on plain-dict test
      doubles.
    * ``readback_unavailable``: True when the page object had no JS
      bridge at all at fill time (``_READBACK_UNAVAILABLE`` —
      incomplete test doubles only). The submit-time check then takes
      the legacy "unavailable" path (loud warning, proceeds) instead
      of failing closed on the missing baseline — without a real
      browser there is no real TOCTOU target.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.indices: dict[str, int] = {}
        self.select_bindings: dict[str, dict[str, str]] = {}
        self.field_count: int | None = None
        self.control_snapshot: dict[str, Any] | None = None
        self.submitter_identity: dict[str, Any] | None = None
        self.readback_unavailable: bool = False


def _select_pair_json(label: str, value: str) -> str:
    """Canonical encoding of a select's bound (label, value-attribute) pair.

    S1 (round 5): the submit-time comparison is exact string equality on
    these canonical encodings — the transmitted bytes AND the visible
    label. No containment, no sanitization, no hashing anywhere in the
    comparison.
    """
    return json.dumps(
        {"label": label, "value": value}, sort_keys=True, ensure_ascii=False
    )


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

    Returns a ``_FilledForm`` (a ``dict`` of ``field_name -> value``
    actually filled, plus the fill-time element identity the M3
    submit-time re-verification binds: positional indices, select
    (label, value-attribute) bindings, the field count, and — MAJOR 1
    (round 6) — the full-control snapshot of EVERY successful form
    control). Fields with no matching profile data are skipped. File
    inputs receive the resume when it exists on disk. Never touches
    submit buttons.
    """
    filled = _FilledForm()
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

    def _record(name: str, value: str, field: dict[str, Any]) -> None:
        filled[name] = value
        # S3: the fill-time positional index is the identity the
        # submit-time re-verification binds by (readback keys are
        # page-controlled and cannot be trusted).
        filled.indices[name] = field["_index"]

    for field in extract_form_fields(page):
        input_type = field["_input_type"]
        tag = field["_tag"]
        try:
            if input_type == "file":
                if resume_ok:
                    _field_locator(page, field).set_input_files(str(resume))
                    _record(field["name"], f"<resume: {resume.name}>", field)
                continue
            if tag == "select":
                key = _match_profile_key(field)
                value = values.get(key or "", "")
                matched = (
                    _select_matching_option(page, field, value) if value else None
                )
                if matched is not None:
                    _record(field["name"], value, field)
                    # S1: bind the matched option's transmitted bytes
                    # (value attribute) and visible label — captured in
                    # the same evaluate that matched the option. Unknown
                    # on old test doubles (bare-int shape): fall back to
                    # the profile value, which is exactly what an
                    # <option> without a value attribute transmits (the
                    # value IDL defaults to the text).
                    filled.select_bindings[field["name"]] = {
                        "label": (
                            matched["label"]
                            if matched["label"] is not None
                            else value
                        ),
                        "value": (
                            matched["value"]
                            if matched["value"] is not None
                            else value
                        ),
                    }
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
            _record(field["name"], value, field)
        except Exception as exc:  # one bad field must not abort the run
            log.debug("Skipping field %r: %s", field.get("name"), exc)
    # MAJOR 1 (round 6): snapshot EVERY successful form control AFTER
    # filling — the submission transmits the post-fill DOM state, so the
    # approval must bind that. Hidden inputs, checkbox/radio checked
    # states, selects, and unfilled fields are all bound, not just the
    # filled subset (the old code never recorded them: hostile page JS
    # could rewrite a hidden input or check an opt-in box after approval
    # and the submission would transmit bytes the approval never bound).
    # Best-effort: when the snapshot cannot be captured,
    # control_snapshot stays None and the submit-time verification falls
    # back to the filled-subset check (documented residual).
    _capture_control_snapshot(page, filled)
    return filled


#: JS for _select_matching_option: find the option whose visible label
#: contains the needle and return its index, label, AND value attribute
#: in a single evaluate — so the fill-time binding captures exactly what
#: was matched, with no TOCTOU between "which option" and "what it
#: transmits".
_SELECT_MATCH_JS = """([fieldIndex, needle]) => {
  const el = [...document.querySelectorAll('input, textarea, select')][fieldIndex];
  if (!el || el.tagName.toLowerCase() !== 'select') return null;
  const n = needle.toLowerCase();
  const opts = [...el.options];
  const i = opts.findIndex(o => (o.text || '').toLowerCase().includes(n));
  if (i < 0) return null;
  const opt = opts[i];
  // The value attribute is the transmitted bytes (S1); the label is what
  // the user saw matched. Both are bound at fill time.
  return {
    index: i,
    label: (opt.text || '').trim(),
    value: opt.value == null ? '' : String(opt.value),
  };
}"""


def _select_matching_option(
    page: Any, field: dict[str, Any], value: str
) -> dict[str, Any] | None:
    """Select the dropdown option whose label contains ``value``.

    Returns ``{"index", "label", "value"}`` for the matched option, or
    None when nothing matched. ``value`` is the option's VALUE ATTRIBUTE
    — the actual transmitted bytes (S1, round 5): the fill-time binding
    captures THAT, never the profile value used as the match needle.
    ``label`` is the visible option text the user saw matched.

    Compatibility: old test doubles return a bare option index (int)
    from this evaluate; that shape is tolerated (label/value reported as
    None so the caller can fall back) — real pages always return the
    dict.

    MAJOR 2 (round 6): the match runs through the unforged readback
    channel (CDP isolated world on real pages), not the page's main
    world — a forged fill-time match would otherwise become a forged
    baseline.
    """
    matched = _evaluate_unforged(page, _SELECT_MATCH_JS, [field["_index"], value])
    if matched is _READBACK_UNAVAILABLE:
        return None
    index: int | None = None
    label: str | None = None
    opt_value: str | None = None
    if isinstance(matched, dict):
        raw_index = matched.get("index")
        index = raw_index if isinstance(raw_index, int) else None
        raw_label = matched.get("label")
        label = raw_label if isinstance(raw_label, str) else None
        raw_value = matched.get("value")
        opt_value = raw_value if isinstance(raw_value, str) else None
    elif isinstance(matched, int) and not isinstance(matched, bool):
        # Legacy test-double shape: bare option index, label/value unknown.
        index = matched
    if index is None or index < 0:
        return None
    _field_locator(page, field).select_option(index=index)
    return {"index": index, "label": label, "value": opt_value}


# ---------------------------------------------------------------------------
# Consent banners, submit detection, screenshots
# ---------------------------------------------------------------------------

#: Button text that REJECTS optional cookies/tracking (privacy-safe), or
#: merely dismisses the banner without choosing. Anything accept-like
#: ("Accept all", "Got it", "Allow all", ...) is deliberately absent:
#: this function must NEVER opt the user into tracking.
_REJECT_TEXT_RE = re.compile(
    r"^(reject( all)?|decline( all)?|deny( all)?|no thanks|"
    r"necessary only|essentials? only|essential only)$",
    re.IGNORECASE,
)
_DISMISS_TEXT_RE = re.compile(r"^(close|dismiss)$", re.IGNORECASE)

#: Selectors whose ONLY action is rejecting optional cookies/tracking.
#: (The old accept selectors were removed deliberately — see above.)
_CONSENT_REJECT_SELECTORS = [
    "#onetrust-reject-all-handler",  # OneTrust "Reject All"
    "button#reject-cookies",  # generic reject-cookie buttons
    "#reject-cookies",
]

#: JS to enumerate visible buttons (index/text/aria) for Python-side
#: classification — the accept/reject decision lives in Python so it is
#: unit-testable, not buried in page JS.
#: R7-C: runs in the CDP isolated world via ``_evaluate_unforged``,
#: NEVER the page's main world — hostile page JS overriding
#: ``innerText`` could otherwise forge "Reject all" over an "Accept
#: all" button, defeating the click-time check and steering the tool
#: into an opt-in click the logs would misreport as a privacy-safe
#: reject.
_CONSENT_BUTTONS_JS = """() => {
  // veto:consent-enumerate
  return [...document.querySelectorAll('button')].map((b, i) => {
    const r = b.getBoundingClientRect();
    return {
      index: i,
      text: (b.innerText || b.textContent || '').trim().slice(0, 80),
      aria: b.getAttribute('aria-label') || '',
      visible: !!(r.width && r.height),
    };
  });
}"""

_CONSENT_CLICK_JS = """([i, expectedText]) => {
  // veto:consent-click
  // N4 (round 4): re-verify the button's text INSIDE the click
  // evaluate — the DOM may have mutated between enumeration and this
  // click (racing page JS), shifting the positional index onto an
  // accept-like button. Only click when the text still matches the
  // reject/dismiss-classified text seen at enumeration time; anything
  // else (missing button, changed text) is left alone (fail closed)
  // and reported to the caller.
  // R7-C: runs in the CDP isolated world — the page's main world can
  // forge innerText, so a main-world re-verification would be theater.
  const b = [...document.querySelectorAll('button')][i];
  if (!b) return 'missing';
  const txt = (b.innerText || b.textContent || '').trim().slice(0, 80);
  if (txt !== expectedText) return 'text-changed';
  b.click();
  return 'clicked';
}"""

#: R7-C: the known-selector path reads the button's text AND clicks it
#: through the isolated world too. The probe returns text/aria for
#: Python-side classification; the click JS atomically re-verifies the
#: text before clicking (N4), so a forged main-world ``innerText`` can
#: neither misclassify the button nor race the click.
_CONSENT_ID_PROBE_JS = """([sel]) => {
  // veto:consent-id-probe
  const el = document.querySelector(sel);
  if (!el) return {found: false, visible: false, text: '', aria: ''};
  const r = el.getBoundingClientRect();
  return {
    found: true,
    visible: !!(r.width && r.height),
    text: ((el.innerText || el.textContent) || '').trim().slice(0, 80),
    aria: el.getAttribute('aria-label') || '',
  };
}"""

_CONSENT_ID_CLICK_JS = """([sel, expectedText]) => {
  // veto:consent-id-click
  // Atomic verify+click (N4): only clicks when the button's text
  // STILL classifies as the expected reject/dismiss text — a DOM race
  // between the probe and the click cannot shift the click onto an
  // accept-like button.
  const el = document.querySelector(sel);
  if (!el) return 'missing';
  const r = el.getBoundingClientRect();
  if (!(r.width && r.height)) return 'hidden';
  const txt = ((el.innerText || el.textContent) || '').trim().slice(0, 80);
  if (txt !== expectedText) return 'text-changed';
  el.click();
  return 'clicked';
}"""


class _ConsentReadbackDead(Exception):
    """The unforged consent-readback channel is unavailable: no consent
    button may be clicked on forgeable readback. The run continues
    without banner dismissal (fail closed on the clicks, not the run)."""


def _consent_button_kind(text: str, aria_label: str = "") -> str | None:
    """Classify a visible button for privacy-safe consent handling.

    Returns ``"reject"`` (rejects optional cookies/tracking),
    ``"dismiss"`` (closes the banner without opting in), or ``None``
    (leave it alone). Notably, anything accept-like returns ``None`` —
    this function NEVER opts the user into tracking.
    """
    t = (text or "").strip().lower()
    aria = (aria_label or "").strip().lower()
    if _REJECT_TEXT_RE.match(t):
        return "reject"
    if _DISMISS_TEXT_RE.match(t):
        return "dismiss"
    # A bare "×" is only a dismiss when its accessible name says so.
    if t in {"\u00d7", "x"} and re.search(r"close|dismiss", aria):
        return "dismiss"
    return None


def dismiss_consent_banners(page: Any) -> int:
    """Privacy-safe consent-banner dismissal. Returns buttons clicked.

    Clicks REJECT / dismiss buttons only — NEVER "Accept". Consent
    banners exist to obtain the user's agreement to tracking; a tool
    that auto-accepts on the user's behalf would opt them into tracking
    they never agreed to.

    TOCTOU defense (N4): the generic-button path enumerates buttons by
    positional index, but re-reads each button's text INSIDE the click
    evaluate — a button whose text changed between enumeration and
    click (racing DOM mutation) is left alone, fail closed. The
    known-selector path verifies and clicks atomically in a single
    evaluate for the same reason.

    Trust boundary (R7-C): EVERY text read that authorizes a click —
    the known-selector probe, the generic enumeration, and both
    click-time re-verifications — runs in the CDP isolated world via
    ``_evaluate_unforged``, never through the page's main world. Under
    the round-6 threat model hostile page JS can override ``innerText``,
    so a main-world readback could forge "Reject all" over an "Accept
    all" button: the forged read would both defeat the N4 check and
    steer the tool into an opt-in click the logs would misreport as a
    privacy-safe reject. When the isolated world cannot be established
    (non-Chromium page, broken CDP channel, or a page object with no
    JS bridge at all), NO consent button is clicked — the run continues
    without banner dismissal (fail closed on the clicks, not on the
    run). The accept/reject CLASSIFICATION itself stays in Python
    (``_consent_button_kind``) so it remains unit-testable; only the
    DOM reads are isolated.
    """

    def _unforged(js: str, arg: Any) -> Any:
        """One isolated-world consent readback.

        Returns the readback value — which may itself be None on a
        transport or JS failure, in which case the caller skips that
        button (fail closed). Raises ``_ConsentReadbackDead`` when the
        unforged CHANNEL itself is unavailable: the caller then skips
        ALL consent clicking, never degrading to the forgeable main
        world.
        """
        try:
            res = _evaluate_unforged(page, js, arg)
        except RuntimeError as exc:
            # Real page but no CDP channel (non-Chromium) or a broken
            # isolated world: button text cannot be verified unforgably.
            raise _ConsentReadbackDead(str(exc)) from exc
        if res is _READBACK_UNAVAILABLE:
            # No JS bridge on the page object at all (incomplete test
            # double only — real Playwright pages always expose it).
            raise _ConsentReadbackDead("page object has no JS bridge")
        return res

    clicked = 0
    try:
        for sel in _CONSENT_REJECT_SELECTORS:
            # m1: verify the button's TEXT before clicking an
            # ID-selected button — never trust the selector alone. A
            # hostile page could repurpose a known ID (e.g. render
            # "Accept all" behind #onetrust-reject-all-handler). R7-C:
            # the text read AND the click both run in the isolated
            # world — a forged main-world innerText can neither
            # misclassify the button nor race the click. Click only
            # when the visible text classifies as reject/dismiss via
            # _consent_button_kind; anything else — including text we
            # failed to read — is left alone (fail closed) and logged
            # loudly.
            try:
                probe = _unforged(_CONSENT_ID_PROBE_JS, sel)
                if not isinstance(probe, dict) or not probe.get("found"):
                    continue
                if not probe.get("visible"):
                    continue
                text = probe.get("text", "") or ""
                aria = probe.get("aria", "") or ""
                if _consent_button_kind(text, aria) is None:
                    log.warning(
                        "consent: NOT clicking %r: its text %r does not "
                        "classify as reject/dismiss (fail closed)",
                        sel, text,
                    )
                    continue
                # N4: verify+click atomically in one isolated evaluate
                # — a DOM race between the probe and the click cannot
                # shift the click onto an accept-like button.
                outcome = _unforged(_CONSENT_ID_CLICK_JS, [sel, text])
                if outcome != "clicked":
                    log.warning(
                        "consent: NOT clicking %r: click-time "
                        "re-verification reported %r (fail closed)",
                        sel, outcome,
                    )
                    continue
                clicked += 1
            except _ConsentReadbackDead:
                raise
            except Exception:
                continue
        buttons = _unforged(_CONSENT_BUTTONS_JS, None) or []
        for button in buttons:
            if clicked >= 3:
                break
            try:
                if not button.get("visible"):
                    continue
                button_text = button.get("text", "")
                if _consent_button_kind(
                    button_text, button.get("aria", "")
                ) is None:
                    continue
                # N4: the index was captured at enumeration time; racing
                # DOM mutation could have shifted it onto an accept-like
                # button by click time. The click JS re-reads the
                # button's text at click time — in the isolated world
                # (R7-C), so page JS cannot forge it — and only clicks
                # when it still matches the classified text; a mismatch
                # is left alone (fail closed) and logged loudly.
                outcome = _unforged(
                    _CONSENT_CLICK_JS, [button.get("index", 0), button_text]
                )
                if outcome != "clicked":
                    log.warning(
                        "consent: NOT clicking button index %r: click-time "
                        "re-verification reported %r (the DOM changed "
                        "between enumeration and click — fail closed)",
                        button.get("index", 0), outcome,
                    )
                    continue
                clicked += 1
            except _ConsentReadbackDead:
                raise
            except Exception:
                continue
    except _ConsentReadbackDead as exc:
        # The unforged channel is unavailable: clicking any consent
        # button would mean trusting the forgeable main world. Loud,
        # then continue the run WITHOUT banner dismissal.
        log.warning(
            "consent: unforged readback unavailable (%s) — skipping "
            "consent-banner dismissal entirely (fail closed)",
            exc,
        )
    return clicked


#: Submit-button search patterns as ``(css, text)`` pairs, in
#: priority order. ``text`` is matched against the button's visible
#: text with Playwright's ``:has-text()`` normalization (whitespace
#: runs collapsed, trimmed, case-insensitive substring); None means
#: CSS-only. The SAME list drives the main-world locator search
#: (``find_submit_button`` — a DISCOVERY HINT only) and the
#: isolated-world submitter locate (``_LOCATE_SUBMITTER_JS`` — the
#: binding). Round 9: the submission NEVER goes through the
#: main-world locator — it targets the isolated-world-resolved node
#: itself (``_SUBMIT_BOUND_FORM_JS``) — so a main/isolated discovery
#: divergence can no longer misdirect the submit onto a button the
#: approval never bound.
_SUBMIT_PATTERNS: list[tuple[str, str | None]] = [
    ("button[type='submit']", None),
    ("input[type='submit']", None),
    ("button", "Submit application"),
    ("button", "Apply now"),
    ("button", "Apply"),
]


def _submit_pattern_selector(pattern: tuple[str, str | None]) -> str:
    """Render a ``_SUBMIT_PATTERNS`` entry as a Playwright selector."""
    css, text = pattern
    if text is None:
        return css
    return f"{css}:has-text('{text}')"


def _find_submit_button_with_pattern(
    page: Any,
) -> tuple[Any | None, tuple[str, str | None] | None]:
    """Return ``(locator, pattern)`` for the first visible submit-button
    match, or ``(None, None)``.

    F1 (round 8): this is a DISCOVERY HINT only — "a submit button
    exists on this page." The returned locator is NEVER the submit
    mechanism anymore (round 9: the submit targets the
    isolated-world-resolved node itself via ``_submit_bound_form``),
    so a hostile page that poisons the main-world selector engine
    cannot divert the submit. The pattern is returned so the submit
    path can tell "the main world found a button but the unforged
    world sees none" apart from "no button at all" (fail closed on
    the former)."""
    for pattern in _SUBMIT_PATTERNS:
        try:
            loc = page.locator(_submit_pattern_selector(pattern))
            if loc.count() and loc.first.is_visible():
                return loc.first, pattern
        except Exception:
            continue
    return None, None


def find_submit_button(page: Any) -> Any | None:
    """Return a locator for the form's submit/apply button, or None."""
    loc, _ = _find_submit_button_with_pattern(page)
    return loc


def _locate_submitter_identity(page: Any) -> dict[str, Any] | None:
    """R7-A: locate the actual submitter in the unforged world.

    Runs ``_LOCATE_SUBMITTER_JS`` in the CDP isolated world (never the
    page's main world) and returns the submitter identity dict
    (``css``/``text``/``formIndex``/``indexInForm``/``nodePath``/
    ``name``/``value``/``type``), or None when no submit button matches
    (the form may submit by other means — the destination binding then
    falls back to the labelled first-form fallback). ``nodePath`` is
    the structural node identity (F1, round 8): the submit probe
    compares it — never the match pattern — to prove the submit
    targets the bound node.

    FAIL CLOSED: a dead unforged channel (RuntimeError — non-Chromium
    page or broken CDP) propagates; the submit path refuses rather
    than bind a submitter it cannot verify. ``_READBACK_UNAVAILABLE``
    (page object with no JS bridge — incomplete test doubles only)
    yields None, like "no button found".
    """
    res = _evaluate_unforged(page, _LOCATE_SUBMITTER_JS, _SUBMIT_PATTERNS)
    if res is _READBACK_UNAVAILABLE or not isinstance(res, dict):
        return None
    return res


def _submit_bound_form(
    page: Any,
    submitter: dict[str, Any] | None,
    approved_binding: dict[str, Any] | None,
) -> dict[str, Any] | None | object:
    """Round 9: submit the bound form WITHOUT dispatching any click.

    Runs ``_SUBMIT_BOUND_FORM_JS`` in the CDP isolated world: it
    re-resolves the baseline-bound ``submitter`` identity, verifies
    structural node identity (``nodePath``), re-captures the FULL
    control set with the shared ``veto_capture_rows`` walk, normalizes
    it with the JS ports of ``_row_binding_key``/``_row_transmitted``,
    and requires EXACT equality with the approved normalized
    ``approved_binding`` (``{"rows": ..., "submit": ...}`` exactly as
    ``_normalize_snapshot`` produced it for the pre-approval
    baseline) — PLUS the submit-time destination/method/target/enctype
    against the approved ``submit`` block — all in ONE synchronous
    isolated-world evaluation. Only on total equality does it set the
    form's ``action``/``method``/``target``/``enctype`` explicitly to
    the approved values (pristine ``Element.prototype.setAttribute`` —
    a named control can shadow the IDL setters) and submit via
    ``HTMLFormElement.prototype.submit.call(form)``. No click event
    and no submit event is ever dispatched, so no page-registered
    click/submit handler can run between the final verification and
    the request build: the round-8 TOCTOU (a hostile handler swapping
    ``formaction`` or flipping ``formmethod`` after the probe's check
    passed) is structurally closed — and because the full rows diff
    runs in the SAME evaluation, there is no gap for a handler to
    rewrite hidden controls between a Python-side diff and the
    submit either. Bound == submitted by construction: the main-world
    locator is never consulted for the submission.

    Returns the submit report dict (``submitted``/``reason``/
    ``nodePath``/``destination`` — on a ``rows-changed`` refusal also
    ``changed``/``added``/``removed`` binding-key lists), None when
    the probe could not run or the unforged channel died (fail closed
    upstream — never a main-world fallback), or
    ``_READBACK_UNAVAILABLE`` when the page object has no JS bridge at
    all (incomplete test doubles only — the caller fails closed: no
    unverified submission path exists).
    """
    expected = approved_binding if isinstance(approved_binding, dict) else {}
    try:
        return _evaluate_unforged(
            page, _SUBMIT_BOUND_FORM_JS, [submitter, expected]
        )
    except RuntimeError:
        # The unforged channel died between the M3 re-read and the
        # submit. Fail closed: never fall back to the forgeable
        # main-world for a production security decision.
        return None


def _precreate_owner_only(path: Path) -> bool:
    """Create ``path`` owner-only (0o600) BEFORE any secret bytes land.

    NIT 7 (round 6): screenshots and session files used to be written
    at umask permissions and chmodded to 0o600 afterwards — the
    PII/secret bytes briefly existed world-readable between the write
    and the chmod. Pre-creating with ``O_CREAT|O_TRUNC|O_WRONLY`` at
    0o600 (plus an explicit ``fchmod``, so a PRE-EXISTING file with a
    wider mode is tightened too) means the bytes never exist at wider
    permissions — Playwright then overwrites the existing inode,
    preserving the mode. Callers keep their post-write chmod as
    defense-in-depth. Returns False (with a loud log) when the file
    could not be secured — callers must treat that as fatal and not
    write secrets to the path.
    """
    try:
        fd = os.open(path, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
        try:
            os.fchmod(fd, 0o600)
        finally:
            os.close(fd)
        return True
    except OSError as exc:
        log.error(
            "Could not pre-create owner-only file %s: %s — refusing to "
            "write PII/secrets to an unsecurable path.",
            path, exc,
        )
        return False


def _take_screenshot(page: Any, suffix: str = "preview") -> Path | None:
    try:
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        path = SCREENSHOTS_DIR / f"apply-{stamp}-{uuid.uuid4().hex[:8]}-{suffix}.png"
        # NIT 7 (round 6): owner-only FROM CREATION — the file exists
        # at 0o600 before page.screenshot() writes a single byte.
        if not _precreate_owner_only(path):
            return None
        page.screenshot(path=str(path), full_page=False)
        # Screenshots of filled forms contain PII (name/email/phone).
        # They are not encrypted (see docs/i09/decisions/
        # communication-connectors.md D2 for why not, and the residual
        # risk routed to Paul) — but they are at least restricted to the
        # owner, and NIT 7 (round 6) the file was pre-created 0o600
        # BEFORE the screenshot bytes landed. This post-write chmod is
        # defense-in-depth (e.g. if the writer ever recreated the
        # inode). N3 (round 4): match the login_session hardening path —
        # a chmod failure is an ERROR, never a warning-only event: the
        # file is DELETED (fallback chmod 0) rather than left on disk at
        # umask permissions, and the failure is reported loudly. Returns
        # None so callers never treat the shot as usable.
        try:
            os.chmod(path, 0o600)
        except OSError as exc:
            try:
                os.unlink(path)
                removal_note = "the captured file was DELETED"
            except OSError as unlink_exc:
                try:
                    os.chmod(path, 0)
                    removal_note = (
                        f"deletion failed ({unlink_exc}); the file was "
                        "chmodded to 0 (no permissions for anyone) as a "
                        "last resort — remove it manually"
                    )
                except OSError as chmod0_exc:
                    removal_note = (
                        "CRITICAL: the file could neither be deleted "
                        f"({unlink_exc}) nor chmodded to 0 ({chmod0_exc}) "
                        "— it may still be readable; remove it manually "
                        "IMMEDIATELY"
                    )
            log.error(
                "Screenshot hardening FAILED (%s): %s. A hardening step "
                "that did not land is an error, never a warning.",
                exc, removal_note,
            )
            return None
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

    Security limitation (disclosed honestly): the saved ``storage_state``
    holds bearer-equivalent secrets (cookies / localStorage) protected
    ONLY by file permissions (0o600) — it is NOT encrypted. Anyone with
    read access to the file (or root) can impersonate these sessions.
    The file is created 0o600 BEFORE any secret bytes are written (NIT
    7, round 6 — never briefly world-readable at umask). Keep the
    ``sessions/`` directory private and delete sessions you no longer
    need. If permission hardening fails, the captured file is DELETED
    and the session is NOT reported as saved — the failure is loud,
    never silent.

    Args:
        board: Board key, e.g. "linkedin" or "indeed".
        timeout_s: How long to wait for the manual login (default 5 min).

    Returns:
        {"ok", "board", "session_path", "warning", "error"}. Never raises
        for automation failures. "warning" discloses the
        permission-only protection on success.
    """
    result: dict[str, Any] = {
        "ok": False,
        "board": board,
        "session_path": None,
        "warning": None,
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
            # NIT 7 (round 6): owner-only FROM CREATION — pre-create the
            # target at 0o600 before storage_state() writes the
            # bearer-equivalent secrets. Refuse to save at all when the
            # path cannot be secured.
            if not _precreate_owner_only(path):
                result["error"] = (
                    "Login session was captured but the session file "
                    "could not be secured owner-only before writing — "
                    "nothing was saved."
                )
                log.error("login_session: %s", result["error"])
                return result
            context.storage_state(path=str(path))
            result["session_path"] = str(path)
            try:
                os.chmod(path, 0o600)
            except OSError as exc:
                # FAIL LOUDLY and REMOVE the secret (m4): the file holds
                # bearer-equivalent secrets (cookies / localStorage). A
                # silent `except: pass` — or leaving the file on disk at
                # umask permissions with a "delete it manually" note —
                # trusts cleanup that may never happen. Delete the file;
                # if deletion itself fails, chmod 0 as a last resort so
                # nobody can read it; if THAT fails too, say so loudly.
                # The session is NOT reported as saved in any case.
                removal_note: str
                try:
                    os.unlink(path)
                    removal_note = (
                        "the captured file was DELETED so the secrets are "
                        "not left on disk"
                    )
                except OSError as unlink_exc:
                    try:
                        os.chmod(path, 0)
                        removal_note = (
                            f"deletion failed ({unlink_exc}); the file was "
                            "chmodded to 0 (no permissions for anyone) as "
                            "a last resort — remove it manually"
                        )
                    except OSError as chmod0_exc:
                        removal_note = (
                            "CRITICAL: the file could neither be deleted "
                            f"({unlink_exc}) nor chmodded to 0 "
                            f"({chmod0_exc}) — it may still be readable; "
                            "remove it manually IMMEDIATELY"
                        )
                result["error"] = (
                    "Login session was captured but permission hardening "
                    f"FAILED ({exc}): {removal_note}. Nothing was reported "
                    "as saved."
                )
                log.error("login_session: %s", result["error"])
                return result
            log.warning(
                "login_session: saved bearer-equivalent session secrets to "
                "%s. They are protected ONLY by file permissions (0o600) "
                "— not encrypted. Anyone with read access to this file "
                "(or root) can impersonate these sessions.",
                path,
            )
            result["ok"] = True
            result["warning"] = (
                "The saved storage_state holds bearer-equivalent secrets "
                "(cookies/localStorage) protected ONLY by file permissions "
                "(0o600); it is not encrypted. Keep the sessions/ "
                "directory private and delete sessions you no longer need."
            )
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
# Approval-bound submit (Rule 1)
# ---------------------------------------------------------------------------


# ANSI escape sequences (terminal-rewrite attacks): stripped BEFORE the
# generic control-character replacement in _sanitize_display_text.
_ANSI_SEQUENCE_RE = re.compile(
    r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"  # OSC ... BEL / ST
    r"|\x1b\[[0-?]*[ -/]*[@-~]"  # CSI ... final byte
    r"|\x1b[()][0-9A-B]"  # charset selection
    r"|\x1b[=>]"  # keypad application/numeric
)


def _sanitize_display_text(value: str) -> str:
    """Display-sanitize a page-controlled string for the approval prompt.

    (m3) Strips ANSI escape sequences outright, then replaces every
    remaining control character — newlines included — with a visible
    placeholder, so a hostile field name (e.g. ``"email\\x1b[2A"`` or a
    name containing a raw newline) cannot rewrite the terminal when the
    approval prompt is shown. DISPLAY ONLY: the raw bytes are preserved
    in the payload's ``fields_raw`` and are what the M3 submit-time
    re-verification compares — the raw fill-time values against the raw
    submit-time DOM read, exact match — sanitization never touches the
    bound bytes.
    """
    text = _ANSI_SEQUENCE_RE.sub("", str(value))
    out: list[str] = []
    for ch in text:
        if ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif unicodedata.category(ch).startswith("C") or ord(ch) == 0x7F:
            out.append("\ufffd")
        else:
            out.append(ch)
    return "".join(out)


def _payload_content_hash(payload: dict[str, Any]) -> str:
    """Canonical SHA-256 over the approval payload's bound triple.

    Uses the same canonicalization the registry binds its approval
    records to (to/subject/body as canonical JSON: sort_keys, compact
    separators, ASCII). Computed locally so callers do not depend on
    the registry's private helpers; ``authorize_send``'s own
    content-mismatch check remains the authoritative binding.

    NOTE (N1, round 4): the submit gate's M3 submit-time re-verification
    no longer uses this helper. Hashing the SANITIZED display body
    cannot bind the raw bytes — two raw values that sanitize
    identically (``"Ada\\x00Lovelace"`` vs ``"Ada\\u200bLovelace"``
    both display as ``"Ada�Lovelace"``) hash identically, so the old
    check passed submits on bytes the user never approved. M3 compares
    the raw fill-time and submit-time dicts directly (exact equality);
    this helper remains as a local content-check utility (test-pinned).
    """
    canonical = json.dumps(
        {
            "to": str(payload.get("to") or "").strip(),
            "subject": str(payload.get("subject") or "").strip(),
            "body": str(payload.get("body") or "").strip(),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _display_field_value(name: str, value: Any, filled: dict[str, str]) -> Any:
    """Render a bound field value for the approval prompt.

    Select fields show the matched label AND the transmitted bytes —
    ``Engineering [transmits: eng]`` — so the user approves knowing
    both what matched and what the submission will actually send (S1, round
    5). The binding itself is untouched: ``fields_raw`` keeps the raw
    values — selects as the exact (label, value-attribute) pair, plain
    fields as their raw values — and M3 compares in binding terms (see
    ``_diff_snapshots``).
    Non-select fields render as their raw value.
    """
    bindings = getattr(filled, "select_bindings", None) or {}
    binding = bindings.get(name)
    if binding is not None:
        return (
            f"{binding.get('label') or ''} "
            f"[transmits: {binding.get('value') or ''}]"
        )
    return value


def _bkey_sort_index(bkey: str) -> int:
    """Numeric position of a snapshot row for deterministic display."""
    parts = _split_bkey(bkey)
    try:
        return int(parts[0])
    except (ValueError, IndexError):
        return 0


def _render_bound_row(bkey: str, transmitted: Any) -> str | None:
    """Render one snapshot-bound row for the approval display (R7-B).

    Returns None for rows that transmit nothing (unsuccessful
    controls) — they ARE bound (their later activation is a visible
    change) but must never be displayed as if the submission would send
    them.
    """
    parts = _split_bkey(bkey)
    index = parts[0] if parts else "?"
    name = parts[3] if len(parts) > 3 else ""
    label = name or f"field_{index}"
    if isinstance(transmitted, dict) and transmitted.get("successful") is False:
        return None
    if isinstance(transmitted, dict) and transmitted.get("submitter"):
        # R7-A: the actual submit button the approval binds, with the
        # overrides that decide where/how the form submits.
        # R9-MINOR (round 10): the round-9 mechanism submits with an
        # event-free form.submit(), which builds the entry list with no
        # submitter — the button's name=value is NEVER transmitted. The
        # per-row render must say so explicitly: the destination
        # overrides (formaction/formmethod/formtarget) ARE honored and
        # are the security-relevant part of this row.
        bits = []
        if transmitted.get("name"):
            bits.append(
                f"{transmitted['name']}={transmitted.get('value', '')} "
                "(name=value NOT transmitted by the event-free submit)"
            )
        else:
            bits.append("(unnamed — transmits no name=value)")
        bits.append(f"type={transmitted.get('type', '')}")
        if transmitted.get("formaction"):
            bits.append(f"formaction={transmitted['formaction']}")
        if transmitted.get("formmethod"):
            bits.append(f"formmethod={transmitted['formmethod']}")
        if transmitted.get("formtarget"):
            bits.append(f"formtarget={transmitted['formtarget']}")
        return (
            f"{label} [submit button the approval binds — overrides "
            "honored; name=value NOT transmitted by the event-free submit]: "
            + ", ".join(bits)
        )
    if isinstance(transmitted, list):
        # select: every selected option — label AND transmitted value
        # attribute (S1).
        opts = ", ".join(
            f"{o.get('label', '')} [transmits: {o.get('value', '')}]"
            for o in transmitted
            if isinstance(o, dict)
        )
        return f"{label}: {opts or '(no option selected)'}"
    if isinstance(transmitted, dict) and "checked" in transmitted:
        if transmitted.get("checked"):
            return (
                f"{label}: checked "
                f"[transmits: {transmitted.get('value', '')}]"
            )
        return f"{label}: unchecked [transmits nothing]"
    return f"{label}: {transmitted}"


def _apply_approval_payload(
    final_url: str, filled: dict[str, str], requested_url: str | None = None
) -> dict[str, Any]:
    """The exact payload a submit approval binds to.

    Shaped as a to/subject/body triple so it rides the SAME
    approval-record mechanism as the email send path
    (``initiatives.i09.channels.registry``): the user is shown WHERE the
    PII is going and EXACTLY what filled values will be transmitted, and
    the approval's content hash binds to this payload — a substituted
    form cannot reuse the approval.

    M1: ``final_url`` is the post-navigation ``page.url`` captured
    immediately before authorization — the submission happens on THAT page.
    R7-A/R7-D: the approval's ``to`` binds the EFFECTIVE destination
    from the pre-approval snapshot — the submitter's ``formaction``
    when present (it overrides the form's action — the form submits
    there), else the submitter's OWN form's ``action`` (not the page's
    first form), else the page URL with the body saying explicitly
    "form has no action — submits to the current page URL". The
    page/navigation
    context (final and requested URLs) is kept SEPARATE in the body so
    a redirect stays visible.

    MAJOR 1 (round 6): the body states EXPLICITLY that the approval
    binds every successful form control — not just the tool-filled
    values — and that the submit-time re-verification aborts on any
    divergence.

    m3: field names/values are page-controlled, so the displayed lines
    are sanitized via ``_sanitize_display_text`` (ANSI/control chars
    neutralized for DISPLAY). The TRUE raw bytes are preserved in
    ``fields_raw`` (canonical JSON, part of the payload) for audit —
    and the M3 submit-time re-verification compares the raw submit-time
    DOM snapshot against the raw fill-time snapshot DIRECTLY
    (exact equality in binding terms; see ``_diff_snapshots``).
    Sanitization never touches that comparison: two raw values that
    sanitize identically (``"Ada\\x00Lovelace"`` vs
    ``"Ada\\u200bLovelace"``, both displayed ``"Ada�Lovelace"``)
    still mismatch and abort the submit. Select fields display as
    ``<label> [transmits: <value>]`` so the prompt shows the actual
    transmitted bytes (the option's value attribute), not just the
    matched profile value (S1). The registry's own prompt
    renderer (``_present_draft``) sanitizes again at display time; this
    is defense-in-depth owned at the construction site, so the prompt
    stays safe even if that renderer ever changes.

    R7-B: the "will transmit" display is RENDERED FROM the pre-approval
    snapshot — the exact rows the submit-time diff compares against —
    never from the claimed filled-values dict. A page that mutates the
    DOM between filling and approval shows the MUTATED state in the
    prompt (honest), and a forged filled dict cannot paint a false
    prompt over a tampered DOM. Plain-dict callers (tests, legacy)
    carry no snapshot and keep the old filled-dict rendering.
    """
    snap = getattr(filled, "control_snapshot", None) or {}
    rows = snap.get("rows") or {}
    if rows:
        # R7-B: render the "will transmit" list from the SAME snapshot
        # rows the submit-time diff binds — the user sees exactly what
        # the submission would transmit, including hidden inputs, unchecked
        # boxes, unfilled fields, and the actual submit button. Rows
        # that transmit nothing (disabled/unnamed/button-ish controls)
        # are bound but not displayed as transmitted.
        display_lines = []
        bound_non_transmitting = 0
        for bkey, transmitted in sorted(
            rows.items(), key=lambda kv: _bkey_sort_index(kv[0])
        ):
            line = _render_bound_row(bkey, transmitted)
            if line is None:
                bound_non_transmitting += 1
                continue
            display_lines.append(_sanitize_display_text(line))
        if bound_non_transmitting:
            display_lines.append(
                f"({bound_non_transmitting} form control(s) on the page "
                "transmit nothing — disabled, unnamed, or non-submitting "
                "— but are still bound: activating one after approval "
                "aborts the submit.)"
            )
        fields_raw = json.dumps(rows, sort_keys=True, ensure_ascii=False)
    else:
        # No snapshot (plain-dict callers, legacy): the pre-round-7
        # filled-dict rendering.
        display_lines = [
            f"{_sanitize_display_text(name)}: "
            f"{_sanitize_display_text(_display_field_value(name, value, filled))}"
            for name, value in sorted(filled.items())
        ]
        # m3: the TRUE raw field bytes (canonical JSON). The registry's
        # content hash binds (to, subject, body); the raw bytes travel
        # here and are bound by the M3 re-verification, which compares
        # the raw submit-time DOM snapshot against the raw pre-approval
        # snapshot (see _diff_snapshots).
        # S1 (round 5): for <select> fields the exact transmitted bytes
        # are the matched option's (label, value-attribute) pair, NOT
        # the approved profile needle — so the pair is encoded
        # explicitly here. Non-select fields serialize as their raw
        # values, unchanged.
        fields_raw = json.dumps(
            {
                name: (
                    {
                        "label": filled.select_bindings[name]["label"],
                        "value": filled.select_bindings[name]["value"],
                    }
                    if isinstance(filled, _FilledForm)
                    and name in filled.select_bindings
                    else value
                )
                for name, value in sorted(filled.items())
            },
            sort_keys=True,
            ensure_ascii=False,
        )
    # R7-A/R7-D: the EFFECTIVE submit destination bound by the
    # pre-approval snapshot — the submitter's formaction when present
    # (it overrides the form's action), else the submitter's OWN form's
    # action, else the empty string (a native submit to the current
    # document URL). Plain-dict callers (tests, legacy) never ran
    # fill_application, so no destination is bound and the page URL
    # stays the destination — the pre-round-6 behavior.
    snap = getattr(filled, "control_snapshot", None) or {}
    submit = snap.get("submit") or {}
    resolved_action = submit.get("resolved") or ""
    to = resolved_action or final_url
    # Round 9: the approval binds the method too — show it, so "send"
    # approves the HOW as well as the WHERE.
    bound_method = (submit.get("method") or "get").upper()
    header_lines = [
        f"Submitting to: {to}",
        f"Submit destination: {_describe_destination(submit)}.",
        f"Submit method: {bound_method}.",
        f"Page URL at approval time: {final_url} (the submission happens on this page).",
    ]
    if requested_url and requested_url != final_url:
        header_lines.append(
            f"(Requested URL was: {requested_url} — the page redirected "
            "before submit; this approval binds the destination above.)"
        )
    header = "\n".join(header_lines)
    # MAJOR 1: say explicitly what the approval binds — the submit-time
    # re-verification covers every successful control, not just the
    # filled values listed below. R7-A: the ACTUAL submit button the
    # approval binds is bound too — its formaction/formmethod/
    # formtarget/formenctype/value, which decide where and how the
    # form submits.
    # R7-B: the snapshot below was captured immediately before this
    # approval was presented — what you see is what the submit-time
    # check compares against.
    binding_note = (
        "This approval binds EVERY successful form control — hidden "
        "inputs, checkbox/radio checked states, all dropdown "
        "selections, and all input values (including fields the tool "
        "did not fill) — plus the actual submit button the approval "
        "binds (its formaction/formmethod/formtarget/formenctype/value) "
        "and the submit destination and method above. The list below "
        "was read from the live form immediately before this approval "
        "was shown. Immediately before submitting, the tool re-reads "
        "the live form through an isolated readback the page's scripts "
        "cannot forge and aborts the submit if ANY bound control "
        "changed. The submission is a native form submission to the "
        "approved destination using the approved method — no click is "
        "dispatched and the page's own submit/click handlers do not run."
    )
    values_heading = (
        "Will transmit (every successful form control):"
        if rows
        else "Filled values:"
    )
    return {
        "to": to,
        "subject": "Job application submission",
        "body": (
            "The browser will submit the form directly to the destination "
            "above — a native form submission using the approved method; "
            "no click is dispatched, so the page's own submit/click "
            "handlers do not run:\n\n"
            + header + "\n\n"
            + binding_note + "\n\n"
            + values_heading + "\n"
            + ("\n".join(display_lines) if display_lines else "(no fields were filled)")
        ),
        # m3: the TRUE raw field bytes (canonical JSON, part of the
        # payload) for audit — snapshot-derived when a snapshot is
        # bound, else the legacy filled-dict encoding. The M3
        # submit-time re-verification compares the raw submit-time DOM
        # snapshot against the raw pre-approval snapshot DIRECTLY
        # (exact equality in binding terms; see _diff_snapshots).
        "fields_raw": fields_raw,
    }


#: JS to re-read the CURRENT values of filled fields from the DOM.
#: MAJOR 2 (round 6): this JS MUST run in the CDP isolated world
#: (``_evaluate_unforged``), NEVER through ``page.evaluate``. The page's
#: own scripts share the DOM with the isolated world but CANNOT touch
#: its JS globals/prototypes — so a hostile page that overrides
#: ``document.querySelectorAll`` or
#: ``HTMLInputElement.prototype.value`` to report approved values while
#: the live DOM is tampered cannot forge the snapshot. There is NO
#: main-world fallback: when the isolated context cannot be
#: established, ``_evaluate_unforged`` refuses loudly (RuntimeError) and
#: the submit path aborts fail closed.
#:
#: Each row carries the positional ``index`` (the same
#: ``querySelectorAll('input, textarea, select')`` order
#: ``extract_form_fields`` and ``_field_locator`` use), the derived
#: ``key`` (name || id || placeholder || label || field_<index>), and
#: ``type``/``tag``/``name``/``disabled``/``formId``.
#:
#: Rows cover EVERY successful form control (MAJOR 1, round 6), not
#: just the filled subset: hidden inputs (name+value), checkbox/radio
#: checked states, ALL selects (every selected option), ALL inputs'
#: values — including unfilled and unmatched controls. Controls that
#: never submit — ``type=button/submit/reset/image``, disabled controls,
#: and controls outside any form with no name — carry
#: ``"successful": false``; they are still recorded so their later
#: activation (e.g. a button becoming enabled, a control gaining a
#: name) is a visible change, but the row comparison binds them by
#: identity+``successful`` so an irrelevant class toggle does not
#: abort a good submit.
#:
#: * text-like inputs / textareas / hidden: the raw current ``el.value``;
#: * selects: ALL selected options as ``[{label, value}]`` (value is
#:   the option's VALUE ATTRIBUTE — the actual transmitted bytes, S1);
#: * checkbox/radio: ``checked`` + the value attribute (the transmitted
#:   ``value`` when checked; unchecked boxes submit nothing);
#: * file inputs: ``<resume: name>`` when a file is still selected
#:   (mirrors fill time);
#: * button-ish ``<button>``: name+value+type — and R7-A binds the
#:   ACTUAL submitter (the button the approval binds): its
#:   ``formaction``/``formmethod``/``formtarget``/``value``/``type`` are
#:   captured in ``submitterInfo`` and rebound onto the snapshot row,
#:   so a formaction swap between approval and submit is a named,
#:   fail-closed abort instead of a redirect of the POST.
#: F1 (round 8): shared isolated-world JS fragments, INTERPOLATED
#: into every probe that locates, snapshots, or submits the submitter
#: (``_LOCATE_SUBMITTER_JS``, ``_SNAPSHOT_JS``,
#: ``_SUBMIT_DESTINATION_JS``, ``_SUBMIT_BOUND_FORM_JS``) — shared by
#: construction, never copy-pasted, so the text matcher and the
#: re-match rule cannot drift apart again the way the raw-``indexOf``
#: text matcher did (it disagreed with Playwright's ``:has-text()``
#: and the two worlds bound different buttons for one pattern).
_VETO_TEXT_MATCHES_JS = """
  // Playwright-convergent text matching. Playwright's :has-text()
  // normalizes whitespace (collapses runs, trims) and matches
  // case-insensitively; the old raw indexOf on innerText missed
  // "Apply\\nnow" (from <br>) while the main-world locator matched
  // it, so the two worlds bound DIFFERENT buttons for one pattern.
  function veto_text_matches(el, text) {
    if (text == null || text === '') return true;
    const veto_norm = (s) =>
      String(s).replace(/\\s+/g, ' ').trim().toLowerCase();
    const t = veto_norm((el.innerText || el.textContent) || '');
    return t.indexOf(veto_norm(text)) !== -1;
  }
"""

_VETO_NODE_PATH_JS = """
  // Structural node identity: the child-index path from
  // document.documentElement to the element. The same DOM node
  // always yields the same path; two different nodes never share
  // one. The submit probe compares this — never the match pattern —
  // to prove the submission targets the bound form.
  function veto_node_path(el) {
    const path = [];
    let node = el;
    while (node && node !== document.documentElement) {
      const parent = node.parentNode;
      if (!parent) return null;
      const idx = Array.prototype.indexOf.call(parent.children, node);
      if (idx < 0) return null;
      path.unshift(idx);
      node = parent;
    }
    return node === document.documentElement ? path : null;
  }
"""

_VETO_MATCH_SUBMITTER_JS = """
  // Re-locate the baseline-bound submitter. Shared matching rule
  // across the snapshot, destination, and submit probes: the
  // candidate must sit at the recorded form-relative index among
  // same-pattern peers in the same form AND carry the same name and
  // value. A page that inserts a decoy button, renames the
  // submitter, or swaps its value after approval fails the re-match.
  function veto_match_submitter(ref) {
    if (!ref || typeof ref.indexInForm !== 'number') return null;
    const forms = [...document.forms];
    const form = ref.formIndex >= 0 ? forms[ref.formIndex] : null;
    if (!form) return null;
    let peers;
    try {
      peers = [...form.querySelectorAll(ref.css || 'button, input')]
        .filter(el => veto_text_matches(el, ref.text));
    } catch (e) { return null; }
    const cand = peers[ref.indexInForm];
    if (!cand) return null;
    if ((cand.name || '') !== (ref.name || '')) return null;
    if ((cand.value || '') !== (ref.value || '')) return null;
    return cand;
  }
"""

#: Shared row-capture fragment: the full control-row walk used by BOTH
#: ``_SNAPSHOT_JS`` (the pre-approval baseline) and
#: ``_SUBMIT_BOUND_FORM_JS`` (the same-evaluation submit-time
#: re-verification). Interpolated AFTER the match helpers (it calls
#: ``veto_match_submitter``) and defines
#: ``veto_capture_rows(submitterRef)`` -> ``{rows, submitterInfo}``.
#: Shared by interpolation — never copy-pasted — so the baseline the
#: approval binds and the rows the submit probe re-verifies are
#: captured by the SAME code: the two can never drift. (Round 9:
#: this sharing is what lets the final submit evaluation re-capture
#: and diff the FULL control set atomically with the submit, instead
#: of trusting a Python-side diff from an earlier evaluation.)
_VETO_CAPTURE_ROWS_JS = (
    _VETO_TEXT_MATCHES_JS
    + _VETO_MATCH_SUBMITTER_JS
    + """
  // veto_capture_rows: every form control's transmitted state, in
  // document order. The SAME walk feeds the pre-approval baseline and
  // the submit-time re-verification.
  const veto_capture_rows = (submitterRef) => {
  const els = [...document.querySelectorAll('input, textarea, select, button')];
  // A page that inserts a decoy button, renames the submitter, or
  // swaps its value after approval fails the re-match — the row then
  // binds as an ordinary unsuccessful button and the destination
  // falls back, both visible to the diff — instead of silently
  // binding the wrong button's formaction.
  const submitterEl = veto_match_submitter(submitterRef);
  const submitterIndex = submitterEl ? els.indexOf(submitterEl) : -1;
  let submitterInfo = null;
  const rows = els.map((el, i) => {
    let label = '';
    if (el.id) {
      // NIT (round 9): the id is escaped for selector use — a hostile
      // id containing a quote or newline previously threw a
      // SyntaxError that failed the WHOLE snapshot (fail-closed DoS:
      // every submit refused). CSS.escape is pristine in the isolated
      // world, and the lookup is additionally guarded so a label read
      // can never fail the snapshot.
      try {
        const lab = document.querySelector(
          'label[for="' + CSS.escape(el.id) + '"]');
        if (lab) label = (lab.innerText || '').trim().slice(0, 160);
      } catch (e) { /* label stays empty */ }
    }
    const type = (el.type || '').toLowerCase();
    const tag = el.tagName.toLowerCase();
    const name = el.name == null ? '' : String(el.name);
    const disabled = !!el.disabled;
    const formId = el.form ? (el.form.id || el.form.name || 'form') : '';
    const key = name || el.id || el.placeholder || label || ('field_' + i);
    // Successful controls: what the submit actually transmits.
    // https://html.spec.whatwg.org — button/submit/reset/image never
    // transmit (except the bound submitter: its overrides are bound
    // name=value is bound via submitterInfo below and its row is
    // rebound as successful); disabled controls and nameless controls
    // never transmit.
    let successful = true;
    if (disabled) successful = false;
    if (!name) successful = false;
    if (tag === 'button' || (tag === 'input' && (
        type === 'submit' || type === 'button' || type === 'reset' || type === 'image'
      ))) successful = false;
    let value = '';
    let checked = null;
    let options = null;
    let selectLabel = '';
    if (tag === 'select') {
      // S1 (round 5): the VALUE ATTRIBUTE is the transmitted bytes —
      // report every selected option's value + label, never the label
      // alone. Page JS can keep a matching label while swapping the
      // value attribute to attacker bytes.
      options = [...el.options].filter(o => o.selected).map(o => ({
        label: (o.text || '').trim(),
        value: o.value == null ? '' : String(o.value),
      }));
      const first = options[0];
      if (first) { value = first.value; selectLabel = first.label; }
    } else if (type === 'checkbox' || type === 'radio') {
      checked = !!el.checked;
      value = el.value == null ? '' : String(el.value);
    } else if (type === 'file') {
      const base = (el.value || '').split(/[\\\\/]/).pop();
      value = base ? '<resume: ' + base + '>' : '';
    } else {
      value = el.value == null ? '' : String(el.value);
    }
    const row = {
      index: i, key, type, tag, name, disabled, formId, successful,
      value, checked, options, selectLabel,
    };
    // R7-A: bind the actual submitter. The located button's
    // formaction overrides the form's action (the submission goes
    // there); formmethod/formtarget/formenctype/value/type all feed
    // the transmitted set, so all are bound and any change aborts the
    // submit. Only ONE row carries submitterInfo — the located
    // button; every other button-ish control stays unsuccessful.
    if (i === submitterIndex) {
      const sForm = el.form || null;
      const formActionRaw = sForm ? sForm.getAttribute('action') : null;
      const formAction = formActionRaw == null ? '' : String(formActionRaw);
      const formActionResolved = formAction
        ? (() => { try { return new URL(formAction, document.baseURI).href; } catch (e) { return formAction; } })()
        : '';
      const fa = el.getAttribute('formaction');
      const faResolved = fa
        ? (() => { try { return new URL(fa, document.baseURI).href; } catch (e) { return fa; } })()
        : '';
      submitterInfo = {
        formIndex: -1,
        index: i,
        name: name,
        value: value,
        type: type,
        formaction: fa == null ? '' : String(fa),
        formactionResolved: faResolved,
        formmethod: (el.getAttribute('formmethod') || '').toLowerCase(),
        formtarget: el.getAttribute('formtarget') || '',
        // Round 9: the submitter's formenctype override is bound too —
        // the final submit verification compares it (like formmethod/
        // formtarget) and the explicit form setup honors it.
        formenctype: (el.getAttribute('formenctype') || '').toLowerCase(),
        formAction: formAction,
        formActionResolved: formActionResolved,
        hasForm: !!sForm,
        source: 'submitter',
      };
      // The bound submitter's overrides determine the destination
      // and method: treat as successful so the approval diff sees its
      // row. NOTE (round 9): the event-free submit path does NOT
      // transmit the submitter's own name=value contribution
      // (form.submit() builds the entry list with no submitter) —
      // the row is still marked successful so formaction/formmethod
      // changes abort (the destination depends on them) and the
      // display shows the submitter even without name=value.
      row.successful = true;
      row.isSubmitter = true;
      row.formaction = fa == null ? '' : String(fa);
      row.formmethod = (el.getAttribute('formmethod') || '').toLowerCase();
      row.formtarget = el.getAttribute('formtarget') || '';
      // Round 9: bound alongside formmethod/formtarget — the final
      // submit verification re-verifies it and the explicit form setup
      // honors the override.
      row.formenctype = (el.getAttribute('formenctype') || '').toLowerCase();
    }
    return row;
  });
  return { rows: rows, submitterInfo: submitterInfo };
  };
"""
)


_SNAPSHOT_JS = (
    "([submitterRef]) => {"
    "\n  // veto:snapshot"
    + _VETO_CAPTURE_ROWS_JS
    + "\n  return veto_capture_rows(submitterRef);\n}"
)


#: JS ports of ``_row_binding_key`` / ``_row_transmitted`` (MAJOR 1).
#: The submit probe must diff the submit-time rows against the approved
#: normalized binding INSIDE the same synchronous evaluation that
#: submits — so the normalization has to run in JS, identically to the
#: Python side. These are line-for-line ports:
#: * binding key: ``JSON.stringify([index, tag, type, name, formId])``
#:   — the same ``["0","input","text","email",""]`` encoding as
#:   Python's ``json.dumps(..., separators=(",", ":"))``;
#: * transmitted state: the same branch order (unsuccessful ->
#:   select -> checkbox/radio -> submitter -> value) and the same
#:   field order (the comparison is per-row ``JSON.stringify``
#:   string equality, so field order is load-bearing).
#: If the two ever disagree, the diff fails CLOSED (a row looks
#: changed and the submit aborts) — never open. ``test_submit_-
#: normalization_parity`` runs this fragment under node against the
#: Python functions on a battery of hostile rows to prove it.
_VETO_NORMALIZE_ROWS_JS = """
  // Ports of _row_binding_key / _row_transmitted — keep in sync with
  // the Python functions of the same name (see the #: comment above
  // this fragment).
  const veto_row_binding_key = (row) => JSON.stringify([
    String(row.index), String(row.tag || ''), String(row.type || ''),
    String(row.name || ''), String(row.formId || ''),
  ]);
  const veto_row_transmitted = (row) => {
    if (!row.successful)
      return { successful: false, disabled: !!row.disabled,
               name: String(row.name || '') };
    if (row.tag === 'select')
      return (row.options || []).map((o) => ({
        label: String(o.label || ''), value: String(o.value || '') }));
    const ctype = String(row.type || '');
    if (ctype === 'checkbox' || ctype === 'radio')
      return { checked: !!row.checked, value: String(row.value || '') };
    if (row.isSubmitter)
      return {
        submitter: true,
        name: String(row.name || ''),
        value: String(row.value || ''),
        type: String(row.type || ''),
        formaction: String(row.formaction || ''),
        formmethod: String(row.formmethod || ''),
        formtarget: String(row.formtarget || ''),
        formenctype: String(row.formenctype || ''),
      };
    return String(row.value || '');
  };
  // Exact-equality diff of the approved normalized rows against the
  // current rows. Returns { changed: [bkey...], added: [bkey...],
  // removed: [bkey...] } — all three empty means identical. A
  // duplicate binding key (impossible from a real DOM walk) is
  // treated as unreadable, like the Python side.
  const veto_diff_rows = (approvedRows, currentRows) => {
    const cur = {};
    for (const row of currentRows || []) {
      const k = veto_row_binding_key(row);
      if (Object.prototype.hasOwnProperty.call(cur, k))
        return { duplicate: true, changed: [], added: [], removed: [] };
      cur[k] = JSON.stringify(veto_row_transmitted(row));
    }
    const changed = [], added = [], removed = [];
    const approved = approvedRows || {};
    for (const k of Object.keys(approved)) {
      if (!Object.prototype.hasOwnProperty.call(cur, k)) {
        removed.push(k);
        continue;
      }
      if (cur[k] !== JSON.stringify(approved[k])) changed.push(k);
    }
    for (const k of Object.keys(cur)) {
      if (!Object.prototype.hasOwnProperty.call(approved, k))
        added.push(k);
    }
    return { changed: changed, added: added, removed: removed };
  };
"""


#: JS returning the submit destination for the approval binding.
#: R7-A/R7-D (round 7): the EFFECTIVE destination is the submitter's
#: ``formaction`` when present — it overrides the form's action (the
#: submission goes to the formaction URL) — else the SUBMITTER'S OWN
#: form's ``action`` (``el.form``, NOT ``document.querySelector('form')``:
#: on multi-form pages the first form may be a search/newsletter form
#: and binding it would display/approve the wrong destination), else
#: the empty string (a native submit to the current document URL).
#: ``source`` records which branch
#: produced the destination so the approval and the logs say honestly
#: where the destination came from. Round 9: the binding ALSO carries
#: the effective submission method (submitter ``formmethod`` ||
#: form ``method`` || ``get`` per the HTML spec), target, and enctype —
#: the final submit verification compares all of them and sets them
#: explicitly on the form, so the bound destination includes the
#: method. The whole capture runs in the isolated world.
_SUBMIT_DESTINATION_JS = (
    "([submitterRef]) => {"
    "\n  // veto:destination"
    + _VETO_TEXT_MATCHES_JS
    + _VETO_MATCH_SUBMITTER_JS
    + """
  // The re-match rule is shared (by interpolation) with the
  // snapshot and submit probes; the captures stay in agreement about
  // which button is bound.
  const resolve = (raw) => {
    if (raw == null || raw === '') return '';
    try { return new URL(raw, document.baseURI).href; }
    catch (e) { return raw; }
  };
  // Round 9: effective submission parameters — the submitter's
  // formmethod/formtarget/formenctype override the form's
  // method/target/enctype; the method defaults to GET per the HTML
  // spec. Both the approval binding and the final submit
  // verification use these, so the approved method is what the
  // submission uses.
  const submissionParams = (el, form) => {
    const fm = el ? (el.getAttribute('formmethod') || '').toLowerCase() : '';
    const ft = el ? (el.getAttribute('formtarget') || '') : '';
    const fe = el ? (el.getAttribute('formenctype') || '').toLowerCase() : '';
    return {
      method: fm || ((form && form.getAttribute('method')) || '').toLowerCase() || 'get',
      formtarget: ft || (form ? (form.getAttribute('target') || '') : ''),
      formenctype: fe || ((form && form.getAttribute('enctype')) || '').toLowerCase() || '',
    };
  };
  const el = veto_match_submitter(submitterRef);
  if (el) {
    const form = el.form || null;
    const params = submissionParams(el, form);
    const fa = el.getAttribute('formaction');
    if (fa) {
      return Object.assign(
        { action: fa, resolved: resolve(fa), hasForm: !!form,
          source: 'submitter-formaction' }, params);
    }
    if (form) {
      const raw = form.getAttribute('action');
      if (raw == null || raw === '')
        return Object.assign(
          { action: '', resolved: '', hasForm: true,
            source: 'submitter-form-no-action' }, params);
      return Object.assign(
        { action: raw, resolved: resolve(raw), hasForm: true,
          source: 'submitter-form-action' }, params);
    }
    return Object.assign(
      { action: '', resolved: '', hasForm: false,
        source: 'submitter-no-form' }, params);
  }
  // No submitter located (submit-by-other-means flow): legacy
  // first-form fallback, labelled as such — a degraded binding the
  // approval says honestly.
  const form = document.querySelector('form');
  if (!form) return Object.assign(
    { action: '', resolved: '', hasForm: false,
      source: 'no-submitter-no-form' },
    submissionParams(null, null));
  const raw = form.getAttribute('action');
  if (raw == null || raw === '')
    return Object.assign(
      { action: '', resolved: '', hasForm: true,
        source: 'no-submitter-first-form-no-action' },
      submissionParams(null, form));
  return Object.assign(
    { action: raw, resolved: resolve(raw), hasForm: true,
      source: 'no-submitter-first-form' },
    submissionParams(null, form));
}"""
)


#: JS locating the submit button the approval will bind, recording
#: its DOM identity for the snapshot/destination/submit captures
#: (R7-A, F1 round 8): for each (css, text) pattern in
#: ``_SUBMIT_PATTERNS`` order — mirroring ``find_submit_button`` —
#: report the first VISIBLE match's pattern, its index among
#: same-pattern peers inside its OWN form, the form's index in
#: ``document.forms``, its current name/value/type, and its
#: STRUCTURAL node identity (``nodePath`` — the child-index path
#: from ``document.documentElement``). The Python side records this
#: as the submitter identity; the snapshot/destination/submit JS
#: re-match it in the isolated world at capture time, and the submit
#: probe verifies ``nodePath`` — never the pattern tuple — to prove
#: the submission targets the bound form. Text matching replicates
#: Playwright's ``:has-text()`` normalization (whitespace collapsed,
#: trimmed, case-insensitive); a None text means CSS-only.
_LOCATE_SUBMITTER_JS = (
    "([patterns]) => {"
    "\n  // veto:locate-submitter"
    + _VETO_TEXT_MATCHES_JS
    + _VETO_NODE_PATH_JS
    + """
  const forms = [...document.forms];
  for (const pair of patterns) {
    const css = pair[0];
    const text = pair[1];
    let els;
    try { els = [...document.querySelectorAll(css)]; }
    catch (e) { continue; }
    for (const el of els) {
      if (!veto_text_matches(el, text)) continue;
      const r = el.getBoundingClientRect();
      if (!(r.width && r.height)) continue;
      const form = el.form || null;
      const formIndex = form ? forms.indexOf(form) : -1;
      let indexInForm = -1;
      if (form) {
        let peers;
        try {
          peers = [...form.querySelectorAll(css)]
            .filter(p => veto_text_matches(p, text));
        } catch (e) { peers = []; }
        indexInForm = peers.indexOf(el);
      }
      return {
        css: css,
        text: text == null ? null : String(text),
        formIndex: formIndex,
        indexInForm: indexInForm,
        // F1 (round 8): structural node identity — the submit probe
        // compares this, never the pattern tuple, to prove the
        // submission targets the bound form.
        nodePath: veto_node_path(el),
        name: el.name == null ? '' : String(el.name),
        value: el.value == null ? '' : String(el.value),
        type: (el.type || '').toLowerCase(),
      };
    }
  }
  return null;
}"""
)


#: JS submitting the BOUND FORM without dispatching any click or submit
#: event (round 9 — replaces the round-8 ``_CLICK_SUBMITTER_JS``).
#:
#: Takes ``[ref, expected]``: ``ref`` is the baseline-bound submitter
#: identity, ``expected`` is the FULL approved normalized binding —
#: ``{"rows": {binding_key: transmitted}, "submit": {resolved, method,
#: formtarget, formenctype, ...}}`` exactly as ``_normalize_snapshot``
#: produced it for the pre-approval baseline.
#:
#: Why no click (the round-9 veto-grade TOCTOU): the old probe verified
#: the destination from ``formaction``/``el.form.action``, compared it
#: to the approved value, THEN called ``el.click()``. Per the HTML
#: submission algorithm the form entry list and the submitter's
#: effective attributes are read AFTER submit-event dispatch — and DOM
#: listeners (any world; ``isTrusted=false`` does not suppress
#: invocation) fire synchronously during ``el.click()`` dispatch. A
#: hostile page could register a click/submit handler that swaps
#: ``formaction`` (or flips ``formmethod`` POST→GET, or rewrites hidden
#: inputs) AFTER the probe's check passed — the tool reported
#: ``submit_clicked=True`` with the approved destination while the
#: actual POST went elsewhere. The probe also never re-verified
#: ``formmethod`` at click time.
#:
#: This probe closes the window STRUCTURALLY, in ONE synchronous
#: isolated-world evaluation: it re-resolves the bound identity,
#: verifies structural node identity (``nodePath`` — never the match
#: pattern), re-captures the FULL control set with the shared
#: ``veto_capture_rows`` walk, normalizes it with the JS ports of
#: ``_row_binding_key``/``_row_transmitted``, and diffs it against the
#: approved binding — exact equality over every successful control,
#: PLUS the submit-time destination/method/target/enctype against the
#: approved binding. Only on total equality does it set the form's
#: ``action``/``method`` (plus ``target``/``enctype``) EXPLICITLY to
#: the approved values — so the submitter's ``formaction``/``formmethod``
#: overrides are honored deterministically even though
#: ``form.submit()`` builds the entry list with no submitter — then
#: submits via ``HTMLFormElement.prototype.submit.call(form)``. Per the
#: HTML spec the ``submit()`` method does NOT fire the submit event, so
#: no page-registered click/submit handler can run between the check
#: and the request build; the form entry list is built from the
#: current DOM, which the just-completed verification checked. No page
#: JS can interleave mid-evaluation: there is no gap between the full
#: snapshot diff and the request construction for a hostile handler
#: to exploit. The prototype call (not ``form.submit()``) is used
#: because a named control (``<input name="submit">``) can shadow the
#: method on the instance; likewise the attributes are set through
#: pristine ``Element.prototype.setAttribute`` because a named control
#: (``<input name="action">``) can shadow the ``form.action`` IDL
#: setter.
#:
#: TRADE-OFF (documented, genuine X-for-Y): sites whose apply flow
#: depends on JS submit handlers (SPA validation, analytics beacons)
#: will not run them — the submission is a native form submission
#: to the approved destination using the approved method. Likewise
#: the submitter's own name=value
#: contribution is not transmitted (no submitter in the entry list).
#: What you gain is handler-immunity for the approved destination: no
#: page script can redirect, re-method, or rewrite the submission
#: between the final verification and the request. The refused
#: alternative is dispatching a click and re-introducing the TOCTOU.
_SUBMIT_BOUND_FORM_JS = (
    "([ref, expected]) => {"
    "\n  // veto:submit-bound-form"
    + _VETO_NODE_PATH_JS
    + _VETO_CAPTURE_ROWS_JS
    + _VETO_NORMALIZE_ROWS_JS
    + """
  const fail = (reason, extra) => Object.assign(
    { submitted: false, reason: reason, nodePath: null, destination: null },
    extra || {});
  let el = null;
  try {
    el = veto_match_submitter(ref);
  } catch (e) {
    return fail('no-match');
  }
  if (!el) return fail('no-match');
  const path = veto_node_path(el);
  // Element identity, not pattern agreement: the re-resolved node
  // must BE the bound node (same structural path). A page that
  // moved, replaced, or reordered the button since the baseline
  // fails here — nothing is submitted on a different node.
  if (JSON.stringify(path) !== JSON.stringify(ref ? ref.nodePath : null))
    return fail('identity-changed', { nodePath: path });
  const form = el.form || null;
  if (!form) return fail('no-form', { nodePath: path });
  // The submit-time submission parameters of THIS node — same
  // precedence as _SUBMIT_DESTINATION_JS: the submitter's
  // formaction/formmethod/formtarget/formenctype override the form's
  // action/method/target/enctype; the method defaults to GET per the
  // HTML spec.
  const resolve = (raw) => {
    if (raw == null || raw === '') return '';
    try { return new URL(raw, document.baseURI).href; }
    catch (e) { return raw; }
  };
  const fa = el.getAttribute('formaction');
  const fm = (el.getAttribute('formmethod') || '').toLowerCase();
  const ft = el.getAttribute('formtarget') || '';
  const fe = (el.getAttribute('formenctype') || '').toLowerCase();
  const rawAction = fa || form.getAttribute('action') || '';
  const destResolved = rawAction ? resolve(rawAction) : '';
  const method =
    fm || (form.getAttribute('method') || '').toLowerCase() || 'get';
  const target = ft || form.getAttribute('target') || '';
  const enctype =
    fe || (form.getAttribute('enctype') || '').toLowerCase() || '';
  const dest = {
    action: rawAction, resolved: destResolved, method: method,
    formtarget: target, formenctype: enctype, hasForm: true,
    source: fa ? 'submitter-formaction' : 'submitter-form-action',
  };
  const want = ((expected || {}).submit) || {};
  const wantMethod = (want.method || 'get').toLowerCase();
  if (destResolved !== (want.resolved || ''))
    return fail('destination-changed',
                { nodePath: path, destination: dest });
  if (method !== wantMethod)
    return fail('method-changed',
                { nodePath: path, destination: dest });
  if (target !== (want.formtarget || ''))
    return fail('target-changed',
                { nodePath: path, destination: dest });
  if (enctype !== (want.formenctype || ''))
    return fail('enctype-changed',
                { nodePath: path, destination: dest });
  // ATOMIC FULL-CONTROL DIFF (round 9): re-capture the full control
  // set with the SAME walk that produced the pre-approval baseline,
  // normalize it with the JS ports of _row_binding_key /
  // _row_transmitted, and require EXACT equality with the approved
  // binding — in this same synchronous evaluation, BEFORE the submit
  // below. No page JS can interleave between this diff and the
  // request construction: a hostile handler cannot rewrite a hidden
  // input, check an opt-in box, or swap the submitter's overrides in
  // a gap that no longer exists.
  const captured = veto_capture_rows(ref);
  const rowsDiff = veto_diff_rows(
    (expected || {}).rows, captured.rows);
  if (rowsDiff.duplicate ||
      rowsDiff.changed.length || rowsDiff.added.length ||
      rowsDiff.removed.length)
    return fail('rows-changed',
                { nodePath: path, destination: dest,
                  changed: rowsDiff.changed, added: rowsDiff.added,
                  removed: rowsDiff.removed });
  // Set the form's submission parameters EXPLICITLY to the approved
  // values. HTMLFormElement.submit() builds the entry list with NO
  // submitter, so the submitter's formaction/formmethod overrides
  // would otherwise be silently dropped — the POST would go to the
  // form's own action instead of the approved destination. Setting
  // them explicitly makes the approved values determinative.
  // Pristine setAttribute (not form.action = ...): a named control
  // (<input name="action">) shadows the IDL attribute on the
  // instance, which would silently swallow the assignment.
  try {
    Element.prototype.setAttribute.call(form, 'action', destResolved);
    Element.prototype.setAttribute.call(form, 'method', method);
    Element.prototype.setAttribute.call(form, 'target', target);
    if (enctype)
      Element.prototype.setAttribute.call(form, 'enctype', enctype);
  } catch (e) {
    return fail('set-attributes-threw',
                { nodePath: path, destination: dest });
  }
  // Submit WITHOUT dispatching any event. Per the HTML spec,
  // form.submit() does NOT fire the submit event, so no
  // page-registered click/submit handler can run between the
  // verification above and the request build — the TOCTOU window the
  // old click-based path left open is structurally closed. Prototype
  // call: a named control (<input name="submit">) shadows form.submit
  // on the instance.
  try {
    HTMLFormElement.prototype.submit.call(form);
  } catch (e) {
    return fail('submit-threw', { nodePath: path, destination: dest });
  }
  return { submitted: true, reason: '', nodePath: path,
           destination: dest };
}"""
)


# ---------------------------------------------------------------------------
# Unforged readback + full-control binding (MAJOR 1 / MAJOR 2, round 6)
# ---------------------------------------------------------------------------

#: Sentinel: the page object has no JS bridge at all. Returned by
#: ``_evaluate_unforged`` when ``page.evaluate`` is missing — which only
#: happens with incomplete test doubles. Real Playwright pages always
#: expose ``evaluate``, and page JS (the M3 threat actor) cannot remove
#: the Python-side method, so "unavailable" never means "the page hid
#: from us" — it means there is no real browser behind this object.
_READBACK_UNAVAILABLE = object()

#: Attribute used to cache the per-page CDP isolated-world context id.
_ISOLATED_WORLD_ATTR = "_veto_isolated_world_id"


def _cdp_isolated_world_id(page: Any) -> int | None:
    """Create (once per page) and return a CDP isolated-world context id.

    MAJOR 2 (round 6): the isolated world shares the page's DOM but runs
    with PRISTINE JS globals and prototypes — the page's own scripts
    cannot override ``document.querySelectorAll`` or
    ``HTMLInputElement.prototype.value`` inside it, so snapshot JS run
    there reports the true DOM even against hostile page JS.

    Returns the world id. Returns None only when the page exposes no
    CDP session factory at all — callers MUST treat None as fatal for
    production security decisions (see ``_evaluate_unforged``): there
    is deliberately NO main-world fallback, because trusting the
    page's own JS realm would let hostile page scripts forge the
    readback. (``_evaluate_unforged`` refuses with RuntimeError when
    the isolated context cannot be established.)
    """
    cached = getattr(page, _ISOLATED_WORLD_ATTR, None)
    if isinstance(cached, int) and not isinstance(cached, bool):
        return cached
    new_cdp_session = getattr(
        getattr(page, "context", None), "new_cdp_session", None
    )
    if not callable(new_cdp_session):
        return None
    try:
        session = new_cdp_session(page)
        try:
            tree = session.send("Page.getFrameTree")
            frame_id = tree["frameTree"]["frame"]["id"]
            world = session.send(
                "Page.createIsolatedWorld",
                {"frameId": frame_id, "worldName": "veto-readback"},
            )
            world_id = int(world["executionContextId"])
        finally:
            try:
                session.detach()
            except Exception:
                pass
    except Exception as exc:
        log.warning(
            "Unforged readback: could not create CDP isolated world: %s", exc
        )
        return None
    try:
        setattr(page, _ISOLATED_WORLD_ATTR, world_id)
    except Exception:
        pass
    return world_id


def _evaluate_unforged(page: Any, js: str, arg: Any = None) -> Any:
    """Evaluate ``js`` where the page's scripts cannot forge the result.

    MAJOR 2 (round 6): on real Chromium pages this runs ``js`` via
    ``Runtime.callFunctionOn`` inside the CDP isolated world (see
    ``_cdp_isolated_world_id``) — a JS realm the page's own scripts
    cannot touch — never through the page's main-world
    ``page.evaluate``. That closes the round-6 threat: hostile page JS
    overriding ``document.querySelectorAll`` /
    ``HTMLInputElement.prototype.value`` to report approved values
    while the live DOM is tampered.

    FAIL CLOSED — ``page.evaluate`` is NEVER consulted for a production
    security decision, so there is deliberately NO main-world fallback.
    The three page kinds are distinguished explicitly:

    - No ``page.context`` at all: an INCOMPLETE TEST DOUBLE. Real
      Playwright pages ALWAYS expose ``.context`` (a BrowserContext),
      and page JS cannot remove the Python-side attribute — so a page
      without one is not driving a real browser and has no real TOCTOU
      target. Returns ``_READBACK_UNAVAILABLE`` with a loud warning
      (never silent); callers take their legacy "unavailable" path.
    - ``page.context`` present but no ``context.new_cdp_session``: a
      REAL non-Chromium page (CDP is Chromium-only). Raises
      RuntimeError — refusing to submit rather than trust the page's
      own JS realm, which hostile page scripts can forge.
    - ``context.new_cdp_session`` present: the isolated world is
      established; if THAT fails, raises RuntimeError (same refusal).

    The RuntimeError propagates to ``apply_via_browser``, which catches
    it, records ``result["error"]``, and never submits. A mid-flight
    CDP transport failure on an already-established world returns None
    (fail closed upstream) — that is a transport error, not a trust
    decision.
    """
    context = getattr(page, "context", None)
    cdp_factory = getattr(context, "new_cdp_session", None)
    if cdp_factory is None:
        if context is None:
            # Incomplete test double: no browser context, so no real
            # browser and no real TOCTOU target. Warn loudly (never
            # silent) and signal unavailability — failing closed here
            # would only break test doubles.
            log.warning(
                "M3 re-verification unavailable: page object has no "
                "browser context and no CDP channel — proceeding WITHOUT "
                "submit-time re-verification. Expected only for incomplete "
                "test doubles; real Playwright pages always expose "
                ".context."
            )
            return _READBACK_UNAVAILABLE
        # Real page (a browser context exists) but no CDP session
        # channel: a non-Chromium browser — CDP is Chromium-only. Fail
        # closed: the page's own JS realm is untrusted (hostile page
        # scripts can forge querySelectorAll / el.value), so there is
        # no main-world fallback to degrade to.
        raise RuntimeError(
            "cannot establish an isolated (unforged) readback context: "
            "this page exposes no CDP session channel (non-Chromium "
            "browsers cannot provide one). Refusing to submit rather "
            "than trust the page's own JS realm, which hostile page "
            "scripts can forge."
        )
    try:
        world_id = _cdp_isolated_world_id(page)
    except Exception as exc:
        raise RuntimeError(
            "could not establish an isolated (unforged) readback "
            f"context: {exc}. Refusing to submit rather than trust the "
            "page's own JS realm."
        ) from exc
    if world_id is None:
        raise RuntimeError(
            "could not establish an isolated (unforged) readback "
            "context (the CDP session factory is present but the "
            "isolated world could not be created). Refusing to submit "
            "rather than trust the page's own JS realm."
        )
    try:
        session = cdp_factory(page)
        try:
            res = session.send(
                "Runtime.callFunctionOn",
                {
                    "contextId": world_id,
                    "functionDeclaration": js,
                    "arguments": [] if arg is None else [{"value": arg}],
                    "returnByValue": True,
                    "awaitPromise": True,
                },
            )
        finally:
            try:
                session.detach()
            except Exception:
                pass
    except Exception as exc:
        log.warning(
            "Unforged readback: isolated-world evaluate failed: %s", exc
        )
        return None
    if res.get("exceptionDetails"):
        log.warning(
            "Unforged readback: isolated-world JS threw: %s",
            res["exceptionDetails"],
        )
        return None
    return res.get("result", {}).get("value")


def _row_binding_key(row: dict[str, Any]) -> str:
    """Identity a snapshot row is compared under (MAJOR 1).

    Positional index first — an inserted decoy shifts every later
    control's index, so insert-shift can never alias onto a bound
    control — then tag/type/name/formId. The page-controlled ``name``
    is deliberately NOT trusted alone: a renamed control must not
    alias onto another control's binding.

    R7-E: the key is the JSON encoding of the component list, NOT a
    separator-joined string. The old ``\\x1f``-joined form had a
    collision: a control whose name/tag contained the separator (or a
    crafted name like ``"email\\x1finput"``) could alias onto a
    different control's binding — two distinct DOM controls mapping to
    one key would silently merge (or a tampered name could collide
    with a bound row and mask a change). JSON arrays are
    self-delimiting: distinct component tuples ALWAYS encode to
    distinct keys. Use ``_split_bkey`` to decode — never
    ``str.split``.
    """
    return json.dumps(
        [
            str(row.get("index")),
            str(row.get("tag") or ""),
            str(row.get("type") or ""),
            str(row.get("name") or ""),
            str(row.get("formId") or ""),
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _split_bkey(bkey: str) -> list[str]:
    """Decode a ``_row_binding_key`` into its components (R7-E).

    Never ``bkey.split(...)`` — the key is a JSON array encoding, and
    splitting on any separator reintroduces the collision the JSON
    form removed. Returns ``[]`` on malformed input (defensive: keys
    only ever come from ``_row_binding_key``).
    """
    try:
        parts = json.loads(bkey)
    except (ValueError, TypeError):
        return []
    if not isinstance(parts, list):
        return []
    return [str(p) for p in parts]


def _row_transmitted(row: dict[str, Any]) -> Any:
    """Canonical transmitted state of one snapshot row (MAJOR 1).

    This is what the submit would actually send for the control —
    compared with EXACT equality, never containment or sanitization:
    * ``select``: the ordered list of selected ``{label, value}``
      pairs — ``value`` is the option's VALUE ATTRIBUTE, the actual
      transmitted bytes (S1);
    * ``checkbox``/``radio``: ``{checked, value}`` — an unchecked box
      transmits nothing; a checked one transmits its value attribute;
    * ``file``: the ``<resume: name>`` marker (mirrors fill time);
    * everything else (text-like, hidden, textarea): the raw value —
      hidden inputs included (the old code never bound them);
    * non-successful controls (disabled, nameless, or button-ish):
      bound by ``{successful: False, disabled, name}`` so that a
      control that BECOMES submittable after approval (enabled, given
      a name) is a visible change, while an irrelevant attribute
      toggle on a never-submitted control does not abort a good
      submit;
    * the bound submitter (R7-A): the button the approval binds is
      rebound as successful with its ``{name, value, type,
      formaction, formmethod, formtarget, formenctype}`` — the
      submission goes to the formaction when present, so a
      post-approval formaction swap is a named abort, not a
      redirect.
    """
    if not row.get("successful"):
        return {
            "successful": False,
            "disabled": bool(row.get("disabled")),
            "name": str(row.get("name") or ""),
        }
    tag = row.get("tag")
    ctype = row.get("type")
    if tag == "select":
        opts = row.get("options") or []
        return [
            {
                "label": str(opt.get("label") or ""),
                "value": str(opt.get("value") or ""),
            }
            for opt in opts
            if isinstance(opt, dict)
        ]
    if ctype in ("checkbox", "radio"):
        return {
            "checked": bool(row.get("checked")),
            "value": str(row.get("value") or ""),
        }
    if row.get("isSubmitter"):
        # R7-A: the ACTUAL submitter the approval binds. Its
        # submission overrides determine WHERE the form submits
        # and HOW — formaction overrides the form's action, formmethod
        # the HTTP method — so all are part of the bound transmitted
        # state: a post-approval formaction/formmethod swap aborts the
        # submit, fail closed, naming the submitter. The row is marked
        # successful (unlike other button-ish controls) precisely so
        # this comparison runs. NOTE (round 9): the row stays bound as
        # successful even though the new event-free submit path does
        # NOT transmit the submitter's own name=value contribution
        # (form.submit() builds the entry list with no submitter) and
        # does NOT run page submit/click handlers — the row's job is
        # binding the submission overrides (destination/method/target/
        # enctype), which the final verification compares and sets
        # explicitly on the form.
        return {
            "submitter": True,
            "name": str(row.get("name") or ""),
            "value": str(row.get("value") or ""),
            "type": str(row.get("type") or ""),
            "formaction": str(row.get("formaction") or ""),
            "formmethod": str(row.get("formmethod") or ""),
            "formtarget": str(row.get("formtarget") or ""),
            "formenctype": str(row.get("formenctype") or ""),
        }
    return str(row.get("value") or "")


def _normalize_snapshot(
    raw_rows: Any, destination: Any, page_url: str = ""
) -> dict[str, Any] | None:
    """Normalize a raw snapshot into the comparable, storable form.

    ``raw_rows`` is the ``_SNAPSHOT_JS`` result
    (``{"rows": [...], "submitterInfo": {...}|None}``) or, for legacy
    callers, a bare list of row dicts. Returns
    ``{"rows": {binding_key: transmitted}, "submit": {...}}`` or None
    when the raw rows are unusable — or when the destination read
    failed (``destination is None``): a security-relevant read that
    failed fails closed (F2, round 8), never binds a fabricated empty
    destination. Duplicate
    binding keys are impossible from a real DOM walk (indices are
    unique) — treated as unreadable rather than silently merged. A
    relative form action is resolved against ``page_url`` via
    ``urljoin`` (MINOR 5) when the page-side URL constructor did not
    already resolve it.

    The ``submit`` block binds the EFFECTIVE destination (R7-A/R7-D):
    the submitter's ``formaction`` when present (it overrides the
    form's action — the submission goes there), else the submitter's
    OWN form's ``action``, else the empty string (a native submit to
    the current document URL). Round 9: the block ALSO binds the
    effective submission method
    (submitter ``formmethod`` || form ``method`` || ``get``), target,
    and enctype — the bound destination includes the method, and the
    final submit verification compares all of them (plus sets them
    explicitly on the form) before the event-free submit.
    ``source`` records which branch produced it — the approval display
    and the logs say honestly where the destination came from instead
    of implying "the form's action" when the binding actually came
    from a button override or a first-form fallback.
    """
    if isinstance(raw_rows, dict):
        raw_list = raw_rows.get("rows")
    else:
        raw_list = raw_rows
    if not isinstance(raw_list, list):
        return None
    rows: dict[str, Any] = {}
    for row in raw_list:
        if not isinstance(row, dict):
            return None
        bkey = _row_binding_key(row)
        if bkey in rows:
            return None
        rows[bkey] = _row_transmitted(row)
    if destination is None:
        # F2 (round 8): a security-relevant read that failed must fail
        # closed, same as unreadable rows. Binding an empty
        # destination here would display "no form found — SPA submit
        # path" as FACT for a destination that was never read, while
        # the submit-time diff only aborts if the submit-time read
        # succeeds — a failed baseline read could sail through on a
        # fabricated empty destination.
        return None
    dest = dict(destination) if isinstance(destination, dict) else {}
    if not dest.get("resolved") and dest.get("action") and page_url:
        try:
            dest["resolved"] = urljoin(page_url, str(dest["action"]))
        except Exception:
            pass
    return {
        "rows": rows,
        "submit": {
            "action": str(dest.get("action") or ""),
            "resolved": str(dest.get("resolved") or ""),
            # Round 9: the bound destination includes the method (plus
            # target/enctype) — the final submit verification compares
            # them against the approved values and sets them explicitly
            # on the form before the event-free submit.
            "method": str(dest.get("method") or "get").lower(),
            "formtarget": str(dest.get("formtarget") or ""),
            "formenctype": str(dest.get("formenctype") or "").lower(),
            "hasForm": bool(dest.get("hasForm")),
            "source": str(dest.get("source") or ""),
        },
    }


def _describe_bkey(bkey: str) -> str:
    """Human-readable control identity for abort messages (MAJOR 1)."""
    parts = _split_bkey(bkey)
    index, tag, ctype, name = (parts + ["", "", "", ""])[:4]
    label = name or f"field_{index}"
    kind = tag or "control"
    if ctype:
        kind += f" (type={ctype})"
    return f"{label!r} [{kind}, position {index}]"


def _summarize_value(value: Any, limit: int = 80) -> str:
    text = repr(value)
    return text if len(text) <= limit else text[:limit] + "…"


def _describe_destination(submit: dict[str, Any]) -> str:
    """Approval-display wording for the bound submit destination.

    R7-A/R7-D: the wording says WHERE the destination came from —
    the submitter's ``formaction`` override, the submitter's own
    form's action, or the degraded no-submitter fallback — because
    "form action X" would be a lie when the binding actually came
    from a button-level override. When there is no action, the prompt
    says so explicitly — "form has no action — submits to the current
    page URL" — instead of implying a submission to some other URL.
    """
    resolved = submit.get("resolved") or ""
    source = submit.get("source") or ""
    if resolved:
        if source == "submitter-formaction":
            return f"submitter formaction {resolved!r} (overrides form action)"
        if source in ("submitter-form-action", ""):
            return f"form action {resolved!r}"
        if source.startswith("no-submitter"):
            return f"form action {resolved!r} (no submit button located — first-form fallback)"
        return f"submit destination {resolved!r} [{source}]"
    if submit.get("hasForm"):
        return "form has no action — submits to the current page URL"
    return "no form found — submits to the current page URL"


def _diff_snapshots(
    old: dict[str, Any], new: dict[str, Any]
) -> list[str]:
    """Compare two normalized snapshots; return change descriptions.

    Empty list == identical. Every divergence the submission could transmit
    is reported: added controls, removed/moved controls, changed
    transmitted state (values, checked states, selections, hidden
    inputs), and a changed submit destination. The caller aborts on ANY
    non-empty list, fail closed, and names the changes.
    """
    changes: list[str] = []
    old_rows = old.get("rows") or {}
    new_rows = new.get("rows") or {}

    def _bkey_index(bkey: str) -> str:
        parts = _split_bkey(bkey)
        return parts[0] if parts else ""

    old_by_index: dict[str, list[str]] = {}
    for bkey in old_rows:
        old_by_index.setdefault(_bkey_index(bkey), []).append(bkey)
    new_by_index: dict[str, list[str]] = {}
    for bkey in new_rows:
        new_by_index.setdefault(_bkey_index(bkey), []).append(bkey)
    renamed_new_keys: set[str] = set()
    for bkey, old_tx in old_rows.items():
        if bkey in new_rows:
            if new_rows[bkey] != old_tx:
                changes.append(
                    "control "
                    + _describe_bkey(bkey)
                    + " changed: "
                    + _summarize_value(old_tx)
                    + " -> "
                    + _summarize_value(new_rows[bkey])
                )
            continue
        # Missing at submit time: either renamed in place (same
        # position, different identity — the S3 spoof) or genuinely
        # removed/moved.
        old_parts = _split_bkey(bkey)
        index = old_parts[0] if old_parts else ""
        candidates = [
            k for k in new_by_index.get(index, []) if k not in old_rows
        ]
        if len(candidates) == 1:
            new_key = candidates[0]
            renamed_new_keys.add(new_key)
            new_parts = _split_bkey(new_key)
            old_name = (old_parts[3] if len(old_parts) > 3 else "") or f"field_{index}"
            new_name = (new_parts[3] if len(new_parts) > 3 else "") or f"field_{index}"
            changes.append(
                f"control {old_name!r} renamed to {new_name!r} "
                f"after approval (position {index})"
            )
        else:
            changes.append(
                "control removed or moved after approval: "
                + _describe_bkey(bkey)
            )
    for bkey in new_rows:
        if bkey not in old_rows and bkey not in renamed_new_keys:
            changes.append(
                "control added after approval: " + _describe_bkey(bkey)
            )
    old_sub = old.get("submit") or {}
    new_sub = new.get("submit") or {}
    if old_sub != new_sub:
        # Round 9: the submit block binds destination AND method AND
        # target/enctype — name which part changed so the abort
        # message is honest (a POST→GET flip is not a "destination"
        # change).
        old_dest = {
            k: old_sub.get(k)
            for k in ("action", "resolved", "hasForm", "source")
        }
        new_dest = {
            k: new_sub.get(k)
            for k in ("action", "resolved", "hasForm", "source")
        }
        if old_dest != new_dest:
            changes.append(
                "submit destination changed: "
                + _describe_destination(old_sub)
                + " -> "
                + _describe_destination(new_sub)
            )
        for key, label in (
            ("method", "submit method"),
            ("formtarget", "submit target"),
            ("formenctype", "submit enctype"),
        ):
            if (old_sub.get(key) or "") != (new_sub.get(key) or ""):
                changes.append(
                    f"{label} changed after approval: "
                    f"{old_sub.get(key) or ''!r} -> {new_sub.get(key) or ''!r}"
                )
    return changes


def _capture_control_snapshot(
    page: Any,
    filled: "_FilledForm",
    submitter: dict[str, Any] | None = None,
) -> None:
    """MAJOR 1: capture the fill-time full-control snapshot.

    Snapshots EVERY successful form control AFTER filling — hidden
    inputs, checkbox/radio checked states, all selects, all input
    values including unfilled fields — because the submission transmits the
    post-fill DOM state, and the approval must bind THAT (the old code
    bound only the tool-filled subset: hostile page JS could rewrite a
    hidden input or check an opt-in box after approval and the submission
    would transmit bytes the approval never bound).

    R7-B: this fill-time capture is kept (``fill_application`` still
    calls it; ``easy_apply`` still consumes it) but it is SUPERSEDED
    on the submit path — ``_attempt_authorized_submit`` re-captures
    the baseline immediately before presenting the approval, and the
    approval display plus the submit-time diff bind THAT pre-approval
    snapshot, not this one.

    ``submitter`` is the isolated-world submitter identity (R7-A);
    None at fill time (no submitter located yet — the destination
    binding then uses the labelled first-form fallback).

    Stores the normalized snapshot plus the submit-destination binding
    on ``filled.control_snapshot``. Best-effort and never raises: when
    the snapshot cannot be captured the sidecar stays None and the
    submit-time check fails closed (the approval claimed to bind every
    control — without the baseline there is nothing to verify the
    submission against). The one exception is a page object with no JS
    bridge at all (``_READBACK_UNAVAILABLE`` — incomplete test doubles
    only): ``filled.readback_unavailable`` is set instead, and the
    submit-time check takes the legacy "unavailable" path.
    """
    try:
        raw_rows = _evaluate_unforged(page, _SNAPSHOT_JS, submitter)
        if raw_rows is _READBACK_UNAVAILABLE:
            # No JS bridge on the page object (incomplete test double
            # only). Record it so the submit-time check can take the
            # same "unavailable" path the old code took instead of
            # failing closed on a missing baseline.
            filled.readback_unavailable = True
            return
        if raw_rows is None:
            return
        dest = _evaluate_unforged(page, _SUBMIT_DESTINATION_JS, submitter)
        if dest is _READBACK_UNAVAILABLE:
            dest = None
        snap = _normalize_snapshot(
            raw_rows, dest, page_url=getattr(page, "url", "") or ""
        )
        if snap is None:
            log.warning(
                "M3 re-verification: fill-time control snapshot "
                "unreadable — full-control binding disabled for this run."
            )
            return
        filled.control_snapshot = snap
        # The snapshot subsumes the old field-count shape check
        # (added/removed controls change the row set), but keep
        # field_count populated for the legacy fallback path.
        filled.field_count = len(snap["rows"])
    except Exception as exc:
        log.warning(
            "M3 re-verification: could not capture fill-time control "
            "snapshot: %s",
            exc,
        )


def _reread_control_snapshot(
    page: Any, filled: dict[str, str]
) -> dict[str, Any] | None | object:
    """Submit-time re-read of the full control snapshot (M3 / MAJOR 1).

    Returns the normalized live snapshot, None when the DOM cannot be
    read (fail closed upstream), or ``_READBACK_UNAVAILABLE`` when the
    page object has no JS bridge at all (incomplete test doubles only).
    The caller diffs against ``filled.control_snapshot`` and aborts on
    ANY divergence, naming the changed controls.

    R7-A/R7-B: re-matches the submitter from
    ``filled.submitter_identity`` (recorded immediately before the
    approval was presented), so the submit-time destination and
    submitter row describe the same button the approval bound.
    """
    submitter = getattr(filled, "submitter_identity", None)
    try:
        raw_rows = _evaluate_unforged(page, _SNAPSHOT_JS, submitter)
        dest = _evaluate_unforged(page, _SUBMIT_DESTINATION_JS, submitter)
    except Exception as exc:  # never let a readback bug submit
        log.warning("M3 re-verification: cannot re-read the form: %s", exc)
        return None
    if raw_rows is _READBACK_UNAVAILABLE:
        return _READBACK_UNAVAILABLE
    if raw_rows is None:
        return None
    if dest is _READBACK_UNAVAILABLE:
        dest = None
    snap = _normalize_snapshot(
        raw_rows, dest, page_url=getattr(page, "url", "") or ""
    )
    if snap is None:
        log.warning("M3 re-verification: submit-time control snapshot unreadable.")
        return None
    return snap


def _submit_destination_display(filled: dict[str, str]) -> str:
    """Approval-display wording for the bound submit destination."""
    snap = getattr(filled, "control_snapshot", None) or {}
    return _describe_destination(snap.get("submit") or {})


#: The interactive approval prompt
#: (``initiatives.i09.channels.registry._present_draft``) renders only
#: the first 4000 body characters ("[…body truncated…]") while the
#: approval binds the FULL body. S4 (round 5): never let the user type
#: "send" for bytes they did not see. The cap itself is defined once in
#: email_sync (NIT 6, round 6) and imported at the top of this module.


def _refuse_overlong_approval_body(body: str) -> str | None:
    """S4: refuse interactive approval for a body the prompt truncates.

    Returns an error message when ``body`` exceeds the approval prompt's
    display cap (the prompt would show the first 4000 characters while
    the approval binds the full body — typing "send" would approve
    bytes the user never saw); returns None when the body fits. The full
    body is saved to a 0o600 preview file — "preview another way" — and
    the message names it.
    """
    text = str(body or "")
    if len(text) <= _APPROVAL_PROMPT_BODY_CAP:
        return None
    # The preview saver is shared with the email path (imported from
    # email_sync): 0o600 at creation, and it prunes old previews on
    # every save so they stop accumulating (MINOR 3, round 6).
    preview = _save_approval_preview(text)
    return (
        "Submit refused: the approval text is "
        f"{len(text)} characters, but the interactive approval prompt "
        "only displays the first "
        f"{_APPROVAL_PROMPT_BODY_CAP} — typing \"send\" would approve "
        f"{len(text) - _APPROVAL_PROMPT_BODY_CAP} characters you would "
        "never see, while the approval binds the FULL body. "
        + (
            f"The complete text was saved to {preview} — read it there, "
            "then shorten the form data so the approval text fits "
            f"{_APPROVAL_PROMPT_BODY_CAP} characters and approve again."
            if preview
            else "Shorten the form data so the approval text fits "
            f"{_APPROVAL_PROMPT_BODY_CAP} characters, then approve again."
        )
    )


def _attempt_authorized_submit(
    page: Any,
    submit: Any,
    apply_url: str,
    *,
    filled: dict[str, str],
    approval_id: str | None,
    board: str | None,
    result: dict[str, Any],
    submit_pattern: tuple[str, str | None] | None = None,
) -> None:
    """Authorize and perform the submit. Mutates ``result``.

    The submit goes through the interactive approval-record mechanism:
    ``authorize_send`` accepts ONLY a valid, fresh, unconsumed approval
    bound to the exact filled form (or prompts the user interactively on
    a TTY); otherwise the submit is refused. Never raises: every failure
    is recorded in ``result["error"]`` with ``result["submit_clicked"]``
    left False.

    Ordering (M2/M3, revised R7-B, revised round 9):

    1. Session-rescue check runs BEFORE authorization. A CAPTCHA/auth
       pause provably fires no submit, so it must not burn the
       single-use approval. (The email path already orders its pre-send
       checks before consume; the browser path now matches.)
    2. Round 9: the actual submitter the approval will bind is located
       in the CDP isolated world and its DOM identity recorded —
       including its structural node identity (``nodePath``). A
       FORMLESS submitter (a button outside any ``<form>`` — common in
       SPA apply flows) is refused HERE, before any approval is minted:
       the bound-form submit path cannot submit without a form, and
       the old code burned the single-use approval on the doomed run.
       The main-world locator is a DISCOVERY HINT only ("a submit
       button exists"); the SUBMISSION targets the bound form itself
       (``_submit_bound_form``), which re-resolves the bound identity
       at submit time, re-captures the FULL control set with the
       shared row walk, requires EXACT equality with the approved
       normalized binding (rows plus submit-time
       destination/method/target/enctype), sets the form's submission
       attributes explicitly to the approved values, and submits via
       ``HTMLFormElement.prototype.submit`` — all in ONE synchronous
       isolated-world evaluation, with NO click event and NO submit
       event ever dispatched. Bound == submitted by construction: no
       page-registered click/submit handler can run between the final
       verification and the request build (the round-8 TOCTOU — a
       hostile handler swapping ``formaction`` or flipping
       ``formmethod`` after the probe's check — is structurally
       closed), and there is no gap for a handler to rewrite hidden
       controls between a Python-side diff and the submit either.
       The old pattern-tuple "agreement" check is deleted: it compared
       pattern tuples (the isolated identity's css/text ARE the
       pattern's components), so it verified "the same pattern
       matched", never "the same element matched".
    3. R7-B: the pre-approval BASELINE snapshot is captured
       immediately before the approval is presented — after the
       pre-approval sleep, screenshot, submit-button search, and
       rescue check — through the unforged (CDP isolated world)
       channel. The approval's "will transmit" display is RENDERED
       FROM this exact snapshot (never from the claimed filled-values
       dict), and ``filled.control_snapshot`` is (re)set to it: the
       fill-time snapshot is superseded. A dead unforged channel or
       an unreadable baseline refuses the submit BEFORE any approval
       is minted or burned.
    4. The final URL is captured and the approval payload is built
       from the baseline (M1), then ``authorize_send`` claims the
       approval.
    5. The submit itself still happens AFTER consumption: a submit that
       fails (or a page that navigates oddly) may still have
       transmitted the attempt, so a failed submit does not refund the
       approval (fail closed — rationale kept from the previous order).
    6. Immediately before the submit, the FULL control snapshot is
       re-read from the DOM through the unforged (CDP isolated world)
       channel and diffed against the PRE-APPROVAL baseline (M3,
       TOCTOU — MAJOR 1/MAJOR 2, round 6; R7-A/R7-B, round 7: exact
       equality over every successful control — hidden inputs,
       checkbox/radio states, all selects, all values — PLUS the
       submitter's formaction/formmethod/formtarget/formenctype/value
       and the effective submit destination AND method, never the
       sanitized display text, so sanitize-colliding raw values cannot
       pass). On ANY divergence the submit aborts, naming the changed
       controls, and the approval STAYS consumed: the user approved
       those exact bytes, and a changed form needs a fresh approval —
       re-run rather than reusing.

    TRADE-OFF (round 9, stated honestly): because the submission
    dispatches no events, sites whose apply flow depends on JS submit
    handlers (SPA validation, analytics) will not run them — the
    submission is a native form submission to the approved
    destination using the approved method, and the submitter's own
    name=value contribution is not transmitted.
    Handler-immunity for the approved destination is bought with
    SPA-handler incompatibility; the refused alternative is
    dispatching a click and re-introducing the TOCTOU.
    """
    try:
        from initiatives.i09.channels import registry as _channels
    except Exception as exc:  # unexpected layout / import failure
        result["error"] = (
            "Submit refused: the send-approval backend is unavailable "
            f"({exc}). Failing closed — nothing was submitted."
        )
        return
    # --- M2: session rescue BEFORE authorization. A CAPTCHA or auth wall
    # may have appeared after filling (invisible reCAPTCHA v3 scores on
    # submit; post-fill injected challenges). CAPTCHA is NEVER bypassed —
    # on a hit, the submit is skipped and the pause-and-hand-off IS the
    # feature. This check provably fires no submit, so it runs before the
    # single-use approval is claimed: a pause must not burn it.
    rescue = session_rescue.check(page, board=board)
    if rescue is not None:
        shot = _take_screenshot(page, f"rescue-pre-submit-{rescue.reason}")
        rescue.screenshot_path = str(shot) if shot else None
        result["paused"] = True
        result["rescue"] = rescue.to_dict()
        result["final_url"] = page.url
        result["error"] = (
            f"Paused: {rescue.reason} detected before submit — control "
            f"handed to the user. {rescue.what_user_should_do}"
        )
        return
    # --- M1: capture the FINAL (post-navigation) url immediately before
    # authorization. The submit transmits to page.url, not to the
    # requested apply_url — the approval must bind what the submit hits.
    final_url = page.url
    result["final_url"] = final_url
    # --- R7-A: locate the ACTUAL submitter the approval will bind, in
    # the unforged world, BEFORE the approval is presented. The
    # isolated identity (css/text/formIndex/indexInForm/name/value/
    # type) is what the baseline snapshot and the submit-time re-read
    # re-match, so the bound formaction/formmethod and the effective
    # destination always describe the bound button's form — never the
    # page's first form, never an unbound guess.
    #
    # Fail closed BEFORE any approval is minted: a dead unforged
    # channel (RuntimeError) refuses the submit — binding a submitter
    # through the forgeable main world would let hostile page JS pick
    # the destination the approval displays.
    if submit is None:
        result["error"] = (
            "Submit refused: no submit/apply button was located, so no "
            "submitter can be bound. Failing closed — nothing was "
            "submitted."
        )
        return
    try:
        submitter = _locate_submitter_identity(page)
    except RuntimeError as exc:
        result["error"] = (
            "Submit refused: the submitter cannot be verified through "
            f"the unforged readback channel ({exc}). Failing closed — "
            "nothing was submitted."
        )
        return
    if isinstance(filled, _FilledForm):
        filled.submitter_identity = submitter
    # MINOR (round 9): a formless submit button — located and visible
    # but with no associated <form> (common in SPA apply flows) — can
    # never be submitted by the bound-form path (there is no form to
    # submit). Refuse BEFORE any approval is minted: the old code let
    # the run proceed to approval and then aborted in the click probe,
    # burning the user's single-use approval on a doomed run.
    if submitter is not None and submitter.get("formIndex", -1) < 0:
        result["error"] = (
            "Submit refused: the located submit button has no "
            "associated form — it sits outside any <form>, so the "
            "bound-form submit path cannot submit it (this is common "
            "in SPA apply flows, which submit via JavaScript the tool "
            "deliberately does not execute — see the round-9 trade-off "
            "note). Failing closed — nothing was submitted, and no "
            "approval was minted or consumed."
        )
        return
    # F1 (round 8), superseded by round 9: the old pattern-tuple
    # "agreement" check lived here and is DELETED. It compared
    # ``(submitter.css, submitter.text)`` against the click mechanism's
    # match pattern — but the isolated identity's css/text ARE the
    # pattern's components, so it verified "the same pattern matched
    # in both worlds", never "the same ELEMENT matched". With
    # divergent text matchers the click could hit a button the approval
    # never bound while this check passed. What replaces it, and why
    # the invariant now holds:
    #   * the main-world locator is a DISCOVERY HINT only — the
    #     submission never goes through it, so a main/isolated
    #     discovery divergence can no longer misdirect the submit;
    #   * bound == submitted BY CONSTRUCTION: ``_submit_bound_form``
    #     re-resolves the baseline-bound identity in the isolated
    #     world, verifies structural node identity (``nodePath``),
    #     re-captures the FULL control set with the shared row walk
    #     and requires EXACT equality with the approved normalized
    #     binding (rows plus submit-time
    #     destination/method/target/enctype), sets the form's
    #     submission attributes explicitly, and submits via
    #     ``HTMLFormElement.prototype.submit`` in one isolated-world
    #     evaluation — with no click event and no submit event ever
    #     dispatched, so no page handler can interleave;
    #   * ``veto_text_matches`` replicates Playwright's
    #     ``:has-text()`` normalization, so the two worlds' discovery
    #     agrees on which element a text pattern selects.
    # The pattern tuple is therefore no longer compared at all —
    # comparing it again would reintroduce the overclaim.
    if submit_pattern is not None and submitter is None:
        # Main world found a button; the unforged world sees none.
        # Same fail-closed reasoning as above. (A page object with no
        # JS bridge at all — incomplete test double only — reaches the
        # submit probe as _READBACK_UNAVAILABLE and fails closed
        # there; there is no unverified legacy path anymore.)
        if getattr(page, "context", None) is not None:
            result["error"] = (
                "Submit refused: a submit button was found, but the "
                "unforged readback cannot locate the submitter, so its "
                "formaction and destination cannot be bound. Failing "
                "closed — nothing was submitted."
            )
            return
    # --- R7-B: the PRE-APPROVAL baseline. Captured AFTER the
    # pre-approval sleep, screenshot, submit-button search, and rescue
    # check, and IMMEDIATELY before the approval payload is built and
    # presented — so the submit-time diff compares against exactly what
    # the user saw, and a DOM mutation during the pre-approval steps
    # becomes the APPROVED state (displayed honestly) rather than a
    # silent post-approval change. The approval's "will transmit"
    # display is rendered from THIS snapshot (see
    # _apply_approval_payload), never from the claimed filled dict.
    # The fill-time snapshot is SUPERSEDED here.
    #
    # Fail closed BEFORE any approval is minted or burned: without an
    # unforged baseline there is nothing the submit-time check could
    # verify the submission against.
    try:
        raw_rows = _evaluate_unforged(page, _SNAPSHOT_JS, submitter)
        dest = _evaluate_unforged(page, _SUBMIT_DESTINATION_JS, submitter)
    except RuntimeError as exc:
        result["error"] = (
            "Submit refused: the pre-approval form snapshot cannot be "
            f"read through the unforged channel ({exc}). Failing "
            "closed — nothing was submitted."
        )
        return
    if raw_rows is _READBACK_UNAVAILABLE or dest is _READBACK_UNAVAILABLE:
        # No JS bridge on the page object at all (incomplete test
        # double only — real Playwright pages always expose it). No
        # real browser, no real TOCTOU target: take the legacy
        # "unavailable" path instead of failing closed on a double.
        if isinstance(filled, _FilledForm):
            filled.readback_unavailable = True
    else:
        baseline = _normalize_snapshot(
            raw_rows, dest, page_url=final_url
        )
        if baseline is None:
            result["error"] = (
                "Submit refused: the pre-approval form snapshot is "
                "unreadable, so the submission cannot be verified against "
                "what you approved. Failing closed — nothing was "
                "submitted."
            )
            return
        if isinstance(filled, _FilledForm):
            filled.control_snapshot = baseline
            filled.field_count = len(baseline["rows"])
    payload = _apply_approval_payload(
        final_url, filled, requested_url=apply_url
    )
    # S4 (round 5): the interactive approval prompt displays only the
    # first 4000 body characters while the approval binds the FULL body.
    # Never ask the user to type "send" for bytes they cannot see —
    # refuse before any prompt is shown (so no approval is minted or
    # burned for an over-cap payload).
    overlong_refusal = _refuse_overlong_approval_body(payload.get("body") or "")
    if overlong_refusal is not None:
        result["error"] = overlong_refusal
        return
    # --- B1: single-use guarantee, provided by
    # initiatives.i09.channels.registry (NOT re-implemented here — this
    # unit may not touch registry.py). This call site relies on:
    #   * authorize_send() atomically validates AND consumes the approval
    #     under the cross-process consent-store lock, so two processes
    #     racing the same approval_id cannot both succeed (the loser
    #     fails closed with approval_already_used);
    #   * consume_approval() is idempotent — a second call after the
    #     atomic claim is a harmless no-op, never a double-spend;
    #   * the on-disk approval_consumed log entry is the cross-process
    #     replay evidence. Full B1 proof (approval replay impossible)
    #     depends on the integration-surfaces unit's registry rework and
    #     is verified when the re-review bundle includes it — see the
    #     report for this round.
    approval, refusal = _channels.authorize_send(
        payload, channel="browser-apply", approval_id=approval_id
    )
    if refusal is not None:
        result["approval_refusal"] = refusal
        result["error"] = (
            "Submit refused: no valid user approval for this exact form. "
            + str(refusal.get("instructions") or "")
        )
        return
    # N2 (round 4): NOT an assert — asserts vanish under ``python -O``.
    # If authorize_send ever returned (None, None), the old assert
    # would disappear and the submit would proceed with no approval.
    # Fail closed explicitly, loudly.
    if approval is None:
        log.error(
            "browser_apply._attempt_authorized_submit: authorize_send "
            "returned no refusal but approval is None (contract "
            "violation); refusing to submit."
        )
        result["error"] = (
            "Submit refused: the approval backend returned success "
            "without an approval record (contract violation). Failing "
            "closed — nothing was submitted."
        )
        return
    # Single-use: consumed BEFORE the submit. A failed submit does not
    # refund the approval (fail closed — the attempt may have gone out).
    _channels.consume_approval(approval, channel="browser-apply")
    # --- M3: TOCTOU re-verification. The approval bound the
    # PRE-APPROVAL form (R7-B: the baseline captured immediately before
    # the approval was presented), but the submit transmits SUBMIT-TIME
    # DOM state — the interactive prompt happened in between, and page
    # JS (or a redirect) could have changed the form. Re-read the FULL
    # control snapshot NOW (MAJOR 1, round 6; R7-A, round 7: every
    # successful control — hidden inputs, checkbox/radio checked
    # states, all selects, all input values — PLUS the submitter's
    # formaction/formmethod/formtarget/formenctype/value and the
    # effective submit destination AND method — not just the filled
    # subset) and diff it against
    # the pre-approval baseline. Fail closed: abort the submit on ANY
    # divergence, naming the changed controls. The approval STAYS
    # consumed (chosen deliberately): the user approved those exact
    # bytes, and a changed form is a different submission and needs a
    # fresh approval — re-run instead of reusing.
    #
    # Exactness (N1 round 4; S1/S3 round 5; MAJOR 1 round 6): the
    # comparison is exact equality in binding terms — raw submit-time
    # DOM values against raw pre-approval values, selects as the exact
    # (label, value-attribute) pairs bound at approval time, controls
    # bound by pre-approval positional index. No hashes, no
    # sanitization, no containment substitution anywhere in the
    # comparison. Two raw values that sanitize identically still
    # mismatch and abort.
    #
    # Unforged channel (MAJOR 2, round 6): the re-read runs in the CDP
    # isolated world, a JS realm the page's own scripts cannot forge —
    # never through the page's main-world evaluate, where hostile page
    # JS could override querySelectorAll / el.value to report approved
    # values while the live DOM is tampered.
    #
    # Round 9: this Python-side diff is the FIRST of two gates. The
    # SECOND gate is inside the final ``_SUBMIT_BOUND_FORM_JS``
    # evaluation itself, which re-captures the FULL control set with
    # the shared ``veto_capture_rows`` walk, normalizes it with the JS
    # ports of ``_row_binding_key``/``_row_transmitted``, and requires
    # EXACT equality with the approved binding — plus the submit-time
    # destination/method/target/enctype — in the SAME synchronous
    # evaluation that submits. No page JS can interleave between that
    # final verification and the request build: the Python-side diff
    # gives the named, user-readable abort and the ``m3_readback``
    # semantics; the in-evaluation diff is the atomic guarantee.
    bound = getattr(filled, "control_snapshot", None)
    if bound is None:
        if getattr(filled, "readback_unavailable", False):
            # No JS bridge on the page object at fill time (incomplete
            # test double only — real Playwright pages always expose
            # evaluate, and page JS cannot remove the Python-side
            # method). The M3 check cannot run; proceeding is safe
            # because without a real browser there is no real TOCTOU
            # target. Loudly logged by the helper, never silent.
            result["m3_readback"] = "unavailable"
        else:
            # No pre-approval baseline (the baseline capture refused or
            # a plain-dict test double that never ran the submit path).
            # Fail closed: the approval claimed to bind every control,
            # and without the baseline there is nothing to verify the
            # submission against.
            result["error"] = (
                "Submit aborted: no pre-approval control snapshot is "
                "bound to this approval, so the submission cannot be "
                "verified against what you approved. Failing closed — "
                "nothing was submitted."
            )
            return
    else:
        current = _reread_control_snapshot(page, filled)
        if current is _READBACK_UNAVAILABLE:
            # No JS bridge on the page object (incomplete test double
            # only). The M3 check cannot run; proceeding is safe because
            # without a real browser there is no real TOCTOU target.
            # Loudly logged by the helper, never silent.
            result["m3_readback"] = "unavailable"
        elif current is None:
            result["error"] = (
                "Submit aborted: the form could not be re-read after your "
                "approval, so the submission cannot be verified against it. "
                "Failing closed — nothing was submitted."
            )
            return
        else:
            changes = _diff_snapshots(bound, current)
            if changes:
                # MAJOR 1: name the changed controls — "a filled value
                # changed" is not enough when the binding covers every
                # control; the user must see WHICH control diverged
                # (e.g. the hidden input the page rewrote, the opt-in
                # box the page checked).
                detail = "; ".join(changes[:5])
                if len(changes) > 5:
                    detail += f"; …and {len(changes) - 5} more"
                result["error"] = (
                    "Submit aborted: the form changed after your approval "
                    f"— {detail}. Failing closed — nothing was submitted. "
                    "Re-run to approve the current form."
                )
                return
            result["m3_readback"] = "verified"
    if page.url != final_url:
        result["error"] = (
            "Submit aborted: the page navigated after your approval "
            f"({final_url} -> {page.url}). The approval bound the "
            "earlier URL. Failing closed — nothing was submitted."
        )
        return
    # --- Round 9: the SUBMISSION targets the bound form ITSELF —
    # never the main-world locator, and never a dispatched click.
    # ``_submit_bound_form`` re-resolves the baseline-bound submitter
    # identity in the isolated world, re-captures the FULL control
    # set with the shared row walk, and requires EXACT equality with
    # the approved normalized binding — rows plus submit-time
    # destination/method/target/enctype — in the SAME synchronous
    # isolated-world evaluation that submits via
    # ``HTMLFormElement.prototype.submit``. No click event and no
    # submit event is ever dispatched, so no page-registered
    # click/submit handler can run between the final verification and
    # the request build: the round-8 TOCTOU (a hostile handler
    # swapping ``formaction`` or flipping ``formmethod`` after the
    # probe's check) is structurally closed — and there is no gap for
    # a handler to rewrite hidden controls between a Python-side diff
    # and the submit either. The ``submit`` locator above was
    # discovery-only.
    submit_report = _submit_bound_form(page, submitter, bound)
    if submit_report is _READBACK_UNAVAILABLE:
        # No JS bridge on the page object at all (incomplete test
        # double only — real Playwright pages always expose evaluate,
        # and page JS cannot remove the Python-side method). With no
        # bridge there is no way to re-resolve the bound identity, so
        # the run fails closed: clicking the discovery-hint locator
        # would reintroduce exactly the TOCTOU the round-9 submit path
        # closes, and it is not retained for any other path either.
        result["submit_channel"] = "main-world-unavailable"
        result["error"] = (
            "Submit-time re-verification is unavailable: the page "
            "object exposes no JS evaluation bridge, so the approved "
            "binding could not be re-resolved. Failing closed — "
            "nothing was submitted."
        )
        log.error("browser submit refused: readback unavailable")
        return
    elif not isinstance(submit_report, dict) or not submit_report.get(
        "submitted"
    ):
        reason = (
            submit_report.get("reason")
            if isinstance(submit_report, dict)
            else None
        ) or "unreadable"
        if reason == "rows-changed":
            # The same-evaluation full-control diff fired: name the
            # changed controls like the Python-side M3 gate does.
            changed_bkeys = []
            if isinstance(submit_report, dict):
                for key in ("changed", "added", "removed"):
                    val = submit_report.get(key) or []
                    if isinstance(val, list):
                        changed_bkeys.extend(
                            (key, b) for b in val if isinstance(b, str)
                        )
            named = []
            for kind, bkey in changed_bkeys[:5]:
                label = _describe_bkey(bkey) if _split_bkey(bkey) else bkey
                named.append(f"{kind}: {label}")
            detail = (
                "the form controls changed after your approval — "
                + "; ".join(named)
                if named
                else "the form controls changed after your approval"
            )
            if len(changed_bkeys) > 5:
                detail += f"; …and {len(changed_bkeys) - 5} more"
        else:
            detail = {
                "no-match": "the bound submitter could not be re-resolved "
                            "at submit time",
                "identity-changed": "the re-resolved node is not the bound "
                                    "node (structural node identity changed)",
                "destination-changed": "the submit-time destination of the "
                                       "bound form differs from the approved one",
                "method-changed": "the submit-time method of the bound form "
                                  "differs from the approved one",
                "target-changed": "the submit-time target of the bound form "
                                  "differs from the approved one",
                "enctype-changed": "the submit-time enctype of the bound form "
                                   "differs from the approved one",
                "no-form": "the bound submitter has no associated form at "
                           "submit time",
                "set-attributes-threw": "the bound form's submission "
                                        "attributes could not be set at "
                                        "submit time",
                "submit-threw": "the isolated-world form submit raised",
            }.get(reason, "the bound-form submit probe failed")
        result["error"] = (
            "Submit aborted: " + detail + ". Failing closed — "
            "nothing was submitted."
        )
        return
    else:
        result["submit_channel"] = "bound-form-submit"
        submitted_dest = submit_report.get("destination") or {}
        # Defense in depth: the submit probe already refused unless the
        # submit-time destination AND method matched the approved ones;
        # double-check in Python — the named destination/method must be
        # the approved ones.
        approved_submit = (bound or {}).get("submit") or {}
        if (submitted_dest.get("resolved") or "") != (
            approved_submit.get("resolved") or ""
        ) or (submitted_dest.get("method") or "get") != (
            approved_submit.get("method") or "get"
        ):
            result["error"] = (
                "Submit aborted: the submitted form's destination or "
                "method does not match the approved binding. Failing "
                "closed — the submit already fired, so treat this run "
                "as untrusted and re-run."
            )
            return
        result["submitted_form"] = {
            "nodePath": submit_report.get("nodePath"),
            "destination": {
                "resolved": submitted_dest.get("resolved") or "",
                "method": submitted_dest.get("method") or "get",
                "source": submitted_dest.get("source") or "",
            },
        }
    try:
        page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    # Result contract (round 9): ``submitted_form`` (set above) is the
    # CANONICAL record — bound nodePath plus the verified
    # destination/method/source. Honesty note (m2): it records that the
    # submit fired and the page settled — no board confirms receipt to
    # us. ``submit_clicked`` no longer means "the button was clicked" —
    # it means the bound form was submitted with the approved
    # destination/method via the event-free submit path (no click event
    # and no submit event were ever dispatched; no page handler ran).
    # It is kept as a compatibility key, and the DEPRECATED
    # ``submitted`` alias only for the out-of-scope server.py consumer,
    # which reads them; server.py should migrate to ``submitted_form``.
    result["submit_clicked"] = True
    result["submitted"] = True  # DEPRECATED alias; see above.
    result["final_url"] = page.url
    shot2 = _take_screenshot(page, "submitted")
    result["screenshot_after_submit"] = str(shot2) if shot2 else None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def apply_via_browser(
    apply_url: str,
    profile: dict[str, Any] | None = None,
    resume_path: str | None = None,
    headless: bool = True,
    confirm: bool = False,
    approval_id: str | None = None,
    timeout_ms: int = 60000,
    board: str | None = None,
    browser_kind: str = "chromium",
) -> dict[str, Any]:
    """Fill (and optionally submit) a job application in a real browser.

    SUBMIT GATE (Rule 1): a caller-asserted boolean can NEVER authorize a
    submit — submitting transmits PII to a third-party URL. The
    submit goes through the SAME interactive approval-record mechanism as
    the email send path (``initiatives.i09.channels.registry``): the user
    is shown the apply URL and the exact filled form on the terminal and
    types ``send`` (``request_send_approval``), which mints a single-use,
    content-hash-bound, 15-minute-TTL approval record; ``authorize_send``
    verifies it and ``consume_approval`` burns it before the submit. Pass
    the minted ``approval_id`` here, or run on a TTY to be prompted after
    the preview. Without an approval the run fills fields, screenshots,
    and returns ``submit_clicked=False`` as a preview.

    Args:
        apply_url: Direct URL of the application form.
        profile: Dict of applicant details (see module docstring).
        resume_path: Local resume file to upload (skipped if missing).
        headless: Run Chromium headless (default True).
        confirm: DEPRECATED and authorizes nothing. A caller-asserted
            boolean can never authorize a submit; it is kept only so
            existing callers fail closed (preview-only) with a warning
            instead of a TypeError.
        approval_id: Approval record from an interactive user approval of
            the EXACT filled form (see above). Without it, the run
            prompts interactively on a TTY, or refuses the submit (no
            TTY) and returns the preview.
        timeout_ms: Navigation timeout.
        board: Optional board key (e.g. "linkedin"). When a saved login
            session exists for the board (see ``login_session``), it is
            loaded into the browser context so logged-in flows
            (e.g. LinkedIn Easy Apply) work.
        browser_kind: Playwright browser to launch: "chromium" (default)
            or "firefox". The chosen browser must be installed
            (``python -m playwright install chromium firefox``).
            MAJOR 2 (round 6): the submit-time security readback
            requires a CDP isolated world, which is Chromium-only — a
            firefox run FAILS CLOSED (refuses to submit, loud error)
            rather than degrade to the forgeable main-world readback.

    Returns:
        Dict with keys: ok, submit_clicked, fields_filled, fields_detected,
        screenshot, screenshot_after_submit, final_url, m3_readback,
        screenshot_cleanup, approval_refusal, error. ``submit_clicked`` is True only when the
        bound form was submitted with the approved destination/method
        after a valid approval — via the event-free submit path (no
        click or submit event is ever dispatched; no page handler runs) —
        it does NOT mean the board confirmed receipt. (``submitted`` is a
        deprecated alias of ``submit_clicked``.) ``m3_readback`` is
        "verified" when the submit-time DOM re-read matched the approved
        values, "unavailable" when the page object had no JS bridge
        (incomplete test doubles only), and "n/a" on every path where no
        readback occurred (preview-only runs, refusals, pauses).
        ``screenshot_cleanup`` is the ``cleanup_screenshots`` report
        (``{"deleted", "kept", "errors"}``) — per-file retention
        failures are surfaced here AND ERROR-logged, never silently
        discarded (S2). Never
        raises on page/automation failures — errors are returned in the
        dict.
    """
    profile = dict(profile or {})
    if confirm:
        log.warning(
            "browser_apply.apply_via_browser: confirm= is deprecated and "
            "authorizes nothing. Submitting requires a genuine interactive "
            "user approval of the exact filled form (see "
            "initiatives.i09.channels.registry.request_send_approval)."
        )
    result: dict[str, Any] = {
        "ok": False,
        # Result contract (round 9): ``submitted_form`` is the CANONICAL
        # record — the bound form's nodePath plus the verified
        # destination/method/source. ``submit_clicked`` no longer means
        # "the button was clicked"; it means the bound form was
        # submitted via the event-free submit path (kept as a
        # compatibility key). ``submitted`` is a DEPRECATED alias (same
        # value) for the out-of-scope server.py consumer; new code must
        # read ``submitted_form``.
        "submit_clicked": False,
        "submitted": False,  # DEPRECATED alias; see _attempt_authorized_submit.
        "submitted_form": None,
        "fields_filled": {},
        "fields_detected": 0,
        "screenshot": None,
        "screenshot_after_submit": None,
        "final_url": apply_url,
        "approval_refusal": None,
        # N6: m3_readback is initialized on every path — "n/a" where no
        # submit-time DOM readback occurred (preview-only runs, refusals,
        # pauses). The submit path overwrites it with "verified" or
        # "unavailable".
        "m3_readback": "n/a",
        # S2: the screenshot-retention report, filled in below. Per-file
        # deletion failures are surfaced here (not discarded).
        "screenshot_cleanup": {"deleted": [], "kept": 0, "errors": []},
        "error": None,
    }
    # Enforce the screenshot retention policy (PII) before creating new
    # ones. S2 (round 5): cleanup is best-effort — it never fails the
    # run — but its failures are NOT silent anymore. Per-file deletion
    # errors are ERROR-logged (these files contain filled-form PII, said
    # explicitly) and surfaced in result["screenshot_cleanup"], so the
    # D2 ops_goal ("screenshot files older than the retention cap —
    # zero") and the "fail loud" standing constraint are actually
    # enforced when deletion fails.
    try:
        screenshot_cleanup = cleanup_screenshots()
    except Exception as exc:  # pragma: no cover - defensive
        log.error(
            "Screenshot retention cleanup CRASHED: %s. PII-bearing "
            "screenshot files may remain on disk past the retention cap "
            "— investigate and remove them manually.",
            exc,
        )
        screenshot_cleanup = {
            "deleted": [],
            "kept": 0,
            "errors": [f"screenshot retention cleanup crashed: {exc}"],
        }
    else:
        if screenshot_cleanup.get("errors"):
            log.error(
                "Screenshot retention cleanup could not delete %d "
                "PII-bearing screenshot file(s): %s. They remain on disk "
                "past the retention cap — remove them manually.",
                len(screenshot_cleanup["errors"]),
                "; ".join(screenshot_cleanup["errors"]),
            )
    result["screenshot_cleanup"] = screenshot_cleanup
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

            # --- Submit gate (Rule 1): NEVER on a caller-asserted boolean.
            # The submit transmits PII to a third-party URL, so it
            # requires a genuine interactive user approval bound to the
            # exact filled form (approval-record mechanism shared with
            # the email send path). Without it this is preview-only.
            # F1 (round 8): the match PATTERN travels with the locator
            # so the submit path can distinguish "the main world found
            # a button but the unforged world sees none" (fail closed)
            # from "no button at all". The locator itself is
            # discovery-only — the submission targets the bound form
            # itself (round 9: no click is ever dispatched), never this
            # locator.
            submit, submit_pattern = _find_submit_button_with_pattern(page)
            if submit is None:
                result["error"] = (
                    "No submit/apply button found — nothing was submitted. "
                    "Review the screenshot; the form may be multi-step or "
                    "require manual interaction."
                )
            else:
                _attempt_authorized_submit(
                    page,
                    submit,
                    apply_url,
                    filled=result["fields_filled"],
                    approval_id=approval_id,
                    board=board,
                    result=result,
                    submit_pattern=submit_pattern,
                )
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

"""Unit tests for easy_apply.py (LinkedIn Easy Apply, fill-only).

Playwright is mocked entirely — no real browser is ever launched.
Compliance state is stubbed so tests never touch compliance.json.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest import mock

import pytest

import browser_apply
import easy_apply
from providers._common import make_job_id

BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeLocator:
    def __init__(self, page, selector):
        self.page = page
        self.selector = selector
        self._label = None

    def count(self):
        if "Easy Apply" in self.selector or "jobs-apply-button" in self.selector:
            return 1 if self.page.easy_apply_visible else 0
        if self.selector == easy_apply._MODAL_SELECTOR:
            return 1 if self.page.modal_open else 0
        if self.selector == "button":
            return len(self.page.current_labels())
        return 0

    @property
    def first(self):
        return self

    def is_visible(self):
        return self.count() > 0

    def filter(self, has_text=None):
        loc = FakeLocator(self.page, self.selector)
        loc._label = has_text
        return loc

    def click(self, timeout=None):
        label = self._label if self._label is not None else self.selector
        self.page.clicks.append(label)
        self.page.advance_frame()


class FakePage:
    """Scripted page: label_frames is the sequence of visible-button sets."""

    def __init__(self, label_frames, easy_apply_visible=True, modal_open=True):
        self.label_frames = [list(f) for f in label_frames]
        self._frame = 0
        self.easy_apply_visible = easy_apply_visible
        self.modal_open = modal_open
        self.clicks: list[str] = []
        self.url = "https://www.linkedin.com/jobs/view/123456"

    def current_labels(self):
        return self.label_frames[min(self._frame, len(self.label_frames) - 1)]

    def advance_frame(self):
        if self._frame < len(self.label_frames) - 1:
            self._frame += 1

    def goto(self, url, **kwargs):
        self.url = url

    def locator(self, selector):
        return FakeLocator(self, selector)

    def evaluate(self, script, *args):
        if "querySelectorAll('button')" in script:
            return list(self.current_labels())
        return []  # form extraction / consent: nothing found

    def screenshot(self, path=None, **kwargs):
        return None

    def wait_for_load_state(self, *args, **kwargs):
        return None


def install_fake_playwright(page, forbid_launch=False):
    """Inject a fake ``playwright.sync_api`` module into sys.modules."""
    entered = mock.MagicMock()
    entered.__enter__.return_value = entered
    entered.__exit__.return_value = False
    browser = mock.MagicMock()
    context = mock.MagicMock()
    entered.chromium.launch.return_value = browser
    browser.new_context.return_value = context
    context.new_page.return_value = page
    if forbid_launch:
        sync_pw = mock.MagicMock(
            side_effect=AssertionError("browser launched during preview!")
        )
    else:
        sync_pw = mock.MagicMock(return_value=entered)
    sync_api = types.ModuleType("playwright.sync_api")
    sync_api.sync_playwright = sync_pw
    pw = types.ModuleType("playwright")
    pw.sync_api = sync_api
    sys.modules["playwright"] = pw
    sys.modules["playwright.sync_api"] = sync_api
    return sync_pw


@pytest.fixture()
def no_browser_side_effects(monkeypatch):
    """Stub compliance gates + screenshots + sleeps + input."""
    monkeypatch.setattr(
        easy_apply.compliance, "is_board_allowed", lambda b: (True, "")
    )
    monkeypatch.setattr(
        easy_apply.compliance, "check_apply_allowed", lambda: (True, "")
    )
    recorded = mock.MagicMock()
    monkeypatch.setattr(easy_apply.compliance, "record_application", recorded)
    shots = []
    monkeypatch.setattr(
        browser_apply, "_take_screenshot",
        lambda page, suffix="preview": shots.append(suffix) or Path(f"/tmp/{suffix}.png"),
    )
    monkeypatch.setattr(easy_apply.time, "sleep", lambda s: None)
    monkeypatch.setattr("builtins.input", lambda *a, **k: "")
    return {"recorded": recorded, "shots": shots}


@pytest.fixture()
def profile():
    return {
        "full_name": "Ada Lovelace",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": "ada@example.com",
        "phone": "+1 555-0100",
        "location": "New York, NY",
        "linkedin_url": "https://www.linkedin.com/in/adalovelace",
    }


# ---------------------------------------------------------------------------
# Preview: zero browser activity
# ---------------------------------------------------------------------------


def test_preview_launches_no_browser(profile, no_browser_side_effects):
    sync_pw = install_fake_playwright(FakePage([["Easy Apply"]]),
                                      forbid_launch=True)
    url = "https://www.linkedin.com/jobs/view/123456"
    result = easy_apply.fill_easy_apply(url, profile, None, confirm=False)
    sync_pw.assert_not_called()
    assert result["status"] == "preview"
    assert result["fill_only"] is True
    assert "disclosure" in result
    disclosure = result["disclosure"]
    assert "ToS" in disclosure or "scraping" in disclosure.lower()
    # names only, no values
    assert "ada@example.com" not in str(result)
    assert "email" in result["fields_would_fill"]
    assert result.get("submitted_by_automation", False) is False
    no_browser_side_effects["recorded"].assert_not_called()


def test_preview_bad_job_id(profile):
    result = easy_apply.fill_easy_apply("not-a-job-id", profile, None)
    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# Confirmed run: fill-only enforcement
# ---------------------------------------------------------------------------


def test_confirmed_flow_never_clicks_submit(profile, no_browser_side_effects):
    page = FakePage([
        ["Easy Apply"],                                  # job page
        ["Next"],                                        # modal step 1
        ["Next"],                                        # modal step 2
        ["Review your application", "Submit application"],  # review step
    ])
    install_fake_playwright(page)
    url = "https://www.linkedin.com/jobs/view/123456"
    result = easy_apply.fill_easy_apply(url, profile, None, confirm=True)

    assert result["status"] == "awaiting_user_submit"
    assert result["submitted_by_automation"] is False
    # The ONLY modal-navigation clicks are the Next ones — never Submit.
    # (page.clicks[0] is the Easy Apply button selector itself.)
    assert page.clicks, "expected modal navigation clicks"
    label_clicks = [c for c in page.clicks if not str(c).startswith("button")]
    assert label_clicks and all(c == "Next" for c in label_clicks), page.clicks
    assert not any("submit" in str(c).lower() for c in page.clicks)
    assert len(result["screenshots"]) >= 3  # step shots + handoff shot
    no_browser_side_effects["recorded"].assert_called_once()


def test_step_bound_respected(profile, no_browser_side_effects):
    # Modal never reaches the review step: must stop after MAX_MODAL_STEPS.
    page = FakePage([["Easy Apply"]] + [["Next"]] * 12)
    install_fake_playwright(page)
    result = easy_apply.fill_easy_apply(
        "https://www.linkedin.com/jobs/view/123456", profile, None, confirm=True
    )
    assert result["status"] == "step_limit_reached"
    assert result["steps_taken"] == easy_apply.MAX_MODAL_STEPS
    next_clicks = [c for c in page.clicks if c == "Next"]
    assert len(next_clicks) == easy_apply.MAX_MODAL_STEPS
    assert not any("submit" in str(c).lower() for c in page.clicks)
    assert result["submitted_by_automation"] is False


def test_already_applied_short_circuits(profile, no_browser_side_effects):
    page = FakePage([["Applied"]], easy_apply_visible=False)
    install_fake_playwright(page)
    result = easy_apply.fill_easy_apply(
        "https://www.linkedin.com/jobs/view/123456", profile, None, confirm=True
    )
    assert result["status"] == "already_applied"
    assert page.clicks == []
    no_browser_side_effects["recorded"].assert_not_called()


def test_no_easy_apply_button(profile, no_browser_side_effects):
    page = FakePage([["Save", "Share"]], easy_apply_visible=False)
    install_fake_playwright(page)
    result = easy_apply.fill_easy_apply(
        "https://www.linkedin.com/jobs/view/123456", profile, None, confirm=True
    )
    assert result["status"] == "no_easy_apply"
    assert page.clicks == []


def test_click_labeled_button_refuses_submit():
    page = mock.MagicMock()
    with pytest.raises(AssertionError, match="FILL-ONLY VIOLATION"):
        easy_apply._click_labeled_button(page, "Submit application")
    with pytest.raises(AssertionError, match="FILL-ONLY VIOLATION"):
        easy_apply._click_labeled_button(page, "submit")
    page.locator.assert_not_called()


def test_compliance_cap_blocks(profile, no_browser_side_effects, monkeypatch):
    monkeypatch.setattr(
        easy_apply.compliance, "check_apply_allowed",
        lambda: (False, "Daily application cap reached"),
    )
    page = FakePage([["Easy Apply"]])
    sync_pw = install_fake_playwright(page, forbid_launch=True)
    result = easy_apply.fill_easy_apply(
        "https://www.linkedin.com/jobs/view/123456", profile, None, confirm=True
    )
    assert result["status"] == "blocked"
    sync_pw.assert_not_called()


# ---------------------------------------------------------------------------
# Wiring contract
# ---------------------------------------------------------------------------


def test_register_tools_exposes_easy_apply_fill(profile, monkeypatch):
    captured = {}

    class FakeMCP:
        def tool(self):
            def deco(fn):
                captured[fn.__name__] = fn
                return fn
            return deco

    fake_server = types.ModuleType("server")
    job_id = make_job_id("linkedin", "https://www.linkedin.com/jobs/view/999")
    fake_server._decode_job_id = lambda jid: ("linkedin", "https://x")
    fake_server._load_saved_profile = lambda: dict(profile)
    monkeypatch.setitem(sys.modules, "server", fake_server)

    easy_apply.register_tools(FakeMCP())
    assert "easy_apply_fill" in captured

    tool = captured["easy_apply_fill"]
    preview = tool(job_id, confirm=False)
    assert preview["status"] == "preview"
    assert preview["fill_only"] is True
    assert "disclosure" in preview

    # non-linkedin board rejected
    fake_server._decode_job_id = lambda jid: ("indeed", "https://x")
    bad = tool("indeed:abc", confirm=False)
    assert bad["status"] == "error"


def test_register_cli_adds_easy_apply_command():
    import argparse

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    easy_apply.register_cli(sub)
    args = parser.parse_args(
        ["easy-apply", "--job-id", "linkedin:abc123", "--confirm"]
    )
    assert args.command == "easy-apply"
    assert args.job_id == "linkedin:abc123"
    assert args.confirm is True
    assert callable(args.func)

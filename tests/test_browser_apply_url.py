#!/usr/bin/env python3
"""Apply-page destination checks: refuse private and metadata URLs."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import browser_apply  # noqa: E402


class _FakePage:
    def __init__(self, final_url):
        self.url = "about:blank"
        self.goto_calls: list[str] = []
        self._final = final_url

    def goto(self, url, wait_until=None, timeout=None):
        self.goto_calls.append(url)
        self.url = self._final


class ApplyUrlTest(unittest.TestCase):
    def test_loopback_apply_url_refused_before_navigation(self):
        result = browser_apply.apply_via_browser("http://127.0.0.1/apply")
        self.assertFalse(result["ok"])
        self.assertIn("error", result)
        self.assertTrue(result["error"])

    def test_imds_apply_url_refused_before_navigation(self):
        result = browser_apply.apply_via_browser(
            "http://169.254.169.254/latest/meta-data"
        )
        self.assertFalse(result["ok"])
        self.assertTrue(result["error"])

    def test_metadata_hostname_refused(self):
        result = browser_apply.apply_via_browser(
            "http://metadata.google.internal/"
        )
        self.assertFalse(result["ok"])
        self.assertTrue(result["error"])

    def test_file_scheme_outside_workspace_refused(self):
        result = browser_apply.apply_via_browser("file:///etc/passwd")
        self.assertFalse(result["ok"])
        self.assertTrue(result["error"])

    def test_landing_on_private_url_aborts_fill(self):
        page = _FakePage("http://169.254.169.254/latest/meta-data")
        err = browser_apply.confirm_apply_landing(
            page, "https://careers.example.com/apply"
        )
        self.assertIsNotNone(err)
        self.assertIn("169.254", err or "")

    def test_goto_then_private_landing_reports_error(self):
        page = _FakePage("http://127.0.0.1/secret")
        page.goto("https://careers.example.com/apply")
        err = browser_apply.confirm_apply_landing(
            page, "https://careers.example.com/apply"
        )
        self.assertIsNotNone(err)
        self.assertEqual(page.url, "http://127.0.0.1/secret")


if __name__ == "__main__":
    unittest.main()

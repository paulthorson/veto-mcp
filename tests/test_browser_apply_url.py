#!/usr/bin/env python3
"""Apply-page destination checks: refuse private and metadata URLs."""

from __future__ import annotations

import ipaddress
import sys
import unittest
from pathlib import Path
from unittest import mock

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import browser_apply  # noqa: E402
import url_policy  # noqa: E402


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
        page.goto("https://careers.example.com/apply")
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

    def test_intermediate_redirect_hop_to_imds_is_refused(self):
        start = "https://careers.example.com/apply"
        private = "http://169.254.169.254/latest/meta-data"
        final = "https://careers.example.com/form"

        class _Req:
            def __init__(self, url, redirected_from=None):
                self.url = url
                self.redirected_from = redirected_from

        first = _Req(start)
        mid = _Req(private, redirected_from=first)
        last = _Req(final, redirected_from=mid)

        class _Resp:
            request = last

        class _Page:
            url = final

        hops = browser_apply.navigation_hop_urls(start, _Resp(), _Page())
        self.assertIn(private, hops)
        self.assertIn(start, hops)
        self.assertIn(final, hops)

        def _resolve(host):
            try:
                return [ipaddress.ip_address(host.strip("[]"))]
            except ValueError:
                return [ipaddress.ip_address("93.184.216.34")]

        with mock.patch.object(url_policy, "resolve_host_ips", side_effect=_resolve):
            err = browser_apply.confirm_apply_hops(hops)
        self.assertIsNotNone(err)
        self.assertIn("169.254", err or "")

    def test_public_intermediate_hops_are_allowed(self):
        start = "https://careers.example.com/apply"
        mid = "https://careers.example.com/next"
        final = "https://careers.example.com/form"

        class _Req:
            def __init__(self, url, redirected_from=None):
                self.url = url
                self.redirected_from = redirected_from

        hops = browser_apply.navigation_hop_urls(
            start,
            type("R", (), {"request": _Req(final, _Req(mid, _Req(start)))})(),
            type("P", (), {"url": final})(),
        )
        with mock.patch.object(
            url_policy,
            "resolve_host_ips",
            return_value=[ipaddress.ip_address("93.184.216.34")],
        ):
            self.assertIsNone(browser_apply.confirm_apply_hops(hops))


if __name__ == "__main__":
    unittest.main()

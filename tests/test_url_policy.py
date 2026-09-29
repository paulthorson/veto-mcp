#!/usr/bin/env python3
"""Workspace path and destination checks."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import url_policy  # noqa: E402


class DestinationTest(unittest.TestCase):
    def test_http_loopback_blocked(self):
        self.assertIsNotNone(url_policy.destination_error("http://127.0.0.1/"))
        self.assertIsNotNone(url_policy.destination_error("http://[::1]/"))

    def test_imds_blocked(self):
        self.assertIsNotNone(
            url_policy.destination_error("http://169.254.169.254/latest/meta-data")
        )
        self.assertIsNotNone(
            url_policy.destination_error("http://metadata.google.internal/")
        )

    def test_rfc1918_blocked(self):
        for url in (
            "http://10.1.2.3/",
            "https://172.16.0.1/job",
            "http://192.168.0.5/x",
        ):
            self.assertIsNotNone(url_policy.destination_error(url), url)

    def test_file_scheme_blocked_by_default(self):
        self.assertIsNotNone(url_policy.destination_error("file:///etc/passwd"))

    def test_public_example_allowed_when_resolver_returns_public_ip(self):
        import ipaddress

        with mock.patch.object(
            url_policy,
            "resolve_host_ips",
            return_value=[ipaddress.ip_address("93.184.216.34")],
        ):
            self.assertIsNone(
                url_policy.destination_error("https://careers.example.com/j/1")
            )


class PathConfineTest(unittest.TestCase):
    def test_relative_path_stays_in_repo(self):
        resolved = url_policy.confine_user_path("applications.csv")
        self.assertEqual(resolved, url_policy.REPO_ROOT / "applications.csv")

    def test_absolute_escape_rejected(self):
        with self.assertRaises(url_policy.PathDenied):
            url_policy.confine_user_path("/tmp/escape.csv")

    def test_dotdot_rejected(self):
        with self.assertRaises(url_policy.PathDenied):
            url_policy.confine_user_path("../secret.csv")

    def test_user_data_dir_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"VETO_DATA_DIR": tmp}):
                target = Path(tmp) / "out.csv"
                self.assertEqual(
                    url_policy.confine_user_path(target), target.resolve()
                )


class WebhookPolicyTest(unittest.TestCase):
    def test_empty_allowlist_fails_closed(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("JOB_MCP_WEBHOOK_ALLOWED_HOSTS", None)
            err = url_policy.webhook_error("https://example.com/hook")
        self.assertIsNotNone(err)
        self.assertIn("allowlist", (err or "").lower())

    def test_https_required(self):
        with mock.patch.dict(
            os.environ, {"JOB_MCP_WEBHOOK_ALLOWED_HOSTS": "example.com"}
        ):
            self.assertIsNotNone(
                url_policy.webhook_error("http://example.com/hook")
            )

    def test_private_host_refused_even_if_listed(self):
        with mock.patch.dict(
            os.environ, {"JOB_MCP_WEBHOOK_ALLOWED_HOSTS": "127.0.0.1"}
        ):
            self.assertIsNotNone(
                url_policy.webhook_error("https://127.0.0.1/hook")
            )


class SvgRenderSourceTest(unittest.TestCase):
    def test_app_js_does_not_assign_raw_svg_innerhtml(self):
        src = (BASE_DIR / "webui" / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("w.innerHTML = s", src)
        self.assertIn("DOMParser", src)
        self.assertIn("sanitizeSvgNode", src)


if __name__ == "__main__":
    unittest.main()

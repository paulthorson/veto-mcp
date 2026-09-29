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

    def test_this_network_and_cgnat_blocked(self):
        for url in (
            "http://0.0.0.0/",
            "http://0.1.2.3/",
            "http://100.64.0.1/",
            "http://100.127.255.1/",
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


class PinRequestTest(unittest.TestCase):
    def test_rewrites_hostname_to_checked_ip_and_sets_host(self):
        import ipaddress

        with mock.patch.object(
            url_policy,
            "resolve_host_ips",
            return_value=[ipaddress.ip_address("93.184.216.34")],
        ):
            connect, headers, err = url_policy.pin_request(
                "https://careers.example.com/j/1"
            )
        self.assertIsNone(err)
        self.assertEqual(connect, "https://93.184.216.34/j/1")
        self.assertEqual(headers.get("Host"), "careers.example.com")

    def test_public_ip_literal_is_unchanged(self):
        connect, headers, err = url_policy.pin_request("https://1.2.3.4/x")
        self.assertIsNone(err)
        self.assertEqual(connect, "https://1.2.3.4/x")
        self.assertEqual(headers, {})

    def test_private_destination_is_not_pinned(self):
        connect, headers, err = url_policy.pin_request("http://127.0.0.1/")
        self.assertIsNotNone(err)
        self.assertEqual(connect, "")
        self.assertEqual(headers, {})

    def test_this_network_and_cgnat_are_not_pinned(self):
        for url in (
            "http://0.0.0.0/",
            "http://100.64.0.1/",
        ):
            connect, _headers, err = url_policy.pin_request(url)
            self.assertIsNotNone(err, url)
            self.assertEqual(connect, "")

    def test_client_get_never_omits_follow_redirects_false(self):
        seen: list[bool | None] = []

        class _Picky:
            def get(self, url, follow_redirects=None, **kwargs):
                if kwargs:
                    raise TypeError("unexpected kwargs")
                seen.append(follow_redirects)
                return object()

        url_policy.client_get_no_redirect(
            _Picky(), "https://example.com/", headers={"Host": "example.com"},
            extensions={"sni_hostname": "example.com"},
        )
        self.assertEqual(seen, [False])

    def test_client_get_refuses_auto_follow_fallback(self):
        class _Auto:
            def get(self, url, **kwargs):
                if "follow_redirects" in kwargs:
                    raise TypeError("no follow_redirects")
                raise AssertionError("must not fall back to auto-follow")

        with self.assertRaises(TypeError):
            url_policy.client_get_no_redirect(_Auto(), "https://example.com/")


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

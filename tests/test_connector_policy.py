#!/usr/bin/env python3
"""Q2 gate policy test suite — Initiative 09.

The roadmap's Q2 exit gate: *every connector passes one capability
contract and one policy test suite before release.* The capability half
lives in test_provider_contracts.py (conformance_suite); this module is
the POLICY half, applied uniformly across every connector:

  P1  Every connector declares a complete manifest (the four
      proof-of-value sections).
  P2  CAPTCHA is never bypassed (pause-and-hand-off is the only path).
  P3  No submit/send/write happens without explicit confirmation at the
      moment of action.
  P4  Health/scorecard/consent state is local-first: no network calls, no
      data leaves the device.
  P5  Communication channels never auto-enable.
"""

import inspect
import unittest

import ats_apply
import browser_apply
import easy_apply
from initiatives.i09 import calendar_handoff, channels
from initiatives.i09.channels import registry as channel_registry
from providers import _contract, health_contract, scorecard, session_rescue


def _all_manifests():
    manifests = list(_contract.all_manifests())
    manifests += [spec.manifest for spec in channel_registry.CHANNELS.values()]
    manifests.append(calendar_handoff.CALENDAR_MANIFEST)
    return manifests


class P1ManifestCompleteness(unittest.TestCase):
    def test_every_connector_manifest_complete(self):
        for manifest in _all_manifests():
            self.assertEqual(
                manifest.validate(), [],
                f"{manifest.name}: incomplete proof-of-value declaration",
            )

    def test_every_manifest_names_what_requires_confirmation(self):
        for manifest in _all_manifests():
            self.assertTrue(
                manifest.what_requires_confirmation,
                f"{manifest.name}: no confirmation requirements declared",
            )

    def test_every_manifest_names_what_data_it_sends(self):
        for manifest in _all_manifests():
            self.assertTrue(
                manifest.what_data_it_sends,
                f"{manifest.name}: data egress not declared",
            )


class P2CaptchaNeverBypassed(unittest.TestCase):
    def test_rescue_module_has_no_bypass_path(self):
        names = [n for n, _ in inspect.getmembers(session_rescue)]
        self.assertFalse(any("bypass" in n.lower() for n in names))

    def test_browser_apply_wires_rescue_pause(self):
        import pathlib
        src = pathlib.Path(browser_apply.__file__).read_text()
        self.assertIn("session_rescue.check", src)
        self.assertIn('result["paused"] = True', src)

    def test_easy_apply_wires_rescue_pause(self):
        import pathlib
        src = pathlib.Path(easy_apply.__file__).read_text()
        self.assertIn("session_rescue.check", src)
        self.assertIn("rescue_paused", src)

    def test_easy_apply_submit_guard_structural(self):
        # The fill-only guarantee: submit-labelled buttons raise.
        class FakeButton:
            def click(self, timeout=None):
                raise AssertionError("should not be clicked")
        class FakePage:
            def get_by_role(self, *a, **k):
                class Q:
                    def all(self_inner):
                        return []
                return Q()
        with self.assertRaises(AssertionError):
            easy_apply._click_labeled_button(FakePage(), "Submit application")


class P3ConfirmationGates(unittest.TestCase):
    def test_ats_apply_preview_without_confirm(self):
        from providers._common import make_job_id
        job_id = make_job_id("ashby", "board:123")
        out = ats_apply.apply_direct(
            "ashby", {"id": job_id}, {"full_name": "Test"},
            confirm=False, dry_run=True,
        )
        self.assertEqual(out["mode"], "preview")
        self.assertEqual(out["network_calls"], 0)
        self.assertFalse(out["direct_apply_available"])

    def test_ats_apply_confirmed_without_endpoint_refuses(self):
        from providers._common import make_job_id
        job_id = make_job_id("greenhouse", "tok:1")
        out = ats_apply.apply_direct(
            "greenhouse", {"id": job_id}, {"full_name": "Test"},
            confirm=True, dry_run=False,
        )
        self.assertFalse(out["ok"])
        self.assertFalse(out["direct_apply_available"])

    def test_calendar_handoff_needs_confirm(self):
        draft = calendar_handoff.propose_followup_reminder(
            {"company": "Acme", "title": "Eng"},
            from_date="2026-09-13T00:00:00+00:00",
        )
        out = calendar_handoff.confirm_and_handoff(draft, confirm=False)
        self.assertFalse(out["ok"])
        self.assertEqual(out["handed_off"], 0)

    def test_gmail_send_needs_two_gates(self):
        # Gate 1: channel enablement. Gate 2: per-send confirm.
        channel = channel_registry.GmailChannel()
        out = channel.send_followup({"to": "r@example.com"}, confirm=True)
        self.assertFalse(out.get("sent", False))
        self.assertEqual(out["error"], "channel_not_enabled")


class P4LocalFirst(unittest.TestCase):
    def test_health_and_scorecard_make_no_network_calls(self):
        import pathlib
        for module in (health_contract, scorecard):
            src = pathlib.Path(module.__file__).read_text().lower()
            for token in ("httpx", "urllib.request", "socket.", "requests."):
                self.assertNotIn(token, src, f"{module.__name__}: {token}")

    def test_consent_log_defaults_inside_repo(self):
        self.assertTrue(
            str(channel_registry.CONSENT_LOG).startswith(
                str(channel_registry.BASE_DIR)
            )
        )

    def test_health_store_defaults_inside_repo(self):
        # The scorecard's default store is 03's contract when importable,
        # else a repo-local JSONL fallback — never a remote service.
        store = health_contract.default_store()
        self.assertTrue(
            isinstance(store, health_contract.ProviderHealthAdapter)
            or isinstance(store, health_contract.FileHealthStore)
        )
        if isinstance(store, health_contract.FileHealthStore):
            self.assertTrue(
                str(store.path).startswith(str(channel_registry.BASE_DIR)),
                f"fallback health store outside repo: {store.path}",
            )


class P5NoAutoEnable(unittest.TestCase):
    def test_channels_never_auto_enable(self):
        for name, spec in channel_registry.CHANNELS.items():
            self.assertFalse(spec.enabled_by_default, name)
        # Fresh registry state (no consent log) => nothing enabled.
        import tempfile
        from pathlib import Path
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(channel_registry, "CONSENT_LOG",
                                   Path(tmp) / "c.jsonl"):
                self.assertEqual(channel_registry.enabled_channels(), [])


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Tests for Initiative 09 epic 3: explicit opt-in communication channels.

Asserts the core invariant: no channel is ever enabled by default, by
upgrade, or by implication. Every enable needs explicit confirm=True and
is audit-logged; every send needs a second confirmation at send time.
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from initiatives.i09 import channels
from initiatives.i09.channels import registry


class ChannelRegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._patch = mock.patch.object(
            registry, "CONSENT_LOG", Path(self.tmp.name) / "consent.jsonl"
        )
        self._patch.start()
        self.addCleanup(self._patch.stop)

    def test_no_channel_enabled_by_default(self):
        for name in registry.CHANNELS:
            self.assertFalse(registry.is_enabled(name), name)
        self.assertEqual(registry.enabled_channels(), [])

    def test_enable_requires_explicit_confirm(self):
        result = registry.enable_channel("gmail")
        self.assertFalse(result["ok"])
        self.assertFalse(registry.is_enabled("gmail"))
        self.assertIn("manifest", result)  # declaration shown first

    def test_enable_with_confirm_and_audit(self):
        result = registry.enable_channel("gmail", confirm=True,
                                         via="test-wizard")
        self.assertTrue(result["ok"])
        self.assertTrue(registry.is_enabled("gmail"))
        history = registry.consent_history("gmail")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["action"], "enable")
        self.assertEqual(history[0]["via"], "test-wizard")

    def test_disable_reverts(self):
        registry.enable_channel("discord", confirm=True, via="test")
        self.assertTrue(registry.is_enabled("discord"))
        out = registry.disable_channel("discord", via="test")
        self.assertTrue(out["ok"])
        self.assertFalse(registry.is_enabled("discord"))
        self.assertNotIn("discord", registry.enabled_channels())

    def test_unknown_channel_rejected(self):
        result = registry.enable_channel("smoke-signals", confirm=True)
        self.assertFalse(result["ok"])
        self.assertIn("known_channels", result)

    def test_channel_spec_invariant(self):
        for name, spec in registry.CHANNELS.items():
            self.assertFalse(spec.enabled_by_default, name)
            self.assertEqual(spec.manifest.validate(), [],
                             f"manifest incomplete: {name}")

    def test_skill_channels_declare_explicit_skill_basis(self):
        for name in ("whatsapp", "discord", "messenger"):
            manifest = registry.channel_manifest(name)
            self.assertIsNotNone(manifest)
            blocked = " ".join(manifest.why_it_may_be_blocked).lower()
            self.assertIn("skill", blocked)
            sent = " ".join(manifest.what_data_it_sends).lower()
            self.assertIn("nothing today", sent)


class GmailChannelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._patch = mock.patch.object(
            registry, "CONSENT_LOG", Path(self.tmp.name) / "consent.jsonl"
        )
        self._patch.start()
        self.addCleanup(self._patch.stop)
        self.channel = registry.GmailChannel()

    def test_blocked_when_channel_not_enabled(self):
        out = self.channel.draft_followup("app-1")
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"], "channel_not_enabled")

    def test_send_refused_without_confirm_even_when_enabled(self):
        registry.enable_channel("gmail", confirm=True, via="test")
        out = self.channel.send_followup({"to": "r@example.com"}, confirm=False)
        self.assertFalse(out["sent"])
        self.assertIn("confirm=True", out["instructions"])

    def test_draft_delegates_to_email_sync_when_enabled(self):
        registry.enable_channel("gmail", confirm=True, via="test")
        with mock.patch("email_sync.draft_followup",
                        return_value={"to": "", "subject": "s"}) as m:
            out = self.channel.draft_followup("app-1", kind="nudge")
        self.assertTrue(out["ok"])
        m.assert_called_once_with("app-1", kind="nudge")

    def test_send_delegates_with_confirm_true(self):
        registry.enable_channel("gmail", confirm=True, via="test")
        with mock.patch("email_sync.send_followup",
                        return_value={"sent": True}) as m:
            out = self.channel.send_followup({"to": "r@example.com"},
                                             confirm=True)
        self.assertTrue(out["sent"])
        m.assert_called_once_with({"to": "r@example.com"}, confirm=True)


if __name__ == "__main__":
    unittest.main()

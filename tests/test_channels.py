#!/usr/bin/env python3
"""Tests for Initiative 09 epic 3: explicit opt-in communication channels.

Core invariants:
* No channel is ever enabled by default, by upgrade, or by implication.
* Every enable needs explicit confirm=True from an enumerated opt-in
  source and is audit-logged; a consent write that does not land is a
  FAILED enable, never reported as success.
* Every send requires a genuine interactive user approval bound to the
  exact draft content (nonce + content hash + timestamp, written only by
  the terminal prompt). A caller-asserted confirm=True is a deprecated
  no-op; a self-minted content digest (draft_approval_token) authorizes
  nothing; direct calls to email_sync.send_followup enforce the same
  boundary — draft substitution and replay fail closed.
* The consent store is integrity-protected (0o600, fsync, HMAC with a
  machine-local key); malformed/tampered entries are loudly logged and
  never trusted (fail closed). A single bad line bricks every channel
  until the audit-preserving quarantine repair
  (registry.quarantine_consent_log) moves it — never deletes it — and
  the store re-verifies. Key loss fails closed with a recovery runbook
  (RECOVERY.md).

Test strategies (stated explicitly):

1. Adversarial attack-regression. Every Rule 1 demonstrated attack
   (self-minted token, caller-asserted confirm=True, direct-call bypass,
   draft substitution, approval replay) has a named regression test that
   runs the REAL authorization boundary against a fake or refused
   transport. This strategy trades away scenario breadth to get
   guaranteed re-detection of the specific exploits that were
   demonstrated against us.

2. Transport-edge mocking. Tests mock at the transport edge
   (_gmail_connected / _gmail_send / _run_gmail_cli) and NEVER at the
   approval edge (authorize_send, _validate_approval, the consent log):
   authorization is genuinely exercised while a real send is physically
   impossible. This strategy trades away end-to-end fidelity to get a
   guarantee that the test suite can never cause a real send on any
   machine.
"""

import contextlib
import hashlib
import hmac
import io
import json
import os
import stat
import threading
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from initiatives.i09 import channels
from initiatives.i09.channels import registry


def _send_expected(draft):
    """The spec §6.2 varying approval value for a send draft.

    The interactive prompt requires the user to type this exact string;
    it is the recipient address as shown in the draft display and varies
    per send — a fixed "send"/"yes" never matches it.
    """
    return str((draft or {}).get("to") or "").strip()



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
        result = registry.enable_channel("gmail", via="cli-wizard")
        self.assertFalse(result["ok"])
        self.assertFalse(registry.is_enabled("gmail"))
        self.assertIn("manifest", result)  # declaration shown first

    def test_enable_with_confirm_and_audit(self):
        result = registry.enable_channel(
            "gmail", confirm=True, via="cli-wizard"
        )
        self.assertTrue(result["ok"])
        self.assertTrue(registry.is_enabled("gmail"))
        history = registry.consent_history("gmail")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["action"], "enable")
        self.assertEqual(history[0]["via"], "cli-wizard")
        self.assertIn("mac", history[0])  # integrity-signed

    def test_consent_files_are_private(self):
        registry.enable_channel("gmail", confirm=True, via="web-ui")
        log_mode = stat.S_IMODE(registry.CONSENT_LOG.stat().st_mode)
        self.assertEqual(log_mode, 0o600)
        key_mode = stat.S_IMODE(
            registry._consent_key_path().stat().st_mode
        )
        self.assertEqual(key_mode, 0o600)

    def test_via_must_be_enumerated(self):
        result = registry.enable_channel(
            "gmail", confirm=True, via="test-wizard"
        )
        self.assertFalse(result["ok"])
        self.assertIn("invalid_via", result["error"])
        self.assertFalse(registry.is_enabled("gmail"))

    def test_disable_reverts(self):
        registry.enable_channel("discord", confirm=True, via="api")
        self.assertTrue(registry.is_enabled("discord"))
        out = registry.disable_channel("discord", via="api")
        self.assertTrue(out["ok"])
        self.assertFalse(registry.is_enabled("discord"))
        self.assertNotIn("discord", registry.enabled_channels())

    def test_unknown_channel_rejected(self):
        result = registry.enable_channel(
            "smoke-signals", confirm=True, via="cli-wizard"
        )
        self.assertFalse(result["ok"])
        self.assertIn("known_channels", result)

    def test_channel_spec_invariant_raises_not_asserts(self):
        bad = registry.ChannelSpec(
            name="evil",
            skill="",
            manifest=registry.channel_manifest("gmail"),
            enabled_by_default=True,
        )
        with self.assertRaises(ValueError):
            registry._register(bad)
        self.assertNotIn("evil", registry.CHANNELS)

    def test_consent_write_failure_is_enable_failure(self):
        with mock.patch("os.open", side_effect=OSError("EIO: disk gone")):
            result = registry.enable_channel(
                "gmail", confirm=True, via="cli-wizard"
            )
        self.assertFalse(result["ok"])
        self.assertFalse(result["enabled"])
        self.assertIn("consent_write_failed", result["error"])

    def test_consent_write_failure_is_disable_failure(self):
        registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        with mock.patch("os.open", side_effect=OSError("EIO: disk gone")):
            result = registry.disable_channel("gmail", via="cli-wizard")
        self.assertFalse(result["ok"])
        self.assertIn("consent_write_failed", result["error"])

    def test_malformed_lines_are_loud_and_fail_closed(self):
        registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        with registry.CONSENT_LOG.open("a", encoding="utf-8") as fh:
            fh.write("this is not json\n")
            fh.write('{"channel": "gmail", "action": "enable"}\n')  # no mac
        with self.assertLogs("veto-mcp.i09.channels", level="ERROR") as cm:
            history = registry.consent_history("gmail")
        loud = "\n".join(cm.output)
        self.assertIn("malformed JSON", loud)
        self.assertIn("rejected", loud)
        # Only the one genuinely signed entry survives; store untrusted.
        self.assertEqual(len(history), 1)
        with self.assertLogs("veto-mcp.i09.channels", level="ERROR"):
            self.assertFalse(registry.is_enabled("gmail"))

    def test_tampered_entry_is_rejected_loudly(self):
        registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        raw = registry.CONSENT_LOG.read_text(encoding="utf-8")
        tampered = raw.replace('"channel": "gmail"', '"channel": "discord"')
        self.assertNotEqual(raw, tampered)
        registry.CONSENT_LOG.write_text(tampered, encoding="utf-8")
        with self.assertLogs("veto-mcp.i09.channels", level="ERROR") as cm:
            history = registry.consent_history()
        self.assertIn("signature mismatch", "\n".join(cm.output))
        self.assertEqual(history, [])
        self.assertFalse(registry.is_enabled("gmail"))  # fail closed

    def test_channel_spec_invariant(self):
        for name, spec in registry.CHANNELS.items():
            self.assertFalse(spec.enabled_by_default, name)
            self.assertEqual(
                spec.manifest.validate(), [], f"manifest incomplete: {name}"
            )

    def test_skill_channels_declare_explicit_skill_basis(self):
        for name in ("whatsapp", "discord", "messenger"):
            manifest = registry.channel_manifest(name)
            self.assertIsNotNone(manifest)
            blocked = " ".join(manifest.why_it_may_be_blocked).lower()
            self.assertIn("skill", blocked)
            sent = " ".join(manifest.what_data_it_sends).lower()
            self.assertIn("nothing today", sent)

    def test_package_exports(self):
        self.assertIn("draft_approval_token", channels.__all__)
        self.assertIn("VALID_VIA_SOURCES", channels.__all__)


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
        self.draft_a = {
            "to": "recruiter@example.com",
            "subject": "Following up",
            "body": "Hi — checking in.",
        }

    def _enable(self):
        result = registry.enable_channel(
            "gmail", confirm=True, via="cli-wizard"
        )
        self.assertTrue(result["ok"])

    def _token_for(self, draft):
        return registry.draft_approval_token(draft)

    def _interactive_approval(self, draft, answer=None):
        """Simulate a genuine interactive user approval of ``draft``.

        Patches the TTY check and the prompt input so request_send_approval
        runs exactly as it would with a real user at the terminal typing
        ``answer`` (default: the per-send varying value — the recipient
        address exactly as shown; a fixed "send"/"yes" fails). Returns
        the approval_id on success.
        """
        expected = _send_expected(draft)
        if answer is None:
            answer = expected
        with (
            mock.patch.object(registry, "_stdin_is_tty", return_value=True),
            mock.patch.object(registry, "_approval_input", return_value=answer),
        ):
            res = registry.request_send_approval(
                draft, channel="gmail", expected_value=expected
            )
        self.assertTrue(res["ok"], res)
        self.assertTrue(res["approved"])
        return res["approval_id"]

    def test_blocked_when_channel_not_enabled(self):
        out = self.channel.draft_followup("app-1")
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"], "channel_not_enabled")

    def test_send_refused_when_channel_disabled(self):
        out = self.channel.send_followup(self.draft_a, confirm=True)
        self.assertFalse(out["sent"])
        self.assertEqual(out["error"], "channel_not_enabled")

    def test_self_mint_attack_fails(self):
        """VETO ATTACK 1 repro: self-minted token + confirm=True sends nothing.

        A caller with zero user involvement computes its own
        draft_approval_token for an arbitrary draft and asserts
        confirm=True. The send must be refused by the REAL boundary
        inside email_sync (only the transport is mocked) — never sent.
        """
        self._enable()
        evil = dict(self.draft_a, to="attacker@evil.example")
        self_minted = self._token_for(evil)  # public digest — proves nothing
        import email_sync

        with mock.patch.object(
            email_sync, "_gmail_send"
        ) as m:
            out = self.channel.send_followup(
                evil, confirm=True, approval_token=self_minted
            )
        self.assertFalse(out["sent"])
        self.assertEqual(out["error"], "not_interactive")  # no TTY here
        m.assert_not_called()  # transport never attempted

    def test_confirm_true_alone_is_not_authorization(self):
        """confirm=True is a deprecated no-op: without a genuine interactive
        approval the send is refused, not sent."""
        self._enable()
        import email_sync

        with mock.patch.object(email_sync, "_gmail_send") as m:
            out = self.channel.send_followup(self.draft_a, confirm=True)
        self.assertFalse(out["sent"])
        self.assertEqual(out["error"], "not_interactive")
        m.assert_not_called()

    def test_approval_token_is_ignored_for_authorization(self):
        """The content digest is never accepted as proof of approval."""
        self._enable()
        token = self._token_for(self.draft_a)
        problem = registry._validate_approval(token, registry._content_hash(self.draft_a))
        self.assertEqual(problem, "no_such_approval")

    def test_draft_substitution_attack_fails_closed(self):
        """Approving draft A must not authorize sending draft B.

        Simulates a genuine interactive approval of draft A, then tries
        to spend that approval on a substituted draft B. Refused, and the
        transport is never attempted.
        """
        self._enable()
        approval_id = self._interactive_approval(self.draft_a)
        draft_b = dict(self.draft_a, to="attacker@evil.example")
        with mock.patch("email_sync._gmail_send") as m:
            out = self.channel.send_followup(draft_b, approval_id=approval_id)
        self.assertFalse(out["sent"])
        self.assertEqual(out["error"], "approval_content_mismatch")
        m.assert_not_called()

    def test_token_binds_exact_content(self):
        self._enable()
        token = self._token_for(self.draft_a)
        # Whitespace-only drift still matches (canonicalized); a real edit
        # does not.
        drifted = dict(self.draft_a, body="  Hi — checking in.  ")
        self.assertEqual(self._token_for(drifted), token)
        edited = dict(self.draft_a, subject="Following up!!!")
        self.assertNotEqual(self._token_for(edited), token)

    def test_draft_returns_approval_token(self):
        self._enable()
        with mock.patch(
            "email_sync.draft_followup", return_value=dict(self.draft_a)
        ):
            out = self.channel.draft_followup("app-1", kind="nudge")
        self.assertTrue(out["ok"])
        self.assertEqual(out["approval_token"], self._token_for(self.draft_a))

    def test_draft_delegates_to_email_sync_when_enabled(self):
        self._enable()
        with mock.patch(
            "email_sync.draft_followup", return_value={"to": "", "subject": "s"}
        ) as m:
            out = self.channel.draft_followup("app-1", kind="nudge")
        self.assertTrue(out["ok"])
        m.assert_called_once_with("app-1", kind="nudge")

    def test_send_does_not_mutate_delegated_result(self):
        self._enable()
        approval_id = self._interactive_approval(self.draft_a)
        delegated = {"sent": True}
        with mock.patch(
            "email_sync.send_followup", return_value=delegated
        ):
            out = self.channel.send_followup(
                self.draft_a, approval_id=approval_id
            )
        self.assertTrue(out["sent"])
        self.assertEqual(out["channel"], "gmail")
        self.assertNotIn("channel", delegated)  # original untouched

    def test_send_against_real_email_sync_gate(self):
        """Two-layer test — the REAL email_sync.send_followup runs its own
        identical boundary, but the TRANSPORT EDGE is mocked so a real
        email can NEVER go out, on this machine or any other.

        A genuine (simulated) interactive approval exists; the real
        email_sync.send_followup then verifies the real approval against
        the real consent log and must refuse at its own
        'gmail_not_connected' gate — a value only the real email_sync
        can produce, proving the approval was honored and delegation
        actually happened. The transport edge (_gmail_connected forced
        False, _gmail_send hard-wired to explode) is mocked, NOT the
        approval edge: authorization is genuinely exercised, sending is
        physically impossible.
        """
        self._enable()
        approval_id = self._interactive_approval(self.draft_a)
        import email_sync

        self.assertTrue(hasattr(email_sync, "send_followup"))
        with (
            mock.patch.object(email_sync, "_gmail_connected", return_value=False),
            mock.patch.object(
                email_sync, "_gmail_send",
                side_effect=AssertionError(
                    "real transport must never be called in tests"
                ),
            ) as m,
        ):
            out = self.channel.send_followup(
                self.draft_a, approval_id=approval_id
            )
        self.assertFalse(out["sent"])
        self.assertEqual(out["error"], "gmail_not_connected")
        self.assertEqual(out["channel"], "gmail")
        m.assert_not_called()

    def test_genuine_interactive_approval_sends(self):
        """The interactive path, end to end: user types 'send', Gmail
        (mocked transport) goes out exactly once."""
        self._enable()
        approval_id = self._interactive_approval(self.draft_a)
        import email_sync

        with (
            mock.patch.object(email_sync, "_gmail_connected", return_value=True),
            mock.patch.object(
                email_sync, "_gmail_send", return_value={"ok": True}
            ) as m,
        ):
            out = self.channel.send_followup(
                self.draft_a, approval_id=approval_id
            )
        self.assertTrue(out["sent"])
        self.assertEqual(out["to"], "recruiter@example.com")
        m.assert_called_once()

    def test_channel_stays_enabled_after_approval_record(self):
        """Regression: send_approval / approval_consumed log entries must
        not flip is_enabled — only enable/disable entries decide state."""
        self._enable()
        approval_id = self._interactive_approval(self.draft_a)
        self.assertTrue(registry.is_enabled("gmail"))
        registry.consume_approval(approval_id, channel="gmail")
        self.assertTrue(registry.is_enabled("gmail"))
        self.assertIn("gmail", registry.enabled_channels())
        out = registry.disable_channel("gmail", via="cli-wizard")
        self.assertTrue(out["ok"])
        self.assertFalse(registry.is_enabled("gmail"))

    def test_approval_is_single_use(self):
        """Spending an approval twice: the replay is refused."""
        self._enable()
        approval_id = self._interactive_approval(self.draft_a)
        import email_sync

        with (
            mock.patch.object(email_sync, "_gmail_connected", return_value=True),
            mock.patch.object(email_sync, "_gmail_send", return_value={"ok": True}),
        ):
            first = self.channel.send_followup(
                self.draft_a, approval_id=approval_id
            )
            second = self.channel.send_followup(
                self.draft_a, approval_id=approval_id
            )
        self.assertTrue(first["sent"])
        self.assertFalse(second["sent"])
        self.assertEqual(second["error"], "approval_already_used")


class InteractiveBoundaryRegressionTests(unittest.TestCase):
    """Regression tests for the Rule 1 veto rework (case
    init-09-comms-rereview): interactive confirmation at the send
    boundary, closing the self-mint + direct-call bypasses."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._patch = mock.patch.object(
            registry, "CONSENT_LOG", Path(self.tmp.name) / "consent.jsonl"
        )
        self._patch.start()
        self.addCleanup(self._patch.stop)
        self.draft = {
            "to": "recruiter@example.com",
            "subject": "Following up",
            "body": "Hi — checking in.",
        }
        import email_sync

        self.email_sync = email_sync
        # email_sync.send_followup enforces the channel-enable gate before
        # the approval boundary: these tests exercise the approval
        # boundary itself, so the channel must be explicitly enabled first.
        self.assertTrue(
            registry.enable_channel("gmail", confirm=True, via="cli-wizard")[
                "ok"
            ]
        )

    def _interactive_approval(self, draft):
        expected = _send_expected(draft)
        with (
            mock.patch.object(registry, "_stdin_is_tty", return_value=True),
            mock.patch.object(
                registry, "_approval_input", return_value=expected
            ),
        ):
            res = registry.request_send_approval(
                draft, channel="gmail", expected_value=expected
            )
        self.assertTrue(res["ok"], res)
        return res["approval_id"]

    def _enable(self):
        self.assertTrue(
            registry.enable_channel("gmail", confirm=True, via="cli-wizard")[
                "ok"
            ]
        )

    def _no_tty(self):
        return mock.patch.object(registry, "_stdin_is_tty", return_value=False)

    # -- VETO ATTACK 1b repro: direct email_sync call, confirm=True, no user --
    def test_direct_email_sync_call_with_confirm_true_refuses(self):
        """email_sync.send_followup(draft, confirm=True) with no user
        approval and no TTY must refuse and never touch Gmail."""
        with (
            self._no_tty(),
            mock.patch.object(self.email_sync, "_run_gmail_cli") as cli,
        ):
            out = self.email_sync.send_followup(dict(self.draft), confirm=True)
        self.assertFalse(out["sent"])
        self.assertEqual(out["error"], "not_interactive")
        cli.assert_not_called()

    # -- Interactive approval happy path through the direct call --
    def test_direct_call_with_genuine_approval_sends(self):
        approval_id = self._interactive_approval(self.draft)
        with (
            mock.patch.object(
                self.email_sync, "_gmail_connected", return_value=True
            ),
            mock.patch.object(
                self.email_sync, "_gmail_send", return_value={"ok": True}
            ) as m,
        ):
            out = self.email_sync.send_followup(
                dict(self.draft), approval_id=approval_id
            )
        self.assertTrue(out["sent"])
        m.assert_called_once_with(
            "recruiter@example.com", "Following up", "Hi — checking in."
        )

    # -- Approval already on file (wizard preview → approve → send flow) --
    def test_unconsumed_approval_on_file_authorizes_without_threading_id(self):
        approval_id = self._interactive_approval(self.draft)
        with (
            mock.patch.object(
                self.email_sync, "_gmail_connected", return_value=True
            ),
            mock.patch.object(
                self.email_sync, "_gmail_send", return_value={"ok": True}
            ) as m,
        ):
            out = self.email_sync.send_followup(dict(self.draft))
        self.assertTrue(out["sent"])
        m.assert_called_once()
        # The approval was spent: a second send must refuse, not reuse.
        with self._no_tty():
            again = self.email_sync.send_followup(dict(self.draft))
        self.assertFalse(again["sent"])

    # -- Declined / aborted approvals write nothing and refuse --
    def test_declined_approval_writes_no_record(self):
        with (
            mock.patch.object(registry, "_stdin_is_tty", return_value=True),
            mock.patch.object(registry, "_approval_input", return_value="no"),
        ):
            res = registry.request_send_approval(self.draft, expected_value=_send_expected(self.draft))
        self.assertFalse(res["ok"])
        self.assertEqual(res["error"], "approval_declined")
        self.assertIsNone(registry._find_unconsumed_approval(
            registry._content_hash(self.draft)))

    def test_non_tty_approval_request_refuses(self):
        with self._no_tty():
            res = registry.request_send_approval(self.draft, expected_value=_send_expected(self.draft))
        self.assertFalse(res["ok"])
        self.assertEqual(res["error"], "not_interactive")

    # -- Expired approvals are refused --
    def test_expired_approval_refused(self):
        approval_id = self._interactive_approval(self.draft)
        with mock.patch.object(registry, "APPROVAL_TTL_SECONDS", -1):
            problem = registry._validate_approval(
                approval_id, registry._content_hash(self.draft)
            )
        self.assertEqual(problem, "approval_expired")
        with (
            self._no_tty(),
            mock.patch.object(registry, "APPROVAL_TTL_SECONDS", -1),
        ):
            out = self.email_sync.send_followup(
                dict(self.draft), approval_id=approval_id
            )
        self.assertFalse(out["sent"])
        self.assertEqual(out["error"], "approval_expired")

    # -- Malformed approval id is not trusted --
    def test_unknown_approval_id_refused(self):
        with self._no_tty():
            out = self.email_sync.send_followup(
                dict(self.draft), approval_id="deadbeef" * 8
            )
        self.assertFalse(out["sent"])
        self.assertEqual(out["error"], "no_such_approval")

    # -- Key loss fails closed and points at the runbook --
    def test_key_loss_fails_closed_with_recovery_pointer(self):
        self._enable()
        self.assertTrue(registry.is_enabled("gmail"))
        registry._consent_key_path().unlink()  # lose the key
        # A fresh key is generated on next use, so every old entry fails
        # verification: the store must read as untrusted and the channel
        # as disabled, with loud logs pointing at the recovery runbook.
        with self.assertLogs(
            "veto-mcp.i09.channels", level="ERROR"
        ) as cm:
            enabled = registry.is_enabled("gmail")
        self.assertFalse(enabled)  # fail closed
        loud = "\n".join(cm.output)
        self.assertIn("RECOVERY.md", loud)
        # The runbook the log points at must actually exist.
        recovery = (
            Path(registry.__file__).parent / "RECOVERY.md"
        )
        self.assertTrue(recovery.is_file())
        self.assertIn("re-key", recovery.read_text(encoding="utf-8").lower())


class QuarantineRepairTests(unittest.TestCase):
    """BLOCKER 1: a single torn consent-log line bricks every channel with
    no recovery (fail closed, dead end). The repair path is
    registry.quarantine_consent_log(): bad lines are MOVED to an
    audit-preserving quarantine file (never silently deleted), the log is
    re-verified, and channel operation is restored."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.log = Path(self.tmp.name) / "consent.jsonl"
        self._patch = mock.patch.object(registry, "CONSENT_LOG", self.log)
        self._patch.start()
        self.addCleanup(self._patch.stop)

    def _tear(self, *lines):
        with self.log.open("a", encoding="utf-8") as fh:
            for line in lines:
                fh.write(line if line.endswith("\n") else line + "\n")

    def test_torn_line_bricks_all_channels(self):
        registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        registry.enable_channel("discord", confirm=True, via="cli-wizard")
        self.assertTrue(registry.is_enabled("gmail"))
        self._tear("this is not json")
        self.assertFalse(registry.is_enabled("gmail"))
        self.assertFalse(registry.is_enabled("discord"))
        self.assertEqual(registry.enabled_channels(), [])

    def test_enable_surfaced_integrity_warning_matches_is_enabled(self):
        """enable_channel must never return ok:true/enabled:true while
        is_enabled reads False. The divergence is surfaced honestly with
        an integrity_warning naming the quarantine repair."""
        self._tear("this is not json")
        with self.assertLogs("veto-mcp.i09.channels", level="ERROR"):
            result = registry.enable_channel(
                "messenger", confirm=True, via="cli-wizard"
            )
        self.assertTrue(result["ok"])  # the write landed
        self.assertFalse(result["enabled"])
        self.assertIn("integrity_warning", result)
        self.assertIn("quarantine", result["integrity_warning"].lower())
        # No SILENT divergence: the return matches is_enabled exactly.
        self.assertEqual(result["enabled"], registry.is_enabled("messenger"))
        self.assertIn("RECOVERY.md", result["integrity_warning"])

    def test_quarantine_repairs_and_preserves_audit_trail(self):
        registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        registry.enable_channel("discord", confirm=True, via="cli-wizard")
        torn = "this is not json"
        no_sig = '{"channel": "gmail", "action": "enable"}'  # unsigned
        self._tear(torn, no_sig)
        original_bytes = self.log.read_bytes()
        self.assertFalse(registry.is_enabled("gmail"))

        with self.assertLogs("veto-mcp.i09.channels", level="WARNING"):
            result = registry.quarantine_consent_log()

        self.assertTrue(result["ok"])
        self.assertEqual(result["quarantined"], 2)
        self.assertTrue(result["integrity_ok"])
        qpath = Path(result["quarantine_file"])
        self.assertTrue(qpath.is_file())
        self.assertEqual(stat.S_IMODE(qpath.stat().st_mode), 0o600)

        # Channels restored: the verified enable entries survived.
        self.assertTrue(registry.is_enabled("gmail"))
        self.assertTrue(registry.is_enabled("discord"))

        # Audit trail intact: the quarantine file holds the ORIGINAL bytes
        # verbatim (nothing deleted), and the repair is a signed entry in
        # the consent log itself.
        qrecords = [
            json.loads(line)
            for line in qpath.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(len(qrecords), 2)
        originals = {r["original_line"] for r in qrecords}
        # The exact original bytes, unaltered (they are JSON-escaped inside
        # the quarantine record — decode and compare verbatim).
        self.assertIn(torn, originals)
        self.assertIn(no_sig, originals)
        reasons = {r["reason"] for r in qrecords}
        self.assertEqual(reasons, {"malformed_json", "missing signature"})
        audit = [
            e
            for e in registry.consent_history()
            if e.get("action") == "consent_quarantine"
        ]
        self.assertEqual(len(audit), 1)
        self.assertEqual(audit[0]["quarantined"], 2)
        self.assertEqual(audit[0]["quarantine_file"], str(qpath))
        # Conservation: every original line is either still in the log or
        # in the quarantine file — nothing vanished.
        log_bytes = self.log.read_bytes()
        for line in original_bytes.split(b"\n"):
            if not line.strip():
                continue
            self.assertTrue(
                line in log_bytes or line.decode("utf-8") in originals,
                f"line lost from both log and quarantine: {line!r}",
            )
        # The store re-verifies clean afterwards.
        _, integrity_ok = registry.consent_history(with_integrity=True)
        self.assertTrue(integrity_ok)

    def test_quarantine_clean_log_is_noop(self):
        registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        result = registry.quarantine_consent_log()
        self.assertTrue(result["ok"])
        self.assertEqual(result["quarantined"], 0)
        self.assertIsNone(result["quarantine_file"])
        self.assertTrue(registry.is_enabled("gmail"))
        audit = [
            e
            for e in registry.consent_history()
            if e.get("action") == "consent_quarantine"
        ]
        self.assertEqual(audit, [])  # no audit entry for a no-op

    def test_quarantine_cleans_dead_entries_after_key_rotation(self):
        registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        self.assertTrue(registry.is_enabled("gmail"))
        rotation = registry.rotate_consent_key()
        self.assertTrue(rotation["ok"])
        # Old entries are cryptographically dead: fail closed.
        self.assertFalse(registry.is_enabled("gmail"))
        result = registry.quarantine_consent_log()
        self.assertTrue(result["ok"])
        self.assertGreaterEqual(result["quarantined"], 1)
        self.assertTrue(result["integrity_ok"])
        # The dead enable is gone from history; the quarantine repair is
        # audited; a fresh explicit enable works again.
        self.assertFalse(registry.is_enabled("gmail"))
        self.assertTrue(
            registry.enable_channel("gmail", confirm=True, via="cli-wizard")[
                "ok"
            ]
        )
        self.assertTrue(registry.is_enabled("gmail"))

    def test_quarantine_never_moves_valid_entries(self):
        registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        registry.enable_channel("discord", confirm=True, via="api")
        result = registry.quarantine_consent_log()
        self.assertEqual(result["quarantined"], 0)
        self.assertTrue(registry.is_enabled("gmail"))
        self.assertTrue(registry.is_enabled("discord"))
        self.assertEqual(len(registry.consent_history()), 2)

    def test_quarantine_package_export(self):
        self.assertIn("quarantine_consent_log", channels.__all__)


class AuthorizeSendDirectTests(unittest.TestCase):
    """M3: authorize_send tested DIRECTLY — every fail-closed branch of the
    security-critical send boundary, not just transitively."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._patch = mock.patch.object(
            registry, "CONSENT_LOG", Path(self.tmp.name) / "consent.jsonl"
        )
        self._patch.start()
        self.addCleanup(self._patch.stop)
        self.draft = {
            "to": "recruiter@example.com",
            "subject": "Following up",
            "body": "Hi — checking in.",
        }

    def _mint(self, channel="gmail"):
        with (
            mock.patch.object(registry, "_stdin_is_tty", return_value=True),
            mock.patch.object(
                registry, "_approval_input", return_value=_send_expected(self.draft)
            ),
        ):
            res = registry.request_send_approval(self.draft, channel=channel, expected_value=_send_expected(self.draft))
        self.assertTrue(res["ok"], res)
        return res["approval_id"]

    def test_valid_approval_id_authorizes(self):
        aid = self._mint()
        got, refusal = registry.authorize_send(
            self.draft, channel="gmail", approval_id=aid,
            expected_value=_send_expected(self.draft),
        )
        self.assertEqual(got, aid)
        self.assertIsNone(refusal)

    def test_unknown_approval_id_refused(self):
        _, refusal = registry.authorize_send(
            self.draft, channel="gmail", approval_id="0" * 64,
            expected_value=_send_expected(self.draft),
        )
        self.assertEqual(refusal["error"], "no_such_approval")
        self.assertFalse(refusal["sent"])

    def test_content_mismatch_refused(self):
        aid = self._mint()
        other = dict(self.draft, subject="Something else")
        _, refusal = registry.authorize_send(
            other, channel="gmail", approval_id=aid,
            expected_value=_send_expected(other),
        )
        self.assertEqual(refusal["error"], "approval_content_mismatch")

    def test_expired_approval_refused(self):
        aid = self._mint()
        with mock.patch.object(registry, "APPROVAL_TTL_SECONDS", -1):
            _, refusal = registry.authorize_send(
                self.draft, channel="gmail", approval_id=aid,
                expected_value=_send_expected(self.draft),
            )
        self.assertEqual(refusal["error"], "approval_expired")

    def test_reused_approval_refused(self):
        aid = self._mint()
        registry.consume_approval(aid, channel="gmail")
        _, refusal = registry.authorize_send(
            self.draft, channel="gmail", approval_id=aid,
            expected_value=_send_expected(self.draft),
        )
        self.assertEqual(refusal["error"], "approval_already_used")

    def test_malformed_approval_refused(self):
        """A signed approval record whose timestamp cannot be parsed is
        rejected as malformed — hand-crafted directly against the key."""
        key = registry._load_or_create_key()
        body = {
            "ts": "not-a-number",
            "action": "send_approval",
            "channel": "gmail",
            "nonce": "malformed-nonce",
            "content_hash": registry._content_hash(self.draft),
        }
        body["mac"] = __import__("hmac").new(
            key, registry._canonical_bytes(body), __import__("hashlib").sha256
        ).hexdigest()
        with registry.CONSENT_LOG.open("a", encoding="utf-8") as fh:
            fh.write(
                __import__("json").dumps(body, sort_keys=True) + "\n"
            )
        problem = registry._validate_approval(
            "malformed-nonce", registry._content_hash(self.draft)
        )
        self.assertEqual(problem, "approval_malformed")
        _, refusal = registry.authorize_send(
            self.draft, channel="gmail", approval_id="malformed-nonce",
            expected_value=_send_expected(self.draft),
        )
        self.assertEqual(refusal["error"], "approval_malformed")

    def test_no_approval_no_tty_refused(self):
        with mock.patch.object(registry, "_stdin_is_tty", return_value=False):
            _, refusal = registry.authorize_send(self.draft, channel="gmail", expected_value=_send_expected(self.draft))
        self.assertEqual(refusal["error"], "not_interactive")
        self.assertFalse(refusal["sent"])

    def test_no_approval_with_tty_prompts_mints_and_claims(self):
        """authorize_send CLAIMS the approval atomically: the interactive
        path mints, then validates+consumes under the store lock, so a
        second validation sees it as already used (single-use)."""
        with (
            mock.patch.object(registry, "_stdin_is_tty", return_value=True),
            mock.patch.object(
                registry, "_approval_input", return_value=_send_expected(self.draft)
            ),
        ):
            got, refusal = registry.authorize_send(
                self.draft, channel="gmail",
                expected_value=_send_expected(self.draft),
            )
        self.assertIsNone(refusal)
        self.assertIsNotNone(got)
        # Claimed: a second validation reports single-use exhaustion, and
        # a second authorize_send for the same approval is refused.
        self.assertEqual(
            registry._validate_approval(
                got, registry._content_hash(self.draft), channel="gmail"
            ),
            "approval_already_used",
        )
        _, refusal2 = registry.authorize_send(
            self.draft, channel="gmail", approval_id=got,
            expected_value=_send_expected(self.draft),
        )
        self.assertEqual(refusal2["error"], "approval_already_used")
        self.assertFalse(refusal2["sent"])

    def test_invalid_draft_refused_not_crash(self):
        got, refusal = registry.authorize_send(None, channel="gmail", expected_value="x")
        self.assertIsNone(got)
        self.assertEqual(refusal["error"], "invalid_draft")

    def test_unverifiable_store_refused(self):
        with mock.patch.object(
            registry, "_read_consent", return_value=([], False)
        ):
            _, refusal = registry.authorize_send(
                self.draft, channel="gmail", approval_id="abc",
                expected_value=_send_expected(self.draft),
            )
        self.assertEqual(refusal["error"], "consent_store_unverifiable")


class RotateConsentKeyTests(unittest.TestCase):
    """M3: rotate_consent_key tested DIRECTLY — the recovery operation."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._patch = mock.patch.object(
            registry, "CONSENT_LOG", Path(self.tmp.name) / "consent.jsonl"
        )
        self._patch.start()
        self.addCleanup(self._patch.stop)

    def _key_path(self):
        return registry._consent_key_path()

    def test_rotate_invalidates_old_consents_fail_closed(self):
        self.assertTrue(
            registry.enable_channel("gmail", confirm=True, via="cli-wizard")[
                "ok"
            ]
        )
        self.assertTrue(registry.is_enabled("gmail"))
        result = registry.rotate_consent_key()
        self.assertTrue(result["ok"])
        backup = Path(result["backup"])
        self.assertTrue(backup.is_file())
        self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o600)
        self.assertIn("warning", result)
        # Old consents fail closed: unverifiable, channel reads disabled.
        with self.assertLogs("veto-mcp.i09.channels", level="ERROR"):
            self.assertFalse(registry.is_enabled("gmail"))
        # The documented procedure: quarantine the cryptographically-dead
        # entries (RECOVERY.md Procedure B) — the dead lines still fail
        # verification until they are archived, so a re-enable alone
        # cannot restore integrity.
        quarantine = registry.quarantine_consent_log()
        self.assertTrue(quarantine["ok"])
        self.assertGreaterEqual(quarantine["quarantined"], 1)
        # A fresh explicit enable under the new key works and verifies.
        self.assertTrue(
            registry.enable_channel("gmail", confirm=True, via="cli-wizard")[
                "ok"
            ]
        )
        self.assertTrue(registry.is_enabled("gmail"))

    def test_rotate_without_existing_key(self):
        result = registry.rotate_consent_key()
        self.assertTrue(result["ok"])
        self.assertIsNone(result["backup"])

    def test_rotate_writes_signed_audit_entry(self):
        """MINOR 7: rotate_consent_key records a signed consent_key_rotated
        audit entry under the fresh key."""
        self.assertTrue(
            registry.enable_channel("gmail", confirm=True, via="cli-wizard")[
                "ok"
            ]
        )
        result = registry.rotate_consent_key()
        self.assertTrue(result["ok"])
        # consent_history only returns integrity-verified entries: the
        # audit entry must be signed with the NEW key.
        audits = [
            e
            for e in registry.consent_history()
            if e.get("action") == "consent_key_rotated"
        ]
        self.assertEqual(len(audits), 1)
        self.assertEqual(audits[0]["key_backup"], result["backup"])
        self.assertIn("mac", audits[0])
        entry, problem = registry._verify_entry(
            audits[0], registry._load_or_create_key()
        )
        self.assertEqual(problem, "")
        self.assertIsNotNone(entry)

    def test_rotate_failure_reported(self):
        self.assertTrue(
            registry.enable_channel("gmail", confirm=True, via="cli-wizard")[
                "ok"
            ]
        )
        with mock.patch("os.rename", side_effect=OSError("EROFS")):
            result = registry.rotate_consent_key()
        self.assertFalse(result["ok"])
        self.assertIn("key_rotation_failed", result["error"])
        # Key still in place; the store still verifies.
        self.assertTrue(self._key_path().exists())
        self.assertTrue(registry.is_enabled("gmail"))


class ApprovalWriteFailureTests(unittest.TestCase):
    """M3: the approval-write-failure branch of request_send_approval —
    a user who typed 'send' must not be told approval succeeded when the
    record never landed."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._patch = mock.patch.object(
            registry, "CONSENT_LOG", Path(self.tmp.name) / "consent.jsonl"
        )
        self._patch.start()
        self.addCleanup(self._patch.stop)
        self.draft = {
            "to": "recruiter@example.com",
            "subject": "Following up",
            "body": "Hi — checking in.",
        }

    def test_approval_write_failure_is_not_an_approval(self):
        with (
            mock.patch.object(registry, "_stdin_is_tty", return_value=True),
            mock.patch.object(
                registry, "_approval_input", return_value=_send_expected(self.draft)
            ),
            mock.patch.object(
                registry, "_append_consent", side_effect=OSError("EIO")
            ),
            self.assertLogs("veto-mcp.i09.channels", level="ERROR"),
        ):
            res = registry.request_send_approval(self.draft, channel="gmail", expected_value=_send_expected(self.draft))
        self.assertFalse(res["ok"])
        self.assertFalse(res["approved"])
        self.assertIn("approval_write_failed", res["error"])
        # Nothing was written: no approval can be found for this draft.
        self.assertIsNone(
            registry._find_unconsumed_approval(
                registry._content_hash(self.draft)
            )
        )

    def test_request_send_approval_rejects_non_dict_draft(self):
        with mock.patch.object(registry, "_stdin_is_tty", return_value=True):
            res = registry.request_send_approval(None, channel="gmail", expected_value="x")
        self.assertFalse(res["ok"])
        self.assertEqual(res["error"], "invalid_draft")

    def test_request_send_approval_timeout_fails_closed(self):
        with (
            mock.patch.object(registry, "_stdin_is_tty", return_value=True),
            mock.patch.object(
                registry, "_approval_input", side_effect=TimeoutError("zzz")
            ),
        ):
            res = registry.request_send_approval(self.draft, channel="gmail", expected_value=_send_expected(self.draft))
        self.assertFalse(res["ok"])
        self.assertFalse(res["approved"])
        self.assertEqual(res["error"], "approval_timeout")
        self.assertIsNone(
            registry._find_unconsumed_approval(
                registry._content_hash(self.draft)
            )
        )


class ApprovalChannelBindingTests(unittest.TestCase):
    """Minor: an approval record is bound to its channel — a gmail
    approval must not authorize a send on any other channel."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._patch = mock.patch.object(
            registry, "CONSENT_LOG", Path(self.tmp.name) / "consent.jsonl"
        )
        self._patch.start()
        self.addCleanup(self._patch.stop)
        self.draft = {
            "to": "recruiter@example.com",
            "subject": "Following up",
            "body": "Hi — checking in.",
        }
        with (
            mock.patch.object(registry, "_stdin_is_tty", return_value=True),
            mock.patch.object(
                registry, "_approval_input", return_value=_send_expected(self.draft)
            ),
        ):
            res = registry.request_send_approval(self.draft, channel="gmail", expected_value=_send_expected(self.draft))
        self.assertTrue(res["ok"], res)
        self.aid = res["approval_id"]
        self.chash = registry._content_hash(self.draft)

    def test_validate_approval_channel_mismatch(self):
        self.assertIsNone(
            registry._validate_approval(self.aid, self.chash, channel="gmail")
        )
        self.assertEqual(
            registry._validate_approval(
                self.aid, self.chash, channel="whatsapp"
            ),
            "approval_channel_mismatch",
        )

    def test_authorize_send_channel_mismatch(self):
        _, refusal = registry.authorize_send(
            self.draft, channel="whatsapp", approval_id=self.aid,
            expected_value=_send_expected(self.draft),
        )
        self.assertEqual(refusal["error"], "approval_channel_mismatch")
        self.assertFalse(refusal["sent"])
        self.assertIn("channel", refusal["instructions"].lower())

    def test_find_unconsumed_approval_binds_channel(self):
        self.assertEqual(
            registry._find_unconsumed_approval(self.chash, channel="gmail"),
            self.aid,
        )
        self.assertIsNone(
            registry._find_unconsumed_approval(
                self.chash, channel="whatsapp"
            )
        )
        # Unbound lookup (legacy callers) still finds it.
        self.assertEqual(
            registry._find_unconsumed_approval(self.chash), self.aid
        )

    def test_cross_channel_send_refused_even_if_enabled(self):
        registry.enable_channel("whatsapp", confirm=True, via="cli-wizard")
        channel = registry.GmailChannel()
        out = channel.send_followup(self.draft, approval_id=self.aid)
        # GmailChannel is gmail-bound; the gmail approval authorizes the
        # gmail send only after enablement — here gmail is not enabled.
        self.assertFalse(out["sent"])


class ChannelCaseNormalizationTests(unittest.TestCase):
    """Minor: channel names are case-normalized in is_enabled and
    consent_history (the store records lowercase)."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._patch = mock.patch.object(
            registry, "CONSENT_LOG", Path(self.tmp.name) / "consent.jsonl"
        )
        self._patch.start()
        self.addCleanup(self._patch.stop)

    def test_is_enabled_case_insensitive(self):
        registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        self.assertTrue(registry.is_enabled("GMAIL"))
        self.assertTrue(registry.is_enabled(" Gmail "))
        registry.disable_channel("GMAIL", via="cli-wizard")
        self.assertFalse(registry.is_enabled("gmail"))

    def test_consent_history_case_insensitive(self):
        registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        self.assertEqual(len(registry.consent_history("Gmail")), 1)
        self.assertEqual(len(registry.consent_history("GMAIL")), 1)


class DraftValidationTests(unittest.TestCase):
    """Minor: send_followup inputs are validated — a None draft yields a
    clear error, not an AttributeError."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._patch = mock.patch.object(
            registry, "CONSENT_LOG", Path(self.tmp.name) / "consent.jsonl"
        )
        self._patch.start()
        self.addCleanup(self._patch.stop)
        self.channel = registry.GmailChannel()

    def test_channel_send_followup_none_draft(self):
        registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        out = self.channel.send_followup(None)
        self.assertFalse(out["sent"])
        self.assertEqual(out["error"], "invalid_draft")
        self.assertIn("instructions", out)

    def test_channel_send_followup_non_dict_draft(self):
        out = self.channel.send_followup("not-a-dict")
        self.assertFalse(out["sent"])
        self.assertEqual(out["error"], "invalid_draft")

    def test_authorize_send_none_draft(self):
        got, refusal = registry.authorize_send(None, channel="gmail", expected_value="x")
        self.assertIsNone(got)
        self.assertEqual(refusal["error"], "invalid_draft")


class ApprovalPromptTimeoutTests(unittest.TestCase):
    """Minor: the approval prompt abandons after a timeout — a user who
    walks away must not hang the process forever."""

    def test_approval_input_timeout_raises(self):
        with mock.patch("select.select", return_value=([], [], [])):
            with self.assertRaises(TimeoutError):
                registry._approval_input("Type send: ")
        self.assertGreater(registry.APPROVAL_PROMPT_TIMEOUT_SECONDS, 0)

    def test_approval_input_reads_line_when_ready(self):
        with (
            mock.patch(
                "select.select", return_value=([object()], [], [])
            ),
            mock.patch.object(
                registry.sys.stdin, "readline", return_value="send\n"
            ),
        ):
            self.assertEqual(registry._approval_input("Type send: "), "send")

    def test_approval_input_eof_raises(self):
        with (
            mock.patch(
                "select.select", return_value=([object()], [], [])
            ),
            mock.patch.object(
                registry.sys.stdin, "readline", return_value=""
            ),
        ):
            with self.assertRaises(EOFError):
                registry._approval_input("Type send: ")


class ConsumedApprovalPruningTests(unittest.TestCase):
    """Minor: _CONSUMED_APPROVALS is pruned in long-lived processes —
    stale markers are dropped, live ones kept."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._patch = mock.patch.object(
            registry, "CONSENT_LOG", Path(self.tmp.name) / "consent.jsonl"
        )
        self._patch.start()
        self.addCleanup(self._patch.stop)
        self._saved = dict(registry._CONSUMED_APPROVALS)
        self.addCleanup(self._restore)

    def _restore(self):
        registry._CONSUMED_APPROVALS.clear()
        registry._CONSUMED_APPROVALS.update(self._saved)

    def test_stale_markers_pruned_live_kept(self):
        import time as _time

        stale = "stale-nonce"
        live = "live-nonce"
        registry._CONSUMED_APPROVALS[stale] = (
            _time.time() - 3 * registry.APPROVAL_TTL_SECONDS
        )
        registry._CONSUMED_APPROVALS[live] = _time.time()
        registry.consume_approval("fresh-nonce", channel="gmail")
        self.assertNotIn(stale, registry._CONSUMED_APPROVALS)
        self.assertIn(live, registry._CONSUMED_APPROVALS)
        self.assertIn("fresh-nonce", registry._CONSUMED_APPROVALS)

    def test_prune_is_idempotent_and_bounded(self):
        import time as _time

        for i in range(5):
            registry._CONSUMED_APPROVALS[f"old-{i}"] = (
                _time.time() - 10 * registry.APPROVAL_TTL_SECONDS
            )
        registry._prune_consumed_approvals()
        for i in range(5):
            self.assertNotIn(f"old-{i}", registry._CONSUMED_APPROVALS)
        registry._prune_consumed_approvals()  # second pass: no-op


class EnableDisableHonestyTests(unittest.TestCase):
    """Minor + Blocker 1b: the 'enabled' field in enable/disable results
    must always report the channel's ACTUAL state — never a blanket
    enabled:true on failure, and never silently diverging from
    is_enabled()."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._patch = mock.patch.object(
            registry, "CONSENT_LOG", Path(self.tmp.name) / "consent.jsonl"
        )
        self._patch.start()
        self.addCleanup(self._patch.stop)

    def test_disable_invalid_via_on_disabled_channel_reports_disabled(self):
        result = registry.disable_channel("gmail", via="bogus-source")
        self.assertFalse(result["ok"])
        self.assertIn("invalid_via", result["error"])
        self.assertFalse(result["enabled"])  # was enabled:true — a lie
        self.assertEqual(result["enabled"], registry.is_enabled("gmail"))

    def test_disable_invalid_via_on_enabled_channel_reports_enabled(self):
        registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        result = registry.disable_channel("gmail", via="bogus-source")
        self.assertFalse(result["ok"])
        self.assertTrue(result["enabled"])  # the disable did not happen
        self.assertTrue(registry.is_enabled("gmail"))

    def test_disable_write_failure_reports_actual_state(self):
        registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        with mock.patch("os.open", side_effect=OSError("EIO")):
            result = registry.disable_channel("gmail", via="cli-wizard")
        self.assertFalse(result["ok"])
        self.assertIn("consent_write_failed", result["error"])
        # The write failed; os.open is also patched for the state check,
        # which fails closed — report matches is_enabled().
        self.assertEqual(result["enabled"], registry.is_enabled("gmail"))

    def test_enable_invalid_via_reports_actual_state(self):
        registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        result = registry.enable_channel(
            "gmail", confirm=True, via="bogus-source"
        )
        self.assertFalse(result["ok"])
        self.assertTrue(result["enabled"])  # still enabled, not a failure
        self.assertTrue(registry.is_enabled("gmail"))

    def test_enable_result_never_diverges_from_is_enabled(self):
        # Clean store: agree.
        result = registry.enable_channel(
            "gmail", confirm=True, via="cli-wizard"
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["enabled"], registry.is_enabled("gmail"))
        # Torn store: agree (False), with the divergence surfaced loudly.
        with registry.CONSENT_LOG.open("a", encoding="utf-8") as fh:
            fh.write("torn\n")
        with self.assertLogs("veto-mcp.i09.channels", level="ERROR"):
            result = registry.enable_channel(
                "discord", confirm=True, via="cli-wizard"
            )
        self.assertEqual(result["enabled"], registry.is_enabled("discord"))
        self.assertFalse(result["enabled"])
        self.assertIn("integrity_warning", result)


class DecisionsDocFieldsTests(unittest.TestCase):
    """M1: DECISIONS.md must carry explicit scope_driven: and product_goal:
    fields on every decision entry (Rule 3/4 mechanical checks)."""

    def test_every_entry_has_scope_and_product_goal(self):
        doc = Path(registry.__file__).parent / "DECISIONS.md"
        text = doc.read_text(encoding="utf-8")
        entries = [
            block
            for block in text.split("\n## ")[1:]
        ]
        self.assertGreaterEqual(len(entries), 2)
        for entry in entries:
            title = entry.splitlines()[0]
            self.assertIn(
                "scope_driven:", entry,
                f"entry {title!r} lacks scope_driven:",
            )
            self.assertIn(
                "product_goal:", entry,
                f"entry {title!r} lacks product_goal:",
            )

    def test_residual_enablement_names_tradeoff_and_human_gate(self):
        doc = Path(registry.__file__).parent / "DECISIONS.md"
        text = doc.read_text(encoding="utf-8")
        residual = text.split("Residual question")[1].split("## ")[0]
        self.assertIn("Trade-off", residual)
        self.assertIn("Human gate", residual)
        self.assertIn("Paul", residual)


class ApprovalDisplaySanitizationTests(unittest.TestCase):
    """BLOCKER 1: the approval display is the trust boundary — a hostile
    draft must not rewrite the terminal (ANSI cursor movement
    overwriting the To: line, or a raw newline injecting a fake To:
    line), while the approval record binds the TRUE content."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._patch = mock.patch.object(
            registry, "CONSENT_LOG", Path(self.tmp.name) / "consent.jsonl"
        )
        self._patch.start()
        self.addCleanup(self._patch.stop)

    def _approve_capturing_display(self, draft, answer=None):
        buf = io.StringIO()
        expected = _send_expected(draft)
        if answer is None:
            answer = expected
        with (
            mock.patch.object(registry, "_stdin_is_tty", return_value=True),
            mock.patch.object(
                registry, "_approval_input", return_value=answer
            ),
            contextlib.redirect_stdout(buf),
        ):
            res = registry.request_send_approval(
                draft, channel="gmail", expected_value=expected
            )
        return res, buf.getvalue()

    def test_ansi_and_newline_injection_cannot_rewrite_display(self):
        evil = {
            "to": "boss@trusted.example\nTo:      attacker@evil.example",
            "subject": "Q3 planning \x1b]0;pwned\x07",
            "body": "Hello,\x1b[2A\x1b[Klook up!",
        }
        res, out = self._approve_capturing_display(evil)
        self.assertTrue(res["ok"], res)
        # No escape byte reaches the terminal, ever.
        self.assertNotIn("\x1b", out)
        # The newline injection became visible text: exactly ONE To:
        # line, and the attacker's address is shown as (sanitized) data
        # on it — never as a second header line.
        to_lines = [ln for ln in out.splitlines() if ln.startswith("To:")]
        self.assertEqual(len(to_lines), 1)
        self.assertIn("boss@trusted.example", to_lines[0])
        self.assertIn("attacker@evil.example", to_lines[0])
        self.assertIn("\\n", to_lines[0])
        # The approval record binds the TRUE content, not the display.
        self.assertEqual(res["content_hash"], registry._content_hash(evil))

    def test_sanitization_is_display_only_true_payload_sent(self):
        """The transport receives the true unsanitized draft bytes."""
        registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        draft = {
            "to": "recruiter@example.com",
            "subject": "Following up",
            "body": "Hi — checking in.\x1b[31mred\x1b[0m",
        }
        res, out = self._approve_capturing_display(draft)
        self.assertTrue(res["ok"], res)
        self.assertNotIn("\x1b", out)  # display sanitized
        import email_sync

        with (
            mock.patch.object(
                email_sync, "_gmail_connected", return_value=True
            ),
            mock.patch.object(
                email_sync, "_gmail_send", return_value={"ok": True}
            ) as m,
        ):
            sent = email_sync.send_followup(
                dict(draft), approval_id=res["approval_id"]
            )
        self.assertTrue(sent["sent"])
        # The TRUE body — escape bytes intact — reached the transport.
        m.assert_called_once_with(
            "recruiter@example.com",
            "Following up",
            "Hi — checking in.\x1b[31mred\x1b[0m",
        )

    def test_control_characters_become_visible_placeholders(self):
        self.assertEqual(
            registry._sanitize_display("a\x00b\x07c"), "a\ufffdb\ufffdc"
        )
        self.assertEqual(registry._sanitize_display("x\ry"), "x\\ry")
        self.assertEqual(registry._sanitize_display("p\nq"), "p\\nq")
        self.assertEqual(
            registry._sanitize_display("plain — ok"), "plain — ok"
        )


class QuarantineConcurrencyTests(unittest.TestCase):
    """MAJOR 2: an entry appended by another process between quarantine's
    read and rewrite must never be silently lost."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.log = Path(self.tmp.name) / "consent.jsonl"
        self._patch = mock.patch.object(registry, "CONSENT_LOG", self.log)
        self._patch.start()
        self.addCleanup(self._patch.stop)

    def test_concurrent_append_during_quarantine_is_not_lost(self):
        registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        with self.log.open("a", encoding="utf-8") as fh:
            fh.write("torn line\n")

        raced = threading.Event()
        release = threading.Event()
        real_replace = os.replace

        def gated_replace(src, dst):
            # Quarantine holds the store lock here, mid-rewrite.
            raced.set()
            self.assertTrue(release.wait(10), "test harness stuck")
            return real_replace(src, dst)

        appended = threading.Event()

        def concurrent_append():
            # Wait until quarantine definitely holds the lock, then append
            # through the public path: it must block until the lock is
            # released, then land in the NEW log file — never in the
            # replaced-away old inode.
            self.assertTrue(
                raced.wait(10), "quarantine never reached replace"
            )
            registry._append_consent(
                {"action": "disable", "channel": "gmail", "via": "api"}
            )
            appended.set()

        t = threading.Thread(target=concurrent_append, daemon=True)
        release_timer = threading.Timer(1.0, release.set)
        try:
            with mock.patch("os.replace", side_effect=gated_replace):
                t.start()
                release_timer.start()
                result = registry.quarantine_consent_log()
        finally:
            release.set()  # never leave the harness wedged
            release_timer.cancel()
        t.join(10)
        self.assertTrue(appended.is_set(), "concurrent append never landed")

        self.assertTrue(result["ok"], result)
        self.assertTrue(result["integrity_ok"])
        entries, integrity_ok = registry.consent_history(with_integrity=True)
        self.assertTrue(integrity_ok)
        disables = [
            e
            for e in entries
            if e.get("action") == "disable" and e.get("channel") == "gmail"
        ]
        self.assertEqual(
            len(disables), 1, "the concurrently-appended entry was lost"
        )
        self.assertFalse(registry.is_enabled("gmail"))


class AtomicClaimRaceTests(unittest.TestCase):
    """MAJOR 4: validate-then-consume is atomic under the store lock —
    two racers on one approval produce exactly one winner."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._patch = mock.patch.object(
            registry, "CONSENT_LOG", Path(self.tmp.name) / "consent.jsonl"
        )
        self._patch.start()
        self.addCleanup(self._patch.stop)
        self.draft = {
            "to": "recruiter@example.com",
            "subject": "Following up",
            "body": "Hi — checking in.",
        }

    def _mint(self):
        with (
            mock.patch.object(registry, "_stdin_is_tty", return_value=True),
            mock.patch.object(
                registry, "_approval_input", return_value=_send_expected(self.draft)
            ),
        ):
            res = registry.request_send_approval(self.draft, channel="gmail", expected_value=_send_expected(self.draft))
        self.assertTrue(res["ok"], res)
        return res["approval_id"]

    def test_concurrent_authorize_send_single_winner(self):
        aid = self._mint()
        entered = threading.Event()
        release = threading.Event()
        real_validate = registry._validate_approval

        def slow_validate(approval_id, content_hash, channel=None):
            entered.set()  # first racer is inside validation, lock held
            self.assertTrue(release.wait(10), "test harness stuck")
            return real_validate(approval_id, content_hash, channel=channel)

        results = []

        def racer():
            results.append(
                registry.authorize_send(
                    self.draft, channel="gmail", approval_id=aid,
                    expected_value=_send_expected(self.draft),
                )
            )

        with mock.patch.object(
            registry, "_validate_approval", side_effect=slow_validate
        ):
            t1 = threading.Thread(target=racer, daemon=True)
            t1.start()
            self.assertTrue(entered.wait(10), "first racer never validated")
            t2 = threading.Thread(target=racer, daemon=True)
            t2.start()
            time.sleep(0.5)  # t2 must NOT finish while t1 holds the lock
            self.assertEqual(
                results,
                [],
                "second authorize_send slipped past the claim lock",
            )
            release.set()
            t1.join(10)
            t2.join(10)

        self.assertEqual(len(results), 2)
        winners = [r for r in results if r[1] is None]
        losers = [r for r in results if r[1] is not None]
        self.assertEqual(len(winners), 1, "expected exactly one claim")
        self.assertEqual(len(losers), 1)
        self.assertEqual(losers[0][1]["error"], "approval_already_used")
        self.assertFalse(losers[0][1]["sent"])


class QuarantineDedupTests(unittest.TestCase):
    """MINOR 6: a re-run after a rewrite failure must not duplicate
    quarantine records."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.log = Path(self.tmp.name) / "consent.jsonl"
        self._patch = mock.patch.object(registry, "CONSENT_LOG", self.log)
        self._patch.start()
        self.addCleanup(self._patch.stop)

    def test_rewrite_failure_then_rerun_no_duplicates(self):
        registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        with self.log.open("a", encoding="utf-8") as fh:
            fh.write("torn\n")
        real_replace = os.replace
        calls = {"n": 0}

        def fail_once(src, dst):
            calls["n"] += 1
            if calls["n"] == 1:
                raise OSError("EROFS: read-only filesystem")
            return real_replace(src, dst)

        with mock.patch("os.replace", side_effect=fail_once):
            first = registry.quarantine_consent_log()
        self.assertFalse(first["ok"])
        self.assertIn("consent_log_rewrite_failed", first["error"])
        second = registry.quarantine_consent_log()
        self.assertTrue(second["ok"], second)
        self.assertTrue(second["integrity_ok"])
        qpath = Path(second["quarantine_file"])
        records = [
            json.loads(line)
            for line in qpath.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        keys = [(r["line_no"], r["original_line"]) for r in records]
        self.assertEqual(
            len(keys), len(set(keys)), f"duplicate quarantine records: {keys}"
        )
        self.assertEqual(len(records), 1)


class QuarantineSigningTests(unittest.TestCase):
    """MINOR 8: quarantine records are HMAC-signed with the machine key;
    tampering is detectable."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.log = Path(self.tmp.name) / "consent.jsonl"
        self._patch = mock.patch.object(registry, "CONSENT_LOG", self.log)
        self._patch.start()
        self.addCleanup(self._patch.stop)

    def _quarantine_one_torn(self):
        registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        with self.log.open("a", encoding="utf-8") as fh:
            fh.write("torn\n")
        result = registry.quarantine_consent_log()
        self.assertTrue(result["ok"], result)
        return [
            json.loads(line)
            for line in Path(result["quarantine_file"])
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]

    def test_quarantine_records_carry_valid_macs(self):
        records = self._quarantine_one_torn()
        self.assertEqual(len(records), 1)
        key = registry._load_or_create_key()
        for rec in records:
            self.assertIn("mac", rec)
            entry, problem = registry._verify_entry(rec, key)
            self.assertEqual(
                problem, "", f"quarantine record failed verification: {problem}"
            )
            self.assertIsNotNone(entry)

    def test_tampered_quarantine_record_detected(self):
        records = self._quarantine_one_torn()
        key = registry._load_or_create_key()
        tampered = dict(records[0])
        tampered["original_line"] = records[0]["original_line"] + " -- forged"
        entry, problem = registry._verify_entry(tampered, key)
        self.assertIsNone(entry)
        self.assertIn("signature mismatch", problem)


class QuarantineForceGateTests(unittest.TestCase):
    """MINOR 12: a wholesale-unverifiable log (lost key, not a torn line)
    is refused loudly until explicitly forced — quarantining it would
    archive every entry permanently."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.log = Path(self.tmp.name) / "consent.jsonl"
        self._patch = mock.patch.object(registry, "CONSENT_LOG", self.log)
        self._patch.start()
        self.addCleanup(self._patch.stop)

    def test_wholesale_unverifiable_log_requires_force(self):
        registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        registry._consent_key_path().unlink()  # key merely LOST (not rotated)
        with self.assertLogs("veto-mcp.i09.channels", level="ERROR") as cm:
            refused = registry.quarantine_consent_log()
        self.assertFalse(refused["ok"])
        self.assertEqual(refused["error"], "quarantine_requires_confirmation")
        self.assertIn("backup", refused["instructions"].lower())
        self.assertIn("force", refused["instructions"].lower())
        self.assertIn("QUARANTINE REFUSED", "\n".join(cm.output))
        # Nothing moved: the log still holds the original lines.
        self.assertIn("gmail", self.log.read_text(encoding="utf-8"))
        self.assertIsNone(refused["quarantine_file"])
        # Explicit confirmation proceeds.
        forced = registry.quarantine_consent_log(force=True)
        self.assertTrue(forced["ok"], forced)
        self.assertTrue(forced["integrity_ok"])
        self.assertGreaterEqual(forced["quarantined"], 1)

    def test_partial_quarantine_needs_no_force(self):
        registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        with self.log.open("a", encoding="utf-8") as fh:
            fh.write("torn\n")
        result = registry.quarantine_consent_log()
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["quarantined"], 1)


class ApprovalAbortTests(unittest.TestCase):
    """MINOR 10: the approval_aborted branch (EOF / KeyboardInterrupt in
    request_send_approval) and the _stdin_is_tty exception path."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._patch = mock.patch.object(
            registry, "CONSENT_LOG", Path(self.tmp.name) / "consent.jsonl"
        )
        self._patch.start()
        self.addCleanup(self._patch.stop)
        self.draft = {
            "to": "recruiter@example.com",
            "subject": "Following up",
            "body": "Hi — checking in.",
        }

    def _tty(self):
        return mock.patch.object(registry, "_stdin_is_tty", return_value=True)

    def test_eof_aborts_approval(self):
        with (
            self._tty(),
            mock.patch.object(
                registry, "_approval_input", side_effect=EOFError("eof")
            ),
        ):
            res = registry.request_send_approval(self.draft, channel="gmail", expected_value=_send_expected(self.draft))
        self.assertFalse(res["ok"])
        self.assertFalse(res["approved"])
        self.assertEqual(res["error"], "approval_aborted")

    def test_keyboard_interrupt_aborts_approval(self):
        with (
            self._tty(),
            mock.patch.object(
                registry, "_approval_input", side_effect=KeyboardInterrupt()
            ),
        ):
            res = registry.request_send_approval(self.draft, channel="gmail", expected_value=_send_expected(self.draft))
        self.assertFalse(res["ok"])
        self.assertFalse(res["approved"])
        self.assertEqual(res["error"], "approval_aborted")
        # No approval record was minted for the aborted prompt.
        self.assertIsNone(
            registry._find_unconsumed_approval(
                registry._content_hash(self.draft)
            )
        )

    def test_stdin_is_tty_exception_fails_closed(self):
        broken = mock.Mock()
        broken.isatty.side_effect = OSError("no tty device")
        with mock.patch.object(registry.sys, "stdin", broken):
            self.assertFalse(registry._stdin_is_tty())
        with mock.patch.object(registry.sys, "stdin", broken):
            res = registry.request_send_approval(self.draft, channel="gmail", expected_value=_send_expected(self.draft))
        self.assertFalse(res["ok"])
        self.assertEqual(res["error"], "not_interactive")


class ApprovalChannelCaseNormalizationTests(unittest.TestCase):
    """MINOR 11: channel names normalize consistently across the approval
    boundary — authorize_send(channel="Gmail") matches an approval
    recorded for "gmail"."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._patch = mock.patch.object(
            registry, "CONSENT_LOG", Path(self.tmp.name) / "consent.jsonl"
        )
        self._patch.start()
        self.addCleanup(self._patch.stop)
        self.draft = {
            "to": "recruiter@example.com",
            "subject": "Following up",
            "body": "Hi — checking in.",
        }

    def test_mixed_case_channel_binds_end_to_end(self):
        with (
            mock.patch.object(registry, "_stdin_is_tty", return_value=True),
            mock.patch.object(
                registry, "_approval_input", return_value=_send_expected(self.draft)
            ),
        ):
            res = registry.request_send_approval(self.draft, channel="Gmail", expected_value=_send_expected(self.draft))
        self.assertTrue(res["ok"], res)
        self.assertEqual(res["channel"], "gmail")  # stored canonical
        aid = res["approval_id"]
        chash = registry._content_hash(self.draft)
        # Validation matches regardless of case on either side.
        self.assertIsNone(
            registry._validate_approval(aid, chash, channel="GMAIL")
        )
        self.assertIsNone(
            registry._validate_approval(aid, chash, channel="gmail")
        )
        self.assertEqual(
            registry._find_unconsumed_approval(chash, channel=" Gmail "), aid
        )
        # authorize_send claims it under a differently-cased channel.
        got, refusal = registry.authorize_send(
            self.draft, channel="GMAIL", approval_id=aid,
            expected_value=_send_expected(self.draft),
        )
        self.assertIsNone(refusal)
        self.assertEqual(got, aid)


class AtomicClaimWriteFailureTests(unittest.TestCase):
    """MAJOR 1 (round 4): the atomic claim fails CLOSED when the
    consumption-marker write fails.

    A marker that did not persist is never reported as a successful
    claim: authorize_send refuses with the named refusal
    ``approval_consume_failed``, the in-process mark is rolled back so a
    retry can claim the approval, and a second process reading the same
    log cannot double-spend."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._patch = mock.patch.object(
            registry, "CONSENT_LOG", Path(self.tmp.name) / "consent.jsonl"
        )
        self._patch.start()
        self.addCleanup(self._patch.stop)
        self.draft = {
            "to": "recruiter@example.com",
            "subject": "Following up",
            "body": "Hi — checking in.",
        }
        self._saved_marks = dict(registry._CONSUMED_APPROVALS)
        self.addCleanup(self._restore_marks)

    def _restore_marks(self):
        registry._CONSUMED_APPROVALS.clear()
        registry._CONSUMED_APPROVALS.update(self._saved_marks)

    def _mint(self):
        with (
            mock.patch.object(registry, "_stdin_is_tty", return_value=True),
            mock.patch.object(
                registry, "_approval_input", return_value=_send_expected(self.draft)
            ),
        ):
            res = registry.request_send_approval(self.draft, channel="gmail", expected_value=_send_expected(self.draft))
        self.assertTrue(res["ok"], res)
        return res["approval_id"]

    def _fail_consumption_writes(self):
        """Only approval_consumed marker writes raise OSError."""
        real = registry._append_consent_locked

        def gated(entry):
            if entry.get("action") == "approval_consumed":
                raise OSError("EIO: disk full")
            return real(entry)

        return mock.patch.object(
            registry, "_append_consent_locked", side_effect=gated
        )

    def test_consumption_write_failure_refuses_with_named_refusal(self):
        aid = self._mint()
        with self._fail_consumption_writes():
            got, refusal = registry.authorize_send(
                self.draft, channel="gmail", approval_id=aid,
                expected_value=_send_expected(self.draft),
            )
        self.assertIsNone(got)  # NOT reported as success
        self.assertEqual(refusal["error"], "approval_consume_failed")
        self.assertFalse(refusal["sent"])
        self.assertIn("instructions", refusal)
        # In-process mark rolled back: the approval is NOT spent here.
        self.assertNotIn(aid, registry._CONSUMED_APPROVALS)
        # No marker persisted in the log either.
        consumed = [
            e
            for e in registry.consent_history()
            if e.get("action") == "approval_consumed"
        ]
        self.assertEqual(consumed, [])

    def test_failed_claim_leaves_approval_consumable_on_retry(self):
        aid = self._mint()
        with self._fail_consumption_writes():
            _, refusal = registry.authorize_send(
                self.draft, channel="gmail", approval_id=aid,
                expected_value=_send_expected(self.draft),
            )
        self.assertEqual(refusal["error"], "approval_consume_failed")
        # Retry with a healthy store: the approval is still valid and the
        # claim now succeeds.
        got, refusal = registry.authorize_send(
            self.draft, channel="gmail", approval_id=aid,
            expected_value=_send_expected(self.draft),
        )
        self.assertIsNone(refusal)
        self.assertEqual(got, aid)

    def test_failed_claim_found_on_file_path_refuses(self):
        """The no-approval_id path (fresh approval on file) also fails the
        claim rather than reporting success."""
        self._mint()
        with self._fail_consumption_writes():
            got, refusal = registry.authorize_send(
                self.draft, channel="gmail",
                expected_value=_send_expected(self.draft),
            )
        self.assertIsNone(got)
        self.assertEqual(refusal["error"], "approval_consume_failed")
        self.assertFalse(refusal["sent"])

    def test_failed_claim_interactive_mint_path_refuses(self):
        """authorize_send's own interactive mint: the mint lands, the claim
        fails -> refused, never success."""
        with (
            mock.patch.object(registry, "_stdin_is_tty", return_value=True),
            mock.patch.object(
                registry,
                "_approval_input",
                return_value=_send_expected(self.draft),
            ),
            self._fail_consumption_writes(),
        ):
            got, refusal = registry.authorize_send(
                self.draft, channel="gmail",
                expected_value=_send_expected(self.draft),
            )
        self.assertIsNone(got)
        self.assertEqual(refusal["error"], "approval_consume_failed")
        self.assertFalse(refusal["sent"])

    def test_second_process_cannot_double_spend_after_failed_claim(self):
        aid = self._mint()
        # "Process A": the claim's marker write fails -> refused.
        with self._fail_consumption_writes():
            got, refusal = registry.authorize_send(
                self.draft, channel="gmail", approval_id=aid,
                expected_value=_send_expected(self.draft),
            )
        self.assertEqual(refusal["error"], "approval_consume_failed")
        # "Process A" retries on a healthy store and spends the approval:
        # exactly one approval_consumed marker lands in the log.
        got, refusal = registry.authorize_send(
            self.draft, channel="gmail", approval_id=aid,
            expected_value=_send_expected(self.draft),
        )
        self.assertEqual(got, aid)
        # "Process B": fresh in-process state, same on-disk log — it must
        # see the persisted marker and refuse: no double-spend.
        saved = dict(registry._CONSUMED_APPROVALS)
        registry._CONSUMED_APPROVALS.clear()
        try:
            got2, refusal2 = registry.authorize_send(
                self.draft, channel="gmail", approval_id=aid,
                expected_value=_send_expected(self.draft),
            )
        finally:
            registry._CONSUMED_APPROVALS.clear()
            registry._CONSUMED_APPROVALS.update(saved)
        self.assertIsNone(got2)
        self.assertEqual(refusal2["error"], "approval_already_used")
        self.assertFalse(refusal2["sent"])

    def test_consume_approval_write_failure_keeps_in_process_mark(self):
        """The transport-layer consume_approval keeps its pinned contract:
        a failed marker write is ERROR-logged (never raised), and the
        in-process mark is KEPT — same-process reuse stays blocked. (The
        atomic claim inside authorize_send instead FAILS the claim; see
        TestConsumeMarkerFailure.*.)"""
        aid = self._mint()
        with self._fail_consumption_writes():
            with self.assertLogs("veto-mcp.i09.channels", level="ERROR"):
                registry.consume_approval(aid, channel="gmail")
        # Mark kept: same-process authorize_send is refused as reused.
        got, refusal = registry.authorize_send(
            self.draft, channel="gmail", approval_id=aid,
            expected_value=_send_expected(self.draft),
        )
        self.assertIsNone(got)
        self.assertEqual(refusal["error"], "approval_already_used")


class QuarantineResultShapeTests(unittest.TestCase):
    """MINOR 3: every quarantine_consent_log failure branch returns the
    RECOVERY.md-documented keys: integrity_ok, reasons, instructions."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.log = Path(self.tmp.name) / "consent.jsonl"
        self._patch = mock.patch.object(registry, "CONSENT_LOG", self.log)
        self._patch.start()
        self.addCleanup(self._patch.stop)

    def _assert_failure_shape(self, result, error_prefix):
        self.assertFalse(result["ok"])
        self.assertIn(error_prefix, result["error"])
        for key in ("integrity_ok", "reasons", "instructions"):
            self.assertIn(key, result, f"missing {key} in {result}")
        self.assertIsInstance(result["reasons"], dict)
        self.assertTrue(result["instructions"])

    def _tear(self):
        registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        with self.log.open("a", encoding="utf-8") as fh:
            fh.write("torn\n")

    def test_lock_failure_shape(self):
        self._tear()
        with mock.patch.object(
            registry, "_consent_store_lock", side_effect=OSError("EBUSY")
        ):
            result = registry.quarantine_consent_log()
        self._assert_failure_shape(result, "quarantine_lock_failed")

    def test_lock_enter_failure_shape(self):
        # The REAL @contextmanager failure mode: _consent_store_lock()
        # constructs fine, but lock acquisition raises OSError at
        # with-entry. This must ALSO return quarantine_lock_failed —
        # never propagate as an uncaught exception.
        self._tear()

        @contextlib.contextmanager
        def _broken_lock():
            raise OSError("EACCES")
            yield

        with mock.patch.object(
            registry, "_consent_store_lock", _broken_lock
        ):
            result = registry.quarantine_consent_log()
        self._assert_failure_shape(result, "quarantine_lock_failed")

    def test_key_unavailable_shape(self):
        self._tear()
        with mock.patch.object(
            registry, "_load_or_create_key", side_effect=OSError("EIO")
        ):
            result = registry.quarantine_consent_log()
        self._assert_failure_shape(result, "consent_key_unavailable")

    def test_log_unreadable_shape(self):
        self._tear()
        with mock.patch(
            "pathlib.Path.read_text", side_effect=OSError("EIO")
        ):
            result = registry.quarantine_consent_log()
        self._assert_failure_shape(result, "consent_log_unreadable")

    def test_quarantine_write_failure_shape(self):
        self._tear()
        real_open = os.open

        def gated(path, flags, *args):
            if str(path).endswith("channel_consent.quarantine.jsonl"):
                raise OSError("EROFS: read-only filesystem")
            return real_open(path, flags, *args)

        with mock.patch("os.open", side_effect=gated):
            result = registry.quarantine_consent_log()
        self._assert_failure_shape(result, "quarantine_write_failed")
        self.assertEqual(result["reasons"], {"malformed_json": 1})

    def test_rewrite_failure_shape(self):
        self._tear()
        with mock.patch("os.replace", side_effect=OSError("EROFS")):
            result = registry.quarantine_consent_log()
        self._assert_failure_shape(result, "consent_log_rewrite_failed")
        self.assertEqual(result["reasons"], {"malformed_json": 1})

    def test_force_gate_refusal_carries_reasons(self):
        registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        registry._consent_key_path().unlink()  # key lost, not rotated
        refused = registry.quarantine_consent_log()
        self.assertFalse(refused["ok"])
        self.assertIn("reasons", refused)
        self.assertTrue(refused["reasons"])  # classification still reported
        self.assertIn("integrity_ok", refused)
        self.assertIn("instructions", refused)

    def test_noop_result_carries_documented_keys(self):
        registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        result = registry.quarantine_consent_log()
        self.assertTrue(result["ok"])
        for key in ("integrity_ok", "reasons", "quarantine_file"):
            self.assertIn(key, result)


class QuarantineAuditFailureTests(unittest.TestCase):
    """MINOR 4: a repair whose consent_quarantine audit append failed is
    re-auditable — never permanently unaudited."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.log = Path(self.tmp.name) / "consent.jsonl"
        self._patch = mock.patch.object(registry, "CONSENT_LOG", self.log)
        self._patch.start()
        self.addCleanup(self._patch.stop)

    def _fail_audit_writes(self):
        real = registry._append_consent_locked

        def gated(entry):
            if entry.get("action") == "consent_quarantine":
                raise OSError("EIO: disk full")
            return real(entry)

        return mock.patch.object(
            registry, "_append_consent_locked", side_effect=gated
        )

    def test_audit_write_failure_returns_reaudit_instructions(self):
        registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        with self.log.open("a", encoding="utf-8") as fh:
            fh.write("torn\n")
        with self._fail_audit_writes():
            result = registry.quarantine_consent_log()
        self.assertFalse(result["ok"])
        self.assertIn("quarantine_audit_write_failed", result["error"])
        for key in ("integrity_ok", "reasons", "instructions"):
            self.assertIn(key, result)
        self.assertIn("record_quarantine_audit", result["instructions"])
        # The repair itself landed: channels restored, lines moved.
        self.assertTrue(registry.is_enabled("gmail"))
        # ...but no audit entry exists yet.
        self.assertEqual(
            [
                e
                for e in registry.consent_history()
                if e.get("action") == "consent_quarantine"
            ],
            [],
        )

    def test_record_quarantine_audit_makes_promise_true(self):
        registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        with self.log.open("a", encoding="utf-8") as fh:
            fh.write("torn\n")
        with self._fail_audit_writes():
            result = registry.quarantine_consent_log()
        self.assertFalse(result["ok"])
        # Follow the instructions: re-audit with the failed result's values.
        reaudit = registry.record_quarantine_audit(
            quarantine_file=result["quarantine_file"],
            quarantined=result["quarantined"],
            reasons=result["reasons"],
        )
        self.assertTrue(reaudit["ok"], reaudit)
        audits = [
            e
            for e in registry.consent_history()
            if e.get("action") == "consent_quarantine"
        ]
        self.assertEqual(len(audits), 1)
        self.assertEqual(audits[0]["quarantined"], result["quarantined"])
        self.assertEqual(
            audits[0]["quarantine_file"], result["quarantine_file"]
        )
        self.assertEqual(audits[0]["reasons"], result["reasons"])
        _, integrity_ok = registry.consent_history(with_integrity=True)
        self.assertTrue(integrity_ok)

    def test_record_quarantine_audit_failure_is_loud(self):
        with self._fail_audit_writes():
            out = registry.record_quarantine_audit(
                quarantine_file="/tmp/q.jsonl",
                quarantined=1,
                reasons={"malformed_json": 1},
            )
        self.assertFalse(out["ok"])
        self.assertIn("quarantine_audit_write_failed", out["error"])

    def test_record_quarantine_audit_exported(self):
        self.assertIn("record_quarantine_audit", channels.__all__)


class DualTtyApprovalTests(unittest.TestCase):
    """MINOR 5: the approval prompt requires BOTH stdin and stdout to be
    TTYs — a stdin-TTY with stdout piped away is not interactive."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._patch = mock.patch.object(
            registry, "CONSENT_LOG", Path(self.tmp.name) / "consent.jsonl"
        )
        self._patch.start()
        self.addCleanup(self._patch.stop)
        self.draft = {
            "to": "recruiter@example.com",
            "subject": "Following up",
            "body": "Hi — checking in.",
        }

    def _check_interactive(self, stdin_tty, stdout_tty):
        fake_in = mock.Mock()
        fake_in.isatty.return_value = stdin_tty
        fake_out = mock.Mock()
        fake_out.isatty.return_value = stdout_tty
        with (
            mock.patch.object(registry.sys, "stdin", fake_in),
            mock.patch.object(registry.sys, "stdout", fake_out),
        ):
            return registry._stdin_is_tty()

    def test_both_ttys_required(self):
        self.assertTrue(self._check_interactive(True, True))
        self.assertFalse(self._check_interactive(True, False))
        self.assertFalse(self._check_interactive(False, True))
        self.assertFalse(self._check_interactive(False, False))

    def test_stdout_piped_refuses_approval(self):
        """stdin is a TTY but stdout is piped: the user would type 'send'
        blind, so the prompt must not run."""
        fake_in = mock.Mock()
        fake_in.isatty.return_value = True
        fake_out = mock.Mock()
        fake_out.isatty.return_value = False
        with (
            mock.patch.object(registry.sys, "stdin", fake_in),
            mock.patch.object(registry.sys, "stdout", fake_out),
        ):
            res = registry.request_send_approval(self.draft, channel="gmail", expected_value=_send_expected(self.draft))
        self.assertFalse(res["ok"])
        self.assertEqual(res["error"], "not_interactive")
        self.assertIn("stdout", res["instructions"].lower())
        # No approval record was minted.
        self.assertIsNone(
            registry._find_unconsumed_approval(
                registry._content_hash(self.draft)
            )
        )


class KeyPermissionTests(unittest.TestCase):
    """MINOR 6: a pre-existing key file with permissions more permissive
    than 0o600 is refused loudly — never used silently."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._patch = mock.patch.object(
            registry, "CONSENT_LOG", Path(self.tmp.name) / "consent.jsonl"
        )
        self._patch.start()
        self.addCleanup(self._patch.stop)

    def test_world_readable_key_refuses_to_operate(self):
        registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        key_path = registry._consent_key_path()
        os.chmod(key_path, 0o644)  # e.g. restored from a backup
        with self.assertLogs(
            "veto-mcp.i09.channels", level="ERROR"
        ) as cm:
            self.assertFalse(registry.is_enabled("gmail"))  # fail closed
        loud = "\n".join(cm.output)
        self.assertIn(str(key_path), loud)  # names the file
        # And writes refuse too: enable reports a failed operation.
        result = registry.enable_channel(
            "discord", confirm=True, via="cli-wizard"
        )
        self.assertFalse(result["ok"])
        self.assertIn("consent_write_failed", result["error"])
        # Fixing permissions restores operation — no re-key needed.
        os.chmod(key_path, 0o600)
        self.assertTrue(registry.is_enabled("gmail"))

    def test_group_readable_key_refused(self):
        registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        key_path = registry._consent_key_path()
        os.chmod(key_path, 0o640)
        with self.assertRaises(OSError) as cm:
            registry._load_or_create_key()
        self.assertIn(str(key_path), str(cm.exception))

    def test_owner_only_key_accepted(self):
        registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        key_path = registry._consent_key_path()
        os.chmod(key_path, 0o400)  # owner-read-only: not MORE permissive
        self.assertTrue(registry.is_enabled("gmail"))


if __name__ == "__main__":
    unittest.main()

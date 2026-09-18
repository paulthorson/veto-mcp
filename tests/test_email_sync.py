#!/usr/bin/env python3
"""Unit tests for email_sync.py — the Gmail skill interface is fully mocked.

No network access happens here: ``email_sync._run_gmail_cli`` is replaced
with fakes, and the applications store is pointed at a temp file.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import urljoin

import browser_apply
import email_sync


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROFILE = {
    "full_name": "Ada Lovelace",
    "first_name": "Ada",
    "email": "ada@example.com",
    "phone": "+1 555-0100",
    "skills": ["Python", "Algorithms"],
}


def _app(job_id: str, company: str, title: str, stage: str = "applied") -> dict:
    return {
        "job_id": job_id,
        "board": "greenhouse",
        "title": title,
        "company": company,
        "location": "Remote",
        "apply_url": "https://example.com/apply",
        "stage": stage,
        "stage_history": [{"stage": stage, "at": "2026-09-01T00:00:00+00:00", "note": ""}],
        "follow_up_due": None,
    }


class EmailSyncTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.apps_file = Path(self.tmp.name) / "applications.json"
        self.patch_apps = mock.patch.object(
            email_sync, "APPLICATIONS_FILE", self.apps_file
        )
        self.patch_apps.start()
        self.addCleanup(self.patch_apps.stop)
        self.patch_profile = mock.patch.object(
            email_sync, "_load_profile", return_value=dict(PROFILE)
        )
        self.patch_profile.start()
        self.addCleanup(self.patch_profile.stop)

    def write_apps(self, apps: list[dict]) -> None:
        self.apps_file.write_text(json.dumps(apps), encoding="utf-8")

    def read_apps(self) -> list[dict]:
        return json.loads(self.apps_file.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------


class TestClassifier(unittest.TestCase):
    def test_interview_invite(self) -> None:
        self.assertEqual(
            email_sync.classify_recruiter_email(
                "Interview invitation: Senior Engineer",
                "We would like to schedule a phone screen next week.",
                "Jane Recruiter <jane@acme.com>",
            ),
            "interview_invite",
        )

    def test_rejection(self) -> None:
        self.assertEqual(
            email_sync.classify_recruiter_email(
                "Update on your application",
                "After careful consideration, we've decided to move forward "
                "with other candidates. We wish you the best.",
                "talent@acme.com",
            ),
            "rejection",
        )

    def test_offer(self) -> None:
        self.assertEqual(
            email_sync.classify_recruiter_email(
                "Offer letter — Senior Engineer",
                "We are pleased to offer you the position of Senior Engineer. "
                "Please find your offer letter attached.",
                "hr@acme.com",
            ),
            "offer",
        )

    def test_recruiter_outreach(self) -> None:
        self.assertEqual(
            email_sync.classify_recruiter_email(
                "Exciting opportunity at Beta",
                "I came across your profile and was impressed by your "
                "background. Would you be open to a conversation?",
                "sam@beta.io",
            ),
            "recruiter_outreach",
        )

    def test_followup_needed(self) -> None:
        self.assertEqual(
            email_sync.classify_recruiter_email(
                "Re: Senior Engineer role",
                "Just following up on my previous note — are you still "
                "interested?",
                "sam@beta.io",
            ),
            "followup_needed",
        )

    def test_none_for_job_alert_newsletter(self) -> None:
        self.assertIsNone(
            email_sync.classify_recruiter_email(
                "Job alert: 12 new jobs for you",
                "New Python jobs in New York. Unsubscribe here.",
                "noreply@jobboard.example",
            )
        )

    def test_none_for_application_confirmation(self) -> None:
        self.assertIsNone(
            email_sync.classify_recruiter_email(
                "Application received",
                "Thank you for applying! We received your application and "
                "will review it shortly.",
                "noreply@greenhouse.io",
            )
        )

    def test_none_for_ambiguous_tie(self) -> None:
        # Both interview and rejection signals: never guess.
        self.assertIsNone(
            email_sync.classify_recruiter_email(
                "Update",
                "We will not schedule an interview; we are not moving "
                "forward at this time.",
                "talent@acme.com",
            )
        )


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------


class TestMatchToApplication(unittest.TestCase):
    APPS = [
        _app("job-1", "Acme Corp", "Senior Engineer"),
        _app("job-2", "Beta LLC", "Data Scientist"),
    ]

    def test_unambiguous_sender_domain_match(self) -> None:
        self.assertEqual(
            email_sync.match_to_application(
                {
                    "sender": "Jane <jane@acme.com>",
                    "subject": "Interview invitation",
                    "body": "Let's schedule a phone screen.",
                },
                self.APPS,
            ),
            "job-1",
        )

    def test_company_mention_in_body(self) -> None:
        self.assertEqual(
            email_sync.match_to_application(
                {
                    "sender": "recruiter@unknown-mail.com",
                    "subject": "Next steps",
                    "body": "Thanks for applying to Beta for the data role.",
                },
                self.APPS,
            ),
            "job-2",
        )

    def test_ambiguous_returns_none(self) -> None:
        apps = [
            _app("job-1", "Acme Corp", "Senior Engineer"),
            _app("job-2", "Acme Labs", "Backend Engineer"),
        ]
        self.assertIsNone(
            email_sync.match_to_application(
                {
                    "sender": "jane@acme.com",
                    "subject": "Interview invitation",
                    "body": "Phone screen next week?",
                },
                apps,
            )
        )

    def test_no_match_returns_none(self) -> None:
        self.assertIsNone(
            email_sync.match_to_application(
                {
                    "sender": "sam@gamma.dev",
                    "subject": "Opportunity",
                    "body": "I came across your profile.",
                },
                self.APPS,
            )
        )


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

TRIAGE_MSG = {
    "id": "m1",
    "from": "Jane Recruiter <jane@acme.com>",
    "subject": "Interview invitation — Senior Engineer",
    "date": "2026-09-08",
    "snippet": (
        "We would like to schedule a phone screen and a technical "
        "assessment as the next round."
    ),
}


def _connected_gmail_fake(*args):
    if args[0] == "status":
        return {"ok": True, "status": "connected"}
    if "+triage" in args:
        return [dict(TRIAGE_MSG)]
    if "+read" in args:
        return dict(TRIAGE_MSG, body=TRIAGE_MSG["snippet"] + " Please reply.")
    raise AssertionError(f"unexpected gmail call: {args}")


class TestScan(EmailSyncTestBase):
    def setUp(self) -> None:
        super().setUp()
        # Isolate the consent/approval store: the approval-bound
        # auto-apply tests must never touch the real repo consent log.
        from initiatives.i09.channels import registry

        self.consent_log = Path(self.tmp.name) / "consent.jsonl"
        patch = mock.patch.object(registry, "CONSENT_LOG", self.consent_log)
        patch.start()
        self.addCleanup(patch.stop)

    def test_scan_proposes_but_does_not_apply(self) -> None:
        self.write_apps([_app("job-1", "Acme Corp", "Senior Engineer")])
        with mock.patch.object(
            email_sync, "_run_gmail_cli", side_effect=_connected_gmail_fake
        ):
            result = email_sync.scan_recruiter_emails(
                days=14, apply_updates=False
            )
        self.assertEqual(result["scanned"], 1)
        self.assertEqual(result["matched"], 1)
        self.assertEqual(len(result["proposed_updates"]), 1)
        proposal = result["proposed_updates"][0]
        self.assertEqual(proposal["classification"], "interview_invite")
        self.assertEqual(proposal["proposed_stage"], "interviewing")
        self.assertEqual(proposal["action"], "proposed")
        self.assertEqual(result["applied_updates"], [])
        # Store untouched.
        self.assertEqual(self.read_apps()[0]["stage"], "applied")

    def test_scan_apply_updates_requires_approval_record(self) -> None:
        # m4 / Q4 governance contract: proposal-only until the user
        # approves. apply_updates=True WITHOUT a valid approval (and no
        # TTY to obtain one) degrades to propose-only. A bare boolean
        # never authorizes the write.
        self.write_apps([_app("job-1", "Acme Corp", "Senior Engineer")])
        from initiatives.i09.channels import registry

        with (
            mock.patch.object(
                email_sync, "_run_gmail_cli", side_effect=_connected_gmail_fake
            ),
            mock.patch.object(registry, "_stdin_is_tty", return_value=False),
        ):
            result = email_sync.scan_recruiter_emails(
                days=14, apply_updates=True
            )
        self.assertEqual(result["applied_updates"], [])
        proposal = result["proposed_updates"][0]
        self.assertEqual(proposal["action"], "proposed")
        self.assertIn("approval", proposal["note"].lower())
        self.assertEqual(self.read_apps()[0]["stage"], "applied")

    def test_scan_applies_with_interactive_approval(self) -> None:
        # m4: with a genuine interactive approval bound to the exact
        # proposed updates, the confident unambiguous update is applied.
        self.write_apps([_app("job-1", "Acme Corp", "Senior Engineer")])
        from initiatives.i09.channels import registry

        with (
            mock.patch.object(
                email_sync, "_run_gmail_cli", side_effect=_connected_gmail_fake
            ),
            mock.patch.object(registry, "_stdin_is_tty", return_value=True),
            # §6.2: the email-scan approval prompt requires the per-action
            # varying value — the number of updates shown in the display.
            mock.patch.object(registry, "_approval_input", return_value="1"),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            result = email_sync.scan_recruiter_emails(
                days=14, apply_updates=True
            )
        self.assertEqual(len(result["applied_updates"]), 1)
        applied = result["applied_updates"][0]
        self.assertEqual(applied["action"], "applied")
        self.assertEqual(applied["proposed_stage"], "interviewing")
        entry = self.read_apps()[0]
        self.assertEqual(entry["stage"], "interviewing")
        self.assertTrue(
            any(
                h["stage"] == "interviewing" and "email-sync" in h["note"]
                for h in entry["stage_history"]
            )
        )

    def test_scan_rejects_forged_approval_id(self) -> None:
        # m4: a self-minted approval_id authorizes nothing.
        self.write_apps([_app("job-1", "Acme Corp", "Senior Engineer")])
        with mock.patch.object(
            email_sync, "_run_gmail_cli", side_effect=_connected_gmail_fake
        ):
            result = email_sync.scan_recruiter_emails(
                days=14, apply_updates=True, approval_id="deadbeef" * 8
            )
        self.assertEqual(result["applied_updates"], [])
        self.assertEqual(result["proposed_updates"][0]["action"], "proposed")
        self.assertEqual(self.read_apps()[0]["stage"], "applied")

    def test_none_approval_contract_violation_degrades_to_proposed(
        self,
    ) -> None:
        """N2 (round 4): if authorize_send ever returned (None, None) —
        refusal None but no approval (a contract violation) — stage
        updates must fail closed even under python -O (no asserts): no
        writes, every proposal degrades to propose-only, loud log."""
        from initiatives.i09.channels import registry

        eligible = [
            {
                "application_id": "job-1",
                "current_stage": "applied",
                "proposed_stage": "interviewing",
                "classification": "interview_invite",
                "confidence": 0.92,
            }
        ]
        result = {"proposed_updates": []}
        with (
            mock.patch.object(
                registry, "authorize_send", return_value=(None, None)
            ),
            mock.patch.object(email_sync, "lifecycle") as fake_lifecycle,
            self.assertLogs(
                "veto-mcp.email_sync", level="ERROR"
            ),
        ):
            email_sync._apply_eligible_updates(eligible, result, None)
        self.assertEqual(eligible[0]["action"], "proposed")
        self.assertIn("contract violation", eligible[0]["note"])
        self.assertEqual(len(result["proposed_updates"]), 1)
        fake_lifecycle.update_stage.assert_not_called()

    def test_scan_approval_is_single_use(self) -> None:
        # m4: replaying a consumed approval is refused.
        self.write_apps([_app("job-1", "Acme Corp", "Senior Engineer")])
        from initiatives.i09.channels import registry

        with (
            mock.patch.object(
                email_sync, "_run_gmail_cli", side_effect=_connected_gmail_fake
            ),
            mock.patch.object(registry, "_stdin_is_tty", return_value=True),
            # §6.2: the email-scan approval prompt requires the per-action
            # varying value — the number of updates shown in the display.
            mock.patch.object(registry, "_approval_input", return_value="1"),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            result = email_sync.scan_recruiter_emails(
                days=14, apply_updates=True
            )
        self.assertEqual(len(result["applied_updates"]), 1)
        nonce = None
        for line in self.consent_log.read_text(encoding="utf-8").splitlines():
            entry = json.loads(line)
            if entry.get("action") == "send_approval":
                nonce = entry["nonce"]
        self.assertIsNotNone(nonce)
        # Reset the store so the same proposals are eligible again, then
        # replay the consumed approval: refused, nothing applied.
        self.write_apps([_app("job-1", "Acme Corp", "Senior Engineer")])
        with (
            mock.patch.object(
                email_sync, "_run_gmail_cli", side_effect=_connected_gmail_fake
            ),
            mock.patch.object(registry, "_stdin_is_tty", return_value=False),
        ):
            result2 = email_sync.scan_recruiter_emails(
                days=14, apply_updates=True, approval_id=nonce
            )
        self.assertEqual(result2["applied_updates"], [])
        proposal = result2["proposed_updates"][0]
        self.assertEqual(proposal["action"], "proposed")
        self.assertIn("approval", proposal["note"].lower())
        self.assertEqual(self.read_apps()[0]["stage"], "applied")

    def test_scan_skips_ambiguous_match(self) -> None:
        self.write_apps(
            [
                _app("job-1", "Acme Corp", "Senior Engineer"),
                _app("job-2", "Acme Labs", "Backend Engineer"),
            ]
        )
        with mock.patch.object(
            email_sync, "_run_gmail_cli", side_effect=_connected_gmail_fake
        ):
            result = email_sync.scan_recruiter_emails()
        self.assertEqual(result["scanned"], 1)
        self.assertEqual(result["matched"], 0)
        self.assertEqual(result["proposed_updates"], [])
        self.assertEqual(result["applied_updates"], [])

    def test_scan_reports_not_connected(self) -> None:
        with mock.patch.object(
            email_sync,
            "_run_gmail_cli",
            return_value={"ok": True, "status": "not_connected"},
        ):
            result = email_sync.scan_recruiter_emails()
        self.assertEqual(result["error"], "gmail_not_connected")
        self.assertEqual(result["scanned"], 0)


# ---------------------------------------------------------------------------
# Drafts + sending
# ---------------------------------------------------------------------------


class TestDraftFollowup(EmailSyncTestBase):
    def test_draft_check_in(self) -> None:
        self.write_apps([_app("job-1", "Acme Corp", "Senior Engineer")])
        draft = email_sync.draft_followup("job-1", kind="check_in")
        self.assertEqual(draft["application_id"], "job-1")
        self.assertIn("Senior Engineer", draft["subject"])
        self.assertIn("Acme Corp", draft["body"])
        self.assertIn("Ada Lovelace", draft["body"])
        self.assertEqual(draft["to"], "")  # no contact on file

    def test_draft_thank_you(self) -> None:
        self.write_apps([_app("job-1", "Acme Corp", "Senior Engineer")])
        draft = email_sync.draft_followup("job-1", kind="thank_you")
        self.assertIn("Thank you", draft["subject"])
        self.assertIn("Ada", draft["body"])

    def test_draft_unknown_application(self) -> None:
        self.write_apps([_app("job-1", "Acme Corp", "Senior Engineer")])
        with self.assertRaises(KeyError):
            email_sync.draft_followup("no-such-job")

    def test_draft_bad_kind(self) -> None:
        self.write_apps([_app("job-1", "Acme Corp", "Senior Engineer")])
        with self.assertRaises(ValueError):
            email_sync.draft_followup("job-1", kind="birthday_card")


class TestSendFollowup(EmailSyncTestBase):
    DRAFT = {
        "application_id": "job-1",
        "kind": "check_in",
        "to": "jane@acme.com",
        "subject": "Following up — Senior Engineer application",
        "body": "Hi, just following up.",
    }

    def setUp(self) -> None:
        super().setUp()
        # Isolate the consent/approval store: interactive-approval tests
        # must never write to the real repo consent log.
        from initiatives.i09.channels import registry

        self.consent_log = Path(self.tmp.name) / "consent.jsonl"
        patch = mock.patch.object(registry, "CONSENT_LOG", self.consent_log)
        patch.start()
        self.addCleanup(patch.stop)
        # The send boundary requires the gmail channel to be explicitly
        # enabled (defense-in-depth, M3); enable it in the isolated log.
        res = registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        self.assertTrue(res["ok"], res)

    def test_send_without_confirm_does_not_send(self) -> None:
        with mock.patch.object(email_sync, "_run_gmail_cli") as fake:
            result = email_sync.send_followup(dict(self.DRAFT), confirm=False)
        self.assertFalse(result["sent"])
        self.assertIn("draft", result)
        self.assertIn("instructions", result)
        fake.assert_not_called()

    def _simulated_approval(self, draft):
        """A genuine interactive approval, simulated for tests: TTY
        present, user types the per-send varying value (the recipient
        address exactly as shown; a fixed "send"/"yes" fails) at the
        prompt."""
        from initiatives.i09.channels import registry

        expected = str(draft.get("to") or "").strip()
        with (
            mock.patch.object(registry, "CONSENT_LOG", self.consent_log),
            mock.patch.object(registry, "_stdin_is_tty", return_value=True),
            mock.patch.object(registry, "_approval_input", return_value=expected),
        ):
            res = registry.request_send_approval(
                draft, channel="gmail", expected_value=expected
            )
        self.assertTrue(res["ok"], res)
        return res["approval_id"]

    def _no_tty(self):
        from initiatives.i09.channels import registry

        return mock.patch.object(registry, "_stdin_is_tty", return_value=False)

    def test_confirm_true_alone_does_not_send(self) -> None:
        """VETO regression: a caller-asserted confirm=True is not proof of
        approval. Without a genuine interactive approval (no TTY here),
        the send is refused and Gmail is never touched."""
        with (
            self._no_tty(),
            mock.patch.object(email_sync, "_run_gmail_cli") as fake,
        ):
            result = email_sync.send_followup(dict(self.DRAFT), confirm=True)
        self.assertFalse(result["sent"])
        self.assertEqual(result["error"], "not_interactive")
        fake.assert_not_called()

    def test_send_with_genuine_interactive_approval_sends(self) -> None:
        calls = []

        def fake(*args):
            calls.append(args)
            return {"ok": True, "status": "connected"} if args[0] == "status" else {"ok": True}

        approval_id = self._simulated_approval(self.DRAFT)
        with mock.patch.object(email_sync, "_run_gmail_cli", side_effect=fake):
            result = email_sync.send_followup(
                dict(self.DRAFT), approval_id=approval_id
            )
        self.assertTrue(result["sent"])
        self.assertEqual(result["to"], "jane@acme.com")
        send_calls = [c for c in calls if "+send" in c]
        self.assertEqual(len(send_calls), 1)
        self.assertIn("jane@acme.com", send_calls[0])

    def test_none_approval_contract_violation_refuses(self) -> None:
        """N2 (round 4): if authorize_send ever returned (None, None) —
        refusal None but no approval (a contract violation) — the send
        must fail closed even under python -O (no asserts): no Gmail
        call, named refusal, loud log."""
        from initiatives.i09.channels import registry

        with (
            mock.patch.object(
                registry, "authorize_send", return_value=(None, None)
            ),
            mock.patch.object(email_sync, "_run_gmail_cli") as fake,
            self.assertLogs(
                "veto-mcp.email_sync", level="ERROR"
            ),
        ):
            result = email_sync.send_followup(dict(self.DRAFT))
        self.assertFalse(result["sent"])
        self.assertEqual(result["error"], "approval_contract_violation")
        fake.assert_not_called()

    def test_send_with_confirm_but_no_recipient(self) -> None:
        draft = dict(self.DRAFT, to="")
        with mock.patch.object(email_sync, "_run_gmail_cli") as fake:
            result = email_sync.send_followup(draft, confirm=True)
        self.assertFalse(result["sent"])
        self.assertEqual(result["error"], "no_recipient")
        fake.assert_not_called()

    def test_send_refuses_when_channel_disabled_before_consuming_approval(
        self,
    ) -> None:
        """M3 defense-in-depth: the channel check fires BEFORE any approval
        is consumed. A valid approval survives the refusal and still works
        once the channel is re-enabled.

        B1: asserts ONLY on the public contract (authorize_send /
        send_followup behavior) — never on the registry's in-memory
        internals. The proof that the refused attempt did not consume the
        approval is that the SAME approval_id still authorizes the send
        after re-enabling (a consumed approval would be refused with
        approval_already_used).
        """
        from initiatives.i09.channels import registry

        approval_id = self._simulated_approval(self.DRAFT)
        registry.disable_channel("gmail", via="cli-wizard")
        with mock.patch.object(email_sync, "_run_gmail_cli") as fake:
            result = email_sync.send_followup(
                dict(self.DRAFT), approval_id=approval_id
            )
        self.assertFalse(result["sent"])
        self.assertEqual(result["error"], "channel_not_enabled")
        fake.assert_not_called()
        # Public-contract proof the approval survived the refusal:
        # re-enable, and the SAME approval_id completes the send. Had the
        # refused attempt consumed it, authorize_send would fail closed
        # with approval_already_used.
        registry.enable_channel("gmail", confirm=True, via="cli-wizard")

        def fake_cli(*args):
            if args[0] == "status":
                return {"ok": True, "status": "connected"}
            return {"ok": True}

        with mock.patch.object(
            email_sync, "_run_gmail_cli", side_effect=fake_cli
        ):
            result2 = email_sync.send_followup(
                dict(self.DRAFT), approval_id=approval_id
            )
        self.assertTrue(result2["sent"])
        self.assertEqual(result2["to"], "jane@acme.com")

    def test_send_rejects_header_injection_in_recipient(self) -> None:
        """m1: embedded newlines in 'to' are rejected at the send boundary."""
        for evil_to in (
            "jane@acme.com\nBcc: evil@example.com",
            "jane@acme.com\r\nBcc: evil@example.com",
        ):
            with self.subTest(to=evil_to):
                draft = dict(self.DRAFT, to=evil_to)
                with mock.patch.object(email_sync, "_run_gmail_cli") as fake:
                    result = email_sync.send_followup(draft)
                self.assertFalse(result["sent"])
                self.assertEqual(result["error"], "bad_recipient")
                fake.assert_not_called()

    def test_send_rejects_header_injection_in_subject(self) -> None:
        """m1: embedded newlines in 'subject' are rejected at the boundary."""
        for evil_subject in (
            "Hello\nX-Injected: yes",
            "Hello\r\nX-Injected: yes",
        ):
            with self.subTest(subject=evil_subject):
                draft = dict(self.DRAFT, subject=evil_subject)
                with mock.patch.object(email_sync, "_run_gmail_cli") as fake:
                    result = email_sync.send_followup(draft)
                self.assertFalse(result["sent"])
                self.assertEqual(result["error"], "bad_subject")
                fake.assert_not_called()

    def test_body_over_display_cap_refuses_before_prompt(self) -> None:
        """S4 (round 5): the approval prompt shows only the first 4000
        body chars while binding the FULL body — an over-cap body is
        refused BEFORE any interactive prompt, with the full body saved
        to a named preview file ("preview another way"). No Gmail call,
        no approval minted."""
        from initiatives.i09.channels import registry

        draft = dict(self.DRAFT, body="x" * 4001)
        buf = io.StringIO()
        with (
            mock.patch.object(
                registry, "_stdin_is_tty", return_value=True
            ),
            mock.patch.object(
                registry, "_approval_input", return_value="send"
            ) as fake_input,
            mock.patch.object(email_sync, "_run_gmail_cli") as fake,
            contextlib.redirect_stdout(buf),
        ):
            result = email_sync.send_followup(draft, confirm=True)
        self.assertFalse(result["sent"])
        self.assertEqual(result["error"], "body_exceeds_approval_display_cap")
        self.assertIn("4000", result["instructions"])
        self.assertIn("never see", result["instructions"])
        fake.assert_not_called()
        fake_input.assert_not_called()
        self.assertNotIn("Veto send approval", buf.getvalue())
        # "Preview another way": the full body was saved to the named file.
        preview = Path(
            result["instructions"].split("saved to ")[1].split(" — ")[0]
        )
        try:
            self.assertEqual(
                preview.read_text(encoding="utf-8"), "x" * 4001
            )
        finally:
            if preview.exists():
                preview.unlink()

    def test_body_at_display_cap_is_allowed(self) -> None:
        """S4 boundary: a body of exactly 4000 chars fits the prompt —
        no S4 refusal (the send then proceeds to the normal no-TTY
        refusal)."""
        draft = dict(self.DRAFT, body="x" * 4000)
        with (
            self._no_tty(),
            mock.patch.object(email_sync, "_run_gmail_cli") as fake,
        ):
            result = email_sync.send_followup(draft, confirm=True)
        self.assertNotEqual(
            result.get("error"), "body_exceeds_approval_display_cap"
        )
        fake.assert_not_called()


# ---------------------------------------------------------------------------
# Wiring contract
# ---------------------------------------------------------------------------


class FakeMCP:
    def __init__(self) -> None:
        self.tools: dict[str, object] = {}

    def tool(self):
        def deco(fn):
            self.tools[fn.__name__] = fn
            return fn

        return deco


class TestWiring(unittest.TestCase):
    def test_register_tools(self) -> None:
        mcp = FakeMCP()
        email_sync.register_tools(mcp)
        self.assertIn("scan_recruiter_emails", mcp.tools)
        self.assertIn("draft_followup_email", mcp.tools)

    def test_register_cli(self) -> None:
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers()
        email_sync.register_cli(sub)
        args = parser.parse_args(["email-scan", "--days", "7"])
        self.assertEqual(args.func, email_sync._cli_email_scan)
        self.assertEqual(args.days, 7)
        args = parser.parse_args(["email-followup", "job-1", "--kind", "nudge"])
        self.assertEqual(args.func, email_sync._cli_email_followup)
        self.assertEqual(args.kind, "nudge")


# ---------------------------------------------------------------------------
# B1: browser submit requires a consumed approval record
# ---------------------------------------------------------------------------


class _FakeDelegatingCDPSession:
    """Emulates a Chromium CDP session whose isolated world is HONEST:
    it delegates to the fake page's own DOM model (the ``evaluate``
    dispatch). Models a benign page's isolated world — the values are
    the true DOM. The forged-main-world test (``_FakeForgedPage``) uses
    a NON-delegating session instead.

    The ``veto:<marker>`` dispatch contract is shared with the page
    doubles: the marker identifies the probe, and the first CDP
    argument (the submitter reference) is forwarded so the page-side
    re-match sees the same input a real isolated world would."""

    def __init__(self, page):
        self._page = page

    def send(self, method, params=None):
        if method == "Page.getFrameTree":
            return {"frameTree": {"frame": {"id": "frame-1"}}}
        if method == "Page.createIsolatedWorld":
            return {"executionContextId": 7}
        if method == "Runtime.callFunctionOn":
            fn = (params or {}).get("functionDeclaration", "")
            args = (params or {}).get("arguments", [])
            arg = args[0].get("value") if args else None
            return {"result": {"value": self._page.evaluate(fn, arg)}}
        raise AssertionError(f"unexpected CDP method {method}")

    def detach(self):
        pass


class _FakeDelegatingCDPContext:
    """Fake Chromium browser context: exposes the CDP session factory,
    like a real Playwright ``BrowserContext`` on Chromium."""

    def __init__(self, page):
        self._page = page

    def new_cdp_session(self, page):
        return _FakeDelegatingCDPSession(self._page)


# ---------------------------------------------------------------------------
# Round 7: shared submitter model for the fake pages.
#
# The fake pages model ONE submit button. ``submitter`` is the page's
# current DOM truth about it (or None for "no submitter"); the
# marker-dispatch ``evaluate`` below emulates what the isolated-world
# probes return for that truth.
# ---------------------------------------------------------------------------


def _default_submitter():
    """A plausible submit button: <button type="submit"> with a name and
    a value, no formaction override, in form 0. ``domText`` is the
    button's ACTUAL visible text (what the text matcher reads —
    distinct from ``text``, which is the matched PATTERN's text);
    ``nodePath`` is its structural node identity (F1, round 8)."""
    return {
        "css": "button[type='submit']",
        "text": None,
        "formIndex": 0,
        "indexInForm": 0,
        "nodePath": [0, 1, 0],
        "name": "submit_btn",
        "value": "Submit application",
        "type": "submit",
        "tag": "button",
        "domText": "Submit application",
        "visible": True,
        "formaction": "",
        "formmethod": "",
        "formtarget": "",
        "formenctype": "",
    }


def _submitter_identity(submitter):
    """Identity dict the ``veto:locate-submitter`` probe returns."""
    if submitter is None:
        return {"found": False}
    return {
        "found": True,
        "css": submitter.get("css"),
        "text": submitter.get("text"),
        "formIndex": submitter.get("formIndex"),
        "indexInForm": submitter.get("indexInForm"),
        # F1 (round 8): structural node identity — the submit probe
        # compares this, never the pattern tuple.
        "nodePath": list(submitter.get("nodePath") or []),
        "name": submitter.get("name"),
        "value": submitter.get("value"),
    }


def _submitter_ref_matches(submitter, ref):
    """Emulate the page-side re-match: True when the reference still
    identifies the submitter. F1 (round 8): element identity FIRST —
    when both sides carry a ``nodePath``, the structural node
    descriptor decides (pattern-tuple agreement is not identity). A
    forged/attacker reference that no longer matches resolves to a
    miss — the submitter row is then absent. Falls back to the
    form-relative index + name/value rule when no nodePath is
    present (hand-built refs only)."""
    if submitter is None or not isinstance(ref, dict):
        return False
    ref_path = ref.get("nodePath")
    sub_path = submitter.get("nodePath")
    if ref_path is not None or sub_path is not None:
        return (
            list(ref_path or []) == list(sub_path or [])
            and bool(ref_path)
        )
    if (
        ref.get("formIndex") == submitter.get("formIndex")
        and ref.get("indexInForm") == submitter.get("indexInForm")
    ):
        return True
    return (
        bool(ref.get("name") or ref.get("value"))
        and ref.get("formIndex") == submitter.get("formIndex")
        and ref.get("name") == submitter.get("name")
        and ref.get("value") == submitter.get("value")
    )


def _fake_text_matches(dom_text, pattern_text):
    """Emulate ``veto_text_matches``: Playwright-convergent text
    matching — collapse whitespace runs, trim, lowercase, then
    substring match. A ``None``/empty pattern matches anything (the
    CSS-only rule). This is what makes the D1/D2 exploit case work:
    a button whose visible text is ``"Apply\\nnow"`` (from ``<br>``)
    matches the ``"Apply now"`` pattern, exactly like the real
    isolated-world probe and Playwright's ``:has-text()``."""
    if pattern_text is None or pattern_text == "":
        return True
    norm = lambda s: " ".join(str(s).split()).lower()
    return norm(pattern_text) in norm(dom_text or "")


def _fake_css_matches(btn, css):
    """Emulate the probe's per-CSS matching for the button dicts
    (the ``el.matches(css)`` fallback in the real probe): ``button``/
    ``input`` tags, ``[type=submit]`` (quoted or not — the attribute
    must be PRESENT: a ``<button>`` with no type attribute has IDL
    type "submit" but does NOT match ``[type='submit']``, which is
    how the D1/D2 exploit case skips the CSS-only patterns), and
    ``[role=button]`` (attribute present)."""
    tag = (btn.get("tag") or "").lower()
    css_nq = css.replace("'", "").replace('"', "")
    if "[type=submit]" in css_nq:
        if tag != "button":
            return False
        # CSS attribute selector: the attribute must be PRESENT.
        return btn.get("type_attr_present", True) and (
            btn.get("type") or ""
        ).lower() == "submit"
    if "[role=button]" in css_nq:
        return tag != "button" and tag != "input" and bool(
            btn.get("role") == "button"
        )
    if css_nq in ("button", "input"):
        return tag == css_nq
    return False


def _fake_rematch_button(buttons, ref):
    """Emulate ``veto_match_submitter``: the FIRST visible button
    matching the ref's css + normalized text (visibility = rect>0;
    in the fakes a ``visible`` flag). Returns the button or None."""
    css = (ref or {}).get("css")
    text = (ref or {}).get("text")
    for btn in buttons:
        if not btn.get("visible", True):
            continue
        if not _fake_css_matches(btn, css or ""):
            continue
        if not _fake_text_matches(btn.get("domText"), text):
            continue
        return btn
    return None


def _fake_locate_submitter_result(buttons, patterns):
    """Emulate ``veto:locate-submitter``: run each ``(css, text)``
    pattern in order against the visible DOM buttons and return the
    identity of the FIRST match — or ``{"found": False}``. ``patterns``
    is the real ``_SUBMIT_PATTERNS`` list, so the fake exercises the
    production discovery order."""
    for css, text in patterns or []:
        match = _fake_rematch_button(buttons, {"css": css, "text": text})
        if match is not None:
            return _submitter_identity(match)
    return {"found": False}


def _fake_submit_bound_form(page, identity, approved):
    """Emulate ``veto:submit-bound-form`` against the fake DOM, in the
    same order as the production probe:

    1. re-match the baseline-bound submitter from its identity;
    2. verify the re-resolved node's structural ``nodePath`` equals
       the baseline-bound path (F1: element identity is never the
       match pattern);
    3. re-read the submit-time destination/method/target/enctype
       page-side and require each to equal the approved binding
       (round 9: the bound destination includes the method);
    4. re-capture the full control set and require exact equality
       with the approved normalized rows — the production probe does
       this diff in the SAME synchronous evaluation as the submit, so
       the fake reuses the production ``_normalize_snapshot`` /
       ``_diff_snapshots`` to make the fake's comparison the
       production comparison;
    5. "submit" the bound form: record it on
       ``page.submitted_forms``. NO click event and NO submit event is
       ever dispatched — the fake never invokes the page's registered
       click/submit handlers (a hostile-handler page's handlers must
       stay unfired).

    Returns the probe-shaped result dict. The destination re-read
    goes through ``page._destination`` — the page's own
    destination-probe emulation — so pages with custom destination
    logic (multi-form) stay faithful.
    """
    def fail(reason, btn=None, destination=None, row_diff=None):
        return {
            "submitted": False,
            "reason": reason,
            "nodePath": list((btn or {}).get("nodePath") or []),
            "destination": destination,
            "row_diff": row_diff or [],
        }

    if not isinstance(identity, dict) or not isinstance(approved, dict):
        return fail("no-baseline")
    resolved = _fake_rematch_button(page._dom_buttons(), identity)
    if resolved is None:
        return fail("no-match")
    if list(resolved.get("nodePath") or []) != list(
        identity.get("nodePath") or []
    ):
        return fail("identity-changed", resolved)
    dest = page._destination(identity)
    want = approved.get("submit") or {}
    if dest is None or (dest.get("resolved") or "") != (
        want.get("resolved") or ""
    ):
        return fail("destination-changed", resolved, dest)
    if (dest.get("method") or "get") != (want.get("method") or "get"):
        return fail("method-changed", resolved, dest)
    if (dest.get("target") or "") != (want.get("formtarget") or ""):
        return fail("target-changed", resolved, dest)
    if (dest.get("enctype") or "") != (want.get("formenctype") or ""):
        return fail("enctype-changed", resolved, dest)
    current = browser_apply._normalize_snapshot(
        page._snapshot_result(identity), dest, page_url=page.url
    )
    if current is None:
        return fail("unreadable", resolved, dest)
    row_diff = browser_apply._diff_snapshots(approved, current)
    if row_diff:
        return fail("rows-changed", resolved, dest, row_diff)
    # Event-free submit: record the bound form as submitted. No DOM
    # event is dispatched and no page handler runs — by construction
    # this emulation never touches ``page.handlers``.
    record = {
        "nodePath": list(resolved.get("nodePath") or []),
        "destination": dict(dest),
        "button": resolved,
    }
    page.submitted_forms.append(record)
    page.form_submitted = True
    return {
        "submitted": True,
        "reason": "",
        "nodePath": list(resolved.get("nodePath") or []),
        "destination": dest,
    }


def _approved_binding(page, identity):
    """Build the approved normalized binding exactly as production
    does at baseline: ``_normalize_snapshot`` over the page's
    snapshot rows and its page-side destination read."""
    return browser_apply._normalize_snapshot(
        page._snapshot_result(identity),
        page._destination(identity),
        page_url=page.url,
    )


def _parse_fake_selector(selector):
    """Split a production ``_submit_pattern_selector`` rendering back
    into ``(css, text)``: ``"button:has-text('Apply now')"`` ->
    ``("button", "Apply now")``; a bare CSS selector -> ``(css,
    None)``."""
    marker = ":has-text('"
    if marker in selector and selector.endswith("')"):
        css, text = selector.split(marker, 1)
        return css, text[:-2]
    return selector, None


class _FakeLocator:
    """Playwright-locator stand-in for DISCOVERY. ``count()`` /
    ``first.is_visible()`` model the main-world selector engine
    faithfully against the fake DOM (CSS + normalized text — the
    same rule the isolated-world probes use). The locator is never
    clicked: production submits the bound form via
    ``veto:submit-bound-form`` without dispatching any click."""

    def __init__(self, page, selector):
        self._page = page
        self._selector = selector

    def _matches(self):
        css, text = _parse_fake_selector(self._selector)
        return [
            b
            for b in self._page._dom_buttons()
            if b.get("visible", True)
            and _fake_css_matches(b, css)
            and _fake_text_matches(b.get("domText"), text)
        ]

    def count(self):
        return len(self._matches())

    @property
    def first(self):
        return _FakeLocatorFirst(self)

    def click(self):  # pragma: no cover - production never calls this
        raise AssertionError(
            "the production submit path must not click the locator; "
            "it submits the bound form via veto:submit-bound-form "
            "without dispatching any click"
        )


class _FakeLocatorFirst:
    """The ``locator.first`` view: visibility only. Production never
    clicks — not the locator, not the ``.first`` view."""

    def __init__(self, locator):
        self._locator = locator

    def is_visible(self):
        matches = self._locator._matches()
        return bool(matches) and bool(matches[0].get("visible", True))

    def click(self, timeout=None):  # pragma: no cover
        raise AssertionError(
            "the production submit path must not click the locator; "
            "it submits the bound form via veto:submit-bound-form "
            "without dispatching any click"
        )


def _submitter_row(submitter):
    """Snapshot row for the bound submitter (round 7-A)."""
    return {
        "index": -1,
        "key": submitter.get("name") or "submitter",
        "type": submitter.get("type") or "submit",
        "tag": "button",
        "name": submitter.get("name") or "",
        "disabled": False,
        "formId": "",
        "successful": True,
        "value": submitter.get("value") or "",
        "checked": None,
        "options": None,
        "selectLabel": "",
        "formaction": submitter.get("formaction") or "",
        "formmethod": submitter.get("formmethod") or "",
        "formtarget": submitter.get("formtarget") or "",
        "formenctype": submitter.get("formenctype") or "",
        "isSubmitter": True,
        "submitterCss": submitter.get("css"),
        "submitterText": submitter.get("text"),
        "submitterFormIndex": submitter.get("formIndex"),
        "submitterIndexInForm": submitter.get("indexInForm"),
    }


def _fake_destination_params(page):
    """Emulate the ``submissionParams`` of ``_SUBMIT_DESTINATION_JS``:
    the submitter's formmethod/formtarget/formenctype override the
    form's method/target/enctype; the method defaults to GET per the
    HTML spec (round 9: the bound destination includes the method)."""
    sub = page.submitter or {}
    return {
        "method": (
            sub.get("formmethod") or getattr(page, "form_method", "") or "get"
        ).lower(),
        "target": sub.get("formtarget") or getattr(page, "form_target", "") or "",
        "enctype": (
            sub.get("formenctype") or getattr(page, "form_enctype", "") or ""
        ).lower(),
    }


class _FakeApplyPage:
    def __init__(self):
        self.url = "https://example.com/apply"
        # MAJOR 2 (round 6): a real Playwright page ALWAYS exposes
        # .context; the fakes model Chromium pages, so they expose the
        # CDP session factory. The M3 readback must go through the
        # isolated world — never the main-world evaluate().
        self.context = _FakeDelegatingCDPContext(self)
        # Current DOM field values, keyed like extract_form_fields'
        # "name". The M3 re-verification reads these via the isolated
        # world.
        self.dom_values = {
            "full_name": "Ada Lovelace",
            "email": "ada@example.com",
        }
        # The form's action attribute ("" = no action: native submit
        # to the current document URL).
        self.form_action = ""
        # Round 9: the form's submission parameters — the submitter's
        # formmethod/formtarget/formenctype override these, else they
        # are the bound method/target/enctype.
        self.form_method = "post"
        self.form_target = ""
        self.form_enctype = ""
        # Round 7-A: the page's actual submit button (None = no
        # submitter on the page).
        self.submitter = _default_submitter()
        # Round 9: forms the isolated submit probe actually submitted,
        # in submit order. Production never dispatches a click or
        # submit event — assertions must check this list, never a
        # locator mock, and ``dom_event_log`` must stay empty.
        self.submitted_forms = []
        self.form_submitted = False
        # DOM events the fake page "dispatched" (click/submit). The
        # event-free submit path never dispatches any — tests assert
        # this stays empty.
        self.dom_event_log = []
        # Page-registered JS handlers (click/submit), modelled as
        # Python callables. The event-free submit path never invokes
        # them — the hostile-handler regression asserts they stay
        # unfired.
        self.handlers = {"click": [], "submit": []}

    def _dom_buttons(self):
        """The page's true-DOM buttons in document order — the
        isolated-world view every probe resolves against. Pages
        modelling multi-button DOMs override this."""
        return [self.submitter] if self.submitter is not None else []

    def locator(self, selector):
        # Discovery only: production never clicks the returned
        # locator (the submit targets the bound form itself via
        # veto:submit-bound-form — no click is ever dispatched).
        return _FakeLocator(self, selector)

    def goto(self, url, **kwargs):
        self.url = url

    def wait_for_load_state(self, state, timeout=None):
        pass

    def _control_rows(self):
        # Emulates the control rows of the _SNAPSHOT_JS output: one row
        # per successful control.
        return [
            {
                "index": i,
                "key": name,
                "type": "text",
                "tag": "input",
                "name": name,
                "disabled": False,
                "formId": "",
                "successful": True,
                "value": value,
                "checked": None,
                "options": None,
                "selectLabel": "",
            }
            for i, (name, value) in enumerate(self.dom_values.items())
        ]

    def _snapshot_rows(self):
        # Emulates the full _SNAPSHOT_JS output: control rows plus the
        # round-7-A submitter row, when a submitter is present.
        rows = self._control_rows()
        if self.submitter is not None:
            rows = rows + [_submitter_row(self.submitter)]
        return rows

    def _snapshot_result(self, ref):
        # Emulates the _SNAPSHOT_JS return envelope: rows plus the
        # page-side submitter re-match info. A reference that no
        # longer matches yields a miss (submitterInfo.found False,
        # no submitter row) — the binding notices the disappearance.
        if self.submitter is not None and _submitter_ref_matches(
            self.submitter, ref
        ):
            info = dict(_submitter_identity(self.submitter))
        else:
            info = {"found": False}
        rows = self._control_rows()
        if info["found"]:
            rows = rows + [_submitter_row(self.submitter)]
        return {"rows": rows, "submitterInfo": info}

    def _destination(self, ref=None):
        # Emulates _SUBMIT_DESTINATION_JS output: the SUBMITTER's
        # formaction wins, then the SUBMITTER's own form's action, then
        # the SPA/no-form path. ``source`` names which step answered.
        # Like the real probe, relative URLs resolve against the page
        # URL page-side. Round 9: the method/target/enctype ride along
        # (the bound destination includes the method).
        def _resolve(value):
            if not value:
                return ""
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", value):
                return value
            return urljoin(self.url, value)

        params = _fake_destination_params(self)
        has_form = (self.submitter or {}).get("formIndex", 0) >= 0
        if self.submitter is not None and (
            ref is None or _submitter_ref_matches(self.submitter, ref)
        ):
            formaction = self.submitter.get("formaction") or ""
            if formaction:
                return dict(
                    {
                        "action": formaction,
                        "resolved": _resolve(formaction),
                        "hasForm": has_form,
                        "source": "submitter-formaction",
                    },
                    **params,
                )
            action = self.form_action
            if action:
                return dict(
                    {
                        "action": action,
                        "resolved": _resolve(action),
                        "hasForm": has_form,
                        "source": "submitter-form-action",
                    },
                    **params,
                )
            return dict(
                {
                    "action": "",
                    "resolved": "",
                    "hasForm": has_form,
                    "source": "submitter-no-action",
                },
                **params,
            )
        # No submitter (or the reference no longer matches): legacy
        # first-form fallback, explicitly labeled.
        action = self.form_action
        return dict(
            {
                "action": action,
                "resolved": _resolve(action),
                "hasForm": True,
                "source": "no-submitter-fallback",
            },
            **params,
        )

    def _consent_evaluate(self, js, arg=None):
        # No consent banner on these pages: the enumeration finds
        # nothing, and no known-ID probe matches.
        if "veto:consent-enumerate" in js:
            return []
        if "veto:consent-id-probe" in js:
            return {"found": False}
        if "veto:consent-id-click" in js:
            return {"clicked": False}
        raise AssertionError(f"unexpected consent JS: {js[:60]}")

    def evaluate(self, js, arg=None):
        # Marker dispatch: each isolated-world probe carries a
        # ``veto:<marker>`` dispatch marker. Anything WITHOUT a marker
        # is either the (non-security) field-detection read or an
        # unmarked probe the tests must notice loudly.
        if "veto:locate-submitter" in js:
            # Round 8 (F1): run the REAL production pattern list
            # against the fake DOM — the fake models discovery, not
            # the production's answer.
            return _fake_locate_submitter_result(
                self._dom_buttons(), arg
            )
        if "veto:submit-bound-form" in js:
            # Round 9: the submit targets the BOUND FORM itself —
            # no click event and no submit event is ever dispatched.
            # ``arg`` is [submitter_identity, approved_binding].
            identity, approved = arg
            return _fake_submit_bound_form(self, identity, approved)
        if "veto:snapshot" in js:
            return self._snapshot_result(arg)
        if "veto:destination" in js:
            return self._destination(arg)
        if "veto:consent" in js:
            return self._consent_evaluate(js, arg)
        if "querySelectorAll('input, textarea, select')" in js:
            # Field detection (non-security): the fill is mocked, so
            # no fields are needed.
            return []
        raise AssertionError(f"unexpected JS without marker: {js[:80]}")


class _FakeApplyContext:
    def __init__(self, page):
        self._page = page

    def new_page(self):
        return self._page


class _FakeApplyBrowser:
    def __init__(self, page):
        self._page = page

    def new_context(self, **kwargs):
        return _FakeApplyContext(self._page)

    def close(self):
        pass


class _FakeApplyChromium:
    def __init__(self, page):
        self._page = page

    def launch(self, headless=True, args=None):
        return _FakeApplyBrowser(self._page)


class _FakeApplyPlaywright:
    def __init__(self, page):
        self.chromium = _FakeApplyChromium(page)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _FakeSelectPage:
    """Fake page with <select> fields, in the _SNAPSHOT_JS row shape.

    ``selects`` maps field name -> {"label": visible text, "value": value
    attribute}. Hostile page JS is simulated by mutating ``selects``
    between fill and submit.
    """

    def __init__(self):
        self.url = "https://example.com/apply"
        # MAJOR 2 (round 6): models a Chromium page — CDP channel
        # present, readback via the isolated world.
        self.context = _FakeDelegatingCDPContext(self)
        self.selects = {
            "department": {"label": "Engineering", "value": "eng"},
        }
        self.form_action = ""
        # Round 7-A: the page's actual submit button.
        self.submitter = _default_submitter()
        # Round 9: forms the isolated submit probe actually
        # submitted, in submit order (see _FakeApplyPage).
        self.submitted_forms = []
        self.form_submitted = False
        self.dom_event_log = []
        self.handlers = {"click": [], "submit": []}

    def _dom_buttons(self):
        """The page's true-DOM buttons in document order — the
        isolated-world view every probe resolves against."""
        return [self.submitter] if self.submitter is not None else []

    def locator(self, selector):
        # Discovery only: production never clicks the returned
        # locator (the submit targets the bound form itself via
        # veto:submit-bound-form — no click is ever dispatched).
        return _FakeLocator(self, selector)

    def goto(self, url, **kwargs):
        self.url = url

    def wait_for_load_state(self, state, timeout=None):
        pass

    def _control_rows(self):
        return [
            {
                "index": i,
                "key": name,
                "type": "select-one",
                "tag": "select",
                "name": name,
                "disabled": False,
                "formId": "",
                "successful": True,
                "value": opt["value"],
                "checked": None,
                "options": [
                    {"label": opt["label"], "value": opt["value"]}
                ],
                "selectLabel": opt["label"],
            }
            for i, (name, opt) in enumerate(self.selects.items())
        ]

    def _snapshot_result(self, ref):
        if self.submitter is not None and _submitter_ref_matches(
            self.submitter, ref
        ):
            info = dict(_submitter_identity(self.submitter))
        else:
            info = {"found": False}
        rows = self._control_rows()
        if info["found"]:
            rows = rows + [_submitter_row(self.submitter)]
        return {"rows": rows, "submitterInfo": info}

    def _destination(self, ref=None):
        # Round 9: the method/target/enctype ride along with the
        # destination (the bound destination includes the method).
        params = _fake_destination_params(self)
        if self.submitter is not None and (
            ref is None or _submitter_ref_matches(self.submitter, ref)
        ):
            return dict(
                {
                    "action": "",
                    "resolved": "",
                    "hasForm": True,
                    "source": "submitter-no-action",
                },
                **params,
            )
        return dict(
            {
                "action": "",
                "resolved": "",
                "hasForm": True,
                "source": "no-submitter-fallback",
            },
            **params,
        )

    def _consent_evaluate(self, js, arg=None):
        if "veto:consent-enumerate" in js:
            return []
        if "veto:consent-id-probe" in js:
            return {"found": False}
        if "veto:consent-id-click" in js:
            return {"clicked": False}
        raise AssertionError(f"unexpected consent JS: {js[:60]}")

    def evaluate(self, js, arg=None):
        if "veto:locate-submitter" in js:
            # Round 8 (F1): run the REAL production pattern list
            # against the fake DOM.
            return _fake_locate_submitter_result(
                self._dom_buttons(), arg
            )
        if "veto:submit-bound-form" in js:
            # Round 9: the submit targets the BOUND FORM itself —
            # no click event and no submit event is ever dispatched.
            # ``arg`` is [submitter_identity, approved_binding].
            identity, approved = arg
            return _fake_submit_bound_form(self, identity, approved)
        if "veto:snapshot" in js:
            return self._snapshot_result(arg)
        if "veto:destination" in js:
            return self._destination(arg)
        if "veto:consent" in js:
            return self._consent_evaluate(js, arg)
        if "querySelectorAll('input, textarea, select')" in js:
            return []
        raise AssertionError(f"unexpected JS without marker: {js[:80]}")


class _FakeIndexedPage(_FakeApplyPage):
    """_FakeApplyPage with a distinct subclass for the S3 index-binding
    tests (inherits the _SNAPSHOT_JS-shaped evaluate)."""


class _FakeFullFormPage:
    """Fake page with a full control set for the MAJOR 1 (round 6)
    full-control binding tests: a filled text field, a hidden input, a
    checkbox, and an unfilled text input. Hostile page JS is simulated
    by mutating ``controls`` between fill and submit."""

    def __init__(self):
        self.url = "https://example.com/apply"
        self.form_action = ""
        # MAJOR 2 (round 6): models a Chromium page — CDP channel
        # present, readback via the isolated world.
        self.context = _FakeDelegatingCDPContext(self)
        # Round 7-A: the page's actual submit button.
        self.submitter = _default_submitter()
        # Round 9: forms the isolated submit probe actually
        # submitted, in submit order (see _FakeApplyPage).
        self.submitted_forms = []
        self.form_submitted = False
        self.dom_event_log = []
        self.handlers = {"click": [], "submit": []}
        # name -> control descriptor.
        self.controls = {
            "email": {
                "tag": "input", "type": "text", "value": "ada@example.com",
                "checked": None, "options": None, "disabled": False,
            },
            "csrf_token": {
                "tag": "input", "type": "hidden", "value": "abc123",
                "checked": None, "options": None, "disabled": False,
            },
            "newsletter": {
                "tag": "input", "type": "checkbox", "value": "yes",
                "checked": False, "options": None, "disabled": False,
            },
            "phone": {
                "tag": "input", "type": "text", "value": "",
                "checked": None, "options": None, "disabled": False,
            },
        }

    def _dom_buttons(self):
        """The page's true-DOM buttons in document order — the
        isolated-world view every probe resolves against."""
        return [self.submitter] if self.submitter is not None else []

    def locator(self, selector):
        # Discovery only: production never clicks the returned
        # locator (the submit targets the bound form itself via
        # veto:submit-bound-form — no click is ever dispatched).
        return _FakeLocator(self, selector)

    def goto(self, url, **kwargs):
        self.url = url

    def wait_for_load_state(self, state, timeout=None):
        pass

    def true_snapshot_rows(self):
        """The TRUE current DOM, in _SNAPSHOT_JS row shape (control
        rows plus the round-7-A submitter row, when present)."""
        rows = []
        for i, (name, ctl) in enumerate(self.controls.items()):
            rows.append(
                {
                    "index": i,
                    "key": name,
                    "type": ctl["type"],
                    "tag": ctl["tag"],
                    "name": name,
                    "disabled": ctl["disabled"],
                    "formId": "",
                    "successful": True,
                    "value": ctl["value"],
                    "checked": ctl["checked"],
                    "options": ctl["options"],
                    "selectLabel": "",
                }
            )
        if self.submitter is not None:
            rows.append(_submitter_row(self.submitter))
        return rows

    def _snapshot_result(self, ref):
        if self.submitter is not None and _submitter_ref_matches(
            self.submitter, ref
        ):
            info = dict(_submitter_identity(self.submitter))
        else:
            info = {"found": False}
        rows = [
            row for row in self.true_snapshot_rows()
            if not row.get("isSubmitter")
        ]
        if info["found"]:
            rows = rows + [_submitter_row(self.submitter)]
        return {"rows": rows, "submitterInfo": info}

    def _destination(self, ref=None):
        # Round 9: the method/target/enctype ride along with the
        # destination (the bound destination includes the method).
        params = _fake_destination_params(self)
        if self.submitter is not None and (
            ref is None or _submitter_ref_matches(self.submitter, ref)
        ):
            return dict(
                {
                    "action": "",
                    "resolved": "",
                    "hasForm": True,
                    "source": "submitter-no-action",
                },
                **params,
            )
        return dict(
            {
                "action": "",
                "resolved": "",
                "hasForm": True,
                "source": "no-submitter-fallback",
            },
            **params,
        )

    def _consent_evaluate(self, js, arg=None):
        if "veto:consent-enumerate" in js:
            return []
        if "veto:consent-id-probe" in js:
            return {"found": False}
        if "veto:consent-id-click" in js:
            return {"clicked": False}
        raise AssertionError(f"unexpected consent JS: {js[:60]}")

    def evaluate(self, js, arg=None):
        if "veto:locate-submitter" in js:
            # Round 8 (F1): run the REAL production pattern list
            # against the fake DOM.
            return _fake_locate_submitter_result(
                self._dom_buttons(), arg
            )
        if "veto:submit-bound-form" in js:
            # Round 9: the submit targets the BOUND FORM itself —
            # no click event and no submit event is ever dispatched.
            # ``arg`` is [submitter_identity, approved_binding].
            identity, approved = arg
            return _fake_submit_bound_form(self, identity, approved)
        if "veto:snapshot" in js:
            return self._snapshot_result(arg)
        if "veto:destination" in js:
            return self._destination(arg)
        if "veto:consent" in js:
            return self._consent_evaluate(js, arg)
        if "querySelectorAll('input, textarea, select')" in js:
            return []
        raise AssertionError(f"unexpected JS without marker: {js[:80]}")


class _FakeCDPSession:
    """Fake Chromium CDP session: the isolated world reports the TRUE
    DOM, whatever the page's main world claims. Reads are dispatched
    on the ``veto:<marker>`` probes with page-side arguments forwarded
    — never on the forgeable main-world ``page.evaluate``."""

    def __init__(self, page):
        self._page = page

    def send(self, method, params=None):
        if method == "Page.getFrameTree":
            return {"frameTree": {"frame": {"id": "frame-1"}}}
        if method == "Page.createIsolatedWorld":
            return {"executionContextId": 42}
        if method == "Runtime.callFunctionOn":
            fn = (params or {}).get("functionDeclaration", "")
            args = (params or {}).get("arguments", [])
            arg = args[0].get("value") if args else None
            return {
                "result": {"value": self._page.isolated_evaluate(fn, arg)}
            }
        raise AssertionError(f"unexpected CDP method {method}")

    def detach(self):
        pass


class _FakeCDPContext:
    def __init__(self, page):
        self._page = page

    def new_cdp_session(self, page):
        self._page.cdp_sessions_created.append(page)
        return _FakeCDPSession(self._page)


class _FakeNonChromiumPage(_FakeApplyPage):
    """Models a REAL non-Chromium (Firefox/WebKit) page: a genuine
    browser context exists, but CDP is Chromium-only — there is no
    session channel. MAJOR 2 fail-closed: the readback must REFUSE,
    never degrade to the forgeable main-world ``page.evaluate``."""

    def __init__(self):
        super().__init__()
        # A real browser context object — deliberately WITHOUT
        # new_cdp_session.
        self.context = object()


class _FakeBrokenCDPContext:
    """Chromium page whose CDP channel cannot be established."""

    def new_cdp_session(self, page):
        raise RuntimeError("CDP not attached")


class _FakeForgedPage(_FakeFullFormPage):
    """MAJOR 2 (round 6) test double: ``page.evaluate`` (the main world)
    is FORGED — it returns stale approved values no matter how the live
    DOM is tampered — while the CDP isolated world reports the true
    DOM. Proves the re-verification never trusts the main world."""

    def __init__(self):
        super().__init__()
        self.context = _FakeCDPContext(self)
        self.cdp_sessions_created = []
        self.evaluate_calls = []
        # What the forged main world reports (stale approved state).
        self.forged_rows = []

    def evaluate(self, js, arg=None):
        self.evaluate_calls.append(js)
        return self.forged_rows

    def isolated_evaluate(self, js, arg=None):
        # The isolated world defeats the main-world forgery: resolve
        # the probes against the TRUE model (the parent's honest
        # marker dispatch), never the forged main-world view.
        return _FakeFullFormPage.evaluate(self, js, arg)


class TestEvaluateUnforgedFailClosed(unittest.TestCase):
    """Surviving CDP isolated-world readback contract.

    The browser-apply approval/submit flow that
    ``TestBrowserApplyApproval`` covered was removed by
    legal-hardening commit 3 (spec section 1: Veto never
    submits). These three fail-closed tests survive because
    they pin live behavior of
    ``browser_apply._evaluate_unforged`` — the CDP
    isolated-world readback still used by the fill-only
    flow — not the deleted submit machinery.
    """

    def test_evaluate_unforged_refuses_non_chromium_page_directly(
        self,
    ) -> None:
        """MAJOR 2 fail-closed: a REAL non-Chromium page (browser
        context present, no CDP channel — CDP is Chromium-only) raises
        RuntimeError. There is deliberately no main-world fallback:
        trusting ``page.evaluate`` for a production security decision
        would let hostile page JS forge the readback."""
        page = _FakeNonChromiumPage()
        with self.assertRaisesRegex(RuntimeError, "isolated.*unforged"):
            browser_apply._evaluate_unforged(page, "1+1")

    def test_evaluate_unforged_refuses_broken_cdp_channel(self) -> None:
        """MAJOR 2 fail-closed: a Chromium page whose CDP isolated
        world cannot be established raises RuntimeError — same
        refusal, no main-world fallback."""
        page = _FakeApplyPage()
        page.context = _FakeBrokenCDPContext()
        with self.assertRaisesRegex(RuntimeError, "isolated.*unforged"):
            browser_apply._evaluate_unforged(page, "1+1")

    def test_incomplete_test_double_keeps_unavailable_path(self) -> None:
        """MAJOR 2 compatibility: a page object with NO browser context
        at all is an incomplete test double (real Playwright pages
        always expose .context) — it keeps the legacy loud
        ``_READBACK_UNAVAILABLE`` path instead of raising."""

        class _BareDouble:
            def evaluate(self, js, arg=None):
                raise AssertionError("must not be consulted")

        self.assertIs(
            browser_apply._evaluate_unforged(_BareDouble(), "1+1"),
            browser_apply._READBACK_UNAVAILABLE,
        )
class _FakeIsolatedCDPSession:
    """CDP session double whose reads resolve ONLY against the page's
    isolated model (``page.isolated_evaluate``). The main-world
    ``page.evaluate`` may be forged; this session never consults it —
    mirroring how a real isolated world defeats a main-world forgery."""

    def __init__(self, page):
        self._page = page

    def send(self, method, params=None):
        if method == "Page.getFrameTree":
            return {"frameTree": {"frame": {"id": "frame-1"}}}
        if method == "Page.createIsolatedWorld":
            return {"executionContextId": 9}
        if method == "Runtime.callFunctionOn":
            fn = (params or {}).get("functionDeclaration", "")
            args = (params or {}).get("arguments", [])
            arg = args[0].get("value") if args else None
            return {
                "result": {"value": self._page.isolated_evaluate(fn, arg)}
            }
        raise AssertionError(f"unexpected CDP method {method}")

    def detach(self):
        pass


class _FakeIsolatedCDPContext:
    """Chromium context double whose CDP sessions read only the page's
    isolated model."""

    def __init__(self, page):
        self._page = page

    def new_cdp_session(self, page):
        return _FakeIsolatedCDPSession(self._page)


class _FakeConsentLocator:
    def count(self):
        return 0

    @property
    def first(self):
        return self

    def is_visible(self):
        return False

    def click(self, timeout=None):
        raise AssertionError("must not click a hidden selector")


class _FakeConsentPage:
    """Consent-banner page double with an explicit trust boundary.

    ``isolated_buttons`` is the ISOLATED-world truth: what the CDP
    probes observe and what the click-time re-verification checks.
    ``page.evaluate`` (the forgeable main world) dispatches consent
    markers to the isolated model only so the delegating CDP double
    works; hostile tests override it to forge the main world.
    """

    def __init__(self):
        self.url = "https://example.com/apply"
        self.context = _FakeDelegatingCDPContext(self)
        self.isolated_buttons = [
            {"index": 0, "text": "Accept all", "aria": "", "visible": True},
            {"index": 1, "text": "Reject all", "aria": "", "visible": True},
            {"index": 2, "text": "×", "aria": "Close", "visible": True},
        ]
        # Known-ID probes: selector -> {"index", "text", "aria"}.
        self.id_probes = {}
        self.clicked_indexes = []

    def locator(self, sel):
        return _FakeConsentLocator()

    def _note_click(self, index):
        self.clicked_indexes.append(index)

    def isolated_evaluate(self, js, arg=None):
        # Emulates the isolated-world consent probes with the exact
        # production string protocol: the enumeration returns
        # [{index, text, aria, visible}]; the click probes return
        # 'clicked' / 'text-changed' / 'missing' / 'hidden'.
        if "veto:consent-id-probe" in js:
            probe = self.id_probes.get(arg)
            if probe is None:
                return {
                    "found": False, "visible": False,
                    "text": "", "aria": "",
                }
            return {
                "found": True,
                "visible": True,
                "text": probe["text"],
                "aria": probe.get("aria", ""),
            }
        if "veto:consent-id-click" in js:
            sel, expected = arg[0], arg[1]
            probe = self.id_probes.get(sel)
            if probe is None:
                return "missing"
            # Atomic verify+click: only when the isolated text still
            # matches the classified text.
            if probe["text"] != expected:
                return "text-changed"
            self._note_click(probe["index"])
            return "clicked"
        if "veto:consent-enumerate" in js:
            return [dict(b) for b in self.isolated_buttons]
        if "veto:consent-click" in js:
            index, expected = arg[0], arg[1]
            btn = next(
                (b for b in self.isolated_buttons if b["index"] == index),
                None,
            )
            if btn is None:
                return "missing"
            # N4 re-verification: the slot's CURRENT isolated text must
            # still equal the enumeration-time text.
            if btn["text"] != expected:
                return "text-changed"
            self._note_click(index)
            return "clicked"
        raise AssertionError(f"unexpected consent JS: {js[:60]}")

    def evaluate(self, js, arg=None):
        # Production consent reads NEVER use this channel (they go
        # through CDP). Dispatch consent markers to the isolated model
        # so the delegating CDP double works; fail loudly otherwise.
        if "veto:consent" in js:
            return self.isolated_evaluate(js, arg)
        if "querySelectorAll('input, textarea, select')" in js:
            return []
        raise AssertionError(f"unexpected JS without marker: {js[:80]}")


class _FakeForgedConsentPage(_FakeConsentPage):
    """Round 7-C test double: the hostile main world forges the consent
    enumeration — the single slot the isolated world reports as
    'Accept all' is reported as 'Reject all' here. Production must use
    the isolated world and click nothing."""

    def __init__(self):
        super().__init__()
        # The CDP channel reads ONLY the isolated model — the forged
        # main world below is invisible to it.
        self.context = _FakeIsolatedCDPContext(self)
        # Isolated truth: a single "Accept all" button.
        self.isolated_buttons = [
            {"index": 0, "text": "Accept all", "aria": "", "visible": True},
        ]
        self.forged_buttons = [
            dict(b, text="Reject all") for b in self.isolated_buttons
        ]
        self.main_world_reads = []

    def evaluate(self, js, arg=None):
        # FORGED main world: reports the approved-looking lie. Any
        # consent probe reaching this channel is a security regression
        # — record it loudly.
        self.main_world_reads.append(js)
        if "veto:consent-enumerate" in js:
            return [dict(b) for b in self.forged_buttons]
        raise AssertionError(f"unexpected JS without marker: {js[:80]}")


class _FakeConsentPageWithIdButton(_FakeConsentPage):
    """A consent page where a known-ID selector matches a button with
    the given text in the ISOLATED world (simulating a hostile/changed
    button behind a trusted selector id)."""

    def __init__(self, text, aria=""):
        super().__init__()
        self.id_button_text = text
        self.id_button_aria = aria
        self.id_button_clicked = False
        # The isolated world sees the button behind the first
        # known-ID selector with the given text.
        self.id_probes = {
            browser_apply._CONSENT_REJECT_SELECTORS[0]: {
                "index": 10,
                "text": text,
                "aria": aria,
            }
        }

    def _note_click(self, index):
        # The known-ID click lands on the ID-selected button, not the
        # enumerated slot.
        if index == 10:
            self.id_button_clicked = True
        else:
            super()._note_click(index)


class TestConsentBannerPrivacy(unittest.TestCase):
    """M1: dismiss_consent_banners must NEVER opt the user into tracking."""

    def test_accept_like_buttons_are_never_classified(self) -> None:
        for text in (
            "Accept all", "Accept", "Got it", "Allow all", "Agree",
            "I agree", "OK", "Accept cookies", "Yes, accept",
        ):
            self.assertIsNone(
                browser_apply._consent_button_kind(text), text
            )

    def test_reject_buttons_are_classified(self) -> None:
        for text in (
            "Reject all", "Reject", "Decline", "Decline all", "Deny",
            "No thanks", "Necessary only", "Essential only",
        ):
            self.assertEqual(
                browser_apply._consent_button_kind(text), "reject", text
            )

    def test_dismiss_buttons_are_classified(self) -> None:
        self.assertEqual(
            browser_apply._consent_button_kind("Close"), "dismiss"
        )
        self.assertEqual(
            browser_apply._consent_button_kind("Dismiss"), "dismiss"
        )
        self.assertEqual(
            browser_apply._consent_button_kind("×", "Close"), "dismiss"
        )
        # A bare × without an accessible close/dismiss name is left alone.
        self.assertIsNone(browser_apply._consent_button_kind("×", "menu"))

    def test_dismiss_clicks_reject_and_close_never_accept(self) -> None:
        page = _FakeConsentPage()
        clicked = browser_apply.dismiss_consent_banners(page)
        self.assertEqual(clicked, 2)
        self.assertEqual(sorted(page.clicked_indexes), [1, 2])

    def test_click_time_text_change_never_clicks(self) -> None:
        """N4 (round 4): the click re-verifies the button's text at click
        time through the ISOLATED world. A button that said "Reject all"
        at enumeration but whose DOM slot changed by click time (racing
        mutation / hostile page JS) is left alone — fail closed, never
        clicked by a shifted index."""
        page = _FakeConsentPage()
        real_isolated = page.isolated_evaluate

        def _racing_isolated(js, arg=None):
            if "veto:consent-click" in js:
                # Racing mutation in the isolated world: the targeted
                # slot now reads "Accept all".
                for b in page.isolated_buttons:
                    if b["index"] == arg[0]:
                        b["text"] = "Accept all"
            return real_isolated(js, arg)

        page.isolated_evaluate = _racing_isolated
        with self.assertLogs(
            "veto-mcp.browser", level="WARNING"
        ):
            clicked = browser_apply.dismiss_consent_banners(page)
        self.assertEqual(clicked, 0)
        self.assertEqual(page.clicked_indexes, [])

    def test_id_selector_button_with_accept_text_is_never_clicked(self) -> None:
        """m1: an ID-selected selector now VERIFIES the button's text
        before clicking — a hostile 'Accept all' behind a trusted ID is
        left alone (this would have been auto-clicked before)."""
        page = _FakeConsentPageWithIdButton("Accept all")
        with self.assertLogs(
            "veto-mcp.browser", level="WARNING"
        ):
            browser_apply.dismiss_consent_banners(page)
        self.assertFalse(page.id_button_clicked)

    def test_id_selector_button_with_reject_text_is_clicked(self) -> None:
        """m1: the same ID selector WITH a reject label is still clicked —
        verification doesn't break the legitimate path."""
        page = _FakeConsentPageWithIdButton("Reject all")
        clicked = browser_apply.dismiss_consent_banners(page)
        self.assertTrue(page.id_button_clicked)
        self.assertGreaterEqual(clicked, 1)

    def test_id_selector_button_with_unreadable_text_is_never_clicked(
        self,
    ) -> None:
        """m1: fail closed — if the isolated-world text read fails, no
        click."""

        page = _FakeConsentPageWithIdButton("whatever")
        real_isolated = page.isolated_evaluate

        def _detached(js, arg=None):
            if "veto:consent-id-probe" in js:
                raise RuntimeError("detached")
            return real_isolated(js, arg)

        page.isolated_evaluate = _detached
        browser_apply.dismiss_consent_banners(page)
        self.assertFalse(page.id_button_clicked)

    def test_forged_main_world_consent_never_clicked(self) -> None:
        """Round 7-C: hostile page JS forges the MAIN world — the slot
        the isolated world reports as 'Accept all' is reported as
        'Reject all' there. Consent enumeration and click-time
        verification must use the isolated world only: no button is
        clicked, and the forged main-world channel is never read."""
        page = _FakeForgedConsentPage()
        clicked = browser_apply.dismiss_consent_banners(page)
        self.assertEqual(clicked, 0)
        self.assertEqual(page.clicked_indexes, [])
        # The forged main-world evaluate() was NEVER consulted — the
        # old main-world enumeration would have clicked the forged
        # "Reject all".
        self.assertEqual(page.main_world_reads, [])


# ---------------------------------------------------------------------------
# M2: storage_state permission hardening fails loudly
# ---------------------------------------------------------------------------


class _FakeZeroLocator:
    def count(self):
        return 0


class _FakeLoginPage:
    def __init__(self):
        self.url = "https://www.linkedin.com/feed/"

    def goto(self, url, **kwargs):
        # Simulate the manual login completing: the browser lands on the
        # post-login feed, which is what _looks_logged_in detects.
        self.url = "https://www.linkedin.com/feed/"

    def locator(self, sel):
        return _FakeZeroLocator()


class _FakeLoginContext:
    def __init__(self):
        self._page = _FakeLoginPage()

    def new_page(self):
        return self._page

    def storage_state(self, path=None, **kwargs):
        Path(path).write_text("{}", encoding="utf-8")


class _FakeLoginBrowser:
    def new_context(self, **kwargs):
        return _FakeLoginContext()

    def close(self):
        pass


class _FakeLoginChromium:
    def launch(self, **kwargs):
        return _FakeLoginBrowser()


class _FakeLoginPlaywright:
    chromium = _FakeLoginChromium()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False
class TestScreenshotRetention(unittest.TestCase):
    """m2: PII screenshots are pruned by age and capped by count."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.shots = Path(self.tmp.name) / "shots"
        self.shots.mkdir()
        patch = mock.patch.object(browser_apply, "SCREENSHOTS_DIR", self.shots)
        patch.start()
        self.addCleanup(patch.stop)

    def _shot(self, name, mtime=None):
        p = self.shots / name
        p.write_text("fake-png", encoding="utf-8")
        if mtime is not None:
            os.utime(p, (mtime, mtime))
        return p

    def test_cleanup_removes_old_screenshots(self) -> None:
        old = self._shot("apply-20200101-000000-deadbeef-preview.png", mtime=0)
        new = self._shot("apply-20260913-120000-abcdef01-preview.png")
        other = self.shots / "notes.txt"
        other.write_text("keep", encoding="utf-8")
        result = browser_apply.cleanup_screenshots()
        self.assertIn(old.name, result["deleted"])
        self.assertFalse(old.exists())
        self.assertTrue(new.exists())
        self.assertTrue(other.exists())  # foreign files untouched
        self.assertEqual(result["kept"], 1)
        self.assertEqual(result["errors"], [])

    def test_cleanup_trims_to_max_count(self) -> None:
        names = [
            f"apply-20260913-12000{i}-abcdef{i:02d}-preview.png"
            for i in range(4)
        ]
        now = time.time()
        for i, name in enumerate(names):
            # Fresh files (well within the age window), ordered oldest→newest.
            self._shot(name, mtime=now - (4 - i))
        result = browser_apply.cleanup_screenshots(
            max_count=2, max_age_days=3650
        )
        self.assertEqual(len(result["deleted"]), 2)
        self.assertEqual(result["kept"], 2)
        remaining = sorted(p.name for p in self.shots.glob("apply-*.png"))
        self.assertEqual(remaining, sorted(names[2:]))

    def test_retention_policy_constants(self) -> None:
        self.assertEqual(browser_apply.SCREENSHOT_MAX_COUNT, 50)
        self.assertEqual(browser_apply.SCREENSHOT_MAX_AGE_DAYS, 30)


# ---------------------------------------------------------------------------
# m3: approval-payload field names are sanitized for display, raw bytes kept
# ---------------------------------------------------------------------------
class TestGmailCliScrub(unittest.TestCase):
    def test_cli_error_redacts_email_addresses(self) -> None:
        """m5: the first stderr line can echo PII (e.g. a recipient
        address) — it is redacted, and the docstring no longer claims
        PII-free errors."""
        with mock.patch("subprocess.run") as fake_run:
            fake_run.return_value = mock.Mock(
                returncode=1,
                stdout="",
                stderr="ERROR: invalid recipient <jane@acme.com>\n",
            )
            with self.assertRaises(RuntimeError) as ctx:
                email_sync._run_gmail_cli("status")
        message = str(ctx.exception)
        self.assertNotIn("jane@acme.com", message)
        self.assertIn("[redacted-address]", message)

    def test_no_pii_free_claim(self) -> None:
        # The old false claim was "...with a PII-free message...".
        self.assertNotIn("a PII-free message", email_sync._run_gmail_cli.__doc__)


# ---------------------------------------------------------------------------
# Screenshot files land owner-only on disk
# ---------------------------------------------------------------------------


class _FakeShotPage:
    def screenshot(self, path, full_page=None):
        Path(path).write_bytes(b"fake-png")


class TestScreenshotPermissions(unittest.TestCase):
    def test_screenshot_is_owner_only(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        with mock.patch.object(
            browser_apply, "SCREENSHOTS_DIR", Path(tmp.name)
        ):
            shot = browser_apply._take_screenshot(_FakeShotPage(), "preview")
        self.assertIsNotNone(shot)
        mode = os.stat(shot).st_mode & 0o777
        self.assertEqual(oct(mode), "0o600")

    def test_screenshot_chmod_failure_deletes_file_and_errors(self) -> None:
        """N3 (round 4): a chmod 0o600 failure is an ERROR, never a
        warning — the captured PII is DELETED (never left at umask
        permissions) and the shot is not reported as usable."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        with (
            mock.patch.object(
                browser_apply, "SCREENSHOTS_DIR", Path(tmp.name)
            ),
            mock.patch("os.chmod", side_effect=OSError("EPERM")),
            self.assertLogs(
                "veto-mcp.browser", level="ERROR"
            ) as logs,
        ):
            shot = browser_apply._take_screenshot(_FakeShotPage(), "preview")
        self.assertIsNone(shot)
        self.assertEqual(list(Path(tmp.name).glob("apply-*.png")), [])
        self.assertTrue(
            any("hardening" in rec.getMessage() for rec in logs.records),
            [rec.getMessage() for rec in logs.records],
        )


# ---------------------------------------------------------------------------
# MINOR 3 (round 6): approval-preview retention cap
# ---------------------------------------------------------------------------


class TestApprovalPreviewPruning(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patch = mock.patch.object(
            tempfile, "gettempdir", return_value=self.tmp.name
        )
        patch.start()
        self.addCleanup(patch.stop)

    def _preview(self, name: str, age_s: float) -> Path:
        p = Path(self.tmp.name) / name
        p.write_text("preview", encoding="utf-8")
        ts = time.time() - age_s
        os.utime(p, (ts, ts))
        return p

    def test_prune_keeps_newest_ten(self) -> None:
        """13 stale previews -> 3 deleted, the 10 NEWEST kept."""
        for i in range(13):
            self._preview(f"veto-approval-preview-{i:02d}.txt", age_s=130 - i * 10)
        deleted = email_sync._prune_approval_previews()
        self.assertEqual(deleted, 3)
        remaining = sorted(
            Path(self.tmp.name).glob("veto-approval-preview-*.txt")
        )
        self.assertEqual(len(remaining), 10)
        # The three OLDEST are gone; the ten newest survive.
        self.assertFalse((Path(self.tmp.name) / "veto-approval-preview-00.txt").exists())
        self.assertFalse((Path(self.tmp.name) / "veto-approval-preview-01.txt").exists())
        self.assertFalse((Path(self.tmp.name) / "veto-approval-preview-02.txt").exists())
        self.assertTrue((Path(self.tmp.name) / "veto-approval-preview-12.txt").exists())

    def test_prune_ignores_non_preview_files(self) -> None:
        other = Path(self.tmp.name) / "veto-other-notes.txt"
        other.write_text("not a preview", encoding="utf-8")
        for i in range(11):
            self._preview(f"veto-approval-preview-{i:02d}.txt", age_s=100 - i)
        deleted = email_sync._prune_approval_previews()
        self.assertEqual(deleted, 1)
        self.assertTrue(other.exists())

    def test_save_triggers_prune_and_newest_survives(self) -> None:
        """The just-saved preview is always the newest, so 'preview
        another way' still works after pruning."""
        for i in range(10):
            self._preview(f"veto-approval-preview-{i:02d}.txt", age_s=1000 - i)
        saved = email_sync._save_approval_preview("x" * 4001)
        self.assertIsNotNone(saved)
        remaining = list(Path(self.tmp.name).glob("veto-approval-preview-*.txt"))
        self.assertEqual(len(remaining), 10)
        self.assertIn(Path(saved), remaining)
        self.assertEqual(Path(saved).read_text(encoding="utf-8"), "x" * 4001)


# ---------------------------------------------------------------------------
# MINOR 4 (round 6): live-stage re-verification before stage writes
# ---------------------------------------------------------------------------


class TestStageReverification(EmailSyncTestBase):
    def _eligible(self) -> list[dict]:
        return [
            {
                "application_id": "job-1",
                "current_stage": "applied",
                "proposed_stage": "interviewing",
                "classification": "interview_invite",
                "confidence": 0.92,
            }
        ]

    def _run_updates(self, eligible):
        from initiatives.i09.channels import registry

        result = {"proposed_updates": [], "applied_updates": []}
        fake_approval = {"approval_id": "test-nonce"}
        with (
            mock.patch.object(
                registry, "authorize_send",
                return_value=(fake_approval, None),
            ),
            mock.patch.object(
                registry, "consume_approval", return_value=None
            ),
            mock.patch.object(
                email_sync.lifecycle, "update_stage"
            ) as spy_update,
        ):
            email_sync._apply_eligible_updates(eligible, result, None)
        return result, spy_update

    def test_stage_changed_after_approval_refuses_write(self) -> None:
        """MINOR 4: the approval said applied -> interviewing, but the
        store moved to interviewing (or elsewhere) before the write —
        the update is refused with the named action
        refused_stage_changed, and lifecycle.update_stage is NEVER
        called (no write under a stale approval)."""
        self.write_apps([_app("job-1", "Acme Corp", "Engineer", stage="interviewing")])
        eligible = self._eligible()
        result, spy_update = self._run_updates(eligible)
        self.assertEqual(eligible[0]["action"], "refused_stage_changed")
        self.assertIn("changed after", eligible[0]["note"])
        spy_update.assert_not_called()
        self.assertEqual(result["applied_updates"], [])
        self.assertEqual(len(result["proposed_updates"]), 1)
        # The store is untouched.
        self.assertEqual(self.read_apps()[0]["stage"], "interviewing")

    def test_stage_unverifiable_refuses_write(self) -> None:
        """MINOR 4: the live stage cannot be re-read (entry gone) — fail
        closed with refused_stage_unverifiable, no write."""
        self.write_apps([_app("job-1", "Acme Corp", "Engineer", stage="applied")])
        eligible = self._eligible()
        with mock.patch.object(
            email_sync, "_read_live_stage", return_value=None
        ):
            result, spy_update = self._run_updates(eligible)
        self.assertEqual(eligible[0]["action"], "refused_stage_unverifiable")
        self.assertIn("could not be re-read", eligible[0]["note"])
        spy_update.assert_not_called()
        self.assertEqual(result["applied_updates"], [])

    def test_ordinary_approved_update_still_applies(self) -> None:
        """MINOR 4: when the live stage still matches the approved
        current_stage, the write goes through as before."""
        self.write_apps([_app("job-1", "Acme Corp", "Engineer", stage="applied")])
        eligible = self._eligible()
        result, spy_update = self._run_updates(eligible)
        self.assertEqual(eligible[0]["action"], "applied")
        spy_update.assert_called_once()
        self.assertEqual(len(result["applied_updates"]), 1)


# ---------------------------------------------------------------------------
# NIT 7 (round 6): owner-only files from creation
# ---------------------------------------------------------------------------


class _RecordingShotPage:
    """Fake page whose screenshot() records the target's mode BEFORE
    writing a single byte."""

    def __init__(self):
        self.mode_at_write_start = None

    def screenshot(self, path, full_page=None):
        self.mode_at_write_start = os.stat(path).st_mode & 0o777
        Path(path).write_bytes(b"fake-png")


class TestSecureFileCreation(unittest.TestCase):
    def test_screenshot_owner_only_when_write_begins(self) -> None:
        """NIT 7: the screenshot target is already 0o600 when
        page.screenshot() begins writing — the PII bytes never exist at
        umask permissions."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        page = _RecordingShotPage()
        with mock.patch.object(
            browser_apply, "SCREENSHOTS_DIR", Path(tmp.name)
        ):
            shot = browser_apply._take_screenshot(page, "preview")
        self.assertIsNotNone(shot)
        self.assertEqual(oct(page.mode_at_write_start), "0o600")
        self.assertEqual(oct(os.stat(shot).st_mode & 0o777), "0o600")

    def test_precreate_tightens_preexisting_wide_file(self) -> None:
        """A pre-existing 0o644 target is tightened to 0o600 by the
        pre-creation (fchmod), not left wide."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "linkedin.json"
        path.write_text("{}", encoding="utf-8")
        os.chmod(path, 0o644)
        self.assertTrue(browser_apply._precreate_owner_only(path))
        self.assertEqual(oct(os.stat(path).st_mode & 0o777), "0o600")

    def test_session_target_owner_only_before_storage_state_writes(
        self,
    ) -> None:
        """NIT 7: the login_session composition — pre-create, then
        storage_state — presents a 0o600 target when the secrets begin
        writing."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "linkedin.json"
        self.assertTrue(browser_apply._precreate_owner_only(path))
        observed = {}

        def fake_storage_state(path=None, **kwargs):
            observed["mode"] = os.stat(path).st_mode & 0o777
            Path(path).write_text('{"cookies": []}', encoding="utf-8")

        fake_storage_state(path=str(path))
        self.assertEqual(oct(observed["mode"]), "0o600")

    def test_precreate_failure_refuses_loudly(self) -> None:
        """When the target cannot be secured, _precreate_owner_only
        returns False (loud log) so callers write nothing."""
        with (
            mock.patch("os.open", side_effect=OSError("EROFS")),
            self.assertLogs("veto-mcp.browser", level="ERROR"),
        ):
            self.assertFalse(
                browser_apply._precreate_owner_only(
                    Path("/nonexistent-dir/x.png")
                )
            )


if __name__ == "__main__":
    unittest.main()

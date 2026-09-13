#!/usr/bin/env python3
"""Tests for the Initiative 07 session kit (epic 4): agenda, consent-gated
context packet, question builder, notes, follow-up, feedback.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import mentors  # noqa: E402
from initiatives.i07 import consent, safety, session_kit  # noqa: E402


def _mentor_profile(i: int = 0) -> dict:
    return {
        "name": f"Mentor {i}",
        "industry": "software",
        "role": "Staff Engineer",
        "seniority": "ic5+",
        "topics": ["interviewing"],
        "linkedin_url": f"https://www.linkedin.com/in/synthetic-mentor-{i}",
        "availability": "Fridays",
        "max_mentees": 3,
        "bio": "I help with interviews.",
    }


class SessionKitTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        mentors.MENTORS_FILE = tmp / "mentors.json"
        consent.HANDSHAKES_FILE = tmp / "handshakes.json"
        consent.AUDIT_FILE = tmp / "consent_audit.jsonl"
        safety.SAFETY_FILE = tmp / "safety.json"
        safety.REPORTS_FILE = tmp / "reports.jsonl"
        safety.reset_rate_limits()
        session_kit.SESSIONS_FILE = tmp / "sessions.json"
        self.mentor_id = mentors.mentor_opt_in(_mentor_profile(0))["card"]["id"]

    def tearDown(self):
        self._tmp.cleanup()

    def _mutual_handshake(self, **kw):
        kw.setdefault("mentor_id", self.mentor_id)
        kw.setdefault("mentee_id", "me")
        kw.setdefault("mentee_label", "PT")
        kw.setdefault("goal", "Break into staff engineering")
        kw.setdefault("expected_outcome", "A study plan")
        kw["synthetic"] = True
        res = consent.request_introduction(**kw)
        hs_id = res["handshake"]["id"]
        consent.mentor_respond(hs_id, "approve", channel="email")
        return hs_id

    def _pending_handshake(self):
        res = consent.request_introduction(
            self.mentor_id, "me", "PT", "goal here", synthetic=True
        )
        return res["handshake"]["id"]

    # -- consent gating ---------------------------------------------------------

    def test_context_packet_refused_before_mutual(self):
        hs_id = self._pending_handshake()
        res = session_kit.context_packet(hs_id, "me")
        self.assertFalse(res["ok"])
        self.assertIn("mutual", res["error"])

    def test_notes_refused_before_mutual(self):
        hs_id = self._pending_handshake()
        self.assertFalse(session_kit.add_note(hs_id, "me", "hello")["ok"])
        self.assertFalse(session_kit.get_notes(hs_id, "me")["ok"])

    def test_feedback_refused_before_mutual(self):
        hs_id = self._pending_handshake()
        res = session_kit.session_feedback(hs_id, "me", 5)
        self.assertFalse(res["ok"])

    def test_context_packet_full_after_mutual(self):
        hs_id = self._mutual_handshake()
        res = session_kit.context_packet(hs_id, "me")
        self.assertTrue(res["ok"])
        packet = res["packet"]
        self.assertIn("linkedin_url", packet["mentor"])
        self.assertEqual(packet["mentee"]["expected_outcome"], "A study plan")
        self.assertIn("mentor_consented_at", packet["consent_receipt"])

    # -- agenda ------------------------------------------------------------------

    def test_agenda_includes_expected_outcome(self):
        hs_id = self._mutual_handshake()
        res = session_kit.build_agenda(hs_id, "me")
        self.assertTrue(res["ok"])
        self.assertIn("A study plan", res["agenda"])

    # -- question builder ----------------------------------------------------------

    def test_question_builder(self):
        res = session_kit.question_builder(["interviewing"], goal="staff promo", n=3)
        self.assertTrue(res["ok"])
        self.assertEqual(len(res["questions"]), 3)
        self.assertEqual(res["questions"][0]["topic"], "goal")

    def test_question_builder_bad_topic(self):
        res = session_kit.question_builder(["skydiving"])
        self.assertFalse(res["ok"])

    # -- notes ---------------------------------------------------------------------

    def test_notes_append_only(self):
        hs_id = self._mutual_handshake()
        self.assertTrue(session_kit.add_note(hs_id, "me", "n1", kind="takeaway")["ok"])
        self.assertTrue(session_kit.add_note(hs_id, "me", "n2", kind="action")["ok"])
        got = session_kit.get_notes(hs_id, "me")
        self.assertEqual(len(got["notes"]), 2)
        self.assertEqual(got["notes"][0]["kind"], "takeaway")

    def test_note_requires_text(self):
        hs_id = self._mutual_handshake()
        self.assertFalse(session_kit.add_note(hs_id, "me", "  ")["ok"])

    # -- follow-up -------------------------------------------------------------------

    def test_followup_plan_uses_notes(self):
        hs_id = self._mutual_handshake()
        session_kit.add_note(hs_id, "me", "Do 3 mocks", kind="action")
        res = session_kit.followup_plan(hs_id, "me")
        self.assertTrue(res["ok"])
        self.assertIn("Do 3 mocks", res["plan"])
        self.assertIn("thank-you", res["plan"])

    # -- feedback ----------------------------------------------------------------------

    def test_feedback_feeds_ratings(self):
        hs_id = self._mutual_handshake()
        res = session_kit.session_feedback(hs_id, "me", 5, note="great session")
        self.assertTrue(res["ok"])
        self.assertEqual(res["side"], "mentee")
        summary = res["rating_summary"]
        self.assertEqual(summary["mentee"]["count"], 1)

    def test_feedback_bad_score_rejected(self):
        hs_id = self._mutual_handshake()
        self.assertFalse(session_kit.session_feedback(hs_id, "me", 6)["ok"])
        self.assertFalse(session_kit.session_feedback(hs_id, "me", 0)["ok"])

    def test_mentor_side_feedback(self):
        hs_id = self._mutual_handshake()
        res = session_kit.session_feedback(hs_id, self.mentor_id, 4)
        self.assertTrue(res["ok"])
        self.assertEqual(res["side"], "mentor")

    # -- deletion support --------------------------------------------------------------

    def test_scrub_mentor_notes(self):
        hs_id = self._mutual_handshake()
        session_kit.add_note(hs_id, "me", "secret note")
        n = session_kit.scrub_mentor_notes(self.mentor_id)
        self.assertEqual(n, 1)
        self.assertEqual(session_kit.get_notes(hs_id, "me")["notes"], [])


if __name__ == "__main__":
    unittest.main()

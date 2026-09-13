#!/usr/bin/env python3
"""Tests for Initiative 07 mentors.py extensions: epic 1 (mentor profile
fields) and epic 2 (match questionnaire v2 + consent previews).
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


def _profile(**over) -> dict:
    p = {
        "name": "Ada Lovelace",
        "industry": "software",
        "role": "Staff Engineer",
        "seniority": "ic5+",
        "topics": ["interviewing", "ai_skills"],
        "linkedin_url": "https://www.linkedin.com/in/ada-lovelace",
        "availability": "Fridays",
        "max_mentees": 3,
        "bio": "I help with interviews.",
    }
    p.update(over)
    return p


class MentorProfileFieldsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        mentors.MENTORS_FILE = tmp / "mentors.json"
        mentors.OUTBOX_DIR = tmp / "outbox"

    def tearDown(self):
        self._tmp.cleanup()

    def test_opt_in_accepts_new_fields(self):
        res = mentors.mentor_opt_in(
            _profile(
                availability_windows=[{"day": "Friday", "start": "14:00", "end": "16:00"}],
                boundaries={
                    "offers": ["mock interviews"],
                    "wont": ["referrals to my employer"],
                    "note": "No weekends.",
                },
                preferred_contact="linkedin_public",
            )
        )
        self.assertTrue(res["ok"])
        card = res["card"]
        self.assertEqual(card["preferred_contact"], "linkedin_public")
        self.assertEqual(card["boundaries"]["wont"], ["referrals to my employer"])
        self.assertEqual(card["availability_windows"][0]["day"], "Friday")

    def test_preferred_contact_defaults_hidden(self):
        res = mentors.mentor_opt_in(_profile())
        self.assertEqual(res["card"]["preferred_contact"], "hidden")

    def test_bad_preferred_contact_rejected(self):
        with self.assertRaises(ValueError):
            mentors.mentor_opt_in(_profile(preferred_contact="sms"))

    def test_bad_boundaries_rejected(self):
        with self.assertRaises(ValueError):
            mentors.mentor_opt_in(_profile(boundaries={"offers": "not-a-list"}))
        with self.assertRaises(ValueError):
            mentors.mentor_opt_in(_profile(boundaries={"wont": [""]}))
        with self.assertRaises(ValueError):
            mentors.mentor_opt_in(_profile(boundaries={"note": "x" * 501}))

    def test_bad_availability_windows_rejected(self):
        with self.assertRaises(ValueError):
            mentors.mentor_opt_in(_profile(availability_windows="fridays"))
        with self.assertRaises(ValueError):
            mentors.mentor_opt_in(_profile(availability_windows=[{"start": "9"}]))

    def test_card_edit_allows_new_fields(self):
        mentors.mentor_opt_in(_profile())
        res = mentors.my_mentor_card(
            {"boundaries": {"offers": ["career advice"], "wont": [], "note": ""}}
        )
        self.assertTrue(res["ok"])
        self.assertEqual(res["card"]["boundaries"]["offers"], ["career advice"])


class QuestionnaireV2Test(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        mentors.MENTORS_FILE = tmp / "mentors.json"
        mentors.OUTBOX_DIR = tmp / "outbox"
        mentors.mentor_opt_in(_profile())

    def tearDown(self):
        self._tmp.cleanup()

    def _answers(self, **over):
        a = {
            "industry": "software",
            "target_role": "Staff Engineer",
            "topics_ranked": ["interviewing"],
            "goal": "Break into staff engineering",
        }
        a.update(over)
        return a

    def test_v2_fields_echoed(self):
        res = mentors.matchmake(
            self._answers(
                context="5y backend, no system design reps",
                urgency="this_week",
                expected_outcome="A system-design study plan",
            )
        )
        self.assertTrue(res["ok"])
        self.assertEqual(res["mentee_context"], "5y backend, no system design reps")
        self.assertEqual(res["mentee_urgency"], "this_week")
        self.assertEqual(res["mentee_expected_outcome"], "A system-design study plan")
        self.assertIn("urgent", res["guidance"].lower())

    def test_urgency_defaults_and_validates(self):
        res = mentors.matchmake(self._answers(urgency="ASAP"))
        self.assertEqual(res["mentee_urgency"], "exploring")

    def test_identity_preferences_voluntary_and_unranked(self):
        plain = mentors.matchmake(self._answers())
        with_prefs = mentors.matchmake(
            self._answers(identity_preferences={"prefer": ["women in eng"]})
        )
        self.assertEqual(
            [m["score"] for m in plain["matches"]],
            [m["score"] for m in with_prefs["matches"]],
        )
        self.assertEqual(
            with_prefs["identity_preferences"], {"prefer": ["women in eng"]}
        )
        self.assertIn("never used for ranking", with_prefs["guidance"])

    def test_consent_preview_redacts_contact(self):
        res = mentors.matchmake(self._answers(), consent_preview=True)
        self.assertTrue(res["ok"])
        self.assertTrue(res["consent_preview"])
        for m in res["matches"]:
            self.assertNotIn("linkedin_url", m)
            self.assertIn("topics", m)
            self.assertIn("mentor_id", m)

    def test_consent_preview_respects_linkedin_public(self):
        mentors.mentor_opt_in(
            _profile(
                linkedin_url="https://www.linkedin.com/in/grace-hopper",
                preferred_contact="linkedin_public",
            )
        )
        res = mentors.matchmake(self._answers(), consent_preview=True)
        public = [m for m in res["matches"] if m.get("linkedin_url")]
        self.assertTrue(public, "linkedin_public mentor should show URL in preview")

    def test_default_mode_unchanged_for_cold_path(self):
        res = mentors.matchmake(self._answers())
        self.assertFalse(res["consent_preview"])
        self.assertTrue(all("linkedin_url" in m for m in res["matches"]))


if __name__ == "__main__":
    unittest.main()

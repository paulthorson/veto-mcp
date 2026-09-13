#!/usr/bin/env python3
"""Tests for the two-sided consent handshake (Initiative 07, epic 3).

Covers the proof of value: a match cannot become an introduction without
explicit consent from both people, and either person can withdraw.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import mentors  # noqa: E402
from initiatives.i07 import consent  # noqa: E402


def _mentor_profile(i: int = 0, **over) -> dict:
    p = {
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
    p.update(over)
    return p


class ConsentTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        mentors.MENTORS_FILE = tmp / "mentors.json"
        consent.HANDSHAKES_FILE = tmp / "handshakes.json"
        consent.AUDIT_FILE = tmp / "consent_audit.jsonl"
        from initiatives.i07 import safety

        safety.SAFETY_FILE = tmp / "safety.json"
        safety.REPORTS_FILE = tmp / "reports.jsonl"
        safety.reset_rate_limits()
        self.safety = safety
        self.mentor_id = mentors.mentor_opt_in(_mentor_profile(0))["card"]["id"]

    def tearDown(self):
        self._tmp.cleanup()

    def _request(self, **kw):
        kw.setdefault("mentor_id", self.mentor_id)
        kw.setdefault("mentee_id", "me")
        kw.setdefault("mentee_label", "PT")
        kw.setdefault("goal", "Break into staff engineering")
        kw["synthetic"] = True
        return consent.request_introduction(**kw)

    # -- request validation -------------------------------------------------

    def test_request_without_goal_is_rejected(self):
        res = consent.request_introduction(
            self.mentor_id, "me", "PT", "", synthetic=True
        )
        self.assertFalse(res["ok"])
        self.assertIn("goal", res["error"])

    def test_request_without_label_is_rejected(self):
        res = self._request(mentee_label="")
        self.assertFalse(res["ok"])

    def test_request_unknown_mentor_rejected(self):
        res = self._request(mentor_id="nope")
        self.assertFalse(res["ok"])

    def test_request_creates_awaiting_mentor(self):
        res = self._request()
        self.assertTrue(res["ok"])
        self.assertFalse(res["sent"])
        self.assertIn("Nothing was sent", res["note"])
        hs = res["handshake"]
        self.assertEqual(hs["state"], "awaiting_mentor")
        self.assertIsNotNone(hs["mentee_consented_at"])
        self.assertIsNone(hs["mentor_consented_at"])
        self.assertTrue(hs["id"].startswith("SYNTHETIC-"))

    def test_duplicate_pending_rejected(self):
        self.assertTrue(self._request()["ok"])
        res = self._request()
        self.assertFalse(res["ok"])
        self.assertIn("already pending", res["error"])

    def test_daily_rate_limit(self):
        ids = []
        for i in range(consent.MAX_REQUESTS_PER_DAY):
            mid = mentors.mentor_opt_in(_mentor_profile(i + 1))["card"]["id"]
            ids.append(mid)
            res = self._request(mentor_id=mid)
            self.assertTrue(res["ok"], res)
        mid = mentors.mentor_opt_in(_mentor_profile(99))["card"]["id"]
        res = self._request(mentor_id=mid)
        self.assertFalse(res["ok"])
        self.assertIn("rate limit", res["error"])

    # -- revelation is sealed until mutual -----------------------------------

    def test_reveal_refused_before_mutual(self):
        res = self._request()
        hs_id = res["handshake"]["id"]
        for actor in ("me", self.mentor_id):
            r = consent.reveal_contact(hs_id, actor)
            self.assertFalse(r["ok"], actor)
            self.assertIn("sealed", r["error"])

    def test_mentor_respond_requires_channel(self):
        res = self._request()
        r = consent.mentor_respond(res["handshake"]["id"], "approve", channel="")
        self.assertFalse(r["ok"])
        self.assertIn("channel", r["error"])

    def test_mentor_respond_bad_decision(self):
        res = self._request()
        r = consent.mentor_respond(
            res["handshake"]["id"], "maybe", channel="email"
        )
        self.assertFalse(r["ok"])

    def test_approve_reaches_mutual_and_unseals(self):
        res = self._request()
        hs_id = res["handshake"]["id"]
        r = consent.mentor_respond(hs_id, "approve", channel="linkedin_dm")
        self.assertTrue(r["ok"])
        self.assertEqual(r["handshake"]["state"], "mutual")
        self.assertIsNotNone(r["handshake"]["mentor_consented_at"])

        mentee_view = consent.reveal_contact(hs_id, "me")
        self.assertTrue(mentee_view["ok"])
        self.assertIn("linkedin_url", mentee_view["mentor_contact"])
        mentor_view = consent.reveal_contact(hs_id, self.mentor_id)
        self.assertTrue(mentor_view["ok"])
        self.assertIn("mentee_contact", mentor_view)

    def test_non_party_cannot_reveal(self):
        res = self._request()
        hs_id = res["handshake"]["id"]
        consent.mentor_respond(hs_id, "approve", channel="email")
        r = consent.reveal_contact(hs_id, "stranger")
        self.assertFalse(r["ok"])

    # -- decline + cooldown ---------------------------------------------------

    def test_decline_and_cooldown(self):
        res = self._request()
        hs_id = res["handshake"]["id"]
        r = consent.mentor_respond(hs_id, "decline", channel="email")
        self.assertTrue(r["ok"])
        self.assertEqual(r["handshake"]["state"], "declined")
        res2 = self._request()
        self.assertFalse(res2["ok"])
        self.assertIn("cooldown", res2["error"])

    # -- withdrawal: either party, any stage ----------------------------------

    def test_mentee_can_withdraw_pending(self):
        res = self._request()
        hs_id = res["handshake"]["id"]
        r = consent.withdraw(hs_id, "me", reason="changed my mind")
        self.assertTrue(r["ok"])
        self.assertEqual(r["handshake"]["state"], "withdrawn")

    def test_mentor_can_withdraw_after_mutual_and_seals_reveal(self):
        res = self._request()
        hs_id = res["handshake"]["id"]
        consent.mentor_respond(hs_id, "approve", channel="email")
        self.assertTrue(consent.reveal_contact(hs_id, "me")["ok"])
        r = consent.withdraw(hs_id, self.mentor_id)
        self.assertTrue(r["ok"])
        r2 = consent.reveal_contact(hs_id, "me")
        self.assertFalse(r2["ok"])
        self.assertIn("sealed", r2["error"])

    def test_withdraw_twice_rejected(self):
        res = self._request()
        hs_id = res["handshake"]["id"]
        consent.withdraw(hs_id, "me")
        r = consent.withdraw(hs_id, "me")
        self.assertFalse(r["ok"])

    def test_non_party_cannot_withdraw(self):
        res = self._request()
        r = consent.withdraw(res["handshake"]["id"], "stranger")
        self.assertFalse(r["ok"])

    # -- expiry ----------------------------------------------------------------

    def test_approve_consumes_capacity(self):
        res = self._request()
        hs_id = res["handshake"]["id"]
        before = mentors.remaining_capacity(
            mentors._load_directory()[self.mentor_id]
        )
        consent.mentor_respond(hs_id, "approve", channel="email")
        after = mentors.remaining_capacity(
            mentors._load_directory()[self.mentor_id]
        )
        self.assertEqual(after, before - 1)

    def test_approve_refused_when_capacity_filled(self):
        res = self._request()
        hs_id = res["handshake"]["id"]
        # Fill the mentor's capacity out from under the pending request.
        directory = mentors._load_directory()
        directory[self.mentor_id]["mentee_count"] = 99
        mentors._save_directory(directory)
        r = consent.mentor_respond(hs_id, "approve", channel="email")
        self.assertFalse(r["ok"])
        self.assertIn("capacity", r["error"])

    def test_lazy_expiry_on_read(self):
        res = self._request()
        hs_id = res["handshake"]["id"]
        store = consent._load()
        past = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        store[hs_id]["expires_at"] = past
        consent._save(store)
        # No explicit expire_stale call: the read itself enforces the TTL.
        got = consent.get_handshake(hs_id, "me")
        self.assertEqual(got["handshake"]["state"], "expired")

    def test_expire_stale(self):
        res = self._request()
        hs_id = res["handshake"]["id"]
        store = consent._load()
        past = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        store[hs_id]["expires_at"] = past
        consent._save(store)
        out = consent.expire_stale()
        self.assertIn(hs_id, out["expired"])
        got = consent.get_handshake(hs_id, "me")
        self.assertEqual(got["handshake"]["state"], "expired")
        # Re-request allowed after expiry.
        res2 = self._request()
        self.assertTrue(res2["ok"], res2)

    # -- audit trail ------------------------------------------------------------

    def test_audit_trail_records_transitions(self):
        res = self._request()
        hs_id = res["handshake"]["id"]
        consent.mentor_respond(hs_id, "approve", channel="email")
        consent.withdraw(hs_id, "me")
        trail = consent.audit_trail(hs_id)
        events = [e["event"] for e in trail]
        self.assertEqual(events, ["request", "mentor_approve", "withdraw"])

    def test_audit_has_no_delete_api(self):
        for name in dir(consent):
            self.assertNotIn("delete", name.lower().replace("_audit", ""),
                             f"unexpected mutating audit API: {name}")

    # -- previews ----------------------------------------------------------------

    def test_redacted_preview_hides_contact_by_default(self):
        card = mentors._load_directory()[self.mentor_id]
        preview = consent.redacted_preview(card)
        self.assertNotIn("linkedin_url", preview)
        self.assertIn("topics", preview)

    def test_redacted_preview_respects_linkedin_public_opt_in(self):
        mid = mentors.mentor_opt_in(
            _mentor_profile(7, preferred_contact="linkedin_public")
        )["card"]["id"]
        card = mentors._load_directory()[mid]
        preview = consent.redacted_preview(card)
        self.assertIn("linkedin_url", preview)


if __name__ == "__main__":
    unittest.main()

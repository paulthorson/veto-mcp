#!/usr/bin/env python3
"""Tests for Initiative 07 safety controls: block, report, rate limits,
deletion, and the segregation guard (epic 6).
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import mentors  # noqa: E402
from initiatives.i07 import consent, safety  # noqa: E402


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


class SafetyTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        mentors.MENTORS_FILE = tmp / "mentors.json"
        consent.HANDSHAKES_FILE = tmp / "handshakes.json"
        consent.AUDIT_FILE = tmp / "consent_audit.jsonl"
        safety.SAFETY_FILE = tmp / "safety.json"
        safety.REPORTS_FILE = tmp / "reports.jsonl"
        safety.reset_rate_limits()
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

    # -- block -----------------------------------------------------------------

    def test_block_prevents_request(self):
        self.assertTrue(safety.block_actor("me", self.mentor_id)["ok"])
        res = self._request()
        self.assertFalse(res["ok"])
        self.assertIn("block", res["error"])

    def test_block_is_directional_for_check(self):
        self.assertTrue(safety.block_actor("me", self.mentor_id)["ok"])
        self.assertTrue(safety.is_blocked("me", self.mentor_id))
        self.assertFalse(safety.is_blocked(self.mentor_id, "me"))
        # ...but consent is refused if EITHER side blocked the other.
        check = safety.consent_block_check("me", self.mentor_id)
        self.assertTrue(check["blocked"])
        check2 = safety.consent_block_check(self.mentor_id, "me")
        self.assertTrue(check2["blocked"])

    def test_block_withdraws_pending_handshake(self):
        res = self._request()
        hs_id = res["handshake"]["id"]
        out = safety.block_actor("me", self.mentor_id)
        self.assertIn(hs_id, out["withdrawn_handshakes"])
        got = consent.get_handshake(hs_id, "me")
        self.assertEqual(got["handshake"]["state"], "withdrawn")
        # The audit honestly records a system withdrawal, not the mentee.
        trail = consent.audit_trail(hs_id)
        withdrawals = [e for e in trail if e["event"] == "withdraw"]
        self.assertEqual(len(withdrawals), 1)
        self.assertEqual(withdrawals[0]["actor"], "system")

    def test_withdraw_rejects_unknown_actor(self):
        res = self._request()
        r = consent.withdraw(res["handshake"]["id"], "intruder")
        self.assertFalse(r["ok"])

    def test_block_self_rejected(self):
        res = safety.block_actor("me", "me")
        self.assertFalse(res["ok"])

    def test_unblock(self):
        safety.block_actor("me", self.mentor_id)
        self.assertTrue(safety.unblock_actor("me", self.mentor_id)["ok"])
        self.assertFalse(safety.is_blocked("me", self.mentor_id))
        self.assertTrue(self._request()["ok"])

    # -- report + quarantine ----------------------------------------------------

    def test_report_bad_category_rejected(self):
        res = safety.report("me", self.mentor_id, "rude")
        self.assertFalse(res["ok"])

    def test_two_distinct_reporters_quarantine(self):
        r1 = safety.report("alice", self.mentor_id, "spam", detail="d1")
        self.assertTrue(r1["ok"])
        self.assertFalse(r1["quarantined"])
        self.assertFalse(safety.is_quarantined(self.mentor_id))
        r2 = safety.report("bob", self.mentor_id, "spam", detail="d2")
        self.assertTrue(r2["ok"])
        self.assertTrue(r2["quarantined"])
        self.assertTrue(safety.is_quarantined(self.mentor_id))

    def test_same_reporter_twice_does_not_quarantine(self):
        safety.report("alice", self.mentor_id, "spam")
        r = safety.report("alice", self.mentor_id, "harassment")
        self.assertTrue(r["ok"])
        self.assertFalse(r["quarantined"])

    def test_quarantined_mentor_blocked_from_consent(self):
        safety.report("alice", self.mentor_id, "spam")
        safety.report("bob", self.mentor_id, "spam")
        res = self._request()
        self.assertFalse(res["ok"])
        self.assertIn("safety review", res["error"])

    def test_quarantine_withdraws_pending_handshakes(self):
        res = self._request()
        hs_id = res["handshake"]["id"]
        safety.report("alice", self.mentor_id, "spam")
        safety.report("bob", self.mentor_id, "spam")
        got = consent.get_handshake(hs_id, "me")
        self.assertEqual(got["handshake"]["state"], "withdrawn")

    def test_clear_quarantine_requires_human(self):
        safety.report("alice", self.mentor_id, "spam")
        safety.report("bob", self.mentor_id, "spam")
        bad = safety.clear_quarantine(self.mentor_id, reviewed_by="")
        self.assertFalse(bad["ok"])
        good = safety.clear_quarantine(self.mentor_id, reviewed_by="paul")
        self.assertTrue(good["ok"])
        self.assertFalse(safety.is_quarantined(self.mentor_id))

    # -- rate limits --------------------------------------------------------------

    def test_token_bucket_exhaustion(self):
        limits = {"ping": (2, 0.0)}
        self.assertTrue(safety.check_rate_limit("u", "ping", limits=limits))
        self.assertTrue(safety.check_rate_limit("u", "ping", limits=limits))
        self.assertFalse(safety.check_rate_limit("u", "ping", limits=limits))

    def test_rate_limit_scoped_per_actor(self):
        limits = {"ping": (1, 0.0)}
        self.assertTrue(safety.check_rate_limit("u1", "ping", limits=limits))
        self.assertTrue(safety.check_rate_limit("u2", "ping", limits=limits))

    # -- deletion -------------------------------------------------------------------

    def test_delete_mentor_data_erases_everything(self):
        res = self._request()
        hs_id = res["handshake"]["id"]
        safety.block_actor("someone", self.mentor_id, reason="test reason")
        out = safety.delete_mentor_data(self.mentor_id, requested_by="me")
        self.assertTrue(out["ok"])
        self.assertTrue(out["removed"]["card"])
        self.assertEqual(out["removed"]["handshakes"], 1)
        # Card gone from directory.
        self.assertNotIn(self.mentor_id, mentors._load_directory())
        # Handshake is a tombstone with no PII.
        store = consent._load()
        tomb = store[hs_id]
        self.assertTrue(tomb.get("deleted"))
        self.assertNotIn("goal", tomb)
        self.assertNotIn("mentee_label", tomb)
        # Audit trail keeps a tombstone entry, not PII.
        trail = consent.audit_trail()
        self.assertTrue(any(e["event"] == "deletion" for e in trail))
        # Block entry survives (id only), reason scrubbed.
        self.assertTrue(safety.is_blocked("someone", self.mentor_id))

    def test_delete_requires_requester(self):
        res = safety.delete_mentor_data(self.mentor_id, requested_by="")
        self.assertFalse(res["ok"])

    def test_delete_mentee_data(self):
        self._request()
        out = safety.delete_mentee_data("me", requested_by="me")
        self.assertTrue(out["ok"])
        self.assertEqual(out["removed"]["handshakes"], 1)
        for hs in consent._load().values():
            self.assertNotIn("goal", hs)

    # -- discovery exclusions ------------------------------------------------------

    def test_discovery_exclusions_union_blocked_and_quarantined(self):
        other = mentors.mentor_opt_in(
            {
                "name": "Other",
                "industry": "software",
                "role": "Engineer",
                "seniority": "ic4",
                "topics": ["interviewing"],
                "linkedin_url": "https://www.linkedin.com/in/synthetic-other",
                "max_mentees": 3,
            }
        )["card"]["id"]
        safety.block_actor("me", self.mentor_id)
        safety.report("alice", other, "spam")
        safety.report("bob", other, "spam")
        excluded = safety.discovery_exclusions("me")
        self.assertIn(self.mentor_id, excluded)
        self.assertIn(other, excluded)

    def test_excluded_mentors_hidden_from_matchmake(self):
        safety.block_actor("me", self.mentor_id)
        excluded = safety.discovery_exclusions("me")
        res = mentors.matchmake(
            {
                "industry": "software",
                "target_role": "Engineer",
                "topics_ranked": ["interviewing"],
                "goal": "x",
            },
            consent_preview=True,
            exclude_mentor_ids=excluded,
        )
        self.assertEqual(res["matches"], [])
        self.assertIn("exclusions", res["guidance"])

    # -- segregation ---------------------------------------------------------------
    # (section header restored after exclusion tests were inserted above)

    def test_segregation_check_clean(self):
        self._request()
        out = safety.segregation_check()
        self.assertTrue(out["ok"], out["violations"])
        self.assertEqual(out["violations"], [])

    def test_segregation_check_catches_application_reference(self):
        real_base = mentors.BASE_DIR
        tmp_base = Path(self._tmp.name) / "fakeproj"
        tmp_base.mkdir()
        try:
            mentors.BASE_DIR = tmp_base
            (tmp_base / "applications.json").write_text(
                json.dumps([{"id": "app-1", "note": f"mentor {self.mentor_id}"}]),
                encoding="utf-8",
            )
            out = safety.segregation_check()
            self.assertFalse(out["ok"])
            self.assertTrue(any(self.mentor_id in v for v in out["violations"]))
        finally:
            mentors.BASE_DIR = real_base


if __name__ == "__main__":
    unittest.main()

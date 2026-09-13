#!/usr/bin/env python3
"""Tests for the Initiative 07 warm-path planner (epic 5): drafts only,
never sends; honest empty states; no invented people.
"""

from __future__ import annotations

import inspect
import sys
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import network_crm  # noqa: E402
import referrals  # noqa: E402
from initiatives.i07 import warm_path  # noqa: E402


class WarmPathTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        network_crm.NETWORK_FILE = tmp / "network.json"
        referrals.CONNECTIONS_CSV = tmp / "connections.csv"
        referrals.CONNECTIONS_JSON = tmp / "connections.json"
        warm_path.DRAFT_OUTBOX = tmp / "draft_outbox.jsonl"

    def tearDown(self):
        self._tmp.cleanup()

    def _contact(self, name="Ada Lovelace", company="Initech", role="Engineer"):
        c = network_crm.add_contact(name=name, company=company, role=role)
        return c["id"]

    # -- planner ------------------------------------------------------------------

    def test_empty_network_honest_empty_plan(self):
        res = warm_path.plan_warm_path("Initech")
        self.assertTrue(res["ok"])
        self.assertEqual(res["plans"], [])
        self.assertIn("never", res["guidance"])
        self.assertIn("invent", res["guidance"])

    def test_crm_path_produces_draft(self):
        cid = self._contact()
        network_crm.log_interaction(cid, "coffee", "Great chat about Initech")
        res = warm_path.plan_warm_path("Initech")
        self.assertTrue(res["ok"])
        self.assertEqual(len(res["plans"]), 1)
        plan = res["plans"][0]
        self.assertEqual(plan["source"], "network_crm")
        self.assertEqual(plan["degrees"], 1)
        self.assertIn("Initech", plan["draft"]["body"])
        self.assertTrue(res["honesty_checklist"])

    def test_drafts_recorded_in_outbox_as_draft(self):
        self._contact()
        warm_path.plan_warm_path("Initech")
        drafts = warm_path.list_drafts()
        self.assertEqual(len(drafts), 1)
        self.assertEqual(drafts[0]["status"], "draft")

    def test_no_send_path_exists(self):
        for mod in (warm_path, network_crm, referrals):
            for name, fn in inspect.getmembers(mod, inspect.isfunction):
                self.assertNotIn(
                    "send",
                    name.lower(),
                    f"{mod.__name__}.{name} looks like a send path",
                )

    def test_discard_draft(self):
        self._contact()
        warm_path.plan_warm_path("Initech")
        draft_id = warm_path.list_drafts()[0]["draft_id"]
        self.assertTrue(warm_path.discard_draft(draft_id)["ok"])
        self.assertEqual(warm_path.list_drafts(), [])
        self.assertFalse(warm_path.discard_draft("nope")["ok"])

    def test_requires_company(self):
        self.assertFalse(warm_path.plan_warm_path("")["ok"])

    def test_second_degree_path(self):
        cid = self._contact(name="Grace Hopper", company="Acme")
        network_crm.log_interaction(cid, "email", "Grace mentioned Initech hiring")
        res = warm_path.plan_warm_path("Initech")
        self.assertTrue(res["ok"])
        self.assertTrue(res["plans"])
        self.assertEqual(res["plans"][0]["degrees"], 2)

    # -- network_crm draft logging ---------------------------------------------------

    def test_log_outreach_draft(self):
        cid = self._contact()
        d = network_crm.log_outreach_draft(
            cid, "linkedin", "Hello", "Hi Ada, ...", target_company="Initech"
        )
        self.assertEqual(d["status"], "draft")
        contact = network_crm._get_contact(network_crm._load_network(), cid)
        self.assertEqual(len(contact["outreach_drafts"]), 1)

    def test_log_outreach_draft_validates(self):
        cid = self._contact()
        with self.assertRaises(ValueError):
            network_crm.log_outreach_draft(cid, "", "s", "b")
        with self.assertRaises(ValueError):
            network_crm.log_outreach_draft(cid, "email", "s", "  ")

    # -- referrals plan_outreach_drafts -----------------------------------------------

    def test_plan_outreach_drafts(self):
        prospects = [
            {
                "name": "Alan Turing",
                "company": "Initech",
                "position": "Engineer",
                "evidence": ["same company"],
                "reasons": ["works at Initech"],
            }
        ]
        drafts = referrals.plan_outreach_drafts(
            prospects, job={"company": "Initech", "title": "Engineer"}
        )
        self.assertEqual(len(drafts), 1)
        self.assertEqual(drafts[0]["status"], "draft")
        self.assertEqual(drafts[0]["evidence"], ["same company"])

    def test_plan_outreach_drafts_caps(self):
        prospects = [
            {"name": f"P{i}", "company": "Initech", "position": "E"} for i in range(10)
        ]
        drafts = referrals.plan_outreach_drafts(prospects, max_drafts=3)
        self.assertEqual(len(drafts), 3)


if __name__ == "__main__":
    unittest.main()

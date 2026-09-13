"""Tests for Initiative 05 evidence library (Epic 2).

All fixtures are synthetic and labeled as such. Every store write goes
to a temp dir — the real ``evidence_library/`` tree is never touched.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from initiatives.i05 import contracts, evidence_library


def _profile() -> dict:
    return {
        "full_name": "Synthetic Fixture",
        "skills": ["Python", "Docker"],
        "linkedin_url": "https://example.com/in/fixture",
        "experience": [
            {
                "title": "Backend Engineer",
                "company": "FixtureCorp",
                "bullets": [
                    "Shipped Python services handling 1M requests a day.",
                    "Mentored junior engineers.",
                ],
            }
        ],
    }


class EvidenceLibraryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_build_from_profile_derives_only_real_facts(self):
        items = evidence_library.build_from_profile(
            _profile(), library_dir=self.dir)
        kinds = [i["kind"] for i in items]
        self.assertIn("achievement", kinds)
        self.assertIn("metric", kinds)  # the "1M requests" bullet
        self.assertIn("approved_phrase", kinds)  # skills
        self.assertIn("portfolio_link", kinds)  # linkedin_url
        # Everything starts as a draft.
        self.assertTrue(all(i["approved"] is False for i in items))
        # Every item satisfies the 01-02 evidence contract.
        for item in items:
            self.assertEqual(contracts.validate_evidence(item), [])
        # Text is verbatim from the profile — nothing invented.
        texts = [i["text"] for i in items]
        self.assertIn(
            "Shipped Python services handling 1M requests a day.", texts)

    def test_add_item_requires_text_and_source(self):
        with self.assertRaises(ValueError):
            evidence_library.add_item("achievement", "", "experience[0]",
                                      library_dir=self.dir)
        with self.assertRaises(ValueError):
            evidence_library.add_item("achievement", "Did things.", "",
                                      library_dir=self.dir)
        with self.assertRaises(ValueError):
            evidence_library.add_item("rumor", "Did things.", "experience[0]",
                                      library_dir=self.dir)

    def test_approve_and_use_flow(self):
        item = evidence_library.add_item(
            "achievement", "Synthetic win.", "experience[0].bullets[0]",
            library_dir=self.dir)
        self.assertFalse(item["approved"])
        evidence_library.approve_item(item["evidence_id"],
                                      library_dir=self.dir)
        got = evidence_library.get_item(item["evidence_id"],
                                        library_dir=self.dir)
        self.assertTrue(got["approved"])
        self.assertIn("approved_at", got)

    def test_edit_resets_approval(self):
        item = evidence_library.add_item(
            "achievement", "Synthetic win.", "experience[0].bullets[0]",
            library_dir=self.dir)
        evidence_library.approve_item(item["evidence_id"],
                                      library_dir=self.dir)
        evidence_library.update_item(
            item["evidence_id"], "Synthetic win, revised.",
            library_dir=self.dir)
        got = evidence_library.get_item(item["evidence_id"],
                                        library_dir=self.dir)
        self.assertFalse(got["approved"])
        self.assertNotIn("approved_at", got)

    def test_delete_protects_approved_items(self):
        item = evidence_library.add_item(
            "achievement", "Synthetic win.", "experience[0].bullets[0]",
            library_dir=self.dir)
        evidence_library.approve_item(item["evidence_id"],
                                      library_dir=self.dir)
        with self.assertRaises(ValueError):
            evidence_library.delete_item(item["evidence_id"],
                                         library_dir=self.dir)
        # Unknown id -> False, not an exception.
        self.assertFalse(
            evidence_library.delete_item("ev_nope", library_dir=self.dir))

    def test_find_returns_only_approved(self):
        a = evidence_library.add_item(
            "achievement", "Shipped Python services.",
            "experience[0].bullets[0]", library_dir=self.dir)
        b = evidence_library.add_item(
            "achievement", "Shipped Python services.",
            "experience[0].bullets[0]", library_dir=self.dir)
        evidence_library.approve_item(a["evidence_id"],
                                      library_dir=self.dir)
        hits = evidence_library.find_for_requirement(
            "need python experience", library_dir=self.dir)
        self.assertEqual([h["evidence_id"] for h in hits],
                         [a["evidence_id"]])
        self.assertNotIn(b["evidence_id"], [h["evidence_id"] for h in hits])

    def test_find_empty_when_nothing_relevant(self):
        evidence_library.build_from_profile(_profile(), library_dir=self.dir)
        # Nothing approved yet -> no hits even with overlap.
        self.assertEqual(
            evidence_library.find_for_requirement(
                "python", library_dir=self.dir), [])
        self.assertEqual(
            evidence_library.find_for_requirement("", library_dir=self.dir),
            [])

    def test_record_use_tracks_provenance(self):
        item = evidence_library.add_item(
            "achievement", "Synthetic win.", "experience[0].bullets[0]",
            library_dir=self.dir)
        evidence_library.record_use(item["evidence_id"], "var_abc",
                                    library_dir=self.dir)
        got = evidence_library.get_item(item["evidence_id"],
                                        library_dir=self.dir)
        self.assertIn("var_abc", got["used_in"])
        with self.assertRaises(KeyError):
            evidence_library.record_use("ev_nope", "var_abc",
                                        library_dir=self.dir)

    def test_list_filters(self):
        evidence_library.build_from_profile(_profile(), library_dir=self.dir)
        metrics = evidence_library.list_items(kind="metric",
                                              library_dir=self.dir)
        self.assertTrue(metrics)
        self.assertTrue(all(m["kind"] == "metric" for m in metrics))
        self.assertEqual(
            evidence_library.list_items(approved_only=True,
                                        library_dir=self.dir), [])

    def test_corrupt_store_reads_empty(self):
        (self.dir / "library.json").write_text("{nope", encoding="utf-8")
        self.assertEqual(
            evidence_library.list_items(library_dir=self.dir), [])


if __name__ == "__main__":
    unittest.main()


class EvidenceLibraryEdgeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_build_from_empty_profile_yields_nothing(self):
        self.assertEqual(
            evidence_library.build_from_profile({}, library_dir=self.dir),
            [])
        self.assertEqual(
            evidence_library.list_items(library_dir=self.dir), [])

    def test_approve_unknown_raises(self):
        with self.assertRaises(KeyError):
            evidence_library.approve_item("ev_nope", library_dir=self.dir)

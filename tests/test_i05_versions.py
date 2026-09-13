"""Tests for Initiative 05 versioned resume variants (Epic 1).

All fixtures are synthetic and labeled as such. Every store write goes
to a temp dir — the real ``resume_variants/`` tree is never touched.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import tailor
from initiatives.i05 import versions


def _profile() -> dict:
    return {
        "full_name": "Synthetic Fixture",
        "email": "fixture@example.com",
        "summary": "Synthetic fixture profile for tests.",
        "skills": ["Python", "PostgreSQL"],
        "experience": [
            {
                "title": "Backend Engineer",
                "company": "FixtureCorp",
                "dates": "2020 - 2024",
                "bullets": [
                    "Shipped Python services handling 1M requests a day.",
                    "Cut PostgreSQL query times by half.",
                ],
            }
        ],
        "education": [
            {"degree": "B.S.", "school": "Fixture University",
             "dates": "2016 - 2020"}
        ],
    }


def _job() -> dict:
    return {
        "id": "job-synth-1",
        "title": "Backend Engineer",
        "company": "HiringCorp",
        "description": "We need Python and PostgreSQL experience.",
    }


class VersionLifecycleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_create_base_and_branch(self):
        base = versions.create_base(_profile(), variants_dir=self.dir)
        self.assertIsNone(base["parent_variant"])
        self.assertEqual(base["branch_name"], "base")
        branch = versions.create_variant(
            "backend-fixturecorp", job_id="job-synth-1",
            parent_variant_id=base["variant_id"],
            initial_resume_md="# Resume\n",
            variants_dir=self.dir)
        self.assertEqual(branch["parent_variant"], base["variant_id"])

    def test_commit_chains_parents(self):
        v = versions.create_variant("b", variants_dir=self.dir,
                                    initial_resume_md="v1")
        v1 = v["versions"][0]["version_id"]
        v2 = versions.commit_version(
            v["variant_id"], "v2", variants_dir=self.dir)
        self.assertEqual(v2["parent_version"], v1)
        hist = versions.history(v["variant_id"], variants_dir=self.dir)
        self.assertEqual(len(hist), 2)
        self.assertEqual(hist[0]["version_id"], v2["version_id"])
        self.assertTrue(hist[0]["is_current"])

    def test_restore_any_prior_version_byte_identical(self):
        v = versions.create_variant("b", variants_dir=self.dir,
                                    initial_resume_md="first")
        first_id = v["versions"][0]["version_id"]
        versions.commit_version(v["variant_id"], "second",
                                variants_dir=self.dir)
        restored = versions.restore_version(
            v["variant_id"], first_id, variants_dir=self.dir)
        self.assertEqual(restored["resume_md"], "first")
        # Restoring with no id gives the head.
        head = versions.restore_version(v["variant_id"],
                                        variants_dir=self.dir)
        self.assertEqual(head["resume_md"], "second")

    def test_restore_unknown_raises(self):
        v = versions.create_variant("b", variants_dir=self.dir,
                                    initial_resume_md="x")
        with self.assertRaises(KeyError):
            versions.restore_version(v["variant_id"], "ver_nope",
                                     variants_dir=self.dir)
        with self.assertRaises(KeyError):
            versions.restore_version("var_nope", variants_dir=self.dir)

    def test_checkout_repoints_head_with_audit(self):
        v = versions.create_variant("b", variants_dir=self.dir,
                                    initial_resume_md="first")
        first_id = v["versions"][0]["version_id"]
        v2 = versions.commit_version(v["variant_id"], "second",
                                     variants_dir=self.dir)
        self.assertNotEqual(first_id, v2["version_id"])
        content = versions.checkout_version(
            v["variant_id"], first_id, variants_dir=self.dir)
        self.assertEqual(content["resume_md"], "first")
        variant = versions.get_variant(v["variant_id"],
                                       variants_dir=self.dir)
        self.assertEqual(variant["current_version"], first_id)
        self.assertEqual(variant["audit"][-1]["action"], "checkout")
        # Old versions are all still present — history is append-only.
        self.assertEqual(len(variant["versions"]), 2)

    def test_approve_version_marks_approved(self):
        v = versions.create_variant("b", variants_dir=self.dir,
                                    initial_resume_md="x")
        vid = v["versions"][0]["version_id"]
        approved = versions.approve_version(v["variant_id"], vid,
                                            variants_dir=self.dir)
        self.assertTrue(approved["provenance"]["approved"])
        self.assertIn("approved_at", approved["provenance"])

    def test_list_variants(self):
        versions.create_variant("one", variants_dir=self.dir,
                                initial_resume_md="x")
        versions.create_variant("two", variants_dir=self.dir,
                                initial_resume_md="y")
        listed = versions.list_variants(variants_dir=self.dir)
        self.assertEqual(len(listed), 2)
        self.assertEqual({l["branch_name"] for l in listed}, {"one", "two"})


class ClaimTracingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _tailored_variant(self):
        result = tailor.tailor_with_provenance(
            _profile(), _job(),
            evidence_links=[{
                "link_id": "lnk_synth_py",
                "requirement_id": "req_synth_python",
                "evidence_id": "ev_synth_py",
                "quote": "Shipped Python services handling 1M requests",
                "confidence": 0.9,
            }])
        variant = versions.create_variant(
            "backend-hiringcorp", job_id="job-synth-1",
            initial_resume_md=result["resume_md"],
            provenance=result["provenance"],
            variants_dir=self.dir)
        return variant, result

    def test_every_statement_maps_to_evidence(self):
        variant, result = self._tailored_variant()
        vid = variant["versions"][0]["version_id"]
        for entry in result["provenance"]["statement_map"]:
            hits = versions.trace_statement(
                variant["variant_id"], vid, entry["statement"],
                variants_dir=self.dir)
            self.assertTrue(hits, f"untraceable: {entry['statement']}")
            self.assertTrue(hits[0]["evidence_ids"])

    def test_link_ids_flow_into_trace(self):
        variant, result = self._tailored_variant()
        vid = variant["versions"][0]["version_id"]
        all_link_ids = [
            lid
            for e in result["provenance"]["statement_map"]
            for lid in e["link_ids"]
        ]
        self.assertIn("lnk_synth_py", all_link_ids)
        hits = versions.trace_statement(
            variant["variant_id"], vid,
            "Shipped Python services handling 1M requests a day.",
            variants_dir=self.dir)
        self.assertIn("lnk_synth_py", hits[0]["link_ids"])

    def test_untraced_statements_reports_gaps(self):
        variant, _ = self._tailored_variant()
        vid = variant["versions"][0]["version_id"]
        gaps = versions.untraced_statements(
            variant["variant_id"], vid, variants_dir=self.dir)
        self.assertEqual(gaps, [])

    def test_untraced_statements_flags_unmapped_lines(self):
        variant, _ = self._tailored_variant()
        vid = variant["versions"][0]["version_id"]
        gaps = versions.untraced_statements(
            variant["variant_id"], vid,
            resume_md="- Invented line with no provenance at all.",
            variants_dir=self.dir)
        self.assertEqual(len(gaps), 1)

    def test_trace_unknown_statement_empty(self):
        variant, _ = self._tailored_variant()
        vid = variant["versions"][0]["version_id"]
        self.assertEqual(
            versions.trace_statement(
                variant["variant_id"], vid, "zzz no such statement",
                variants_dir=self.dir), [])

    def test_trace_is_exact_not_fuzzy(self):
        # A substring of a recorded statement must NOT trace: lenient
        # matching could claim a trace that isn't real.
        variant, _ = self._tailored_variant()
        vid = variant["versions"][0]["version_id"]
        self.assertEqual(
            versions.trace_statement(
                variant["variant_id"], vid, "Python",
                variants_dir=self.dir), [])

    def test_skill_matching_is_word_bounded(self):
        # Skill "Go" must not attach to a line containing "Good".
        profile = {
            "full_name": "Synthetic Fixture",
            "summary": "Good communicator with five years of experience.",
            "skills": ["Go"],
            "experience": [],
        }
        job = {"id": "j", "title": "Engineer",
               "description": "We need go developers."}
        result = tailor.tailor_with_provenance(profile, job)
        self.assertIn("Go", result["matched_skills"])
        summary_lines = [
            e for e in result["provenance"]["statement_map"]
            if "good communicator" in e["statement"].lower()
        ]
        self.assertTrue(summary_lines)
        self.assertNotIn("profile:skills",
                         summary_lines[0]["evidence_ids"])

    def test_base_is_fully_traceable(self):
        base = versions.create_base(_profile(), variants_dir=self.dir)
        vid = base["versions"][0]["version_id"]
        gaps = versions.untraced_statements(
            base["variant_id"], vid, variants_dir=self.dir)
        self.assertEqual(gaps, [])

    def test_approve_unknown_version_raises(self):
        v = versions.create_variant("b", variants_dir=self.dir,
                                    initial_resume_md="x")
        with self.assertRaises(KeyError):
            versions.approve_version(v["variant_id"], "ver_nope",
                                     variants_dir=self.dir)

    def test_reads_do_not_create_store_dir(self):
        fresh = Path(self.tmp.name) / "never-created"
        self.assertIsNone(
            versions.get_variant("var_nope", variants_dir=fresh))
        self.assertEqual(
            versions.list_variants(variants_dir=fresh), [])
        self.assertFalse(fresh.exists())

    def test_trace_report_classifies_evidence(self):
        variant, _ = self._tailored_variant()
        vid = variant["versions"][0]["version_id"]
        items = [
            {"evidence_id": "ev_synth_py", "kind": "achievement",
             "text": "synthetic", "source": "experience[0].bullets[0]",
             "approved": True},
            {"evidence_id": "ev_draft", "kind": "metric",
             "text": "synthetic", "source": "experience[0].bullets[1]",
             "approved": False},
        ]
        report = versions.trace_report(
            variant["variant_id"], vid, items, variants_dir=self.dir)
        statuses = {}
        for st in report["statements"]:
            statuses.update(st["evidence_status"])
        # ev_synth_py is referenced by the link and approved.
        self.assertEqual(statuses.get("ev_synth_py"), "approved")
        # profile: pseudo-refs classify as profile, never unknown.
        self.assertTrue(
            any(v == "profile" for v in statuses.values()))
        self.assertNotIn("ev_draft", report["unapproved"])
        # Inject an unapproved + unknown reference via a manual version.
        v2 = versions.create_variant("b2", variants_dir=self.dir,
                                     initial_resume_md="x",
                                     provenance={"statement_map": [
                                         {"statement": "x",
                                          "evidence_ids": ["ev_draft",
                                                           "ev_ghost"],
                                          "link_ids": []}]})
        rep2 = versions.trace_report(
            v2["variant_id"], v2["versions"][0]["version_id"], items,
            variants_dir=self.dir)
        self.assertIn("ev_draft", rep2["unapproved"])
        self.assertIn("ev_ghost", rep2["unknown"])


if __name__ == "__main__":
    unittest.main()

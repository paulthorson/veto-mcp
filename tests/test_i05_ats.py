"""Tests for Initiative 05 ATS readiness check (Epic 3).

All fixtures are synthetic and labeled as such.

The QA contract is a release blocker: these tests fail if ANY
user-facing copy implies or predicts vendor ranking — both in emitted
messages and in module prose outside the contract-definition block.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from initiatives.i05 import ats_check


def _profile() -> dict:
    return {
        "full_name": "Synthetic Fixture",
        "email": "fixture@example.com",
        "phone": "555-010-2030",
        "location": "New York, NY",
        "linkedin_url": "https://example.com/in/fixture",
        "website": "https://example.com",
        "summary": "Synthetic fixture profile for tests.",
        "skills": ["Python", "PostgreSQL"],
        "experience": [
            {
                "title": "Backend Engineer",
                "company": "FixtureCorp",
                "dates": "2020 - 2024",
                "bullets": [
                    "Shipped Python services handling 1M requests a day.",
                ],
            }
        ],
        "education": [{"degree": "B.S.", "school": "Fixture University",
                       "dates": "2016 - 2020"}],
    }


def _resume_md() -> str:
    return (
        "# Synthetic Fixture\n"
        "fixture@example.com | 555-010-2030 | New York, NY\n"
        "https://example.com/in/fixture\n"
        "\n"
        "## Summary\n"
        "Synthetic fixture profile for tests.\n"
        "\n"
        "## Experience\n"
        "### Backend Engineer — FixtureCorp\n"
        "*2020 - 2024*\n"
        "- Shipped Python services handling 1M requests a day.\n"
        "\n"
        "## Skills\n"
        "Python, PostgreSQL\n"
    )


def _job() -> dict:
    return {
        "id": "job-synth-1",
        "title": "Backend Engineer",
        "description": "We need Python and PostgreSQL experience.",
    }


class CopyContractTest(unittest.TestCase):
    def test_no_banned_phrase_in_any_emitted_message(self):
        # Battery of inputs: good resume, empty resume, partial resume.
        resumes = [
            _resume_md(),
            "",
            "# Name Only\n",
            _resume_md().replace("## Skills\nPython, PostgreSQL\n", ""),
        ]
        for md in resumes:
            report = ats_check.ats_readiness_check(md, _job(), _profile())
            for finding in report["findings"]:
                violations = ats_check.check_copy(finding["message"])
                self.assertEqual(
                    violations, [],
                    f"banned phrase in {finding['message']!r}")
            text = ats_check.render_report_text(report)
            self.assertEqual(ats_check.check_copy(text), [])

    def test_module_prose_outside_contract_block_is_clean(self):
        src = Path(ats_check.__file__).read_text(encoding="utf-8")
        begin = src.index("# COPY_CONTRACT_BEGIN")
        end = src.index("# COPY_CONTRACT_END")
        outside = src[:begin] + src[end:]
        violations = ats_check.check_copy(outside)
        self.assertEqual(
            violations, [],
            f"module prose violates its own QA contract: {violations}")

    def test_check_copy_detects_violations(self):
        self.assertTrue(
            ats_check.check_copy("This will rank you #1 in Workday"))
        self.assertTrue(
            ats_check.check_copy("beat the ATS with these keywords"))
        self.assertEqual(ats_check.check_copy("parseable and complete"), [])


class StructureCheckTest(unittest.TestCase):
    def test_good_resume_passes_structure(self):
        findings = ats_check.check_structure(_resume_md())
        by_area = {}
        for f in findings:
            by_area.setdefault(f["area"], []).append(f["severity"])
        self.assertNotIn("fail", by_area["structure"])

    def test_empty_resume_fails_loudly(self):
        report = ats_check.ats_readiness_check("", _job(), _profile())
        self.assertFalse(report["ready"])
        self.assertGreater(report["summary"]["fail"], 0)

    def test_table_warns(self):
        md = _resume_md() + "\n| a | b |\n|---|---|\n| 1 | 2 |\n"
        findings = ats_check.check_structure(md)
        tables = [f for f in findings if "Tables" in f["message"]]
        self.assertTrue(tables)
        self.assertEqual(tables[0]["severity"], "warn")

    def test_pipe_contact_line_is_not_a_table(self):
        # tailor.py joins contact bits with " | " — that is not a table.
        findings = ats_check.check_structure(_resume_md())
        self.assertFalse(
            [f for f in findings if "Tables were detected" in f["message"]])


class KeywordCoverageTest(unittest.TestCase):
    def test_full_coverage_passes(self):
        findings = ats_check.check_keyword_coverage(
            _resume_md(), _job(), _profile())
        self.assertEqual(findings[0]["severity"], "pass")

    def test_partial_coverage_warns_with_missing_list(self):
        md = _resume_md().replace("PostgreSQL", "a database")
        findings = ats_check.check_keyword_coverage(md, _job(), _profile())
        self.assertEqual(findings[0]["severity"], "warn")
        self.assertIn("PostgreSQL", findings[0]["message"])

    def test_no_keywords_is_not_a_failure(self):
        findings = ats_check.check_keyword_coverage(
            _resume_md(), {"title": "x"}, _profile())
        self.assertEqual(findings[0]["severity"], "pass")


class FieldCompletenessTest(unittest.TestCase):
    def test_complete_profile_passes(self):
        findings = ats_check.check_field_completeness(_profile())
        self.assertEqual(findings[0]["severity"], "pass")

    def test_missing_fields_listed(self):
        profile = dict(_profile())
        del profile["phone"]
        del profile["website"]
        findings = ats_check.check_field_completeness(profile)
        self.assertEqual(findings[0]["severity"], "warn")
        self.assertIn("phone", findings[0]["message"])
        self.assertIn("website", findings[0]["message"])


class ExportCheckTest(unittest.TestCase):
    def test_exports_render(self):
        findings = ats_check.check_exports(_profile())
        self.assertEqual(findings[0]["severity"], "pass")
        self.assertTrue(
            any("PDF backend" in f["message"] for f in findings))

    def test_report_ready_flag(self):
        report = ats_check.ats_readiness_check(
            _resume_md(), _job(), _profile())
        self.assertTrue(report["ready"])
        text = ats_check.render_report_text(report)
        self.assertIn("ATS readiness check", text)
        # Summary counts add up.
        s = report["summary"]
        self.assertEqual(
            s["pass"] + s["warn"] + s["fail"], len(report["findings"]))


if __name__ == "__main__":
    unittest.main()

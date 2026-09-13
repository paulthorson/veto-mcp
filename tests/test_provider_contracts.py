#!/usr/bin/env python3
"""Conformance tests for the Initiative 09 provider contract kit.

Covers: normalized schema validation, terms classification, budgets,
manifest completeness, and the per-provider conformance suite
(the Q2 gate's "capability contract" half).
"""

import unittest

from providers import _contract
from providers import ashby, greenhouse, lever
from providers._contract import (
    ConnectorManifest,
    JobDetail,
    JobPosting,
    TermsClass,
    budget_for,
    conformance_suite,
    manifest_for,
    suite_passed,
    terms_for,
    validate_job_detail,
    validate_job_posting,
)


def _good_posting(**over):
    base = {
        "id": "greenhouse:dG9rZW46MTIz",
        "title": "Backend Engineer",
        "company": "Acme",
        "location": "New York, NY",
        "url": "https://example.com/jobs/123",
        "board": "greenhouse",
        "snippet": "Backend Engineer — Acme",
    }
    base.update(over)
    return base


def _good_detail(**over):
    base = {
        "url": "https://example.com/jobs/123",
        "board": "greenhouse",
        "title": "Backend Engineer",
        "company": "Acme",
        "location": "New York, NY",
        "description": "Build things.",
        "apply_url": "https://example.com/apply/123",
    }
    base.update(over)
    return base


class SchemaValidationTests(unittest.TestCase):
    def test_posting_conforms(self):
        self.assertEqual(validate_job_posting(_good_posting()), [])

    def test_posting_missing_fields(self):
        problems = validate_job_posting({"id": "x", "title": "t"})
        self.assertTrue(any("company" in p for p in problems))

    def test_posting_id_must_be_self_describing(self):
        problems = validate_job_posting(_good_posting(id="not-a-job-id"))
        self.assertTrue(any("self-describing" in p for p in problems))

    def test_posting_id_prefix_must_match_board(self):
        problems = validate_job_posting(
            _good_posting(id="lever:abc123", board="greenhouse")
        )
        self.assertTrue(any("prefix" in p for p in problems))

    def test_detail_conforms(self):
        self.assertEqual(validate_job_detail(_good_detail()), [])

    def test_detail_error_shape_conforms(self):
        err = {"board": "lever", "payload": "x", "error": "not found"}
        self.assertEqual(validate_job_detail(err), [])

    def test_detail_error_without_board_fails(self):
        self.assertTrue(validate_job_detail({"error": "boom"}))

    def test_job_posting_dataclass_roundtrip(self):
        posting = JobPosting(**{k: v for k, v in _good_posting().items()
                                 if k in JobPosting.__dataclass_fields__})
        self.assertEqual(validate_job_posting(posting.to_dict()), [])

    def test_job_detail_dataclass_roundtrip(self):
        detail = JobDetail(**{k: v for k, v in _good_detail().items()
                              if k in JobDetail.__dataclass_fields__})
        self.assertEqual(validate_job_detail(detail.to_dict()), [])


class TermsClassificationTests(unittest.TestCase):
    def test_official_boards_classified(self):
        for name in ("greenhouse", "lever", "ashby"):
            terms, basis, robots_url = terms_for(name)
            self.assertEqual(terms, TermsClass.OFFICIAL_API, name)
            self.assertTrue(basis, name)
            self.assertTrue(robots_url.startswith("https://"), name)

    def test_scraping_boards_classified(self):
        terms, _, _ = terms_for("ziprecruiter")
        self.assertEqual(terms, TermsClass.HTML_SCRAPING)

    def test_unknown_provider_defaults_to_honest_stub(self):
        terms, basis, _ = terms_for("definitely-not-a-board")
        self.assertEqual(terms, TermsClass.HONEST_STUB)
        self.assertIn("No classification registered", basis)

    def test_unknown_provider_gets_zero_budget(self):
        self.assertEqual(budget_for("definitely-not-a-board"), (0, 3600))

    def test_registered_budgets_are_sane(self):
        for name in ("greenhouse", "lever", "ashby", "ziprecruiter"):
            daily, cooldown = budget_for(name)
            self.assertGreater(daily, 0, name)
            self.assertGreater(cooldown, 0, name)


class ManifestTests(unittest.TestCase):
    def test_every_registered_manifest_is_complete(self):
        for manifest in _contract.all_manifests():
            self.assertEqual(
                manifest.validate(), [],
                f"manifest {manifest.name!r} incomplete",
            )

    def test_manifest_for_unknown_is_none(self):
        self.assertIsNone(manifest_for("definitely-not-a-board"))

    def test_ats_direct_manifest_declares_no_direct_submit(self):
        manifest = manifest_for("ats_direct")
        self.assertIsNotNone(manifest)
        blocked = " ".join(manifest.why_it_may_be_blocked).lower()
        self.assertIn("401", blocked)
        self.assertIn("api key", blocked)
        sent = " ".join(manifest.what_data_it_sends).lower()
        self.assertIn("nothing today", sent)

    def test_incomplete_manifest_fails_validation(self):
        bad = ConnectorManifest(
            name="x", connector_type="job_provider",
            what_it_can_do=["a"], why_it_may_be_blocked=[],
            what_data_it_sends=["b"], what_requires_confirmation=["c"],
        )
        problems = bad.validate()
        self.assertTrue(any("why_it_may_be_blocked" in p for p in problems))


class ConformanceSuiteTests(unittest.TestCase):
    def _run(self, provider):
        results = conformance_suite(
            provider,
            search_fixture=[_good_posting(id=f"{provider.name}:abc",
                                          board=provider.name)],
            detail_fixture=_good_detail(board=provider.name),
        )
        return results

    def test_greenhouse_passes_conformance(self):
        results = self._run(greenhouse.GreenhouseProvider(tokens=[]))
        self.assertTrue(suite_passed(results),
                        [r for r in results if not r["passed"]])

    def test_lever_passes_conformance(self):
        results = self._run(lever.LeverProvider(tokens=[]))
        self.assertTrue(suite_passed(results),
                        [r for r in results if not r["passed"]])

    def test_ashby_passes_conformance(self):
        results = self._run(ashby.AshbyProvider(tokens=[]))
        self.assertTrue(suite_passed(results),
                        [r for r in results if not r["passed"]])

    def test_suite_flags_bad_fixture(self):
        results = conformance_suite(
            greenhouse.GreenhouseProvider(tokens=[]),
            search_fixture=[{"id": "x"}],
        )
        self.assertFalse(suite_passed(results))
        failed = [r["check"] for r in results if not r["passed"]]
        self.assertIn("schema.search_rows", failed)

    def test_suite_flags_unregistered_provider(self):
        class Mystery:
            name = "mystery-board"
        results = conformance_suite(Mystery())
        failed = [r["check"] for r in results if not r["passed"]]
        self.assertIn("manifest.registered", failed)


if __name__ == "__main__":
    unittest.main()

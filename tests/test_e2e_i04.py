"""End-to-end retro-validation for Initiative 04 (Fit decoder & career graph).

These tests exercise the shipped 04 features against REAL surfaces, not
unit mocks:

1. The real ``file_ingest`` CLI entry point
   (``python -m initiatives.i04.file_ingest <file> --yes``) via subprocess,
   with a genuine resume file on disk.
2. The full fit-scoring pipeline exactly as the product drives it:
   ingest -> decode_resume -> build_evidence_map -> fit_explain ->
   schema validation. i04 ships no dedicated cli.py subcommands of its own
   (its surfaces are the library modules + the file_ingest CLI), so the
   real-product code path IS this module chain.
3. role_compare across multiple job postings (the comparison surface).
4. build_career_graph over real outcome-event JSON (the career-graph
   read model).
5. Share-card encode/decode with the privacy scrub verified:
   no raw resume or job-description text may leak into the payload.

All fixtures are synthetic and labeled as such. Every temp file lives in
a TemporaryDirectory. No network is used anywhere (all stdlib text
processing); a socket block enforces that.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from initiatives.i04 import (
    career_graph,
    evidence_map,
    fit_explain,
    resume_decoder,
    role_compare,
    schemas,
    share_card,
)

REPO = Path(__file__).resolve().parent.parent

# Synthetic fixture data: deliberately fictional person, companies, and
# job postings, used only to exercise the pipeline.
RESUME_TEXT = """\
SYNTHETIC FIXTURE RESUME
Alex Example
alex.example@example.com | 555-010-2030 | New York, NY

EXPERIENCE
Senior Backend Engineer, FixtureCorp, New York, NY — 2021 - 2024
- Shipped Python microservices handling 1M requests per day.
- Cut PostgreSQL query times by 50 percent with new indexes.
- Led a team of 4 engineers on Kubernetes migration.

Backend Engineer, FixtureLabs, New York, NY — 2018 - 2021
- Built Django APIs serving synthetic fixture data.
- Wrote PostgreSQL migrations with careful rollout playbooks.

SKILLS
Python, PostgreSQL, Django, Kubernetes, Redis

EDUCATION
B.S. Computer Science, Fixture State University, 2018
"""

JD_TEXT_1 = """\
Senior Backend Engineer — HiringCorp (New York, NY)
We are hiring a Senior Backend Engineer. You must have 5+ years of
Python experience and deep PostgreSQL knowledge. Experience with
Kubernetes is a must-have. You will lead a small team of engineers.
Nice to have: Redis, Django.
"""

JD_TEXT_2 = """\
Junior Frontend Developer — PixelShop (Remote)
We need a junior frontend developer with 1 year of experience. Must
have React and TypeScript. No leadership expected.
"""


def _block_network():
    """Fail closed: any socket creation raises. i04 is pure stdlib text
    processing — if any network call happens, something is wrong."""
    def _deny(*args, **kwargs):
        raise AssertionError("network call attempted during i04 e2e flow")
    return socket.socket, _deny


class I04IngestCliE2E(unittest.TestCase):
    """Real CLI: ``python -m initiatives.i04.file_ingest``."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.orig_socket, deny = _block_network()
        socket.socket = deny

    def tearDown(self):
        socket.socket = self.orig_socket
        self.tmp.cleanup()

    def test_ingest_cli_extracts_txt_resume(self):
        resume_file = self.dir / "resume.txt"
        resume_file.write_text(RESUME_TEXT, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, "-m", "initiatives.i04.file_ingest",
             str(resume_file), "--yes"],
            cwd=REPO, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(proc.returncode, 0,
                         f"ingest CLI failed: {proc.stderr}")
        out = proc.stdout
        # The CLI prints the extracted text verbatim after the gate.
        self.assertIn("EXPERIENCE", out)
        self.assertIn("FixtureCorp", out)
        self.assertIn("Kubernetes", out)

    def test_ingest_cli_refuses_missing_file(self):
        proc = subprocess.run(
            [sys.executable, "-m", "initiatives.i04.file_ingest",
             str(self.dir / "nope.txt"), "--yes"],
            cwd=REPO, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("Error", proc.stdout)


class I04FitPipelineE2E(unittest.TestCase):
    """The full real-product fit pipeline, module by module."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.orig_socket, deny = _block_network()
        socket.socket = deny
        # Drive the REAL file-ingest module (not just the text constant):
        resume_file = self.dir / "resume.txt"
        resume_file.write_text(RESUME_TEXT, encoding="utf-8")
        extraction = None
        from initiatives.i04 import file_ingest
        extraction = file_ingest.extract_file(resume_file)
        self.resume_text = extraction["text"]

    def tearDown(self):
        socket.socket = self.orig_socket
        self.tmp.cleanup()

    def test_decode_resume_real_text(self):
        decoded = resume_decoder.decode_resume(self.resume_text)
        skills = {s["skill"] for s in decoded.get("skills_found", [])}
        self.assertIn("Python", skills)
        self.assertIn("PostgreSQL", skills)
        self.assertIn("Kubernetes", skills)
        # Seniority signal from "Led a team of 4 engineers".
        self.assertEqual(decoded["seniority"]["label"], "senior")
        # Honesty invariant: every matched skill carries its verbatim quote.
        for s in decoded["skills_found"]:
            self.assertTrue(s.get("quote"),
                            f"skill without quote: {s}")

    def test_fit_pipeline_scores_and_validates(self):
        job_id = "job-e2e-1"
        ev = evidence_map.build_evidence_map(
            JD_TEXT_1, self.resume_text, job_id, "Senior Backend Engineer")
        self.assertEqual(ev["validation_errors"], [],
                         f"evidence map invalid: {ev['validation_errors']}")
        self.assertGreater(len(ev["evidence_map"]["entries"]), 0)
        problems = schemas.validate_evidence_map(ev["evidence_map"])
        self.assertEqual(problems, [], f"schema problems: {problems}")

        result = fit_explain.fit_explain(
            self.resume_text, JD_TEXT_1, job_id, "Senior Backend Engineer")
        self.assertEqual(result["validation_errors"], [],
                         f"fit result invalid: {result['validation_errors']}")
        fr = result["fit_result"]
        problems = schemas.validate_fit_result(fr)
        self.assertEqual(problems, [], f"schema problems: {problems}")
        self.assertGreaterEqual(fr["fit_score"], 0)
        self.assertLessEqual(fr["fit_score"], 100)
        # Real breakdown: components must be a non-empty mapping of the
        # score's parts — the "fit decoder" promise.
        self.assertIsInstance(fr["components"], dict)
        self.assertGreater(len(fr["components"]), 0)
        # The strong-fit posting must beat the bar and carry evidence.
        self.assertGreaterEqual(fr["fit_score"], 60)
        self.assertGreater(fr["evidence_summary"]["supported"], 0)
        # Honesty invariant: every supported requirement carries a
        # verbatim quote — nothing is inferred beyond the text.
        for entry in fr["evidence_map"]["entries"]:
            if entry["status"] == "supported":
                quotes = [i.get("quote") for i in
                          (entry.get("evidence") or [])]
                self.assertTrue(
                    any(q and q.strip() for q in quotes),
                    f"supported entry has no quote: {entry}",
                )

    def test_fit_pipeline_low_fit_for_unrelated_job(self):
        result = fit_explain.fit_explain(
            self.resume_text, JD_TEXT_2, "job-e2e-2",
            "Junior Frontend Developer")
        fr = result["fit_result"]
        self.assertEqual(result["validation_errors"], [])
        # A backend resume against a frontend posting must score poorly.
        self.assertLess(fr["fit_score"], 60)
        self.assertGreater(fr["evidence_summary"]["gaps"], 0)


class I04RoleCompareE2E(unittest.TestCase):
    """role_compare: the multi-job comparison surface, end to end."""

    def setUp(self):
        self.orig_socket, deny = _block_network()
        socket.socket = deny

    def tearDown(self):
        socket.socket = self.orig_socket

    def test_compare_two_jobs_end_to_end(self):
        doc = role_compare.compare_roles(
            [
                {"job_id": "job-e2e-1", "job_title": "Senior Backend Engineer",
                 "jd_text": JD_TEXT_1},
                {"job_id": "job-e2e-2", "job_title": "Junior Frontend Dev",
                 "jd_text": JD_TEXT_2},
            ],
            resume_text=RESUME_TEXT,
        )
        rows = doc.get("jobs") or []
        self.assertEqual(len(rows), 2)
        by_id = {r.get("job_id"): r for r in rows}
        self.assertIn("job-e2e-1", by_id)
        self.assertIn("job-e2e-2", by_id)
        # The backend role must rank above the unrelated frontend role.
        best = max(rows, key=lambda r: r.get("fit_score", 0))
        self.assertEqual(best["job_id"], "job-e2e-1")
        self.assertGreater(by_id["job-e2e-1"]["fit_score"],
                           by_id["job-e2e-2"]["fit_score"])
        # Each job carries its own real fit breakdown.
        self.assertGreater(len(best["components"]), 0)


class I04CareerGraphE2E(unittest.TestCase):
    """Career graph read model over real outcome-event JSON."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.orig_socket, deny = _block_network()
        socket.socket = deny

    def tearDown(self):
        socket.socket = self.orig_socket
        self.tmp.cleanup()

    @staticmethod
    def _event(app_id, event_type, occurred_at, role="Backend Engineer",
               schema_version="outcome-min-v0"):
        return {
            "event_id": f"ev-{app_id}-{event_type}",
            "application_id": app_id,
            "event_type": event_type,
            "occurred_at": occurred_at,
            "source": "manual",
            "role": role,
            "provenance": {"actor": "user"},
            "schema_version": schema_version,
        }

    def test_career_graph_from_events_file(self):
        events = [
            self._event("a1", "applied", "2026-09-01T10:00:00+00:00"),
            self._event("a1", "interviewed", "2026-09-08T10:00:00+00:00"),
            self._event("a2", "applied", "2026-09-03T10:00:00+00:00"),
            self._event("a2", "rejected", "2026-09-10T10:00:00+00:00"),
        ]
        events_file = self.dir / "outcomes.json"
        events_file.write_text(json.dumps(events), encoding="utf-8")
        loaded = json.loads(events_file.read_text(encoding="utf-8"))
        graph = career_graph.build_career_graph(loaded)
        self.assertTrue(graph["rendered"],
                        f"refused to render: {graph.get('reason')}")
        tl = graph["timeline"]
        self.assertIn("a1", tl)
        self.assertIn("a2", tl)
        # Timeline is time-ordered per application.
        self.assertEqual(
            [e["event_type"] for e in tl["a1"]["events"]],
            ["applied", "interviewed"],
        )
        self.assertTrue(tl["a1"]["progressed"])
        self.assertEqual(tl["a2"]["current_state"], "rejected")
        # The read-model counts what happened: 2 applications.
        self.assertEqual(graph.get("applications"), 2)
        # Conversion bands are honest about low data rather than guessing.
        bands = graph.get("conversion_by_fit_band") or {}
        for band in bands.values():
            self.assertEqual(band["label"], "insufficient_data")


class I04ShareCardE2E(unittest.TestCase):
    """Share card: scores + chosen evidence only — no raw text may leak."""

    def setUp(self):
        self.orig_socket, deny = _block_network()
        socket.socket = deny

    def tearDown(self):
        socket.socket = self.orig_socket

    def test_share_card_encodes_without_raw_text(self):
        result = fit_explain.fit_explain(
            RESUME_TEXT, JD_TEXT_1, "job-e2e-1", "Senior Backend Engineer")
        self.assertEqual(result["validation_errors"], [])
        fr = result["fit_result"]
        supported = [
            item
            for entry in fr["evidence_map"]["entries"]
            if entry["status"] == "supported"
            for item in (entry.get("evidence") or [])
        ]
        self.assertGreater(len(supported), 0)
        selected = supported[:2]
        payload = share_card.build_share_card(
            fr, [s["evidence_id"] for s in selected], RESUME_TEXT, JD_TEXT_1)
        # The validator needs the raw inputs to scrub against, plus the
        # explicitly selected fragments as the allow-list — that IS the
        # privacy certification (no verbatim 24+ char runs outside the
        # fragments the user opted in to share).
        allowed = [s["quote"] for s in selected]
        problems = schemas.validate_share_card(
            payload, raw_resume_text=RESUME_TEXT, raw_job_text=JD_TEXT_1,
            allowed_quotes=allowed)
        self.assertEqual(problems, [], f"share card invalid: {problems}")
        # And the same gate fails when the fragments are NOT declared as
        # user-selected — the validator catches verbatim resume text.
        leakage = schemas.validate_share_card(
            payload, raw_resume_text=RESUME_TEXT, raw_job_text=JD_TEXT_1)
        self.assertTrue(leakage, "privacy gate missed verbatim resume text")
        fragment = share_card.encode_share_payload(payload)
        roundtrip = share_card.decode_share_payload(fragment)
        self.assertEqual(roundtrip["fit_score"], fr["fit_score"])
        # Privacy: raw resume and job text must not appear in the payload.
        payload_json = json.dumps(payload)
        self.assertNotIn("alex.example@example.com", payload_json)
        self.assertNotIn("555-010-2030", payload_json)
        self.assertNotIn(JD_TEXT_1.strip()[:60], payload_json)
        self.assertNotIn("alex.example@example.com", fragment)

    def test_share_card_fails_closed_on_invalid_fit_result(self):
        with self.assertRaises(share_card.ShareCardPrivacyError):
            share_card.build_share_card({}, ["x"], RESUME_TEXT, JD_TEXT_1)


if __name__ == "__main__":
    unittest.main()

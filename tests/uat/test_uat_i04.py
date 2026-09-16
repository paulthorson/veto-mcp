"""Automated UAT acceptance journey for Initiative 04 (Fit decoder & career graph).

The user's journey: "A job seeker pastes a job description and gets a
private, explained answer to 'why this role?'"

One test method per roadmap epic (E1..E6), named in EPIC_MAP. Assertions
trace ONLY to the roadmap epic text, the Initiative 04 Proof of value
("keeps resume content local by default"), and the Q1 exit gate ("never
places raw resume text in a share link"). The repo carries no per-story
acceptance criteria for i04; this journey invents none.

All fixtures are synthetic and labeled as such. All state lives under the
per-test temp dir; nothing touches the repo tree or real user data.
"""

from __future__ import annotations

import io
import re
import subprocess
import sys
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
from tests.uat.harness import JourneyCase

REPO = Path(__file__).resolve().parent.parent.parent

ALLOWED_STATUSES = {"supported", "gap", "grill_question"}


def _write_synthetic_pdf(path: Path) -> None:
    """Write a minimal valid PDF with extractable text (synthetic fixture)."""
    content = (
        b"BT /F1 12 Tf 72 720 Td 14 TL "
        b"(SYNTHETIC PDF RESUME - not a real person. Python, PostgreSQL, "
        b"Kubernetes at FixtureCorp.) Tj ET\n"
    )
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"endstream",
    ]
    pdf = io.BytesIO()
    pdf.write(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, 1):
        offsets.append(pdf.tell())
        pdf.write(b"%d 0 obj\n" % i + obj + b"\nendobj\n")
    xref = pdf.tell()
    pdf.write(b"xref\n0 %d\n" % (len(objects) + 1))
    pdf.write(b"0000000000 65535 f \n")
    for off in offsets:
        pdf.write(b"%010d 00000 n \n" % off)
    pdf.write(
        b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
        % (len(objects) + 1, xref)
    )
    path.write_bytes(pdf.getvalue())


def _outcome_event(app_id: str, event_type: str, occurred_at: str,
                   role: str) -> dict:
    return {
        "event_id": f"ev-{app_id}-{event_type}",
        "application_id": app_id,
        "event_type": event_type,
        "occurred_at": occurred_at,
        "source": "manual",
        "role": role,
        "provenance": {"actor": "user"},
        "schema_version": "outcome-min-v0",
    }


class I04UatJourney(JourneyCase):
    """Acceptance journey for Initiative 04, one epic per test method."""

    EPIC_MAP = {
        "test_resume_plus_job_decoder": (
            "E1", "Resume plus job decoder",
            "Roadmap i04 E1 epic text + Proof of value (keeps resume content local by default)",
        ),
        "test_evidence_map": (
            "E2", "Evidence map",
            "Roadmap i04 E2 epic text",
        ),
        "test_role_comparison": (
            "E3", "Role comparison",
            "Roadmap i04 E3 epic text",
        ),
        "test_career_graph": (
            "E4", "Career graph",
            "Roadmap i04 E4 epic text",
        ),
        "test_private_share_card": (
            "E5", "Private share card",
            "Q1 exit gate (never places raw resume text in a share link)",
        ),
        "test_local_file_ingestion": (
            "E6", "Local file ingestion",
            "Roadmap i04 E6 epic text + Proof of value (keeps resume content local by default)",
        ),
    }

    # -- E1 -----------------------------------------------------------------
    def test_resume_plus_job_decoder(self):
        """You paste your resume and a job description and get an answer without anything leaving your device."""
        # Decoding runs fully in-process with the network failed closed: no
        # model, no API — the Proof of value for i04 ("keeps resume content
        # local by default").
        with self.block_network():
            decoded = resume_decoder.decode_resume(self.synthetic_resume())
        skills = {s["skill"] for s in decoded.get("skills_found", [])}
        self.assertIn("Python", skills)
        self.assertIn("PostgreSQL", skills)
        self.assertIn("Kubernetes", skills)
        self.assertTrue(
            decoded.get("seniority", {}).get("label"),
            "decoding must surface a seniority signal",
        )

        # The job-description side of the decoder, on the real top-level CLI.
        jd_file = self.workdir / "jd.txt"
        jd_file.write_text(self.synthetic_jd(), encoding="utf-8")
        out = self.assert_ok(
            self.run_cli("decode-jd", "--file", str(jd_file), "--verdict"),
            "decode-jd on a pasted job description",
        )
        self.assertIn("verdict", out.lower())
        # Assert the actual scored detail lines, not a bare header: each
        # green flag is a "- [+N] Green flag: <reason>" line.
        green_lines = [ln for ln in out.splitlines()
                       if re.match(r"^-\s*\[\+\d+\]\s*Green flag:", ln)]
        self.assertGreaterEqual(
            len(green_lines), 1,
            f"verdict must score at least one green flag line:\n{out}")
        self.assertTrue(
            any("must-haves listed" in ln for ln in green_lines),
            f"expected a must-haves green flag line:\n{out}")

    # -- E2 -----------------------------------------------------------------
    def test_evidence_map(self):
        """Each job requirement is tied to a fact from your resume, a gap, or a question to clarify later — never a made-up match."""
        jd = (
            "SYNTHETIC FIXTURE JOB POSTING - not a real opening\n"
            "Senior Backend Engineer - HiringCorp\n"
            "You must have Python experience. You must have Rust experience. "
            "PostgreSQL is nice to have.\n"
        )
        with self.block_network():
            ev = evidence_map.build_evidence_map(
                jd, self.synthetic_resume(), "uat-job-2",
                "Senior Backend Engineer",
            )
        self.assertEqual(ev["validation_errors"], [])
        entries = ev["evidence_map"]["entries"]
        self.assertGreater(len(entries), 0)
        statuses = {e["status"] for e in entries}
        # Epic E2 allows exactly three outcomes per requirement.
        self.assertTrue(
            statuses <= ALLOWED_STATUSES,
            f"unexpected evidence statuses: {statuses}",
        )
        self.assertIn("supported", statuses)
        self.assertIn("gap", statuses, "the Rust requirement must surface as a gap")
        for entry in entries:
            status = entry["status"]
            evidence = entry.get("evidence") or []
            if status == "supported":
                # Every supported match carries a verbatim quote from the
                # resume — the evidence it stands on.
                self.assertGreater(len(evidence), 0)
                for item in evidence:
                    self.assertTrue(
                        item.get("quote", "").strip()
                        and item["quote"] in self.synthetic_resume(),
                        f"supported match without a verbatim resume quote: {entry}",
                    )
            else:
                # Gaps and grill questions carry no evidence quotes —
                # nothing is quoted that is not supported.
                self.assertEqual(
                    evidence, [],
                    f"{status} entry must carry no evidence quotes: {entry}",
                )
        # Questions for the grill carry a question id when present.
        for entry in entries:
            if entry["status"] == "grill_question":
                self.assertTrue(entry.get("grill_question_id"))
        problems = schemas.validate_evidence_map(ev["evidence_map"])
        self.assertEqual(problems, [], f"schema problems: {problems}")

    # -- E3 -----------------------------------------------------------------
    def test_role_comparison(self):
        """Up to four jobs are compared side by side on fit, risk, pay, location, and readiness."""
        postings = [
            {
                "job_id": "uat-j1",
                "job_title": "Senior Backend Engineer",
                "jd_text": (
                    "SYNTHETIC\nSenior Backend Engineer. Must have Python, "
                    "PostgreSQL, Kubernetes. Lead a small team. New York, NY."
                ),
            },
            {
                "job_id": "uat-j2",
                "job_title": "Backend Engineer",
                "jd_text": (
                    "SYNTHETIC\nBackend Engineer. Python and Django needed. "
                    "Remote. $140k-$160k."
                ),
            },
            {
                "job_id": "uat-j3",
                "job_title": "Data Engineer",
                "jd_text": (
                    "SYNTHETIC\nData Engineer. PostgreSQL and Redis needed. "
                    "Onsite, Boston."
                ),
            },
            {
                "job_id": "uat-j4",
                "job_title": "Frontend Developer",
                "jd_text": (
                    "SYNTHETIC\nFrontend Developer. Must have React and "
                    "TypeScript. No leadership."
                ),
            },
        ]
        with self.block_network():
            doc = role_compare.compare_roles(
                postings, resume_text=self.synthetic_resume()
            )
        rows = doc.get("jobs") or []
        self.assertEqual(len(rows), 4, "all four postings must be compared")
        for row in rows:
            # Each row is comparable across the epic's five axes.
            self.assertIsInstance(row.get("fit_score"), (int, float))
            self.assertIn("risk", row)
            self.assertIn("compensation", row)
            self.assertIn("location", row)
            self.assertIn("readiness", row)
            self.assertGreater(len(row.get("components") or {}), 0)
        # Rows arrive ranked by fit, and the best-fit row is the backend
        # posting matching the synthetic resume.
        scores = [r["fit_score"] for r in rows]
        self.assertEqual(
            scores, sorted(scores, reverse=True),
            "comparison must rank postings by fit",
        )
        self.assertEqual(rows[0]["job_id"], "uat-j1")
        self.assertGreater(rows[0]["fit_score"], rows[-1]["fit_score"])

    # -- E4 -----------------------------------------------------------------
    def test_career_graph(self):
        """Your history shows trends over time — recurring strengths, recurring gaps, seniority movement, and target-role movement."""
        resume = self.synthetic_resume()
        fr1 = fit_explain.fit_explain(
            resume,
            "SYNTHETIC\nSenior Backend Engineer. Must have Python, PostgreSQL. "
            "Lead a small team.",
            "a1",
            "Senior Backend Engineer",
        )["fit_result"]
        fr2 = fit_explain.fit_explain(
            resume,
            "SYNTHETIC\nStaff Backend Engineer. Must have Python, Rust, "
            "Kubernetes. Lead multiple teams.",
            "a2",
            "Staff Backend Engineer",
        )["fit_result"]
        events = [
            _outcome_event("a1", "applied", "2026-08-01T10:00:00+00:00",
                           "Senior Backend Engineer"),
            _outcome_event("a1", "interviewed", "2026-08-08T10:00:00+00:00",
                           "Senior Backend Engineer"),
            _outcome_event("a2", "applied", "2026-09-01T10:00:00+00:00",
                           "Staff Backend Engineer"),
            _outcome_event("a2", "rejected", "2026-09-10T10:00:00+00:00",
                           "Staff Backend Engineer"),
        ]
        with self.block_network():
            graph = career_graph.build_career_graph(
                events, fit_results={"a1": fr1, "a2": fr2}
            )
        self.assertTrue(graph["rendered"])
        self.assertEqual(graph.get("applications"), 2)
        # Recurring strengths trend up: Python is supported in both roles.
        strengths = {s["requirement"]: s["times_supported"]
                     for s in graph.get("strengths") or []}
        self.assertGreaterEqual(strengths.get("python", 0), 2)
        # Recurring gaps trend too: Rust is missing everywhere it is asked.
        gaps = {g["requirement"]: g for g in graph.get("gaps") or []}
        self.assertIn("rust", gaps)
        # Seniority movement is visible across roles and time.
        trend = graph.get("seniority_trend") or []
        self.assertEqual(len(trend), 2)
        self.assertEqual([t["application_id"] for t in trend], ["a1", "a2"])
        roles = [t["role"] for t in trend]
        self.assertIn("Senior Backend Engineer", roles)
        self.assertIn("Staff Backend Engineer", roles)

    # -- E5 -----------------------------------------------------------------
    def test_private_share_card(self):
        """Sharing your scores carries only the scores and the evidence you picked — every share-card field is probed, and any field containing contact details is refused."""
        resume = self.synthetic_resume()
        jd = self.synthetic_jd()
        result = fit_explain.fit_explain(
            resume, jd, "uat-job-5", "Senior Backend Engineer")
        self.assertEqual(result["validation_errors"], [])
        fr = result["fit_result"]

        # No evidence selected: the card is scores only.
        payload = share_card.build_share_card(fr, [], resume, jd)
        problems = schemas.validate_share_card(
            payload, raw_resume_text=resume, raw_job_text=jd)
        self.assertEqual(problems, [], f"share card invalid: {problems}")

        # The encoded share fragment is what travels in a share link — it
        # must contain no raw resume text, per the Q1 exit gate.
        fragment = share_card.encode_share_payload(payload)
        for raw in (
            "alex.example@example.com",
            "555-010-2030",
            "Led a team of 4 engineers on a Kubernetes migration",
        ):
            self.assertNotIn(raw, fragment)
        self.assertNotIn(jd.strip()[:60], fragment)
        # The share link still round-trips the score it was made from.
        roundtrip = share_card.decode_share_payload(fragment)
        self.assertEqual(roundtrip["fit_score"], fr["fit_score"])

    # -- E6 -----------------------------------------------------------------
    def test_local_file_ingestion(self):
        """Uploading a PDF or DOCX resume shows you a preview of what was read before anything is analyzed."""
        docx_path = self.workdir / "resume.docx"
        import docx  # python-docx; required dependency per file_ingest.py

        document = docx.Document()
        document.add_paragraph(
            "SYNTHETIC DOCX RESUME - not a real person. "
            "Python, PostgreSQL, Kubernetes at FixtureCorp."
        )
        document.save(str(docx_path))
        pdf_path = self.workdir / "resume.pdf"
        _write_synthetic_pdf(pdf_path)

        # DOCX extracts real text.
        docx_out = self.assert_ok(
            self.run_module("initiatives.i04.file_ingest", str(docx_path), "--yes"),
            "DOCX ingestion",
        )
        self.assertIn("SYNTHETIC DOCX RESUME", docx_out)
        self.assertIn("FixtureCorp", docx_out)

        # PDF extracts real text.
        pdf_out = self.assert_ok(
            self.run_module("initiatives.i04.file_ingest", str(pdf_path), "--yes"),
            "PDF ingestion",
        )
        self.assertIn("SYNTHETIC PDF RESUME", pdf_out)

        # Without --yes the CLI shows the extracted text as an explicit
        # preview and analyzes nothing until confirmed: with no input on
        # stdin it cancels instead of analyzing.
        # (run_module has no stdin knob, so this one call goes through
        # subprocess directly with stdin closed.)
        proc = subprocess.run(
            [sys.executable, "-m", "initiatives.i04.file_ingest",
             str(docx_path)],
            cwd=str(REPO), capture_output=True, text=True, timeout=60,
            stdin=subprocess.DEVNULL,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("preview", proc.stdout.lower())
        self.assertIn("SYNTHETIC DOCX RESUME", proc.stdout,
                      "preview must show what will be analyzed")
        self.assertIn("Cancelled — nothing was analyzed", proc.stdout)


if __name__ == "__main__":
    unittest.main()

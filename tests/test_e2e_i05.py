"""End-to-end retro-validation for Initiative 05 (Application Studio).

These tests exercise the shipped 05 features against REAL surfaces: the
actual ``studio.py`` CLI entry point (``python initiatives/i05/studio.py
<subcommand>``) via subprocess, with all stores pointed at hermetic temp
dirs. The full real-product flow is driven:

    evidence-build -> evidence-list -> evidence-approve
      -> variant-create -> variant-tailor -> variant-trace
      -> variant-approve -> packet-build -> packet-review
      -> packet-approve

plus the ``ats`` readiness check, the ``diff`` explanation, and
``variant-restore``.

Fill-only boundary (the legal mandate: Veto never the last actor before
a third party; every outbound action initiated by a human hand): the
studio flow must perform zero network calls, and the packet contract
must be approval-only — no submit path exists. This is asserted by (a) a
source scan proving no network I/O imports/calls exist anywhere in the
i05 flow's modules, (b) the approved packet JSON containing no submit
endpoints, and (c) the product's own approval contract text.

All fixtures are synthetic and labeled as such. Deterministic: fixed
fixtures, temp dirs, no ports, no network.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STUDIO = REPO / "initiatives" / "i05" / "studio.py"

# Synthetic fixture data: deliberately fictional person, companies, and
# job postings, used only to exercise the studio flow.
PROFILE = {
    "full_name": "Synthetic Fixture",
    "email": "fixture@example.com",
    "phone": "555-010-2030",
    "location": "New York, NY",
    "linkedin_url": "https://example.com/in/fixture",
    "website": "https://example.com",
    "summary": (
        "Synthetic fixture profile used only for tests. Backend "
        "engineer with seven years of experience building Python web "
        "services and PostgreSQL data pipelines for synthetic workloads. "
        "Enjoys testing, code review, and writing documentation that "
        "keeps on-call rotations quiet."
    ),
    "skills": ["Python", "PostgreSQL", "Django", "Redis"],
    "experience": [
        {
            "title": "Backend Engineer",
            "company": "FixtureCorp",
            "dates": "2020 - 2024",
            "bullets": [
                "Shipped Python services handling 1M requests a day.",
                "Cut PostgreSQL query times by half with indexes.",
                "Built synthetic load tests that caught regressions "
                "before release.",
                "Mentored two junior engineers on testing and code review.",
            ],
        },
        {
            "title": "Junior Backend Engineer",
            "company": "FixtureLabs",
            "dates": "2017 - 2020",
            "bullets": [
                "Maintained Django APIs serving synthetic fixture data.",
                "Wrote PostgreSQL migrations with careful rollout playbooks.",
                "Built dashboards that flagged slow endpoints within minutes.",
            ],
        },
    ],
}

JOB = {
    "id": "job-synth-1",
    "title": "Backend Engineer",
    "company": "HiringCorp",
    "description": (
        "We need Python and PostgreSQL experience. You will build web "
        "services and data pipelines. Django experience is a plus."
    ),
}

RESUME_MD = """\
# Synthetic Fixture
fixture@example.com | 555-010-2030

## Summary
Synthetic fixture profile used only for tests. Backend engineer with
seven years of experience.

## Experience
### Backend Engineer, FixtureCorp (2020 - 2024)
- Shipped Python services handling 1M requests a day.
- Cut PostgreSQL query times by half with indexes.
"""


class StudioE2E(unittest.TestCase):
    """Drive the real studio CLI end to end against temp stores."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.variants = self.dir / "variants"
        self.library = self.dir / "library"
        self.packets = self.dir / "packets"
        self.state = self.dir / "state"
        self.profile = self.dir / "profile.json"
        self.profile.write_text(json.dumps(PROFILE), encoding="utf-8")
        self.job = self.dir / "job.json"
        self.job.write_text(json.dumps(JOB), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    # -- harness -------------------------------------------------------
    # Only some subcommands accept the --*-dir store overrides
    # (variant-*, evidence-*, packet-*); ats/diff/feedback do not.
    STORE_SUBCOMMANDS = {
        "variant-create", "variant-tailor", "variant-approve",
        "variant-restore", "variant-trace", "evidence-build",
        "evidence-list", "evidence-approve", "packet-build",
        "packet-review", "packet-approve",
    }

    def studio(self, *args: str) -> subprocess.CompletedProcess:
        """Run the REAL studio CLI (subprocess, cwd=repo root)."""
        cmd = [sys.executable, str(STUDIO), *args]
        if args and args[0] in self.STORE_SUBCOMMANDS:
            cmd += [
                "--variants-dir", str(self.variants),
                "--library-dir", str(self.library),
                "--packets-dir", str(self.packets),
                "--state-dir", str(self.state),
            ]
        proc = subprocess.run(
            cmd, cwd=REPO, capture_output=True, text=True, timeout=120,
        )
        return proc

    @staticmethod
    def _variant_id(create_output: str) -> str:
        m = re.search(r"variant (\S+) created", create_output)
        assert m, f"no variant id in: {create_output}"
        return m.group(1)

    def studio_ok(self, *args: str) -> str:
        proc = self.studio(*args)
        self.assertEqual(
            proc.returncode, 0,
            f"studio {' '.join(args)} failed rc={proc.returncode}\n"
            f"stdout: {proc.stdout}\nstderr: {proc.stderr}")
        return proc.stdout

    # -- evidence library ----------------------------------------------
    def test_evidence_build_list_approve(self):
        out = self.studio_ok("evidence-build", "--profile", str(self.profile))
        m = re.search(r"derived (\d+) items", out)
        self.assertIsNotNone(m)
        self.assertGreater(int(m.group(1)), 0)

        out = self.studio_ok("evidence-list")
        # All items start unapproved (marked with the empty circle).
        self.assertIn("○", out)

        # Approve every derived item through the real CLI.
        from initiatives.i05 import evidence_library
        for item in evidence_library.list_items(library_dir=self.library):
            out = self.studio_ok("evidence-approve", item["evidence_id"])
            self.assertIn("approved", out.lower())

        out = self.studio_ok("evidence-list", "--approved-only")
        self.assertNotIn("○", out)
        self.assertIn("✓", out)

    # -- variant lifecycle ---------------------------------------------
    def test_variant_tailor_trace_approve_restore(self):
        self.studio_ok("evidence-build", "--profile", str(self.profile))
        out = self.studio_ok("variant-create", "backend-role",
                             "--job-id", "job-synth-1")
        vid = self._variant_id(out)

        out = self.studio_ok(
            "variant-tailor", vid,
            "--profile", str(self.profile), "--job", str(self.job),
            "--job-id", "job-synth-1")
        m = re.search(r"committed (\S+)", out)
        self.assertIsNotNone(m, f"no version committed: {out}")
        version = m.group(1)
        self.assertIn("Python", out)  # matched skills listed

        out = self.studio_ok("variant-trace", vid, version)
        self.assertIn("profile-backed statements:", out)

        out = self.studio_ok("variant-approve", vid, version)
        self.assertIn(f"approved {version}", out)

        # Restore writes a real markdown file with the tailored resume.
        restored = self.dir / "restored.md"
        out = self.studio_ok("variant-restore", vid, version,
                             "--out", str(restored))
        self.assertTrue(restored.is_file())
        content = restored.read_text(encoding="utf-8")
        self.assertIn("FixtureCorp", content)
        self.assertIn("Python", content)

    # -- clean user errors --------------------------------------------
    def test_variant_tailor_missing_profile_clean_error(self):
        missing = self.dir / "nope.json"
        proc = self.studio(
            "variant-tailor", "some-variant",
            "--profile", str(missing), "--job", str(self.job))
        self.assertEqual(proc.returncode, 2)
        self.assertIn("profile file not found", proc.stderr)
        self.assertIn(str(missing), proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)

    def test_variant_tailor_missing_job_clean_error(self):
        missing = self.dir / "nope-job.json"
        proc = self.studio(
            "variant-tailor", "some-variant",
            "--profile", str(self.profile), "--job", str(missing))
        self.assertEqual(proc.returncode, 2)
        self.assertIn("job file not found", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)

    def test_variant_tailor_corrupt_profile_clean_error(self):
        corrupt = self.dir / "corrupt.json"
        corrupt.write_text('{"not": json', encoding="utf-8")
        proc = self.studio(
            "variant-tailor", "some-variant",
            "--profile", str(corrupt), "--job", str(self.job))
        self.assertEqual(proc.returncode, 2)
        self.assertIn("cannot parse profile file", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)

    # -- ATS readiness --------------------------------------------------
    def test_ats_readiness_check(self):
        resume_file = self.dir / "resume.md"
        resume_file.write_text(RESUME_MD, encoding="utf-8")
        proc = self.studio("ats", "--resume", str(resume_file),
                           "--job", str(self.job), "--profile", str(self.profile))
        # rc 0 = ready, rc 2 = not ready; both are real report paths.
        self.assertIn(proc.returncode, (0, 2))
        self.assertIn("ATS", proc.stdout.upper())

    # -- diff explanation ------------------------------------------------
    def test_diff_explains_changes(self):
        base = self.dir / "base.md"
        tailored = self.dir / "tailored.md"
        base.write_text(RESUME_MD, encoding="utf-8")
        tailored.write_text(
            RESUME_MD.replace("seven years of experience",
                              "seven years of experience building "
                              "PostgreSQL data pipelines"),
            encoding="utf-8")
        out = self.studio_ok("diff", "--base", str(base),
                             "--tailored", str(tailored))
        self.assertIn("PostgreSQL", out)

    # -- full packet flow -------------------------------------------------
    def test_packet_build_review_approve(self):
        self.studio_ok("evidence-build", "--profile", str(self.profile))
        from initiatives.i05 import evidence_library
        for item in evidence_library.list_items(library_dir=self.library):
            evidence_library.approve_item(item["evidence_id"],
                                          library_dir=self.library)
        out = self.studio_ok("variant-create", "backend-role",
                             "--job-id", "job-synth-1")
        vid = self._variant_id(out)
        out = self.studio_ok(
            "variant-tailor", vid,
            "--profile", str(self.profile), "--job", str(self.job),
            "--job-id", "job-synth-1")
        version = re.search(r"committed (\S+)", out).group(1)

        out = self.studio_ok(
            "packet-build", "--job", str(self.job),
            "--profile", str(self.profile), "--job-id", "job-synth-1",
            "--variant", vid, "--version", version)
        m = re.search(r"packet (\S+) \((\S+)\)", out)
        self.assertIsNotNone(m, f"no packet id: {out}")
        packet_id = m.group(1)
        self.assertTrue(packet_id.startswith("pkt_"),
                        f"unexpected packet id: {packet_id}")
        # Packet text renders the fit rationale with real evidence
        # citations (evidence id + profile source for each strength).
        self.assertIn("Shipped Python services handling 1M requests a day.",
                      out)
        self.assertIn("source: experience[0].bullets[0]", out)

        # Approve the variant version first (the checklist requires it),
        # then review every proposed diff change through the real CLI.
        out = self.studio_ok("variant-approve", vid, version)
        self.assertIn(f"approved {version}", out)

        from initiatives.i05 import packet as packet_mod
        pkt = packet_mod.get_packet(packet_id, packets_dir=self.packets)
        self.assertIsNotNone(pkt)
        changes = [c["change_id"] for c in (pkt.get("changes") or [])
                   if not c.get("reviewed")]
        self.assertGreater(len(changes), 0)
        for change_id in changes:
            out = self.studio_ok("packet-review", packet_id, change_id)
            self.assertIn(f"reviewed {change_id}", out)

        out = self.studio_ok("packet-approve", packet_id,
                             "--profile", str(self.profile),
                             "--job", str(self.job))
        self.assertIn(f"approved {packet_id}", out)

        # The approved packet is a real JSON artifact on disk.
        files = list(self.packets.rglob("*.json"))
        self.assertTrue(files, "no packet JSON written")
        approved = None
        for f in files:
            doc = json.loads(f.read_text(encoding="utf-8"))
            if doc.get("packet_id") == packet_id:
                approved = doc
        self.assertIsNotNone(approved)
        self.assertEqual(approved["status"], "approved")
        self.assertTrue(approved.get("content_sha256"))
        # Approval-only contract: no submit machinery in the artifact.
        # (Blunt URL/substring checks are excluded: the resume legitimately
        # contains words like "endpoints" and the profile's LinkedIn URL.)
        artifact = json.dumps(approved).lower()
        for word in ("submit", "post_application", "apply_to_job",
                     "browser_apply", "ats_apply", "api_key", "bearer"):
            self.assertNotIn(word, artifact,
                             f"packet artifact mentions '{word}'")
        self.assertIn("FixtureCorp", approved["resume_md"])

    def test_packet_approve_blocked_until_reviewed(self):
        self.studio_ok("evidence-build", "--profile", str(self.profile))
        out = self.studio_ok("variant-create", "backend-role",
                             "--job-id", "job-synth-1")
        vid = self._variant_id(out)
        out = self.studio_ok(
            "variant-tailor", vid,
            "--profile", str(self.profile), "--job", str(self.job),
            "--job-id", "job-synth-1")
        version = re.search(r"committed (\S+)", out).group(1)
        out = self.studio_ok(
            "packet-build", "--job", str(self.job),
            "--profile", str(self.profile), "--job-id", "job-synth-1",
            "--variant", vid, "--version", version)
        packet_id = re.search(r"packet (\S+) \((\S+)\)", out).group(1)
        # Unreviewed packet must NOT approve (rc 2 + blocked message).
        proc = self.studio("packet-approve", packet_id,
                           "--profile", str(self.profile),
                           "--job", str(self.job))
        self.assertEqual(proc.returncode, 2)
        self.assertIn("blocked", proc.stdout.lower())


class StudioFillOnlyE2E(unittest.TestCase):
    """The legal boundary: the studio flow performs zero network I/O and
    the packet contract is approval-only. If a future change adds any
    network call to this flow, these tests fail."""

    def test_no_network_imports_in_studio_flow(self):
        flow_modules = [
            REPO / "initiatives" / "i05" / name
            for name in ("studio.py", "packet.py", "evidence_library.py",
                         "ats_check.py", "diff_explain.py", "versions.py",
                         "contracts.py", "success_feedback.py")
        ] + [REPO / "tailor.py", REPO / "cover_letters.py"]
        network_pattern = re.compile(
            r"^(import|from)\s+(urllib|requests|httpx|http|socket)\b|"
            r"urlopen\(|requests\.(get|post|put|delete)|"
            r"httpx\.(get|post|put|delete)|HTTPConnection|"
            r"socket\.socket\(")
        for path in flow_modules:
            for i, line in enumerate(
                    path.read_text(encoding="utf-8").splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                self.assertIsNone(
                    network_pattern.search(stripped),
                    f"{path.name}:{i} performs network I/O: {stripped}")

    def test_packet_contract_is_approval_only(self):
        src = (REPO / "initiatives" / "i05" / "packet.py").read_text(
            encoding="utf-8")
        self.assertIn("approval never submits anything", src)
        # No submit-path symbol anywhere in the packet module.
        self.assertNotRegex(
            src, r"\bsubmit\b.*\(|\.post\(|urlopen",
            "submit-path code found in packet.py")


if __name__ == "__main__":
    unittest.main()

"""Automated UAT acceptance journey for Initiative 05 (Application Studio).

Acceptance journey (plain English): a job seeker tailors a resume for a
role with an evidence library gated so that unapproved evidence never
reaches the tailor; the tailored result is bundled into an application
packet whose approval is checklist-gated.

Each test method maps to exactly one roadmap epic in EPIC_MAP below and
traces its assertions to the roadmap epic text, the Initiative 05
"Proof of value", or the Q1 exit gate. The repo has epics but no
per-story acceptance criteria; these journeys do not invent story-level
criteria.

What these tests assert vs. the E2E suite (tests/test_e2e_i05.py): the
E2E suite drives the same CLI for engineering coverage. This journey
asserts the acceptance contract the operator signs off on: exact version
restore, evidence-approval gating before tailoring, the ATS copy
contract, explained diffs, the checklist-gated packet, and the
earned-success gate.

All fixtures are synthetic and labeled as such. All state lives under
the per-test temp dir via the studio store overrides; nothing touches
the repo tree or real user data.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from tests.uat.harness import JourneyCase

STUDIO = Path(__file__).resolve().parent.parent.parent / "initiatives" / "i05" / "studio.py"

# Only some subcommands accept the --*-dir store overrides
# (variant-*, evidence-*, packet-*, feedback*); ats/diff do not.
STORE_SUBCOMMANDS = {
    "variant-create", "variant-tailor", "variant-approve",
    "variant-restore", "variant-trace", "evidence-build",
    "evidence-list", "evidence-approve", "packet-build",
    "packet-review", "packet-approve", "feedback", "feedback-dismiss",
}

PROFILE = {
    "full_name": "SYNTHETIC UAT Persona",
    "email": "uat@example.com",
    "phone": "555-019-9000",
    "location": "New York, NY",
    "linkedin_url": "https://example.com/in/uat",
    "website": "https://example.com/uat",
    "summary": (
        "SYNTHETIC fixture profile used only for automated UAT. "
        "Backend engineer with six years of experience building Python "
        "services and PostgreSQL pipelines for synthetic workloads."
    ),
    "skills": ["Python", "PostgreSQL", "Django", "Redis", "Kubernetes"],
    "experience": [
        {
            "title": "Backend Engineer",
            "company": "FixtureCorp",
            "dates": "2020 - 2024",
            "bullets": [
                "Shipped Python services handling 1M requests a day.",
                "Cut PostgreSQL query times by half with indexes.",
                "Led a synthetic incident review that fixed flaky deploys.",
            ],
        },
        {
            "title": "Junior Backend Engineer",
            "company": "FixtureLabs",
            "dates": "2017 - 2020",
            "bullets": [
                "Maintained Django APIs serving synthetic fixture data.",
                "Added Redis caching that cut page loads by 30 percent.",
            ],
        },
    ],
}

JOB = {
    "id": "job-uat-1",
    "title": "Senior Backend Engineer",
    "company": "HiringCorp",
    "description": (
        "SYNTHETIC fixture posting. We need deep Python and PostgreSQL "
        "experience. You will build web services and data pipelines and "
        "lead a small team. Kubernetes is a must-have; Django and Redis "
        "are a plus."
    ),
}

# A genuinely different role: tailoring for JOB2 must produce genuinely
# different output (different matched skills, ordering, cover letter).
# The journey tailors once per job so version comparisons never depend
# on hash-ordering noise between identical runs (tailoring is
# deterministic: identical inputs give byte-identical output).
JOB2 = {
    "id": "job-uat-2",
    "title": "Django Platform Engineer",
    "company": "FixtureWeb",
    "description": (
        "SYNTHETIC fixture posting. We need a Django specialist to build "
        "and maintain web applications. Deep Django and Redis experience "
        "required; Python fluency expected. You will own our API and "
        "caching layers."
    ),
}

# Subprocess runs must not add repo-root entries that would shadow the
# repo tree: in-process module imports assume cwd == repo root (as does
# the E2E suite).
import sys as _sys  # noqa: E402
if str(Path(__file__).resolve().parent.parent.parent) not in _sys.path:
    _sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class ApplicationStudioJourney(JourneyCase):
    """Acceptance journey for Initiative 05: the application studio."""

    EPIC_MAP = {
        "test_epic1_versioned_resume_variants": (
            "E1", "Versioned resume variants",
            "Roadmap i05 E1 epic text; Q1 exit gate: "
            "\"every version can be restored\""),
        "test_epic2_evidence_library_trace": (
            "E2", "Evidence library",
            "i05 evidence-library mechanism, as implemented (this journey "
            "verifies the weaker property actually checkable: unapproved "
            "evidence never reaches the tailor): every derived item "
            "starts unapproved; links_for_job exposes only approved "
            "links to the tailor (studio.py cmd_variant_tailor feeds it "
            "directly to tailor_with_provenance); variant-trace joins "
            "each statement to its evidence status and reports no "
            "unapproved or unknown items (versions.py trace_report, "
            "whose docstring notes a clean report does NOT prove every "
            "line traces to approved evidence)"),
        "test_epic3_ats_readiness_copy_contract": (
            "E3", "ATS readiness check",
            "Roadmap i05 E3 epic text QA contract: \"it must never imply "
            "or predict vendor ranking, and any such claim blocks "
            "release\""),
        "test_epic4_diff_explains_changes": (
            "E4", "Side-by-side diff",
            "Roadmap i05 E4 epic text: explain every proposed resume and "
            "cover-letter change before approval"),
        "test_epic5_application_packet_checklist_gate": (
            "E5", "Application packet",
            "Roadmap i05 E5 epic text: bundle resume, letter, answers, "
            "fit rationale, and review checklist for one role"),
        "test_epic6_earned_success_feedback_gate": (
            "E6", "Earned success feedback",
            "Roadmap i05 E6 epic text; i05 Proof of value: the reviewer "
            "verifies delight is absent from prohibited states, "
            "dismissible everywhere, inert under reduced motion"),
    }

    # -- helpers ------------------------------------------------------
    def setUp(self) -> None:
        super().setUp()
        self.variants = self.workdir / "variants"
        self.library = self.workdir / "library"
        self.packets = self.workdir / "packets"
        self.state = self.workdir / "state"
        self.profile = self.workdir / "profile.json"
        self.profile.write_text(json.dumps(PROFILE), encoding="utf-8")
        self.job = self.workdir / "job.json"
        self.job.write_text(json.dumps(JOB), encoding="utf-8")
        self.job2 = self.workdir / "job2.json"
        self.job2.write_text(json.dumps(JOB2), encoding="utf-8")
        self.stores = [
            "--variants-dir", str(self.variants),
            "--library-dir", str(self.library),
            "--packets-dir", str(self.packets),
            "--state-dir", str(self.state),
        ]

    def studio(self, *args: str):
        cmd = list(args)
        if args and args[0] in STORE_SUBCOMMANDS:
            cmd += self.stores
        return self.run_script(STUDIO, *cmd, timeout=120)

    def studio_ok(self, *args: str) -> str:
        proc = self.studio(*args)
        return self.assert_ok(proc, f"studio {' '.join(args[:2])}")

    @staticmethod
    def _variant_id(create_output: str) -> str:
        m = re.search(r"variant (\S+) created", create_output)
        assert m, f"no variant id in: {create_output}"
        return m.group(1)

    @staticmethod
    def _version_id(tailor_output: str) -> str:
        m = re.search(r"committed (\S+)", tailor_output)
        assert m, f"no committed version in: {tailor_output}"
        return m.group(1)

    def _approve_all_evidence(self) -> None:
        from initiatives.i05 import evidence_library
        for item in evidence_library.list_items(library_dir=self.library):
            out = self.studio_ok("evidence-approve", item["evidence_id"])
            self.assertIn("approved", out.lower())

    def _tailored_variant(self) -> tuple[str, str]:
        """Approved-evidence variant flow used by several epics."""
        self.studio_ok("evidence-build", "--profile", str(self.profile))
        self._approve_all_evidence()
        out = self.studio_ok("variant-create", "senior-backend",
                             "--job-id", "job-uat-1")
        vid = self._variant_id(out)
        out = self.studio_ok(
            "variant-tailor", vid,
            "--profile", str(self.profile), "--job", str(self.job),
            "--job-id", "job-uat-1")
        return vid, self._version_id(out)

    # -- E1 -----------------------------------------------------------
    def test_epic1_versioned_resume_variants(self):
        """Checks that earlier resume versions can be restored exactly as they were committed, each carrying its own provenance."""
        out = self.studio_ok("variant-create", "base", "--job-id", "")
        base_vid = self._variant_id(out)
        out = self.studio_ok("variant-create", "senior-backend",
                             "--job-id", "job-uat-1")
        role_vid = self._variant_id(out)
        self.assertNotEqual(base_vid, role_vid,
                            "base and role branches must be distinct variants")

        # Two tailor runs on the role branch with genuinely different jobs:
        # two committed versions with genuinely different content.
        # (Tailoring is deterministic, so identical inputs would give
        # byte-identical output; the jobs must differ.)
        first = self._version_id(self.studio_ok(
            "variant-tailor", role_vid,
            "--profile", str(self.profile), "--job", str(self.job),
            "--job-id", "job-uat-1"))
        second = self._version_id(self.studio_ok(
            "variant-tailor", role_vid,
            "--profile", str(self.profile), "--job", str(self.job2),
            "--job-id", "job-uat-2"))
        self.assertNotEqual(first, second)

        # Restoring the prior version brings it back exactly:
        # byte-identical across two restores, different from v2.
        a = self.workdir / "v1a.md"
        b = self.workdir / "v1b.md"
        c = self.workdir / "v2.md"
        out = self.studio_ok("variant-restore", role_vid, first, "--out", str(a))
        self.assertIn(first, out)
        self.studio_ok("variant-restore", role_vid, first, "--out", str(b))
        self.studio_ok("variant-restore", role_vid, second, "--out", str(c))
        self.assertEqual(a.read_bytes(), b.read_bytes(),
                         "restoring a prior version must be byte-identical")
        self.assertNotEqual(a.read_bytes(), c.read_bytes(),
                            "restore must return the requested version, "
                            "not the latest")
        self.assertIn("FixtureCorp", a.read_text(encoding="utf-8"))

        # Every version carries provenance: job id, skill matches, and a
        # per-statement source map. Each tailored version records the job
        # it was tailored for.
        variant_doc = json.loads(
            next(self.variants.glob(f"{role_vid}.json")).read_text(
                encoding="utf-8"))
        versions = variant_doc["versions"]
        self.assertGreaterEqual(len(versions), 3)  # initial + two tailored
        prov1 = versions[1].get("provenance") or {}
        prov2 = versions[2].get("provenance") or {}
        self.assertEqual(prov1.get("job_id"), "job-uat-1")
        self.assertEqual(prov2.get("job_id"), "job-uat-2")
        for prov in (prov1, prov2):
            self.assertTrue(prov.get("statement_map"),
                            "tailored version must record its statement map")

        # The gate says "every version": the initial base version from
        # variant-create (versions[0]) restores too — byte-identical
        # across two restores, matching the committed content, and
        # distinct from the tailored v1.
        initial_id = versions[0]["version_id"]
        d0 = self.workdir / "v0a.md"
        e0 = self.workdir / "v0b.md"
        out = self.studio_ok("variant-restore", role_vid, initial_id,
                             "--out", str(d0))
        self.assertIn(initial_id, out)
        self.studio_ok("variant-restore", role_vid, initial_id,
                       "--out", str(e0))
        self.assertEqual(d0.read_bytes(), e0.read_bytes(),
                         "restoring the base version must be byte-identical")
        self.assertEqual(d0.read_bytes(),
                         versions[0]["resume_md"].encode("utf-8"),
                         "restored base version must match the committed "
                         "content")
        self.assertNotEqual(d0.read_bytes(), a.read_bytes(),
                            "base version must differ from the tailored v1")

    # -- E2 -----------------------------------------------------------
    def test_epic2_evidence_library_trace(self):
        """Checks that evidence starts unapproved, that only approved evidence reaches the tailor, and that the trace report classifies every statement's evidence with no unapproved or unknown items."""
        out = self.studio_ok("evidence-build", "--profile", str(self.profile))
        self.assertIn("derived", out)

        # Every derived item is tied to a source fact and starts
        # unapproved.
        from initiatives.i05 import evidence_library
        items = evidence_library.list_items(library_dir=self.library)
        self.assertGreater(len(items), 0)
        for item in items:
            self.assertTrue(item.get("text"),
                            "evidence must carry its phrasing")
            self.assertTrue(item.get("source"),
                            "evidence must name its source fact")
            self.assertFalse(item.get("approved"),
                             "evidence starts unapproved")

        # The tailor consults only APPROVED evidence: with nothing
        # approved, the tailor receives nothing.
        links = evidence_library.links_for_job("job-uat-1",
                                               library_dir=self.library)
        self.assertEqual(links, [],
                         "unapproved evidence must not reach the tailor")

        self._approve_all_evidence()
        items = evidence_library.list_items(library_dir=self.library)
        for item in items:
            self.assertTrue(item.get("approved"))

        # Now the tailor sees only approved items.
        links = evidence_library.links_for_job("job-uat-1",
                                               library_dir=self.library)
        self.assertGreater(len(links), 0,
                           "approved portfolio links should reach the tailor")
        approved_ids = {item["evidence_id"] for item in items}
        for link in links:
            self.assertIn(link.get("evidence_id"), approved_ids,
                          "only approved evidence reaches the tailor")

        # The trace report classifies each statement's evidence ids as
        # profile/system/approved/unapproved/unknown: a clean report
        # means no statement references unapproved or unknown evidence.
        # (Per the trace_report docstring, a clean report does NOT prove
        # every line traces to approved evidence — profile:* and
        # system:* lines are disclosed, never approved — so this journey
        # makes no per-statement approved-backing claim.)
        out = self.studio_ok("variant-create", "senior-backend",
                             "--job-id", "job-uat-1")
        vid = self._variant_id(out)
        out = self.studio_ok(
            "variant-tailor", vid,
            "--profile", str(self.profile), "--job", str(self.job),
            "--job-id", "job-uat-1")
        version = self._version_id(out)
        out = self.studio_ok("variant-trace", vid, version)
        self.assertIn("unapproved: (none)", out)
        self.assertIn("unknown: (none)", out)

    # -- E3 -----------------------------------------------------------
    def test_epic3_ats_readiness_copy_contract(self):
        """Checks that the readiness check talks about format and completeness only, and never claims or predicts any hiring-system ranking."""
        resume = self.workdir / "resume.md"
        resume.write_text(
            "# SYNTHETIC UAT Persona\n"
            "uat@example.com | 555-019-9000 | New York, NY\n\n"
            "## Experience\n"
            "### Backend Engineer, FixtureCorp (2020 - 2024)\n"
            "- Shipped Python services handling 1M requests a day.\n"
            "- Cut PostgreSQL query times by half with indexes.\n\n"
            "## Skills\n"
            "Python, PostgreSQL, Django, Redis, Kubernetes\n",
            encoding="utf-8")
        proc = self.studio("ats", "--resume", str(resume),
                           "--job", str(self.job),
                           "--profile", str(self.profile))
        # rc 0 = ready, rc 2 = not ready: both are real report paths.
        self.assertIn(proc.returncode, (0, 2))
        text = proc.stdout.lower()

        from initiatives.i05 import ats_check
        for banned in ats_check.COPY_CONTRACT_BANNED:
            self.assertNotIn(
                banned, text,
                f"QA contract violation: ATS output contains '{banned}'")
        # The product's own honesty disclaimer must accompany the report.
        self.assertIn("does not predict how any hiring system", proc.stdout)

    # -- E4 -----------------------------------------------------------
    def test_epic4_diff_explains_changes(self):
        """Checks that the side-by-side diff explains every proposed resume change before anything is approved."""
        vid, first = self._tailored_variant()
        # Tailor the same variant for a genuinely different job so the
        # diff explains real changes. (Tailoring is deterministic:
        # re-tailoring the identical job would give byte-identical
        # output and an empty diff.)
        out = self.studio_ok(
            "variant-tailor", vid,
            "--profile", str(self.profile), "--job", str(self.job2),
            "--job-id", "job-uat-2")
        second = self._version_id(out)

        base = self.workdir / "before.md"
        tailored = self.workdir / "after.md"
        self.studio_ok("variant-restore", vid, first, "--out", str(base))
        self.studio_ok("variant-restore", vid, second, "--out", str(tailored))

        out = self.studio_ok("diff", "--base", str(base),
                             "--tailored", str(tailored))
        m = re.search(r"(\d+) proposed change\(s\)", out)
        self.assertIsNotNone(m, f"diff must report a change count: {out}")
        change_count = int(m.group(1))
        self.assertGreater(change_count, 0,
                           "two tailored versions must differ")

        # Every change is numbered and explained, not just listed.
        lines = [ln for ln in out.splitlines() if re.match(r"^\d+\. ", ln)]
        self.assertEqual(
            len(lines), change_count,
            "every proposed change must have its own explanation line")
        for ln in lines:
            self.assertRegex(
                ln.lower(), r"resume|skills|cover[- ]letter|experience",
                f"explanation must say where the change lands: {ln}")
            self.assertIn("'", ln,
                          f"explanation must quote the changed text: {ln}")
        self.assertIn("need review before approval", out)

    # -- E5 -----------------------------------------------------------
    def test_epic5_application_packet_checklist_gate(self):
        """Checks that one packet bundles the resume, letter, answers, fit rationale, and review checklist, and that approval stays blocked until the checklist is complete — including when only some changes have been reviewed."""
        vid, version = self._tailored_variant()
        self.studio_ok("variant-approve", vid, version)
        out = self.studio_ok(
            "packet-build", "--job", str(self.job),
            "--profile", str(self.profile), "--job-id", "job-uat-1",
            "--variant", vid, "--version", version)
        m = re.search(r"packet (\S+) \((\S+)\)", out)
        self.assertIsNotNone(m, f"no packet id in: {out}")
        packet_id = m.group(1)

        packet_doc = json.loads(
            (self.packets / f"{packet_id}.json").read_text(encoding="utf-8"))
        # The packet always carries these parts (answers is an empty list
        # until a grill session supplies interview answers).
        for part in ("resume_md", "cover_letter", "answers",
                     "fit_rationale", "review_checklist"):
            self.assertIn(part, packet_doc,
                          f"packet must bundle '{part}'")
        for part in ("resume_md", "cover_letter", "fit_rationale",
                     "review_checklist"):
            self.assertTrue(packet_doc.get(part),
                            f"packet must bundle a non-empty '{part}'")
        checklist_ids = {item["id"] for item in
                         packet_doc["review_checklist"]}
        self.assertEqual(
            checklist_ids,
            {"diff-reviewed", "honesty-clean", "ats-ready",
             "version-approved", "trace-clean"},
            "packet must carry the full review checklist")
        self.assertTrue(any(item["status"] == "pending"
                            for item in packet_doc["review_checklist"]),
                        "fresh packet must have pending checklist items")

        # Approval is checklist-gated: pending items block it.
        proc = self.studio("packet-approve", packet_id,
                           "--profile", str(self.profile),
                           "--job", str(self.job))
        self.assertEqual(proc.returncode, 2)
        self.assertIn("pending checklist items", proc.stdout.lower())

        # Review every proposed change, then the gate opens.
        from initiatives.i05 import packet as packet_mod
        pkt = packet_mod.get_packet(packet_id, packets_dir=self.packets)
        changes = [c["change_id"] for c in (pkt.get("changes") or [])
                   if not c.get("reviewed")]
        self.assertGreater(len(changes), 0)

        # Distracted-user path: review only SOME of the changes. The
        # checklist is still incomplete, so approval must STAY blocked.
        reviewed_some, remaining = changes[:-1], changes[-1:]
        self.assertTrue(reviewed_some,
                        "need at least two changes for the partial-review "
                        "path")
        for change_id in reviewed_some:
            out = self.studio_ok("packet-review", packet_id, change_id)
            self.assertIn(change_id, out)
        proc = self.studio("packet-approve", packet_id,
                           "--profile", str(self.profile),
                           "--job", str(self.job))
        self.assertEqual(proc.returncode, 2,
                         "a partial review must not unblock approval")
        self.assertIn("blocked:", proc.stdout)
        self.assertIn("pending checklist items", proc.stdout.lower())

        # Review the rest, then the gate opens.
        for change_id in remaining:
            out = self.studio_ok("packet-review", packet_id, change_id)
            self.assertIn(change_id, out)

        out = self.studio_ok("packet-approve", packet_id,
                             "--profile", str(self.profile),
                             "--job", str(self.job))
        self.assertIn(f"approved {packet_id}", out)
        approved_doc = packet_mod.get_packet(packet_id,
                                             packets_dir=self.packets)
        self.assertEqual(approved_doc["status"], "approved")
        self.assertTrue(all(item["status"] != "pending"
                            for item in
                            approved_doc["review_checklist"]))

    # -- E6 -----------------------------------------------------------
    def test_epic6_earned_success_feedback_gate(self):
        """Checks that the congratulatory message appears only after a success you triggered, never on failure or rejection, and can always be dismissed."""
        # Gate closed: no delight.
        out = self.studio_ok("feedback")
        self.assertIn("(no success moment", out)

        # Gate open but the success wasn't user-initiated: still quiet.
        out = self.studio_ok("feedback", "--gate-open")
        self.assertIn("(no success moment", out)

        # A prohibited state (rejection) silences delight even with the
        # gate open and a user-initiated event.
        out = self.studio_ok("feedback", "--gate-open", "--user-initiated",
                             "--state", "rejection")
        self.assertIn("(no success moment", out)

        # The real success path: gate open, user-initiated success.
        out = self.studio_ok("feedback", "--gate-open", "--user-initiated",
                             "--state", "success")
        self.assertNotIn("(no success moment", out)
        m = re.search(r"feedback-dismiss (\S+)\)", out)
        self.assertIsNotNone(m, "moment must print its dismiss command")
        dismiss_key = m.group(1)

        # Every moment is dismissible, and a dismissed moment never
        # re-surfaces.
        out = self.studio_ok("feedback-dismiss", dismiss_key)
        self.assertIn(dismiss_key, out)
        out = self.studio_ok("feedback", "--gate-open", "--user-initiated",
                             "--state", "success")
        self.assertIn("(no success moment", out)

        # Under reduced motion the payload carries no animation at all.
        from initiatives.i05 import success_feedback
        moment = success_feedback.success_moment(
            "packet-approved",
            {"state": "success", "gate_open": True,
             "user_initiated": True, "reduced_motion": True},
            state_dir=self.state)
        self.assertIsNone(moment["animation"],
                          "reduced-motion payload must carry no animation")


if __name__ == "__main__":
    unittest.main()

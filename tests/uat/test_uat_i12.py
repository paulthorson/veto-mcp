#!/usr/bin/env python3
"""Automated UAT acceptance journey for Initiative 12 (public growth & education).

The journey follows the visitor in the roadmap story: "A curious visitor
tries the public JD decoder demo, gets a fit explanation, and shares a
privacy-safe score card -- with no account and no data leaving their machine."

Each method drives the REAL product code against a hermetic temp working
dir: as a subprocess (``python -m initiatives.i12``) by default, with two
narrow in-process carve-outs (no mocks of the machinery anywhere):
- the changelog render has no CLI flag for the entries-file location, so
  the render path goes through ``cli.main()`` in-process with
  ``ENTRIES_FILE`` redirected to a temp file (the same seam the shipped
  E2E suite uses);
- the analytics tripwire injection and the tripwire-adjacent store
  protocol go through the real, unmocked ``TelemetryStore`` bound to the
  same temp state file the CLI uses, because the CLI's token grammar is
  deliberately too strict to smuggle a content-bearing field through
  ``--record`` (the module's own backstop proof pattern from
  ``tests/test_i12_telemetry.py``).

Nothing here is published, submitted, or sent anywhere: the module is
local-only by design and the journey keeps it that way.

Rule-2 trade-off statement: this journey trades re-proving the ground the
shipped ``tests/test_e2e_i12.py`` suite already owns (the JD-decoder demo,
deterministic onboarding assignment, score-card privacy refusal, changelog
health, and the consent/record flow) for genuinely new acceptance ground
the E2E suite never covers: the analytics tripwire's quarantine and
re-enable chain, the named security-specialist plus independent-reviewer
protocol, the operator veto, dark-pattern copy checks, and the exact shape of
the public analytics payload the Q3 exit gate watches.

The repo has roadmap epics but no per-story acceptance criteria, so
assertions trace only to the epic text, the Proof of value, the Q3 exit
gate, and the i12 README -- named in EPIC_MAP per the harness contract.
"""

from __future__ import annotations

import io
import json
import os
import re
import stat
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from tests.uat.harness import JourneyCase

from initiatives.i12 import __main__ as i12_cli
from initiatives.i12 import changelog as i12_changelog
from initiatives.i12 import telemetry as i12_telemetry

REPO = Path(__file__).resolve().parent.parent.parent

EPIC_MAP = {
    "test_public_tools_decode_explain_and_rank_locally": (
        "E1", "Interactive public tools", "Roadmap i12 E1 epic text"),
    "test_share_artifacts_never_carry_private_content": (
        "E2", "Shareable artifacts",
        "Roadmap i12 E2 epic text + Q3 exit gate (no content fields in public payloads)"),
    "test_changelog_shows_shipped_rejected_limited_with_reasons": (
        "E3", "Transparent changelog", "Roadmap i12 E3 epic text"),
    "test_education_library_reachable": (
        "E4", "Education library", "Roadmap i12 E4 epic text"),
    "test_onboarding_experiment_deterministic_and_clean": (
        "E5", "Onboarding experiments", "Roadmap i12 E5 epic text"),
    "test_telemetry_tripwire_shuts_off_and_quarantines": (
        "E6", "Consent-based product analytics",
        "Q3 exit gate + Roadmap i12 E6 epic text"),
}

#: The 9 onboarding experiment cells (role maturity x tech comfort),
#: read from ``initiatives/i12/onboarding.py::build_paths``.
CELLS = [
    (rm, tc)
    for rm in ("new", "switching", "senior")
    for tc in ("low", "medium", "high")
]

#: Synthetic contact details used as hostile input to the privacy gates.
#: Not real people; only ever fed to the product as injection probes.
PROBE_EMAIL = "alex.example@example.com"
PROBE_PHONE = "555-010-2030"

#: The pinned public-analytics schema id (Q3 exit-gate contract).
PUBLIC_ANALYTICS_SCHEMA = "i12-public-analytics-v1"

#: Grammar the product pins telemetry tokens to (no free-text fields exist
#: in the schema on purpose); guide-view keys must be real guide ids from
#: the education library, never arbitrary strings.
_TOKEN_GRAMMAR = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,31}$")


class Initiative12UATJourney(JourneyCase):
    # -- helpers -------------------------------------------------------
    def _i12(self, *argv: str):
        """Run the real i12 CLI in the hermetic temp working dir."""
        return self.run_module(
            "initiatives.i12", *argv,
            env={"PYTHONPATH": str(REPO)}, cwd=self.workdir)

    def _render_changelog(self, entries: list[dict]) -> str:
        """Render the changelog markdown against a temp entries file.

        The i12 CLI exposes no flag for the entries-file location, so the
        real render entrypoint is driven in-process with ENTRIES_FILE
        redirected to the temp dir (proven seam from tests/test_e2e_i12.py).
        The repo's entries copy is never touched.
        """
        fake = self.workdir / "CHANGELOG_ENTRIES.json"
        fake.write_text(json.dumps(entries), encoding="utf-8")
        buf = io.StringIO()
        with mock.patch.object(i12_changelog, "ENTRIES_FILE", fake):
            with redirect_stdout(buf):
                rc = i12_cli.main(["changelog"])
            health = i12_changelog.health()
        self.assertEqual(rc, 0, "changelog render failed")
        return buf.getvalue(), health

    # ------------------------------------------------------------------
    # E1: Interactive public tools
    # ------------------------------------------------------------------
    def test_public_tools_decode_explain_and_rank_locally(self):
        """Trying the public demos: a visitor can decode a job posting, get a fit explanation, check application risk, and compare roles — all on their own machine, with nothing uploaded or submitted."""
        jd = self.synthetic_jd()
        job = {"title": "Senior Backend Engineer", "company": "HiringCorp",
               "requirements": ["Python", "PostgreSQL", "Kubernetes"],
               "nice_to_have": ["Redis"]}
        job_file = self.workdir / "job.json"
        job_file.write_text(json.dumps(job), encoding="utf-8")
        jobs_file = self.workdir / "jobs.json"
        jobs_file.write_text(json.dumps([
            {"title": "Senior Backend Engineer", "requirements": ["Python"]},
            {"title": "Rust Systems Engineer", "requirements": ["Rust"]},
        ]), encoding="utf-8")

        # JD decoder: a decode with reasons, flags, and a plain-English
        # statement of its limits -- and it never submits anything.
        proc = self._i12("tools", "jd", "--text", jd, "--json")
        out = self.assert_ok(proc, "tools jd")
        decode = json.loads(out)
        self.assertEqual(decode["tool"], "jd_decoder")
        self.assertTrue(decode.get("demo"), "demo must be labeled a demo")
        self.assertFalse(
            decode.get("submits_anything"),
            "the demo must never submit anything")
        self.assertGreater(len(decode.get("top_reasons", [])), 0,
                           "decode must explain itself with reasons")
        self.assertTrue(decode.get("limitations"),
                        "decode must state its limits in plain language")
        self.assertIn("device", decode["limitations"].lower(),
                      "the decode must say the analysis stays on the device")

        # Fit explainer: factor-by-factor explanation against typed skills.
        proc = self._i12("tools", "fit", "--job-json", str(job_file),
                         "--skills", "python,sql", "--json")
        out = self.assert_ok(proc, "tools fit")
        fit = json.loads(out)
        self.assertGreater(len(fit.get("factors", [])), 0,
                           "fit explanation must break down its factors")
        for factor in fit["factors"]:
            for key in ("factor", "score", "why"):
                self.assertIn(key, factor,
                              f"fit factor missing {key!r}: {factor}")

        # Application-risk check: findings with next steps, proposal-only.
        proc = self._i12("tools", "risk", "--job-json", str(job_file),
                         "--skills", "python", "--json")
        out = self.assert_ok(proc, "tools risk")
        risk = json.loads(out)
        self.assertEqual(risk["tool"], "risk_check")
        self.assertGreater(len(risk.get("findings", [])), 0,
                           "risk check must return useful findings")
        for finding in risk["findings"]:
            for key in ("severity", "area", "finding", "next_step"):
                self.assertIn(key, finding,
                              f"risk finding missing {key!r}: {finding}")
        self.assertTrue(risk.get("proposal_only"))
        self.assertTrue(risk.get("cannot_submit"),
                        "risk check must not be able to submit anything")

        # Role comparison: two roles ranked side by side.
        proc = self._i12("tools", "compare", "--jobs-json", str(jobs_file),
                         "--skills", "python", "--json")
        out = self.assert_ok(proc, "tools compare")
        compare = json.loads(out)
        self.assertEqual(compare["tool"], "role_compare")
        self.assertEqual(compare.get("compared"), 2)
        self.assertEqual(len(compare.get("rows", [])), 2)
        for row in compare["rows"]:
            self.assertIn("title", row)
            self.assertIn("fit", row)

    # ------------------------------------------------------------------
    # E2: Shareable artifacts
    # ------------------------------------------------------------------
    def _assert_share_refuses(self, label: str, *argv: str) -> None:
        """A share invocation carrying contact details must fail closed.

        The real, empirically observed contract (probed 2026-09-16): the
        command exits non-zero, emits no artifact on stdout, and the
        private tokens never reach stdout.
        """
        proc = self._i12(*argv)
        self.assertNotEqual(
            proc.returncode, 0,
            f"{label}: carrying contact details must not build successfully "
            f"(rc={proc.returncode})")
        for token in (PROBE_EMAIL, PROBE_PHONE):
            self.assertNotIn(token, proc.stdout,
                             f"{label}: contact details leaked into output")
        self.assertNotIn("# Veto ", proc.stdout,
                         f"{label}: an artifact was emitted despite the "
                         "privacy failure")

    def test_share_artifacts_never_carry_private_content(self):
        """Sharing a score card stays private: the card carries scores and a methodology note, and every field is probed — any attempt to sneak contact details into any field is refused, never scrubbed-and-published."""
        # A clean score card: scores only, methodology note attached, and
        # the card says out loud what it never contains. POSITIVE
        # assertions: the card carries its own content and its privacy
        # promise, verbatim from the product.
        proc = self._i12(
            "share", "score-card", "--role", "Backend Eng",
            "--company", "Acme", "--score", "82", "--verdict", "strong",
            "--reasons", "solid Python depth|clear ownership examples",
            "--factors-json", "[]", "--markdown")
        out = self.assert_ok(proc, "share score-card")
        self.assertIn("Backend Eng", out)
        self.assertIn("Acme", out)
        self.assertIn("82", out)
        self.assertIn("strong", out)
        self.assertIn("_Methodology:", out,
                      "the card must carry its methodology note")
        self.assertIn("never includes your resume text", out.lower(),
                      "the card must state its privacy promise")

        # Field-by-field injection: every content-bearing field is probed
        # with a real email + phone, and the REAL behavior is asserted.
        # Empirically (2026-09-16) every field FAILS CLOSED (rc != 0, no
        # artifact on stdout); nothing is scrubbed-and-emitted:
        #  - score-card --role/--company/--verdict/--reasons/--factors-json:
        #      privacy.assert_clean raises ContentDetected (rc=1); stderr
        #      names the offending field path, e.g.
        #      "top_reasons: [0]: value contains an email address".
        #  - interview-plan --role/--factors-json: ContentDetected (rc=1).
        #  - progress --factors-json: ValueError (rc=1) -- email-shaped
        #      keys die on "workflow names must be simple tokens",
        #      phone-shaped values die on int() conversion.
        #  - --sessions/--weeks/--outcomes (type=int) and --score
        #      (type=float): the argparse grammar itself rejects
        #      non-numeric content outright (rc=2, usage on stderr,
        #      nothing on stdout) -- these fields cannot carry a contact
        #      detail past the CLI boundary at all.
        contact = f"reach me at {PROBE_EMAIL} or {PROBE_PHONE}"
        sc = ["share", "score-card", "--company", "Acme", "--score", "82",
              "--verdict", "strong", "--factors-json", "[]", "--markdown"]
        self._assert_share_refuses(
            "score-card --role", *sc, "--role", contact,
            "--reasons", "fine")
        self._assert_share_refuses(
            "score-card --company",
            "share", "score-card", "--role", "Backend Eng",
            "--company", contact, "--score", "82", "--verdict", "strong",
            "--reasons", "fine", "--factors-json", "[]", "--markdown")
        self._assert_share_refuses(
            "score-card --verdict",
            "share", "score-card", "--role", "Backend Eng",
            "--company", "Acme", "--score", "82", "--verdict", contact,
            "--reasons", "fine", "--factors-json", "[]", "--markdown")
        self._assert_share_refuses(
            "score-card --reasons",
            "share", "score-card", "--role", "Backend Eng",
            "--company", "Acme", "--score", "82", "--verdict", "strong",
            "--reasons", contact, "--factors-json", "[]", "--markdown")
        self._assert_share_refuses(
            "score-card --factors-json",
            "share", "score-card", "--role", "Backend Eng",
            "--company", "Acme", "--score", "82", "--verdict", "strong",
            "--reasons", "fine",
            "--factors-json", json.dumps(
                [{"name": "depth", "score": 9,
                  "evidence_summary": contact}]),
            "--markdown")
        self._assert_share_refuses(
            "score-card --score",
            "share", "score-card", "--role", "Backend Eng",
            "--company", "Acme", "--score", PROBE_PHONE, "--verdict",
            "strong", "--reasons", "fine", "--factors-json", "[]",
            "--markdown")

        ip = ["share", "interview-plan", "--factors-json", "[]",
              "--markdown"]
        self._assert_share_refuses(
            "interview-plan --role",
            *ip, "--role", contact, "--sessions", "3")
        self._assert_share_refuses(
            "interview-plan --factors-json",
            *ip, "--role", "Backend Eng", "--sessions", "3",
            "--factors-json", json.dumps(
                [{"area": "system design", "why_short": contact,
                  "drills": 2}]))
        self._assert_share_refuses(
            "interview-plan --sessions",
            *ip, "--role", "Backend Eng", "--sessions", PROBE_PHONE)

        pr = ["share", "progress", "--factors-json", "{}", "--markdown"]
        self._assert_share_refuses(
            "progress --weeks",
            *pr, "--weeks", PROBE_PHONE, "--outcomes", "0")
        self._assert_share_refuses(
            "progress --outcomes",
            *pr, "--weeks", "4", "--outcomes", PROBE_EMAIL)
        self._assert_share_refuses(
            "progress --factors-json (email key)",
            *pr, "--weeks", "4", "--outcomes", "0",
            "--factors-json", json.dumps({PROBE_EMAIL: 1}))
        self._assert_share_refuses(
            "progress --factors-json (phone value)",
            *pr, "--weeks", "4", "--outcomes", "0",
            "--factors-json", json.dumps({"jd_decode": PROBE_PHONE}))

        # The other two artifacts build cleanly with the same guarantees.
        for kind, extra in (
                ("interview-plan", ["--role", "Backend Eng",
                                    "--factors-json", "[]", "--sessions", "3"]),
                ("progress", ["--weeks", "4", "--factors-json", "{}",
                              "--outcomes", "2"])):
            proc = self._i12("share", kind, *extra, "--markdown")
            out = self.assert_ok(proc, f"share {kind}")
            self.assertIn("_Methodology:", out)
            self.assertIn("never includes your resume text", out.lower())

    # ------------------------------------------------------------------
    # E3: Transparent changelog
    # ------------------------------------------------------------------
    def test_changelog_shows_shipped_rejected_limited_with_reasons(self):
        """Reading the changelog shows what shipped, what was rejected, and what's still limited — each with a reason; missing rejections or limitations are flagged as transparency defects."""
        healthy = [
            {"date": "2026-09-15", "category": "shipped",
             "title": "SYNTHETIC shipped item",
             "why": "SYNTHETIC shipped reason: the demo set was finished.",
             "limitation": "SYNTHETIC shipped limitation: demos only.",
             "source": "synthetic-uat"},
            {"date": "2026-09-15", "category": "rejected",
             "title": "SYNTHETIC rejected item",
             "why": "SYNTHETIC rejection reason: it would count vanity traffic.",
             "limitation": "N/A -- rejected outright.",
             "source": "synthetic-uat"},
            {"date": "2026-09-15", "category": "limited",
             "title": "SYNTHETIC limited item",
             "why": "SYNTHETIC limitation reason: needs the local app.",
             "limitation": "SYNTHETIC known limitation: demos only.",
             "source": "synthetic-uat"},
        ]
        rendered, health = self._render_changelog(healthy)
        for section in ("## Shipped", "## Rejected", "## Limited"):
            self.assertIn(section, rendered,
                          f"changelog must show a {section} section")
        for entry in healthy:
            self.assertIn(entry["title"], rendered)
            self.assertIn(entry["why"], rendered,
                          "every entry must carry its reason, not just a title")
        self.assertNotIn("\u26a0\ufe0f", rendered,
                         "a complete changelog must not flag transparency "
                         "defects")
        self.assertFalse(health["missing_rejections"])
        self.assertFalse(health["missing_limitations"])

        # The defect flag: a changelog with no rejections and no limitations
        # says so out loud instead of hiding the gaps.
        thin = [dict(healthy[0])]
        rendered, health = self._render_changelog(thin)
        self.assertIn("no rejected items", rendered,
                      "missing rejections must be flagged as a defect")
        self.assertIn("no known limitations", rendered,
                      "missing limitations must be flagged as a defect")
        self.assertTrue(health["missing_rejections"])
        self.assertTrue(health["missing_limitations"])

    # ------------------------------------------------------------------
    # E4: Education library
    # ------------------------------------------------------------------
    def test_education_library_reachable(self):
        """The education guides exist as real, titled documents a visitor can read. (Honest scope: these are the /learn page's source files; verifying the rendered web page itself needs a real browser and stays a manual acceptance check, not an automated one.)"""
        guides = sorted((REPO / "docs" / "i12" / "education").glob("*.md"))
        self.assertGreater(
            len(guides), 0,
            "the education library must contain at least one guide")
        for guide in guides:
            text = guide.read_text(encoding="utf-8").strip()
            self.assertTrue(text, f"{guide.name} must not be empty")
            first_line = text.splitlines()[0]
            self.assertTrue(
                first_line.startswith("# "),
                f"{guide.name} must carry a title, got {first_line!r}")
        # Manual-check note (deliberately NOT automated): whether a visitor
        # can actually reach these on the marketing site's rendered /learn
        # page can only be proven in a real browser; the automated journey
        # covers the guides' existence, substance, and titles only.

    # ------------------------------------------------------------------
    # E5: Onboarding experiments
    # ------------------------------------------------------------------
    def test_onboarding_experiment_deterministic_and_clean(self):
        """Joining the onboarding experiment: the same answers always lead to the same guided path (9 possible combinations), and manipulative copy is caught by automatic checks."""
        # All 9 cells of the role-maturity x tech-comfort grid assign
        # their canonical path -- same inputs, same path, every time.
        seen = set()
        for role_maturity, tech_comfort in CELLS:
            proc = self._i12(
                "onboarding", "--role-maturity", role_maturity,
                "--tech-comfort", tech_comfort,
                "--session-token", "uat-session-1")
            out = self.assert_ok(proc, "onboarding assign")
            payload = json.loads(out)
            expected = f"onboard-{role_maturity}-{tech_comfort}"
            self.assertEqual(payload["path_id"], expected)
            seen.add(payload["path_id"])
            self.assertGreaterEqual(len(payload["steps"]), 3,
                                    "an onboarding path must guide with "
                                    "real steps")
        self.assertEqual(len(seen), 9,
                         "all 9 experiment cells must assign distinct paths")

        # Determinism across separate runs: the experiment never
        # re-randomizes a visitor between visits.
        first = json.loads(self.assert_ok(
            self._i12("onboarding", "--role-maturity", "senior",
                      "--tech-comfort", "high",
                      "--session-token", "uat-session-2"),
            "onboarding run 1"))["path_id"]
        second = json.loads(self.assert_ok(
            self._i12("onboarding", "--role-maturity", "senior",
                      "--tech-comfort", "high",
                      "--session-token", "uat-session-2"),
            "onboarding run 2"))["path_id"]
        self.assertEqual(first, second)
        self.assertEqual(first, "onboard-senior-high")

        # Dark patterns are banned by code-checked rules: manipulative
        # copy is flagged, honest copy passes.
        dark = self.workdir / "dark-copy.txt"
        dark.write_text(
            "Only 3 spots left! Act now before they are gone. Everyone "
            "else already signed up -- do not miss out.", encoding="utf-8")
        proc = self._i12("onboarding", "--check-copy", str(dark))
        out = self.assert_ok(proc, "onboarding check-copy (dark)")
        dark_result = json.loads(out)
        self.assertFalse(dark_result["clean"],
                         "manipulative copy must be flagged")
        self.assertGreater(len(dark_result["findings"]), 0)
        self.assertTrue(any("why_banned" in f
                            for f in dark_result["findings"]),
                        "each finding must say why the pattern is banned")

        honest = self.workdir / "honest-copy.txt"
        honest.write_text(
            "Paste a job description. Veto decodes it on your device -- "
            "no account needed, and you can skip any step.",
            encoding="utf-8")
        proc = self._i12("onboarding", "--check-copy", str(honest))
        out = self.assert_ok(proc, "onboarding check-copy (honest)")
        honest_result = json.loads(out)
        self.assertTrue(honest_result["clean"],
                        "honest copy must pass the dark-pattern check")
        self.assertEqual(honest_result["findings"], [])

    # ------------------------------------------------------------------
    # E6: Consent-based product analytics (Q3 exit gate)
    # ------------------------------------------------------------------
    def test_telemetry_tripwire_shuts_off_and_quarantines(self):
        """Analytics stay off until you opt in; if any private content slips into an event, analytics shut off, the data is quarantined, and turning them back on requires a named security specialist, a different independent reviewer, and no operator veto."""
        state = self.workdir / "telemetry.json"

        # 1. Off by default: a fresh install consents to nothing and
        #    records nothing.
        proc = self._i12("telemetry", "--status", "--state", str(state))
        status = json.loads(self.assert_ok(proc, "telemetry status"))
        self.assertFalse(status["consented"], "analytics default OFF")
        self.assertFalse(status["enabled"], "analytics default OFF")

        # 2. Enabling is explicit: opt in through the consent switch.
        proc = self._i12("telemetry", "--consent", "on",
                         "--state", str(state))
        out = self.assert_ok(proc, "telemetry consent on")
        self.assertTrue(json.loads(out)["consent"]["opted_in"])
        proc = self._i12("telemetry", "--status", "--state", str(state))
        status = json.loads(self.assert_ok(proc, "telemetry status"))
        self.assertTrue(status["enabled"])
        self.assertTrue(status["tripwire_armed"],
                        "the tripwire arms as soon as recording is possible")

        # 3. The tripwire: a content field smuggled into an event trips it.
        #    The CLI's token grammar cannot carry such a value, so this goes
        #    through the REAL TelemetryStore (unmocked) -- the module's own
        #    backstop proof pattern from tests/test_i12_telemetry.py.
        store = i12_telemetry.TelemetryStore(state)
        store.record("tool_opened", tool="jd_decoder", surface="terminal",
                     session_id="sess1")
        with self.assertRaises(i12_telemetry.TripwireTripped):
            store.record("tool_opened", tool="jd_decoder",
                         surface="terminal", session_id="5551234567")

        # 4. User-visible fallout: analytics are off and an incident is open.
        proc = self._i12("telemetry", "--status", "--state", str(state))
        status = json.loads(self.assert_ok(proc, "telemetry status"))
        self.assertFalse(status["enabled"],
                         "the tripwire must shut analytics off")
        self.assertEqual(status["open_incidents"], 1)

        # 5. Quarantine: the offending payload plus the live events are
        #    persisted access-controlled, and the live copy is deleted.
        qdir = state.parent / "quarantine"
        self.assertTrue(qdir.is_dir(), "a quarantine directory must exist")
        self.assertEqual(stat.S_IMODE(os.stat(qdir).st_mode), 0o700,
                         "quarantine directory must be access-controlled")
        qfiles = list(qdir.glob("INC-*.json"))
        self.assertEqual(len(qfiles), 1,
                         "exactly one incident must be quarantined")
        self.assertEqual(stat.S_IMODE(os.stat(qfiles[0]).st_mode), 0o600,
                         "quarantine file must be access-controlled")
        quarantined = json.loads(qfiles[0].read_text(encoding="utf-8"))
        self.assertIn("incident_id", quarantined)
        self.assertEqual(quarantined["offending_event"]["session_id"],
                         "5551234567",
                         "the offending payload must be preserved for the "
                         "specialist's investigation")
        self.assertEqual(len(quarantined["prior_live_events"]), 1,
                         "prior live events move into quarantine too")
        # Public accessor: the live copy must be deleted after quarantine.
        live = i12_telemetry.TelemetryStore(state)
        self.assertEqual(live.status()["events_stored"], 0,
                         "the live copy must be deleted after quarantine")

        # 6. Re-enable requires the named chain. The CLI exposes no
        #    re-enable surface (verified in `telemetry --help`), so the
        #    real store API is driven against the same temp state file.
        store2 = i12_telemetry.TelemetryStore(state)
        with self.assertRaises(i12_telemetry.TelemetryError):
            store2.reenable()  # open incident: blocked
        # (No public incident-id accessor exists; the _state read below is
        # read-only test plumbing, never product state poking.)
        incident_id = store2._state["incidents"][-1]["incident_id"]
        with self.assertRaises(i12_telemetry.TelemetryError):
            store2.clear_incident(incident_id, "", "x" * 30)
        store2.set_roles(specialist="Jordan Ellis",
                         reviewer="Independent Reviewer",
                         populated_by="uat-journey")
        with self.assertRaises(i12_telemetry.TelemetryError):
            store2.clear_incident(incident_id, "Jordan Ellis", "too short")
        store2.clear_incident(
            incident_id, "Jordan Ellis",
            "SYNTHETIC tripwire test: a phone-shaped token value was "
            "injected into a test event; no real user content involved.")
        with self.assertRaises(i12_telemetry.TelemetryError):
            store2.reenable()  # cleared but not yet verified: blocked
        with self.assertRaises(i12_telemetry.TelemetryError):
            store2.verify_clearance(incident_id, "Jordan Ellis", "ref-1")
        store2.verify_clearance(incident_id, "Independent Reviewer",
                                "uat-evidence-1")
        store2.reenable()
        self.assertTrue(store2.enabled)
        proc = self._i12("telemetry", "--status", "--state", str(state))
        status = json.loads(self.assert_ok(proc, "telemetry status"))
        self.assertTrue(status["enabled"])
        self.assertEqual(status["open_incidents"], 0)

        # 7. Operator veto blocks re-enable unconditionally -- only a typed
        #    confirmation lifts it. (A second trip to exercise the path.)
        store2.record("tool_opened", tool="jd_decoder", surface="terminal",
                      session_id="sess2")
        with self.assertRaises(i12_telemetry.TripwireTripped):
            store2.record("tool_opened", tool="jd_decoder",
                          surface="terminal", session_id="5559876543")
        store3 = i12_telemetry.TelemetryStore(state)
        incident2 = store3._state["incidents"][-1]["incident_id"]
        store3.clear_incident(
            incident2, "Jordan Ellis",
            "SYNTHETIC second trip: same phone-shaped token test as the "
            "first; scanner still armed.")
        store3.verify_clearance(incident2, "Independent Reviewer",
                                "uat-evidence-2")
        store3.paul_veto("holding for deeper investigation")
        with self.assertRaises(i12_telemetry.TelemetryError):
            store3.reenable()  # veto in force: blocked
        with self.assertRaises(i12_telemetry.TelemetryError):
            store3.lift_paul_veto("yes")  # not an explicit confirmation
        store3.lift_paul_veto(
            "Veto lifted after reviewing the specialist's incident report "
            "(human-confirmed)")
        store3.reenable()
        self.assertTrue(store3.enabled)

        # 8. The public payload (what the Q3 exit gate watches) carries
        #    counts and fixed tokens only. Proven by STRUCTURAL assertions
        #    that are independent of the product's own privacy scanner --
        #    using scan_payload here would certify the product with the
        #    product, so the journey deliberately does not.
        store3.record("tool_opened", tool="jd_decoder", surface="terminal",
                      session_id="qual1")
        store3.record("tool_completed", tool="jd_decoder",
                      surface="terminal", duration_s=9, completed=True,
                      session_id="qual1")
        store3.record("workflow_completed", workflow="jd_decode",
                      surface="terminal", duration_s=9, session_id="qual1")
        store3.record("artifact_shared", kind="score_card",
                      surface="terminal", session_id="qual1")
        store3.record("guide_viewed", guide_id="evidence-writing",
                      surface="web", session_id="qual1")
        proc = self._i12("telemetry", "--public-payload",
                         "--state", str(state))
        payload = json.loads(self.assert_ok(proc, "telemetry public-payload"))

        # Pinned public-analytics schema id (the Q3 exit-gate contract)
        # and a fixed top-level key set: no content fields can hide here.
        self.assertEqual(payload.get("schema"), PUBLIC_ANALYTICS_SCHEMA)
        self.assertEqual(
            set(payload),
            {"schema", "tool_opens", "workflow_completion",
             "qualified_activation", "guide_views"},
            "the public payload has a fixed key set")

        # tool_opens: pinned tool tokens -> integer counts, nothing else.
        opens = payload["tool_opens"]
        self.assertEqual(set(opens), set(i12_telemetry.TOOLS),
                         "tool keys are the pinned tool vocabulary")
        for tool, count in opens.items():
            self.assertIs(type(count), int,
                          f"tool_opens[{tool!r}] must be a count")
            self.assertGreaterEqual(count, 0)
        self.assertEqual(opens["jd_decoder"], 1)

        # workflow_completion: fixed shape, fixed metric token, integers,
        # and a rate that is a number (or None only if nothing opened).
        wc = payload["workflow_completion"]
        self.assertEqual(set(wc),
                         {"metric", "opened", "completed", "rate"})
        self.assertEqual(wc["metric"], "workflow_completion_rate")
        self.assertIs(type(wc["opened"]), int)
        self.assertIs(type(wc["completed"]), int)
        self.assertTrue(wc["rate"] is None
                        or isinstance(wc["rate"], (int, float)),
                        "rate must be a number or None, never text")
        self.assertEqual(wc["opened"], 1)
        self.assertEqual(wc["completed"], 1)

        # qualified_activation: fixed shape, fixed metric token, integers.
        qa = payload["qualified_activation"]
        self.assertEqual(set(qa),
                         {"metric", "sessions", "qualified_sessions"})
        self.assertEqual(qa["metric"], "qualified_activation")
        self.assertIs(type(qa["sessions"]), int)
        self.assertIs(type(qa["qualified_sessions"]), int)
        self.assertEqual(qa["qualified_sessions"], 1,
                         "qual1 completed a workflow AND shared an artifact")

        # guide_views: grammar-bound guide ids -> integer counts. The ids
        # name real education guides (cross-checked against the repo's
        # guide files), never free text.
        known_guides = {p.stem
                        for p in (REPO / "docs" / "i12" / "education")
                        .glob("*.md")}
        guides = payload["guide_views"]
        self.assertGreater(len(guides), 0,
                           "the recorded guide_view must appear")
        for guide_id, views in guides.items():
            self.assertTrue(
                _TOKEN_GRAMMAR.match(guide_id),
                f"guide id {guide_id!r} must be a short token, never "
                "free text")
            self.assertIn(guide_id, known_guides,
                          f"guide id {guide_id!r} must name a real guide")
            self.assertIs(type(views), int)
        self.assertEqual(guides["evidence-writing"], 1)


if __name__ == "__main__":
    unittest.main()

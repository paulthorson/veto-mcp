"""Automated UAT acceptance journey: Initiative 07 (Mentor matching & warm paths).

Acceptance contract (plain-English summary for Paul's report):
"A job seeker finds a mentor, and an introduction happens only with
explicit consent from both sides."

The journey is exercised against REAL surfaces only:
- the real ``cli.py mentors`` subcommands (in-process ``cli.main`` with the
  same store-redirection seams the shipped E2E suite uses),
- the real i07 modules (consent handshake, session kit, warm-path planner,
  safety) with every state file redirected to a per-test temp dir.

Paul cleared three Rule 1 vetos on 2026-09-14 (WS2 safety fail-open, WS4
silent-empty, WS1 pre-consent PII leaks) as human veto-clearances; these
tests do NOT re-challenge them but assert the hardened behaviors hold:
no PII revealed before mutual two-sided consent, goalless requests are
not consent-bearing, and corrupt stores fail closed.

Hermetic: no network, no repo-tree writes, no real user data. All
fixtures are synthetic and labeled SYNTHETIC.

Acceptance-criteria trace: the repo has roadmap epics but NO per-story
acceptance criteria, so assertions trace to the epic text, the Proof of
value ("A match cannot become an introduction without explicit consent
from both people, and either person can withdraw"), and the Q2 exit gate
("Mentor introductions have two-sided consent, revocation, and abuse
controls"). Each test's acceptance source is named in EPIC_MAP.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cli  # noqa: E402
import mentors  # noqa: E402
import network_crm  # noqa: E402
from initiatives.i07 import consent as consent  # noqa: E402
from initiatives.i07 import safety as safety  # noqa: E402
from initiatives.i07 import session_kit as kit  # noqa: E402
from initiatives.i07 import warm_path as warm  # noqa: E402

from tests.uat.harness import JourneyCase  # noqa: E402


#: The shipped i07 CLI identifies the local user as "me" everywhere, so the
#: journey uses the same identity it would in real use.
MENTEE_ID = "me"
MENTEE_LABEL = "SYNTHETIC UAT Mentee"

PII_NEEDLES = (
    "linkedin.com",
    "@example.com",
    "555-010-2030",
    "5550102030",
)


def _synthetic_mentor_profile(name: str, slug: str, **overrides):
    profile = {
        "name": name,
        "industry": "Technology",
        "role": "Staff Engineer",
        "seniority": "ic5+",
        "linkedin_url": f"https://www.linkedin.com/in/{slug}",
        "topics": ["interviewing", "leadership"],
        "bio": "SYNTHETIC fixture mentor — not a real person.",
        "availability": "Tue/Thu afternoons",
        "availability_windows": [{"day": "Tue", "start": "14:00", "end": "17:00"}],
        "boundaries": {
            "offers": ["mock interviews", "career advice"],
            "wont": ["job referrals", "evening calls"],
            "note": "Weekday afternoons only.",
        },
        "preferred_contact": "hidden",
        "max_mentees": 2,
    }
    profile.update(overrides)
    return profile


class TestI07Journey(JourneyCase):
    """Initiative 07 UAT journey: mentor matching with two-sided consent."""

    EPIC_MAP = {
        "test_e1_mentor_profile_opt_in": (
            "E1",
            "Mentor profile",
            "Roadmap i07 E1 epic text",
        ),
        "test_e2_match_questionnaire_goal": (
            "E2",
            "Match questionnaire",
            "Roadmap i07 E2 epic text",
        ),
        "test_e3_two_sided_consent": (
            "E3",
            "Two-sided consent",
            "Roadmap i07 E3 epic text + i07 Proof of value",
        ),
        "test_e4_session_kit": (
            "E4",
            "Session kit",
            "Roadmap i07 E4 epic text",
        ),
        "test_e5_warm_path_drafts_never_send": (
            "E5",
            "Warm-path planner",
            "Roadmap i07 E5 epic text",
        ),
        "test_e6_safety_controls": (
            "E6",
            "Safety controls",
            "Q2 exit gate (two-sided consent, revocation, abuse controls)",
        ),
    }

    # -- journey setup ----------------------------------------------------
    def setUp(self):
        super().setUp()
        t = self.workdir
        for module, attr, name in [
            (mentors, "MENTORS_FILE", "mentors.json"),
            (consent, "HANDSHAKES_FILE", "handshakes.json"),
            (consent, "AUDIT_FILE", "consent_audit.jsonl"),
            (safety, "SAFETY_FILE", "safety.json"),
            (safety, "REPORTS_FILE", "reports.jsonl"),
            (kit, "SESSIONS_FILE", "kit_sessions.json"),
            (warm, "DRAFT_OUTBOX", "warm_drafts.jsonl"),
            (network_crm, "NETWORK_FILE", "network.json"),
        ]:
            p = mock.patch.object(module, attr, t / name)
            p.start()
            self.addCleanup(p.stop)
        safety.reset_rate_limits()

    # -- helpers -----------------------------------------------------------
    def cli_json(self, *argv: str) -> dict:
        """Run the real ``cli.py mentors`` command; return parsed JSON."""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli.main(list(argv))
        self.assertEqual(rc, 0, f"cli exited rc={rc}\n{buf.getvalue()}")
        return json.loads(buf.getvalue())

    def opt_in_mentor(self, name: str, slug: str, **overrides) -> str:
        result = self.cli_json(
            "mentors", "opt-in",
            "--profile", json.dumps(_synthetic_mentor_profile(name, slug, **overrides)),
            "--json",
        )
        self.assertTrue(result["ok"], result)
        return result["card"]["id"]

    def match(self, **flags) -> dict:
        argv = [
            "mentors", "match",
            "--industry", flags.get("industry", "technology"),
            "--target-role", flags.get("target_role", "staff engineer"),
            "--topics", flags.get("topics", "interviewing"),
            "--json",
        ]
        if "goal" in flags:
            argv.insert(-1, "--goal")
            argv.insert(-1, flags["goal"])
        return self.cli_json(*argv)

    def assert_no_pii(self, obj, where: str) -> None:
        blob = json.dumps(obj, default=str)
        for needle in PII_NEEDLES:
            self.assertNotIn(needle, blob,
                             f"PII leaked in {where}: {needle}")

    def request_introduction(self, mentor_id: str, goal: str) -> dict:
        return consent.request_introduction(
            mentor_id, MENTEE_ID, MENTEE_LABEL,
            goal=goal,
            context="SYNTHETIC fixture context.",
            urgency="this_month",
            expected_outcome="A mock system-design round with feedback.",
            synthetic=True,
        )

    def request_and_mutual(self, mentor_id: str,
                           goal: str = "Prepare for staff interviews.") -> str:
        req = self.request_introduction(mentor_id, goal)
        self.assertTrue(req["ok"], req)
        hs_id = req["handshake"]["id"]
        resp = consent.mentor_respond(hs_id, "approve",
                                      channel="linkedin_dm",
                                      note="SYNTHETIC approval.")
        self.assertTrue(resp["ok"], resp)
        self.assertEqual(resp["handshake"]["state"], "mutual")
        return hs_id

    # -- E1 ----------------------------------------------------------------
    def test_e1_mentor_profile_opt_in(self):
        """A mentor can publish an opt-in profile with topics, industries,
        seniority, availability, boundaries, and a preferred contact path —
        and opt back out again."""
        mentor_id = self.opt_in_mentor("SYNTHETIC Maya R.",
                                       "synthetic-maya-r-uat")

        # The mentor's own card shows everything E1 promises.
        card = self.cli_json("mentors", "card", "--json")
        self.assertTrue(card["ok"], card)
        mine = card["card"]
        self.assertEqual(mine["name"], "SYNTHETIC Maya R.")
        self.assertEqual(mine["industry"], "Technology")
        self.assertEqual(mine["seniority"], "ic5+")
        self.assertEqual(mine["topics"], ["interviewing", "leadership"])
        self.assertEqual(mine["availability"], "Tue/Thu afternoons")
        self.assertEqual(mine["boundaries"]["offers"],
                         ["mock interviews", "career advice"])
        self.assertEqual(mine["boundaries"]["wont"],
                         ["job referrals", "evening calls"])
        self.assertEqual(mine["preferred_contact"], "hidden")

        # A match sees the profile fields but no contact detail.
        matches = self.match(goal="Prepare for staff interviews.")
        self.assertTrue(matches["ok"], matches)
        maya = next(m for m in matches["matches"]
                    if m["mentor_id"] == mentor_id)
        for field in ("industry", "seniority", "topics", "availability"):
            self.assertIn(field, maya)
        self.assert_no_pii(matches, "E1 match results")

        # Opt-out removes the mentor from discovery.
        out = self.cli_json("mentors", "opt-out", "--mentor-id",
                            mentor_id, "--json")
        self.assertTrue(out["ok"], out)
        after = self.match(goal="Prepare for staff interviews.")
        self.assertTrue(after["ok"], after)
        self.assertNotIn(mentor_id,
                         [m["mentor_id"] for m in after["matches"]])

    # -- E2 ----------------------------------------------------------------
    def test_e2_match_questionnaire_goal(self):
        """Matching returns ranked mentors without revealing contact details,
        and an introduction request without a stated goal is not a
        consent-bearing act — it is rejected."""
        mentor_id = self.opt_in_mentor("SYNTHETIC Maya R.",
                                       "synthetic-maya-r-uat")

        matches = self.match(goal="Prepare for staff interviews.")
        self.assertTrue(matches["ok"], matches)
        self.assertGreaterEqual(len(matches["matches"]), 1)
        self.assert_no_pii(matches, "E2 match results")
        first = matches["matches"][0]
        self.assertNotIn("linkedin_url", first)

        # The questionnaire answers shape the ranking: reasons cite the
        # topics. A community-directory card with no topical overlap
        # ranks below the topical mentor — the ranking is real.
        mentors.mentor_opt_in(
            _synthetic_mentor_profile(
                "SYNTHETIC Ned N.", "synthetic-ned-n-uat",
                topics=["networking"]),
            own=False,
        )
        ranked = self.match(goal="Prepare for staff interviews.")
        self.assertTrue(ranked["ok"], ranked)
        self.assertGreaterEqual(len(ranked["matches"]), 2)
        self.assertIn("interviewing",
                      json.dumps(ranked["matches"][0]["reasons"], default=str),
                      "topical mentor should rank first")
        self.assertEqual(ranked["matches"][0]["name"], "SYNTHETIC Maya R.")

        # A request WITHOUT a goal is not consent: rejected, nothing created.
        bad = self.request_introduction(mentor_id, goal="")
        self.assertFalse(bad["ok"])
        self.assertEqual(consent.list_handshakes(actor=MENTEE_ID), [])

        # A request WITH a goal records the mentee's consent as a handshake
        # in awaiting_mentor — still sealed from contact detail.
        req = self.request_introduction(mentor_id,
                                        goal="Prepare for staff interviews.")
        self.assertTrue(req["ok"], req)
        hs_id = req["handshake"]["id"]
        self.assertTrue(hs_id.startswith("SYNTHETIC-"))
        self.assertEqual(req["handshake"]["state"], "awaiting_mentor")
        early = consent.reveal_contact(hs_id, MENTEE_ID)
        self.assertFalse(early["ok"])

    # -- E3 ----------------------------------------------------------------
    def test_e3_two_sided_consent(self):
        """No contact detail is revealed until BOTH sides approve — the
        mentor's profile and contact stay private with only one side's
        consent, and either side can withdraw."""
        mentor_id = self.opt_in_mentor("SYNTHETIC Maya R.",
                                       "synthetic-maya-r-uat")

        # One-sided: the mentee asked, the mentor has not approved. Nothing
        # is revealed to anyone.
        req = self.request_introduction(mentor_id,
                                        goal="Prepare for staff interviews.")
        self.assertTrue(req["ok"], req)
        hs_id = req["handshake"]["id"]
        for actor in (MENTEE_ID, mentor_id):
            denied = consent.reveal_contact(hs_id, actor)
            self.assertFalse(denied["ok"], f"reveal leaked to {actor}")

        # The mentor's approval is a recorded explicit act, not identity
        # proof: the consent model is two recorded acts (mentee request +
        # mentor approval), and the approval call must name its channel.
        nochan = consent.mentor_respond(hs_id, "approve", channel="")
        self.assertFalse(nochan["ok"])
        still_sealed = consent.reveal_contact(hs_id, MENTEE_ID)
        self.assertFalse(still_sealed["ok"])

        # Second consent arrives: BOTH sides have now approved.
        resp = consent.mentor_respond(hs_id, "approve",
                                      channel="linkedin_dm",
                                      note="SYNTHETIC approval.")
        self.assertTrue(resp["ok"], resp)
        self.assertEqual(resp["handshake"]["state"], "mutual")

        # Only NOW is contact revealed — to the handshake parties only,
        # each side seeing the other's contact path.
        revealed = consent.reveal_contact(hs_id, MENTEE_ID)
        self.assertTrue(revealed["ok"], revealed)
        self.assertIn("linkedin.com",
                      json.dumps(revealed["mentor_contact"], default=str))
        mentor_view = consent.reveal_contact(hs_id, mentor_id)
        self.assertTrue(mentor_view["ok"], mentor_view)
        self.assertIn("mentee_contact", mentor_view)
        stranger = consent.reveal_contact(hs_id, "someone-else")
        self.assertFalse(stranger["ok"])

        # Either person can withdraw: after withdrawal the reveal is gone
        # again, even though both sides once consented.
        w = consent.withdraw(hs_id, MENTEE_ID, reason="no longer needed")
        self.assertTrue(w["ok"], w)
        gone = consent.reveal_contact(hs_id, MENTEE_ID)
        self.assertFalse(gone["ok"])

    # -- E4 ----------------------------------------------------------------
    def test_e4_session_kit(self):
        """Once both sides consent, a session kit is produced: agenda,
        context packet, question builder, notes, and a follow-up plan."""
        mentor_id = self.opt_in_mentor("SYNTHETIC Maya R.",
                                       "synthetic-maya-r-uat")
        hs_id = self.request_and_mutual(mentor_id)

        # The real CLI agenda for a matched mentor with a stated goal.
        agenda = self.cli_json("mentors", "agenda",
                               "--mentor-id", mentor_id,
                               "--mentee-goal", "Prepare for staff interviews.",
                               "--json")
        self.assertTrue(agenda["ok"], agenda)
        self.assertIn("Prepare for staff interviews.", agenda["markdown"])
        self.assertIn("SYNTHETIC Maya R.", agenda["markdown"])

        # The module-level session kit for the mutual handshake.
        built = kit.build_agenda(hs_id, MENTEE_ID)
        self.assertTrue(built["ok"], built)
        self.assertTrue(built["agenda"])

        packet = kit.context_packet(hs_id, MENTEE_ID)
        self.assertTrue(packet["ok"], packet)
        # The packet exists only because both sides consented: it carries
        # the consent receipt, and contact is present only post-mutuality.
        self.assertIn("consent_receipt", packet["packet"])
        receipt = packet["packet"]["consent_receipt"]
        self.assertIn("mentee_consented_at", receipt)
        self.assertIn("mentor_consented_at", receipt)

        questions = kit.question_builder(["interviewing", "leadership"],
                                         goal="staff interviews")
        self.assertTrue(questions["ok"], questions)
        self.assertTrue(questions["questions"])

        note = kit.add_note(hs_id, MENTEE_ID,
                            "SYNTHETIC note: mock round went well.")
        self.assertTrue(note["ok"], note)
        notes = kit.get_notes(hs_id, MENTEE_ID)
        self.assertTrue(notes["ok"], notes)
        self.assertTrue(notes["notes"])

        followup = kit.followup_plan(hs_id, MENTEE_ID)
        self.assertTrue(followup["ok"], followup)

        # The kit requires mutual consent: before approval there is no kit.
        req2_id = self.opt_in_mentor("SYNTHETIC Sam Q.",
                                     "synthetic-sam-q-uat")
        pending = self.request_introduction(
            req2_id, goal="Prepare for staff interviews.")
        self.assertTrue(pending["ok"], pending)
        prem = kit.build_agenda(pending["handshake"]["id"], MENTEE_ID)
        self.assertFalse(prem["ok"])

        # Topic prep from the CLI names the concrete practice for the
        # topic — a recommendation, never a requirement or a gate.
        prep = self.cli_json("mentors", "prep", "--topic", "interviewing",
                             "--json")
        self.assertTrue(prep["ok"], prep)
        self.assertEqual(prep["topic"], "interviewing")
        self.assertIn("star_storytelling", prep["prep"],
                      "prep must name the concrete practice for the topic")
        self.assertIn("not a requirement", prep["note"],
                      "prep must stay a recommendation, never a gate")
        bad_topic = self.cli_json("mentors", "prep", "--topic", "nope",
                                  "--json")
        self.assertFalse(bad_topic["ok"])

    # -- E5 ----------------------------------------------------------------
    def test_e5_warm_path_drafts_never_send(self):
        """The warm-path planner finds the seeker's own connections and
        drafts outreach — but nothing is ever sent on the seeker's behalf."""
        network_crm.add_contact(
            name="SYNTHETIC Dana K.",
            company="Initech",
            role="VP Engineering",
            industry="Technology",
            linkedin_url="https://www.linkedin.com/in/synthetic-dana-k-uat",
            notes="SYNTHETIC fixture contact — not a real person.")

        plan = warm.plan_warm_path("Initech", synthetic=True)
        self.assertTrue(plan["ok"], plan)
        self.assertTrue(plan["plans"])
        first = plan["plans"][0]
        self.assertIn("draft", first)
        draft_text = json.dumps(first["draft"], default=str)
        self.assertIn("Initech", draft_text)
        self.assertIn("honesty_checklist", plan)

        # The draft sits in the outbox for human review. Nothing sends it:
        # the planner only ever records drafts, and there is no send path —
        # the outbox records are review artifacts.
        drafts = warm.list_drafts()
        self.assertTrue(drafts)
        outbox = (self.workdir / "warm_drafts.jsonl").read_text(
            encoding="utf-8")
        self.assertIn("Initech", outbox)
        self.assertNotIn("sent", outbox.lower())
        self.assertNotIn("send", outbox.lower())

        # The mentors CLI draft is explicitly labeled a draft, never a send.
        mentor_id = self.opt_in_mentor("SYNTHETIC Public Pat",
                                       "synthetic-public-pat-uat",
                                       preferred_contact="linkedin_public")
        d = self.cli_json("mentors", "draft", "--mentor-id", mentor_id,
                          "--mentee-name", "SYNTHETIC UAT Mentee",
                          "--mentee-goal", "Prepare for staff interviews.",
                          "--json")
        self.assertTrue(d["ok"], d)
        self.assertEqual(d["status"], "DRAFT — not sent")
        self.assertTrue(len(d["note"]) <= 300)

        # Recording outreach only logs it — it does not contact the mentor.
        rec = self.cli_json("mentors", "record-outreach", "--mentor-id",
                            mentor_id, "--json")
        self.assertTrue(rec["ok"], rec)
        self.assertIn("remaining_capacity", rec)

    # -- E6 ----------------------------------------------------------------
    def test_e6_safety_controls(self):
        """Block, report, rate limits, and deletion protect both sides; a
        corrupt handshake store fails closed instead of failing open."""
        mentor_id = self.opt_in_mentor("SYNTHETIC Maya R.",
                                       "synthetic-maya-r-uat")

        # Blocking removes the mentor from discovery AND blocks handshakes.
        b = safety.block_actor(MENTEE_ID, mentor_id, reason="SYNTHETIC block")
        self.assertTrue(b["ok"], b)
        matches = self.match(goal="Prepare for staff interviews.")
        self.assertTrue(matches["ok"], matches)
        self.assertNotIn(mentor_id,
                         [m["mentor_id"] for m in matches["matches"]])
        blocked_req = self.request_introduction(
            mentor_id, goal="Prepare for staff interviews.")
        self.assertFalse(blocked_req["ok"])
        u = safety.unblock_actor(MENTEE_ID, mentor_id)
        self.assertTrue(u["ok"], u)

        # Abuse reports are recorded and listable against the reported
        # mentor. (Quarantine thresholds on repeated reports are a product
        # behavior this journey does not exercise; it is not asserted here.)
        rep = safety.report(MENTEE_ID, mentor_id, "spam",
                            detail="SYNTHETIC report fixture.")
        self.assertTrue(rep["ok"], rep)
        reports = safety.list_reports(reported_id=mentor_id)
        self.assertTrue(reports)

        # Rate limits: the same actor exhausts a 1-token bucket for one action.
        self.assertTrue(safety.check_rate_limit(
            MENTEE_ID, "e6_probe", limits={"e6_probe": (1, 0)}))
        self.assertFalse(safety.check_rate_limit(
            MENTEE_ID, "e6_probe", limits={"e6_probe": (1, 0)}))

        # Corrupt store fails closed: nothing proceeds, nothing is fabricated.
        (self.workdir / "handshakes.json").write_text("{not valid json",
                                                      encoding="utf-8")
        corrupt = self.request_introduction(
            mentor_id, goal="Prepare for staff interviews.")
        self.assertFalse(corrupt["ok"])
        self.assertIn("corrupt", json.dumps(corrupt).lower())

        # Deletion erases the mentee's handshake footprint on request.
        (self.workdir / "handshakes.json").unlink()
        hs_id = self.request_and_mutual(mentor_id)
        d = safety.delete_mentee_data(MENTEE_ID, requested_by=MENTEE_ID)
        self.assertTrue(d["ok"], d)
        self.assertEqual(consent.list_handshakes(actor=MENTEE_ID), [])
        self.assertNotIn(hs_id, [h["id"] for h in
                                 consent.list_handshakes(actor=mentor_id)])

        # Mentor deletion erases their card and sessions on request.
        dm = safety.delete_mentor_data(mentor_id, requested_by=mentor_id)
        self.assertTrue(dm["ok"], dm)
        after = self.match(goal="Prepare for staff interviews.")
        self.assertTrue(after["ok"], after)
        self.assertNotIn(mentor_id,
                         [m["mentor_id"] for m in after["matches"]])


if __name__ == "__main__":
    unittest.main()

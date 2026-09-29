"""End-to-end retro-validation for Initiative 07 (Mentor matching).

Exercised against REAL surfaces:
  - the real mentor directory (``mentors.py``), matchmaking engine, and the
    i07 consent handshake (``initiatives/i07/consent.py``) — every state
    file redirected to a tmp dir per test,
  - the session kit, warm-path planner, and safety modules wired across
    the same handshake records a real user journey would produce,
  - the append-only, hash-chained consent audit log on real disk.

Consent gates under test (operator cleared three Rule 1 vetos on 2026-09-14 —
WS2 safety fail-open, WS4 silent-empty, WS1 pre-consent PII leaks — as
human veto-clearances; these tests do NOT re-challenge them but verify
the hardened behaviors hold):
  - no PII is revealed before mutual two-sided consent,
  - a request without a stated goal is not a consent-bearing act,
  - the mentor's reply is never fabricated: it needs an explicit record
    with channel provenance,
  - safety paths fail closed (corrupt store refuses to operate).

Hermetic: no network, no real user data, deterministic. Synthetic
handshakes follow the codebase's SYNTHETIC- labeling convention.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mentors  # noqa: E402
import network_crm  # noqa: E402
from initiatives.i07 import consent as _consent  # noqa: E402
from initiatives.i07 import safety as _safety  # noqa: E402
from initiatives.i07 import session_kit as _kit  # noqa: E402
from initiatives.i07 import warm_path as _warm  # noqa: E402


def _mentor_profile(name, linkedin, bio="", preferred_contact="hidden",
                    topics=("interviewing", "leadership")):
    return {
        "name": name,
        "industry": "Technology",
        "role": "Staff Engineer",
        "seniority": "ic5+",
        "linkedin_url": linkedin,
        "topics": list(topics),
        "bio": bio,
        "availability": "Tue/Thu afternoons",
        "preferred_contact": preferred_contact,
        "max_mentees": 2,
    }


#: The shipped i07 CLI identifies the local user as "me" everywhere
#: (block_actor("me", ...), request_introduction(mentor_id, "me", ...),
#: discovery_exclusions("me")). The E2E journey must use the same
#: identity or it exercises a flow the product never runs.
MENTEE = {"mentee_id": "me", "mentee_label": "E.E."}

MATCH_ANSWERS = {
    "industry": "technology",
    "target_role": "staff engineer",
    "topics_ranked": ["interviewing", "leadership"],
    "goal": "Prepare for staff-level system design interviews.",
    "urgency": "this_month",
    "expected_outcome": "A mock system-design round with feedback.",
}


class E2EBase(unittest.TestCase):
    """Redirect every i07 state file into a tmp dir."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        t = Path(self._tmp.name)
        for module, attr, name in [
            (mentors, "MENTORS_FILE", "mentors.json"),
            (_consent, "HANDSHAKES_FILE", "handshakes.json"),
            (_consent, "AUDIT_FILE", "consent_audit.jsonl"),
            (_safety, "SAFETY_FILE", "safety.json"),
            (_safety, "REPORTS_FILE", "reports.jsonl"),
            (_kit, "SESSIONS_FILE", "kit_sessions.json"),
            (_warm, "DRAFT_OUTBOX", "warm_drafts.jsonl"),
            (network_crm, "NETWORK_FILE", "network.json"),
        ]:
            p = mock.patch.object(module, attr, t / name)
            p.start()
            self.addCleanup(p.stop)
        self.tmp = t

    # -- journey helpers -------------------------------------------------------
    def seed_mentors(self):
        """Two opted-in mentors; one hides contact, one sneaks contact info
        into the bio to prove the pre-consent scrubber catches it."""
        r1 = mentors.mentor_opt_in(
            _mentor_profile(
                "Maya R.",
                "https://www.linkedin.com/in/maya-r-example",
                bio="Staff engineer; happy to help with system design."),
            own=False)
        self.assertTrue(r1["ok"])
        r2 = mentors.mentor_opt_in(
            _mentor_profile(
                "Sneaky Sam",
                "https://www.linkedin.com/in/sneaky-sam-example",
                bio="DM me at sneaky.sam@example.com or 555-010-2030!"),
            own=False)
        self.assertTrue(r2["ok"])
        return r1["card"]["id"], r2["card"]["id"]

    def assert_no_pii(self, obj, where):
        blob = json.dumps(obj, default=str)
        for needle in ("linkedin.com", "@example.com", "555-010-2030",
                       "5550102030"):
            self.assertNotIn(needle, blob,
                             f"PII leaked in {where}: {needle}")

    def request_and_mutual(self, mentor_id, mentee=None):
        mentee = mentee or MENTEE
        req = _consent.request_introduction(
            mentor_id, mentee["mentee_id"], mentee["mentee_label"],
            goal="Prepare for staff-level system design interviews.",
            context="Staff promo loop in Q1.", urgency="this_month",
            expected_outcome="A mock system-design round with feedback.",
            synthetic=True)
        self.assertTrue(req["ok"], req)
        hs_id = req["handshake"]["id"]
        resp = _consent.mentor_respond(hs_id, "approve",
                                       channel="linkedin_dm", note="Happy to help.")
        self.assertTrue(resp["ok"], resp)
        self.assertEqual(resp["handshake"]["state"], "mutual")
        return hs_id


class TestHandshakeJourneyE2E(E2EBase):
    """The full mentor-matching journey: opt-in -> match -> consent ->
    mutual -> reveal -> session kit -> feedback."""

    def test_full_journey(self):
        maya_id, sam_id = self.seed_mentors()

        # 1. Match with consent previews: contact sealed by default.
        result = mentors.matchmake(MATCH_ANSWERS, consent_preview=True)
        self.assertTrue(result["ok"])
        self.assertGreaterEqual(len(result["matches"]), 1)
        for m in result["matches"]:
            preview = m if "linkedin_url" not in m else None
            self.assert_no_pii(m, "consent preview")

        # The sneaky bio is scrubbed even though it looked like plain text.
        sam_match = next(m for m in result["matches"]
                         if m["mentor_id"] == sam_id)
        self.assertNotIn("sneaky.sam", json.dumps(sam_match, default=str))
        self.assertNotIn("555", json.dumps(sam_match, default=str))

        # A redacted preview of the raw card also carries no contact.
        card = mentors._load_directory()[maya_id]
        preview = _consent.redacted_preview(card)
        self.assert_no_pii(preview, "redacted_preview")

        # 2. A request WITHOUT a goal is not consent: rejected.
        bad = _consent.request_introduction(
            maya_id, MENTEE["mentee_id"], MENTEE["mentee_label"], goal="",
            synthetic=True)
        self.assertFalse(bad["ok"])

        # 3. A real request records the mentee's consent (audit on disk).
        req = _consent.request_introduction(
            maya_id, MENTEE["mentee_id"], MENTEE["mentee_label"],
            goal="Prepare for staff-level system design interviews.",
            context="Staff promo loop in Q1.", urgency="this_month",
            expected_outcome="A mock system-design round with feedback.",
            synthetic=True)
        self.assertTrue(req["ok"], req)
        hs_id = req["handshake"]["id"]
        self.assertEqual(req["handshake"]["state"], "awaiting_mentor")
        self.assertTrue(hs_id.startswith("SYNTHETIC-"))

        # 4. Reveal BEFORE mutual consent is refused: no PII leaks.
        early = _consent.reveal_contact(hs_id, MENTEE["mentee_id"])
        self.assertFalse(early["ok"])

        # 5. The mentor's reply needs channel provenance — never fabricated.
        nochan = _consent.mentor_respond(hs_id, "approve", channel="")
        self.assertFalse(nochan["ok"])
        resp = _consent.mentor_respond(hs_id, "approve",
                                       channel="linkedin_dm",
                                       note="Happy to help.")
        self.assertTrue(resp["ok"], resp)
        self.assertEqual(resp["handshake"]["state"], "mutual")

        # 6. Only NOW is contact revealed — to the handshake parties.
        revealed = _consent.reveal_contact(hs_id, MENTEE["mentee_id"])
        self.assertTrue(revealed["ok"], revealed)
        self.assertIn("linkedin.com",
                      json.dumps(revealed["mentor_contact"], default=str))

        # 7. Session kit outputs are generated for the mutual handshake.
        agenda = _kit.build_agenda(hs_id, MENTEE["mentee_id"])
        self.assertTrue(agenda["ok"], agenda)
        self.assertTrue(agenda["agenda"])

        packet = _kit.context_packet(hs_id, MENTEE["mentee_id"])
        self.assertTrue(packet["ok"], packet)

        questions = _kit.question_builder(["interviewing", "leadership"],
                                          goal="system design prep")
        self.assertTrue(questions["ok"], questions)
        self.assertTrue(questions["questions"])

        followup = _kit.followup_plan(hs_id, MENTEE["mentee_id"])
        self.assertTrue(followup["ok"], followup)

        # 8. Feedback feeds the mentor card's two-sided rating history.
        fb = _kit.session_feedback(hs_id, MENTEE["mentee_id"], 5,
                                   note="Great mock round.")
        self.assertTrue(fb["ok"], fb)
        card_after = mentors._load_directory()[maya_id]
        ratings = card_after.get("ratings") or {}
        self.assertTrue(ratings)

        # 9. The audit trail is a real, verifiable hash chain on disk.
        audit_lines = (self.tmp / "consent_audit.jsonl").read_text(
            encoding="utf-8").strip().splitlines()
        self.assertGreaterEqual(len(audit_lines), 3)
        check = _consent.verify_audit()
        self.assertTrue(check["ok"], check)

        # 10. Handshake record is queryable by the mentee.
        mine = _consent.list_handshakes(actor=MENTEE["mentee_id"])
        self.assertIn(hs_id, [h["id"] for h in mine])

    def test_withdraw_blocks_later_reveal(self):
        maya_id, _ = self.seed_mentors()
        hs_id = self.request_and_mutual(maya_id)
        w = _consent.withdraw(hs_id, MENTEE["mentee_id"], reason="no longer needed")
        self.assertTrue(w["ok"], w)
        # A withdrawn handshake reveals nothing, even after a mutual.
        gone = _consent.reveal_contact(hs_id, MENTEE["mentee_id"])
        self.assertFalse(gone["ok"])

    def test_decline_arms_cooldown(self):
        maya_id, _ = self.seed_mentors()
        req = _consent.request_introduction(
            maya_id, MENTEE["mentee_id"], MENTEE["mentee_label"],
            goal="Prepare for interviews.", synthetic=True)
        hs_id = req["handshake"]["id"]
        resp = _consent.mentor_respond(hs_id, "decline", channel="email")
        self.assertTrue(resp["ok"])
        again = _consent.request_introduction(
            maya_id, MENTEE["mentee_id"], MENTEE["mentee_label"],
            goal="Prepare for interviews.", synthetic=True)
        self.assertFalse(again["ok"])
        self.assertIn("cooldown", again["error"].lower())

    def test_kit_requires_mutual(self):
        maya_id, _ = self.seed_mentors()
        req = _consent.request_introduction(
            maya_id, MENTEE["mentee_id"], MENTEE["mentee_label"],
            goal="Prepare for interviews.", synthetic=True)
        hs_id = req["handshake"]["id"]
        agenda = _kit.build_agenda(hs_id, MENTEE["mentee_id"])
        self.assertFalse(agenda["ok"])


class TestSafetyGatesE2E(E2EBase):
    """Safety choke points: blocks, discovery exclusion, fail-closed stores."""

    def test_block_excludes_from_discovery_and_handshakes(self):
        maya_id, _ = self.seed_mentors()
        # Sanity: Maya is discoverable before the block.
        before = mentors.matchmake(MATCH_ANSWERS, consent_preview=True)
        self.assertIn(maya_id, [m["mentor_id"] for m in before["matches"]])

        b = _safety.block_actor(MENTEE["mentee_id"], maya_id,
                                reason="test block")
        self.assertTrue(b["ok"], b)
        self.assertTrue(_safety.is_blocked(MENTEE["mentee_id"], maya_id))

        after = mentors.matchmake(MATCH_ANSWERS, consent_preview=True)
        self.assertNotIn(maya_id, [m["mentor_id"] for m in after["matches"]])

        req = _consent.request_introduction(
            maya_id, MENTEE["mentee_id"], MENTEE["mentee_label"],
            goal="Prepare for interviews.", synthetic=True)
        self.assertFalse(req["ok"])

        u = _safety.unblock_actor(MENTEE["mentee_id"], maya_id)
        self.assertTrue(u["ok"])
        req2 = _consent.request_introduction(
            maya_id, MENTEE["mentee_id"], MENTEE["mentee_label"],
            goal="Prepare for interviews.", synthetic=True)
        self.assertTrue(req2["ok"], req2)

    def test_corrupt_handshake_store_fails_closed(self):
        maya_id, _ = self.seed_mentors()
        (self.tmp / "handshakes.json").write_text("{not valid json",
                                                  encoding="utf-8")
        req = _consent.request_introduction(
            maya_id, MENTEE["mentee_id"], MENTEE["mentee_label"],
            goal="Prepare for interviews.", synthetic=True)
        # The store refuses to operate rather than failing open.
        self.assertFalse(req["ok"])
        self.assertIn("corrupt", json.dumps(req).lower())

    def test_tampered_audit_chain_detected(self):
        maya_id, _ = self.seed_mentors()
        hs_id = self.request_and_mutual(maya_id)
        self.assertTrue(_consent.verify_audit()["ok"])
        # Forge an audit line: the hash chain must catch it.
        with open(self.tmp / "consent_audit.jsonl", "a",
                  encoding="utf-8") as fh:
            fh.write(json.dumps({
                "event": "reveal_contact", "handshake_id": hs_id,
                "actor": "attacker", "prev_hash": "forged",
                "hash": "forged",
            }) + "\n")
        check = _consent.verify_audit()
        self.assertFalse(check["ok"])

    def test_delete_me_removes_mentee_footprint(self):
        maya_id, _ = self.seed_mentors()
        hs_id = self.request_and_mutual(maya_id)
        d = _safety.delete_mentee_data(MENTEE["mentee_id"],
                                       requested_by=MENTEE["mentee_id"])
        self.assertTrue(d["ok"], d)
        mine = _consent.list_handshakes(actor=MENTEE["mentee_id"])
        self.assertEqual(mine, [])


class TestWarmPathE2E(E2EBase):
    """Warm-path planner: real CRM contacts -> ranked drafts with evidence."""

    def test_plan_with_crm_contact_produces_draft(self):
        network_crm.add_contact(
            name="Dana K.", company="Initech", role="VP Engineering",
            industry="Technology",
            linkedin_url="https://www.linkedin.com/in/dana-k-example",
            notes="Met at the 2025 systems conference.")
        plan = _warm.plan_warm_path("Initech")
        self.assertTrue(plan["ok"], plan)
        self.assertTrue(plan["plans"])
        first = plan["plans"][0]
        self.assertIn("draft", first)
        # Drafts are built against the contact's ACTUAL recorded company.
        draft_text = json.dumps(first["draft"], default=str)
        self.assertIn("Initech", draft_text)
        self.assertIn("Dana", draft_text)
        self.assertIn("honesty_checklist", plan)
        self.assertTrue(plan["honesty_checklist"])
        self.assertEqual(first["contact_company"].lower(), "initech")
        self.assertIn("works at", first["via"])
        # The draft outbox on disk holds it for human review.
        outbox = (self.tmp / "warm_drafts.jsonl").read_text(encoding="utf-8")
        self.assertIn("Initech", outbox)

    def test_plan_with_empty_network_is_honest(self):
        plan = _warm.plan_warm_path("Nonexistent Corp XYZ")
        self.assertTrue(plan["ok"], plan)
        self.assertEqual(plan["plans"], [])
        self.assertIn("guidance", plan)


class TestPublicContactOptInE2E(E2EBase):
    """Mentors who explicitly opt their LinkedIn URL public keep it visible
    in discovery; everyone else stays sealed until mutual consent."""

    def test_public_opt_in_keeps_url_in_preview(self):
        pub = mentors.mentor_opt_in(
            _mentor_profile(
                "Public Pat",
                "https://www.linkedin.com/in/public-pat-example",
                preferred_contact="linkedin_public"),
            own=False)
        self.assertTrue(pub["ok"])
        pub_id = pub["card"]["id"]
        result = mentors.matchmake(MATCH_ANSWERS, consent_preview=True)
        pat_match = next(m for m in result["matches"]
                         if m["mentor_id"] == pub_id)
        self.assertIn("linkedin.com", pat_match.get("linkedin_url", ""))

    def test_hidden_default_seals_url_until_mutual(self):
        maya_id, _ = self.seed_mentors()
        result = mentors.matchmake(MATCH_ANSWERS, consent_preview=True)
        maya_match = next(m for m in result["matches"]
                          if m["mentor_id"] == maya_id)
        self.assertNotIn("linkedin_url", maya_match)


if __name__ == "__main__":
    unittest.main()

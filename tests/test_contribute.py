"""Unit tests for contribute.py: opt-in training-data contributions.

All session stores and the contributions directory are redirected to a
tmp dir per test. Nothing here touches the network or transmits anything.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import contribute  # noqa: E402

PII_ANSWER = (
    "In 2023 the situation was dire. I'm Jane Alvarez, reach me at "
    "jane.alvarez@example.com or +1 (555) 123-4567. My LinkedIn is "
    "linkedin.com/in/janealvarez and my handle is @jane_builds. "
    "As the Senior Backend Engineer at Initech I led the billing rebuild."
)


def _mock_store() -> dict:
    return {
        "sess_complete": {
            "session_id": "sess_complete",
            "company": "Initech",
            "role": "Senior Backend Engineer",
            "questions": [{"id": "q1", "kind": "behavioral",
                           "question": "Tell me about yourself."}],
            "answers": {"q1": {"answer": PII_ANSWER, "overall": 82}},
            "complete": True,
            "created": "2026-09-01T00:00:00+00:00",
        },
        "sess_incomplete": {
            "session_id": "sess_incomplete",
            "company": "Initech",
            "role": "Backend Engineer",
            "questions": [{"id": "q1", "kind": "behavioral",
                           "question": "Tell me about yourself."}],
            "answers": {},
            "complete": False,
        },
    }


def _soft_store() -> dict:
    return {
        "drill_done": {
            "type": "drill",
            "area": "negotiation",
            "mode": "adversarial",
            "difficulty": "hardball",
            "prompt": "Counter this offer.",
            "history": [{"round": 1, "answer": "I'd like 160k.", "score": 70}],
            "done": True,
            "created_at": "2026-09-02T00:00:00+00:00",
        },
        "drill_open": {
            "type": "drill",
            "area": "star_storytelling",
            "mode": "coach",
            "done": False,
        },
    }


def _ai_store() -> dict:
    return {
        "sessions": {
            "ex_done": {
                "track": "generalist",
                "lesson_id": "prompting-101",
                "submitted": True,
                "score": 0.9,
                "passed": True,
            },
            "ex_open": {
                "track": "generalist",
                "lesson_id": "prompting-101",
                "submitted": False,
            },
        }
    }


class ContributeTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)

        self._mock_file = root / "mock_sessions.json"
        self._soft_file = root / "soft_skill_sessions.json"
        self._ai_file = root / "ai_proficiency.json"
        self._mock_file.write_text(json.dumps(_mock_store()), encoding="utf-8")
        self._soft_file.write_text(json.dumps(_soft_store()), encoding="utf-8")
        self._ai_file.write_text(json.dumps(_ai_store()), encoding="utf-8")

        contrib_dir = root / "contributions"
        patchers = [
            mock.patch.object(
                contribute, "_source_paths",
                return_value={
                    "mock_interview": self._mock_file,
                    "soft_skills": self._soft_file,
                    "ai_proficiency": self._ai_file,
                }),
            mock.patch.object(contribute, "CONTRIB_DIR", contrib_dir),
            mock.patch.object(contribute, "OUTBOX_DIR", contrib_dir / "outbox"),
            mock.patch.object(contribute, "CONSENT_PATH",
                               contrib_dir / "consent.json"),
            mock.patch.object(contribute, "SETTINGS_PATH",
                               contrib_dir / "settings.json"),
            mock.patch.object(contribute, "PREVIEWED_PATH",
                               contrib_dir / "previewed.json"),
        ]
        for p in patchers:
            p.start()
            self.addCleanup(p.stop)

    # -- scrubber ------------------------------------------------------

    def test_scrub_email_url_phone_handle(self):
        text = ("Email jane.alvarez@example.com, site https://example.com/me, "
                "call +1 (555) 123-4567, handle @jane_builds.")
        scrubbed, report = contribute.scrub_text(text)
        self.assertNotIn("jane.alvarez@example.com", scrubbed)
        self.assertNotIn("https://example.com/me", scrubbed)
        self.assertNotIn("555", scrubbed)
        self.assertNotIn("@jane_builds", scrubbed)
        counts = {r["rule"]: r["redactions"] for r in report}
        self.assertEqual(counts["email"], 1)
        self.assertEqual(counts["url"], 1)
        self.assertEqual(counts["phone"], 1)
        self.assertEqual(counts["handle"], 1)

    def test_scrub_name_heuristic_and_company(self):
        scrubbed, report = contribute.scrub_text(
            "I'm Jane Alvarez from Initech, a Senior Backend Engineer.",
            known_companies=("Initech",),
        )
        self.assertIn("[NAME]", scrubbed)
        self.assertNotIn("Jane Alvarez", scrubbed)
        self.assertIn("[COMPANY]", scrubbed)
        self.assertNotIn("Initech", scrubbed)
        # Role titles are kept — useful persona signal, not identifying.
        self.assertIn("Senior Backend Engineer", scrubbed)

    def test_scrub_keeps_short_numbers_and_single_words(self):
        scrubbed, _ = contribute.scrub_text(
            "In 2023 we cut latency 40 percent.")
        self.assertIn("2023", scrubbed)
        self.assertIn("40", scrubbed)

    def test_scrub_rules_report_is_visible(self):
        rules = contribute.scrub_rules_report()
        names = [r["rule"] for r in rules]
        self.assertEqual(names, ["email", "url", "phone", "handle",
                                 "company", "name"])
        for r in rules:
            self.assertTrue(r["description"])

    # -- ratings -------------------------------------------------------

    def test_rate_persona_stores_locally(self):
        result = contribute.rate_persona("sess_complete", 5, "Tough but fair")
        self.assertEqual(result["stars"], 5)
        self.assertEqual(result["note"], "Tough but fair")
        stored = json.loads(self._mock_file.read_text(encoding="utf-8"))
        self.assertEqual(
            stored["sess_complete"]["persona_rating"]["stars"], 5)

    def test_rate_persona_rejects_bad_stars(self):
        for bad in (0, 6, "five"):
            result = contribute.rate_persona("sess_complete", bad)
            self.assertIn("error", result)

    def test_rate_persona_unknown_session(self):
        self.assertIn("error", contribute.rate_persona("nope", 4))

    def test_rate_persona_refuses_incomplete_session(self):
        result = contribute.rate_persona("sess_incomplete", 4)
        self.assertIn("error", result)

    # -- list ----------------------------------------------------------

    def test_list_contributable_only_completed_no_transcripts(self):
        result = contribute.list_contributable()
        ids = {i["session_id"] for i in result["contributable"]}
        self.assertEqual(ids, {"sess_complete", "drill_done", "ex_done"})
        self.assertEqual(result["count"], 3)
        for item in result["contributable"]:
            blob = json.dumps(item)
            self.assertNotIn("jane.alvarez@example.com", blob)
            self.assertNotIn("transcript", blob)
            self.assertIn("persona", item)
            self.assertIn("rating_stars", item)

    # -- preview -------------------------------------------------------

    def test_preview_returns_scrubbed_bundle_and_records_hash(self):
        result = contribute.preview_contribution(["sess_complete"])
        self.assertIn("bundle", result)
        self.assertIn("bundle_hash", result)
        self.assertIn("scrub_rules", result)  # rule set visible to user
        blob = json.dumps(result["bundle"])
        self.assertNotIn("jane.alvarez@example.com", blob)
        self.assertNotIn("Jane Alvarez", blob)
        self.assertNotIn("Initech", blob)
        self.assertIn("[REDACTED]", blob)
        self.assertIn("[NAME]", blob)
        self.assertIn("[COMPANY]", blob)
        previewed = json.loads(
            (Path(self._tmp.name) / "contributions" / "previewed.json")
            .read_text(encoding="utf-8"))
        self.assertIn(result["bundle_hash"], previewed)

    def test_preview_bundle_hash_deterministic(self):
        first = contribute.preview_contribution(["sess_complete"])
        second = contribute.preview_contribution(["sess_complete"])
        # created_at differs, so hashes differ — but same session set means
        # same transcript content after scrubbing.
        t1 = first["bundle"]["sessions"][0]["transcript"]
        t2 = second["bundle"]["sessions"][0]["transcript"]
        self.assertEqual(t1, t2)

    def test_preview_rejects_unknown_and_incomplete(self):
        self.assertIn("error",
                      contribute.preview_contribution(["nope"]))
        self.assertIn("error",
                      contribute.preview_contribution(["sess_incomplete"]))
        self.assertIn("error", contribute.preview_contribution([]))

    def test_preview_dedupes_session_ids(self):
        result = contribute.preview_contribution(
            ["sess_complete", "sess_complete"])
        self.assertEqual(len(result["bundle"]["sessions"]), 1)

    # -- submit --------------------------------------------------------

    def test_submit_requires_confirmed(self):
        contribute.preview_contribution(["sess_complete"])
        result = contribute.submit_contribution(["sess_complete"],
                                                confirmed=False)
        self.assertIn("error", result)

    def test_submit_requires_preview(self):
        result = contribute.submit_contribution(["sess_complete"],
                                                confirmed=True)
        # No preview was recorded in this test -> refused.
        self.assertIn("error", result)

    def test_submit_happy_path_stages_locally(self):
        preview = contribute.preview_contribution(
            ["sess_complete", "drill_done"])
        with mock.patch("builtins.print") as fake_print:
            result = contribute.submit_contribution(
                ["sess_complete", "drill_done"], confirmed=True)
        self.assertTrue(result["staged"])
        self.assertFalse(result["transmitted"])  # never transmits itself
        self.assertEqual(result["bundle_hash"], preview["bundle_hash"])
        outbox = Path(result["outbox"])
        self.assertTrue(outbox.exists())
        staged = json.loads(outbox.read_text(encoding="utf-8"))
        self.assertEqual(staged["schema"], "veto-contribution/1")
        self.assertEqual(len(staged["sessions"]), 2)
        # Consent log is append-only.
        consent = json.loads(
            (Path(self._tmp.name) / "contributions" / "consent.json")
            .read_text(encoding="utf-8"))
        self.assertEqual(len(consent), 1)
        self.assertEqual(consent[0]["bundle_hash"], preview["bundle_hash"])
        self.assertIn("consented_to", consent[0])
        # Next steps printed for manual delivery.
        printed = " ".join(c.args[0] for c in fake_print.call_args_list)
        self.assertIn("gh", printed)

    def test_consent_log_is_append_only(self):
        contribute.preview_contribution(["sess_complete"])
        contribute.submit_contribution(["sess_complete"], confirmed=True)
        contribute.preview_contribution(["drill_done"])
        contribute.submit_contribution(["drill_done"], confirmed=True)
        consent = json.loads(
            (Path(self._tmp.name) / "contributions" / "consent.json")
            .read_text(encoding="utf-8"))
        self.assertEqual(len(consent), 2)

    def test_kill_switch_blocks_submit(self):
        contribute.set_contributions_enabled(False)
        contribute.preview_contribution(["sess_complete"])
        result = contribute.submit_contribution(["sess_complete"],
                                                confirmed=True)
        self.assertIn("error", result)
        self.assertIn("kill-switch", result["error"])
        # Re-enable and submit works.
        contribute.set_contributions_enabled(True)
        ok = contribute.submit_contribution(["sess_complete"],
                                            confirmed=True)
        self.assertTrue(ok.get("staged"))

    def test_preview_still_works_with_kill_switch_off(self):
        contribute.set_contributions_enabled(False)
        result = contribute.preview_contribution(["sess_complete"])
        self.assertIn("bundle", result)

    # -- MCP + CLI wiring ----------------------------------------------

    def test_register_tools(self):
        seen: dict[str, Any] = {}

        class FakeMCP:
            def tool(self):
                def deco(fn):
                    seen[fn.__name__] = fn
                    return fn
                return deco

        contribute.register_tools(FakeMCP())
        for name in ("rate_persona", "list_contributable",
                     "preview_contribution", "submit_contribution",
                     "scrub_rules"):
            self.assertIn(name, seen)
        self.assertEqual(len(seen["scrub_rules"]()["scrub_rules"]), 6)
        listed = seen["list_contributable"]()
        self.assertEqual(listed["count"], 3)

    def test_register_cli(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers()
        mapping = contribute.register_cli(sub)
        self.assertEqual(list(mapping), ["contribute"])

        args = argparse.Namespace(action="list", json=True,
                                  session_id=None, session_ids=None,
                                  stars=None, note="", confirm=False)
        self.assertEqual(mapping["contribute"](args), 0)

        args = argparse.Namespace(action="rules", json=True,
                                  session_id=None, session_ids=None,
                                  stars=None, note="", confirm=False)
        self.assertEqual(mapping["contribute"](args), 0)

        args = argparse.Namespace(action="rate", json=True,
                                  session_id="sess_complete",
                                  session_ids=None, stars=4,
                                  note="good", confirm=False)
        self.assertEqual(mapping["contribute"](args), 0)


if __name__ == "__main__":
    unittest.main()

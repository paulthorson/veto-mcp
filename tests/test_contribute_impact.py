"""Unit tests for the contribution impact loop in contribute.py.

Covers record_impact / impact_log / my_impact plus their MCP and CLI
wiring. The contributions directory is redirected to a tmp dir per
test; nothing touches the network or transmits anything.
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


class ImpactTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        contrib_dir = root / "contributions"

        patchers = [
            mock.patch.object(contribute, "CONTRIB_DIR", contrib_dir),
            mock.patch.object(contribute, "OUTBOX_DIR",
                               contrib_dir / "outbox"),
            mock.patch.object(contribute, "CONSENT_PATH",
                               contrib_dir / "consent.json"),
            mock.patch.object(contribute, "SETTINGS_PATH",
                               contrib_dir / "settings.json"),
            mock.patch.object(contribute, "PREVIEWED_PATH",
                               contrib_dir / "previewed.json"),
            mock.patch.object(contribute, "IMPACT_PATH",
                               contrib_dir / "impact.json"),
        ]
        for p in patchers:
            p.start()
            self.addCleanup(p.stop)

        self.outbox = contrib_dir / "outbox"
        self.impact_path = contrib_dir / "impact.json"

    # -- helpers -------------------------------------------------------

    def _stage_bundle(self, bundle_id: str) -> Path:
        self.outbox.mkdir(parents=True, exist_ok=True)
        path = self.outbox / f"{bundle_id}.json"
        path.write_text(
            json.dumps({"schema": "veto-contribution/1", "sessions": []}),
            encoding="utf-8",
        )
        return path

    # -- record_impact -------------------------------------------------

    def test_record_impact_happy_path(self):
        self._stage_bundle("aaa111")
        result = contribute.record_impact(
            "1.3", "hardball_negotiator",
            "now pushes on equity, not just base", ["aaa111"])
        self.assertTrue(result.get("recorded"))
        self.assertNotIn("warnings", result)
        stored = json.loads(self.impact_path.read_text(encoding="utf-8"))
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]["version"], "1.3")
        self.assertEqual(stored[0]["persona"], "hardball_negotiator")
        self.assertEqual(stored[0]["bundle_ids"], ["aaa111"])
        self.assertIn("recorded_at", stored[0])

    def test_record_impact_validates_required_fields(self):
        self._stage_bundle("aaa111")
        self.assertIn("error", contribute.record_impact(
            "", "p", "change", ["aaa111"]))
        self.assertIn("error", contribute.record_impact(
            "1.0", "", "change", ["aaa111"]))
        self.assertIn("error", contribute.record_impact(
            "1.0", "p", "", ["aaa111"]))
        self.assertIn("error", contribute.record_impact(
            "1.0", "p", "change", []))
        # Nothing recorded on validation failure.
        self.assertFalse(self.impact_path.exists())

    def test_record_impact_accepts_comma_separated_bundle_ids(self):
        self._stage_bundle("aaa111")
        self._stage_bundle("bbb222")
        result = contribute.record_impact(
            "1.3", "p", "change", "aaa111,bbb222")
        self.assertTrue(result.get("recorded"))
        self.assertEqual(result["entry"]["bundle_ids"], ["aaa111", "bbb222"])

    def test_record_impact_warns_on_unknown_bundle_id_but_still_records(self):
        result = contribute.record_impact(
            "1.3", "p", "change", ["nope-not-real"])
        self.assertTrue(result.get("recorded"))
        self.assertIn("warnings", result)
        self.assertTrue(any("nope-not-real" in w for w in result["warnings"]))
        # Append-only: entry is there.
        self.assertEqual(len(contribute.impact_log()["impacts"]), 1)

    def test_record_impact_is_append_only(self):
        self._stage_bundle("aaa111")
        contribute.record_impact("1.2", "p", "first change", ["aaa111"])
        contribute.record_impact("1.3", "p", "second change", ["aaa111"])
        stored = json.loads(self.impact_path.read_text(encoding="utf-8"))
        self.assertEqual([e["version"] for e in stored], ["1.2", "1.3"])

    # -- impact_log ----------------------------------------------------

    def test_impact_log_newest_first(self):
        self._stage_bundle("aaa111")
        contribute.record_impact("1.2", "p", "first change", ["aaa111"])
        contribute.record_impact("1.3", "p", "second change", ["aaa111"])
        result = contribute.impact_log()
        self.assertEqual(result["count"], 2)
        self.assertEqual(
            [e["version"] for e in result["impacts"]], ["1.3", "1.2"])
        self.assertIn("1.3", result["rendered"])
        self.assertIn("second change", result["rendered"])

    def test_impact_log_empty_is_plain(self):
        result = contribute.impact_log()
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["impacts"], [])
        self.assertIn("No persona improvements", result["rendered"])

    def test_impact_log_tolerates_corrupt_file(self):
        self.impact_path.parent.mkdir(parents=True, exist_ok=True)
        self.impact_path.write_text("not json{{{", encoding="utf-8")
        self.assertEqual(contribute.impact_log()["count"], 0)

    # -- my_impact -----------------------------------------------------

    def test_my_impact_no_bundles_says_so_plainly(self):
        contribute.record_impact("1.3", "p", "change", ["someone-else"])
        result = contribute.my_impact()
        self.assertEqual(result["contributed_bundles"], 0)
        self.assertEqual(result["improvements"], [])
        self.assertIn("not staged", result["headline"])
        self.assertIn("impact_log", result)

    def test_my_impact_bundles_not_cited_yet_shows_full_log(self):
        self._stage_bundle("aaa111")
        contribute.record_impact("1.3", "p", "change", ["other-person"])
        result = contribute.my_impact()
        self.assertEqual(result["contributed_bundles"], 1)
        self.assertEqual(result["improvements"], [])
        self.assertIn("not been cited", result["headline"])
        self.assertIn("Full impact log", result["rendered"])
        self.assertIn("1.3", result["rendered"])  # full log present

    def test_my_impact_links_only_actually_cited_bundles(self):
        # Two local bundles; the impact entry cites only one of them.
        self._stage_bundle("aaa111")
        self._stage_bundle("bbb222")
        contribute.record_impact("1.3", "hardball_negotiator",
                                 "now pushes on equity, not just base",
                                 ["bbb222"])
        result = contribute.my_impact()
        self.assertEqual(result["contributed_bundles"], 2)
        self.assertEqual(len(result["improvements"]), 1)
        improvement = result["improvements"][0]
        self.assertEqual(improvement["persona"], "hardball_negotiator")
        self.assertEqual(improvement["your_bundles"], ["bbb222"])
        # Honesty: the uncited bundle is never attributed.
        self.assertNotIn("aaa111", json.dumps(result["improvements"]))
        self.assertIn("bbb222", improvement["your_bundles"])
        self.assertIn("hardball_negotiator v1.3", result["headline"])

    def test_my_impact_headline_is_satisfying(self):
        self._stage_bundle("aaa111")
        self._stage_bundle("bbb222")
        contribute.record_impact(
            "1.3", "hardball_negotiator",
            "now pushes on equity, not just base", ["aaa111", "bbb222"])
        result = contribute.my_impact()
        headline = result["headline"]
        self.assertIn("2 contributed bundles", headline)
        self.assertIn("hardball_negotiator v1.3", headline)
        self.assertIn("equity", headline)
        # Rendered block names each improvement.
        self.assertIn("your cited bundles: 2", result["rendered"])

    def test_my_impact_aggregates_across_multiple_entries(self):
        self._stage_bundle("aaa111")
        contribute.record_impact("1.2", "skeptical_interviewer",
                                 "challenges vague ownership claims",
                                 ["aaa111"])
        contribute.record_impact("1.3", "hardball_negotiator",
                                 "equity pushback", ["aaa111"])
        result = contribute.my_impact()
        self.assertEqual(len(result["improvements"]), 2)
        personas = {i["persona"] for i in result["improvements"]}
        self.assertEqual(personas,
                         {"skeptical_interviewer", "hardball_negotiator"})
        self.assertIn("2 personas", result["headline"])

    # -- MCP + CLI wiring ----------------------------------------------

    def test_register_tools_includes_impact_tools(self):
        seen: dict = {}

        class FakeMCP:
            def tool(self):
                def deco(fn):
                    seen[fn.__name__] = fn
                    return fn
                return deco

        contribute.register_tools(FakeMCP())
        for name in ("record_impact", "impact_log", "my_impact",
                     "rate_persona", "scrub_rules"):
            self.assertIn(name, seen)
        self.assertIn("No persona improvements",
                      seen["impact_log"]()["rendered"])
        rec = seen["record_impact"]("2.0", "coach", "friendlier openers",
                                    ["ghost-id"])
        self.assertTrue(rec["recorded"])
        self.assertIn("warnings", rec)  # unknown id warns, doesn't fail

    def _cli_namespace(self, action: str, **kwargs) -> argparse.Namespace:
        defaults = dict(action=action, json=True, session_id=None,
                        session_ids=None, stars=None, note="", confirm=False,
                        version=None, persona=None, change=None,
                        bundle_ids=None)
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_cli_impact_actions(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers()
        mapping = contribute.register_cli(sub)
        handler = mapping["contribute"]

        self.assertEqual(handler(self._cli_namespace("impact-log")), 0)
        self.assertEqual(handler(self._cli_namespace("my-impact")), 0)

        self._stage_bundle("aaa111")
        rc = handler(self._cli_namespace(
            "record-impact", version="1.3", persona="hardball_negotiator",
            change="equity pushback", bundle_ids="aaa111"))
        self.assertEqual(rc, 0)
        self.assertEqual(contribute.impact_log()["count"], 1)

    def test_cli_record_impact_validation_returns_nonzero(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers()
        mapping = contribute.register_cli(sub)
        rc = mapping["contribute"](self._cli_namespace("record-impact"))
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()

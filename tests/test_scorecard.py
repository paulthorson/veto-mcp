#!/usr/bin/env python3
"""Tests for Initiative 09 epic 6: the reliability scorecard and the
provider-health contract interface (defined by i09 pending 03's publication).

No network; the health store is a temp JSONL file. Asserts streak math,
honest "no data" rows, and the four scorecard columns.
"""

import json
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from providers import health_contract, scorecard
from providers.health_contract import (
    FileHealthStore,
    HealthSnapshot,
    record_fetch,
)


class HealthStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = FileHealthStore(Path(self.tmp.name) / "health.jsonl")

    def test_record_and_latest_roundtrip(self):
        snap = record_fetch(
            self.store, "greenhouse", success=True,
            capability_label="search+details",
            budget_used=12, budget_total=500,
        )
        self.assertTrue(snap.success)
        self.assertEqual(snap.recovery_streak, 1)
        latest = self.store.latest("greenhouse")
        self.assertEqual(latest.capability_label, "search+details")

    def test_streak_math(self):
        record_fetch(self.store, "lever", success=True)
        record_fetch(self.store, "lever", success=True)
        third = record_fetch(self.store, "lever", success=False,
                             error_state="http_429")
        self.assertEqual(third.recovery_streak, 0)
        self.assertEqual(third.consecutive_failures, 1)
        self.assertEqual(third.error_state, "http_429")
        fourth = record_fetch(self.store, "lever", success=True)
        self.assertEqual(fourth.recovery_streak, 1)
        self.assertEqual(fourth.consecutive_failures, 0)
        self.assertEqual(fourth.error_state, "")

    def test_last_success_carries_forward(self):
        first = record_fetch(self.store, "ashby", success=True)
        time.sleep(0.01)
        second = record_fetch(self.store, "ashby", success=False,
                              error_state="timeout")
        self.assertEqual(second.last_success_ts, first.last_success_ts)

    def test_unknown_provider_has_no_snapshot(self):
        self.assertIsNone(self.store.latest("nope"))

    def test_store_is_local_jsonl(self):
        record_fetch(self.store, "greenhouse", success=True)
        path = Path(self.tmp.name) / "health.jsonl"
        self.assertTrue(path.exists())
        raw = json.loads(path.read_text().strip().splitlines()[-1])
        self.assertEqual(raw["provider"], "greenhouse")

    def test_snapshot_protocol_fields(self):
        snap = HealthSnapshot(provider="x", fetched_at=time.time(),
                              success=True)
        d = snap.to_dict()
        for key in ("freshness_s", "error_state", "last_success_ts",
                    "capability_label", "budget_used", "budget_total",
                    "cooldown_until", "captcha_state", "recovery_streak",
                    "consecutive_failures"):
            self.assertIn(key, d, key)


class ScoreboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = FileHealthStore(Path(self.tmp.name) / "health.jsonl")

    def test_no_data_rows_are_honest(self):
        rows = scorecard.scoreboard(self.store)
        names = {r["provider"] for r in rows}
        self.assertIn("greenhouse", names)
        gh = next(r for r in rows if r["provider"] == "greenhouse")
        self.assertEqual(gh["status"], "no data")
        self.assertEqual(gh["last_success"], "never")
        # Unknowns are unknowns, never "healthy".
        self.assertNotEqual(gh["status"], "ok")

    def test_recorded_provider_shows_four_columns(self):
        record_fetch(self.store, "lever", success=True,
                     capability_label="search+details")
        rows = scorecard.scoreboard(self.store)
        lv = next(r for r in rows if r["provider"] == "lever")
        self.assertEqual(lv["status"], "ok")
        self.assertEqual(lv["freshness"], "fresh")
        self.assertNotEqual(lv["last_success"], "never")
        self.assertEqual(lv["capability"], "search+details")
        self.assertEqual(lv["error_state"], "—")

    def test_error_row_shows_error_state(self):
        record_fetch(self.store, "ziprecruiter", success=False,
                     error_state="captcha", captcha_state="blocking")
        rows = scorecard.scoreboard(self.store)
        zr = next(r for r in rows if r["provider"] == "ziprecruiter")
        self.assertEqual(zr["status"], "error")
        self.assertEqual(zr["error_state"], "captcha")
        self.assertEqual(zr["captcha"], "blocking")

    def test_manifest_completeness_flag(self):
        rows = scorecard.scoreboard(self.store)
        for r in rows:
            if r["provider"] in ("greenhouse", "lever", "ashby"):
                self.assertTrue(r["manifest_complete"], r["provider"])

    def test_terminal_render_is_a_table(self):
        text = scorecard.render_terminal(scorecard.scoreboard(self.store))
        self.assertIn("provider", text)
        self.assertIn("capability", text)
        self.assertIn("local-first", text)

    def test_json_output_parses(self):
        rows = scorecard.scoreboard(self.store)
        parsed = json.loads(scorecard.to_json(rows))
        self.assertEqual(len(parsed), len(rows))


class ProviderHealthAdapterTests(unittest.TestCase):
    """The 03→09 adapter: Initiative 03's provider_health.py mapped onto
    HealthSnapshot. Patches 03's DEFAULT_STORE to a temp file.

    Skipped when 03's file is not in the tree (uncommitted) — the adapter
    then exercises its FileHealthStore fallback instead.
    """

    @classmethod
    def setUpClass(cls):
        try:
            import provider_health  # noqa: F401
        except ImportError:
            raise unittest.SkipTest(
                "provider_health (Initiative 03) not in tree; "
                "adapter falls back to FileHealthStore"
            )

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        import provider_health
        self._patch = mock.patch.object(
            provider_health, "DEFAULT_STORE",
            Path(self.tmp.name) / "provider_health.json",
        )
        self._patch.start()
        self.addCleanup(self._patch.stop)
        self.adapter = health_contract.ProviderHealthAdapter()

    def test_success_maps_to_ok_snapshot(self):
        import provider_health
        provider_health.record_fetch("greenhouse", True)
        snap = self.adapter.latest("greenhouse")
        self.assertIsNotNone(snap)
        self.assertTrue(snap.success)
        self.assertEqual(snap.status if hasattr(snap, "status") else "ok", "ok")
        self.assertNotEqual(snap.last_success_ts, 0.0)
        self.assertEqual(snap.capability_label, "search+details")
        self.assertEqual(snap.captcha_state, "none")

    def test_captcha_blocked_maps(self):
        import provider_health
        provider_health.record_fetch("ziprecruiter", False, note="denied")
        provider_health.record_captcha("ziprecruiter", "blocked")
        snap = self.adapter.latest("ziprecruiter")
        self.assertFalse(snap.success)
        self.assertEqual(snap.captcha_state, "blocking")
        self.assertIn("captcha", snap.error_state)

    def test_degraded_maps_failure_count(self):
        import provider_health
        for _ in range(3):
            provider_health.record_fetch("lever", False)
        snap = self.adapter.latest("lever")
        self.assertEqual(snap.consecutive_failures, 3)
        self.assertIn("failure", snap.error_state)

    def test_unknown_provider_returns_none(self):
        self.assertIsNone(self.adapter.latest("nope"))

    def test_adapter_record_delegates_to_03(self):
        import provider_health
        snap = health_contract.HealthSnapshot(
            provider="ashby", fetched_at=0.0, success=True)
        self.adapter.record(snap)
        row = provider_health.provider_status("ashby")
        self.assertEqual(row["status"], "ok")
        self.assertEqual(row["consecutive_failures"], 0)

    def test_scoreboard_reads_through_adapter(self):
        import provider_health
        provider_health.record_fetch("greenhouse", True)
        rows = scorecard.scoreboard(self.adapter)
        gh = next(r for r in rows if r["provider"] == "greenhouse")
        self.assertEqual(gh["status"], "ok")
        self.assertNotEqual(gh["last_success"], "never")

    def test_snapshot_from_status_field_mapping(self):
        row = {
            "status": "cooling", "cooldown_remaining_s": 100,
            "cooldown_reason": "http_429", "captcha_state": "clear",
            "consecutive_failures": 1, "recovery_streak_days": 2,
            "last_successful_fetch": "2026-09-13T10:00:00+00:00",
            "budget": {"used_today": 5, "daily_limit": 40},
        }
        snap = health_contract.snapshot_from_status("ziprecruiter", row)
        self.assertEqual(snap.error_state, "http_429")
        self.assertEqual(snap.budget_used, 5)
        self.assertEqual(snap.budget_total, 40)
        self.assertEqual(snap.recovery_streak, 2)
        self.assertTrue(snap.is_cooling_down)


if __name__ == "__main__":
    unittest.main()

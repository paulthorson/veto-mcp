#!/usr/bin/env python3
"""Tests for the circuit-breaker recovery path (compliance.py).

``compliance.record_block`` trips a 1h/doubling/24h-capped cooldown with
no decay path. ``compliance.record_search_success`` closes the gap: a
window of consecutive genuine successful fetches clears the block and
resets the cooldown. These tests cover:

  (a) blocks escalate to the 24h cap,
  (b) sustained successes clear the block and reset the cooldown,
  (c) intermittent failures still escalate (a block resets the streak),
  (d) the ZipRecruiter provider records successes only on genuine
      fetches (never on 403/429/CAPTCHA), and
  (e) server.search_jobs wires successful provider searches into the
      recovery counter.

All state is pointed at a temp compliance.json; all HTTP is mocked.
"""

import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import compliance


def _block_info(board, path):
    return compliance.load_state(path)["blocks"][board]


class ComplianceRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cpath = Path(self.tmp.name) / "compliance.json"
        state = compliance._default_state()
        state["risk_acknowledged"] = True
        compliance.save_state(state, self.cpath)
        patcher = mock.patch.object(compliance, "COMPLIANCE_FILE", self.cpath)
        self.addCleanup(patcher.stop)
        patcher.start()

    # -- (a) escalation -------------------------------------------------

    def test_block_cooldown_escalates_to_24h_cap(self):
        expected = [3600, 7200, 14400, 28800, 57600, 86400, 86400]
        for want in expected:
            self.assertEqual(compliance.record_block("ziprecruiter"), want)
        info = _block_info("ziprecruiter", self.cpath)
        self.assertEqual(info["consecutive"], 7)
        self.assertIsNotNone(info["blocked_until"])

    # -- (b) sustained successes clear the block -----------------------

    def test_three_consecutive_successes_clear_block(self):
        compliance.record_block("ziprecruiter")
        allowed, reason = compliance.check_search_allowed("ziprecruiter")
        self.assertFalse(allowed)
        self.assertIn("cooling down", reason)

        # Two successes are not enough: the block stands.
        self.assertFalse(compliance.record_search_success("ziprecruiter"))
        self.assertFalse(compliance.record_search_success("ziprecruiter"))
        info = _block_info("ziprecruiter", self.cpath)
        self.assertEqual(info["consecutive"], 1)
        self.assertIsNotNone(info["blocked_until"])
        allowed, _ = compliance.check_search_allowed("ziprecruiter")
        self.assertFalse(allowed)

        # The third consecutive success clears the block and resets the
        # cooldown.
        self.assertTrue(compliance.record_search_success("ziprecruiter"))
        info = _block_info("ziprecruiter", self.cpath)
        self.assertEqual(info["consecutive"], 0)
        self.assertIsNone(info["blocked_until"])
        self.assertEqual(info["successes"], 0)
        allowed, _ = compliance.check_search_allowed("ziprecruiter")
        self.assertTrue(allowed)

    # -- (f) observability -------------------------------------------------

    def test_status_summary_surfaces_recovery_streak(self):
        summary = compliance.status_summary()
        board = summary["boards"]["ziprecruiter"]
        self.assertEqual(board["recovery_successes"], 0)
        self.assertEqual(board["recovery_window"], compliance.RECOVERY_SUCCESS_WINDOW)

        compliance.record_block("ziprecruiter")
        compliance.record_search_success("ziprecruiter")
        board = compliance.status_summary()["boards"]["ziprecruiter"]
        self.assertEqual(board["recovery_successes"], 1)
        self.assertEqual(board["consecutive_blocks"], 1)

        # Recovery clears the block and the streak together.
        for _ in range(compliance.RECOVERY_SUCCESS_WINDOW - 1):
            compliance.record_search_success("ziprecruiter")
        board = compliance.status_summary()["boards"]["ziprecruiter"]
        self.assertEqual(board["recovery_successes"], 0)
        self.assertEqual(board["consecutive_blocks"], 0)

    def test_block_after_recovery_restarts_at_base_cooldown(self):
        compliance.record_block("ziprecruiter")
        for _ in range(compliance.RECOVERY_SUCCESS_WINDOW):
            compliance.record_search_success("ziprecruiter")
        # Recovery cleared the history, so the next block starts at 1h.
        self.assertEqual(compliance.record_block("ziprecruiter"), 3600)
        info = _block_info("ziprecruiter", self.cpath)
        self.assertEqual(info["consecutive"], 1)

    # -- (c) intermittent failures still escalate -----------------------

    def test_block_resets_success_streak_and_escalation_continues(self):
        compliance.record_block("ziprecruiter")  # 1h, consecutive=1
        compliance.record_search_success("ziprecruiter")
        compliance.record_search_success("ziprecruiter")
        # A new block breaks the streak and escalates.
        self.assertEqual(compliance.record_block("ziprecruiter"), 7200)
        info = _block_info("ziprecruiter", self.cpath)
        self.assertEqual(info["consecutive"], 2)
        self.assertEqual(info["successes"], 0)
        allowed, reason = compliance.check_search_allowed("ziprecruiter")
        self.assertFalse(allowed)
        self.assertIn("cooling down", reason)
        # Recovery still needs a full fresh window afterwards.
        compliance.record_search_success("ziprecruiter")
        compliance.record_search_success("ziprecruiter")
        info = _block_info("ziprecruiter", self.cpath)
        self.assertEqual(info["consecutive"], 2)  # not cleared yet
        self.assertTrue(compliance.record_search_success("ziprecruiter"))
        info = _block_info("ziprecruiter", self.cpath)
        self.assertEqual(info["consecutive"], 0)

    def test_success_without_block_history_is_noop(self):
        self.assertFalse(compliance.record_search_success("greenhouse"))
        # No block history means no state churn at all: nothing persisted.
        st = compliance.load_state(self.cpath)
        self.assertNotIn("greenhouse", st["blocks"])


# ---------------------------------------------------------------------------
# Provider-level wiring: ZipRecruiter records successes only on genuine
# fetches (200 without 403/429/CAPTCHA).
# ---------------------------------------------------------------------------


class FakeResponse:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class FakeClient:
    def __init__(self, handler):
        self._handler = handler

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, url, params=None, **kwargs):
        return self._handler(url, params)


SEARCH_HTML = """<html><head>
<script type="application/ld+json">
{"@type": "ItemList", "itemListElement": [
  {"@type": "ListItem", "position": 1, "name": "Backend Engineer",
   "url": "/c/Acme/Job/Backend-Engineer?jid=abc123"}
]}
</script>
</head><body>
<div class="job_result">
  <span data-testid="job-card-company">Acme Corp</span>
  <span data-testid="job-card-location">New York, NY</span>
</div>
</body></html>"""

DETAILS_HTML = """<html><head>
<script type="application/ld+json">
{"@type": "JobPosting", "title": "Backend Engineer",
 "hiringOrganization": {"name": "Acme Corp"},
 "description": "Build great systems."}
</script>
</head><body><h1>Backend Engineer</h1></body></html>"""


class ZipRecruiterProviderRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cpath = Path(self.tmp.name) / "compliance.json"
        compliance.save_state(compliance._default_state(), self.cpath)
        cpatcher = mock.patch.object(compliance, "COMPLIANCE_FILE", self.cpath)
        self.addCleanup(cpatcher.stop)
        cpatcher.start()

        from providers import _common
        from providers import ziprecruiter as zr

        self.zr = zr
        _common.clear_robots_cache()
        self.addCleanup(_common.clear_robots_cache)
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(zr, "polite_delay", return_value=None).start()
        mock.patch.object(
            _common, "make_client", side_effect=lambda *a, **k: self.client
        ).start()
        mock.patch.object(
            zr, "make_client", side_effect=lambda *a, **k: self.client
        ).start()

    def _serve(self, handler):
        self.client = FakeClient(handler)

    def _ok_handler(self, fail_first_search=False):
        state = {"search_fetches": 0}

        def handler(url, params):
            if url.endswith("/robots.txt"):
                return FakeResponse(200, "User-agent: *\nDisallow:\n")
            state["search_fetches"] += 1
            if fail_first_search and state["search_fetches"] == 1:
                return FakeResponse(429, "")
            if "jobs-search" in url:
                return FakeResponse(200, SEARCH_HTML)
            return FakeResponse(200, DETAILS_HTML)

        return handler

    def test_429_records_block_and_sustained_success_clears_it(self):
        self._serve(self._ok_handler(fail_first_search=True))
        prov = self.zr.ZipRecruiterProvider()

        # First search: 429 on page 1 -> block recorded, no results.
        jobs = prov.search("engineer", "New York, NY", limit=10,
                           remote_only=False)
        self.assertEqual(jobs, [])
        info = _block_info("ziprecruiter", self.cpath)
        self.assertEqual(info["consecutive"], 1)
        self.assertIsNotNone(info["blocked_until"])

        # Next search: two genuine page fetches (page 2 dedupes to no
        # progress and stops). Two successes < window: block stands.
        jobs = prov.search("engineer", "New York, NY", limit=10,
                           remote_only=False)
        self.assertEqual(len(jobs), 1)
        info = _block_info("ziprecruiter", self.cpath)
        self.assertEqual(info["consecutive"], 1)
        self.assertEqual(info["successes"], 2)

        # One more successful page fetch completes the window and clears.
        jobs = prov.search("engineer", "New York, NY", limit=10,
                           remote_only=False)
        self.assertEqual(len(jobs), 1)
        info = _block_info("ziprecruiter", self.cpath)
        self.assertEqual(info["consecutive"], 0)
        self.assertIsNone(info["blocked_until"])

    def test_details_success_counts_toward_recovery(self):
        self._serve(self._ok_handler())
        prov = self.zr.ZipRecruiterProvider()
        compliance.record_block("ziprecruiter")

        details = prov.get_details(
            "https://www.ziprecruiter.com/c/Acme/Job/x?jid=zzz"
        )
        self.assertEqual(details["title"], "Backend Engineer")
        info = _block_info("ziprecruiter", self.cpath)
        self.assertEqual(info["successes"], 1)

        # Two more genuine fetches complete the window.
        prov.get_details(
            "https://www.ziprecruiter.com/c/Acme/Job/x?jid=zzz"
        )
        self.assertFalse(
            _block_info("ziprecruiter", self.cpath)["blocked_until"]
            is None
        )
        prov.get_details(
            "https://www.ziprecruiter.com/c/Acme/Job/x?jid=zzz"
        )
        info = _block_info("ziprecruiter", self.cpath)
        self.assertEqual(info["consecutive"], 0)
        self.assertIsNone(info["blocked_until"])

    def test_captcha_fetch_records_block_not_success(self):
        html = ("<html><head><title>verify you are human</title></head>"
                "<body>captcha challenge</body></html>")

        def handler(url, params):
            if url.endswith("/robots.txt"):
                return FakeResponse(200, "User-agent: *\nDisallow:\n")
            return FakeResponse(200, html)

        self._serve(handler)
        prov = self.zr.ZipRecruiterProvider()
        # Seed two successes, then a CAPTCHA page: the streak must break
        # and escalate, never count as a success.
        compliance.record_block("ziprecruiter")
        compliance.record_search_success("ziprecruiter")
        compliance.record_search_success("ziprecruiter")
        jobs = prov.search("engineer", "New York, NY", limit=10,
                           remote_only=False)
        self.assertEqual(jobs, [])
        info = _block_info("ziprecruiter", self.cpath)
        self.assertEqual(info["consecutive"], 2)
        self.assertEqual(info["successes"], 0)


# ---------------------------------------------------------------------------
# Server-level wiring: search_jobs does NOT record recovery successes
# itself. Providers record genuine fetches at their own call sites (post
# block/CAPTCHA checks), and those recordings flow through
# server.search_jobs into the recovery counter. A provider whose fetch was
# pushed back (403/429/CAPTCHA) returns [] without raising and records a
# block, never a success -- the server must not count such a fetch.
# ---------------------------------------------------------------------------


class _RecordingStubProvider:
    name = "greenhouse"

    def search(self, query, location, limit, remote_only):
        # Mirrors a real provider: only genuine fetches are recorded.
        compliance.record_search_success(self.name)
        return [{
            "id": "greenhouse:test-1",
            "title": "Backend Engineer",
            "company": "Acme Corp",
            "location": "New York, NY",
            "url": "https://example.com/j/1",
            "board": self.name,
        }]


class _BlockedStubProvider:
    name = "greenhouse"

    def search(self, query, location, limit, remote_only):
        # Mirrors the ZipRecruiter provider on 403/429/CAPTCHA: record a
        # block, return [] without raising, never record a success.
        compliance.record_block(self.name)
        return []


class ServerRecoveryWiringTest(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cpath = Path(self.tmp.name) / "compliance.json"
        compliance.save_state(compliance._default_state(), self.cpath)
        cpatcher = mock.patch.object(compliance, "COMPLIANCE_FILE", self.cpath)
        self.addCleanup(cpatcher.stop)
        cpatcher.start()
        self.addCleanup(mock.patch.stopall)

        import server

        self.server = server
        stub = _RecordingStubProvider()
        mock.patch.dict(server.PROVIDERS, {"greenhouse": stub}).start()
        # Keep the test hermetic: adjudication always allows; the gate
        # under test is compliance.check_search_allowed.
        mock.patch.object(
            server, "_risk_policy",
            mock.Mock(**{"adjudicate_search.return_value": {
                "allowed": True, "reason": "", "tier": "official",
            }}),
        ).start()

    def _expire_cooldown(self):
        st = compliance.load_state(self.cpath)
        st["blocks"]["greenhouse"]["blocked_until"] = (
            datetime.now(timezone.utc) - timedelta(seconds=1)
        ).isoformat()
        compliance.save_state(st, self.cpath)

    def test_successful_searches_clear_block_via_server(self):
        compliance.record_block("greenhouse")
        self._expire_cooldown()  # cooldown elapsed; history remains

        for _ in range(compliance.RECOVERY_SUCCESS_WINDOW - 1):
            jobs = self.server.search_jobs(query="engineer", location="New York",
                                           board="greenhouse", limit=5)
            self.assertEqual(len(jobs), 1)
        info = _block_info("greenhouse", self.cpath)
        self.assertEqual(info["consecutive"], 1)  # not cleared yet

        jobs = self.server.search_jobs(query="engineer", location="New York",
                                       board="greenhouse", limit=5)
        self.assertEqual(len(jobs), 1)
        info = _block_info("greenhouse", self.cpath)
        self.assertEqual(info["consecutive"], 0)
        self.assertIsNone(info["blocked_until"])


    def test_blocked_search_does_not_count_toward_recovery_via_server(self):
        # Defect regression: a 429/CAPTCHA'd fetch through the real
        # server.search_jobs wiring must leave `successes` at 0 and never
        # clear the block.
        compliance.record_block("greenhouse")
        self._expire_cooldown()  # cooldown elapsed; history remains

        with mock.patch.dict(self.server.PROVIDERS,
                             {"greenhouse": _BlockedStubProvider()}):
            for _ in range(compliance.RECOVERY_SUCCESS_WINDOW):
                jobs = self.server.search_jobs(
                    query="engineer", location="New York",
                    board="greenhouse", limit=5)
                self.assertEqual(jobs, [])
        info = _block_info("greenhouse", self.cpath)
        self.assertEqual(info["successes"], 0)
        self.assertEqual(info["consecutive"], 4)  # 1 + 3 new blocks
        self.assertIsNotNone(info["blocked_until"])

    def test_server_does_not_record_successes_itself(self):
        # A provider that returns normally without recording any success
        # must not gain recovery credit from the server.
        import types
        plain = types.SimpleNamespace(
            name="greenhouse",
            search=lambda *a, **k: [{"board": "greenhouse"}],
        )
        compliance.record_block("greenhouse")
        self._expire_cooldown()
        with mock.patch.dict(self.server.PROVIDERS, {"greenhouse": plain}):
            jobs = self.server.search_jobs(query="engineer", location="New York",
                                           board="greenhouse", limit=5)
            self.assertEqual(len(jobs), 1)
        info = _block_info("greenhouse", self.cpath)
        self.assertEqual(info["successes"], 0)
        self.assertEqual(info["consecutive"], 1)  # still blocked


if __name__ == "__main__":
    unittest.main()

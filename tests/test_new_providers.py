#!/usr/bin/env python3
"""Unit tests for the ZipRecruiter + Glassdoor provider modules.

All HTTP is mocked; no network. ZipRecruiter tests assert the job-id
format round-trips through ``providers._common.decode_payload``, that
HTTP 429/403 and CAPTCHA pages trigger ``compliance.record_block``
(monkeypatched), that robots.txt is honored, and that the policy
machinery (daily budgets, circuit-breaker cooldowns, ledger entries)
gates searches via ``risk_policy.adjudicate_search``.
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import compliance
from governance import risk_policy
from providers import _common
from providers import glassdoor as gd
from providers import ziprecruiter as zr


# ---------------------------------------------------------------------------
# Fake HTTP layer
# ---------------------------------------------------------------------------


class FakeResponse:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def json(self):  # pragma: no cover - not used by these tests
        raise AssertionError("no JSON in these fixtures")


class FakeClient:
    def __init__(self, handler):
        self._handler = handler
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, url, params=None, **kwargs):
        self.calls.append((url, params))
        return self._handler(url, params)


SEARCH_HTML = """<html><head>
<script type="application/ld+json">
{"@type": "ItemList", "itemListElement": [
  {"@type": "ListItem", "position": 1, "name": "Backend Engineer",
   "url": "/c/Acme/Job/Backend-Engineer-in-NYC?jid=abc123"},
  {"@type": "ListItem", "position": 2, "name": "Frontend Engineer",
   "url": "https://www.ziprecruiter.com/c/Beta/Job/Frontend-Engineer?jid=def456"}
]}
</script>
</head><body>
<div class="job_result card-x">
  <span data-testid="job-card-company">Acme Corp</span>
  <span data-testid="job-card-location">New York, NY</span>
  <span>$120,000 - $150,000 a year</span>
</div>
<div class="job_result card-y">
  <span data-testid="job-card-company">Beta Inc</span>
  <span data-testid="job-card-location">Remote</span>
</div>
</body></html>"""

DETAILS_HTML = """<html><head>
<script type="application/ld+json">
{"@type": "JobPosting", "title": "Backend Engineer",
 "hiringOrganization": {"name": "Acme Corp"},
 "description": "<p>Build great systems.</p>"}
</script>
</head><body><h1>Backend Engineer</h1></body></html>"""


def _patch_provider(testcase, handler):
    """Point the provider at a fake client; silence politeness delays.

    Also intercepts the robots.txt fetch (``_common.make_client``, used
    by ``robots_allows``) and clears the robots cache so tests are
    independent.
    """
    client = FakeClient(handler)
    testcase.addCleanup(mock.patch.stopall)
    _common.clear_robots_cache()
    testcase.addCleanup(_common.clear_robots_cache)
    mock.patch.object(zr, "make_client", return_value=client).start()
    mock.patch.object(_common, "make_client", return_value=client).start()
    mock.patch.object(zr, "polite_delay", return_value=None).start()
    return client


def _with_robots(handler, robots_body="User-agent: *\nDisallow:\n"):
    """Route /robots.txt to a fixed body; everything else to ``handler``."""
    def route(url, params):
        if url.endswith("/robots.txt"):
            return FakeResponse(200, robots_body)
        return handler(url, params)
    return route


class TestZipRecruiterSearch(unittest.TestCase):
    def test_parses_itemlist_and_pairs_cards_by_index(self):
        client = _patch_provider(
            self, lambda url, params: FakeResponse(200, SEARCH_HTML)
        )
        jobs = zr.ZipRecruiterProvider().search(
            "engineer", "New York, NY", limit=10, remote_only=False
        )
        self.assertEqual(len(jobs), 2)
        first, second = jobs
        self.assertEqual(first["title"], "Backend Engineer")
        self.assertEqual(first["company"], "Acme Corp")
        self.assertEqual(first["location"], "New York, NY")
        self.assertEqual(first["board"], "ziprecruiter")
        self.assertIn("$120,000", first["snippet"])
        self.assertEqual(second["company"], "Beta Inc")
        self.assertEqual(second["location"], "Remote")
        # params actually sent to the SSR search endpoint (robots.txt is
        # fetched first and honored before any search request)
        search_calls = [c for c in client.calls if c[0] == zr.SEARCH_URL]
        self.assertTrue(search_calls, "expected a call to the search page")
        url, params = search_calls[0]
        self.assertEqual(url, zr.SEARCH_URL)
        self.assertEqual(params["search"], "engineer")
        self.assertIn("page", params)

    def test_job_id_round_trips_through_common(self):
        _patch_provider(self, lambda url, params: FakeResponse(200, SEARCH_HTML))
        jobs = zr.ZipRecruiterProvider().search("engineer", "", limit=10,
                                               remote_only=False)
        job = jobs[0]
        board, token = job["id"].split(":", 1)
        self.assertEqual(board, "ziprecruiter")
        payload = _common.decode_payload(token)
        self.assertEqual(
            payload,
            "https://www.ziprecruiter.com/c/Acme/Job/Backend-Engineer-in-NYC"
            "?jid=abc123",
        )
        self.assertEqual(payload, job["url"])
        # and the canonical builder produces the same id
        self.assertEqual(job["id"], _common.make_job_id("ziprecruiter", payload))

    def test_results_carry_scraping_risk_tag(self):
        _patch_provider(self, lambda url, params: FakeResponse(200, SEARCH_HTML))
        jobs = zr.ZipRecruiterProvider().search("engineer", "", limit=10,
                                               remote_only=False)
        for job in jobs:
            self.assertEqual(job["tos_risk_tier"], "scraping")
            self.assertIn("tos_notice", job)

    def test_remote_only_filter(self):
        _patch_provider(self, lambda url, params: FakeResponse(200, SEARCH_HTML))
        jobs = zr.ZipRecruiterProvider().search("engineer", "", limit=10,
                                               remote_only=True)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["company"], "Beta Inc")

    def test_limit_respected(self):
        _patch_provider(self, lambda url, params: FakeResponse(200, SEARCH_HTML))
        jobs = zr.ZipRecruiterProvider().search("engineer", "", limit=1,
                                               remote_only=False)
        self.assertEqual(len(jobs), 1)

    def test_429_triggers_record_block_and_returns_empty(self):
        _patch_provider(
            self, lambda url, params: FakeResponse(429, "rate limited")
        )
        blocked = []
        with mock.patch.object(
            compliance, "record_block",
            side_effect=lambda board: blocked.append(board) or 3600,
        ):
            jobs = zr.ZipRecruiterProvider().search(
                "engineer", "", limit=10, remote_only=False
            )
        self.assertEqual(jobs, [])
        self.assertEqual(blocked, ["ziprecruiter"])

    def test_403_triggers_record_block(self):
        _patch_provider(self, lambda url, params: FakeResponse(403, "denied"))
        blocked = []
        with mock.patch.object(
            compliance, "record_block",
            side_effect=lambda board: blocked.append(board) or 3600,
        ):
            jobs = zr.ZipRecruiterProvider().search(
                "engineer", "", limit=10, remote_only=False
            )
        self.assertEqual(jobs, [])
        self.assertEqual(blocked, ["ziprecruiter"])

    def test_captcha_page_stops_without_bypass_and_trips_breaker(self):
        html = "<html><head><title>verify you are human</title></head>" \
               "<body>captcha challenge</body></html>"
        _patch_provider(
            self, _with_robots(lambda url, params: FakeResponse(200, html))
        )
        blocked = []
        with mock.patch.object(
            compliance, "record_block",
            side_effect=lambda board: blocked.append(board) or 3600,
        ):
            jobs = zr.ZipRecruiterProvider().search(
                "engineer", "", limit=10, remote_only=False
            )
        # No results, no bypass attempt, and the circuit breaker tripped
        # (per policy, CAPTCHAs feed the same 1h-doubling cooldown as
        # 403/429).
        self.assertEqual(jobs, [])
        self.assertEqual(blocked, ["ziprecruiter"])

    def test_page_without_itemlist_returns_empty(self):
        _patch_provider(
            self, lambda url, params: FakeResponse(200, "<html></html>")
        )
        jobs = zr.ZipRecruiterProvider().search("engineer", "", limit=10,
                                               remote_only=False)
        self.assertEqual(jobs, [])

    def test_request_exception_returns_empty(self):
        def boom(url, params):
            raise ConnectionError("nope")
        _patch_provider(self, boom)
        jobs = zr.ZipRecruiterProvider().search("engineer", "", limit=10,
                                               remote_only=False)
        self.assertEqual(jobs, [])


class TestZipRecruiterRobots(unittest.TestCase):
    def test_robots_disallow_skips_search_without_fetching(self):
        client = _patch_provider(
            self,
            _with_robots(
                lambda url, params: FakeResponse(200, SEARCH_HTML),
                robots_body="User-agent: *\nDisallow: /jobs-search\n",
            ),
        )
        jobs = zr.ZipRecruiterProvider().search(
            "engineer", "", limit=10, remote_only=False
        )
        self.assertEqual(jobs, [])
        # robots.txt was consulted; the disallowed search page was not.
        self.assertTrue(
            any(url.endswith("/robots.txt") for url, _ in client.calls)
        )
        self.assertFalse(
            any(url == zr.SEARCH_URL for url, _ in client.calls)
        )

    def test_robots_disallow_skips_details(self):
        _patch_provider(
            self,
            _with_robots(
                lambda url, params: FakeResponse(200, DETAILS_HTML),
                robots_body="User-agent: *\nDisallow: /c/\n",
            ),
        )
        details = zr.ZipRecruiterProvider().get_details(
            "https://www.ziprecruiter.com/c/Acme/Job/Backend-Engineer?jid=abc123"
        )
        self.assertIn("error", details)
        self.assertIn("robots", details["error"].lower())

    def test_missing_robots_fails_open(self):
        def route(url, params):
            if url.endswith("/robots.txt"):
                return FakeResponse(404, "not found")
            return FakeResponse(200, SEARCH_HTML)
        _patch_provider(self, route)
        jobs = zr.ZipRecruiterProvider().search(
            "engineer", "", limit=10, remote_only=False
        )
        self.assertEqual(len(jobs), 2)


class _FakeFramework:
    """Stand-in for the agentic-governance framework module."""

    def __init__(self, veto_hits=()):
        self.veto_hits = list(veto_hits)
        self.recorded = []

    def check_veto(self, domain, text):
        return {"veto_hits": list(self.veto_hits)}

    def record_verdict(self, domain, verdict, summary, ticket, case_tag):
        self.recorded.append(
            {"verdict": verdict, "ticket": ticket, "case_tag": case_tag}
        )
        return {"recorded": True}


class TestZipRecruiterPolicyIntegration(unittest.TestCase):
    """Budget / circuit-breaker / ledger behavior for ziprecruiter.

    compliance state is pointed at a temp file; the governance framework
    is stubbed with the same _FakeMod pattern as test_risk_policy.py.
    """

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cpath = Path(self.tmp.name) / "compliance.json"
        self.state = compliance._default_state()
        compliance.save_state(self.state, self.cpath)
        compliance.acknowledge_risks(state=self.state, path=self.cpath)
        self.fake = _FakeFramework()
        patcher = mock.patch.object(
            risk_policy.adapter, "load_framework", return_value=self.fake
        )
        self.addCleanup(patcher.stop)
        patcher.start()
        cpatcher = mock.patch.object(
            compliance, "COMPLIANCE_FILE", self.cpath
        )
        self.addCleanup(cpatcher.stop)
        cpatcher.start()

    def test_budget_exhaustion_blocks_search_and_logs_ledger(self):
        for _ in range(compliance.DEFAULT_SEARCH_BUDGET["scraping"]):
            compliance.record_search("ziprecruiter", path=self.cpath)
        out = risk_policy.adjudicate_search("ziprecruiter", "engineer")
        self.assertFalse(out["allowed"])
        self.assertIn("budget exhausted", out["reason"])
        entries = [
            e for e in self.fake.recorded
            if e["ticket"] == "job-apply:risk:search:ziprecruiter"
        ]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["verdict"], "veto")
        self.assertEqual(entries[0]["case_tag"], "risk-blocked")

    def test_search_allowed_under_budget_logs_allow_verdict(self):
        out = risk_policy.adjudicate_search("ziprecruiter", "engineer")
        self.assertTrue(out["allowed"])
        entries = [
            e for e in self.fake.recorded
            if e["ticket"] == "job-apply:risk:search:ziprecruiter"
        ]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["verdict"], "pass")
        self.assertEqual(entries[0]["case_tag"], "risk-allowed")

    def test_block_cooldown_doubles_and_gates_search(self):
        # First block: 1h cooldown; second consecutive block: 2h.
        self.assertEqual(
            compliance.record_block("ziprecruiter", path=self.cpath), 3600
        )
        self.assertEqual(
            compliance.record_block("ziprecruiter", path=self.cpath), 7200
        )
        allowed, reason = compliance.check_search_allowed(
            "ziprecruiter", path=self.cpath
        )
        self.assertFalse(allowed)
        self.assertIn("cooling down", reason)


class TestZipRecruiterDetails(unittest.TestCase):
    def test_details_from_ld_json_jobposting(self):
        _patch_provider(self, lambda url, params: FakeResponse(200, DETAILS_HTML))
        details = zr.ZipRecruiterProvider().get_details(
            "https://www.ziprecruiter.com/c/Acme/Job/Backend-Engineer?jid=abc123"
        )
        self.assertEqual(details["title"], "Backend Engineer")
        self.assertEqual(details["company"], "Acme Corp")
        self.assertIn("Build great systems.", details["description"])
        self.assertNotIn("<p>", details["description"])  # HTML stripped
        self.assertEqual(details["board"], "ziprecruiter")
        self.assertTrue(details["apply_url"].endswith("?jid=abc123"))

    def test_details_failure_returns_error_dict(self):
        def boom(url, params):
            raise ConnectionError("nope")
        _patch_provider(self, boom)
        details = zr.ZipRecruiterProvider().get_details(
            "https://www.ziprecruiter.com/c/Acme/Job/x?jid=zzz"
        )
        self.assertIn("error", details)

    def test_details_captcha_trips_breaker_without_bypass(self):
        html = "<html><head><title>verify you are human</title></head>" \
               "<body>captcha challenge</body></html>"
        _patch_provider(
            self, _with_robots(lambda url, params: FakeResponse(200, html))
        )
        blocked = []
        with mock.patch.object(
            compliance, "record_block",
            side_effect=lambda board: blocked.append(board) or 3600,
        ):
            details = zr.ZipRecruiterProvider().get_details(
                "https://www.ziprecruiter.com/c/Acme/Job/x?jid=zzz"
            )
        self.assertIn("error", details)
        self.assertIn("captcha", details["error"].lower())
        self.assertEqual(blocked, ["ziprecruiter"])


class TestZipRecruiterRegistry(unittest.TestCase):
    def test_get_providers(self):
        providers = zr.get_providers()
        self.assertIn("ziprecruiter", providers)
        self.assertEqual(providers["ziprecruiter"].name, "ziprecruiter")
        self.assertIsInstance(providers["ziprecruiter"], zr.ZipRecruiterProvider)


class TestGlassdoorStub(unittest.TestCase):
    def test_search_raises_not_implemented_with_clear_reason(self):
        provider = gd.GlassdoorProvider()
        with self.assertRaises(NotImplementedError) as ctx:
            provider.search("engineer", "New York, NY", limit=10,
                            remote_only=False)
        message = str(ctx.exception).lower()
        self.assertIn("not supported", message)
        self.assertIn("bot", message)  # anti-bot explanation

    def test_details_raises_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            gd.GlassdoorProvider().get_details("https://example.com/job")

    def test_get_providers(self):
        providers = gd.get_providers()
        self.assertIn("glassdoor", providers)
        self.assertEqual(providers["glassdoor"].name, "glassdoor")


class TestGlassdoorServerStub(unittest.TestCase):
    """server.py keeps Glassdoor as a *documented* stub, not a TODO.

    The NotImplementedError message must be the shared policy rationale
    from providers/glassdoor.py (no public API + bot mitigation), so a
    search surfaces an honest reason instead of fake-empty results.
    """

    def test_server_stub_raises_documented_reason(self):
        import server

        provider = server.PROVIDERS["glassdoor"]
        self.assertEqual(provider.name, "glassdoor")
        with self.assertRaises(NotImplementedError) as ctx:
            provider.search(
                "engineer", "New York, NY", limit=5, remote_only=False
            )
        message = str(ctx.exception).lower()
        self.assertIn("not supported", message)
        self.assertIn("public api", message)
        with self.assertRaises(NotImplementedError) as ctx:
            provider.get_details("https://www.glassdoor.com/job/x")
        self.assertIn("not supported", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()

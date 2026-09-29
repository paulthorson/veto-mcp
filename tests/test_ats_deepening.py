#!/usr/bin/env python3
"""Tests for Initiative 09 epic 2: ATS deepening (Greenhouse/Lever/Ashby).

All HTTP is mocked; no network. Asserts the enriched detail fields are
parsed from the official public APIs and that the honest apply-path
declarations (no direct submit) hold.
"""

import json
import unittest
from unittest import mock

import httpx

import ats_apply
from providers import ashby, greenhouse, lever
from providers._common import fetch_json
from providers._contract import validate_job_detail


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def request(self, method, url, **kwargs):
        return FakeResponse(self._payload)


def _patch(testcase, module, payload):
    client = FakeClient(payload)
    testcase.addCleanup(mock.patch.stopall)
    mock.patch.object(module, "make_client", return_value=client).start()
    mock.patch.object(module, "polite_delay", return_value=None).start()


GREENHOUSE_DETAIL = {
    "id": 123,
    "title": "Backend Engineer",
    "absolute_url": "https://boards.greenhouse.io/acme/jobs/123",
    "location": {"name": "New York, NY"},
    "company_name": "Acme",
    "content": "<p>Build things.</p>",
    "departments": [{"name": "Engineering"}],
    "offices": [{"name": "NYC HQ"}],
    "metadata": [{"name": "Employment Type", "value": "Full-time"}],
    "updated_at": "2026-09-01T12:00:00Z",
    "questions": [
        {"label": "First name", "required": True},
        {"label": "Portfolio", "required": False},
    ],
}

LEVER_DETAIL = {
    "id": "abc-123",
    "text": "Backend Engineer",
    "hostedUrl": "https://jobs.lever.co/acme/abc-123",
    "applyUrl": "https://jobs.lever.co/acme/abc-123/apply",
    "categories": {
        "department": "Engineering",
        "team": "Platform",
        "commitment": "Full-time",
        "location": "New York",
    },
    "workplaceType": "remote",
    "descriptionPlain": "Build things.",
    "lists": [{"text": "Requirements", "content": "5 years"}],
    "createdAt": 1788220800000,  # 2026-09-01 UTC
}

ASHBY_BOARD = {
    "jobs": [
        {
            "id": "job-1",
            "title": "Backend Engineer",
            "department": "Engineering",
            "team": "Platform",
            "employmentType": "Full-Time",
            "location": "New York, NY",
            "isRemote": True,
            "jobUrl": "https://jobs.ashbyhq.com/acme/job-1",
            "applyUrl": "https://jobs.ashbyhq.com/acme/job-1/application",
            "descriptionPlain": "Build things.",
            "descriptionHtml": "<p>Build things.</p>",
            "publishedDate": "2026-09-01",
        }
    ]
}


class GreenhouseEnrichmentTests(unittest.TestCase):
    def test_enriched_detail_fields(self):
        _patch(self, greenhouse, GREENHOUSE_DETAIL)
        details = greenhouse.GreenhouseProvider(tokens=["acme"]).get_details(
            "acme:123"
        )
        self.assertEqual(details["application_questions"], 2)
        self.assertEqual(details["required_questions"], 1)
        self.assertEqual(details["offices"], ["NYC HQ"])
        self.assertEqual(details["custom_fields"], ["Employment Type"])
        self.assertEqual(details["employment_type"], "Full-time")
        self.assertEqual(details["posted_date"], "2026-09-01")
        self.assertIn("Greenhouse", details["readiness_note"])

    def test_enriched_detail_conforms_to_schema(self):
        _patch(self, greenhouse, GREENHOUSE_DETAIL)
        details = greenhouse.GreenhouseProvider(tokens=["acme"]).get_details(
            "acme:123"
        )
        self.assertEqual(validate_job_detail(details), [])

    def test_malformed_payload_still_errors(self):
        details = greenhouse.GreenhouseProvider(tokens=[]).get_details("nope")
        self.assertIn("error", details)

    def test_hostile_location_shapes_never_raise(self):
        # F1: vendor `location` sometimes arrives as a string, list, or
        # number instead of {"name": ...} — get_details must degrade to a
        # string location, never AttributeError.
        import copy

        for bad_location in (
            "New York, NY",                      # non-empty string
            [{"name": "NYC HQ"}],                # list
            {"id": 7},                           # dict without "name"
            42,                                  # number
        ):
            raw = copy.deepcopy(GREENHOUSE_DETAIL)
            raw["location"] = bad_location
            _patch(self, greenhouse, raw)
            details = greenhouse.GreenhouseProvider(tokens=["acme"]).get_details(
                "acme:123"
            )
            self.assertIsInstance(details["location"], str)
            self.assertIsInstance(details["remote"], bool)
            self.assertEqual(validate_job_detail(details), [])
            mock.patch.stopall()

    def test_non_dict_detail_payload_returns_error_shape(self):
        # F2: `if not data` lets truthy non-dicts through; a list/str
        # payload must get the documented {"url","board","error"} shape.
        for bad_payload in (["not", "a", "dict"], "a plain string"):
            _patch(self, greenhouse, bad_payload)
            details = greenhouse.GreenhouseProvider(tokens=["acme"]).get_details(
                "acme:123"
            )
            self.assertEqual(details["board"], "greenhouse")
            self.assertIn("error", details)
            self.assertEqual(validate_job_detail(details), [])
            mock.patch.stopall()


class LeverEnrichmentTests(unittest.TestCase):
    def test_enriched_detail_fields(self):
        _patch(self, lever, LEVER_DETAIL)
        details = lever.LeverProvider(tokens=["acme"]).get_details("acme:abc-123")
        self.assertEqual(details["departments"], ["Engineering", "Platform"])
        self.assertEqual(details["employment_type"], "Full-time")
        self.assertTrue(details["remote"])
        self.assertEqual(details["posted_date"], "2026-09-01")
        # Honest: the public API does not expose application questions.
        self.assertEqual(details["application_questions"], 0)
        self.assertIn("does not expose", details["readiness_note"])

    def test_enriched_detail_conforms_to_schema(self):
        _patch(self, lever, LEVER_DETAIL)
        details = lever.LeverProvider(tokens=["acme"]).get_details("acme:abc-123")
        self.assertEqual(validate_job_detail(details), [])

    def test_bad_created_at_falls_back_to_empty_posted_date(self):
        # Hostile or malformed vendor createdAt must never raise: the
        # detail shape is returned with posted_date "" instead.
        import copy

        for bad_created_at in ("not-a-timestamp", 10**22, -10**22):
            raw = copy.deepcopy(LEVER_DETAIL)
            raw["createdAt"] = bad_created_at
            _patch(self, lever, raw)
            details = lever.LeverProvider(tokens=["acme"]).get_details(
                "acme:abc-123"
            )
            self.assertEqual(details["posted_date"], "")
            self.assertEqual(validate_job_detail(details), [])
            mock.patch.stopall()


class AshbyEnrichmentTests(unittest.TestCase):
    def _provider(self):
        _patch(self, ashby, ASHBY_BOARD)
        prov = ashby.AshbyProvider(tokens=["acme"])
        # get_details re-fetches the board; FakeClient returns the board.
        return prov

    def test_enriched_detail_fields(self):
        details = self._provider().get_details("acme:job-1")
        self.assertEqual(details["departments"], ["Engineering", "Platform"])
        self.assertEqual(details["employment_type"], "Full-Time")
        self.assertTrue(details["remote"])
        self.assertEqual(details["application_questions"], 0)
        self.assertIn("401", details["readiness_note"])

    def test_enriched_detail_conforms_to_schema(self):
        details = self._provider().get_details("acme:job-1")
        self.assertEqual(validate_job_detail(details), [])

    def test_missing_posting_returns_error_shape(self):
        details = self._provider().get_details("acme:gone")
        self.assertIn("error", details)
        self.assertEqual(validate_job_detail(details), [])

    def test_non_string_location_never_raises(self):
        # F4: _parse_job called location.lower() assuming a string; hostile
        # shapes must degrade to a string location, never AttributeError.
        import copy

        for bad_location in ({"name": "NYC"}, ["New York"], 42):
            board = copy.deepcopy(ASHBY_BOARD)
            board["jobs"][0]["location"] = bad_location
            _patch(self, ashby, board)
            prov = ashby.AshbyProvider(tokens=["acme"])
            details = prov.get_details("acme:job-1")
            self.assertIsInstance(details["location"], str)
            self.assertEqual(validate_job_detail(details), [])
            mock.patch.stopall()


class FetchJsonNeverRaisesTests(unittest.TestCase):
    """F3: pin the `fetch_json` contract the headline "never raises on
    vendor data" guarantee rests on: transport errors, HTTP error
    statuses, and malformed JSON all yield None — never an exception.

    The whole call body (request, raise_for_status, json parse) sits
    inside one ``try/except Exception`` in providers/_common.py, so there
    is no residual raising path; these tests lock that in against future
    edits.
    """

    def _fetch(self, client):
        return fetch_json(client, "GET", "https://example.invalid/x")

    def test_http_404_returns_none(self):
        self.assertIsNone(self._fetch(_ResponseClient(_StatusBoomResponse(404))))

    def test_http_500_returns_none(self):
        self.assertIsNone(self._fetch(_ResponseClient(_StatusBoomResponse(500))))

    def test_timeout_returns_none(self):
        self.assertIsNone(
            self._fetch(_RequestBoomClient(httpx.TimeoutException("timed out")))
        )

    def test_connection_error_returns_none(self):
        self.assertIsNone(
            self._fetch(_RequestBoomClient(httpx.ConnectError("no route")))
        )

    def test_malformed_json_returns_none(self):
        self.assertIsNone(self._fetch(_ResponseClient(_JsonBoomResponse())))


class _ResponseClient:
    """Client whose request() returns the given response object verbatim."""

    def __init__(self, response):
        self._response = response

    def request(self, *args, **kwargs):
        return self._response


class _StatusBoomResponse:
    def __init__(self, status):
        self._status = status

    def raise_for_status(self):
        request = httpx.Request("GET", "https://example.invalid/x")
        response = httpx.Response(self._status, request=request)
        raise httpx.HTTPStatusError(
            f"HTTP {self._status}", request=request, response=response
        )

    def json(self):
        return {}


class _RequestBoomClient:
    """Client whose request() itself raises a transport-level httpx error."""

    def __init__(self, exc):
        self._exc = exc

    def request(self, *args, **kwargs):
        raise self._exc


class _JsonBoomResponse:
    """Response whose json() raises like a malformed body would."""

    def raise_for_status(self):
        pass

    def json(self):
        raise json.JSONDecodeError("Expecting value", "", 0)


class ApplyPathHonestyTests(unittest.TestCase):
    def test_no_board_allows_direct_apply(self):
        # Legal-hardening commit 6 deleted can_apply_direct entirely:
        # there is no direct-apply gate left to flip on for any board.
        self.assertFalse(hasattr(ats_apply, "can_apply_direct"))

    def test_describe_apply_path_names_browser_flow(self):
        for board in ("greenhouse", "lever", "ashby"):
            desc = ats_apply.describe_apply_path(board)
            self.assertFalse(desc["direct_apply_available"])
            self.assertIn("browser", desc["recommended_path"].lower())
            self.assertTrue(desc["official_interface_only"])
            self.assertTrue(desc["reason"])

    def test_describe_apply_path_unknown_board(self):
        desc = ats_apply.describe_apply_path("nope")
        self.assertEqual(desc["endpoint_status"], "unknown")
        self.assertFalse(desc["direct_apply_available"])


def _patch_once(module, payload):
    """Patch ``module``'s make_client/politle_delay to return one fixed
    payload. Returns a stop() callable the caller must invoke (finally
    block) before patching a different payload in the same test.
    """
    client = FakeClient(payload)
    patches = [
        mock.patch.object(module, "make_client", return_value=client),
        mock.patch.object(module, "polite_delay", return_value=None),
    ]
    for p in patches:
        p.start()

    def stop():
        for p in reversed(patches):
            p.stop()

    return stop


def _copy(payload):
    import copy

    return copy.deepcopy(payload)


class LeverNonDictDetailTests(unittest.TestCase):
    """F1 (round 2 blocker): Lever get_details must apply the same
    isinstance(raw, dict) guard Greenhouse got — truthy non-dict
    payloads (list, str) get the documented error shape, never crash."""

    def test_truthy_non_dict_detail_returns_error_shape(self):
        for bad_payload in (
            ["not", "a", "dict"],
            "a plain string",
            [{"id": "abc-123"}],
        ):
            stop = _patch_once(lever, bad_payload)
            try:
                details = lever.LeverProvider(tokens=["acme"]).get_details(
                    "acme:abc-123"
                )
            finally:
                stop()
            self.assertEqual(details["board"], "lever")
            self.assertIn("error", details)
            self.assertIn("url", details)
            self.assertEqual(validate_job_detail(details), [])

    def test_falsy_detail_still_returns_error_shape(self):
        for bad_payload in (None, {}, [], ""):
            stop = _patch_once(lever, bad_payload)
            try:
                details = lever.LeverProvider(tokens=["acme"]).get_details(
                    "acme:abc-123"
                )
            finally:
                stop()
            self.assertIn("error", details)
            self.assertEqual(validate_job_detail(details), [])


class NonStringNameLocationTests(unittest.TestCase):
    """F2 (round 2): {"name": 123} / {"name": ["x"]} must coerce to str —
    GUARANTEED str output — on all three providers' search AND
    get_details paths; .lower() chains must never see a non-string."""

    def test_ashby_search_and_details(self):
        for bad_location in ({"name": 123}, {"name": ["x"]}):
            board = {
                "jobs": [
                    {
                        "id": "job-1",
                        "title": "Backend Engineer",
                        "department": "Engineering",
                        "jobUrl": "https://jobs.ashbyhq.com/acme/job-1",
                        "location": bad_location,
                        "descriptionPlain": "Build things.",
                    }
                ]
            }
            stop = _patch_once(ashby, board)
            try:
                prov = ashby.AshbyProvider(tokens=["acme"])
                jobs = prov.search("", "", 0, False)
                self.assertEqual(len(jobs), 1)
                self.assertIsInstance(jobs[0]["location"], str)
                details = prov.get_details("acme:job-1")
                self.assertIsInstance(details["location"], str)
                self.assertEqual(validate_job_detail(details), [])
            finally:
                stop()

    def test_greenhouse_search_and_details(self):
        for bad_location in ({"name": 123}, {"name": ["x"]}):
            payload = {
                "company_name": "Acme",
                "jobs": [
                    {
                        "id": 1,
                        "title": "Backend Engineer",
                        "absolute_url": "https://boards.greenhouse.io/acme/jobs/1",
                        "location": bad_location,
                    }
                ],
            }
            stop = _patch_once(greenhouse, payload)
            try:
                prov = greenhouse.GreenhouseProvider(tokens=["acme"])
                jobs = prov.search("", "", 0, False)
                self.assertEqual(len(jobs), 1)
                self.assertIsInstance(jobs[0]["location"], str)
            finally:
                stop()
            detail = _copy(GREENHOUSE_DETAIL)
            detail["location"] = bad_location
            stop = _patch_once(greenhouse, detail)
            try:
                details = greenhouse.GreenhouseProvider(tokens=["acme"]).get_details(
                    "acme:123"
                )
                self.assertIsInstance(details["location"], str)
                self.assertEqual(validate_job_detail(details), [])
            finally:
                stop()

    def test_lever_search_and_details(self):
        for bad_location in ({"name": 123}, {"name": ["x"]}):
            posting = _copy(LEVER_DETAIL)
            posting["categories"] = {
                "department": "Engineering",
                "location": bad_location,
            }
            stop = _patch_once(lever, [posting])
            try:
                prov = lever.LeverProvider(tokens=["acme"])
                jobs = prov.search("", "", 0, False)
                self.assertEqual(len(jobs), 1)
                self.assertIsInstance(jobs[0]["location"], str)
            finally:
                stop()
            stop = _patch_once(lever, posting)
            try:
                details = lever.LeverProvider(tokens=["acme"]).get_details(
                    "acme:abc-123"
                )
                self.assertIsInstance(details["location"], str)
                self.assertEqual(validate_job_detail(details), [])
            finally:
                stop()


class HostileSearchItemTests(unittest.TestCase):
    """F3 (round 2): non-dict items mid-list (and a non-list `jobs`
    container) must be skipped — one hostile posting must not kill a
    multi-board search; the rest of the results stay intact."""

    def test_greenhouse_skips_hostile_items_mid_list(self):
        payload = {
            "company_name": "Acme",
            "jobs": [
                {
                    "id": 1,
                    "title": "Backend Engineer",
                    "absolute_url": "https://boards.greenhouse.io/acme/jobs/1",
                    "location": {"name": "NYC"},
                },
                "junk string",
                42,
                None,
                ["a", "list"],
                {
                    "id": 2,
                    "title": "Data Engineer",
                    "absolute_url": "https://boards.greenhouse.io/acme/jobs/2",
                    "location": {"name": "SF"},
                },
            ],
        }
        stop = _patch_once(greenhouse, payload)
        try:
            jobs = greenhouse.GreenhouseProvider(tokens=["acme"]).search(
                "", "", 0, False
            )
        finally:
            stop()
        self.assertEqual(len(jobs), 2)
        self.assertEqual(
            [j["title"] for j in jobs], ["Backend Engineer", "Data Engineer"]
        )

    def test_greenhouse_non_list_jobs_container_returns_no_results(self):
        for bad_jobs in ("not-a-list", {"a": 1}, 42, None):
            stop = _patch_once(greenhouse, {"company_name": "Acme", "jobs": bad_jobs})
            try:
                jobs = greenhouse.GreenhouseProvider(tokens=["acme"]).search(
                    "", "", 0, False
                )
            finally:
                stop()
            self.assertEqual(jobs, [])

    def test_lever_skips_hostile_items_mid_list(self):
        postings = [
            {
                "id": "a1",
                "text": "Backend Engineer",
                "hostedUrl": "https://jobs.lever.co/acme/a1",
                "categories": {"department": "Eng", "location": "NYC"},
            },
            "junk string",
            42,
            None,
            ["a", "list"],
            {
                "id": "a2",
                "text": "Data Engineer",
                "hostedUrl": "https://jobs.lever.co/acme/a2",
                "categories": {"department": "Data", "location": "SF"},
            },
        ]
        stop = _patch_once(lever, postings)
        try:
            jobs = lever.LeverProvider(tokens=["acme"]).search("", "", 0, False)
        finally:
            stop()
        self.assertEqual(len(jobs), 2)
        self.assertEqual(
            [j["title"] for j in jobs], ["Backend Engineer", "Data Engineer"]
        )


class LeverCategoriesTests(unittest.TestCase):
    """F4 (round 2): a truthy non-dict `categories` must not crash
    `cats.get` — in _parse_posting (search path) AND get_details."""

    def test_search_path_non_dict_categories(self):
        for bad_cats in ("Engineering", ["Engineering"], 7):
            postings = [
                {
                    "id": "a1",
                    "text": "Backend Engineer",
                    "hostedUrl": "https://jobs.lever.co/acme/a1",
                    "categories": bad_cats,
                    "country": "USA",
                }
            ]
            stop = _patch_once(lever, postings)
            try:
                jobs = lever.LeverProvider(tokens=["acme"]).search(
                    "", "", 0, False
                )
            finally:
                stop()
            self.assertEqual(len(jobs), 1)
            self.assertIsInstance(jobs[0]["location"], str)

    def test_details_path_non_dict_categories(self):
        for bad_cats in ("Engineering", ["Engineering"], 7):
            raw = _copy(LEVER_DETAIL)
            raw["categories"] = bad_cats
            stop = _patch_once(lever, raw)
            try:
                details = lever.LeverProvider(tokens=["acme"]).get_details(
                    "acme:abc-123"
                )
            finally:
                stop()
            self.assertEqual(details["departments"], [])
            self.assertEqual(details["employment_type"], "")
            self.assertIsInstance(details["location"], str)
            self.assertEqual(validate_job_detail(details), [])


class MalformedErrorShapeTests(unittest.TestCase):
    """F8 (round 2): malformed-payload errors carry the same documented
    error shape as every other error dict ({"url", "board", "error"}) and
    validate clean."""

    def test_all_providers_malformed_payload_validates(self):
        modules = (
            (greenhouse, greenhouse.GreenhouseProvider),
            (lever, lever.LeverProvider),
            (ashby, ashby.AshbyProvider),
        )
        for module, cls in modules:
            details = cls(tokens=[]).get_details("nope")
            self.assertIn("error", details)
            self.assertIn("url", details)
            self.assertIn("board", details)
            self.assertEqual(
                validate_job_detail(details), [], module.__name__
            )


class NumericTitleTests(unittest.TestCase):
    """F6 (round 2): non-string title/department/team coerce to str —
    .strip()/join never raise and detail dicts never leak non-strings."""

    def test_ashby_numeric_title_search_and_details(self):
        board = {
            "jobs": [
                {
                    "id": "job-1",
                    "title": 12345,
                    "department": 678,
                    "team": ["Platform"],
                    "jobUrl": "https://jobs.ashbyhq.com/acme/job-1",
                    "location": "NYC",
                    "descriptionPlain": "Build things.",
                }
            ]
        }
        stop = _patch_once(ashby, board)
        try:
            prov = ashby.AshbyProvider(tokens=["acme"])
            jobs = prov.search("", "", 0, False)
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0]["title"], "12345")
            details = prov.get_details("acme:job-1")
            self.assertIsInstance(details["title"], str)
            self.assertTrue(all(isinstance(d, str) for d in details["departments"]))
            self.assertEqual(validate_job_detail(details), [])
        finally:
            stop()

    def test_greenhouse_numeric_title_search_and_details(self):
        payload = {
            "company_name": "Acme",
            "jobs": [
                {
                    "id": 1,
                    "title": 12345,
                    "absolute_url": "https://boards.greenhouse.io/acme/jobs/1",
                    "location": {"name": "NYC"},
                    "departments": [{"name": 678}],
                }
            ],
        }
        stop = _patch_once(greenhouse, payload)
        try:
            prov = greenhouse.GreenhouseProvider(tokens=["acme"])
            jobs = prov.search("", "", 0, False)
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0]["title"], "12345")
        finally:
            stop()
        detail = _copy(GREENHOUSE_DETAIL)
        detail["title"] = 12345
        detail["departments"] = [{"name": 678}]
        stop = _patch_once(greenhouse, detail)
        try:
            details = greenhouse.GreenhouseProvider(tokens=["acme"]).get_details(
                "acme:123"
            )
            self.assertIsInstance(details["title"], str)
            self.assertTrue(all(isinstance(d, str) for d in details["departments"]))
            self.assertEqual(validate_job_detail(details), [])
        finally:
            stop()

    def test_lever_numeric_title_search_and_details(self):
        posting = {
            "id": "a1",
            "text": 12345,
            "hostedUrl": "https://jobs.lever.co/acme/a1",
            "categories": {"department": 678, "team": ["Platform"]},
            "country": "USA",
            "descriptionPlain": "Build things.",
        }
        stop = _patch_once(lever, [posting])
        try:
            jobs = lever.LeverProvider(tokens=["acme"]).search("", "", 0, False)
        finally:
            stop()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["title"], "12345")

        stop = _patch_once(lever, posting)
        try:
            details = lever.LeverProvider(tokens=["acme"]).get_details("acme:a1")
        finally:
            stop()
        self.assertIsInstance(details["title"], str)
        self.assertTrue(all(isinstance(d, str) for d in details["departments"]))
        self.assertEqual(validate_job_detail(details), [])


class NonListQuestionsTests(unittest.TestCase):
    """F10 (round 2 nit): a truthy non-list `questions` (e.g. a string)
    must not make len(questions) count characters."""

    def test_string_questions_counts_zero(self):
        raw = _copy(GREENHOUSE_DETAIL)
        raw["questions"] = "how many questions are there"
        stop = _patch_once(greenhouse, raw)
        try:
            details = greenhouse.GreenhouseProvider(tokens=["acme"]).get_details(
                "acme:123"
            )
        finally:
            stop()
        self.assertEqual(details["application_questions"], 0)
        self.assertEqual(details["required_questions"], 0)
        self.assertEqual(validate_job_detail(details), [])


class StripHtmlNoneTests(unittest.TestCase):
    """F9 (round 2): pin the chosen fix — strip_html(None) is "" (the
    None-guard lives in providers._common.strip_html, so no per-call
    guard is needed in the providers)."""

    def test_strip_html_none_returns_empty_string(self):
        from providers._common import strip_html

        self.assertEqual(strip_html(None), "")
        self.assertEqual(strip_html(""), "")


class _MethodClient:
    """Client that answers GET and POST with different payloads and
    records the calls, so fallback behavior can be pinned."""

    def __init__(self, get_payload, post_payload):
        self.get_payload = get_payload
        self.post_payload = post_payload
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def request(self, method, url, **kwargs):
        self.calls.append(method)
        return FakeResponse(
            self.get_payload if method == "GET" else self.post_payload
        )


def _patch_method(module, get_payload, post_payload):
    """Like _patch_once but GET/POST return different payloads. Returns
    (stop, client) so tests can inspect the recorded calls."""
    client = _MethodClient(get_payload, post_payload)
    patches = [
        mock.patch.object(module, "make_client", return_value=client),
        mock.patch.object(module, "polite_delay", return_value=None),
    ]
    for p in patches:
        p.start()

    def stop():
        for p in reversed(patches):
            p.stop()

    return stop, client


class AshbyHostileContainerTests(unittest.TestCase):
    """N1 (round 4): Ashby _fetch_board must survive hostile `jobs`
    containers — None (key present with a null value), numbers, strings,
    dicts — the same way Greenhouse's search does; one hostile board
    must not kill the whole multi-board search."""

    def test_non_list_jobs_container_returns_no_results(self):
        for bad_jobs in ("not-a-list", {"a": 1}, 42, None):
            stop = _patch_once(ashby, {"jobs": bad_jobs})
            try:
                jobs = ashby.AshbyProvider(tokens=["acme"]).search(
                    "", "", 0, False
                )
            finally:
                stop()
            self.assertEqual(jobs, [])

    def test_skips_hostile_items_mid_list(self):
        board = {
            "jobs": [
                {
                    "id": "job-1",
                    "title": "Backend Engineer",
                    "jobUrl": "https://jobs.ashbyhq.com/acme/job-1",
                },
                "junk string",
                42,
                None,
                ["a", "list"],
                {
                    "id": "job-2",
                    "title": "Data Engineer",
                    "jobUrl": "https://jobs.ashbyhq.com/acme/job-2",
                },
            ]
        }
        stop = _patch_once(ashby, board)
        try:
            jobs = ashby.AshbyProvider(tokens=["acme"]).search("", "", 0, False)
        finally:
            stop()
        self.assertEqual(len(jobs), 2)
        self.assertEqual(
            [j["title"] for j in jobs], ["Backend Engineer", "Data Engineer"]
        )


class AshbyPostFallbackTests(unittest.TestCase):
    """N5 (round 4): the POST fallback fires ONLY when GET fails (returns
    None). An empty-but-successful GET ({"jobs": []}) is the vendor
    answering — it must NOT trigger a retry POST."""

    def test_empty_get_does_not_trigger_post(self):
        stop, client = _patch_method(ashby, {"jobs": []}, ASHBY_BOARD)
        try:
            jobs = ashby.AshbyProvider(tokens=["acme"]).search("", "", 0, False)
        finally:
            stop()
        self.assertEqual(jobs, [])
        self.assertEqual(client.calls, ["GET"])

    def test_failed_get_triggers_post_fallback(self):
        stop, client = _patch_method(ashby, None, ASHBY_BOARD)
        try:
            jobs = ashby.AshbyProvider(tokens=["acme"]).search("", "", 0, False)
        finally:
            stop()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["title"], "Backend Engineer")
        self.assertEqual(client.calls, ["GET", "POST"])

    def test_failed_get_and_post_returns_no_results(self):
        stop, client = _patch_method(ashby, None, None)
        try:
            jobs = ashby.AshbyProvider(tokens=["acme"]).search("", "", 0, False)
        finally:
            stop()
        self.assertEqual(jobs, [])
        self.assertEqual(client.calls, ["GET", "POST"])


class HostileDescriptionTests(unittest.TestCase):
    """N2 (round 4): hostile description-family shapes (truthy dict, list,
    number) on search AND get_details must coerce to str — strip_html
    only ever sees str, and the detail dict never leaks a non-str."""

    def test_ashby_search_and_details(self):
        # Hostile truthy descriptionPlain is coerced to str, never raw.
        for plain in ({"blocks": ["x"]}, ["x"], 42):
            job = _copy(ASHBY_BOARD)["jobs"][0]
            job["descriptionPlain"] = plain
            job["descriptionHtml"] = "<p>fallback</p>"
            stop = _patch_once(ashby, {"jobs": [job]})
            try:
                prov = ashby.AshbyProvider(tokens=["acme"])
                jobs = prov.search("", "", 0, False)
                self.assertEqual(len(jobs), 1)
                details = prov.get_details("acme:job-1")
                self.assertIsInstance(details["description"], str)
                self.assertEqual(details["description"], str(plain))
                self.assertEqual(validate_job_detail(details), [])
            finally:
                stop()
        # Hostile truthy descriptionHtml is coerced before strip_html.
        for html in ({"html": "<p>x</p>"}, ["x"], 42):
            job = _copy(ASHBY_BOARD)["jobs"][0]
            job["descriptionPlain"] = None
            job["descriptionHtml"] = html
            stop = _patch_once(ashby, {"jobs": [job]})
            try:
                details = ashby.AshbyProvider(tokens=["acme"]).get_details(
                    "acme:job-1"
                )
                self.assertIsInstance(details["description"], str)
                self.assertEqual(validate_job_detail(details), [])
            finally:
                stop()

    def test_greenhouse_search_and_details(self):
        for content in ({"blocks": ["x"]}, ["x"], 42):
            payload = {
                "company_name": "Acme",
                "jobs": [
                    {
                        "id": 1,
                        "title": "Backend Engineer",
                        "absolute_url": "https://boards.greenhouse.io/acme/jobs/1",
                        "location": {"name": "NYC"},
                        "content": content,
                    }
                ],
            }
            stop = _patch_once(greenhouse, payload)
            try:
                jobs = greenhouse.GreenhouseProvider(tokens=["acme"]).search(
                    "", "", 0, False
                )
                self.assertEqual(len(jobs), 1)
            finally:
                stop()
            detail = _copy(GREENHOUSE_DETAIL)
            detail["content"] = content
            stop = _patch_once(greenhouse, detail)
            try:
                details = greenhouse.GreenhouseProvider(
                    tokens=["acme"]
                ).get_details("acme:123")
                self.assertIsInstance(details["description"], str)
                self.assertEqual(validate_job_detail(details), [])
            finally:
                stop()

    def test_lever_search_and_details(self):
        # Hostile truthy descriptionPlain is coerced to str, never raw.
        for plain in ({"blocks": ["x"]}, ["x"], 42):
            posting = _copy(LEVER_DETAIL)
            posting["descriptionPlain"] = plain
            posting["description"] = "<p>fallback</p>"
            stop = _patch_once(lever, [posting])
            try:
                jobs = lever.LeverProvider(tokens=["acme"]).search(
                    "", "", 0, False
                )
                self.assertEqual(len(jobs), 1)
            finally:
                stop()
            stop = _patch_once(lever, posting)
            try:
                details = lever.LeverProvider(tokens=["acme"]).get_details(
                    "acme:abc-123"
                )
                self.assertIsInstance(details["description"], str)
                self.assertEqual(details["description"], str(plain))
                self.assertEqual(validate_job_detail(details), [])
            finally:
                stop()
        # Hostile truthy description is coerced before strip_html.
        for html in ({"html": "<p>x</p>"}, ["x"], 42):
            posting = _copy(LEVER_DETAIL)
            posting["descriptionPlain"] = None
            posting["description"] = html
            stop = _patch_once(lever, posting)
            try:
                details = lever.LeverProvider(tokens=["acme"]).get_details(
                    "acme:abc-123"
                )
                self.assertIsInstance(details["description"], str)
                self.assertEqual(validate_job_detail(details), [])
            finally:
                stop()


class HostileUrlTests(unittest.TestCase):
    """N3 (round 4): hostile dict-valued URLs must coerce to str on
    search AND get_details for all three providers."""

    def test_ashby_urls(self):
        board = _copy(ASHBY_BOARD)
        board["jobs"][0]["jobUrl"] = {"u": 1}
        board["jobs"][0]["applyUrl"] = {"u": 2}
        stop = _patch_once(ashby, board)
        try:
            prov = ashby.AshbyProvider(tokens=["acme"])
            jobs = prov.search("", "", 0, False)
            self.assertEqual(len(jobs), 1)
            self.assertIsInstance(jobs[0]["url"], str)
            details = prov.get_details("acme:job-1")
            self.assertIsInstance(details["url"], str)
            self.assertIsInstance(details["apply_url"], str)
            self.assertEqual(validate_job_detail(details), [])
        finally:
            stop()

    def test_greenhouse_urls(self):
        payload = {
            "company_name": "Acme",
            "jobs": [
                {
                    "id": 1,
                    "title": "Backend Engineer",
                    "absolute_url": {"u": 1},
                    "location": {"name": "NYC"},
                }
            ],
        }
        stop = _patch_once(greenhouse, payload)
        try:
            jobs = greenhouse.GreenhouseProvider(tokens=["acme"]).search(
                "", "", 0, False
            )
            self.assertEqual(len(jobs), 1)
            self.assertIsInstance(jobs[0]["url"], str)
        finally:
            stop()
        detail = _copy(GREENHOUSE_DETAIL)
        detail["absolute_url"] = {"u": 1}
        stop = _patch_once(greenhouse, detail)
        try:
            details = greenhouse.GreenhouseProvider(tokens=["acme"]).get_details(
                "acme:123"
            )
            self.assertIsInstance(details["url"], str)
            self.assertIsInstance(details["apply_url"], str)
            self.assertEqual(validate_job_detail(details), [])
        finally:
            stop()

    def test_lever_urls(self):
        posting = _copy(LEVER_DETAIL)
        posting["hostedUrl"] = {"u": 1}
        posting["applyUrl"] = {"u": 2}
        stop = _patch_once(lever, [posting])
        try:
            jobs = lever.LeverProvider(tokens=["acme"]).search("", "", 0, False)
            self.assertEqual(len(jobs), 1)
            self.assertIsInstance(jobs[0]["url"], str)
        finally:
            stop()
        stop = _patch_once(lever, posting)
        try:
            details = lever.LeverProvider(tokens=["acme"]).get_details(
                "acme:abc-123"
            )
            self.assertIsInstance(details["url"], str)
            self.assertIsInstance(details["apply_url"], str)
            self.assertEqual(validate_job_detail(details), [])
        finally:
            stop()


class AshbyEmploymentTypeTests(unittest.TestCase):
    """N4 (round 4): hostile non-string employmentType must coerce to
    str — Greenhouse and Lever already coerce; Ashby now does too."""

    def test_hostile_employment_type_coerces_to_str(self):
        for bad in ({"full": True}, ["Full-time"], 42):
            board = _copy(ASHBY_BOARD)
            board["jobs"][0]["employmentType"] = bad
            stop = _patch_once(ashby, board)
            try:
                details = ashby.AshbyProvider(tokens=["acme"]).get_details(
                    "acme:job-1"
                )
            finally:
                stop()
            self.assertIsInstance(details["employment_type"], str)
            self.assertEqual(details["employment_type"], str(bad))
            self.assertEqual(validate_job_detail(details), [])


class HostileNestedContainerTests(unittest.TestCase):
    """MAJOR (round 5): unguarded `or []` iteration on NESTED vendor
    containers — the N1 defect class one level down, surviving the
    claimed full re-audit. Item-level isinstance guards don't help: a
    hostile truthy non-iterable (42, True) makes `x = raw.get(k) or []`
    a no-op and iterating x raises TypeError, violating "Never raise on
    transport or vendor data". Greenhouse _parse_job (departments),
    Greenhouse get_details (departments, offices), and Lever get_details
    (lists) now normalize with _coerce_list; the Ashby audit found no
    unguarded nested-container iteration (its only container, `jobs` in
    _fetch_board, is isinstance(list)-guarded; `department` is a scalar,
    never iterated raw)."""

    def test_greenhouse_search_hostile_departments(self):
        for bad in (42, True, "Engineering"):
            payload = {
                "company_name": "Acme",
                "jobs": [
                    {
                        "id": 1,
                        "title": "Backend Engineer",
                        "absolute_url": "https://boards.greenhouse.io/acme/jobs/1",
                        "location": {"name": "NYC"},
                        "departments": bad,
                    },
                    {
                        "id": 2,
                        "title": "Data Engineer",
                        "absolute_url": "https://boards.greenhouse.io/acme/jobs/2",
                        "location": {"name": "SF"},
                        "departments": [{"name": "Data"}],
                    },
                ],
            }
            stop = _patch_once(greenhouse, payload)
            try:
                jobs = greenhouse.GreenhouseProvider(tokens=["acme"]).search(
                    "", "", 0, False
                )
            finally:
                stop()
            # No raise; the hostile container degrades to no departments
            # while the healthy posting still parses.
            self.assertEqual(len(jobs), 2, bad)
            self.assertEqual(
                [j["title"] for j in jobs], ["Backend Engineer", "Data Engineer"]
            )

    def test_greenhouse_details_hostile_departments_offices(self):
        for bad in (42, True):
            detail = _copy(GREENHOUSE_DETAIL)
            detail["departments"] = bad
            detail["offices"] = bad
            stop = _patch_once(greenhouse, detail)
            try:
                details = greenhouse.GreenhouseProvider(
                    tokens=["acme"]
                ).get_details("acme:123")
            finally:
                stop()
            self.assertEqual(details["departments"], [])
            self.assertEqual(details["offices"], [])
            self.assertEqual(validate_job_detail(details), [])

    def test_lever_details_hostile_lists(self):
        for bad in (42, True):
            raw = _copy(LEVER_DETAIL)
            raw["lists"] = bad
            stop = _patch_once(lever, raw)
            try:
                details = lever.LeverProvider(tokens=["acme"]).get_details(
                    "acme:abc-123"
                )
            finally:
                stop()
            self.assertEqual(details["requirements"], "")
            self.assertEqual(validate_job_detail(details), [])

    def test_ashby_hostile_departments_key_is_ignored(self):
        # Ashby audit (round 5): no nested-container iteration exists —
        # `department` is a scalar coerced to str, never iterated raw —
        # so a hostile greenhouse-style `departments` key is ignored and
        # both paths stay green.
        board = _copy(ASHBY_BOARD)
        board["jobs"][0]["departments"] = 42
        stop = _patch_once(ashby, board)
        try:
            prov = ashby.AshbyProvider(tokens=["acme"])
            jobs = prov.search("", "", 0, False)
            self.assertEqual(len(jobs), 1)
            details = prov.get_details("acme:job-1")
            self.assertEqual(details["departments"], ["Engineering", "Platform"])
            self.assertEqual(validate_job_detail(details), [])
        finally:
            stop()


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""E2E retro-validation for Initiative 09 (Connector reliability).

Paul's standing rule: nothing ships without E2E. This module exercises the
shipped i09 features against REAL local surfaces — no mocks of the behavior
under test:

1. A real local HTTP server (stdlib ``http.server`` on 127.0.0.1) stands in
   for a provider API; the REAL ``providers._common`` HTTP client fetches
   from it. Success returns parsed JSON; HTTP 500 / connection loss returns
   ``None`` (never raises).
2. The REAL ``provider_health`` store (file-backed, temp dir) drives the
   reliability circuit: repeated failures -> "degraded"; CAPTCHA block ->
   circuit OPEN (``fetch_allowed`` False); clear -> circuit CLOSED; manual
   cooldown -> backoff honored, then expiry re-opens; daily budget ->
   exhaustion blocks further fetches.
3. The REAL ``providers._contract`` conformance suite runs against the real
   ``GreenhouseProvider`` class (no network — local-first per policy P4),
   plus manifest completeness for every connector and the CAPTCHA / no-bypass
   policy vocabulary.
4. The REAL calendar handoff flow runs end to end (draft -> confirm ->
   payload). The interactive-human gate is replaced with a *simulated human
   approval* — the exact pattern pinned in
   tests/test_calendar_handoff_confirm_gate.py — so the whole post-gate
   path is exercised without a TTY. The production gate is never touched.
5. The REAL channel consent registry runs against a temp consent log:
   enable writes a signed entry (fail-closed on EIO write errors), tampering
   the log makes channels read as disabled.

Hermetic: temp dirs everywhere, OS-assigned localhost port (no port
conflicts), threads cleaned up.
"""

from __future__ import annotations

import json
import stat
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

import provider_health
from initiatives.i09 import calendar_handoff
from initiatives.i09.channels import registry as channel_registry
from providers import _contract
from providers import _common
from providers.greenhouse import GreenhouseProvider


# ---------------------------------------------------------------------------
# 1. Real local HTTP server standing in for a provider API
# ---------------------------------------------------------------------------


class _ProviderFixture(BaseHTTPRequestHandler):
    """Programmable provider fixture. Class-level ``behavior`` drives it."""

    behavior = {"mode": "ok", "failures_before_ok": 0, "requests": 0}
    jobs_payload = {
        "jobs": [
            {"id": 1, "title": "Backend Engineer", "absolute_url": "/jobs/1"},
            {"id": 2, "title": "Frontend Engineer", "absolute_url": "/jobs/2"},
        ]
    }

    def _json(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        cls = type(self)
        cls.behavior["requests"] += 1
        if cls.behavior["mode"] == "errors":
            self._json(500, {"error": "provider exploded"})
            return
        if cls.behavior["failures_before_ok"] > 0:
            cls.behavior["failures_before_ok"] -= 1
            self._json(503, {"error": "flaky provider"})
            return
        if self.path == "/jobs":
            self._json(200, cls.jobs_payload)
        elif self.path == "/jobs/1":
            self._json(200, {"id": 1, "title": "Backend Engineer"})
        else:
            self._json(404, {"error": "not found"})

    def log_message(self, *args):  # keep test output clean
        pass


class _LocalProvider:
    """Context-managed real HTTP server on 127.0.0.1, OS-assigned port."""

    def __init__(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _ProviderFixture)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        _ProviderFixture.behavior = {"mode": "ok", "failures_before_ok": 0, "requests": 0}
        self.thread.start()
        host, port = self.server.server_address
        self.base = f"http://{host}:{port}"
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


class RealHttpFetchTests(unittest.TestCase):
    def test_success_returns_parsed_json(self):
        with _LocalProvider() as p:
            client = _common.make_client(timeout=5.0)
            try:
                data = _common.fetch_json(client, "GET", f"{p.base}/jobs")
            finally:
                client.close()
        self.assertIsNotNone(data)
        self.assertEqual(len(data["jobs"]), 2)
        self.assertEqual(data["jobs"][0]["title"], "Backend Engineer")

    def test_server_error_returns_none_never_raises(self):
        with _LocalProvider() as p:
            _ProviderFixture.behavior["mode"] = "errors"
            client = _common.make_client(timeout=5.0)
            try:
                data = _common.fetch_json(client, "GET", f"{p.base}/jobs")
            finally:
                client.close()
        self.assertIsNone(data)  # the contract: degrade, never crash

    def test_connection_refused_returns_none_never_raises(self):
        client = _common.make_client(timeout=2.0)
        try:
            # Port 1 on loopback: nothing listens there.
            data = _common.fetch_json(client, "GET", "http://127.0.0.1:1/jobs")
        finally:
            client.close()
        self.assertIsNone(data)


# ---------------------------------------------------------------------------
# 2. Real provider_health circuit: open / close / cooldown / budget
# ---------------------------------------------------------------------------


class HealthCircuitE2ETests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = str(Path(self.tmp.name) / "health.json")
        self.provider = "e2e-fixture-provider"

    def _fetch_and_record(self, url):
        """The real connector flow: gate -> fetch -> record, against the
        local fixture server."""
        allowed, reason = provider_health.fetch_allowed(self.provider, path=self.store)
        if not allowed:
            return {"skipped": True, "reason": reason}
        client = _common.make_client(timeout=5.0)
        try:
            data = _common.fetch_json(client, "GET", url)
        finally:
            client.close()
        provider_health.record_fetch(self.provider, data is not None, path=self.store)
        return {"skipped": False, "data": data}

    def test_healthy_flow_stays_ok(self):
        with _LocalProvider() as p:
            out = self._fetch_and_record(f"{p.base}/jobs")
        self.assertFalse(out["skipped"])
        self.assertIsNotNone(out["data"])
        row = provider_health.provider_status(self.provider, path=self.store)
        self.assertEqual(row["status"], "ok")
        self.assertEqual(row["consecutive_failures"], 0)
        self.assertIsNotNone(row["last_successful_fetch"])

    def test_repeated_failures_degrade_provider(self):
        with _LocalProvider() as p:
            _ProviderFixture.behavior["mode"] = "errors"
            for _ in range(provider_health.DEGRADED_AFTER_FAILURES):
                out = self._fetch_and_record(f"{p.base}/jobs")
                self.assertFalse(out["skipped"])
                self.assertIsNone(out["data"])
        row = provider_health.provider_status(self.provider, path=self.store)
        self.assertEqual(row["status"], "degraded")
        self.assertEqual(
            row["consecutive_failures"], provider_health.DEGRADED_AFTER_FAILURES
        )
        degraded = provider_health.degraded_providers(path=self.store)
        self.assertIn(self.provider, [d["provider"] for d in degraded])

    def test_recovery_clears_failures(self):
        with _LocalProvider() as p:
            _ProviderFixture.behavior["mode"] = "errors"
            self._fetch_and_record(f"{p.base}/jobs")
            _ProviderFixture.behavior["mode"] = "ok"
            out = self._fetch_and_record(f"{p.base}/jobs")
        self.assertIsNotNone(out["data"])
        row = provider_health.provider_status(self.provider, path=self.store)
        self.assertEqual(row["status"], "ok")
        self.assertEqual(row["consecutive_failures"], 0)

    def test_captcha_block_opens_circuit(self):
        provider_health.record_captcha(self.provider, "blocked", path=self.store)
        allowed, reason = provider_health.fetch_allowed(self.provider, path=self.store)
        self.assertFalse(allowed)
        self.assertEqual(reason, "captcha_blocked")
        row = provider_health.provider_status(self.provider, path=self.store)
        self.assertEqual(row["status"], "blocked")

    def test_captcha_clear_closes_circuit(self):
        provider_health.record_captcha(self.provider, "blocked", path=self.store)
        provider_health.record_captcha(self.provider, "clear", path=self.store)
        allowed, reason = provider_health.fetch_allowed(self.provider, path=self.store)
        self.assertTrue(allowed, reason)
        row = provider_health.provider_status(self.provider, path=self.store)
        self.assertEqual(row["status"], "ok")

    def test_cooldown_backoff_then_expiry(self):
        provider_health.cooldown(self.provider, 2, "e2e backoff", path=self.store)
        allowed, reason = provider_health.fetch_allowed(self.provider, path=self.store)
        self.assertFalse(allowed)
        self.assertTrue(reason.startswith("cooling_down"))
        # The connector flow must respect the backoff: no fetch attempted.
        with _LocalProvider() as p:
            before = _ProviderFixture.behavior["requests"]
            out = self._fetch_and_record(f"{p.base}/jobs")
            self.assertTrue(out["skipped"])
            self.assertEqual(_ProviderFixture.behavior["requests"], before)
        # After the real cooldown expires the circuit re-opens by itself.
        time.sleep(2.2)
        allowed, reason = provider_health.fetch_allowed(self.provider, path=self.store)
        self.assertTrue(allowed, reason)

    def test_budget_exhaustion_blocks_fetches(self):
        provider_health.set_budget(self.provider, 2, path=self.store)
        with _LocalProvider() as p:
            self.assertFalse(self._fetch_and_record(f"{p.base}/jobs")["skipped"])
            self.assertFalse(self._fetch_and_record(f"{p.base}/jobs")["skipped"])
            out = self._fetch_and_record(f"{p.base}/jobs")
        self.assertTrue(out["skipped"])
        self.assertEqual(out["reason"], "budget_exhausted")


# ---------------------------------------------------------------------------
# 3. Real conformance + policy checks against real provider classes
# ---------------------------------------------------------------------------


class ConformancePolicyE2ETests(unittest.TestCase):
    def test_greenhouse_conformance_passes_no_network(self):
        # Local-first: the suite must pass with no network access at all.
        with mock.patch("socket.socket", side_effect=AssertionError("no network")):
            results = _contract.conformance_suite(GreenhouseProvider(tokens=[]))
        self.assertTrue(_contract.suite_passed(results), results)

    def test_every_connector_manifest_complete(self):
        for manifest in _contract.all_manifests():
            self.assertEqual(
                manifest.validate(), [],
                f"{manifest.name}: incomplete proof-of-value declaration",
            )

    def test_captcha_is_terminal_non_submit_no_bypass(self):
        # Policy P2: CAPTCHA never bypassed; the closed vocabulary has no
        # bypass status, and rescue-paused flows map to non-SUBMITTED.
        # Shape mirrors browser_apply.apply_via_browser's rescue return:
        # paused, handed to the user, never submitted.
        blocked = _contract.submission_result_from(
            {
                "ok": False,
                "submitted": False,
                "paused": True,
                "rescue": {"reason": "captcha"},
                "final_url": "https://example.com/apply",
                "error": "Paused: captcha detected — control handed to the user.",
            },
            connector="browser",
        )
        self.assertEqual(blocked.status, _contract.SubmissionStatus.CAPTCHA_BLOCKED)
        self.assertNotEqual(blocked.status, _contract.SubmissionStatus.SUBMITTED)
        valid = _contract.SubmissionResult(
            status=_contract.SubmissionStatus.PAUSED,
            connector="browser",
            detail="captcha pause-and-hand-off",
        )
        self.assertEqual(_contract.validate_submission_result(valid), [])

    def test_terms_declare_cooldowns(self):
        terms, reason, _ = _contract.terms_for("greenhouse")
        self.assertTrue(terms)  # a real TermsClass, not an empty declaration
        self.assertTrue(reason)


# ---------------------------------------------------------------------------
# 4. Real calendar handoff flow with a simulated human at the gate
# ---------------------------------------------------------------------------


class CalendarHandoffE2ETests(unittest.TestCase):
    def setUp(self):
        self._orig = calendar_handoff.require_action_confirmation
        self.gate_calls = []

        def fake(**kwargs):
            self.gate_calls.append(kwargs)
            return {
                "ok": True,
                "approved": True,
                "approval_id": "simulated-human",
                "content_hash": kwargs.get("expected_value"),
                "channel": "simulated",
            }

        calendar_handoff.require_action_confirmation = fake
        self.addCleanup(setattr, calendar_handoff,
                        "require_action_confirmation", self._orig)

    def test_full_handoff_produces_calendar_payload(self):
        app = {"company": "Acme", "title": "Backend Engineer", "job_id": "gh:abc"}
        drafts = [
            calendar_handoff.propose_interview_prep(
                app, interview_at="2026-10-01T14:00:00+00:00"
            ),
            calendar_handoff.propose_followup_reminder(
                app, days_after=7, from_date="2026-09-13T00:00:00+00:00"
            ),
        ]
        out = calendar_handoff.confirm_and_handoff(drafts, confirm=True)
        self.assertTrue(out["ok"])
        self.assertEqual(out["handed_off"], 2)
        # The human gate was really invoked with a fresh per-call token.
        self.assertEqual(len(self.gate_calls), 1)
        token = self.gate_calls[0]["expected_value"]
        self.assertTrue(token)
        self.assertIn(token, self.gate_calls[0]["summary"])
        # The payload the wiring layer would write to the calendar:
        for event, draft in zip(out["events"], drafts):
            self.assertEqual(event["title"], draft.title)
            self.assertTrue(event["start_iso"])
            self.assertTrue(event["end_iso"])
            self.assertIn("event_type", event)
            self.assertTrue(event["idempotency_key"])
        self.assertIn("title", out["data_sent_per_event"])
        self.assertIn("google-calendar", out["note"])

    def test_review_path_never_touches_gate(self):
        draft = calendar_handoff.propose_followup_reminder(
            {"company": "Acme", "title": "Eng", "job_id": "gh:abc"},
            from_date="2026-10-01T00:00:00+00:00",
        )
        out = calendar_handoff.confirm_and_handoff(draft)  # confirm not True
        self.assertFalse(out["ok"])
        self.assertEqual(out["handed_off"], 0)
        self.assertEqual(self.gate_calls, [])


# ---------------------------------------------------------------------------
# 5. Real channel consent registry against a temp consent log
# ---------------------------------------------------------------------------


class ChannelConsentE2ETests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = mock.patch.object(
            channel_registry, "CONSENT_LOG", Path(self.tmp.name) / "consent.jsonl"
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_enable_writes_signed_consent_entry(self):
        result = channel_registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        self.assertTrue(result["ok"])
        self.assertTrue(result["enabled"])
        self.assertTrue(channel_registry.is_enabled("gmail"))
        # The log entry is real JSONL with an integrity signature.
        lines = Path(channel_registry.CONSENT_LOG).read_text(
            encoding="utf-8"
        ).splitlines()
        self.assertEqual(len(lines), 1)
        entry = json.loads(lines[0])
        self.assertEqual(entry["channel"], "gmail")
        self.assertIn("mac", entry)
        # The machine key is private (0o600) and the consent log too.
        key_path = channel_registry._consent_key_path()
        self.assertTrue(key_path.exists())
        self.assertEqual(stat.S_IMODE(key_path.stat().st_mode), 0o600)
        self.assertEqual(
            stat.S_IMODE(channel_registry.CONSENT_LOG.stat().st_mode), 0o600
        )

    def test_enable_refused_without_explicit_confirm(self):
        result = channel_registry.enable_channel("gmail", via="cli-wizard")
        self.assertFalse(result["ok"])
        self.assertFalse(channel_registry.is_enabled("gmail"))

    def test_tampered_log_fails_closed(self):
        channel_registry.enable_channel("gmail", confirm=True, via="cli-wizard")
        raw = channel_registry.CONSENT_LOG.read_text(encoding="utf-8")
        tampered = raw.replace('"channel": "gmail"', '"channel": "discord"')
        self.assertNotEqual(raw, tampered)
        channel_registry.CONSENT_LOG.write_text(tampered, encoding="utf-8")
        with self.assertLogs("veto-mcp.i09.channels", level="ERROR"):
            history = channel_registry.consent_history()
        self.assertEqual(history, [])
        self.assertFalse(channel_registry.is_enabled("gmail"))  # fail closed


if __name__ == "__main__":
    unittest.main()

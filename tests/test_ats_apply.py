"""Unit tests for ats_apply.py — direct ATS application submission.

No network access: httpx.Client is mocked everywhere. Compliance state
is pointed at a temp file.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import compliance

import ats_apply


def _job_id(board: str, payload: str) -> str:
    token = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    return f"{board}:{token}"


APPLICANT = {
    "full_name": "Ada Lovelace",
    "email": "ada@example.com",
    "phone": "+1 555-0100",
    "location": "New York, NY",
    "linkedin_url": "https://www.linkedin.com/in/adalovelace",
    "website": "",
}

VERIFIED_SPEC = {
    "status": "verified",
    "endpoint": "https://example.invalid/submit",
    "method": "POST",
    "locator_field": "jobPostingId",
    "reason": "test fixture",
    "sources": [],
}


def _no_bytes(obj) -> bool:
    """Recursively assert no bytes objects anywhere in a structure."""
    if isinstance(obj, bytes):
        return False
    if isinstance(obj, dict):
        return all(_no_bytes(v) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return all(_no_bytes(v) for v in obj)
    return True


class TestRegistry(unittest.TestCase):
    def test_no_board_currently_verified(self):
        # 2026-09-10 verification: Ashby 401s, Lever needs a Lever-issued
        # key, Greenhouse needs an employer Job Board API key.
        for board in ("ashby", "lever", "greenhouse"):
            self.assertFalse(ats_apply.can_apply_direct(board), board)

    def test_unknown_board_not_direct(self):
        self.assertFalse(ats_apply.can_apply_direct("workday"))

    def test_endpoint_status_documents_blockers(self):
        for board in ("ashby", "lever", "greenhouse"):
            info = ats_apply.endpoint_status(board)
            self.assertNotEqual(info["status"], "verified")
            self.assertTrue(info["reason"])
            self.assertTrue(info["sources"])


class TestPreview(unittest.TestCase):
    def setUp(self):
        self.job = {"id": _job_id("ashby", "ashby:posting-123"),
                    "board": "ashby", "title": "Engineer"}

    def test_preview_makes_zero_http_calls(self):
        with mock.patch.object(ats_apply.httpx, "Client") as client_cls:
            preview = ats_apply.apply_direct(
                "ashby", self.job, APPLICANT,
                resume_path="/tmp/resume.pdf", cover_letter="Hi",
                confirm=False)
        client_cls.assert_not_called()
        self.assertEqual(preview["mode"], "preview")
        self.assertEqual(preview["network_calls"], 0)
        self.assertEqual(preview["board"], "ashby")
        self.assertIn("endpoint", preview)
        self.assertIn("fields_that_would_be_sent", preview)
        self.assertIn("disclosure", preview)
        self.assertTrue(_no_bytes(preview))

    def test_preview_field_names_but_no_resume_bytes(self):
        preview = ats_apply.apply_direct("lever", self.job, APPLICANT,
                                         resume_path="/tmp/resume.pdf")
        fields = preview["fields_that_would_be_sent"]
        self.assertEqual(fields["full_name"], "Ada Lovelace")
        self.assertEqual(fields["email"], "ada@example.com")
        # Filename may be mentioned; raw bytes never are.
        self.assertTrue(_no_bytes(fields))
        self.assertNotIn("bytes", json.dumps(preview).lower()
                         .replace("bytes never included", ""))

    def test_unconfirmed_submit_makes_zero_calls(self):
        # confirm=True but dry_run=True still means preview-only.
        with mock.patch.object(ats_apply.httpx, "Client") as client_cls:
            out = ats_apply.apply_direct(
                "ashby", self.job, APPLICANT, confirm=True, dry_run=True)
        client_cls.assert_not_called()
        self.assertEqual(out["mode"], "preview")

    def test_unknown_board_raises(self):
        with self.assertRaises(ValueError):
            ats_apply.apply_direct("workday", self.job, APPLICANT)

    def test_malformed_job_id_returns_error(self):
        out = ats_apply.apply_direct(
            "ashby", {"id": "not-a-valid-id"}, APPLICANT, confirm=True)
        self.assertFalse(out.get("ok", True))
        self.assertIn("error", out)


class TestConfirmedUnverified(unittest.TestCase):
    def test_confirmed_submit_unverified_board_no_network(self):
        job = {"id": _job_id("ashby", "ashby:posting-123"), "board": "ashby"}
        with mock.patch.object(ats_apply.httpx, "Client") as client_cls:
            out = ats_apply.apply_direct(
                "ashby", job, APPLICANT, confirm=True, dry_run=False)
        client_cls.assert_not_called()
        self.assertFalse(out["ok"])
        self.assertFalse(out["direct_apply_available"])
        self.assertIn("error", out)
        self.assertIn("disclosure", out)

    def test_confirmed_submit_greenhouse_reports_key_requirement(self):
        job = {"id": _job_id("greenhouse", "stripe:12345"),
               "board": "greenhouse"}
        out = ats_apply.apply_direct(
            "greenhouse", job, APPLICANT, confirm=True, dry_run=False)
        self.assertFalse(out["ok"])
        self.assertEqual(out["endpoint_status"], "key_required")


class TestComplianceGating(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.cpath = Path(self.tmp.name) / "compliance.json"
        self.addCleanup(self.tmp.cleanup)
        self._patch_ep = mock.patch.dict(
            ats_apply._ENDPOINTS, {"testboard": dict(VERIFIED_SPEC)})
        self._patch_ep.start()
        self.addCleanup(self._patch_ep.stop)
        self._patch_file = mock.patch.object(
            compliance, "COMPLIANCE_FILE", self.cpath)
        self._patch_file.start()
        self.addCleanup(self._patch_file.stop)
        self.job = {"id": _job_id("testboard", "testboard:posting-9"),
                    "board": "testboard"}

    def _write_state(self, applies: int):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.cpath.write_text(json.dumps({
            "mode": "standard",
            "counters": {today: {"applies": applies}},
            "blocks": {},
        }))

    def _mock_client(self, status=200, payload=None, text=""):
        resp = mock.MagicMock()
        resp.status_code = status
        resp.text = text
        resp.json.return_value = payload or {}
        client = mock.MagicMock()
        client.post.return_value = resp
        client.__enter__.return_value = client
        return client

    def test_daily_cap_blocks_confirmed_submit(self):
        self._write_state(applies=5)  # == DEFAULT_DAILY_APPLY_CAP
        client = self._mock_client()
        client.post.side_effect = AssertionError("must not POST when capped")
        with mock.patch.object(ats_apply.httpx, "Client",
                               return_value=client):
            out = ats_apply.apply_direct(
                "testboard", self.job, APPLICANT,
                confirm=True, dry_run=False)
        self.assertFalse(out["ok"])
        self.assertIn("cap", out["error"].lower())

    def test_successful_submit_records_application(self):
        self._write_state(applies=0)
        client = self._mock_client(
            status=200, payload={"applicationId": "app-1"})
        with mock.patch.object(ats_apply.httpx, "Client",
                               return_value=client):
            out = ats_apply.apply_direct(
                "testboard", self.job, APPLICANT,
                resume_path=None, cover_letter="Hello",
                confirm=True, dry_run=False)
        self.assertTrue(out["ok"])
        self.assertEqual(out["status_code"], 200)
        self.assertEqual(out["confirmation"], "app-1")
        state = json.loads(self.cpath.read_text())
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.assertEqual(state["counters"][today]["applies"], 1)

    def test_error_body_is_truncated(self):
        self._write_state(applies=0)
        client = self._mock_client(status=500, text="X" * 5000)
        client.post.return_value.json.side_effect = ValueError("no json")
        with mock.patch.object(ats_apply.httpx, "Client",
                               return_value=client):
            out = ats_apply.apply_direct(
                "testboard", self.job, APPLICANT,
                confirm=True, dry_run=False)
        self.assertFalse(out["ok"])
        self.assertLessEqual(len(out["error"]), 520)
        self.assertTrue(_no_bytes(out))


class FakeMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def deco(fn):
            self.tools[fn.__name__] = fn
            return fn
        return deco


class TestRegisterTools(unittest.TestCase):
    def test_apply_via_ats_registered_with_docstring(self):
        mcp = FakeMCP()
        ats_apply.register_tools(mcp)
        fn = mcp.tools["apply_via_ats"]
        self.assertIn("job_id", fn.__doc__)
        self.assertIn("confirm", fn.__doc__)

    def test_apply_via_ats_preview_no_network(self):
        fake_server = types.ModuleType("server")
        fake_server._load_saved_profile = lambda: dict(APPLICANT)
        with mock.patch.dict(sys.modules, {"server": fake_server}), \
             mock.patch.object(ats_apply.httpx, "Client") as client_cls:
            mcp = FakeMCP()
            ats_apply.register_tools(mcp)
            out = mcp.tools["apply_via_ats"](
                job_id=_job_id("ashby", "ashby:posting-123"))
        client_cls.assert_not_called()
        self.assertEqual(out["mode"], "preview")
        self.assertEqual(out["board"], "ashby")


class TestRegisterCli(unittest.TestCase):
    def test_apply_direct_command_flags(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        handler = ats_apply.register_cli(sub)["apply-direct"]
        self.assertTrue(callable(handler))
        args = parser.parse_args(
            ["apply-direct", "--job-id", "ashby:abc123", "--confirm"])
        self.assertEqual(args.job_id, "ashby:abc123")
        self.assertTrue(args.confirm)

    def test_apply_direct_preview_handler_exit_zero(self):
        fake_server = types.ModuleType("server")
        fake_server._load_saved_profile = lambda: dict(APPLICANT)
        fake_server._decode_job_id = lambda jid: ("ashby", "posting-123")
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        handler = ats_apply.register_cli(sub)["apply-direct"]
        args = parser.parse_args(
            ["apply-direct", "--job-id", _job_id("ashby", "ashby:1")])
        with mock.patch.dict(sys.modules, {"server": fake_server}), \
             mock.patch.object(ats_apply.httpx, "Client") as client_cls:
            rc = handler(args)
        client_cls.assert_not_called()
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()

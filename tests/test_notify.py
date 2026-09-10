#!/usr/bin/env python3
"""Tests for the notification module (notify.py).

Stdlib unittest only. No network (urllib is mocked), no real env
dependence (env vars monkeypatched), log file redirected to a temp dir.

Run:  cd ~/workspace/job-apply-mcp && python3 -m unittest discover -s tests -v
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import notify


class _FakeResponse:
    def __init__(self, status=200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class TestSend(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.log = Path(self.tmp.name) / "notifications.jsonl"
        self.addCleanup(self.tmp.cleanup)
        self.log_patch = mock.patch.object(notify, "NOTIFY_LOG", self.log)
        self.log_patch.start()
        self.addCleanup(self.log_patch.stop)
        # Start with no sinks configured.
        self.env_patch = mock.patch.dict(os.environ, {}, clear=False)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        os.environ.pop("NTFY_TOPIC", None)
        os.environ.pop("JOB_MCP_WEBHOOK", None)

    def _log_entries(self):
        return [
            json.loads(line)
            for line in self.log.read_text(encoding="utf-8").splitlines()
        ]

    def test_always_writes_local_log(self):
        result = notify.send("Hi", "body text")
        self.assertEqual(result, {"ok": True, "delivered_via": ["log"]})
        entries = self._log_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["title"], "Hi")
        self.assertEqual(entries[0]["body"], "body text")
        self.assertIn("ts", entries[0])

    def test_ntfy_delivery(self):
        os.environ["NTFY_TOPIC"] = "my-topic"
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["title"] = req.headers.get("Title")
            captured["timeout"] = timeout
            return _FakeResponse(200)

        with mock.patch("urllib.request.urlopen", fake_urlopen):
            result = notify.send("T", "B")
        self.assertEqual(
            result["delivered_via"], ["log", "ntfy"]
        )
        self.assertEqual(captured["url"], "https://ntfy.sh/my-topic")
        self.assertEqual(captured["title"], "T")
        self.assertEqual(captured["timeout"], 5)

    def test_webhook_delivery(self):
        os.environ["JOB_MCP_WEBHOOK"] = "https://example.com/hook"
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["payload"] = json.loads(req.data.decode("utf-8"))
            return _FakeResponse(200)

        with mock.patch("urllib.request.urlopen", fake_urlopen):
            result = notify.send("T", "B")
        self.assertEqual(result["delivered_via"], ["log", "webhook"])
        self.assertEqual(captured["url"], "https://example.com/hook")
        self.assertEqual(captured["payload"]["title"], "T")
        self.assertEqual(captured["payload"]["body"], "B")

    def test_channel_selection(self):
        os.environ["NTFY_TOPIC"] = "my-topic"
        os.environ["JOB_MCP_WEBHOOK"] = "https://example.com/hook"
        with mock.patch(
            "urllib.request.urlopen", return_value=_FakeResponse(200)
        ):
            ntfy_only = notify.send("T", "B", channel="ntfy")
            webhook_only = notify.send("T", "B", channel="webhook")
        self.assertEqual(ntfy_only["delivered_via"], ["log", "ntfy"])
        self.assertEqual(webhook_only["delivered_via"], ["log", "webhook"])

    def test_sink_failure_never_raises(self):
        os.environ["NTFY_TOPIC"] = "my-topic"
        os.environ["JOB_MCP_WEBHOOK"] = "https://example.com/hook"

        def boom(req, timeout=None):
            raise OSError("network down")

        with mock.patch("urllib.request.urlopen", boom):
            result = notify.send("T", "B")  # must not raise
        self.assertEqual(result, {"ok": True, "delivered_via": ["log"]})

    def test_non_2xx_is_not_counted(self):
        os.environ["NTFY_TOPIC"] = "my-topic"
        with mock.patch(
            "urllib.request.urlopen", return_value=_FakeResponse(500)
        ):
            result = notify.send("T", "B")
        self.assertEqual(result["delivered_via"], ["log"])


if __name__ == "__main__":
    unittest.main()

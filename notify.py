#!/usr/bin/env python3
"""Outbound notifications for the job-apply MCP server.

``send(title, body, channel="auto")`` always appends the notification
to a local JSONL log (``notifications.jsonl`` next to this project, one
JSON object per line) and additionally delivers through whichever
sinks are configured via the environment:

* ``NTFY_TOPIC`` — POSTs to ``https://ntfy.sh/<topic>`` (free push
  notifications to your phone via the ntfy app), title in the
  ``Title`` header.
* ``JOB_MCP_WEBHOOK`` — POSTs ``{"title", "body", "ts"}`` as JSON to
  the given URL (Discord/Slack/custom webhooks).

Delivery is stdlib-only (``urllib``), best-effort with a 5s timeout,
and ``send`` never raises: a failing sink is simply left out of
``delivered_via``.

NOTE on .gitignore: this module deliberately does not edit it. The
notification log can contain job titles and company names, so add
``notifications.jsonl`` to ``.gitignore`` if you want it ignored.
"""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
NOTIFY_LOG = BASE_DIR / "notifications.jsonl"

_NTFY_BASE = "https://ntfy.sh"
_TIMEOUT_SECONDS = 5


def _post_ntfy(topic: str, title: str, body: str) -> bool:
    """POST to ntfy.sh. Returns True on 2xx; never raises."""
    try:
        req = urllib.request.Request(
            f"{_NTFY_BASE}/{topic}",
            data=body.encode("utf-8"),
            headers={"Title": title},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def _post_webhook(url: str, title: str, body: str) -> bool:
    """POST JSON to a generic webhook. Returns True on 2xx; never raises."""
    try:
        payload = json.dumps(
            {
                "title": title,
                "body": body,
                "ts": datetime.now(timezone.utc).isoformat(),
            },
            ensure_ascii=False,
        ).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def send(title: str, body: str, channel: str = "auto") -> dict:
    """Send a notification. Never raises.

    Always writes to the local JSONL log; also delivers via ntfy and/or
    webhook when ``NTFY_TOPIC`` / ``JOB_MCP_WEBHOOK`` are set and the
    channel allows it (``"auto"`` tries everything configured).

    Returns ``{"ok": True, "delivered_via": [...]}`` where the list is a
    subset of ``["log", "ntfy", "webhook"]``.
    """
    delivered: list[str] = []
    title, body = str(title), str(body)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "title": title,
        "body": body,
        "channel": channel,
    }
    try:
        with NOTIFY_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        delivered.append("log")
    except Exception:
        pass

    if channel in ("auto", "ntfy"):
        topic = os.environ.get("NTFY_TOPIC", "").strip()
        if topic and _post_ntfy(topic, title, body):
            delivered.append("ntfy")

    if channel in ("auto", "webhook"):
        webhook = os.environ.get("JOB_MCP_WEBHOOK", "").strip()
        if webhook and _post_webhook(webhook, title, body):
            delivered.append("webhook")

    return {"ok": True, "delivered_via": delivered}

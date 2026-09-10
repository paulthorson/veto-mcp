"""Shared helpers for the job-board provider modules.

Duplicates the tiny pieces providers need from ``server.py`` so the
providers package stays independent (server.py imports providers, never
the reverse).
"""

from __future__ import annotations

import base64
import logging
import os
import random
import re
import time
from typing import Any

import httpx
from bs4 import BeautifulSoup

log = logging.getLogger("job-apply-mcp.providers")

USER_AGENTS = [
    
    "VETO-REDACTED-UA"
    "",
    "VETO-REDACTED-UA"
    "",
    "VETO-REDACTED-UA",
    "VETO-REDACTED-UA"
    "",
]

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def sanitize_proxy_env() -> None:
    """Drop no_proxy entries that httpx cannot parse.

    Some environments ship entries like ``*[::1]`` or bracketed IPv6
    (``[::1]``). httpx turns any entry it doesn't recognize as IPv4/IPv6
    into an ``all://*<host>`` pattern, and ``URLPattern`` then crashes at
    client init ("Invalid port"). The unbracketed equivalents (``::1``)
    are kept and parsed correctly, so dropping the problematic forms is
    safe.
    """
    for var in ("no_proxy", "NO_PROXY"):
        val = os.environ.get(var)
        if not val:
            continue
        kept = [
            entry
            for entry in val.split(",")
            if "*" not in entry and "[" not in entry and "]" not in entry
        ]
        os.environ[var] = ",".join(kept)


sanitize_proxy_env()


def make_client(timeout: float = 20.0) -> httpx.Client:
    """Return an httpx client with a rotated user agent."""
    return httpx.Client(
        headers={
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json,text/html,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
        timeout=timeout,
        follow_redirects=True,
    )


def polite_delay(min_s: float = 1.0, max_s: float = 2.0) -> None:
    """Sleep 1-2s between requests to respect rate limits."""
    delay = random.uniform(min_s, max_s)
    log.debug("Politeness delay: %.2fs", delay)
    time.sleep(delay)


def encode_payload(payload: str) -> str:
    """base64url-encode ``payload`` with padding stripped (matches server.py)."""
    return (
        base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")
    )


def decode_payload(token: str) -> str:
    """Decode a stripped-padding base64url token back to the payload string."""
    padded = token + "=" * (-len(token) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")


def make_job_id(board: str, payload: str) -> str:
    """Build a self-describing job id: ``<board>:<base64url(payload)>``."""
    return f"{board}:{encode_payload(payload)}"


def prettify_token(token: str) -> str:
    """Turn a board token like ``"robinhood"`` into ``"Robinhood"``."""
    return token.replace("-", " ").replace("_", " ").strip().title()


def fetch_json(
    client: httpx.Client, method: str, url: str, **kwargs: Any
) -> Any | None:
    """Safe JSON fetch: returns the parsed body, or None on any failure.

    Logs the failure but never raises, so one dead board can't crash a
    multi-board search.
    """
    try:
        resp = client.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        log.warning("fetch_json failed for %s %s: %s", method.upper(), url, exc)
        return None


def strip_html(html: str | None) -> str:
    """Convert an HTML fragment to plain text ("" for empty input)."""
    if not html:
        return ""
    text = BeautifulSoup(html, "lxml").get_text("\n", strip=True)
    # Collapse runs of blank lines left over from block elements.
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def words_match(text: str, words: list[str]) -> bool:
    """True when every query word appears (case-insensitively) in ``text``."""
    lowered = text.lower()
    return all(word in lowered for word in words)

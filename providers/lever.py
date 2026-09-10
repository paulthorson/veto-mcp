"""Lever board provider (public API, no auth).

List:   GET https://api.lever.co/v0/postings/{company}?mode=json
Detail: GET https://api.lever.co/v0/postings/{company}/{posting_id}?mode=json

Board tokens are read from providers/boards.json ("lever" key). Each token
was verified live against the API; dead ones were dropped.

Caveat: Lever's public API is per-company and tokens churn as employers
join/leave Lever. A token that 404s is skipped gracefully (logged).
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any

from providers._common import (
    fetch_json,
    make_client,
    make_job_id,
    polite_delay,
    prettify_token,
    strip_html,
    words_match,
)

log = logging.getLogger("job-apply-mcp.providers.lever")

_BOARDS_FILE = Path(__file__).resolve().parent / "boards.json"


def _load_tokens() -> list[str]:
    try:
        return list(json.loads(_BOARDS_FILE.read_text(encoding="utf-8"))["lever"])
    except Exception as exc:  # missing/corrupt file: degrade, don't crash
        log.warning("Could not load board tokens from %s: %s", _BOARDS_FILE, exc)
        return []


class LeverProvider:
    """Search jobs across curated Lever-hosted company boards."""

    name = "lever"
    LIST_URL = "https://api.lever.co/v0/postings/{company}?mode=json"
    DETAIL_URL = "https://api.lever.co/v0/postings/{company}/{posting_id}?mode=json"

    def __init__(self, tokens: list[str] | None = None) -> None:
        self.tokens = tokens if tokens is not None else _load_tokens()

    # -- search ---------------------------------------------------------
    def search(
        self, query: str, location: str, limit: int, remote_only: bool
    ) -> list[dict[str, Any]]:
        query_words = query.lower().split()
        location = (location or "").lower()
        jobs: list[dict[str, Any]] = []
        tokens = self.tokens
        per_token = max(1, math.ceil(limit / max(1, len(tokens)))) if limit else 0

        with make_client() as client:
            for i, company in enumerate(tokens):
                if limit and len(jobs) >= limit:
                    break
                if i:
                    polite_delay()
                postings = fetch_json(
                    client, "GET", self.LIST_URL.format(company=company)
                )
                if not postings or not isinstance(postings, list):
                    continue
                taken = 0
                for raw in postings:
                    if limit and (len(jobs) >= limit or taken >= per_token):
                        break
                    job = self._parse_posting(raw, company)
                    if not job:
                        continue
                    if query_words and not words_match(job["_search_text"], query_words):
                        continue
                    if location and location not in job["location"].lower():
                        continue
                    if remote_only and "remote" not in (
                        job["location"] + " " + job["_workplace"]
                    ).lower():
                        continue
                    taken += 1
                    del job["_search_text"]
                    del job["_workplace"]
                    jobs.append(job)
        log.info(
            "Lever: %d jobs for %r in %r across %d boards",
            len(jobs),
            query,
            location,
            len(tokens),
        )
        return jobs

    def _parse_posting(
        self, raw: dict[str, Any], company: str
    ) -> dict[str, Any] | None:
        posting_id = raw.get("id")
        title = (raw.get("text") or "").strip()
        if not posting_id or not title:
            return None
        cats = raw.get("categories") or {}
        department = cats.get("department") or ""
        commitment = cats.get("commitment") or ""
        loc = cats.get("location") or raw.get("country") or "Unknown"
        workplace = (raw.get("workplaceType") or "").lower()
        url = raw.get("hostedUrl") or raw.get("applyUrl") or ""
        payload = f"{company}:{posting_id}"
        snippet_bits = [t for t in (title, department, commitment, loc) if t]
        return {
            "id": make_job_id(self.name, payload),
            "title": title,
            "company": prettify_token(company),
            "location": loc,
            "url": url,
            "board": self.name,
            "snippet": " — ".join(snippet_bits)[:400],
            # internal: query matching + remote matching text
            "_search_text": f"{title} {department} {commitment}",
            "_workplace": workplace,
        }

    # -- details --------------------------------------------------------
    def get_details(self, payload: str) -> dict[str, Any]:
        """Full details for a posting. ``payload`` is the decoded id payload
        (``"company:posting_id"``)."""
        company, sep, posting_id = payload.partition(":")
        if not sep or not company or not posting_id:
            return {"board": self.name, "payload": payload,
                    "error": f"Malformed Lever payload: {payload!r}"}
        with make_client() as client:
            polite_delay()
            raw = fetch_json(
                client,
                "GET",
                self.DETAIL_URL.format(company=company, posting_id=posting_id),
            )
        if not raw:
            return {
                "url": "",
                "board": self.name,
                "error": f"Lever posting {payload!r} not found or fetch failed",
            }
        cats = raw.get("categories") or {}
        description = raw.get("descriptionPlain") or strip_html(raw.get("description"))
        req_bits = [
            f"{item.get('text', '')}: {item.get('content', '')}".strip(": ")
            for item in (raw.get("lists") or [])
            if isinstance(item, dict)
        ]
        return {
            "url": raw.get("hostedUrl") or "",
            "board": self.name,
            "title": raw.get("text") or "Unknown",
            "company": prettify_token(company),
            "location": cats.get("location") or raw.get("country") or "Unknown",
            "description": description,
            "requirements": "\n".join(b for b in req_bits if b),
            "apply_url": raw.get("applyUrl") or raw.get("hostedUrl") or "",
        }

"""Greenhouse board provider (public API, no auth).

API docs: https://developers.greenhouse.io/harvest.html (job board variant
served from boards-api.greenhouse.io).

List:   GET https://boards-api.greenhouse.io/v1/boards/{token}/jobs
Detail: GET https://boards-api.greenhouse.io/v1/boards/{token}/jobs/{id}?questions=true

Board tokens are read from providers/boards.json ("greenhouse" key).
Each token was verified live against the API; dead ones were dropped
(see the module docstring / test notes in the repo README).
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

log = logging.getLogger("job-apply-mcp.providers.greenhouse")

_BOARDS_FILE = Path(__file__).resolve().parent / "boards.json"


def _load_tokens() -> list[str]:
    try:
        return list(json.loads(_BOARDS_FILE.read_text(encoding="utf-8"))["greenhouse"])
    except Exception as exc:  # missing/corrupt file: degrade, don't crash
        log.warning("Could not load board tokens from %s: %s", _BOARDS_FILE, exc)
        return []


class GreenhouseProvider:
    """Search jobs across curated Greenhouse-hosted company boards."""

    name = "greenhouse"
    LIST_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
    DETAIL_URL = (
        "https://boards-api.greenhouse.io/v1/boards/{token}/jobs/{job_id}"
        "?questions=true"
    )

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
        # Cap per-token contributions so the total stays within ``limit``.
        per_token = max(1, math.ceil(limit / max(1, len(tokens)))) if limit else 0

        with make_client() as client:
            for i, token in enumerate(tokens):
                if limit and len(jobs) >= limit:
                    break
                if i:
                    polite_delay()
                data = fetch_json(client, "GET", self.LIST_URL.format(token=token))
                if not data or not isinstance(data, dict):
                    continue
                company = data.get("company_name") or prettify_token(token)
                taken = 0
                for raw in data.get("jobs", []):
                    if limit and (len(jobs) >= limit or taken >= per_token):
                        break
                    job = self._parse_job(raw, token, company)
                    if not job:
                        continue
                    if query_words and not words_match(job["_search_text"], query_words):
                        continue
                    if location and location not in job["location"].lower():
                        continue
                    if remote_only and "remote" not in job["location"].lower():
                        continue
                    taken += 1
                    del job["_search_text"]
                    jobs.append(job)
        log.info(
            "Greenhouse: %d jobs for %r in %r across %d boards",
            len(jobs),
            query,
            location,
            len(tokens),
        )
        return jobs

    def _parse_job(
        self, raw: dict[str, Any], token: str, company: str
    ) -> dict[str, Any] | None:
        job_id = raw.get("id")
        title = (raw.get("title") or "").strip()
        if job_id is None or not title:
            return None
        loc = raw.get("location") or {}
        location = (loc.get("name") if isinstance(loc, dict) else str(loc)) or "Unknown"
        departments = raw.get("departments") or []
        dept_text = " ".join(
            (d.get("name") or "") for d in departments if isinstance(d, dict)
        )
        url = raw.get("absolute_url") or ""
        payload = f"{token}:{job_id}"
        snippet = f"{title} — {dept_text} — {location}".strip(" —")[:400]
        return {
            "id": make_job_id(self.name, payload),
            "title": title,
            "company": company,
            "location": location,
            "url": url,
            "board": self.name,
            "snippet": snippet,
            # internal: full text the query words are matched against
            "_search_text": f"{title} {dept_text}",
        }

    # -- details --------------------------------------------------------
    def get_details(self, payload: str) -> dict[str, Any]:
        """Full details for a job. ``payload`` is the decoded id payload
        (``"token:jobid"``)."""
        token, sep, job_id = payload.partition(":")
        if not sep or not token or not job_id:
            return {"board": self.name, "payload": payload,
                    "error": f"Malformed Greenhouse payload: {payload!r}"}
        with make_client() as client:
            polite_delay()
            data = fetch_json(
                client, "GET", self.DETAIL_URL.format(token=token, job_id=job_id)
            )
        if not data:
            return {
                "url": "",
                "board": self.name,
                "error": f"Greenhouse job {payload!r} not found or fetch failed",
            }
        url = data.get("absolute_url") or ""
        departments = data.get("departments") or []
        offices = data.get("offices") or []
        metadata = data.get("metadata")
        # Apply-readiness enrichment (Initiative 09, epic 2): the official
        # Job Board API already answers ?questions=true, so we surface the
        # application surface honestly without submitting anything.
        questions = data.get("questions") or []
        required_questions = sum(
            1 for q in questions if isinstance(q, dict) and q.get("required")
        )
        custom_fields = [
            m.get("name")
            for m in (metadata if isinstance(metadata, list) else [])
            if isinstance(m, dict) and m.get("name")
        ]
        # Wire the Employment Type metadata value through instead of
        # hardcoding "". Case-insensitive name match; first hit wins.
        employment_type = ""
        for m in metadata if isinstance(metadata, list) else []:
            if (
                isinstance(m, dict)
                and str(m.get("name") or "").strip().lower() == "employment type"
            ):
                employment_type = str(m.get("value") or "").strip()
                break
        location_name = (data.get("location") or {}).get("name") or "Unknown"
        return {
            "url": url,
            "board": self.name,
            "title": data.get("title") or "Unknown",
            "company": data.get("company_name") or prettify_token(token),
            "location": location_name,
            "description": strip_html(data.get("content")),
            "requirements": self._format_metadata(metadata),
            "departments": [
                d.get("name") for d in departments if isinstance(d, dict)
            ],
            "apply_url": url,
            # --- Initiative 09 enrichment (additive; official API only) ---
            "offices": [
                o.get("name") for o in offices if isinstance(o, dict)
            ],
            "employment_type": employment_type,
            "remote": "remote" in location_name.lower(),
            "posted_date": str(data.get("updated_at") or "")[:10],
            "application_questions": len(questions),
            "required_questions": required_questions,
            "custom_fields": custom_fields,
            "closing_date": "",
            "readiness_note": (
                "Details and application questions come from Greenhouse's "
                "official public Job Board API (read-only). Direct API "
                "submission is not permitted to job seekers: POST "
                "applications requires an employer-issued Job Board API key "
                "(see ats_apply.endpoint_status('greenhouse'))."
            ),
        }

    @staticmethod
    def _format_metadata(metadata: Any) -> str:
        """Best-effort text extraction from the job's metadata block."""
        if not metadata:
            return ""
        try:
            if isinstance(metadata, list):
                parts = [
                    f"{m.get('name')}: {m.get('value')}"
                    for m in metadata
                    if isinstance(m, dict) and m.get("name")
                ]
                return "\n".join(parts)
            if isinstance(metadata, dict):
                return "\n".join(f"{k}: {v}" for k, v in metadata.items())
            return str(metadata)
        except Exception:
            return ""

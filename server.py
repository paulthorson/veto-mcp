#!/usr/bin/env python3
"""Job Apply MCP server.

Exposes job-board search and assisted-application tools over the Model
Context Protocol (MCP) so an AI agent can:

  * search jobs across major boards (Indeed, LinkedIn; stubs for
    Glassdoor / ZipRecruiter),
  * fetch full job descriptions,
  * prepare (and, only with explicit user confirmation, record)
    job applications without manual form filling.

Phase 1 application support returns an application *preview* plus the direct
``apply_url`` and extracted form fields, and logs the attempt to
``applications.json``. It never auto-submits a form. A commented Phase 2
hook sketches future Playwright-based browser automation.

Safety: scraping job boards may violate their Terms of Service and can
trigger rate limits / CAPTCHAs / account restrictions. Built-in politeness
(1-2s delays, user-agent rotation) reduces but does not eliminate that risk.
"""

from __future__ import annotations

import abc
import base64
import json
import logging
import os
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from mcp.server.mcpserver import MCPServer

# API-based providers (Greenhouse / Lever / Ashby / Adzuna) live in
# providers/. They intentionally do NOT import server.py (no circular
# imports); server.py imports them here. Job ids stay self-describing
# (<board>:<base64url(payload)>), so _decode_job_id needs no changes.
try:
    from providers import (
        AdzunaProvider,
        AshbyProvider,
        GreenhouseProvider,
        LeverProvider,
    )

    _API_PROVIDERS: dict[str, Any] = {
        "greenhouse": GreenhouseProvider(),
        "lever": LeverProvider(),
        "ashby": AshbyProvider(),
        "adzuna": AdzunaProvider(),
    }
except ImportError as exc:  # defensive: the server must still start
    log.warning("providers/ package failed to import; API boards disabled: %s", exc)
    _API_PROVIDERS = {}

# Application-quality helpers (dedup.py, prefs.py, filters.py, tailor.py).
# Imported defensively: the server must start even if one is missing.
try:
    from dedup import dedupe_jobs
except ImportError as exc:
    log.warning("dedup.py unavailable; result dedup disabled: %s", exc)
    dedupe_jobs = None  # type: ignore[assignment]

try:
    from prefs import apply_preferences, load_preferences, save_preferences
except ImportError as exc:
    log.warning("prefs.py unavailable; company preferences disabled: %s", exc)
    apply_preferences = None  # type: ignore[assignment]
    load_preferences = None  # type: ignore[assignment]
    save_preferences = None  # type: ignore[assignment]

try:
    from filters import filter_by_salary, filter_by_seniority
except ImportError as exc:
    log.warning("filters.py unavailable; salary/seniority filters disabled: %s", exc)
    filter_by_salary = None  # type: ignore[assignment]
    filter_by_seniority = None  # type: ignore[assignment]


def _sanitize_proxy_env() -> None:
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


_sanitize_proxy_env()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [job-apply-mcp] %(message)s",
)
log = logging.getLogger("job-apply-mcp")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
APPLICATIONS_FILE = BASE_DIR / "applications.json"
WATCHES_FILE = BASE_DIR / "watches.json"

# Lifecycle (application stages / stats / follow-ups), job watches, and
# multi-profile helpers live in their own modules so the tools below stay
# thin. They use stdlib + local code only (no heavy deps).
import lifecycle
import watch as watch_store

USER_AGENTS = [
    # Rotated to look like ordinary browser traffic. Add more as needed.
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

# In-memory cache of jobs returned by recent search_jobs calls, keyed by
# job_id. Enriches previews/details; job_ids are also self-describing
# (board + base64url of the job URL) so they work without a prior search.
_JOB_REGISTRY: dict[str, dict[str, Any]] = {}


def _headers() -> dict[str, str]:
    """Return request headers with a rotated user agent."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }


def _polite_delay() -> None:
    """Sleep 1-2s between requests to respect rate limits."""
    delay = random.uniform(1.0, 2.0)
    log.debug("Politeness delay: %.2fs", delay)
    time.sleep(delay)


def _encode_job_id(board: str, url: str) -> str:
    """Build a self-describing job id: ``<board>:<base64url(url)>``."""
    token = base64.urlsafe_b64encode(url.encode("utf-8")).decode("ascii").rstrip("=")
    return f"{board}:{token}"


def _decode_job_id(job_id: str) -> tuple[str, str]:
    """Split a job id back into ``(board, url)``.

    Raises:
        ValueError: If the job id is malformed.
    """
    board, sep, token = job_id.partition(":")
    if not sep or not board or not token:
        raise ValueError(f"Malformed job_id: {job_id!r}")
    padded = token + "=" * (-len(token) % 4)
    url = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
    return board, url


def _load_applications() -> list[dict[str, Any]]:
    """Read the local applications store (empty list if missing/corrupt)."""
    try:
        return json.loads(APPLICATIONS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        log.warning("Could not read %s: %s", APPLICATIONS_FILE, exc)
        return []


def _save_applications(applications: list[dict[str, Any]]) -> None:
    """Persist the local applications store."""
    APPLICATIONS_FILE.write_text(
        json.dumps(applications, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


PROFILE_FILE = BASE_DIR / "profiles" / "profile.json"


def _load_saved_profile() -> dict[str, Any]:
    """Return the wizard-saved applicant profile, or {} if none exists."""
    try:
        data = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        log.debug("No saved profile at %s: %s", PROFILE_FILE, exc)
        return {}
    return data if isinstance(data, dict) else {}


# ---------------------------------------------------------------------------
# Provider abstraction
# ---------------------------------------------------------------------------


class JobProvider(abc.ABC):
    """Pluggable job-board provider."""

    name: str = "base"

    @abc.abstractmethod
    def search(
        self, query: str, location: str, limit: int, remote_only: bool
    ) -> list[dict[str, Any]]:
        """Return up to ``limit`` job dicts for the query/location."""

    @abc.abstractmethod
    def get_details(self, url: str) -> dict[str, Any]:
        """Return full details for a job posting URL."""


class IndeedProvider(JobProvider):
    """Indeed public search (no auth). HTML scraping; resilient selectors."""

    name = "indeed"
    SEARCH_URL = "https://www.indeed.com/jobs"

    def search(
        self, query: str, location: str, limit: int, remote_only: bool
    ) -> list[dict[str, Any]]:
        params = {"q": query, "l": location, "sort": "date", "fromage": "14"}
        jobs: list[dict[str, Any]] = []
        try:
            with httpx.Client(
                headers=_headers(), timeout=20.0, follow_redirects=True
            ) as client:
                _polite_delay()
                resp = client.get(self.SEARCH_URL, params=params)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")
                # Multiple selector generations; fall back gracefully.
                cards = (
                    soup.select("div.job_seen_beacon")
                    or soup.select("td.resultContent")
                    or soup.select("[data-jk]")
                )
                for card in cards:
                    job = self._parse_card(card)
                    if not job:
                        continue
                    if remote_only and "remote" not in (
                        job["location"] + " " + job["snippet"]
                    ).lower():
                        continue
                    jobs.append(job)
                    if len(jobs) >= limit:
                        break
        except Exception as exc:  # never crash the tool on a scrape failure
            log.warning("Indeed search failed: %s", exc)
        log.info("Indeed: %d jobs for %r in %r", len(jobs), query, location)
        return jobs

    def _parse_card(self, card: Any) -> dict[str, Any] | None:
        anchor = (
            card.select_one("h2.jobTitle a")
            or card.select_one("a.jcs-JobTitle")
            or card.select_one("a[data-jk]")
        )
        if anchor is None:
            return None
        title = anchor.get("aria-label") or anchor.get_text(strip=True)
        if not title:
            return None
        jk = anchor.get("data-jk") or ""
        if not jk:
            m = re.search(r"[?&]jk=([A-Za-z0-9_-]+)", anchor.get("href", ""))
            jk = m.group(1) if m else ""
        url = (
            f"https://www.indeed.com/viewjob?jk={jk}"
            if jk
            else urljoin("https://www.indeed.com", anchor.get("href", ""))
        )
        company_el = card.select_one(
            'span[data-testid="company-name"]'
        ) or card.select_one("span.companyName")
        location_el = card.select_one(
            'div[data-testid="text-location"]'
        ) or card.select_one("div.companyLocation")
        snippet_el = card.select_one('div[data-testid="job-snippet"]') or card.select_one(
            "div.job-snippet"
        )
        job = {
            "id": _encode_job_id(self.name, url),
            "title": title.strip(),
            "company": company_el.get_text(strip=True) if company_el else "Unknown",
            "location": location_el.get_text(strip=True) if location_el else "Unknown",
            "url": url,
            "board": self.name,
            "snippet": (
                snippet_el.get_text(" ", strip=True)[:500] if snippet_el else ""
            ),
        }
        _JOB_REGISTRY[job["id"]] = job
        return job

    def get_details(self, url: str) -> dict[str, Any]:
        try:
            with httpx.Client(
                headers=_headers(), timeout=20.0, follow_redirects=True
            ) as client:
                _polite_delay()
                resp = client.get(url)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")
                desc_el = soup.select_one("div#jobDescriptionText")
                title_el = soup.select_one("h1.jobsearch-JobInfoHeader-title")
                return {
                    "url": url,
                    "board": self.name,
                    "title": title_el.get_text(strip=True) if title_el else "Unknown",
                    "description": (
                        desc_el.get_text("\n", strip=True) if desc_el else ""
                    ),
                    "requirements": "",  # Indeed embeds these in the description text
                    "apply_url": url,
                }
        except Exception as exc:
            log.warning("Indeed details failed for %s: %s", url, exc)
            return {"url": url, "board": self.name, "error": str(exc)}


class LinkedInProvider(JobProvider):
    """LinkedIn guest jobs API (no auth required).

    Uses the public ``jobs-guest`` endpoints. If LinkedIn blocks the guest
    API (HTTP 403/429), search returns an empty list and logs the fallback.
    """

    name = "linkedin"
    SEARCH_URL = (
        "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    )
    DETAILS_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{}"
    # Guest posting URLs look like /jobs/view/<slug>-<numeric-id>[?...]
    JOB_ID_RE = re.compile(r"-(\d{6,})(?:[/?#]|$)")

    @classmethod
    def _job_id_from_url(cls, url: str) -> str | None:
        """Extract the numeric LinkedIn job id from a posting URL."""
        m = cls.JOB_ID_RE.search(url)
        return m.group(1) if m else None

    def search(
        self, query: str, location: str, limit: int, remote_only: bool
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"keywords": query, "location": location, "start": 0}
        if remote_only:
            params["f_WT"] = "2"  # LinkedIn "Remote" workplace-type filter
        jobs: list[dict[str, Any]] = []
        try:
            with httpx.Client(
                headers=_headers(), timeout=20.0, follow_redirects=True
            ) as client:
                start = 0
                while len(jobs) < limit:
                    params["start"] = start
                    _polite_delay()
                    resp = client.get(self.SEARCH_URL, params=params)
                    if resp.status_code != 200:
                        log.warning(
                            "LinkedIn guest API returned HTTP %s; "
                            "it may be blocking automated access.",
                            resp.status_code,
                        )
                        break
                    soup = BeautifulSoup(resp.text, "lxml")
                    cards = soup.select("li div.base-card")
                    if not cards:
                        break
                    for card in cards:
                        job = self._parse_card(card)
                        if job:
                            jobs.append(job)
                            if len(jobs) >= limit:
                                break
                    start += len(cards)
        except Exception as exc:
            log.warning("LinkedIn search failed: %s", exc)
        log.info("LinkedIn: %d jobs for %r in %r", len(jobs), query, location)
        return jobs

    def _parse_card(self, card: Any) -> dict[str, Any] | None:
        link = card.select_one("a.base-card__full-link")
        if link is None or not link.get("href"):
            return None
        href = urljoin("https://www.linkedin.com", link["href"])
        job_key = self._job_id_from_url(href) or href
        title_el = card.select_one("h3.base-search-card__title")
        company_el = card.select_one("h4.base-search-card__subtitle")
        location_el = card.select_one("span.job-search-card__location")
        time_el = card.select_one("time")
        job = {
            "id": _encode_job_id(self.name, href),
            "title": title_el.get_text(strip=True) if title_el else "Unknown",
            "company": company_el.get_text(strip=True) if company_el else "Unknown",
            "location": location_el.get_text(strip=True) if location_el else "Unknown",
            "url": href,
            "board": self.name,
            "snippet": (
                f"Posted {time_el.get_text(strip=True)}" if time_el else ""
            ),
            "linkedin_job_key": job_key,
        }
        _JOB_REGISTRY[job["id"]] = job
        return job

    def get_details(self, url: str) -> dict[str, Any]:
        job_key = self._job_id_from_url(url)
        try:
            with httpx.Client(
                headers=_headers(), timeout=20.0, follow_redirects=True
            ) as client:
                _polite_delay()
                target = self.DETAILS_URL.format(job_key) if job_key else url
                resp = client.get(target)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")
                title_el = soup.select_one("h2.top-card-layout__title")
                company_el = soup.select_one("a.topcard__org-name-link")
                desc_el = soup.select_one("div.description__text")
                criteria = [
                    li.get_text(" ", strip=True)
                    for li in soup.select("ul.description__job-criteria-list li")
                ]
                return {
                    "url": url,
                    "board": self.name,
                    "title": title_el.get_text(strip=True) if title_el else "Unknown",
                    "company": (
                        company_el.get_text(strip=True) if company_el else "Unknown"
                    ),
                    "description": (
                        desc_el.get_text("\n", strip=True) if desc_el else ""
                    ),
                    "requirements": "\n".join(criteria),
                    "apply_url": url,
                }
        except Exception as exc:
            log.warning("LinkedIn details failed for %s: %s", url, exc)
            return {"url": url, "board": self.name, "error": str(exc)}


class GlassdoorProvider(JobProvider):
    """Stub: Glassdoor requires JS-heavy pages / auth for search results."""

    name = "glassdoor"

    def search(self, query: str, location: str, limit: int, remote_only: bool):
        # TODO: Glassdoor search is behind bot mitigation. Options:
        #   1. Playwright with a logged-in session (see Phase 2 hook below).
        #   2. Official/partner API access if available.
        raise NotImplementedError(
            "Glassdoor provider is a stub: scraping is blocked without a "
            "logged-in browser session. See Phase 2 hook."
        )

    def get_details(self, url: str):
        raise NotImplementedError("Glassdoor provider is a stub.")


class ZipRecruiterProvider(JobProvider):
    """Stub: ZipRecruiter search pages are JS-rendered and bot-protected."""

    name = "ziprecruiter"

    def search(self, query: str, location: str, limit: int, remote_only: bool):
        # TODO: ZipRecruiter needs a JS-capable fetcher (Playwright) or
        # partner API. Wire into the Phase 2 browser hook when available.
        raise NotImplementedError(
            "ZipRecruiter provider is a stub: pages are JS-rendered and "
            "bot-protected. See Phase 2 hook."
        )

    def get_details(self, url: str):
        raise NotImplementedError("ZipRecruiter provider is a stub.")


PROVIDERS: dict[str, JobProvider] = {
    "indeed": IndeedProvider(),
    "linkedin": LinkedInProvider(),
    "glassdoor": GlassdoorProvider(),
    "ziprecruiter": ZipRecruiterProvider(),
    **_API_PROVIDERS,
}
ACTIVE_BOARDS = {"indeed", "linkedin", "greenhouse", "lever", "ashby"}


# ---------------------------------------------------------------------------
# Phase 2: browser-automation apply hook (browser_apply.py)
# ---------------------------------------------------------------------------
#
# Implemented in browser_apply.py (Playwright, sync API). Enable with the
# environment variable JOB_MCP_BROWSER_APPLY=1. When enabled and
# apply_to_job(..., confirm=True) is called, the server opens the job's
# apply_url in headless Chromium, fills the form from `profile`, uploads
# the resume, screenshots the result, and clicks submit — all logged to
# applications.json. Without the env var, Phase 1 (preview + local log)
# behavior is preserved.
#
# Anti-bot note: automated applications can lead to CAPTCHAs / IP throttles
# / account restrictions on LinkedIn, Indeed, etc. Keep human review in the
# loop and apply at a human pace.


def _browser_apply_enabled() -> bool:
    """True when the operator opted into Phase 2 browser automation."""
    return os.environ.get("JOB_MCP_BROWSER_APPLY") == "1"


# ---------------------------------------------------------------------------
# MCP server + tools
# ---------------------------------------------------------------------------

mcp = MCPServer(
    "job-apply",
    instructions=(
        "Search jobs across major boards and prepare assisted job "
        "applications. apply_to_job NEVER submits without confirm=True. "
        "Without the JOB_MCP_BROWSER_APPLY env var, confirm=True only "
        "records the application locally (Phase 1) and the user completes "
        "the submission in their browser; with JOB_MCP_BROWSER_APPLY=1, "
        "confirm=True auto-fills and submits the form in headless Chromium "
        "via a profile dict (Phase 2)."
    ),
)


@mcp.tool()
def list_boards() -> list[dict[str, str]]:
    """List supported job boards and whether each provider is active or a stub."""
    notes = {
        "adzuna": "needs ADZUNA_APP_ID + ADZUNA_APP_KEY env vars (developer.adzuna.com)",
        "glassdoor": "not yet implemented; see provider TODO",
        "ziprecruiter": "not yet implemented; see provider TODO",
    }
    return [
        {
            "board": name,
            "status": "active" if name in ACTIVE_BOARDS else "stub",
            "notes": (
                "search + details supported"
                if name in ACTIVE_BOARDS
                else notes.get(name, "not yet implemented")
            ),
        }
        for name in PROVIDERS
    ]


@mcp.tool()
def search_jobs(
    query: str,
    location: str,
    board: str = "all",
    limit: int = 10,
    remote_only: bool = False,
    salary_min: int = 0,
    seniority: str = "",
) -> list[dict[str, Any]]:
    """Search job postings across major boards.

    Args:
        query: Job title / keywords, e.g. "software engineer".
        location: e.g. "New York, NY" or "Remote".
        board: One of "all", "indeed", "linkedin", "greenhouse", "lever",
            "ashby", "adzuna", "glassdoor", "ziprecruiter". Stub boards and
            boards missing required credentials raise an error.
        limit: Max jobs to return per board (default 10).
        remote_only: Only include remote-friendly postings.
        salary_min: Keep jobs whose best salary hint meets this annual USD
            floor (post-filter on listing text; jobs with no salary hint
            are kept). 0 disables.
        seniority: One of entry|mid|senior|staff|principal (post-filter on
            title keywords; untitled/unknown seniority is kept). ""
            disables.

    Returns:
        Deduplicated, preference-filtered list of jobs with id, title,
        company, location, url, board, snippet. Preferred-company matches
        carry "preferred": True and sort first.
    """
    board = board.lower().strip()
    if board != "all" and board not in PROVIDERS:
        raise ValueError(
            f"Unknown board {board!r}. Use list_boards() to see supported boards."
        )
    targets = (
        [b for b in PROVIDERS if b in ACTIVE_BOARDS]
        if board == "all"
        else [board]
    )
    results: list[dict[str, Any]] = []
    for name in targets:
        provider = PROVIDERS[name]
        try:
            results.extend(
                provider.search(query, location, limit=limit, remote_only=remote_only)
            )
        except (NotImplementedError, RuntimeError) as exc:
            # NotImplementedError: stub boards (glassdoor/ziprecruiter).
            # RuntimeError: providers needing user credentials (adzuna
            # without ADZUNA_APP_ID/ADZUNA_APP_KEY). Surface as ValueError
            # so the tool contract stays consistent.
            log.warning("%s: %s", name, exc)
            raise ValueError(f"Board {name!r} is not usable: {exc}")
    results = results[: limit * len(targets)]

    # Application-quality pipeline (all recall-friendly; each degrades to
    # a no-op when its module failed to import).
    if apply_preferences is not None:
        results = apply_preferences(results)
    if dedupe_jobs is not None:
        before = len(results)
        results = dedupe_jobs(results)
        log.info("dedup: %d -> %d jobs", before, len(results))
    if filter_by_salary is not None:
        results = filter_by_salary(results, salary_min)
    if filter_by_seniority is not None:
        results = filter_by_seniority(results, seniority)
    return results


@mcp.tool()
def get_job_details(job_id: str) -> dict[str, Any]:
    """Fetch the full description for a job from search_jobs.

    Args:
        job_id: The job id returned by search_jobs.

    Returns:
        Dict with title, company, description, requirements, apply_url
        (or an "error" key if the fetch failed).
    """
    try:
        board, url = _decode_job_id(job_id)
    except ValueError as exc:
        return {"job_id": job_id, "error": str(exc)}
    provider = PROVIDERS.get(board)
    if provider is None:
        return {"job_id": job_id, "error": f"Unknown board {board!r}"}
    try:
        details = provider.get_details(url)
    except NotImplementedError as exc:
        return {"job_id": job_id, "error": str(exc)}
    cached = _JOB_REGISTRY.get(job_id, {})
    details.setdefault("title", cached.get("title", "Unknown"))
    details.setdefault("company", cached.get("company", "Unknown"))
    details["job_id"] = job_id
    return details


# ---------------------------------------------------------------------------
# Governance wiring (additive)
#
# Gates confirm=True applications through the user's agentic governance
# framework (governance/adapter.py): constitutional veto screen,
# cover-letter honesty check, qualification assessment, and an advisory
# adversarial review. Every helper below is a no-op when the framework is
# not installed, so behavior is unchanged without it.
# ---------------------------------------------------------------------------


def _governance_precheck(
    *,
    job_id: str,
    board: str,
    url: str,
    preview: dict[str, Any],
    profile: dict[str, str],
    cover_letter: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Run the governance gate before any submission or logging.

    Returns ``(blocked_response, warnings)``. ``blocked_response`` is None
    when the application may proceed; otherwise the caller must return it
    immediately (nothing was submitted or recorded). Never raises:
    unexpected errors degrade to non-blocking warnings, except veto-check
    failures which the adapter fails closed on.
    """
    try:
        from governance import adapter as _gov
    except Exception as exc:
        log.warning("Governance adapter unavailable: %s", exc)
        return None, []
    if not _gov.governance_enabled():
        return None, []
    details: dict[str, Any] = {}
    try:
        fetched = get_job_details(job_id)
        if isinstance(fetched, dict) and not fetched.get("error"):
            details = fetched
    except Exception as exc:
        log.warning("Governance: job details fetch failed: %s", exc)
    effective_profile = dict(profile or {}) or _gov.load_saved_profile()
    try:
        gate = _gov.governance_gate(
            job_id=job_id,
            job={
                "job_id": job_id,
                "title": preview.get("title"),
                "company": preview.get("company"),
                "location": preview.get("location"),
                "board": board,
                "url": url,
            },
            job_details=details,
            profile=effective_profile,
            cover_letter=cover_letter,
        )
    except Exception as exc:  # fail-open: a crashed gate warns, never blocks
        log.warning("Governance gate crashed (non-blocking): %s", exc)
        return None, [f"governance gate error (non-blocking): {exc}"]
    if gate.get("blocked"):
        return gate["response"], []
    return None, gate.get("warnings", [])


def _governance_record_outcome(
    *, job_id: str, preview: dict[str, Any], passed: bool, note: str
) -> None:
    """Record an allow-verdict after a confirmed application.

    No-op when the governance framework is not installed. Never raises.
    """
    try:
        from governance import adapter as _gov
    except Exception:
        return
    if not _gov.governance_enabled():
        return
    try:
        _gov.record_application_verdict(
            {
                "job_id": job_id,
                "title": preview.get("title"),
                "company": preview.get("company"),
            },
            passed,
            f"job-apply: application {note} for "
            f"{preview.get('title')} at {preview.get('company')}",
        )
    except Exception as exc:
        log.warning("Governance verdict recording failed: %s", exc)


@mcp.tool()
def apply_to_job(
    job_id: str,
    resume_path: str,
    cover_letter: str = "",
    answers: dict[str, str] | None = None,
    confirm: bool = False,
    profile: dict[str, str] | None = None,
    headless: bool = True,
) -> dict[str, Any]:
    """Prepare (and optionally record / browser-submit) a job application.

    Phase 1 (default): does NOT auto-submit any form. Without confirm=True
    this returns a dry-run preview only. With confirm=True the application
    is logged to the local applications.json store and the agent returns
    the direct apply_url so the user can complete submission in their
    browser.

    Phase 2 (opt-in browser automation): set the environment variable
    JOB_MCP_BROWSER_APPLY=1 and pass a `profile` dict. Then confirm=True
    opens the apply_url in headless Chromium, fills the form from the
    profile, uploads the resume, screenshots the result, clicks submit,
    and records the outcome (including screenshot path and submitted flag)
    in applications.json. Without the env var, confirm=True keeps the
    Phase 1 logging behavior.

    Args:
        job_id: The job id returned by search_jobs.
        resume_path: Local path to the resume file to attach.
        cover_letter: Optional cover letter text.
        answers: Optional common application answers, e.g.
            {"work_authorization": "yes", "salary_expectation": "150000"}.
        confirm: MUST be True to record the application (Phase 1) or to
            submit via the browser (Phase 2). Defaults to False
            (dry-run preview only).
        profile: Applicant details for Phase 2 browser fill, e.g.
            {"full_name": "Ada Lovelace", "email": "ada@example.com",
             "phone": "+1 555-0100", "location": "New York, NY",
             "linkedin_url": "...", "website": "...",
             "cover_letter": "..."}. full_name is split into first/last
            when the form asks for them separately. Defaults to the saved
            profiles/profile.json when omitted (see get_profile() and
            wizard.py); pass an explicit dict to override it.
        headless: Run the Phase 2 browser headless (default True). Set
            False to watch / manually log in during the session.

    Returns:
        Dry-run preview, or the recorded application entry when confirmed.
    """
    answers = answers or {}
    # Default to the wizard-saved profile when the caller passes none.
    # An explicitly passed dict (even empty) is respected as-is.
    if profile is None:
        profile = _load_saved_profile()
    else:
        profile = dict(profile)
    try:
        board, url = _decode_job_id(job_id)
    except ValueError as exc:
        return {"status": "error", "error": str(exc)}

    cached = _JOB_REGISTRY.get(job_id, {})
    resume = Path(resume_path).expanduser()
    preview: dict[str, Any] = {
        "job_id": job_id,
        "board": board,
        "title": cached.get("title", "Unknown"),
        "company": cached.get("company", "Unknown"),
        "location": cached.get("location", "Unknown"),
        "apply_url": url,
        "resume_path": str(resume),
        "resume_found": resume.is_file(),
        "cover_letter_chars": len(cover_letter),
        "answers_provided": sorted(answers.keys()),
        "profile_keys_provided": sorted(profile.keys()),
        # Common fields most application forms ask for; extracted so the
        # agent can pre-fill them for the user in Phase 2 / manual apply.
        "typical_form_fields": [
            "full_name",
            "email",
            "phone",
            "location",
            "linkedin_url",
            "work_authorization",
            "sponsorship_required",
            "salary_expectation",
            "start_date",
            "resume_upload",
            "cover_letter_upload",
        ],
    }
    if not preview["resume_found"]:
        preview["warning"] = (
            f"Resume not found at {resume}; attach a valid file before applying."
        )

    if not confirm:
        message = (
            "Dry run only: nothing was submitted or recorded. "
            "Review the preview and re-call with confirm=True to log "
            "this application."
        )
        if _browser_apply_enabled() and profile:
            message += (
                " Phase 2 browser automation is enabled: on confirm, the "
                "form will be auto-filled from your profile in a headless "
                "browser and submitted."
            )
        elif profile:
            message += (
                " Tip: pass profile + set JOB_MCP_BROWSER_APPLY=1 to enable "
                "Phase 2 browser auto-fill on confirm."
            )
        return {
            "status": "dry_run",
            "message": message,
            "preview": preview,
        }

    # confirm=True ---------------------------------------------------------
    # Governance gate (additive): veto + cover-letter-honesty +
    # qualification checks run BEFORE any browser submission or local
    # logging. No-op when the governance framework is not installed.
    # A blocked gate returns immediately: nothing is submitted or recorded.
    _gov_block, _gov_warnings = _governance_precheck(
        job_id=job_id,
        board=board,
        url=url,
        preview=preview,
        profile=profile,
        cover_letter=cover_letter,
    )
    if _gov_block is not None:
        return _gov_block
    if _gov_warnings:
        preview.setdefault("governance_warnings", []).extend(_gov_warnings)

    if _browser_apply_enabled():
        _gov_browser_result = _apply_via_browser_and_record(
            job_id=job_id,
            board=board,
            url=url,
            preview=preview,
            answers=answers,
            profile=profile,
            cover_letter=cover_letter,
            resume=resume,
            headless=headless,
        )
        _governance_record_outcome(
            job_id=job_id,
            preview=preview,
            passed=True,
            note=(
                "phase-2 browser apply finished with status "
                f"{_gov_browser_result.get('status')}"
            ),
        )
        return _gov_browser_result

    entry = {
        "job_id": job_id,
        "board": board,
        "title": preview["title"],
        "company": preview["company"],
        "location": preview["location"],
        "apply_url": url,
        "resume_path": str(resume),
        "cover_letter_chars": len(cover_letter),
        "answers": answers,
        "status": "confirmed",
        "submitted_at": (submitted_at := datetime.now(timezone.utc).isoformat()),
        # Lifecycle fields (see lifecycle.py): every recorded application
        # starts at stage "applied" with a seeded history event.
        "stage": "applied",
        "stage_history": [{"stage": "applied", "at": submitted_at, "note": ""}],
        "follow_up_due": None,
        "note": (
            "Phase 1: recorded locally. Complete the actual submission at "
            "apply_url in your browser. To enable Phase 2 browser "
            "auto-fill, set JOB_MCP_BROWSER_APPLY=1 and pass a profile "
            "dict (see browser_apply.py for the schema)."
        ),
    }
    applications = _load_applications()
    applications.append(entry)
    _save_applications(applications)
    _governance_record_outcome(
        job_id=job_id, preview=preview, passed=True, note="phase-1 recorded"
    )
    log.info("Application confirmed for %s (%s)", entry["title"], job_id)
    return {
        "status": "confirmed",
        "message": (
            "Application recorded locally. Finish submitting it at the "
            f"apply_url: {url}"
        ),
        "application": entry,
        "preview": preview,
    }


def _apply_via_browser_and_record(
    *,
    job_id: str,
    board: str,
    url: str,
    preview: dict[str, Any],
    answers: dict[str, str],
    profile: dict[str, str],
    cover_letter: str,
    resume: Path,
    headless: bool,
) -> dict[str, Any]:
    """Phase 2: fill + submit the form in a real browser, then log it.

    Any failure (missing Playwright, navigation error, no submit button)
    is recorded with submitted=False — the tool never raises.
    """
    if cover_letter and not profile.get("cover_letter"):
        profile = {**profile, "cover_letter": cover_letter}
    try:
        from browser_apply import apply_via_browser

        browser_result = apply_via_browser(
            apply_url=url,
            profile=profile,
            resume_path=str(resume),
            headless=headless,
            confirm=True,
            board=board,  # loads a saved login session when one exists
        )
    except Exception as exc:  # defensive: the tool must never crash
        log.warning("Phase 2 browser apply failed for %s: %s", job_id, exc)
        browser_result = {
            "ok": False,
            "submitted": False,
            "fields_filled": {},
            "fields_detected": 0,
            "screenshot": None,
            "screenshot_after_submit": None,
            "final_url": url,
            "error": f"browser hook crashed: {exc}",
        }

    entry = {
        "job_id": job_id,
        "board": board,
        "title": preview["title"],
        "company": preview["company"],
        "location": preview["location"],
        "apply_url": url,
        "resume_path": str(resume),
        "cover_letter_chars": len(cover_letter),
        "answers": answers,
        "profile_keys": sorted(profile.keys()),
        "status": "browser_submitted" if browser_result.get("submitted") else "browser_failed",
        "submitted": bool(browser_result.get("submitted")),
        "fields_detected": browser_result.get("fields_detected", 0),
        "fields_filled": browser_result.get("fields_filled", {}),
        "screenshot": browser_result.get("screenshot"),
        "screenshot_after_submit": browser_result.get("screenshot_after_submit"),
        "final_url": browser_result.get("final_url"),
        "browser_error": browser_result.get("error"),
        "submitted_at": (submitted_at := datetime.now(timezone.utc).isoformat()),
        # Lifecycle fields (see lifecycle.py).
        "stage": "applied",
        "stage_history": [{"stage": "applied", "at": submitted_at, "note": ""}],
        "follow_up_due": None,
        "note": (
            "Phase 2 browser automation. Verify the submission on the "
            "live site / in the confirmation email before treating it "
            "as complete."
        ),
    }
    applications = _load_applications()
    applications.append(entry)
    _save_applications(applications)
    log.info(
        "Phase 2 apply for %s (%s): submitted=%s",
        entry["title"],
        job_id,
        entry["submitted"],
    )
    if browser_result.get("submitted"):
        message = "Application submitted via browser automation and recorded."
    else:
        message = (
            "Browser automation did not complete a submission "
            f"({browser_result.get('error') or 'no submit button found'}). "
            "The attempt was recorded; review the screenshot and finish "
            "manually if needed."
        )
    return {
        "status": entry["status"],
        "message": message,
        "application": entry,
        "preview": preview,
    }


@mcp.tool()
def track_applications() -> list[dict[str, Any]]:
    """Return all locally recorded job applications (from applications.json).

    Legacy entries (recorded before stages existed) are backfilled in
    memory with ``stage="applied"``; the file is not rewritten.
    """
    return lifecycle.load_entries(APPLICATIONS_FILE)


@mcp.tool()
def update_application(
    job_id_or_index: str, stage: str, note: str = ""
) -> dict[str, Any]:
    """Move a recorded application to a new pipeline stage.

    Args:
        job_id_or_index: The ``job_id`` from track_applications, or its
            numeric index in the list.
        stage: One of ``applied``, ``interviewing``, ``offer``,
            ``rejected``, ``withdrawn``, ``ghosted``.
        note: Optional note recorded with the stage change.

    Moving to ``interviewing`` sets a follow-up reminder 7 days out;
    terminal stages (``offer``/``rejected``/``withdrawn``) clear it.
    """
    try:
        return lifecycle.update_stage(APPLICATIONS_FILE, job_id_or_index, stage, note=note)
    except (ValueError, KeyError) as exc:
        return {"error": str(exc)}


@mcp.tool()
def application_stats() -> dict[str, Any]:
    """Aggregate stats over recorded applications.

    Returns ``{total, by_stage, by_board, response_rate}`` where
    response_rate = (interviewing + offer) / total.
    """
    return lifecycle.stats(lifecycle.load_entries(APPLICATIONS_FILE))


@mcp.tool()
def nudge_followups() -> list[dict[str, Any]]:
    """Applications with a follow-up due today or earlier.

    Covers stages ``applied`` and ``interviewing``. Pair with
    update_application() to advance or clear them.
    """
    return lifecycle.due_followups(lifecycle.load_entries(APPLICATIONS_FILE))


@mcp.tool()
def add_watch(
    name: str,
    query: str,
    location: str = "",
    board: str = "all",
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Save a named job watch (a recurring search).

    The first check of a watch only records a baseline and reports no new
    jobs, so you are not spammed with everything that already existed.
    Run ``check_watches()`` (or ``python watch.py`` on a cron) to poll.
    """
    watches = watch_store.load_watches(WATCHES_FILE)
    try:
        saved = watch_store.add_watch(watches, name, query, location, board, filters)
    except ValueError as exc:
        return {"error": str(exc)}
    watch_store.save_watches(WATCHES_FILE, watches)
    return {
        "watch": saved,
        "message": (
            f"Watch {name!r} saved. The first check records a baseline "
            "(no alerts); later checks report only new postings."
        ),
    }


@mcp.tool()
def list_watches() -> list[dict[str, Any]]:
    """List all saved job watches and their last-check state."""
    return list(watch_store.load_watches(WATCHES_FILE).values())


@mcp.tool()
def remove_watch(name: str) -> dict[str, Any]:
    """Delete a saved job watch."""
    watches = watch_store.load_watches(WATCHES_FILE)
    removed = watch_store.remove_watch(watches, name)
    if removed:
        watch_store.save_watches(WATCHES_FILE, watches)
    return {"removed": removed, "name": name}


@mcp.tool()
def check_watches() -> dict[str, Any]:
    """Run every saved watch and return only the new postings per watch.

    Cron-friendly: output is plain JSON, one entry per watch with
    ``new_jobs`` and ``total_seen``. ``python watch.py`` does the same
    from a shell (prints JSON, exits 0).
    """
    watches = watch_store.load_watches(WATCHES_FILE)
    results = watch_store.check_all(watches, search_jobs)
    watch_store.save_watches(WATCHES_FILE, watches)
    return {
        name: {
            "new_jobs": r.get("new_jobs", []),
            "total_seen": r.get("total_seen", 0),
            **({"error": r["error"]} if r.get("error") else {}),
        }
        for name, r in results.items()
    }


@mcp.tool()
def export_applications_csv(path: str = "applications.csv") -> dict[str, Any]:
    """Export recorded applications to CSV (portability / spreadsheets).

    Args:
        path: Destination file; relative paths resolve under the project
            directory. Defaults to ``applications.csv``.
    """
    out = Path(path)
    if not out.is_absolute():
        out = BASE_DIR / out
    rows = lifecycle.export_csv(lifecycle.load_entries(APPLICATIONS_FILE), out)
    return {"path": str(out), "rows": rows}


@mcp.tool()
def get_profile() -> dict[str, Any]:
    """Return the applicant profile saved by the onboarding wizard.

    Run `python3 wizard.py` in the project directory to create or update
    profiles/profile.json. The wizard asks basic questions (name, contact,
    target titles, locations, remote preference, salary, skills, work
    authorization) and can ingest a LinkedIn data-export ZIP to pre-fill
    experience, education, and skills.

    The saved profile is used as the default `profile` for apply_to_job
    (Phase 2 browser auto-fill) and as the input for resume_builder.py.

    Returns:
        {"profile": {...}} when the wizard has been run, or
        {"profile": None, "message": ...} with setup instructions.
    """
    profile = _load_saved_profile()
    if not profile:
        return {
            "profile": None,
            "message": (
                "No saved profile found. Run the onboarding wizard to "
                "create one: `python3 wizard.py` in "
                "~/workspace/job-apply-mcp/ (it asks basic questions and "
                "can ingest a LinkedIn data-export ZIP to pre-fill "
                "experience/education/skills)."
            ),
        }
    return {"profile": profile}


@mcp.tool()
def tailor_application(
    job_id: str, profile: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build a per-job tailored resume + cover letter.

    Uses tailor.py: extracts the posting's keywords, front-loads matching
    experience bullets in the resume, and drafts a 3-paragraph cover
    letter. Honesty rule: only rephrases/reorders facts already in the
    profile — skills the job wants but the profile lacks are reported in
    ``missing_skills`` and are NOT added to the resume.

    Args:
        job_id: The job id returned by search_jobs.
        profile: Optional profile dict; defaults to the wizard-saved
            profiles/profile.json.

    Returns:
        {"resume_md", "cover_letter", "matched_skills", "missing_skills"}
        or {"error": ...}.
    """
    try:
        from tailor import tailor_resume
    except ImportError as exc:
        return {"error": f"tailor.py unavailable: {exc}"}
    prof = dict(profile) if profile is not None else _load_saved_profile()
    if not prof:
        return {
            "error": (
                "No profile available. Run `python3 wizard.py` to create "
                "one, or pass a profile dict."
            )
        }
    details = get_job_details(job_id)
    if details.get("error"):
        return {"job_id": job_id, "error": details["error"]}
    result = tailor_resume(prof, details)
    result["job_id"] = job_id
    return result


@mcp.tool()
def update_preferences(
    blocked_companies: list[str] | None = None,
    preferred_companies: list[str] | None = None,
    blocked_keywords: list[str] | None = None,
) -> dict[str, Any]:
    """Update company preferences used to filter search_jobs results.

    Each provided list REPLACES that preference list; omitted lists are
    left unchanged. Blocked companies/keywords are removed from results;
    preferred companies are flagged "preferred": True and sorted first.

    Args:
        blocked_companies: e.g. ["Acme Corp"].
        preferred_companies: e.g. ["Initech"].
        blocked_keywords: e.g. ["unpaid internship"].

    Returns:
        The full updated preferences dict.
    """
    if save_preferences is None or load_preferences is None:
        return {"error": "prefs.py unavailable."}
    prefs = load_preferences()
    if blocked_companies is not None:
        prefs["blocked_companies"] = [str(c) for c in blocked_companies]
    if preferred_companies is not None:
        prefs["preferred_companies"] = [str(c) for c in preferred_companies]
    if blocked_keywords is not None:
        prefs["blocked_keywords"] = [str(k) for k in blocked_keywords]
    return {"preferences": save_preferences(prefs)}


@mcp.tool()
def governance_status() -> dict[str, Any]:
    """Report whether the agentic governance framework is active.

    Returns:
        Dict with enabled, root, domains, and the gating policy
        (what fails closed vs. what warns and proceeds).
    """
    try:
        from governance import adapter as _gov
    except Exception as exc:
        return {
            "enabled": False,
            "root": None,
            "domains": [],
            "error": f"governance adapter import failed: {exc}",
        }
    root = _gov.find_governance_root()
    enabled = _gov.governance_enabled()
    domains: list[str] = []
    if enabled:
        try:
            domains = _gov.load_framework().list_domains()
        except Exception:
            domains = []
    return {
        "enabled": enabled,
        "root": str(root) if root else None,
        "domains": domains,
        "gating": {
            "veto_check": "fail-closed: blocks when a veto hits, and also "
            "blocks when the check itself errors",
            "cover_letter_honesty": "fail-closed: blocks on unsupported "
            "claims or framework errors",
            "qualification": "blocks below score 0.4 or on severe "
            "experience gap; warns (proceeds) on 0.4-0.65; fail-open "
            "with a warning when no profile is available",
            "adversarial_review": "advisory: warns on error, never blocks",
            "veto_clearing": "human only: fix the application/profile and "
            "re-run (framework overturn_verdict also exists)",
        },
    }


if __name__ == "__main__":
    # stdio transport (default): hook up to Claude Desktop / Muse via
    # `mcpServers` config pointing at this file.
    mcp.run()

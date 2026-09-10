"""ZipRecruiter provider (unofficial search technique, no auth).

Technique (verified 2026-07; see theabhishekchandra/applyverse
``docs/TECHNIQUES.md``): fetch the server-rendered search page::

    https://www.ziprecruiter.com/jobs-search?search=<q>&location=<loc>&page=N

and read the ``ld+json`` ``ItemList`` — 20 ``ListItem`` entries each with
a title (``name``) and the real job link (``url``, a ``?jid=`` URL).
Company / location / salary are paired **by index** with the rendered
``div[class*="job_result"]`` cards (``[data-testid="job-card-company"]``,
``[data-testid="job-card-location"]``, salary via a ``$`` regex).
Pagination via ``&page=N``.

Risk tier: scraping. CAPTCHAs are detected and stop the search — never
bypassed. HTTP 403/429 trips the compliance circuit breaker via
``compliance.record_block`` and degrades to an empty result (one dead
board must not crash a multi-board search).

Job ids follow the standard ``<board>:<base64url(payload)>`` format via
:mod:`providers._common`; the payload is the canonical job URL.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

import compliance
from providers._common import (
    make_client,
    make_job_id,
    polite_delay,
    strip_html,
)

log = logging.getLogger("job-apply-mcp.providers.ziprecruiter")

BASE = "https://www.ziprecruiter.com"
SEARCH_URL = f"{BASE}/jobs-search"

_CAPTCHA_RE = re.compile(
    r"captcha|verify you are (a )?human|unusual traffic|are you a robot",
    re.IGNORECASE,
)
_SALARY_RE = re.compile(
    r"\$[\d,]+(?:\.\d+)?[Kk]?"
    r"(?:\s*[-\u2013\u2014]\s*\$[\d,]+(?:\.\d+)?[Kk]?)?"
)

#: Safety cap on search pages per query (ZR returns ~20 jobs/page).
_MAX_PAGES = 10


def _extract_itemlist(soup: BeautifulSoup) -> list[dict[str, Any]]:
    """Pull the ld+json ItemList entries: [{position, name, url}]."""
    items: list[dict[str, Any]] = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (TypeError, json.JSONDecodeError):
            continue
        blocks = data if isinstance(data, list) else [data]
        for block in blocks:
            if not isinstance(block, dict):
                continue
            if block.get("@type") != "ItemList":
                continue
            for element in block.get("itemListElement") or []:
                if not isinstance(element, dict):
                    continue
                name = str(element.get("name") or "").strip()
                url = str(element.get("url") or "").strip()
                if not name or not url:
                    continue
                items.append(
                    {
                        "position": element.get("position") or 0,
                        "name": name,
                        "url": urljoin(BASE, url),
                    }
                )
    items.sort(key=lambda item: item["position"])
    return items


def _card_meta(card: Any) -> dict[str, str]:
    """Company/location/salary from a rendered job_result card."""
    company_el = card.select_one('[data-testid="job-card-company"]')
    location_el = card.select_one('[data-testid="job-card-location"]')
    card_text = card.get_text(" ", strip=True)
    salary_match = _SALARY_RE.search(card_text)
    return {
        "company": company_el.get_text(strip=True) if company_el else "Unknown",
        "location": (
            location_el.get_text(strip=True) if location_el else "Unknown"
        ),
        "salary": salary_match.group(0) if salary_match else "",
    }


class ZipRecruiterProvider:
    """Search ZipRecruiter via the public SSR search page (no auth)."""

    name = "ziprecruiter"

    # -- search ---------------------------------------------------------
    def search(
        self, query: str, location: str, limit: int, remote_only: bool
    ) -> list[dict[str, Any]]:
        jobs: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        page = 1
        with make_client() as client:
            while True:
                if limit and len(jobs) >= limit:
                    break
                if page > _MAX_PAGES:
                    break
                if page > 1:
                    polite_delay()
                params = {
                    "search": query,
                    "location": location or "",
                    "page": page,
                }
                try:
                    resp = client.get(SEARCH_URL, params=params)
                except Exception as exc:
                    log.warning("ZipRecruiter request failed: %s", exc)
                    break
                if resp.status_code in (403, 429):
                    compliance.record_block(self.name)
                    log.warning(
                        "ZipRecruiter pushed back (HTTP %s); circuit breaker "
                        "tripped, returning what we have",
                        resp.status_code,
                    )
                    break
                if resp.status_code >= 400:
                    log.warning(
                        "ZipRecruiter HTTP %s; stopping", resp.status_code
                    )
                    break
                text = resp.text or ""
                if _CAPTCHA_RE.search(text):
                    log.warning(
                        "ZipRecruiter CAPTCHA/bot-check detected; stopping "
                        "(never bypassed)"
                    )
                    break
                soup = BeautifulSoup(text, "lxml")
                items = _extract_itemlist(soup)
                if not items:
                    log.debug("ZipRecruiter: no ItemList on page %d", page)
                    break
                cards = soup.select('div[class*="job_result"]')
                new_this_page = 0
                for idx, item in enumerate(items):
                    if limit and len(jobs) >= limit:
                        break
                    url = item["url"]
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    card = cards[idx] if idx < len(cards) else None
                    meta = _card_meta(card) if card is not None else {
                        "company": "Unknown", "location": "Unknown",
                        "salary": "",
                    }
                    if remote_only and "remote" not in (
                        meta["location"] + " " + meta["salary"]
                    ).lower():
                        continue
                    job = {
                        "id": make_job_id(self.name, url),
                        "title": item["name"],
                        "company": meta["company"],
                        "location": meta["location"],
                        "url": url,
                        "board": self.name,
                        "snippet": meta["salary"],
                        **compliance.result_risk_tag(self.name),
                    }
                    jobs.append(job)
                    new_this_page += 1
                if new_this_page == 0:
                    break  # no progress -> stop paginating
                page += 1
        log.info(
            "ZipRecruiter: %d jobs for %r in %r", len(jobs), query, location
        )
        return jobs

    # -- details --------------------------------------------------------
    def get_details(self, payload: str) -> dict[str, Any]:
        """Fetch the full description for a job URL (the id payload)."""
        url = payload
        try:
            with make_client() as client:
                polite_delay()
                resp = client.get(url)
                if resp.status_code in (403, 429):
                    compliance.record_block(self.name)
                    return {
                        "url": url,
                        "board": self.name,
                        "error": f"Blocked by ZipRecruiter (HTTP {resp.status_code})",
                    }
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text or "", "lxml")
                title = company = description = ""
                for tag in soup.find_all("script", type="application/ld+json"):
                    try:
                        data = json.loads(tag.string or "")
                    except (TypeError, json.JSONDecodeError):
                        continue
                    blocks = data if isinstance(data, list) else [data]
                    for block in blocks:
                        if (
                            not isinstance(block, dict)
                            or block.get("@type") != "JobPosting"
                        ):
                            continue
                        title = str(block.get("title") or title).strip()
                        org = block.get("hiringOrganization") or {}
                        if isinstance(org, dict):
                            company = str(org.get("name") or company).strip()
                        if block.get("description"):
                            description = strip_html(
                                str(block.get("description"))
                            )
                if not title:
                    og_title = soup.find("meta", property="og:title")
                    if og_title and og_title.get("content"):
                        title = str(og_title["content"]).strip()
                if not title:
                    h1 = soup.find("h1")
                    title = h1.get_text(strip=True) if h1 else "Unknown"
                if not description:
                    main = soup.find("main") or soup.find("article")
                    if main:
                        description = main.get_text("\n", strip=True)[:20000]
                return {
                    "url": url,
                    "board": self.name,
                    "title": title or "Unknown",
                    "company": company or "Unknown",
                    "description": description,
                    "requirements": "",
                    "apply_url": url,
                }
        except Exception as exc:
            log.warning("ZipRecruiter details failed for %s: %s", url, exc)
            return {"url": url, "board": self.name, "error": str(exc)}


def get_providers() -> dict[str, ZipRecruiterProvider]:
    """Provider registry entry (wired in by the parent; no server import)."""
    return {"ziprecruiter": ZipRecruiterProvider()}

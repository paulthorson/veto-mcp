#!/usr/bin/env python3
"""Provider contract kit — Initiative 09, epic 1.

This module is the single place that defines what a Veto connector *is*:

* ``JobPosting`` / ``JobDetail`` — the normalized search/detail schema every
  provider must emit (and that conformance tests validate against).
* ``TermsClass`` — robots/ToS classification for every provider, aligned
  with the risk tiers in ``compliance.py`` (``official`` / ``scraping``).
* ``PROVIDER_BUDGETS`` — declarative daily budgets and cooldowns per
  provider. Enforcement stays in ``compliance.py`` (daily budgets,
  circuit breakers, recovery streaks); this kit only declares the numbers
  so tests and the scorecard can reason about them.
* ``ConnectorManifest`` — the proof-of-value declaration every connector
  carries: what it can do, why it may be blocked, what data it sends, and
  which actions require confirmation. The Q2 gate requires every connector
  to pass one capability contract *and* one policy test suite; the manifest
  is the capability contract's machine-readable form.
* ``validate_job_posting`` / ``validate_job_detail`` /
  ``validate_manifest`` / ``conformance_suite`` — the conformance tests.

Only stdlib is used (providers must never import ``server.py``).
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

log = logging.getLogger("job-apply-mcp.providers.contract")

# ---------------------------------------------------------------------------
# Terms / robots classification
# ---------------------------------------------------------------------------


class TermsClass(str, Enum):
    """ToS classification for a provider's data interface.

    Mirrors the risk tiers in compliance.py and names the *basis* for the
    classification so a reviewer can see why, not just which tier.
    """

    OFFICIAL_API = "official_api"  # vendor-published API; ToS-friendly
    KEY_GATED_API = "key_gated_api"  # official API, but needs a key the user
    #                               may not have; honest stub until then
    HTML_SCRAPING = "html_scraping"  # guest-endpoint/HTML scraping; ToS risk
    HONEST_STUB = "honest_stub"  # no working interface today; declares it


# Registry: provider name -> (TermsClass, basis, robots_url).
#
# Basis strings name the evidence: an official doc URL, a live probe, or a
# robots.txt policy. They are human-readable so the declaration stays honest.
TERMS_CLASSIFICATION: dict[str, tuple[TermsClass, str, str]] = {
    "greenhouse": (
        TermsClass.OFFICIAL_API,
        "Public Job Board API documented at "
        "https://developers.greenhouse.io/; live-probed on 2026-09-10",
        "https://boards-api.greenhouse.io/robots.txt",
    ),
    "lever": (
        TermsClass.OFFICIAL_API,
        "Public postings API at https://api.lever.co/v0/postings; "
        "live-probed per-company tokens on 2026-09-10",
        "https://api.lever.co/robots.txt",
    ),
    "ashby": (
        TermsClass.OFFICIAL_API,
        "Public posting API at https://api.ashbyhq.com/posting-api; "
        "live-probed on 2026-09-10",
        "https://api.ashbyhq.com/robots.txt",
    ),
    "adzuna": (
        TermsClass.KEY_GATED_API,
        "Official API at https://developer.adzuna.com/ requires "
        "ADZUNA_APP_ID/ADZUNA_APP_KEY; honest stub without them",
        "https://www.adzuna.com/robots.txt",
    ),
    "ziprecruiter": (
        TermsClass.HTML_SCRAPING,
        "Guest HTML endpoints; ToS risk acknowledged in compliance.py "
        "'scraping' tier; robots.txt honored",
        "https://www.ziprecruiter.com/robots.txt",
    ),
    "glassdoor": (
        TermsClass.HONEST_STUB,
        "Declared stub: no working public interface; search raises "
        "NotImplementedError rather than pretending",
        "https://www.glassdoor.com/robots.txt",
    ),
    "linkedin": (
        TermsClass.HTML_SCRAPING,
        "Fill-only browser flow; 'scraping' tier in compliance.py",
        "https://www.linkedin.com/robots.txt",
    ),
    "indeed": (
        TermsClass.HTML_SCRAPING,
        "'scraping' tier in compliance.py",
        "https://www.indeed.com/robots.txt",
    ),
}


def terms_for(provider_name: str) -> tuple[TermsClass, str, str]:
    """Return (TermsClass, basis, robots_url) for a provider.

    Unknown providers default to HONEST_STUB — the safe declaration — so a
    new connector can never silently claim a friendly interface.
    """
    return TERMS_CLASSIFICATION.get(
        provider_name,
        (
            TermsClass.HONEST_STUB,
            "No classification registered; treated as an honest stub "
            "until evidence is recorded",
            "",
        ),
    )


# NOTE on robots.txt: the canonical helper is
# ``providers._common.robots_allows(board, url)`` (cached, fail-open, and
# already honored by the scraping-tier providers). This kit does not ship
# a second implementation; the per-provider robots.txt URLs live in
# TERMS_CLASSIFICATION above so reviewers can audit the policy directly.


# ---------------------------------------------------------------------------
# Budgets and cooldowns — derived from compliance.py (single source of truth)
# ---------------------------------------------------------------------------
#
# Enforcement lives in compliance.py (tier daily budgets, exponential
# circuit-breaker cooldowns). This kit exposes the *same* numbers so the
# scorecard and tests can reason about them without maintaining a second
# table that could drift from enforcement. Registered HONEST_STUB
# connectors get a zero budget: they perform no searches, so displaying
# any budget would be dishonest.


def budget_for(provider_name: str) -> tuple[int, int]:
    """Return (daily_budget, base_cooldown_s) for a provider.

    Derived from ``compliance.py``: the tier budget for the provider's
    risk tier and the circuit-breaker's base cooldown (the actual cooldown
    doubles per consecutive block, capped at 24h — see
    ``compliance.record_block``). Unknown or stub providers get (0, 3600):
    no budget, long cooldown — the safe default until evidence exists.
    """
    base_cooldown = 3600
    try:
        import compliance

        base_cooldown = int(compliance.BLOCK_COOLDOWN_BASE_SECONDS)
        terms, _, _ = terms_for(provider_name)
        if terms is TermsClass.HONEST_STUB:
            return 0, base_cooldown
        tier = compliance.board_tier(provider_name)
        daily = int(compliance.DEFAULT_SEARCH_BUDGET.get(tier, 0))
        return daily, base_cooldown
    except Exception as exc:  # compliance unavailable: fail safe
        log.warning("budget_for: falling back to safe default: %s", exc)
        return 0, base_cooldown


# ---------------------------------------------------------------------------
# Normalized search/detail schema
# ---------------------------------------------------------------------------


@dataclass
class JobPosting:
    """Normalized search result. Every provider's ``search()`` must emit
    dicts that validate against this schema."""

    id: str  # self-describing job id: "<board>:<base64url(payload)>"
    title: str
    company: str
    location: str
    url: str
    board: str  # provider token, e.g. "greenhouse"
    snippet: str = ""
    remote: bool = False
    posted_date: str = ""  # ISO-8601 date or "" when unknown
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class JobDetail:
    """Normalized detail record. Every provider's ``get_details()`` must
    emit dicts that validate against this schema (or an error dict with
    exactly the keys ``{"board", "payload", "error"}`` / ``{"url", "board",
    "error"}``)."""

    url: str
    board: str
    title: str
    company: str
    location: str
    description: str
    apply_url: str = ""
    departments: list[str] = field(default_factory=list)
    employment_type: str = ""
    remote: bool = False
    posted_date: str = ""
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str = ""
    # Apply-readiness enrichment (epic 2): what the ATS API reveals about
    # the application surface, without submitting anything.
    application_questions: int = 0
    custom_fields: list[str] = field(default_factory=list)
    closing_date: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_POSTING_REQUIRED = ("id", "title", "company", "location", "url", "board")
_DETAIL_REQUIRED = ("url", "board", "title", "company", "location", "description")


def validate_job_posting(raw: dict[str, Any]) -> list[str]:
    """Return a list of conformance problems (empty = conforms)."""
    problems: list[str] = []
    for key in _POSTING_REQUIRED:
        if not raw.get(key):
            problems.append(f"missing required field: {key}")
    job_id = str(raw.get("id") or "")
    if job_id and ":" not in job_id:
        problems.append("id is not self-describing (<board>:<payload>)")
    board = str(raw.get("board") or "")
    if job_id and board and not job_id.startswith(board + ":"):
        problems.append("id prefix does not match board")
    return problems


def validate_job_detail(raw: dict[str, Any]) -> list[str]:
    """Return conformance problems (empty = conforms).

    Error dicts (``{"error": ...}``) conform only when they carry exactly
    the documented error shape: a truthy ``error`` plus the board context.
    """
    if raw.get("error"):
        problems: list[str] = []
        if not raw.get("board"):
            problems.append("error dict missing board context")
        return problems
    problems = []
    for key in _DETAIL_REQUIRED:
        if raw.get(key) in (None, ""):
            problems.append(f"missing required field: {key}")
    if not isinstance(raw.get("departments", []), list):
        problems.append("departments must be a list")
    return problems


# ---------------------------------------------------------------------------
# Connector manifest — the proof-of-value declaration
# ---------------------------------------------------------------------------


@dataclass
class ConnectorManifest:
    """What every connector declares before release (roadmap proof of value).

    * ``what_it_can_do`` — capability contract in plain language.
    * ``why_it_may_be_blocked`` — honest limitations: ToS, credentials,
      CAPTCHA, rate limits, probe results.
    * ``what_data_it_sends`` — every byte that leaves the device, named.
    * ``what_requires_confirmation`` — actions that need the human's
      explicit go-ahead at the moment of action.
    """

    name: str
    connector_type: str  # "job_provider" | "ats" | "channel" | "calendar"
    what_it_can_do: list[str]
    why_it_may_be_blocked: list[str]
    what_data_it_sends: list[str]
    what_requires_confirmation: list[str]
    official_interface: str = ""
    interface_basis: str = ""

    def validate(self) -> list[str]:
        """Return conformance problems (empty = conforms).

        A manifest is complete only when all four proof-of-value sections
        are non-empty — an empty section is a missing declaration, which
        blocks release under the Q2 gate.
        """
        problems: list[str] = []
        if not self.name:
            problems.append("manifest missing name")
        for section in (
            "what_it_can_do",
            "why_it_may_be_blocked",
            "what_data_it_sends",
            "what_requires_confirmation",
        ):
            if not getattr(self, section):
                problems.append(f"manifest section empty: {section}")
        return problems

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Registered manifests for the built-in job providers. Communication
# channels and the calendar handoff register their own manifests in
# initiatives/i09 (channels/registry.py, calendar_handoff.py).
PROVIDER_MANIFESTS: dict[str, ConnectorManifest] = {}


def _register_manifest(manifest: ConnectorManifest) -> ConnectorManifest:
    PROVIDER_MANIFESTS[manifest.name] = manifest
    return manifest


_register_manifest(
    ConnectorManifest(
        name="greenhouse",
        connector_type="job_provider",
        what_it_can_do=[
            "Search jobs across curated Greenhouse-hosted company boards "
            "via the public Job Board API (no auth).",
            "Fetch full job details including departments, offices, "
            "metadata, and application questions.",
        ],
        why_it_may_be_blocked=[
            "Direct application submission is NOT possible: the Job Board "
            "API's POST applications endpoint requires an employer-issued "
            "API key a job seeker cannot obtain (verified against official "
            "docs 2026-09-10). Greenhouse applies stay browser-assisted.",
            "Boards are per-company tokens; tokens churn as employers join "
            "or leave Greenhouse.",
        ],
        what_data_it_sends=[
            "Search query, location filter, and limit to "
            "boards-api.greenhouse.io over HTTPS.",
            "Job-id payloads (board token + job id) to fetch details.",
        ],
        what_requires_confirmation=[
            "Browser-assisted application submit (handled by browser_apply "
            "with confirm=True only).",
        ],
        official_interface="https://developers.greenhouse.io/",
        interface_basis="Official public API; live-probed 2026-09-10.",
    )
)

_register_manifest(
    ConnectorManifest(
        name="lever",
        connector_type="job_provider",
        what_it_can_do=[
            "Search jobs across curated Lever-hosted company boards via the "
            "public postings API (no auth).",
            "Fetch full posting details including categories, workplace "
            "type, lists (departments/teams), and apply URLs.",
        ],
        why_it_may_be_blocked=[
            "Direct application submission is NOT possible: POST apply "
            "requires a Lever-issued POST API key (probe returned 403 "
            "'You need an API key' on 2026-09-10). Lever applies stay "
            "browser-assisted.",
            "Public API is per-company; tokens 404 when employers leave "
            "Lever and are skipped gracefully.",
        ],
        what_data_it_sends=[
            "Search query, location filter, and limit to api.lever.co "
            "over HTTPS.",
            "Company token + posting id to fetch details.",
        ],
        what_requires_confirmation=[
            "Browser-assisted application submit (confirm=True only).",
        ],
        official_interface="https://github.com/lever/postings-api",
        interface_basis="Official public API; live-probed 2026-09-10.",
    )
)

_register_manifest(
    ConnectorManifest(
        name="ashby",
        connector_type="job_provider",
        what_it_can_do=[
            "Search jobs across curated Ashby-hosted company boards via the "
            "public posting API (no auth).",
            "Fetch posting details including department, team, employment "
            "type, location, remote flag, and apply URL.",
        ],
        why_it_may_be_blocked=[
            "Direct application submission is NOT possible: "
            "applicationForm.submit returned 401 Unauthorized on live "
            "non-mutating probes (2026-09-10). Ashby applies stay "
            "browser-assisted.",
            "The detail endpoint re-fetches the whole board and finds the "
            "posting by id; if Ashby changes the board shape, details "
            "degrade gracefully.",
        ],
        what_data_it_sends=[
            "Search query, location filter, and limit to "
            "api.ashbyhq.com/posting-api over HTTPS.",
            "Board token + posting id to fetch details.",
        ],
        what_requires_confirmation=[
            "Browser-assisted application submit (confirm=True only).",
        ],
        official_interface="https://developers.ashbyhq.com/docs/creating-a-custom-careers-page",
        interface_basis="Official public API; live-probed 2026-09-10.",
    )
)

_register_manifest(
    ConnectorManifest(
        name="adzuna",
        connector_type="job_provider",
        what_it_can_do=[
            "Search jobs via the official Adzuna API when ADZUNA_APP_ID and "
            "ADZUNA_APP_KEY are configured.",
        ],
        why_it_may_be_blocked=[
            "Without API credentials the provider raises RuntimeError on "
            "search — it is an honest stub, not a working connector.",
            "get_details is not implemented even with credentials.",
        ],
        what_data_it_sends=[
            "Search query, location, and the user's Adzuna app credentials "
            "to api.adzuna.com over HTTPS (only when configured).",
        ],
        what_requires_confirmation=[
            "Credential configuration (user provides their own Adzuna app "
            "key; Veto never invents one).",
        ],
        official_interface="https://developer.adzuna.com/",
        interface_basis="Official API; key-gated.",
    )
)

_register_manifest(
    ConnectorManifest(
        name="ziprecruiter",
        connector_type="job_provider",
        what_it_can_do=[
            "Search jobs via guest HTML endpoints with polite delays, daily "
            "budgets, and robots.txt honored.",
        ],
        why_it_may_be_blocked=[
            "Scraping-tier board: HTML scraping can violate ZipRecruiter's "
            "ToS and trigger 403/429, CAPTCHAs, or IP rate-limiting; the "
            "circuit breaker pauses it automatically.",
            "Requires the user to explicitly acknowledge the ToS risk "
            "(compliance 'standard' mode) before use.",
        ],
        what_data_it_sends=[
            "Search query and location to ziprecruiter.com guest endpoints "
            "over HTTPS, at a human pace.",
        ],
        what_requires_confirmation=[
            "ToS-risk acknowledgment before first scraping-tier search.",
            "Browser-assisted application submit (confirm=True only).",
        ],
        official_interface="",
        interface_basis="No official public API; guest HTML endpoints.",
    )
)

_register_manifest(
    ConnectorManifest(
        name="glassdoor",
        connector_type="job_provider",
        what_it_can_do=[
            "Nothing yet: this is a declared stub so the connector list "
            "stays honest about coverage.",
        ],
        why_it_may_be_blocked=[
            "No working public interface exists in Veto today; search "
            "raises NotImplementedError rather than returning fake results.",
        ],
        what_data_it_sends=[
            "Nothing: the stub performs no network calls.",
        ],
        what_requires_confirmation=[
            "Enabling a future real implementation (would need a new "
            "manifest and review).",
        ],
        official_interface="",
        interface_basis="Declared stub; no interface probed successfully.",
    )
)

_register_manifest(
    ConnectorManifest(
        name="ats_direct",
        connector_type="ats",
        what_it_can_do=[
            "Registry of verified direct-submit ATS endpoints. Today the "
            "registry is empty of verified endpoints: can_apply_direct() "
            "returns False for every board and apply_direct() never "
            "performs a network submit.",
        ],
        why_it_may_be_blocked=[
            "Ashby applicationForm.submit: 401 Unauthorized on live probes "
            "(2026-09-10).",
            "Lever POST apply: requires a Lever-issued POST API key "
            "(403 'You need an API key', 2026-09-10).",
            "Greenhouse POST applications: requires an employer-issued Job "
            "Board API key a job seeker cannot obtain (official docs).",
            "An endpoint is only submittable after flipping its registry "
            "entry to 'verified' with a field spec.",
        ],
        what_data_it_sends=[
            "Nothing today: no verified endpoint exists, so no application "
            "payload ever leaves the device through this path.",
        ],
        what_requires_confirmation=[
            "Any future direct submit would require explicit confirmation "
            "at the moment of action (roadmap constraint 02).",
        ],
        official_interface="https://developers.ashbyhq.com/ + Lever postings API + Greenhouse Job Board API docs",
        interface_basis="Live non-mutating probes + official docs, 2026-09-10.",
    )
)


def manifest_for(name: str) -> ConnectorManifest | None:
    """Return the registered manifest for a connector, or None."""
    return PROVIDER_MANIFESTS.get(name)


def all_manifests() -> list[ConnectorManifest]:
    """All registered job-provider/ATS manifests, sorted by name."""
    return [PROVIDER_MANIFESTS[k] for k in sorted(PROVIDER_MANIFESTS)]


# ---------------------------------------------------------------------------
# Conformance suite — the Q2 gate's "capability contract" half
# ---------------------------------------------------------------------------


def conformance_suite(
    provider: Any,
    search_fixture: list[dict[str, Any]] | None = None,
    detail_fixture: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Run the capability-contract checks for one provider.

    Checks (each returns a ``{"check", "passed", "detail"}`` record):
    1. manifest exists and is complete (the four proof-of-value sections).
    2. terms classification is registered.
    3. budget/cooldown are registered.
    4. search fixture rows validate against the JobPosting schema.
    5. detail fixture validates against the JobDetail schema.
    6. provider exposes ``search`` and ``get_details`` callables.
    """
    results: list[dict[str, Any]] = []

    def record(check: str, passed: bool, detail: str = "") -> None:
        results.append({"check": check, "passed": passed, "detail": detail})

    name = getattr(provider, "name", None) or type(provider).__name__
    manifest = PROVIDER_MANIFESTS.get(name)
    if manifest is None:
        record("manifest.registered", False, f"no manifest for {name!r}")
    else:
        problems = manifest.validate()
        record(
            "manifest.complete",
            not problems,
            "; ".join(problems) if problems else "all four proof-of-value sections present",
        )
    terms, basis, robots_url = terms_for(name)
    record(
        "terms.classified",
        terms is not TermsClass.HONEST_STUB or name in TERMS_CLASSIFICATION,
        f"{terms.value}; basis: {basis[:80]}",
    )
    daily, cooldown = budget_for(name)
    try:
        import compliance

        expected_daily = compliance.DEFAULT_SEARCH_BUDGET.get(
            compliance.board_tier(name), 0
        )
        if terms is TermsClass.HONEST_STUB:
            expected_daily = 0
        budget_ok = daily == expected_daily and cooldown > 0
        budget_detail = (
            f"daily={daily} cooldown_s={cooldown} "
            f"(matches compliance tier budget: {budget_ok})"
        )
    except Exception:
        budget_ok = cooldown > 0
        budget_detail = f"daily={daily} cooldown_s={cooldown}"
    record("budget.declared", budget_ok, budget_detail)
    record(
        "interface.search",
        callable(getattr(provider, "search", None)),
        "provider.search callable" if callable(getattr(provider, "search", None)) else "missing search()",
    )
    record(
        "interface.get_details",
        callable(getattr(provider, "get_details", None)),
        "provider.get_details callable"
        if callable(getattr(provider, "get_details", None))
        else "missing get_details()",
    )
    if search_fixture:
        posting_problems = [
            p for row in search_fixture for p in validate_job_posting(row)
        ]
        record(
            "schema.search_rows",
            not posting_problems,
            "; ".join(posting_problems[:5])
            if posting_problems
            else f"{len(search_fixture)} fixture rows conform",
        )
    if detail_fixture:
        detail_problems = validate_job_detail(detail_fixture)
        record(
            "schema.detail",
            not detail_problems,
            "; ".join(detail_problems) if detail_problems else "detail fixture conforms",
        )
    return results


def suite_passed(results: list[dict[str, Any]]) -> bool:
    """True when every conformance check passed."""
    return all(r["passed"] for r in results)

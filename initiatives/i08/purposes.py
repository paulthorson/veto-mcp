#!/usr/bin/env python3
"""Initiative 08, Epic 2 — purpose-specific consent.

Four roadmap-named purposes, each with a versioned definition the
contributor can read. Everything is OFF by default ("nothing is
transmitted by default"). Consent has two layers:

1. Standing grant — the contributor opts into a purpose. Required before
   ANY collection for the diagnostics, provider-health, and research
   purposes. The persona-improvements purpose keeps its legacy per-bundle
   confirm flow (preview + confirmed submit) as its consent; a standing
   grant is optional and additive there.
2. Per-bundle consent — recorded in the append-only consent log for every
   staged bundle: purpose, purpose definition version, scrub ruleset
   version, bundle hash.

Withdrawing a purpose stops FUTURE collection only. Removal of already
accepted data follows the receipt's removal path "where possible" — the
limits are stated honestly at consent time (see ``receipts``).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PURPOSE_CONSENT_FILENAME = "purpose_consent.json"


class PurposeError(ValueError):
    """Unknown purpose id."""


PURPOSES: dict[str, dict[str, Any]] = {
    "product_diagnostics": {
        "version": "1",
        "title": "Product diagnostics",
        "definition": (
            "Crash and error signatures plus feature usage counts, used to "
            "fix bugs and measure whether features work. NEVER includes "
            "message content, resume text, transcripts, job descriptions, "
            "or any other content field — counts and signatures only."
        ),
        "contents": (
            "event_name, count, veto_version, os_class, error_class. "
            "No content fields."
        ),
        "requires_standing_grant": True,
    },
    "persona_improvements": {
        "version": "1",
        "title": "Persona improvements",
        "definition": (
            "Scrubbed training-session excerpts (mock interviews, "
            "soft-skill drills, AI-proficiency exercises) plus your star "
            "ratings, used to improve Veto's AI personas (interviewer / "
            "adversary characters). Excerpts are scrubbed on-device per the "
            "published rule set; you preview the exact bytes before "
            "confirming each bundle."
        ),
        "contents": (
            "scrubbed transcript excerpts (length-capped), session metadata "
            "(type, persona, difficulty, score), star rating + note. "
            "No raw PII by contract; verified by scrub tests."
        ),
        "requires_standing_grant": False,
    },
    "provider_health": {
        "version": "1",
        "title": "Provider health",
        "definition": (
            "Per-provider success/failure/error-class aggregates (e.g. "
            "greenhouse: 42 searches, 3 blocked, 0 captcha), used to keep "
            "connectors reliable. No job content, no search queries — "
            "aggregate counters only."
        ),
        "contents": (
            "provider_name, window, searches, successes, blocked, "
            "captcha_hits, error_classes. No content fields."
        ),
        "requires_standing_grant": True,
    },
    "research": {
        "version": "1",
        "title": "Research contributions",
        "definition": (
            "Aggregated, cohort-level statistics only, used for public "
            "research on job-search outcomes. Minimum 25 contributing "
            "devices per published slice; sparse or identifying slices are "
            "suppressed, never shown. NEVER record-level rows."
        ),
        "contents": (
            "Cohort aggregates only (counts, rates by slice). Slices below "
            "the minimum cohort are suppressed. No record-level rows, no "
            "content fields."
        ),
        "requires_standing_grant": True,
    },
}

#: Honest removal limits, stated at consent time per purpose.
REMOVAL_LIMITS: dict[str, str] = {
    "product_diagnostics": (
        "Diagnostic aggregates cannot be un-published per contributor once "
        "merged; stop future collection by withdrawing consent."
    ),
    "persona_improvements": (
        "Bundles you deliver (e.g. via PR) can be requested removed by "
        "commenting on the delivery or contacting the maintainer; once "
        "merged into training data, removal may be impossible. Staged "
        "bundles in your local outbox can be deleted any time."
    ),
    "provider_health": (
        "Health aggregates cannot be un-published per contributor once "
        "merged; stop future collection by withdrawing consent."
    ),
    "research": (
        "Published research aggregates cannot be un-published per "
        "contributor; stop future collection by withdrawing consent."
    ),
}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _consent_path(base_dir: Path) -> Path:
    return Path(base_dir) / "contributions" / PURPOSE_CONSENT_FILENAME


def _load_consent(base_dir: Path) -> dict[str, Any]:
    try:
        data = json.loads(_consent_path(base_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("grants", {})
    data.setdefault("withdrawals", {})
    return data


def _atomic_write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    tmp.replace(path)


def _check_purpose(purpose: str) -> dict[str, Any]:
    definition = PURPOSES.get(purpose)
    if definition is None:
        raise PurposeError(
            f"Unknown purpose {purpose!r}. Known: {sorted(PURPOSES)}.")
    return definition


def purpose_definitions() -> dict[str, dict[str, Any]]:
    """Versioned purpose definitions for the consent UI and methodology."""
    return {pid: dict(defn) for pid, defn in PURPOSES.items()}


def grant_consent(purpose: str, base_dir: Path,
                  actor: str = "user") -> dict[str, Any]:
    """Record a standing opt-in grant for ``purpose`` (append-only)."""
    definition = _check_purpose(purpose)
    data = _load_consent(base_dir)
    entry = {
        "granted_at": _utcnow(),
        "actor": actor,
        "purpose": purpose,
        "purpose_version": definition["version"],
        "definition": definition["definition"],
        "removal_limits": REMOVAL_LIMITS[purpose],
    }
    data["grants"].setdefault(purpose, []).append(entry)
    _atomic_write_json(_consent_path(base_dir), data)
    return {"granted": True, "purpose": purpose,
            "purpose_version": definition["version"]}


def withdraw_consent(purpose: str, base_dir: Path,
                     actor: str = "user") -> dict[str, Any]:
    """Withdraw a standing grant. Stops FUTURE collection only."""
    _check_purpose(purpose)
    data = _load_consent(base_dir)
    entry = {
        "withdrawn_at": _utcnow(),
        "actor": actor,
        "purpose": purpose,
        "note": ("Stops future collection for this purpose. Already "
                 "accepted data follows the receipt's removal path 'where "
                 "possible'."),
    }
    data["withdrawals"].setdefault(purpose, []).append(entry)
    _atomic_write_json(_consent_path(base_dir), data)
    return {"withdrawn": True, "purpose": purpose}


def _latest_event(data: dict[str, Any], purpose: str) -> tuple[str, str] | None:
    """Latest grant/withdrawal for a purpose: (kind, timestamp) or None."""
    latest: tuple[str, str] | None = None
    for grant in data.get("grants", {}).get(purpose, []):
        ts = str(grant.get("granted_at", ""))
        if latest is None or ts > latest[1]:
            latest = ("grant", ts)
    for withdrawal in data.get("withdrawals", {}).get(purpose, []):
        ts = str(withdrawal.get("withdrawn_at", ""))
        if latest is None or ts > latest[1]:
            latest = ("withdrawal", ts)
    return latest


def consent_state(purpose: str, base_dir: Path) -> dict[str, Any]:
    """Current consent state for a purpose. Defaults to NOT granted."""
    definition = _check_purpose(purpose)
    data = _load_consent(base_dir)
    latest = _latest_event(data, purpose)
    granted = latest is not None and latest[0] == "grant"
    return {
        "purpose": purpose,
        "purpose_version": definition["version"],
        "granted": granted,
        "requires_standing_grant": definition["requires_standing_grant"],
        "last_event": latest[0] if latest else None,
    }


def consent_summary(base_dir: Path) -> dict[str, Any]:
    """Consent state for all purposes — the consent dashboard view."""
    states = {pid: consent_state(pid, base_dir) for pid in PURPOSES}
    return {
        "purposes": states,
        "any_granted": any(s["granted"] for s in states.values()),
        "note": ("Everything is OFF by default. Grants are standing "
                 "opt-ins; each staged bundle additionally records "
                 "per-bundle consent with purpose, purpose version, scrub "
                 "ruleset version, and bundle hash."),
    }


def require_grant(purpose: str, base_dir: Path) -> dict[str, Any] | None:
    """Return an error dict if ``purpose`` may not be collected now.

    Returns None when collection is allowed. The persona_improvements
    purpose keeps its legacy per-bundle confirm flow and does not require
    a standing grant; the other three purposes do. A grant is valid only
    for the definition version it was given against: if the definition
    changed since the grant, the user must re-grant after reading the new
    definition (methodology: field additions are a new version and
    require re-consent).
    """
    definition = _check_purpose(purpose)
    if not definition["requires_standing_grant"]:
        return None
    state = consent_state(purpose, base_dir)
    if state["granted"]:
        grant_version = _latest_grant_version(purpose, base_dir)
        if grant_version == definition["version"]:
            return None
        return {
            "error": (
                f"Purpose {purpose!r} definition changed since your grant "
                f"(granted v{grant_version}, current v{definition['version']}). "
                f"Re-grant explicitly after reading the new definition: "
                f"{definition['definition']}"
            ),
            "purpose": purpose,
            "removal_limits": REMOVAL_LIMITS[purpose],
        }
    return {
        "error": (
            f"Purpose {purpose!r} is not granted. Nothing is collected by "
            f"default — grant it explicitly first "
            f"(grant_consent({purpose!r})), after reading the purpose "
            f"definition: {definition['definition']}"
        ),
        "purpose": purpose,
        "removal_limits": REMOVAL_LIMITS[purpose],
    }


def _latest_grant_version(purpose: str, base_dir: Path) -> str | None:
    """Purpose version recorded on the latest grant event, if any."""
    data = _load_consent(base_dir)
    grants = data.get("grants", {}).get(purpose, [])
    if not grants:
        return None
    latest = max(grants, key=lambda g: str(g.get("granted_at", "")))
    return latest.get("purpose_version")


def collect_for_purpose(purpose: str, base_dir: Path,
                        payload: dict[str, Any]) -> dict[str, Any]:
    """Gate a purpose-scoped collection behind its standing grant.

    Refuses (returning an error dict, collecting nothing) unless the
    purpose is granted. Tags the payload with purpose + purpose version
    so downstream stages can verify scope.
    """
    error = require_grant(purpose, base_dir)
    if error is not None:
        return error
    definition = _check_purpose(purpose)
    tagged = dict(payload)
    tagged["contribution_purpose"] = purpose
    tagged["purpose_version"] = definition["version"]
    tagged["collected_at"] = _utcnow()
    return {"collected": True, "purpose": purpose, "payload": tagged}

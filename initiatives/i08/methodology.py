#!/usr/bin/env python3
"""Initiative 08, Epic 5 — public methodology.

Generates the public contribution methodology document (schemas,
exclusions, known bias, governance decisions, sanitized incident log).
PUBLIC-REPO HYGIENE: the generator only ever emits authored text plus
sanitized aggregates (incident counts/classes). It NEVER includes
receipts, bundles, cohort contents, contributor-identifying content, or
payload bytes. ``hygiene_check`` asserts this on the generated text.

Methodology changes are versioned; the consent UI links the exact version
the contributor approved.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import aggregation, purposes, quarantine, scrub

METHODOLOGY_VERSION = "0.1"

#: Governance decisions recorded for Initiative 08. Role names only —
#: never personal emails or identifying info.
GOVERNANCE_DECISIONS: list[dict[str, str]] = [
    {
        "id": "D-01",
        "decision": "On-device scrubbing before preview; no server-side scrubbing.",
        "rationale": ("Data must not leave the device before the contributor "
                      "approves the exact bytes. Server-side scrubbing would "
                      "collapse the trust claim."),
        "owner": "roadmap owner",
        "status": "implemented",
    },
    {
        "id": "D-02",
        "decision": "Preview-exactness over differential-privacy noise.",
        "rationale": ("The contributor inspects the exact bytes that leave. "
                      "DP noise would break byte-exact preview and add "
                      "trust cost for small-cohort utility that dies anyway. "
                      "Sparse slices are suppressed, not perturbed."),
        "owner": "roadmap owner",
        "status": "implemented",
    },
    {
        "id": "D-03",
        "decision": "Minimum cohort k=25 per published slice; sparse slices suppressed entirely.",
        "rationale": ("k-anonymity-style floor against re-identification via "
                      "small slices. Suppressed slices are never shown as "
                      "'low N' or interpolated."),
        "owner": "roadmap owner",
        "status": "implemented",
    },
    {
        "id": "D-04",
        "decision": "Quarantine lock is not clearable by user settings toggles.",
        "rationale": ("A scrub failure that a settings toggle could clear "
                      "would make the quarantine contract decorative. Only "
                      "the named-specialist clearing + reviewer verification "
                      "path unlocks sending."),
        "owner": "roadmap owner",
        "status": "implemented",
    },
    {
        "id": "D-05",
        "decision": "Purpose-level consent (not per-field, not one global toggle).",
        "rationale": ("Per-field consent causes consent fatigue and "
                      "meaningless clicks; one global toggle over-collects. "
                      "Purpose-level is the right granularity; field-level "
                      "protection is enforced by schema exclusion instead."),
        "owner": "roadmap owner",
        "status": "implemented",
    },
    {
        "id": "D-06",
        "decision": "Receipts are local-only and never published.",
        "rationale": ("Receipts contain bundle hashes — a linkage primitive. "
                      "They stay on the contributor's machine and are "
                      "exportable only by explicit user action."),
        "owner": "roadmap owner",
        "status": "implemented",
    },
    {
        "id": "D-07",
        "decision": "Impact attribution only for actually-cited bundles.",
        "rationale": ("Attributing product changes to uncited bundles would "
                      "be invented social proof. 'Not yet cited' is stated "
                      "plainly instead."),
        "owner": "roadmap owner",
        "status": "implemented",
    },
]

EXCLUSIONS: list[str] = [
    "Verbatim interview transcripts (excerpts only, length-capped, entity-stripped).",
    "Contact details of any kind (emails, phones, handles, addresses).",
    "Credentials, API keys, tokens, and high-entropy secrets.",
    "Financial and government ID strings (IBAN/account/SSN-shaped).",
    "Absolute file paths and internal hostnames/IPs.",
    "Raw resume text, cover letters, and job descriptions in any telemetry.",
    "Record-level rows in research-purpose data (aggregates only).",
]

KNOWN_BIAS: list[str] = [
    "Contributors self-select: people who opt into sharing training data "
    "are not representative of all job seekers (likely more technical, "
    "more comfortable with tooling). Persona improvements tuned on this "
    "data may under-serve other candidate profiles.",
    "Training sessions skew toward the roles the contributor practiced for; "
    "rare role families are under-represented.",
    "Star ratings reflect the contributor's subjective experience, not an "
    "objective persona quality measure.",
    "Research aggregates inherit the same self-selection bias; slices are "
    "labeled with contributor counts so readers can judge.",
    "Device identity: aggregate bundles carry no device identifier, so the "
    "k>=25 cohort floor is enforced by the maintainer at publication, not "
    "cryptographically by the bundle. A malicious or buggy publisher could "
    "publish a slice below the floor; the floor is a policy control, not a "
    "mathematical one.",
    "Contributor-supplied rows: aggregates are built from bundles contributors "
    "deliver themselves. There is no Sybil resistance, contributor "
    "authentication, or outlier detection — a contributor could submit many "
    "bundles to skew a slice. Mitigations are the k>=25 floor, sparse-slice "
    "suppression, and the fact that delivery is a reviewed manual PR, not an "
    "open API. Research built on these aggregates should treat them as "
    "self-reported, not as a controlled sample.",
]

KNOWN_SCRUB_LIMITATIONS: list[str] = [
    "The name heuristic is best-effort: it can miss unusual names and can "
    "over-redact capitalized phrases. Contributors must check the preview.",
    "National ID formats beyond the US SSN shape are not specifically detected.",
    "IPv4 detection may over-redact version-like strings (e.g. 1.2.3.4).",
    "Heavily paraphrased or implied personal data ('my old boss at the "
    "fruit company') is not detectable by pattern rules.",
    "The contract is detect-and-quarantine, not provably perfect: misses "
    "trigger quarantine and a global send lock, they do not silently pass.",
]


def _purpose_section() -> str:
    parts = []
    for pid, defn in purposes.purpose_definitions().items():
        parts.append(
            f"### {defn['title']} (`{pid}`, definition v{defn['version']})\n\n"
            f"{defn['definition']}\n\n"
            f"Fields: {defn['contents']}\n\n"
            f"Standing grant required: "
            f"{'yes' if defn['requires_standing_grant'] else 'no — per-bundle confirm flow'}\n\n"
            f"Removal limits: {purposes.REMOVAL_LIMITS[pid]}\n")
    return "\n".join(parts)


def _scrub_section() -> str:
    lines = [
        f"Scrub ruleset version: **v{scrub.SCRUB_RULESET_VERSION}** "
        "(recorded on every bundle; rule changes never silently alter what "
        "'scrubbed' meant).",
        "",
        "Rules run on-device, before preview, in this order:",
        "",
    ]
    for rule in scrub.scrub_rules_report():
        lines.append(f"- **{rule['rule']}**: {rule['description']}")
    lines += ["", "Known limitations:", ""]
    lines += [f"- {item}" for item in KNOWN_SCRUB_LIMITATIONS]
    return "\n".join(lines)


def _aggregation_section() -> str:
    return "\n".join([
        f"Minimum cohort: **k >= {aggregation.DEFAULT_MIN_COHORT_K}** "
        "contributing devices per published slice (tunable; the active "
        "value is published with each release).",
        "",
        "- Slices below k are **suppressed entirely** — never shown as "
        "'low N', never interpolated.",
        "- Generalization ladder: exact value -> industry/category -> all; "
        "a sparse exact slice still contributes to a coarser slice when "
        "that slice itself meets k.",
        "- Research-purpose data **never ships record-level rows**; content "
        "fields are rejected by schema before aggregation.",
        "- Suppression (not noise) is the mechanism: it preserves the "
        "contributor's byte-exact preview.",
    ])


def _incident_section(base_dir: Path | None = None) -> str:
    summary = quarantine.incident_summary(base_dir)
    lines = [
        "Sanitized incident log — counts and check classes only. No payload "
        "content, no contributor-identifying information.",
        "",
        f"- Total quarantined payloads: {summary['total_quarantined']}",
        f"- Currently open incidents: {summary['open']}",
        f"- Closed (cleared) incidents: {summary['closed']}",
        f"- Sending currently locked: {summary['sending_locked']}",
        "",
    ]
    if summary["by_check"]:
        lines.append("Quarantines by check:")
        for check, count in sorted(summary["by_check"].items()):
            lines.append(f"- {check}: {count}")
    else:
        lines.append("No quarantine incidents recorded.")
    return "\n".join(lines)


def generate(base_dir: Path | None = None) -> str:
    """Generate the public methodology document text."""
    decisions = "\n".join(
        f"- **{d['id']}** ({d['status']}; owner: {d['owner']}): "
        f"{d['decision']} Rationale: {d['rationale']}"
        for d in GOVERNANCE_DECISIONS)
    exclusions = "\n".join(f"- {item}" for item in EXCLUSIONS)
    bias = "\n".join(f"- {item}" for item in KNOWN_BIAS)
    doc = f"""# Veto contribution methodology v{METHODOLOGY_VERSION}

How Veto learns from community patterns without turning private
job-search records into a hidden training corpus. This document is
public and contains no contributor-identifying content.

## 1. Purpose definitions

Everything is OFF by default. Each purpose below is granted separately.

{_purpose_section()}
## 2. Payload schemas

Per purpose (field lists are pinned; any field addition is a new
purpose-definition version and requires re-consent). Every bundle carries
`bundle_kind` (`persona_excerpts` or `aggregate_counters`) and the builder
for aggregate purposes *rejects* content fields (`transcript`, `answers`,
question/answer text, `rating_note`) — so a standing grant for research,
diagnostics, or provider health can never silently cover excerpts.

- product_diagnostics (`aggregate_counters`): session_count, by_source,
  score_buckets, total_questions_answered. Counters/signatures only.
- persona_improvements (`persona_excerpts`): scrubbed transcript excerpts
  (length-capped at {scrub.MAX_EXCERPT_CHARS} chars/turn), session metadata
  (type, persona, difficulty, score), star rating + note. Bundle schema
  `veto-contribution/1`, scrubbed with ruleset
  v{scrub.SCRUB_RULESET_VERSION}. The ONLY purpose that carries content,
  and it requires explicit per-bundle confirmation.
- provider_health (`aggregate_counters`): session_count, by_source,
  score_buckets, total_questions_answered, plus a telemetry_note stating
  provider-API telemetry is not yet wired (session-derived counters only).
- research (`aggregate_counters`): session_count, by_source,
  score_buckets, total_questions_answered. Cohort aggregates only. Never
  record-level rows; the k>=25 cohort floor applies at publication.

## 3. Scrub rule set

{_scrub_section()}

## 4. Aggregation rules

{_aggregation_section()}

## 5. Exclusions (never collected)

{exclusions}

## 6. Known bias

{bias}

## 7. Governance decisions

{decisions}

## 8. Incident log

{_incident_section(base_dir)}
"""
    return doc


def write_methodology_doc(path: Path,
                           base_dir: Path | None = None) -> dict[str, Any]:
    """Write the methodology doc to ``path`` (public-safe by construction)."""
    text = generate(base_dir)
    check = hygiene_check(text)
    if not check["passed"]:
        return {"error": "Methodology hygiene check failed.",
                "problems": check["problems"]}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return {"written": str(path), "version": METHODOLOGY_VERSION}


#: Markers that must never appear in the public methodology.
_HYGIENE_FORBIDDEN = (
    "receipt_id", "outbox_file", "@example.com", "BEGIN PRIVATE KEY",
    "[SECURITY_DATA]",
)


def hygiene_check(text: str) -> dict[str, Any]:
    """Assert the methodology text is public-safe.

    Fails on forbidden markers and on anything that looks like an email
    address or a private key block.
    """
    import re

    problems: list[str] = []
    for marker in _HYGIENE_FORBIDDEN:
        if marker in text:
            problems.append(f"forbidden marker present: {marker!r}")
    if re.search(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", text):
        problems.append("text contains an email-like string")
    if "PRIVATE KEY" in text:
        problems.append("text contains a private-key marker")
    return {"passed": not problems, "problems": problems}

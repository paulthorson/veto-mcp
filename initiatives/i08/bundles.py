#!/usr/bin/env python3
"""Initiative 08 — purpose-specific contribution bundle builders.

Every purpose gets its own bundle shape so the payload ALWAYS matches the
consent definition the user granted. This is the purpose-binding guarantee:
a standing grant for ``research`` can never silently cover transcript
excerpts, because the research builder cannot produce them.

Shapes:

- ``persona_improvements`` → ``persona_excerpts``: scrubbed transcript
  excerpts (per-bundle explicit confirmation). The only purpose that carries
  content.
- ``product_diagnostics`` → ``aggregate_counters``: counters/signatures
  only (session counts, score buckets, question totals). Content fields are
  rejected by the validator.
- ``provider_health`` → ``aggregate_counters``: aggregate counters only.
  Session-derived for now; provider-API telemetry is not yet wired (see
  ``integration_notes.md``) and the bundle says so.
- ``research`` → ``aggregate_counters``: aggregate counters built on-device.
  NEVER record-level rows. The k>=25 cohort floor applies at *publication*
  (maintainer side); the bundle carries no device identifier.

Validators (``validate_bundle``) reject any content field
(``transcript``, ``answers``, question/answer text, ``rating_note``) in an
aggregate bundle. Defense in depth: builders never emit them, and the
validator refuses them if they ever appear.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from . import purposes as _purposes
from . import scrub as _scrub

#: Bundle kinds. Recorded in every bundle as ``bundle_kind``.
KIND_PERSONA_EXCERPTS = "persona_excerpts"
KIND_AGGREGATE_COUNTERS = "aggregate_counters"

#: Purposes that must never carry content.
AGGREGATE_ONLY_PURPOSES = frozenset({
    "product_diagnostics", "provider_health", "research",
})

#: Free-text/content keys that must never appear in an aggregate bundle,
#: at any nesting level.
_CONTENT_KEYS = frozenset({
    "transcript", "answers", "answer", "question", "question_text",
    "answer_text", "rating_note", "text", "excerpt",
})


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _score_bucket(score: float | None) -> str:
    if score is None:
        return "unscored"
    if score < 60:
        return "0-59"
    if score < 70:
        return "60-69"
    if score < 80:
        return "70-79"
    if score < 90:
        return "80-89"
    return "90-100"


def _aggregate_stats(sessions: list[dict[str, Any]]) -> dict[str, Any]:
    """Counts-only statistics over session metadata. No text in, no text out."""
    by_source: dict[str, int] = {}
    buckets: dict[str, int] = {}
    total_questions = 0
    for s in sessions:
        src = str(s.get("source", "unknown"))
        by_source[src] = by_source.get(src, 0) + 1
        buckets[_score_bucket(s.get("score"))] = \
            buckets.get(_score_bucket(s.get("score")), 0) + 1
        qs = s.get("questions") or []
        total_questions += int(s.get("question_count", len(qs)))
    return {
        "session_count": len(sessions),
        "by_source": by_source,
        "score_buckets": buckets,
        "total_questions_answered": total_questions,
    }


def _find_content_keys(node: Any, path: str = "$") -> list[str]:
    """Paths of any content-bearing key in a nested structure."""
    hits: list[str] = []
    if isinstance(node, dict):
        for k, v in node.items():
            p = f"{path}.{k}"
            if k in _CONTENT_KEYS:
                hits.append(p)
            hits.extend(_find_content_keys(v, p))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            hits.extend(_find_content_keys(v, f"{path}[{i}]"))
    return hits


def validate_bundle(purpose: str, bundle: dict[str, Any]) -> None:
    """Raise ``ValueError`` if the bundle violates its purpose's shape."""
    _purposes._check_purpose(purpose)
    kind = bundle.get("bundle_kind")
    if purpose in AGGREGATE_ONLY_PURPOSES:
        if kind != KIND_AGGREGATE_COUNTERS:
            raise ValueError(
                f"purpose {purpose!r} requires bundle_kind "
                f"{KIND_AGGREGATE_COUNTERS!r}, got {kind!r}")
        hits = _find_content_keys(bundle.get("aggregate"))
        if hits:
            raise ValueError(
                f"aggregate bundle for {purpose!r} carries content at: "
                + ", ".join(hits))
    elif purpose == "persona_improvements":
        if kind != KIND_PERSONA_EXCERPTS:
            raise ValueError(
                f"purpose 'persona_improvements' requires bundle_kind "
                f"{KIND_PERSONA_EXCERPTS!r}, got {kind!r}")


def _base_bundle(purpose: str, kind: str) -> dict[str, Any]:
    definition = _purposes._check_purpose(purpose)
    return {
        "schema": "veto-contribution/1",
        "created_at": _utcnow(),
        "purpose": definition["title"],
        "contribution_purpose": purpose,
        "purpose_version": definition["version"],
        "purpose_definition": definition["definition"],
        "bundle_kind": kind,
        "scrub_ruleset": _scrub.SCRUB_RULESET_VERSION,
    }


def build_persona_bundle(sessions: list[dict[str, Any]],
                         scrub_summary: list[dict[str, Any]]) -> dict[str, Any]:
    """Bundle of scrubbed transcript excerpts (persona purpose only)."""
    bundle = _base_bundle("persona_improvements", KIND_PERSONA_EXCERPTS)
    bundle["sessions"] = sessions
    bundle["scrub_summary"] = scrub_summary
    validate_bundle("persona_improvements", bundle)
    return bundle


def build_aggregate_bundle(purpose: str,
                           session_meta: list[dict[str, Any]],
                           extras: dict[str, Any] | None = None) -> dict[str, Any]:
    """Counters-only bundle for diagnostics / provider health / research.

    ``session_meta`` is session *metadata* (source, score, question counts) —
    never transcripts or answers. ``extras`` carries purpose-specific
    counters (e.g. diagnostics signatures).
    """
    if purpose not in AGGREGATE_ONLY_PURPOSES:
        raise ValueError(f"{purpose!r} is not an aggregate-only purpose")
    bundle = _base_bundle(purpose, KIND_AGGREGATE_COUNTERS)
    aggregate: dict[str, Any] = _aggregate_stats(session_meta)
    if purpose == "provider_health":
        aggregate["telemetry_note"] = (
            "Session-derived counters only; provider-API telemetry is not "
            "yet wired (see integration_notes.md). No provider credentials, "
            "request bodies, or response content are included.")
    if extras:
        aggregate["extras"] = extras
    bundle["aggregate"] = aggregate
    validate_bundle(purpose, bundle)
    return bundle

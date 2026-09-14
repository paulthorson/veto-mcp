#!/usr/bin/env python3
"""Initiative 08, Epic 3 — aggregation rules.

For any aggregate or shared statistic:

- Minimum cohort size ``k`` (default 25, tunable UPWARD ONLY via
  ``min_cohort_k`` in settings — lowering below 25 is rejected). Published
  in the methodology. Any slice with fewer than k contributors is
  SUPPRESSED ENTIRELY — not shown as "low N", not interpolated.
- Domain-generalization ladder: exact value -> industry/category -> all,
  so a slice that is too sparse at the exact level can still contribute
  to a coarser published slice (when that slice itself meets k).
- Research-purpose data NEVER ships record-level rows. ``build_research
  _aggregate`` rejects content fields outright.

Suppression (not perturbation) is the chosen mechanism: it preserves the
contributor's ability to inspect exact bytes (preview-exactness is the
higher trust value) at the cost of sparse slices simply not existing.
"""

from __future__ import annotations

from typing import Any, Mapping

DEFAULT_MIN_COHORT_K = 25

#: Hard floor. The minimum cohort size can be raised for stricter
#: contexts, never lowered below 25.
K_FLOOR = 25

#: Field names that may never appear in a research aggregate. Content
#: fields are excluded by schema, not by consent granularity.
CONTENT_FIELDS = frozenset(
    {
        "transcript", "transcript_excerpt", "excerpts", "answer", "response",
        "note", "notes", "feedback", "question", "prompt", "resume_text",
        "cover_letter", "job_description", "email", "phone", "name",
        "address", "company_raw",
    }
)


def min_cohort_k(settings: Mapping[str, Any] | None = None) -> int:
    """Published minimum cohort size (default 25, tunable UPWARD only).

    A settings override below the floor is rejected loudly — silently
    weakening the cohort minimum would break the published methodology.
    """
    raw = (settings or {}).get("min_cohort_k", DEFAULT_MIN_COHORT_K)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = DEFAULT_MIN_COHORT_K
    if value < K_FLOOR:
        raise ValueError(
            f"min_cohort_k={value} is below the floor {K_FLOOR}; "
            "the cohort minimum can only be raised, never lowered")
    return value


def cohort_check(n: int,
                 settings: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Check whether a cohort of ``n`` contributors meets the minimum."""
    k = min_cohort_k(settings)
    return {
        "n": int(n),
        "k": k,
        "meets_minimum": int(n) >= k,
        "suppressed": int(n) < k,
    }


def suppress_sparse_slices(
    slices: Mapping[str, int],
    settings: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Suppress slices below the minimum cohort.

    ``slices`` maps slice label -> contributor count. Returns the
    publishable slices plus the suppressed labels (suppressed slices are
    dropped entirely, never published as "low N").
    """
    k = min_cohort_k(settings)
    published: dict[str, int] = {}
    suppressed: list[str] = []
    for label, count in slices.items():
        if int(count) >= k:
            published[label] = int(count)
        else:
            suppressed.append(label)
    return {
        "k": k,
        "published": published,
        "suppressed": sorted(suppressed),
        "suppressed_count": len(suppressed),
    }


def generalize(value: str, ladder: Mapping[str, str],
               unknown: str = "all") -> dict[str, str]:
    """Domain-generalization ladder: exact -> mapped category -> all.

    ``ladder`` maps exact values to their coarser category (e.g. employer
    -> industry). Unknown values generalize straight to ``unknown``.
    """
    value = (value or "").strip()
    if not value:
        return {"level": "all", "label": unknown}
    category = ladder.get(value)
    if category:
        return {"level": "category", "label": category}
    return {"level": "all", "label": unknown}


def _assert_no_content_fields(record: Mapping[str, Any]) -> None:
    offending = sorted(set(record) & CONTENT_FIELDS)
    if offending:
        raise ValueError(
            "Research aggregates must never contain content fields; "
            f"rejected keys: {offending}. Strip them before aggregating.")


def build_research_aggregate(
    records: list[Mapping[str, Any]],
    group_key: str,
    metric: str,
    settings: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a cohort-level research aggregate — never record-level rows.

    ``records`` are per-contributor NON-CONTENT rows (content fields raise
    ``ValueError``). ``group_key`` selects the slice dimension, ``metric``
    names the numeric field to average. Slices below k are suppressed.
    Only aggregates leave this function: counts, means, and the slice
    labels that met the cohort minimum.
    """
    k = min_cohort_k(settings)
    for record in records:
        _assert_no_content_fields(record)
    groups: dict[str, list[float]] = {}
    contributors: dict[str, set[str]] = {}
    for record in records:
        label = str(record.get(group_key, ""))
        if not label:
            continue
        try:
            value = float(record.get(metric, 0))
        except (TypeError, ValueError):
            continue
        groups.setdefault(label, []).append(value)
        contributors.setdefault(label, set()).add(
            str(record.get("contributor_id", id(record))))
    published: dict[str, dict[str, Any]] = {}
    suppressed: list[str] = []
    for label, values in groups.items():
        n = len(contributors[label])
        if n < k:
            suppressed.append(label)
            continue
        published[label] = {
            "n": n,
            "mean": round(sum(values) / len(values), 4),
            "count": len(values),
        }
    return {
        "k": k,
        "group_key": group_key,
        "metric": metric,
        "slices": published,
        "suppressed": sorted(suppressed),
        "total_contributors": len({c for s in contributors.values()
                                   for c in s}),
        "record_level": False,
    }


def build_diagnostics_aggregate(
    records: list[Mapping[str, Any]],
    group_key: str,
    metric: str,
    settings: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Diagnostics aggregate: same guarantees as research.

    Crash/error/latency telemetry only — content fields are rejected by
    schema, sparse slices suppressed, never record-level rows.
    """
    result = build_research_aggregate(records, group_key, metric, settings)
    result["purpose"] = "product_diagnostics"
    return result


def build_provider_health_aggregate(
    records: list[Mapping[str, Any]],
    group_key: str,
    metric: str,
    settings: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Provider-health aggregate: same guarantees as research.

    Per-provider latency/error stats only — content fields are rejected
    by schema, sparse slices suppressed, never record-level rows.
    """
    result = build_research_aggregate(records, group_key, metric, settings)
    result["purpose"] = "provider_health"
    return result


def generalize_stars(stars: int) -> str:
    """Bucket a 1-5 star rating for aggregation ('4-5', '3', '1-2')."""
    stars = int(stars)
    if stars >= 4:
        return "4-5"
    if stars == 3:
        return "3"
    return "1-2"


def generalize_turns(turns: int) -> str:
    """Bucket a turn count for aggregation ('1-5', '6-20', '21+')."""
    turns = int(turns)
    if turns <= 5:
        return "1-5"
    if turns <= 20:
        return "6-20"
    return "21+"

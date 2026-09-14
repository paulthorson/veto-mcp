#!/usr/bin/env python3
"""Initiative 08 — machine-readable cross-initiative contracts.

Other initiatives build against THIS module (constants + schemas), not
against in-flight files. The human-readable contract is
``SCRUB_QUARANTINE_CONTRACT.md`` in this package.

Stability promise: names and semantics here are frozen for Q2. Additive
changes only; any breaking change gets a new versioned constant.
"""

from __future__ import annotations

from . import aggregation, purposes, quarantine, scrub

#: Current scrub ruleset version. Bundles record this; reviewers verify it.
SCRUB_RULESET_VERSION: str = scrub.SCRUB_RULESET_VERSION

#: Methodology document version.
METHODOLOGY_VERSION: str = "0.1"

#: Minimum cohort size for any published aggregate slice.
MIN_COHORT_K: int = aggregation.DEFAULT_MIN_COHORT_K

#: Purpose ids with their standing-grant requirement.
PURPOSES: dict[str, dict[str, object]] = {
    pid: {
        "version": d["version"],
        "title": d["title"],
        "requires_standing_grant": d["requires_standing_grant"],
    }
    for pid, d in purposes.PURPOSES.items()
}

#: Roles permitted to author a quarantine clearing entry.
CLEARING_ROLES: frozenset = quarantine.CLEARING_ROLES

#: Contribution bundle schema id (unchanged from contribute.py v1).
BUNDLE_SCHEMA = "veto-contribution/1"

#: Per-turn transcript excerpt cap (chars).
MAX_EXCERPT_CHARS: int = scrub.MAX_EXCERPT_CHARS

__all__ = [
    "SCRUB_RULESET_VERSION",
    "METHODOLOGY_VERSION",
    "MIN_COHORT_K",
    "PURPOSES",
    "CLEARING_ROLES",
    "BUNDLE_SCHEMA",
    "MAX_EXCERPT_CHARS",
]

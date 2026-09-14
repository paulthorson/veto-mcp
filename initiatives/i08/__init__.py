"""Initiative 08 — Collective intelligence with receipts.

Learn from community patterns without turning private job-search records
into a hidden training corpus. Six epics:

1. Contribution preview — the exact scrubbed payload before anything
   leaves the device (``contribute.preview_contribution`` + byte hash).
2. Purpose-specific consent — ``purposes``: product diagnostics, persona
   improvements, provider health, research; each independently granted,
   all off by default.
3. Aggregation rules — ``aggregation``: minimum cohort sizes, sparse or
   identifying slices suppressed, never record-level rows for research.
4. Contributor receipt — ``receipts``: local hash-chained record of what
   was shared, why, when, and how to request removal where possible.
5. Public methodology — ``methodology``: generated public doc with
   schemas, exclusions, known bias, governance decisions, sanitized
   incident log.
6. Impact feedback — ``impact``: which product change a contributor's
   accepted contribution informed, when traceable (cited bundles only;
   never invented).

Hard contract (see ``SCRUB_QUARANTINE_CONTRACT.md``): NOTHING is
transmitted by default. If a scrub test or runtime check finds personal
or secret data, the payload is QUARANTINED and contribution sending is
DISABLED until a named contracted security/privacy specialist writes a
clearing entry naming themselves and the reason, and the independent
framework reviewer verifies the evidence. Paul retains veto authority.
"""

from __future__ import annotations

from . import aggregation, impact, methodology, purposes, quarantine, receipts, scrub

__all__ = [
    "aggregation",
    "impact",
    "methodology",
    "purposes",
    "quarantine",
    "receipts",
    "scrub",
]

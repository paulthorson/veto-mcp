# Proof: Initiative 01 — Outcomes Lifecycle (data-plumbing)

**Shipped:** 2026-09-13 · **Commit:** `b4bed50` (data-plumbing WS-1..WS-6)
· **Review ticket:** `muse/2026-09-13/roadmap-exec/data-plumbing`

## What was built (WS-6)

- `funnels.py` — pipeline views sliced by source, role family, fit band,
  resume variant, and time cohort. Conversion is defined as
  share-of-slice reaching each stage and stated in the output; terminal
  exits (rejected/withdrawn/stale) reported per slice. Falls back to the
  lifecycle stage only when an application has no outcome event.
  Read-only. CLI `funnel view|timeline`, MCP `funnel_view`,
  `application_timeline`.
- `experiment_ledger.py` — append-only `experiment_ledger.jsonl`
  recording ranking_version / tailoring_version / fit_score /
  fit_components per application; refuses unattributed records.
  `linked_evidence()` feeds `calibration.weight_report(scored=...)`,
  closing the loop to Initiative 02.
- `outcome_nudges.py` — `pending_prompts()` wraps the capture contract's
  `missing_outcome_prompts` (read-only); `send_prompts()` delivers one
  `outcome_stale` notification per prompt through notify.py (opt-in,
  quiet hours, digest honored). Notifications propose; they never record
  outcomes.

## Capture-contract verification

The capture team's `outcome-min-v0` contract was present in the shared
tree and is consumed by funnels, briefs, calibration, the action inbox,
and outcome nudges — the "schema integration point reached" milestone.
`tests/test_initiative_01.py` pins the contract's real behavior:

- identity-key duplicates are rejected without double-append
  (`appended: False`, `duplicate_of` set);
- corrections carry provenance (actor, reason) with immutable identity
  (`event_type` cannot be corrected);
- CSV import is idempotent; the guided update requires confirmation;
- `coverage_report` shape verified.

## Proof of value

- 23 new tests, all green (`tests/test_initiative_01.py`).
- Two real bugs were found and fixed by the builder's adversarial review
  pass before shipping: a near-miss resolve path that overwrote the
  application's fit score (now advisory-only), and a `rstrip(" —)")`
  header bug that dropped a closing paren on empty fields.
- Funnel, timeline, ledger, and nudge surfaces are all read-only except
  the append-only ledger and the notify-mediated prompts; every mutation
  boundary in the outcomes flow requires explicit confirmation.

## Open follow-ups (non-blocking)

- Parent to assign fresh blind reviewers for WS-1–WS-6 (builder-issued
  ALLOWs are disclosed as non-independent).
- Wire live personalized scoring only when the calibration evidence gate
  passes against the real event store; weights stay pinned off until then.

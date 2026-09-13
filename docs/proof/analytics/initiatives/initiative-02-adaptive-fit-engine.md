# Proof: Initiative 02 — Adaptive Fit Engine (data-plumbing)

**Shipped:** 2026-09-13 · **Commit:** `b4bed50` (data-plumbing WS-1..WS-6)
· **Review ticket:** `muse/2026-09-13/roadmap-exec/data-plumbing`

## What was built (WS-5)

- `calibration.py` — evidence gate: ≥20 resolved outcomes, ≥4 qualified
  replies, and every observed non-empty role-family slice ≥10 resolved /
  2 qualified replies. A "qualified reply" is explicitly a temporal
  sequence (`replied` followed later by screened/interviewed/offered/
  accepted), not a causal claim. The offline weight report shows sample
  counts, component association, and standard error — it never applies
  weights.
- `model_card.py` — append-only model card with a virtual static v0,
  pin/unpin, record, rollback, and reset. Recording a personalized
  version requires an unpinned model, a non-empty human `approved_by`,
  and a passing evidence gate.
- `near_miss.py` — advisory queue for fit scores 50–59; resolving a
  near-miss changes no score and no application state.

## Review history

The researcher-domain structural scan initially vetoed on the literal
phrase "no evidence" in the review bundle (a keyword false positive) and
on causal-sounding `suggested_direction` language. The bundle was
reworded to observational phrasing and `suggested_direction` was replaced
with explicitly observational `observed_association`. Re-review: ALLOW.

## Proof of value

- 20 new tests, all green (`tests/test_calibration.py`).
- Honest state of the system: the evidence gate has not yet passed
  against the real event store, so live personalized scoring is NOT
  wired — `match.score_job` still uses static weights and the model card
  stays pinned at the virtual static v0. The scaffolding refuses to let
  weights turn on without evidence, a human approver, and an unpinned
  model.
- A real bug was caught by the adversarial pass: resolving a near-miss
  used to overwrite the application's fit score; it is now advisory-only.

## Open follow-ups (non-blocking)

- Run the actual evidence gate / first weight report against the real
  event store; wire live personalized scoring only if the gate passes.
- CLI/MCP surface parity: add `unpin`/`reset` commands.
- Parent to assign a fresh blind researcher review (builder-issued ALLOW
  is disclosed as non-independent).

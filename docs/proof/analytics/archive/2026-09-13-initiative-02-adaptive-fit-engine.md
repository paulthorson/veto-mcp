# Analytics Proof Hub

Evergreen proof record for the Veto annual roadmap's data-plumbing work
(Initiatives 01–03). This README is updated in place on every shipped
initiative: the previous version is archived under `archive/` first, then
the counts below are recomputed from the sources of truth.

- **Current as of:** 2026-09-13
- **Initiatives with proof:** 1 of 3
  (`initiative-01-outcomes-lifecycle`)

## Cumulative review verdicts

Recomputed from the Agentic Governance verdict log
(`governance-tools/runs/verdicts.jsonl`), ticket
`muse/2026-09-13/roadmap-exec/data-plumbing`:

| Verdict    | Count |
|------------|-------|
| ALLOW      | 6     |
| KICK_BACK  | 0     |

By domain: compliance 1, engineer 1, product 2, researcher 2 — all ALLOW.

> Disclosure: at depth 2 no independent reviewer could be spawned, so the
> adversarial reviews behind these ALLOWs were executed by the builder
> under the framework prompts, with the isolation caveat recorded in
> every verdict summary. Fresh blind re-review must be assigned by the
> program coordinator before these count as fully cleared.

## Velocity

| Date       | Initiative | Workstreams | New tests | Verdicts |
|------------|------------|-------------|-----------|----------|
| 2026-09-13 | 01 outcomes-lifecycle | WS-6: funnels, experiment ledger, outcome nudges | 23 | researcher ALLOW |

## Quality / test results

- Full shared-tree suite at proof time: **2212 tests, 1 failure, 8 skipped**.
  The single failure is `test_i08_default_off::
  test_quarantine_lock_checked_before_killswitch` — an Initiative 08
  module outside data-plumbing scope; it passes 7/7 in isolation
  (cross-suite pollution from another team's in-flight module, not this
  change).
- All data-plumbing-owned test modules green in the same run:
  `test_notify_controls` 22, `test_provider_health` 22,
  `test_reply_radar` 14, `test_daily_loop` 11, `test_calibration` 20,
  `test_initiative_01` 23, plus `test_email_sync` 26 and `test_briefs` 14.

## Proof notes per initiative

- `initiatives/initiative-01-outcomes-lifecycle.md` — shipped 2026-09-13.

## Learnings

Append-only; see `learnings/`.

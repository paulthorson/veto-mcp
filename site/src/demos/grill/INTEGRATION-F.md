# INTEGRATION-F — BYOA daily companion loop (Chakra feature F)

Builder F's deliverables are pure presentational + logic layers. This doc is
the exact wiring for the DemoPage integrator. No existing files were modified.

## What was built

| File | Role |
|---|---|
| `site/src/lib/companionTypes.ts` | Types: `Prospect`, `ProspectStage`, `CheckIn`, `NetworkContact`, `WarmPath`. Imports `JobContext` from `chakraTypes.ts` (feature E). |
| `site/src/lib/companionLoop.ts` | Deterministic logic: `analyzeProspects`, `warmPathTo`, `checkInSummary`, `feedNudge`, plus `daysBetween` and `liveProspectCount` helpers. |
| `site/src/lib/fixtures/network.ts` | `FIXTURE_NETWORK`: 8 fictional contacts (all names/companies invented). |
| `site/src/demos/grill/CompanionDashboard.tsx` | Presentational React component. Props: `{ prospects, network, nowIso? }`. Shows the **single warmest** path per prospect company. |
| `site/src/demos/grill/PipelineBoard.tsx` | Presentational React component — the "where do I stand" home view. Props: `{ prospects, nowIso? }`. Four columns: wishlist → applied → interviewing → offer. |
| `site/src/lib/__tests__/companionLoop.test.ts` | 18 vitest cases, all deterministic via pinned `nowIso`. |
| `site/src/lib/__tests__/pipelineBoard.test.tsx` | 6 vitest cases (renderToStaticMarkup): column mapping, staleness display, empty pipeline. |
| `site/e2e/chakra-f.e2e.mjs` (+ `chakra-f.harness.tsx`) | CDP E2E. Serves dist, tries `#/demo` first; falls back to an esbuild scratch harness rendering board + dashboard. |

## 1. Where CompanionDashboard and PipelineBoard mount

Suggested: a **new "Daily check-in" entry point on the demo page**, separate
from the grill flow. The grill is the interview; the companion loop is the
coach around it. Concretely, in `DemoPage.tsx`:

- Add a tab/section toggle at the top of the demo page: `Grill` | `Daily check-in`.
- The `Daily check-in` pane is the **PipelineBoard — the companion home
  view**, the "where do I stand" surface: four columns
  (wishlist → applied → interviewing → offer) with staleness on every card.
- The **CompanionDashboard mounts inside/after the board** on the same pane:
  check-in summary, follow-up callouts, per-prospect warmest paths, and the
  feed-more-jobs nudge. Board first (state), dashboard second (coaching).
- Do NOT nest either inside the grill question flow — they are ambient,
  available before/after a grill run.

Column mapping (fixed in the component, documented here): `interested`
prospects render in the **Wishlist** column — "wishlist" is the user's word
for "on my radar, not yet applied". No new stage was added, so
`ProspectStage` stays stable. `rejected` prospects are excluded from the
board (it is the live-pipeline view).

## 2. How prospects persist

Suggested: **localStorage**, namespaced `veto.companion.v1`:

- `veto.companion.v1.prospects` — `Prospect[]` JSON.
- `veto.companion.v1.checkins` — `CheckIn[]` JSON (append one per day the user opens the check-in).
- Load on mount, save on every mutation. Wrap in try/catch (private-mode
  browsers) and fall back to in-memory state.

## 3. How it consumes JobContext from feature E

Feature E's fed-job flow produces `JobContext` (`title`, `company`,
`requirements`, …). When the user saves a fed job as a prospect:

```ts
import type { JobContext } from '../lib/chakraTypes';
import type { Prospect } from '../lib/companionTypes';

function prospectFromJob(job: JobContext): Prospect {
  const now = new Date().toISOString();
  return {
    id: `p-${Date.now()}`,
    job,
    stage: 'interested',
    notes: [],
    lastActivity: now,
    addedAt: now,
  };
}
```

Stage advances (applied → interviewing → offer) are user-driven buttons on
each prospect card; each advance appends a note and stamps `lastActivity`.
`CompanionDashboard` itself stays presentational — mutations live in the
integrator's container.

## 4. data-testid contract (E2E relies on these)

CompanionDashboard:
- `companion-dashboard` — root section
- `checkin-summary` — the 2–3 sentence coach summary
- `followup-callouts` / `followup-callout` — needs-follow-up list + items
- `prospect-group-<stage>` — one per non-empty stage (`interested`, `applied`, `interviewing`, `offer`, `rejected`)
- `prospect` — each prospect row; `prospect-followup-flag` on flagged rows
- `warm-paths` / `warm-path` — the single warmest path per prospect company
- `warm-path-none` — the honest "no warm path" message
- `feed-nudge` — the feed-more-jobs nudge

PipelineBoard:
- `pipeline-board` — root section
- `pipeline-column-<wishlist|applied|interviewing|offer>` — the four columns
- `pipeline-card` — each prospect card (`data-prospect-id` carries the id)
- `pipeline-card-staleness` — "quiet 12 days" / "active 3d ago" / "active today"

## 5. Warm-path honesty contract (do not weaken)

`warmPathTo` mirrors `network_crm.py`'s honesty rule: paths derive only from
recorded contacts; empty array means no path. The dashboard renders the
`warm-path-none` message in that case ("this one goes in cold, or grow the
network first"). Never present cold outreach as a warm path.

The dashboard shows the **single warmest path per prospect company** via
`warmestPathTo` (new in companionLoop.ts): 1st degree beats 2nd degree, and
within a degree the closest contact comes first. `warmPathTo` itself still
returns all paths ranked — the board/dashboard just render `[0]`.

One documented inference: two contacts at the same company are treated as
knowing each other (colleagues), which is what makes a closeness-3 weak tie
reachable "via" a close colleague (2nd degree). Everything else is direct
record lookup.

## 6. Running the checks

```bash
cd site
npx tsc --noEmit -p tsconfig.app.json
npx vitest run src/lib/__tests__/companionLoop.test.ts src/lib/__tests__/pipelineBoard.test.tsx
node e2e/chakra-f.e2e.mjs            # CDP E2E; screenshot -> /tmp/chakra-f-companion.png
```

After wiring the dashboard into `#/demo`, re-run the E2E with no flags: it
will detect the mounted dashboard and assert against the integrated page
(mode: integrated).

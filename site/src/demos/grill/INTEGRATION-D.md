# INTEGRATION-D — Feature D: real-repository tasks

**Feature D** replaces/augments isolated grill puzzles with tasks against a real
fixture repository: candidates work in a realistic codebase (the Acme orders
API) instead of answering toy questions.

## What's built (all new files — nothing existing was edited)

| File | Purpose |
|---|---|
| `site/public/fixtures/acme-api/` | Fixture repo: `package.json`, `README.md`, `src/server.js`, `src/routes/orders.js`, `src/db/memory.js`, `tests/smoke.test.js` (~113 lines, plain JS, no deps). Planted off-by-one in `listOrders()` page window; `getOrder` stub returns 501. |
| `site/src/lib/repoTasks.ts` | `getRepoTasks(job?: JobContext): RepoTask[]` — the default 2-task set. |
| `site/src/lib/__tests__/repoTasks.test.ts` | vitest: 2 tasks, required fields, determinism, fixture files exist, bug line present, stub present, no secrets/PII. |
| `site/src/demos/grill/RepoTaskView.tsx` | Presentational view. Props `{ task: RepoTask }`. |
| `site/e2e/chakra-d.e2e.mjs` | CDP E2E against the real page (see below). |
| This file | Wiring instructions for the integrator. |

## Wiring: where the tasks appear

Suggested: in the **standard** and **brutal** runs, offer repo tasks as an
alternative to grill question 3 ("scale"), or as a **bonus stage** after the
verdict. Rationale: question 3 ("scale") already probes production code sense —
the repo tasks are its hands-on upgrade.

**DemoPage edits (integrator):**

```tsx
// 1. Import at the top of site/src/pages/DemoPage.tsx
import { getRepoTasks } from '../lib/repoTasks';
import { RepoTaskView } from '../demos/grill/RepoTaskView';
import type { JobContext } from '../lib/chakraTypes';

// 2. Wherever the demo holds a JobContext (Feature E seam), derive tasks:
const repoTasks = getRepoTasks(jobContext /* may be undefined */);

// 3. Render the first task at the chosen mount point:
<RepoTaskView task={repoTasks[0]} />
// Cycle repoTasks[1] as the bonus / alternate stage.
```

**data-testid contract** (must survive styling passes):

- Root: `data-testid="repo-task-view"`
- Title: `data-testid="repo-task-title"` — e.g. "Fix the pagination bug"
- Description: `data-testid="repo-task-description"`
- Repo path: `data-testid="repo-task-repo"` — `fixtures/acme-api`
- File tree: `data-testid="repo-task-files"` — includes `src/routes/orders.js`
- Check description: `data-testid="repo-task-check"` — the page-2/page-3 contract

## JobContext → task selection (future extension point)

`getRepoTasks(job)` currently returns the Acme API set for every job — it's the
default set. The `API_FIT` keyword list (`backend`, `api`, `node`, `node.js`,
`express`, `server`, `rest`) already scores `job.roleKeywords`; when more
fixtures exist (e.g. a React component fixture for frontend keywords, a data
fixture for `python`/`sql`), replace the `void fitsApi` line with real
selection: pick the fixture whose keyword set best overlaps the fed job, fall
back to the Acme API set when nothing overlaps.

**Do not** ship fixture selection keyed on anything other than `roleKeywords`
without also keeping the deterministic default — the demo must render
something sensible with no job fed.

## Verifying after wiring

1. `npx vitest run` in `site/` — 9 tests in `repoTasks.test.ts` must pass.
2. `npx tsc --noEmit -p site/tsconfig.app.json` must be clean.
3. Build + serve dist, then run `node site/e2e/chakra-d.e2e.mjs`:
   asserts the view renders with title + file tree + check description,
   screenshots to `/tmp/chakra-d-repotask.png`. Exits 1 with the intended
   mount point until the wiring above lands.

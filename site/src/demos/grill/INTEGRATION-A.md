# INTEGRATION-A — Wiring the reasoning narrative into the DemoPage verdict

Feature A (Chakra A): every grill verdict shows a reasoning narrative — HOW the
candidate approached the problems, not just pass/fail.

Builder: `site/src/lib/reasoningNarrative.ts`
→ `buildReasoningNarrative(answers: FullAnswer[], job?: JobContext): ReasoningNarrative`

Component: `site/src/demos/grill/ReasoningNarrative.tsx`
→ `<ReasoningNarrative narrative={...} />` (presentational, no interactivity)

E2E: `site/e2e/chakra-a.e2e.mjs` (asserts the contract below; exits 2
`INTEGRATION-PENDING` until this wiring lands, 0 after).

## Steps

### 1. Imports (top of `site/src/pages/DemoPage.tsx`)

```tsx
import { ReasoningNarrative } from '../demos/grill/ReasoningNarrative';
import { buildReasoningNarrative } from '../lib/reasoningNarrative';
```

### 2. Mount in the FullGrill verdict stage

Find the verdict block in `FullGrill`:

```tsx
{stage === 'verdict' && result && (
  <div className="demo-verdict">
```

Inside that `<div className="demo-verdict">`, mount the narrative **after** the
pass/fail card (the `result.pass ? <Card …/> : <div className="demo-veto-term" …/>`
block) and **before** the `<ShareLinks … />` line:

```tsx
<ReasoningNarrative narrative={buildReasoningNarrative(answers)} />
<ShareLinks level={level} vetoed={!result.pass} reason={result.reason} score={result.score} />
```

`answers` is the existing `FullAnswer[]` state in `FullGrill`; `result` is the
existing `computeFullResult(level, answers)` memo. No other changes are needed —
the component is presentational. (Optionally wrap the call in a `useMemo` on
`[answers]` if you want to avoid rebuilding the strings on re-render; the
builder is pure and cheap either way.)

### 3. JobContext tie-in (when Feature E lands)

`buildReasoningNarrative` accepts an optional second argument. Once Feature E
supplies a `JobContext` for the run, change the mount to:

```tsx
<ReasoningNarrative narrative={buildReasoningNarrative(answers, job)} />
```

where `job` is the `JobContext`. Without it, the narrative is job-agnostic.

## Data-testid contract (do not change — the E2E asserts these)

- `[data-testid="reasoning-narrative"]` — the `<section>` wrapper.
- `[data-testid="reasoning-narrative-summary"]` — the 2–3 sentence summary `<p>`.
- `[data-testid="reasoning-narrative-item"]` — one `<li>` per answer, in question
  order, with `data-qid` set to the question id (`years` | `k8s` | `scale` |
  `logistics` | `motivation`).
- The heading text **"How they approached it"** is also asserted by the E2E —
  keep it verbatim.

## Verification after wiring

```bash
cd ~/workspace/wt-demo-immersive/site
npm run build        # rebuild dist/ (the script inlines dist/index.html + bundle)
node e2e/chakra-a.e2e.mjs   # expect PASS, screenshot /tmp/chakra-a-verdict.png
```

Run it serially — the shared CDP helper's debug port (9333) and profile
dir can't be shared with another running chakra-*.e2e.mjs script (see
AGENTS.md). The script drives the real flow (Standard level → 5 quick-pick
clicks → honesty → score → tailor → verdict) with real CDP clicks, asserts
the summary and all five per-answer entries are present at the verdict, and
screenshots. Pre-wiring it exits 2 with an INTEGRATION-PENDING report.

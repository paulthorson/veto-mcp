# Feature B — AI fluency score: integration wiring (DemoPage.tsx)

> BUILDER B deliverable. The integrator owns DemoPage.tsx; this doc is the
> exact wiring. Nothing here modifies existing files — it only describes
> where to add imports and mounts.

## 1. Imports (top of `site/src/pages/DemoPage.tsx`)

```tsx
import AiFluencyPanel from '../demos/grill/AiFluencyPanel';
import { scoreAiFluency } from '../lib/aiFluency';
/* Optional: pass a JobContext so the panel note mentions role relevance.
   Feature E produces this type; a static fixture works for the demo. */
import type { JobContext } from '../lib/chakraTypes';
```

## 2. Compute the fluency score (in `FullGrill`, next to `result`)

```tsx
const fluency = useMemo(
  () => (done ? scoreAiFluency(answers) : null),
  [done, answers],
);
```

`scoreAiFluency` is pure and deterministic — same answers, same score.
Optional second argument: a `JobContext` (Feature E's parsed posting).
When provided, only the `note` changes (it reports how many role
keywords the answers reference); the numeric score is untouched. If
Feature E is not wired yet, omit the argument — the panel still works.

## 3. Mount the panel — verdict stage, beside the fit-score verdict

The fit-score factors render at the `score` stage; the verdict stage shows
the final call. Mount the fluency panel in the `verdict` stage block,
**after** the pass/veto card and **before** `ShareLinks`, so both scores
sit next to each other at the moment of the verdict:

```tsx
{stage === 'verdict' && result && fluency && (
  <div className="demo-verdict">
    {result.pass ? (
      /* ... existing demo-pass Card ... */
    ) : (
      /* ... existing demo-veto-term ... */
    )}
    {/* Feature B: AI fluency dimension, beside the fit-score verdict */}
    <AiFluencyPanel fluency={fluency} />
    <ShareLinks level={level} vetoed={!result.pass} reason={result.reason} score={result.score} />
    {/* ... rest unchanged ... */}
  </div>
)}
```

The panel is presentational and needs no CSS — it carries inline styles
in the demo's pixel/mono language and the radar's red/amber/green
gradient semantics (low = red, mid = amber, high = green).

## 4. data-testid contract (E2E + QA)

| Selector | Element |
|---|---|
| `[data-testid="ai-fluency-panel"]` | Panel root (`role="region"`) |
| `[data-testid="ai-fluency-framing"]` | Framing dimension bar |
| `[data-testid="ai-fluency-judgment"]` | Judgment dimension bar |
| `[data-testid="ai-fluency-steering"]` | Steering dimension bar |

The root's `aria-label` is `AI fluency score <score> out of 100`; each
dimension bar's `aria-label` is `<Label>: <value> out of 100`.
`site/e2e/chakra-b.e2e.mjs` drives the full Standard flow via CDP and
asserts this contract.

## 5. Feeding the fluency score into the Radar (documented, not wired)

`site/src/demos/radar.tsx` is intentionally NOT modified. Options for a
future wiring, integrator's call:

1. **New demo:** a second `RadarDemo`-style component whose axes are
   `framing`, `judgment`, `steering` (weights 0.40 / 0.35 / 0.25, same as
   `AI_FLUENCY_WEIGHTS`), fed the live `AiFluencyDimensions` from the
   grill run. The existing tri-color gradient works unchanged — low
   values sit on red, high values on green.
2. **Overlay:** render the fluency polygon on the existing fit-score
   radar as a dashed amber trace for comparison.

Either way, feed it `scoreAiFluency(answers).dimensions` — never recompute
the heuristics inside a demo component.

## 6. Weights reference

`site/src/lib/aiFluency.ts` exports `AI_FLUENCY_WEIGHTS`:

```
overall = round(0.40 × framing + 0.35 × judgment + 0.25 × steering)
```

Changing the weights changes E2E expectations — the vitest suite pins
them (`site/src/lib/__tests__/aiFluency.test.ts`).

# Feature H — delivery coaching: integration wiring (DemoPage.tsx)

> BUILDER H deliverable. The integrator owns DemoPage.tsx; this doc is the
> exact wiring. Nothing here modifies existing files — it only describes
> where to add imports and mounts.

## 1. Imports (top of `site/src/pages/DemoPage.tsx`)

```tsx
import DeliveryPanel from '../demos/grill/DeliveryPanel';
import { analyzeDeliveryAcross } from '../lib/deliveryCoaching';
```

## 2. Compute the delivery feedback (in `FullGrill`, next to `result`)

`analyzeDeliveryAcross` takes the full run's `{ qid, text }[]` answers,
sums filler words, averages the hedging score, derives the pacing note
from the average answer length, and picks the most frequent suggestion
themes across the run. It is pure and deterministic — same answers, same
feedback. It is the aggregate form the verdict consumes; single answers
can be analyzed with `analyzeDelivery(text)` (e.g. for a live per-answer
hint, integrator's call).

```tsx
const delivery = useMemo(
  () => (done ? analyzeDeliveryAcross(answers) : null),
  [done, answers],
);
```

If the demo's `answers` are `FullAnswer[]` (with a `cls` field), pass them
unchanged — `analyzeDeliveryAcross` only reads `qid` and `text`.

## 3. Mount the panel — verdict stage, after the verdict card

The fit-score factors render at the `score` stage; the verdict stage shows
the final call. Mount the delivery panel in the `verdict` stage block,
**after** the pass/veto card (and after Feature B's `AiFluencyPanel` if
wired) and **before** `ShareLinks`, so all three verdict surfaces sit
together at the moment of the verdict:

```tsx
{stage === 'verdict' && result && delivery && (
  <div className="demo-verdict">
    {result.pass ? (
      /* ... existing demo-pass Card ... */
    ) : (
      /* ... existing demo-veto-term ... */
    )}
    {/* Feature B: AI fluency dimension (if wired) */}
    {/* Feature H: delivery coaching — HOW the candidate answered */}
    <DeliveryPanel feedback={delivery} />
    <ShareLinks level={level} vetoed={!result.pass} reason={result.reason} score={result.score} />
    {/* ... rest unchanged ... */}
  </div>
)}
```

The panel is presentational and needs no CSS — it carries inline styles
in the demo's pixel/mono language and an inverted mirror of the radar's
gradient on the hedging meter (green left -> amber -> red right, so a
high hedging score's leading edge lands on red — inverted vs the
fluency bars, where high is green).

## 4. data-testid contract (E2E + QA)

| Selector | Element |
|---|---|
| `[data-testid="delivery-panel"]` | Panel root (`role="region"`) |
| `[data-testid="delivery-fillers"]` | Filler breakdown: "Filler words — N total" plus per-filler counts, or "None spotted — clean delivery." |
| `[data-testid="delivery-hedging"]` | Hedging meter (`role="img"`, aria-label "Hedging: N out of 100") + plain-English read |
| `[data-testid="delivery-pacing"]` | "Pacing — \<pacing note>" |
| `[data-testid="delivery-suggestions"]` | Ordered list of coach suggestions ("Coach's notes") |

The root's `aria-label` is
`Delivery coaching: <fillerTotal> filler words, hedging <hedgingScore> out of 100`.
`site/e2e/chakra-h.e2e.mjs` drives the full Standard flow via CDP with
deliberately filler-laden answers and asserts this contract.

## 5. Scoring reference

`site/src/lib/deliveryCoaching.ts` exports `analyzeDelivery` and
`analyzeDeliveryAcross`:

```
hedgingScore = min(100, round(hedgeHits / max(1, wordCount) * 400))
pacing:      < 10 words  -> very brief
             10-60 words -> good length
             > 60 words  -> watch rambling
```

Changing the formulas changes E2E expectations — the vitest suite pins
them (`site/src/lib/__tests__/deliveryCoaching.test.ts`).

## 6. Future speech-input seam (no rework when audio arrives)

The analyzer's contract is `string -> DeliveryFeedback`. Today the
string is the candidate's typed answer; when the demo gains a microphone,
the caller feeds the speech-to-text **transcript** string into the same
`analyzeDelivery` / `analyzeDeliveryAcross` functions — no module changes,
no new types, no re-pinning of tests:

```ts
const transcript: string = await speechToText(audioBlob); // future
const feedback = analyzeDelivery(transcript);             // unchanged
```

Everything downstream (DeliveryPanel, the data-testid contract, the
verdict wiring above) keeps working untouched.

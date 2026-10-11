# INTEGRATION-C — wiring DefendStep into DemoPage's brutal flow

Feature C (Chakra): defend-your-answer. All feature code lives in new files;
DemoPage.tsx gets targeted edits only. Brutal level only — standard and
friendly flows are untouched.

## Files (all new, all on this branch)

- `site/src/lib/defendFlow.ts` — `getDefendPrompt`, `shouldDemandDefense`,
  `assessDefense`. Pure, deterministic, no React.
- `site/src/demos/grill/DefendStep.tsx` — the defend stage UI.
- `site/src/lib/__tests__/defendFlow.test.ts` — vitest (18 tests).
- `site/e2e/chakra-c.e2e.mjs` — CDP E2E (needs this wiring + `npm run build`).

## 1. Imports (top of `site/src/pages/DemoPage.tsx`, next to the demoGrill import)

```tsx
import DefendStep from "../demos/grill/DefendStep";
import {
  assessDefense,
  getDefendPrompt,
  shouldDemandDefense,
} from "../lib/defendFlow";
import type { DefenseAssessment } from "../lib/chakraTypes";
```

## 2. New state in `FullGrill` (next to the other useState calls)

```tsx
/* Feature C: pending defend-your-answer demand, brutal level only. */
const [defense, setDefense] = useState<null | {
  qid: string;
  text: string;
  cls: AnswerClass;
  prompt: string;
}>(null);
const [defenseNotes, setDefenseNotes] = useState<Record<string, DefenseAssessment>>({});
```

## 3. Refactor `submit()`: extract the record-and-advance continuation

Move everything inside the `if (cls === 'specific' || nd > maxDepth) { ... }`
branch into a `recordAnswer(qid, text, cls)` function (same body, minus the
`setDraft('')` which stays in `submit`). `submit()` keeps the throttle,
classification, and message-append, then:

```tsx
if (cls === 'specific' || nd > maxDepth) {
  /* Feature C: brutal may demand a defense before the answer is recorded
     and the grill moves on. Vague answers with follow-up depth remaining
     go through the normal brutal follow-ups first; the defense fires when
     the grill would otherwise accept the answer. */
  if (level === 'brutal' && shouldDemandDefense(q.id, text, cls)) {
    setDefense({
      qid: q.id,
      text,
      cls,
      prompt: getDefendPrompt({ id: q.id, text: q.text }, text),
    });
    setDraft('');
    return;
  }
  recordAnswer(q.id, text, cls);
} else {
  /* ...existing follow-up branch, unchanged... */
}
setDraft('');
```

Why at the record point and not right after classification: a vague answer at
depth 0 already gets interrogated by `followupBrutal` / `followupBrutalLast`.
Demanding a defense there too would double-interrogate. The defense fires
when the grill is about to accept the answer and move on — for quick-picks
(R2a), short specifics (R2b), AI-tell answers (R2c), and for vague answers
once follow-up depth is exhausted (R1). "Before moving on", per the spec.

## 4. Render the defend stage (in the `{!done && (...)}` block)

Hide the quick-picks and the input row while a defense is pending — the
candidate defends, not dodges by clicking another pick:

```tsx
{!done && defense == null && (
  <>
    {/* ...existing .demo-picks and .demo-answer-row, unchanged... */}
  </>
)}
{defense != null && (
  <DefendStep
    questionText={q.text}
    candidateAnswer={defense.text}
    defendPrompt={defense.prompt}
    onComplete={(d) => {
      const a = assessDefense(defense.qid, defense.text, d);
      setDefenseNotes((prev) => ({ ...prev, [defense.qid]: a }));
      setMsgs((prev) => [
        ...prev,
        { id: idRef.current++, from: 'you', text: d, tag: 'defense' },
        { id: idRef.current++, from: 'veto', text: a.note, tag: 'defense verdict' },
      ]);
      const held = defense;
      setDefense(null);
      recordAnswer(held.qid, held.text, held.cls);
    }}
  />
)}
```

## 5. Stable E2E hook for the verdict

In the `msgs.map` render, tag the defense-verdict message so
`site/e2e/chakra-c.e2e.mjs` can assert it:

```tsx
<div
  key={m.id}
  className={...}
  {...(m.tag === 'defense verdict' ? { 'data-testid': 'defense-assessment' } : {})}
  aria-live={i === msgs.length - 1 ? 'polite' : undefined}
>
```

(The component itself already exposes `data-testid="defend-step"`,
`data-testid="defend-input"`, `data-testid="defend-submit"`, and the stable
kicker text "Veto demands a defense".)

## 6. Stage-machine sketch

```
brutal FullGrill, answer submitted
  │
  ├─ classifyAnswer -> cls
  │
  ├─ cls === 'vague' && depth left ──> followupBrutal / followupBrutalLast (unchanged)
  │
  └─ answer would be recorded (cls specific, or depth exhausted)
       │
       ├─ shouldDemandDefense(qid, text, cls)? ── no ──> recordAnswer (unchanged)
       │
       └─ yes ──> DEFEND sub-stage
                     DefendStep(questionText, candidateAnswer, defendPrompt)
                     candidate types defense, clicks "Defend it"
                     │
                     onComplete(defense)
                       ├─ assessDefense(qid, original, defense) -> DefenseAssessment
                       ├─ defenseNotes[qid] = assessment
                       ├─ chat += you/defense, veto/"defense verdict" (data-testid="defense-assessment")
                       └─ recordAnswer(qid, text, cls) — the original answer is
                          recorded exactly as classified; the defense is evidence,
                          not a re-classification
```

Notes:

- Defense outcomes do NOT change scoring — `computeFullResult` is untouched.
  The defense note and score live in the chat transcript and `defenseNotes`.
  Folding defenses into scoring is future work, out of scope for C.
- Determinism preserved: `getDefendPrompt` picks its variant by answer-length
  parity; `assessDefense` is a pure function. The only non-deterministic value
  in the flow remains the ledger timestamp.
- Throttle safety: the defend stage renders instead of the input row, so the
  same answer can't be double-submitted while defending. `restart()` should
  also `setDefense(null)` and `setDefenseNotes({})` (add to the existing
  restart body).
- Accessibility: DefendStep uses a real `<textarea>` + `<button>`, a
  `<label>`, and `role="group"` with an aria-label. Ctrl/Cmd+Enter submits.
- AI-slop ban: no banned words in prompts, notes, or copy. AI-tell detection
  phrases ("as an AI", etc.) exist in `defendFlow.ts` code only, never in
  user-facing strings.

## 7. Verification

```bash
cd site
npx tsc --noEmit -p tsconfig.app.json   # clean
npx vitest run src/lib/__tests__/defendFlow.test.ts   # 18 tests green
npm run build                            # dist for E2E
node e2e/chakra-c.e2e.mjs                # real type + click, screenshot /tmp/chakra-c-defend.png
```

The E2E drives the years question with "9 years" (specific, < 20 chars ->
R2b fires), types a real defense into `[data-testid="defend-input"]`, clicks
`[data-testid="defend-submit"]`, and asserts the deterministic verdict note
"The defense named specifics and tied them back to the claim."

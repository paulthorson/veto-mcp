# Chakra Feature E — Integration guide: user-fed job targeting

Feature E lets the visitor paste a job posting so the grill interviews
them for **that** role. It is strictly additive: with no job fed in,
the demo behaves exactly as today. This doc is the exact wiring the
integrator applies in `site/src/pages/DemoPage.tsx`.

Files delivered by Builder E:

| File | Exports |
|---|---|
| `site/src/lib/jobTargeting.ts` | `parseJobPosting`, `tailorQuestions`, `jobFitNote`, `KEYWORDS`, `STACK_KEYWORDS` |
| `site/src/demos/grill/JobInputStep.tsx` | `<JobInputStep onSubmit onSkip />` |
| `site/e2e/chakra-e.e2e.mjs` | CDP E2E (paste path + skip path) |

## 1. Mount `<JobInputStep/>` as the FIRST step (before the level pick)

`DemoPage` (~line 845) currently renders `<LevelSelect/>` when
`level == null` (~line 882). Insert the job-input step ahead of it:

```tsx
import { JobInputStep } from '../demos/grill/JobInputStep';
import type { JobContext } from '../lib/chakraTypes';

const [jobAsked, setJobAsked] = useState(false);
const [job, setJob] = useState<JobContext | null>(null);
```

Replace the render block (~lines 881–885) with:

```tsx
{!jobAsked && (
  <JobInputStep
    onSubmit={(j) => { setJob(j); setJobAsked(true); window.scrollTo({ top: 0, behavior: 'instant' }); }}
    onSkip={() => { setJob(null); setJobAsked(true); window.scrollTo({ top: 0, behavior: 'instant' }); }}
  />
)}
{jobAsked && level == null && <LevelSelect onPick={pick} />}
{jobAsked && level === 'friendly' && <FriendlyGrill job={job} onSwitchLevel={() => pick(null)} />}
{jobAsked && (level === 'standard' || level === 'brutal') && (
  <FullGrill level={level} job={job} onSwitchLevel={() => pick(null)} />
)}
```

- `job === null` after the step means "skip → default posting".
  (`parseJobPosting` never throws, and an empty paste yields the neutral
  `JobContext` whose questions all fall back to `FULL_QUESTIONS` text —
  the submit button is also disabled on empty input.)
- `onSwitchLevel` ("Switch level") should reset back to the level
  select, NOT to the job-input step: keep `jobAsked === true` so the
  fed job survives a level switch.
- Restart (the ledger stage's restart) resets the run but keeps the fed
  job; a full page reload re-asks the job-input step.

## 2. Override question text via `tailorQuestions`

Add a `job: JobContext | null` prop to `FullGrill` (~line 359) and
`FriendlyGrill` (line 142). Inside each, build display questions that
keep everything (picks, follow-ups, placeholders, order) and only swap
the question text:

```tsx
import { tailorQuestions } from '../lib/jobTargeting';

const displayQuestions: GrillQuestion[] = useMemo(() => {
  if (!job) return FULL_QUESTIONS;
  const t = tailorQuestions(job);
  return FULL_QUESTIONS.map((q) => {
    const ov = t.find((x) => x.qid === q.id);
    return ov ? { ...q, text: ov.text } : q;
  });
}, [job]);
```

Then replace the `FULL_QUESTIONS` reads in `FullGrill` with
`displayQuestions`: the initial message (~lines 372–374), `const q`
(~line 386), `done` (~line 387), the next-question lookup
(~lines 428–429), and the restart init (~lines 459–471). Mirror the
same substitution in `FriendlyGrill`'s question reads.

Because only `text` changes, classification (`classifyAnswer`),
follow-ups, scoring, and verdict logic are untouched — the tailored
grill scores exactly like the default one.

## 3. Fit note at the verdict

Where the verdict renders (the `stage === 'verdict'` block, ~line 658),
append the role-specific fit note when a job was fed:

```tsx
import { jobFitNote } from '../lib/jobTargeting';

{job && (
  <p className="demo-fit-note" data-testid="job-fit-note">
    {jobFitNote(job, answers)}
  </p>
)}
```

`answers` is the run's `FullAnswer[]` state (5 in `FullGrill`, 3 in
`FriendlyGrill` — `jobFitNote` handles any length). The note is 1–2
plain-English sentences against THIS role's requirements, e.g.
"Matches the posting's 8+ year ask. The posting's Kubernetes and
Python requirements aren't evidenced in the answers."

## 4. How features A / B / D consume the JobContext

Feature E owns the parsing and the `JobContext`; A, B, and D read it
from the same `job` prop. All three MUST no-op (default behavior) when
`job === null`.

- **A — ReasoningNarrative** (Builder A): accept an optional
  `job?: Pick<JobContext, 'title' | 'company'>`. When present, the
  narrative summary names the role first:
  "Grilling for the {title} role at {company}: …". `DemoPage` passes
  the same `job` down.
- **B — AiFluencyScore note** (Builder B): when `job` is present, the
  one-line `note` gains a role clause, e.g. "…in the context of a
  {title} interview." Scoring dimensions are unchanged.
- **D — RepoTask selection** (Builder D): the task selector receives
  `job?.roleKeywords`; it picks the fixture with the largest keyword
  overlap with the fixture's tags and falls back to the default fixture
  when `job` is null or no keywords overlap.

## 5. data-testid contract (E2E + QA)

| testid | Element | Notes |
|---|---|---|
| `job-input-step` | `<section>` wrapping the step | First visible step on `#/demo` |
| `job-paste-input` | `<textarea>` | Labeled "Job posting text"; typed char-by-char in E2E |
| `job-submit` | submit `<button>` | "Tailor my grill"; disabled while empty |
| `job-skip` | `<button type="button">` | "Skip — use the default posting"; keyboard-accessible link-style button |
| `job-fit-note` | verdict `<p>` (integrator adds) | Rendered only when `job` is non-null |

## 6. E2E verification

`site/e2e/chakra-e.e2e.mjs` (CDP, serial per AGENTS.md):

```
node site/e2e/chakra-e.e2e.mjs
```

Requires `site/dist` built. It (1) really types a fictional Acme
Robotics posting into the textarea and clicks submit, then picks a
level and asserts the first tailored question names "Acme Robotics"
(screenshot `/tmp/chakra-e-jobinput.png`); (2) reloads, clicks skip,
picks a level, and asserts the default years question appears with no
job leakage (screenshot `/tmp/chakra-e-skip.png`). If the job-input
step isn't mounted yet it exits 2 ("NOT WIRED") with the pointer back
to this doc — not a feature failure.

## 7. Additive-guarantee checklist (verifier)

- [ ] No job fed → `job === null` → `displayQuestions === FULL_QUESTIONS`, no `job-fit-note` rendered, demo byte-identical to today.
- [ ] `parseJobPosting('')` / garbage input → neutral JobContext, all question texts fall back, nothing throws.
- [ ] Styling: `JobInputStep` uses `job-input-*` classes; the integrator adds them to the demo stylesheet (or reuses `demo-opt`/`demo-input` styles).
- [ ] `npx tsc --noEmit -p site/tsconfig.app.json` clean; `npx vitest run` green.

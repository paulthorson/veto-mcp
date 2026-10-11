# Chakra Feature G — Integration guide: resume-vs-job match

Feature G lets the visitor paste their resume so the grill scores it
against the fed job posting (Jobscan-style) and drills them on the gaps
it finds. It is strictly additive: skip the resume step and the demo
behaves exactly as today — no match panel, no gap-driven drill focus.
Only the visitor's own pasted text is ever scored; nothing invents
resume content.

Files delivered by Builder G:

| File | Exports |
|---|---|
| `site/src/lib/resumeMatch.ts` | `scoreResumeMatch`, `gapsToDrills`, `resolveQid`, `KEYWORD_TO_QID`, `GrillQid` |
| `site/src/lib/__tests__/resumeMatch.test.ts` | vitest suite |
| `site/src/demos/grill/ResumeInputStep.tsx` | `<ResumeInputStep onSubmit onSkip />` |
| `site/src/demos/grill/ResumeMatchPanel.tsx` | `<ResumeMatchPanel match />` (default export) |
| `site/e2e/chakra-g.e2e.mjs` | CDP E2E (paste path + skip path) |

## 1. Mount `<ResumeInputStep/>` AFTER the job-input step

`DemoPage` mounts `<JobInputStep/>` as the first stage (see
INTEGRATION-E.md). Insert the resume step between it and the level pick:

```tsx
import { ResumeInputStep } from '../demos/grill/ResumeInputStep';

const [resumeAsked, setResumeAsked] = useState(false);
const [resumeText, setResumeText] = useState<string | null>(null);
```

Render order once `jobAsked === true`:

```tsx
{jobAsked && !resumeAsked && (
  <ResumeInputStep
    onSubmit={(t) => { setResumeText(t); setResumeAsked(true); window.scrollTo({ top: 0, behavior: 'instant' }); }}
    onSkip={() => { setResumeText(null); setResumeAsked(true); window.scrollTo({ top: 0, behavior: 'instant' }); }}
  />
)}
{resumeAsked && level == null && <LevelSelect onPick={pick} />}
{resumeAsked && level === 'friendly' && <FriendlyGrill /* + resumeText, job below */ onSwitchLevel={() => pick(null)} />}
{resumeAsked && (level === 'standard' || level === 'brutal') && (
  <FullGrill /* + resumeText, job below */ level={level} onSwitchLevel={() => pick(null)} />
)}
```

- `resumeText === null` after the step means "skip → no resume match".
- `onSwitchLevel` ("Switch level") keeps `resumeAsked === true` so the
  fed resume survives a level switch — same rule as the fed job.
- Restart resets the run but keeps the fed resume; a full page reload
  re-asks both input steps.

## 2. Compute the match at the verdict; mount the panel there

Add `resumeText: string | null` and `job: JobContext | null` props to
`FullGrill` (and `FriendlyGrill`). At the verdict stage, compute once:

```tsx
import { scoreResumeMatch, gapsToDrills } from '../lib/resumeMatch';
import ResumeMatchPanel from '../demos/grill/ResumeMatchPanel';

const match = useMemo(
  () => (resumeText != null && resumeText.trim() && job != null && job.roleKeywords.length > 0)
    ? scoreResumeMatch(resumeText, job)
    : null,
  [resumeText, job],
);
```

Then render it at the top of the verdict block, before the pass/veto
card:

```tsx
{match != null && <ResumeMatchPanel match={match} />}
```

- `scoreResumeMatch` never throws; the guards above are belt-and-braces.
- When `match` is `null` (skipped resume, or a posting with no
  keywords), render nothing — the verdict is exactly today's.
- `gapsToDrills(match)` is the drill-topic list (see §3).

## 3. Consumption contract — how features A and E use the gaps

`gapsToDrills(match)` returns the deduped grill question ids the grill
should emphasize, in missing-keyword order:

- `'years'` — drill the years-of-experience question harder
  (experience/seniority gaps).
- `'k8s'` — drill the Kubernetes/platform question harder
  (infra/cloud/container gaps). `'python' -> 'k8s'` would be wrong;
  languages map elsewhere.
- `'scale'` — drill the scale-numbers question harder
  (throughput/data/reliability gaps).
- `'motivation'` — languages, frameworks, domains, and soft skills
  land here: there is no dedicated language question, so probe them via
  the motivation question ("why this stack, why this role").
- `'logistics'` is never produced: work-authorization keywords do not
  appear in `roleKeywords`.

**Feature E (tailored questions).** In `tailorQuestions`, questions whose
`qid` appears in `gapsToDrills(match)` get the job's own requirement
phrasing appended — e.g. if `'k8s'` is a drill topic and the posting
requires "Kubernetes in production", the k8s question keeps its text but
adds the posting's requirement as context. Questions not in the drill
list render unchanged.

**Feature A (reasoning narrative).** In the verdict's
`ReasoningNarrative`, when the visitor's answers touch a drill topic,
the per-answer narrative may reference the resume gap it fills or leaves
open — e.g. "never claimed Kubernetes in the grill, and the resume is
missing it too." The narrative must cite only what the visitor typed;
it never invents resume lines.

Both consumers take the plain `string[]` from `gapsToDrills`; neither
re-parses the resume.

## 4. Testids

| Testid | Element |
|---|---|
| `resume-input-step` | `<section>` wrapper of the resume step |
| `resume-paste-input` | the resume `<textarea>` |
| `resume-submit` | "Score my resume" button (disabled while empty) |
| `resume-skip` | "Skip — grill me without my resume" button |
| `resume-match-panel` | `<ResumeMatchPanel>` wrapper at the verdict |
| `resume-match-score` | the `{score}/100` readout inside the panel |
| `resume-gaps` | the `<ul>` of plain-English gap statements |

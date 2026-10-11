/* Feature A — reasoning narrative for the grill verdict.
 * HOW the candidate approached the problems, not just pass/fail.
 *
 * Pure, deterministic string building over the recorded FullAnswer[]:
 * no randomness, no model calls, no dates, no I/O. Same answers in =>
 * same narrative out, always. Plain English throughout.
 */

import { parseK8s, parseLogistics, parseYears } from './demoGrill';
import type { FullAnswer } from './demoGrill';
import type { JobContext, ReasoningNarrative } from './chakraTypes';

/* Short topic labels used when naming what was answered or dodged. */
const Q_TOPIC: Record<string, string> = {
  years: 'experience',
  k8s: 'Kubernetes',
  scale: 'scale',
  logistics: 'work authorization',
  motivation: 'motivation',
};

const snippet = (s: string, n: number): string =>
  s.length > n ? `${s.slice(0, n)}…` : s;

const quote = (s: string): string => `“${snippet(s.trim(), 48)}”`;

/* ---------------- per-answer sentences (one sentence each) ---------------- */

function yearsNarrative(a: FullAnswer): string {
  const yrs = parseYears(a.text);
  if (a.cls === 'specific' && yrs != null)
    return `When asked about years of backend experience, they answered with a number straight away: ${quote(a.text)} — a candidate who knows their own track record.`;
  if (a.cls === 'specific')
    return `They gave a direct answer on experience: ${quote(a.text)} — it commits to something, which is what the question was for.`;
  return `Asked how many years of backend experience they have, they dodged with ${quote(a.text)} — even a rough number would do, so the dodge reads as deliberate.`;
}

function k8sNarrative(a: FullAnswer): string {
  const stance = parseK8s(a.text);
  if (a.cls === 'vague' || stance === 'unclear')
    return `On Kubernetes they hedged: ${quote(a.text)} — neither a yes nor a no, which in a grill reads as a no.`;
  if (stance === 'prod')
    return `They gave Kubernetes a straight yes: ${quote(a.text)} — production experience, which is the skill this question exists to check.`;
  if (stance === 'home')
    return `They were honest about Kubernetes being homelab-only: ${quote(a.text)} — an honest gap beats a fake yes.`;
  return `They said plainly they have no Kubernetes experience: ${quote(a.text)} — a clean no that settles the question.`;
}

function scaleNarrative(a: FullAnswer): string {
  if (a.cls === 'specific')
    return `They reached for numbers on scale without being asked twice: ${quote(a.text)} — a candidate comfortable being checked.`;
  return `Asked for the largest scale they had operated at, they gave nothing checkable: ${quote(a.text)} — scale claims without numbers don't survive a grill.`;
}

function logisticsNarrative(a: FullAnswer): string {
  const { auth, nyc } = parseLogistics(a.text);
  if (auth === 'yes' && nyc === 'yes')
    return `They gave a clean logistics answer: ${quote(a.text)} — authorization and NYC settled in one line.`;
  if (auth === 'yes')
    return `They confirmed US work authorization: ${quote(a.text)} — but left the NYC part loose, which is the thread still hanging.`;
  if (auth === 'no')
    return `They answered the authorization question straight: ${quote(a.text)} — a clean no closes the loop faster than a dodge.`;
  return `On work authorization they went fuzzy: ${quote(a.text)} — the one question where fuzzy is the worst possible answer.`;
}

function motivationNarrative(a: FullAnswer): string {
  if (a.cls === 'specific')
    return `They gave a real reason for wanting this role: ${quote(a.text)} — thought through, not memorized.`;
  return `They answered the motivation question with a pitch instead of a reason: ${quote(a.text)} — which says they want a job, not this job.`;
}

function genericNarrative(a: FullAnswer): string {
  const topic = Q_TOPIC[a.qid] ?? a.qid;
  return a.cls === 'specific'
    ? `On ${topic} they answered directly: ${quote(a.text)} — no hedging.`
    : `On ${topic} they dodged: ${quote(a.text)} — the answer says more about caution than substance.`;
}

/* ---------------- job tie-in (Feature E context) ---------------- */

/* A job tie-in is only honest when the answer takes an AFFIRMATIVE
   stance: it must be specific (not a dodge) and must not state a gap.
   Claiming 'speaks to the posting's "X" requirement' for a negation —
   e.g. 'I have no Kubernetes experience' against a 'Kubernetes in
   production' requirement — is a false match, so negations and dodges
   never get a tie-in. Deterministic: requirements are tried in order. */

/* Negation markers that turn a specific answer into a stated gap.
   Word-boundary anchored so ordinary words never false-hit ("note",
   "innovative" are safe). The honest failure mode is withholding the
   tie-in, so a genuinely affirmative phrase with a stray "no" ("no
   problem with X") is also withheld rather than risking a false
   claim. */
const NEGATION_RE =
  /\b(no|not|never|none|zero|without|lack(?:s|ed|ing)?|cannot|can't|won't|don't|doesn't|didn't|haven't|hasn't|hadn't|isn't|aren't|wasn't|weren't|wouldn't|shouldn't|couldn't|mustn't|needn't)\b/i;

function hasNegation(text: string): boolean {
  /* Curly apostrophe U+2019 (what phones and dictation emit, e.g.
     "don’t") is normalized to ASCII ' before testing — cheaper and
     less error-prone than doubling every contraction alternation in
     NEGATION_RE. Plain English: negation wording stays negation
     wording however it was typed. */
  return NEGATION_RE.test(text.replace(/\u2019/g, "'"));
}

function isAffirmativeStance(a: FullAnswer): boolean {
  if (a.cls !== 'specific') return false;
  switch (a.qid) {
    case 'k8s':
      /* Only a production yes maps to a Kubernetes requirement; a
         homelab-only or explicit no is a stated gap, not a match. */
      return parseK8s(a.text) === 'prod' && !hasNegation(a.text);
    case 'logistics': {
      /* A tie-in claims the answer lines up with a posting requirement,
         so it needs a fully affirmative parse: authorization CONFIRMED
         and the location settled. A denied authorization is a negation,
         and fuzzy authorization ('unclear') contradicts the claim — the
         posting's "US work authorization" requirement cannot be tied to
         an answer that went fuzzy on authorization — so only
         auth==='yes' + nyc==='yes' qualifies. */
      const { auth, nyc } = parseLogistics(a.text);
      return auth === 'yes' && nyc === 'yes';
    }
    default:
      /* years / scale / motivation / unknown qids: a specific answer
         commits to something, which is the affirmative stance — unless
         the text carries a negation marker, which turns it into a
         stated gap ("I have zero years of backend experience",
         "I do not want a backend engineering role"). */
      return !hasNegation(a.text);
  }
}

/* First requirement phrase that shares a real word (4+ chars) with the
   answer text, or null. Deterministic: requirements are tried in order. */
function matchRequirement(job: JobContext, text: string): string | null {
  const t = text.toLowerCase();
  for (const req of job.requirements) {
    const words = req
      .toLowerCase()
      .split(/[^a-z0-9+]+/)
      .filter((w) => w.length >= 4);
    if (words.some((w) => t.includes(w))) return req;
  }
  return null;
}

/* Fold the job tie-in into the single sentence as a trailing clause —
   the per-answer narrative stays one sentence. Only affirmative
   stances get a tie-in; negations and dodges keep the base sentence. */
function withJobTie(base: string, job: JobContext | undefined, a: FullAnswer): string {
  if (!job) return base;
  if (!isAffirmativeStance(a)) return base;
  const req = matchRequirement(job, a.text);
  if (!req) return base;
  return `${base.slice(0, -1)} — which speaks to the posting's “${req}” requirement.`;
}

function buildPerAnswer(
  answers: FullAnswer[],
  job: JobContext | undefined,
): ReasoningNarrative['perAnswer'] {
  return answers.map((a) => {
    const base =
      a.qid === 'years'
        ? yearsNarrative(a)
        : a.qid === 'k8s'
          ? k8sNarrative(a)
          : a.qid === 'scale'
            ? scaleNarrative(a)
            : a.qid === 'logistics'
              ? logisticsNarrative(a)
              : a.qid === 'motivation'
                ? motivationNarrative(a)
                : genericNarrative(a);
    return { qid: a.qid, narrative: withJobTie(base, job, a) };
  });
}

/* The job tie-in sentence: the first affirmative answer (in question
   order) that shares a topic with one of the posting's requirements,
   or '' when there is none. Not the "strongest" link — just the first
   overlap, in deterministic order. */
function jobTieSentence(specific: FullAnswer[], job: JobContext | undefined): string {
  if (!job) return '';
  const hit = specific
    .filter(isAffirmativeStance)
    .map((a) => ({ a, req: matchRequirement(job, a.text) }))
    .find((x) => x.req != null);
  if (!hit || !hit.req) return '';
  const topic = Q_TOPIC[hit.a.qid] ?? hit.a.qid;
  return ` Their ${topic} answer speaks to the posting's “${hit.req}” requirement.`;
}

function buildSummary(
  answers: FullAnswer[],
  job: JobContext | undefined,
): string {
  if (answers.length === 0)
    return `No answers came back from the grill, so there is no read to give. The narrative needs answers before it can say anything about how the candidate thinks.`;
  const specific = answers.filter((a) => a.cls === 'specific');
  const vague = answers.filter((a) => a.cls !== 'specific');
  const topics = (list: FullAnswer[]): string =>
    list.map((a) => Q_TOPIC[a.qid] ?? a.qid).join(', ');
  if (vague.length === 0)
    return `They answered every question head-on: numbers where numbers were due, straight stances on Kubernetes and authorization, and a real reason for wanting the role.${jobTieSentence(specific, job)} That is the pattern of a candidate who expects their claims to be checked — nothing in the session reads as a dodge.`;
  if (specific.length === 0)
    return `They dodged the whole grill. No usable numbers on experience or scale, no firm stance on Kubernetes or authorization, and a pitch where a reason should be. When every answer is a dodge, it reads as a candidate who does not want their claims checked.`;
  const first = `They went ${specific.length} for ${answers.length} on specifics: ${topics(specific)} got straight answers, while ${topics(vague)} got dodges.`;
  const last = `The read is mixed — the answers they gave look checkable, and the ones they dodged are where the story gets thin.`;
  return `${first}${jobTieSentence(specific, job)} ${last}`;
}

/* ---------------- entry point ---------------- */

export function buildReasoningNarrative(
  answers: FullAnswer[],
  job?: JobContext,
): ReasoningNarrative {
  return {
    summary: buildSummary(answers, job),
    perAnswer: buildPerAnswer(answers, job),
  };
}

/* Feature B: AI fluency scoring for the immersive grill demo.
 *
 * A second score dimension alongside the fit score: how well the candidate
 * works WITH AI. Three deterministic sub-dimensions (0-100 each):
 *   - framing:  did they frame the problem well — specific context,
 *                constraints, numbers a collaborator could act on
 *   - judgment: did they show judgment rather than blind trust —
 *                qualified claims, tradeoffs/limits noted
 *   - steering: did they steer effectively — precise, directed answers
 *                vs vague hand-waving
 *
 * All heuristics are deterministic, rule-based, and derived from answer
 * text only. No randomness, no model calls — E2E tests can drive exact
 * paths (same contract as demoGrill.ts).
 *
 * WEIGHTS (documented, exported, pinned by tests):
 *   overall = round(0.40 * framing + 0.35 * judgment + 0.25 * steering)
 */

import type { FullAnswer } from './demoGrill';
import type { AiFluencyDimensions, AiFluencyScore, JobContext } from './chakraTypes';

/** Weights of the three sub-dimensions in the overall score. Sum = 1. */
export const AI_FLUENCY_WEIGHTS = {
  framing: 0.4,
  judgment: 0.35,
  steering: 0.25,
} as const;

/* ---------------- Shared patterns ---------------- */

/* A number only counts when it carries meaning: digit + a domain word
   that gives the number context (scale, time, users, money, limits).
   The 'ms' alternative only matches the millisecond token — standalone
   ('500 ms') or digit-attached ('120ms') — never word tails like
   'teams' or 'dreams' (the lookbehind requires a digit before 'ms'). */
const DIGIT_RE = /\d/;
const CONTEXT_RE =
  /(year|month|week|day|req|request|rps|qps|latency|p99|p95|throughput|user|customer|node|cluster|pod|container|instance|server|machine|traffic|million|billion|thousand|percent|cost|budget|sla|deadline|(\bms\b|(?<=\d)ms\b)|scale|on-?call|constraint|requirement|deadline|incident|deploy)/;

/* Named, concrete tooling — saying the actual thing beats "some tool". */
const TOOL_RE =
  /(kubernetes|eks|gke|aks|helm|terraform|docker|postgres|mysql|redis|kafka|aws|gcp|azure|grafana|prometheus|datadog|github actions|ci\/cd|sqs|sns)/;

/* Framing boosters: the constraints a collaborator would need to act. */
const FRAMING_MOD_RE = /(constraint|requirement|deadline|budget|cost|sla|acceptance|scale to|handle|support)/;

/* Judgment: tradeoff/limit language — qualified claims, not certainties.
   'reviewed' is deliberately NOT here: VERIFY_RE already counts the
   'review' inside it, so listing it here would double-count one word. */
const TRADEOFF_RE =
  /(trade-?off|depends on|however|in production|in practice|limitation|edge case|caveat|assuming|risk|downside|rather than|instead of|alternatively|not always|peer review)/;

/* Judgment: verification language — checked the output, not blind trust. */
const VERIFY_RE = /(review|verify|verified|checked|tested|validated|double-?check|audit|measure|measured)/;

/* Judgment: honest uncertainty — naming what you don't know is judgment. */
const HONEST_RE = /(i don't know|don't know|not sure|would have to check|need to check)/;

/* Judgment penalty: absolute, unqualified claims read as blind trust. */
const ABSOLUTE_RE = /\b(always|never|guarantee[sd]?|best practice|industry standard|obviously|no-?brainer)\b/;

/* Steering penalty: hedge words — the opposite of a precise instruction. */
const HEDGE_RE = /\b(some|kinda|sort of|a bit|around|roughly|stuff|things|maybe|probably|decent|basically|a little|ish)\b|-ish\b/;

function clamp100(n: number): number {
  return Math.max(0, Math.min(100, Math.round(n)));
}

/* ---------------- Per-answer dimension scoring (0-100 each) ---------------- */

/** Framing: did the answer frame the problem with concrete, actionable context?
 *  Reachable range 0–100: an answer with concrete numbers in context, a
 *  named constraint, and a named tool earns the completeness bonus and
 *  the full 100 (mirrors scoreSteering's precision bonus). */
export function scoreFraming(text: string): number {
  const t = text.toLowerCase();
  let s = 25;
  const hasSubstance = DIGIT_RE.test(t) && CONTEXT_RE.test(t);
  if (hasSubstance) s += 40;
  const hasConstraint = FRAMING_MOD_RE.test(t);
  if (hasConstraint) s += 20;
  const hasTool = TOOL_RE.test(t);
  if (hasTool) s += 10;
  /* Completeness bonus: substance + constraint + named tool together is
     a fully-framed answer — this is what makes 100 reachable. */
  if (hasSubstance && hasConstraint && hasTool) s += 5;
  return clamp100(s);
}

/** Judgment: did the answer show judgment — qualified claims, tradeoffs, checks? */
export function scoreJudgment(text: string): number {
  const t = text.toLowerCase();
  /* Neutral baseline: an answer is neither judgmental nor blind by
     default. Tradeoff/verification language raises it; absolutes lower it. */
  let s = 50;
  const tradeoffHits = (t.match(new RegExp(TRADEOFF_RE.source, 'g')) ?? []).length;
  s += Math.min(tradeoffHits, 2) * 20;
  if (VERIFY_RE.test(t)) s += 15;
  if (HONEST_RE.test(t)) s += 10;
  const absoluteHits = (t.match(new RegExp(ABSOLUTE_RE.source, 'g')) ?? []).length;
  s -= Math.min(absoluteHits, 2) * 10;
  return clamp100(s);
}

/** Steering: is the answer precise and directed, or hedgy hand-waving?
 *  Reachable range 0–100: a precisely-steered answer (concrete numbers with
 *  context, sufficient length, zero hedge words) earns the full 100. */
export function scoreSteering(text: string): number {
  const t = text.toLowerCase();
  let s = 40;
  const hasSubstance = DIGIT_RE.test(t) && CONTEXT_RE.test(t);
  if (hasSubstance) s += 25;
  if (t.length >= 30) s += 10;
  const hedgeHits = (t.match(new RegExp(HEDGE_RE.source, 'g')) ?? []).length;
  s -= hedgeHits * 15;
  /* Precision bonus: concrete substance with zero hedging is exactly what
     precise steering looks like — this makes 100 reachable. */
  if (hasSubstance && hedgeHits === 0) s += 25;
  return clamp100(s);
}

const avg = (ns: number[]): number =>
  ns.length === 0 ? 0 : ns.reduce((a, b) => a + b, 0) / ns.length;

/* ---------------- Overall ---------------- */

/** Plain-English band for an overall score. Exported for boundary testing. */
export function bandNote(score: number): string {
  if (score >= 75)
    return 'frames problems with concrete context, shows judgment, and steers precisely';
  if (score >= 50) return 'decent signal — firmer numbers and sharper steering would help';
  return 'vague — hand-waving dominates; AI collaborations would stall on follow-ups';
}

/** How many of the posting's role keywords show up in the candidate's answers.
 *
 * MATCHING POLICY (deliberate, pinned by tests): substring matching.
 * A keyword counts when it appears anywhere in the answers,
 * case-insensitive — including inside other words ('end' matches
 * 'backend'). This favors recall over precision for the demo; the note
 * only feeds copy, never the score. */
function roleKeywordHits(answers: FullAnswer[], job: JobContext): { hits: number; total: number } {
  const corpus = answers.map((a) => a.text.toLowerCase()).join(' ');
  const keywords = job.roleKeywords.map((k) => k.toLowerCase()).filter((k) => k.length > 0);
  const total = keywords.length > 0 ? keywords.length : job.requirements.length;
  if (total === 0) return { hits: 0, total: 0 };
  const hits = (keywords.length > 0 ? keywords : job.requirements.map((r) => r.toLowerCase())).filter(
    (k) => corpus.includes(k),
  ).length;
  return { hits, total };
}

/** Score AI fluency for a completed grill run. Deterministic. */
export function scoreAiFluency(answers: FullAnswer[], job?: JobContext): AiFluencyScore {
  const dimensions: AiFluencyDimensions = {
    framing: Math.round(avg(answers.map((a) => scoreFraming(a.text)))),
    judgment: Math.round(avg(answers.map((a) => scoreJudgment(a.text)))),
    steering: Math.round(avg(answers.map((a) => scoreSteering(a.text)))),
  };
  const score = Math.round(
    dimensions.framing * AI_FLUENCY_WEIGHTS.framing +
      dimensions.judgment * AI_FLUENCY_WEIGHTS.judgment +
      dimensions.steering * AI_FLUENCY_WEIGHTS.steering,
  );
  let note = `AI fluency ${score}/100 — ${bandNote(score)}.`;
  if (job) {
    const { hits, total } = roleKeywordHits(answers, job);
    note +=
      total > 0
        ? ` For the ${job.title} posting, answers reference ${hits}/${total} of the role keywords.`
        : ` For the ${job.title} posting, the job has no listed keywords to match against.`;
  }
  return { score, dimensions, note };
}

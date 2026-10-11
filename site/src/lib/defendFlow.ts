/* Feature C (Chakra): defend-your-answer flow, brutal level only.
 * After a candidate submits an answer, the grill may demand they DEFEND it —
 * especially when the answer looks AI-generated or was accepted via quick-pick
 * without engagement. This tests real understanding vs pasted output.
 *
 * Pure functions — no randomness, no model calls, fully deterministic.
 * Implements DefenseAssessment from ./chakraTypes.
 */

import type { DefenseAssessment } from './chakraTypes';
import { FULL_QUESTIONS, classifyAnswer } from './demoGrill';

/* ------------------------------------------------------------------ */
/* getDefendPrompt: a pointed follow-up demanding explanation.         */
/* Two variants per question id; the variant is picked deterministically */
/* by answer-text length parity (even -> variant 0, odd -> variant 1). */
/* Plain, sharp tone matching the brutal voice.                       */
/* ------------------------------------------------------------------ */

type QuestionId = 'years' | 'k8s' | 'scale' | 'logistics' | 'motivation';

const SNIPPET_LEN = 64;
const snippet = (s: string): string =>
  s.length > SNIPPET_LEN ? `${s.slice(0, SNIPPET_LEN)}…` : s;

type DefendPromptFn = (answerSnippet: string) => string;

const DEFEND_PROMPTS: Record<QuestionId, [DefendPromptFn, DefendPromptFn]> = {
  years: [
    (a: string) =>
      `You said "${a}". Defend it: what did those years actually teach you that a junior couldn't pick up in a weekend?`,
    (a: string) =>
      `That number — "${a}". Convince me it's real: describe one war story only someone with those years would have.`,
  ],
  k8s: [
    (a: string) =>
      `You said "${a}". Walk me through what breaks at 3am when a node goes NotReady — no hand-waving.`,
    (a: string) =>
      `You claimed "${a}". Your cluster just lost its control plane at deploy time. First command you run, and why?`,
  ],
  scale: [
    (a: string) =>
      `You threw out "${a}". Back it up: what does that load do to your p99 when a downstream goes slow?`,
    (a: string) =>
      `"${a}" — big number. Prove you were there: what broke at that scale that nobody warned you about?`,
  ],
  logistics: [
    (a: string) =>
      `You said "${a}". Spelled out: what status, and who holds the paperwork?`,
    (a: string) =>
      `"${a}". Fine. Which office is your manager sitting in on the three days you're on-site?`,
  ],
  motivation: [
    (a: string) =>
      `You said "${a}". That's a line. Name one thing this fintech does that its competitors don't — and why you care.`,
    (a: string) =>
      `"${a}". Cute. Now the real one: what would make you stay past year two?`,
  ],
};

const FALLBACK_PROMPT = (a: string): string =>
  `You said "${a}". Defend it: prove you understand what you just claimed, in your own words.`;

/** Pointed follow-up demanding the candidate explain their answer. */
export function getDefendPrompt(
  question: { id: string; text: string },
  answerText: string,
): string {
  const a = snippet(answerText.trim());
  const pair = (DEFEND_PROMPTS as Record<string, [(s: string) => string, (s: string) => string] | undefined>)[
    question.id
  ];
  if (!pair) return FALLBACK_PROMPT(a);
  return pair[answerText.trim().length % 2](a);
}

/* ------------------------------------------------------------------ */
/* shouldDemandDefense: deterministic trigger rules.                   */
/*                                                                     */
/*  R1. Vague answers ALWAYS trigger. The grill already doubts the      */
/*      answer; a defense is the only way to keep it.                  */
/*  R2. Specific answers trigger only when they look low-effort:        */
/*      R2a. quick-pick label verbatim — an exact label match cannot      */
/*           prove a click (a typed answer could match the label too),    */
/*           but verbatim label text means no engagement beyond the       */
/*           label itself, so understanding is unproven. (Exact label    */
/*           match against FULL_QUESTIONS.)                              */
/*      R2b. under 20 chars — too short to carry real detail, even      */
/*           when the classifier calls it specific ("9 years").        */
/*      R2c. contains an AI-tell — phrases typical of pasted chatbot    */
/*           output ("as an AI", "it's important to note",            */
/*           "in today's fast-paced", "furthermore"). Detection only;  */
/*           these phrases never appear in user-facing copy.           */
/*  Anything else is a real typed answer: no defense demanded.         */
/* ------------------------------------------------------------------ */

const AI_TELL_RE =
  /as an ai\b|as a language model|it's important to note|in today's fast-paced|furthermore|moreover|in the ever-evolving/;

function isQuickPickVerbatim(qid: string, text: string): boolean {
  const q = FULL_QUESTIONS.find((x) => x.id === qid);
  return q?.picks.some((p) => p.label === text.trim()) ?? false;
}

export function shouldDemandDefense(
  qid: string,
  answerText: string,
  cls: 'specific' | 'vague',
): boolean {
  const text = answerText.trim();
  /* R1: vague always triggers. */
  if (cls === 'vague') return true;
  /* R2a: quick-pick clicked, not typed. */
  if (isQuickPickVerbatim(qid, text)) return true;
  /* R2b: too short to carry detail. */
  if (text.length < 20) return true;
  /* R2c: pasted-chatbot tells. */
  if (AI_TELL_RE.test(text.toLowerCase())) return true;
  return false;
}

/* ------------------------------------------------------------------ */
/* assessDefense: did the defense demonstrate real understanding?      */
/*                                                                     */
/*  understood = true only when the defense is BOTH:                   */
/*    (a) specific — digit+domain context, or >= 24 chars, AND no       */
/*        hedge words. The no-hedge bar is explicit here (a local       */
/*        hedge-word list, below), not just delegated to classifyAnswer */
/*        — defenses are held to a higher bar than answers, hence the   */
/*        raised length floor and the hedge check that fires even when  */
/*        digit+context text would otherwise pass; and                  */
/*    (b) referencing — shares at least one key term with the original */
/*        answer (content word of 3+ letters, or a digit). The defense  */
/*        must tie back to what was actually claimed, not deflect.      */
/*                                                                     */
/*  score 0–100: +55 specific, +25 references the claim, +10 digit +   */
/*  domain context, +10 length >= 60. Clamped. Deterministic.           */
/* ------------------------------------------------------------------ */

const STOPWORDS = new Set(
  'a,an,the,and,or,of,to,in,on,for,with,is,it,its,i,my,me,we,our,at,as,be,was,were,by,from,that,this,these,those,have,has,had,you,your,they,their,them,he,she,his,her,do,does,did,not,no,so,but,if,just,very,about,some,all,can,will,would,when,what,which,who,how,been,are,into,out,up,over,than,then,there,also,only,own,such'.split(
    ',',
  ),
);

function keyTerms(text: string): Set<string> {
  const terms = new Set<string>();
  for (const tok of text.toLowerCase().split(/[^a-z0-9]+/)) {
    if (tok === '') continue;
    if (/^\d+$/.test(tok)) {
      terms.add(tok);
      continue;
    }
    if (tok.length >= 3 && !STOPWORDS.has(tok)) terms.add(tok);
  }
  return terms;
}

/** classifyAnswer-like specificity check for defenses: digit+domain
 *  context, or >= 24 chars — with an explicit no-hedge-words check on
 *  top. classifyAnswer alone passes digit+context text even when it is
 *  hedged ('I ran EKS for 5 years, sort of'); defenses are held to a
 *  higher bar, so hedged defenses fail here regardless of substance. */
/* Hedge words that fail a defense outright. Mirrors demoGrill's hedge
   list (kept local and explicit so the raised bar is real in this
   module rather than inherited from the classifier's rule order). */
const DEFENSE_HEDGE_RE =
  /\b(some|kinda|familiar|exposure|decent|around|touched|basics|little|sort of|a bit|-ish)\b/;

function defenseIsSpecific(qid: string, text: string): boolean {
  const t = text.trim();
  if (t.length === 0) return false;
  if (DEFENSE_HEDGE_RE.test(t.toLowerCase())) return false;
  if (classifyAnswer(qid, t) !== 'specific') return false;
  return /\d/.test(t) || t.length >= 24;
}

function referencesClaim(originalAnswer: string, defenseText: string): boolean {
  const orig = keyTerms(originalAnswer);
  if (orig.size === 0) return true; /* nothing to tie back to — can't fail this check */
  const def = keyTerms(defenseText);
  for (const term of orig) {
    if (def.has(term)) return true;
  }
  return false;
}

export function assessDefense(
  questionId: string,
  originalAnswer: string,
  defenseText: string,
): DefenseAssessment {
  const specific = defenseIsSpecific(questionId, defenseText.trim());
  const tied = referencesClaim(originalAnswer, defenseText);

  let score = 0;
  if (specific) score += 55;
  if (tied) score += 25;
  if (/\d/.test(defenseText) && classifyAnswer(questionId, defenseText.trim()) === 'specific')
    score += 10;
  if (defenseText.trim().length >= 60) score += 10;
  score = Math.max(0, Math.min(100, score));

  const understood = specific && tied;

  let note: string;
  if (understood) {
    note =
      'The defense named specifics and tied them back to the claim. It held.';
  } else if (!specific) {
    note =
      'The defense had no detail to check — nothing to verify, nothing kept.';
  } else {
    note =
      'The defense dodged the claim — it never touched what was actually said.';
  }

  return { understood, score, note };
}

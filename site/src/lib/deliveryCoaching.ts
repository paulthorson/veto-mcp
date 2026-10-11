/* Feature H: delivery coaching for the immersive grill demo.
 *
 * Coaches HOW the candidate answers — filler words, hedging, pacing —
 * in the spirit of Yoodli-style speech coaching, but text-based so the
 * demo works without a microphone.
 *
 * The analyzer takes plain text (analyzeDelivery(text)) and returns
 * DeliveryFeedback (see chakraTypes.ts).
 *
 * FUTURE SPEECH SEAM: when real audio arrives, feed the speech-to-text
 * transcript string into analyzeDelivery unchanged — `transcript: string`
 * in, the same DeliveryFeedback out. The module never needs rework;
 * only the caller changes (typed answers become transcripts).
 * analyzeDeliveryAcross aggregates a full grill run and is what the
 * verdict stage consumes.
 *
 * Deterministic, rule-based, no randomness, no model calls.
 * Coach tone: direct and specific, never shaming.
 */

import type { DeliveryFeedback } from './chakraTypes';

/* ---------------- Filler words ---------------- */

/* MATCHING POLICY (deliberate, pinned by tests): bare-word matching.
   Every occurrence of a filler word counts — including content uses, so
   "I like this framework" counts a "like". Text has no prosody, and a
   syntactic parser would be false precision in a demo, so the meter
   reports what it can see. The suggestion copy stays honest about it:
   "you said 'like' N times" is literally true, and the fix is phrased
   as trading the filler uses for a pause (leaving the content uses
   alone).
   Word-boundary, case-insensitive matches. "well," and "so," only count
   at the start of a sentence (start of text, or right after . ! ?) —
   a mid-sentence "well," is emphasis, not a filler. */
const SINGLE_FILLERS: [string, string][] = [
  ['um', '\\bum\\b'],
  ['uh', '\\buh\\b'],
  ['like', '\\blike\\b'],
  ['you know', '\\byou know\\b'],
  ['sort of', '\\bsort of\\b'],
  ['kind of', '\\bkind of\\b'],
  ['basically', '\\bbasically\\b'],
  ['actually', '\\bactually\\b'],
];

const SENTENCE_START_FILLERS: [string, string][] = [
  ['well,', 'well'],
  ['so,', 'so'],
];

const SENTENCE_END = /[.!?]\s+/;

/* ---------------- Hedging ---------------- */

/* FORMULA (pinned by tests):
 *   hedgingScore = min(100, round(hedgeHits / max(1, wordCount) * 400))
 * hedgeHits counts phrase occurrences, not words — a two-word phrase
 * like "i think" is ONE hit — so one phrase hit per four words
 * saturates the meter at 100. The max(1, ...) guard keeps empty text
 * at 0 instead of dividing by zero.
 */
const HEDGE_PHRASES = [
  'maybe',
  'probably',
  'i think',
  'might',
  'could be',
  'not sure',
  'i guess',
  'hopefully',
];

const HEDGE_SUGGESTION_THRESHOLD = 40; // 40/100 ~= one hedge per ten words

/* ---------------- Pacing ---------------- */

/* THRESHOLDS (pinned by tests), on word count:
 *   < 10 words        -> very brief: the grill reads short answers as evasive
 *   10–60 words       -> good length for a spoken-style answer
 *   > 60 words        -> thorough, but risks rambling
 */
export const PACING_BRIEF_MAX = 10;
export const PACING_GOOD_MAX = 60;

export function pacingNoteFor(wordCount: number): string {
  if (wordCount <= 0)
    return 'No answer to pace — nothing to read yet.';
  if (wordCount < PACING_BRIEF_MAX)
    return 'Very brief — the grill reads short answers as evasive.';
  if (wordCount <= PACING_GOOD_MAX) return 'Good length for a spoken-style answer.';
  return 'Thorough, but watch rambling — tighten to the strongest point.';
}

/* ---------------- Shared counting ---------------- */

function wordCount(text: string): number {
  const trimmed = text.trim();
  return trimmed === '' ? 0 : trimmed.split(/\s+/).length;
}

function countMatches(text: string, source: string): number {
  return (text.match(new RegExp(source, 'gi')) ?? []).length;
}

function countSentenceStart(text: string, word: string): number {
  let n = 0;
  const re = new RegExp(`(^|${SENTENCE_END.source})(${word}),`, 'gi');
  for (const _ of text.matchAll(re)) n++;
  return n;
}

/* Byte-wise string comparison for tie-breaks. localeCompare is
   locale-dependent, which would weaken the determinism claim; < / >
   on UTF-16 code units is the same on every machine. */
function byteCompare(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

function countFillers(text: string): { word: string; count: number }[] {
  const counts = new Map<string, number>();
  for (const [label, source] of SINGLE_FILLERS) {
    const n = countMatches(text, source);
    if (n > 0) counts.set(label, n);
  }
  for (const [label, word] of SENTENCE_START_FILLERS) {
    const n = countSentenceStart(text, word);
    if (n > 0) counts.set(label, n);
  }
  /* Deterministic ranking: most frequent first, byte-wise tie-break. */
  return [...counts.entries()]
    .map(([word, count]) => ({ word, count }))
    .sort((a, b) => b.count - a.count || byteCompare(a.word, b.word));
}

function countHedges(text: string): number {
  return HEDGE_PHRASES.reduce(
    (total, phrase) => total + countMatches(text, `\\b${phrase}\\b`),
    0,
  );
}

/* ---------------- Suggestions ---------------- */

type SuggestionTheme = 'filler' | 'hedging' | 'short' | 'long' | 'general';

interface ThemedSuggestion {
  theme: SuggestionTheme;
  text: string;
}

const EMPTY_SUGGESTION = 'No answer to analyze — even a rough answer beats silence.';

function times(n: number): string {
  return n === 1 ? 'time' : 'times';
}

/* Top filler gets the named callout (e.g. "You said 'um' 4 times —
   trade the filler uses for a silent pause."). The phrasing stays
   honest about the bare-word policy: the count is literal, and only the
   filler uses get traded. Sentence-start "well,"/"so," get their own
   phrasing since the fix is different: let the pause do the work. */
function fillerSuggestion(top: { word: string; count: number }): ThemedSuggestion {
  if (top.word === 'well,' || top.word === 'so,') {
    return {
      theme: 'filler',
      text: `You started ${top.count} sentence${top.count === 1 ? '' : 's'} with '${top.word}' — let the pause do the work instead.`,
    };
  }
  return {
    theme: 'filler',
    text: `You said '${top.word}' ${top.count} ${times(top.count)} — trade the filler uses for a silent pause.`,
  };
}

function suggestionsFor(
  fillerWords: { word: string; count: number }[],
  fillerTotal: number,
  hedgingScore: number,
  wc: number,
): ThemedSuggestion[] {
  if (wc === 0) return [{ theme: 'general', text: EMPTY_SUGGESTION }];
  const out: ThemedSuggestion[] = [];
  if (fillerTotal > 0) out.push(fillerSuggestion(fillerWords[0]));
  if (hedgingScore >= HEDGE_SUGGESTION_THRESHOLD)
    out.push({
      theme: 'hedging',
      text: "Hedging like 'maybe' and 'I think' softened this answer — trade one hedge for a claim you can defend.",
    });
  if (wc < PACING_BRIEF_MAX)
    out.push({
      theme: 'short',
      text: "Very short — add one concrete example so it doesn't read as dodging.",
    });
  if (wc > PACING_GOOD_MAX)
    out.push({
      theme: 'long',
      text: 'Long answer — cut it to your single strongest point and let them ask for more.',
    });
  if (out.length === 0)
    out.push({
      theme: 'general',
      text: 'Clean delivery — read it out loud once; if it sounds steady, submit it.',
    });
  return out.slice(0, 3);
}

/* ---------------- Public API ---------------- */

interface BuiltDelivery {
  feedback: DeliveryFeedback;
  wordCount: number;
  themes: SuggestionTheme[];
}

function buildDelivery(text: string): BuiltDelivery {
  const fillerWords = countFillers(text);
  const fillerTotal = fillerWords.reduce((sum, f) => sum + f.count, 0);
  const wc = wordCount(text);
  const hedgeHits = countHedges(text);
  const hedgingScore = Math.min(100, Math.round((hedgeHits / Math.max(1, wc)) * 400));
  const themed = suggestionsFor(fillerWords, fillerTotal, hedgingScore, wc);
  const feedback: DeliveryFeedback = {
    fillerWords,
    fillerTotal,
    hedgingScore,
    pacingNote: pacingNoteFor(wc),
    suggestions: themed.map((s) => s.text),
  };
  return { feedback, wordCount: wc, themes: themed.map((s) => s.theme) };
}

/** Analyze delivery for a single answer's text. Deterministic. */
export function analyzeDelivery(text: string): DeliveryFeedback {
  return buildDelivery(text).feedback;
}

/* Aggregate phrasing: same themes as single-answer suggestions, but
   rendered with run-wide numbers ("across your answers"). */
function aggregateSuggestionFor(
  theme: SuggestionTheme,
  topFiller: { word: string; count: number } | null,
): string {
  switch (theme) {
    case 'filler': {
      const top = topFiller ?? { word: 'um', count: 0 };
      if (top.word === 'well,' || top.word === 'so,')
        return `You started ${top.count} sentence${top.count === 1 ? '' : 's'} with '${top.word}' across your answers — let the pause do the work instead.`;
      return `You said '${top.word}' ${top.count} ${times(top.count)} across your answers — trade the filler uses for a silent pause.`;
    }
    case 'hedging':
      return "Hedging like 'maybe' and 'I think' softened your answers — trade one hedge per answer for a claim you can defend.";
    case 'short':
      return 'Your answers ran short on average — add one concrete example per answer.';
    case 'long':
      return 'Your answers ran long on average — tighten each to its strongest point.';
    case 'general':
      return 'Delivery held steady across your answers — keep it that way.';
  }
}

/** Analyze delivery across a full grill run (what the verdict consumes).
 *
 * Fillers are summed, the hedging score is averaged (rounded), the pacing
 * note is computed from the average word count, and suggestions come from
 * the most frequent suggestion themes across the run's non-blank answers
 * (frequency descending, byte-wise tie-break — deterministic). A
 * mostly-blank run never reports 'Delivery held steady'.
 */
export function analyzeDeliveryAcross(
  answers: { qid: string; text: string }[],
): DeliveryFeedback {
  const built = answers.map((a) => buildDelivery(a.text));

  if (built.every((b) => b.wordCount === 0)) {
    return {
      fillerWords: [],
      fillerTotal: 0,
      hedgingScore: 0,
      pacingNote: pacingNoteFor(0),
      suggestions: ['No answers to analyze — even a rough answer beats silence.'],
    };
  }

  const counts = new Map<string, number>();
  for (const b of built) {
    for (const f of b.feedback.fillerWords) {
      counts.set(f.word, (counts.get(f.word) ?? 0) + f.count);
    }
  }
  const fillerWords = [...counts.entries()]
    .map(([word, count]) => ({ word, count }))
    .sort((a, b) => b.count - a.count || byteCompare(a.word, b.word));
  const fillerTotal = fillerWords.reduce((sum, f) => sum + f.count, 0);

  const hedgingScore = Math.round(
    built.reduce((sum, b) => sum + b.feedback.hedgingScore, 0) / built.length,
  );

  const avgWords = Math.round(
    built.reduce((sum, b) => sum + b.wordCount, 0) / built.length,
  );
  const pacingNote = pacingNoteFor(avgWords);

  /* Most frequent suggestion themes across the run's answers
     (frequency descending, byte-wise tie-break — deterministic).
     Blank answers are excluded from the theme vote: a blank answer's
     'general' theme would otherwise dilute real signal, and a
     mostly-blank run must never report 'Delivery held steady'. */
  const nonBlank = built.filter((b) => b.wordCount > 0);
  const mostlyBlank = nonBlank.length * 2 < built.length;
  const themeCounts = new Map<SuggestionTheme, number>();
  for (const b of nonBlank) {
    for (const theme of b.themes) {
      themeCounts.set(theme, (themeCounts.get(theme) ?? 0) + 1);
    }
  }
  const topThemes = [...themeCounts.entries()]
    .sort((a, b) => b[1] - a[1] || byteCompare(a[0], b[0]))
    .slice(0, 3)
    .map(([theme]) => theme);

  const suggestions = topThemes.map((theme) =>
    theme === 'general' && mostlyBlank
      ? 'Most answers were blank — delivery coaching needs real answers to work with.'
      : aggregateSuggestionFor(theme, fillerWords[0] ?? null),
  );

  return { fillerWords, fillerTotal, hedgingScore, pacingNote, suggestions };
}

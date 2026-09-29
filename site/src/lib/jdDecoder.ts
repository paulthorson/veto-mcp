/* JD decoder: faithful TypeScript port of jd_decoder.py.
 *
 * The engine is deterministic regex + counting. This file mirrors the
 * Python module rule for rule, so pasting any posting here produces the
 * exact same numbers, quotes, and verdict as `cli.py decode-jd`.
 *
 * Fidelity notes (where JS and Python semantics differ, Python wins):
 * - _quote() snaps to word boundaries using Python's str.isspace() set,
 *   not JS's \s. See PY_SPACE_SRC.
 * - text.split() uses the same set (PY_SPLIT_RE), with empty runs dropped.
 * - str.strip() uses the same set (pyTrim), not JS's String.trim().
 * - Every regex \s is the PY_WS class: JS \s misses NEL and \x1c-\x1f
 *   and wrongly matches U+FEFF.
 * - Every regex \b is the PY_B lookaround pair: JS \b is ASCII-only even
 *   with the u flag, while Python's is Unicode-aware.
 * - \d is PY_DIGIT (\p{Nd}): Python matches Unicode decimal digits.
 * - \w is PY_WORD ([\p{L}\p{N}_]): Python matches Unicode word chars.
 * - Bullet anchoring is (?:^|(?<=\n)) with no m flag: Python's MULTILINE
 *   ^ matches after \n only, while JS multiline ^ also matches after
 *   \r, U+2028 and U+2029.
 * - density uses Python's round(x, 2): IEEE754 half-even on the exact
 *   binary value (pyRound2). The vagueness integer round can never hit
 *   exactly .5 (8*density always lands on a multiple of 0.04), so
 *   Math.round is safe there.
 * - Phrase repr uses Python's repr() for plain strings: 'phrase'.
 * - Factor sorting is stable and descending, exactly like
 *   sorted(..., reverse=True) on (has_quote, abs(impact)).
 * - jd_verdict('') returns no 'signals' key (mirrored via the optional
 *   JdVerdict.signals), never via a cast.
 */

/* Python str.isspace() character set (single characters), verified
 * exhaustively against the engine: Python's re \s for str patterns
 * matches exactly this set. Note U+FEFF is NOT in it. */
const PY_SPACE_SRC =
  '\\t\\n\\v\\f\\r \\x1c-\\x1f\\x85\\xa0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000';
const PY_SPACE_RE = new RegExp(`^[${PY_SPACE_SRC}]$`, 'u');
const PY_SPLIT_RE = new RegExp(`[${PY_SPACE_SRC}]+`, 'u');
const PY_TRIM_RE = new RegExp(`^[${PY_SPACE_SRC}]+|[${PY_SPACE_SRC}]+$`, 'gu');

/* Python re character-class equivalents for str patterns. JS \s misses
 * NEL and \x1c-\x1f (and wrongly matches U+FEFF); JS \b is ASCII-only
 * even with the u flag; JS \d is ASCII-only. Python wins everywhere. */
const PY_WS = `[${PY_SPACE_SRC}]`;
const PY_WS_Q = `${PY_WS}?`;
const PY_WS_STAR = `${PY_WS}*`;
const PY_WS_PLUS = `${PY_WS}+`;
/* Python \w for str patterns: Unicode letters/numbers + underscore.
 * Inherent skew: Python's unicodedata and browser ICU disagree on roughly
 * the newest ~9.6k assigned code points for \w. Fixing it would require
 * shipping a Unicode table to the browser, which is not worth it. This
 * only affects text containing very recently assigned Unicode characters;
 * normal job-post text is unaffected. Behavior intentionally not changed. */
const PY_WORD = '[\\p{L}\\p{N}_]'; // Python \w: Unicode letters/numbers + _
const PY_DIGIT = '\\p{Nd}'; // Python \d: Unicode decimal digits
/* Python \b for str patterns: a boundary iff exactly one side is a
 * word character. */
const PY_B = `(?:(?<!${PY_WORD})(?=${PY_WORD})|(?<=${PY_WORD})(?!${PY_WORD}))`;

function pyIsSpace(ch: string): boolean {
  return PY_SPACE_RE.test(ch);
}

/** Python's str.strip(): trim the str.isspace() set, not JS's trim set. */
function pyTrim(s: string): string {
  return s.replace(PY_TRIM_RE, '');
}

/**
 * Convert a UTF-16 code-unit index to a Unicode code-point index.
 * Python indexes strings by code point (astral characters count as one);
 * JS regex match indices are UTF-16 units. All window arithmetic mirrors
 * Python, so indices are converted before use.
 */
function utf16ToCp(text: string, i16: number): number {
  let cp = 0;
  let u16 = 0;
  while (u16 < i16) {
    const cu = text.charCodeAt(u16);
    u16 += cu >= 0xd800 && cu <= 0xdbff ? 2 : 1;
    cp += 1;
  }
  return cp;
}

/** Python's " ".join(text.split()): split on any whitespace run, drop empties. */
function pySplitJoin(text: string): string {
  return text.split(PY_SPLIT_RE).filter((s) => s.length > 0).join(' ');
}

/** Python's round(x, 2): half-even rounding of the exact double value. */
function pyRound2(x: number): number {
  const y = x * 100;
  const k = Math.trunc(y);
  const frac = Math.abs(y - k);
  let r: number;
  if (frac < 0.5) {
    r = k;
  } else if (frac > 0.5) {
    r = k + (y >= 0 ? 1 : -1);
  } else {
    r = k % 2 === 0 ? k : k + (y >= 0 ? 1 : -1);
  }
  return r / 100;
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** Python repr() of a plain phrase string: 'fast-paced'. */
function pyRepr(s: string): string {
  return `'${s}'`;
}

/* ------------------------------------------------------------------ */
/* Pattern tables                                                       */
/* ------------------------------------------------------------------ */

const SALARY_RANGE_RE = new RegExp(
  `(?:[$£€]|USD|EUR|GBP|CAD|AUD)${PY_WS_Q}(${PY_DIGIT}[${PY_DIGIT},]*(?:\\.${PY_DIGIT}+)?)` +
    `${PY_WS_Q}[kK]?${PY_WS_STAR}(?:-|–|—|${PY_B}to${PY_B})${PY_WS_STAR}(?:[$£€])?` +
    `${PY_WS_Q}(${PY_DIGIT}[${PY_DIGIT},]*(?:\\.${PY_DIGIT}+)?)${PY_WS_Q}[kK]?`,
  'u',
);
const SALARY_SINGLE_RE = new RegExp(
  `[$£€]${PY_WS_Q}${PY_DIGIT}[${PY_DIGIT},]*(?:\\.${PY_DIGIT}+)?${PY_WS_Q}[kK]?${PY_B}`,
  'u',
);
const SALARY_WORDS_RE = new RegExp(
  `${PY_B}competitive${PY_WS_PLUS}(salary|compensation|pay)${PY_B}` +
    `|${PY_B}market[ -]rate${PY_WS_PLUS}(salary|compensation|pay)${PY_B}` +
    `|${PY_B}salary${PY_WS_STAR}:?${PY_WS_STAR}(competitive|negotiable|tbd)${PY_B}`,
  'iu',
);

const EQUITY_TERMS_RE = new RegExp(
  `${PY_B}stock options?${PY_B}|${PY_B}RSUs?${PY_B}|${PY_B}ESOP${PY_B}` +
    `|${PY_B}equity${PY_B}|${PY_B}ownership stake${PY_B}`,
  'iu',
);
const EQUITY_DETAIL_RE = new RegExp(
  `${PY_B}vest(?:ing|ed|s)?${PY_B}|${PY_B}grant${PY_B}` +
    `|${PY_B}refresh(?:er)?s?${PY_B}|[$£€]${PY_WS_Q}${PY_DIGIT}|%`,
  'iu',
);

const OVERWORK_PHRASES: Record<string, string> = {
  'fast-paced':
    'Signals high urgency and shifting priorities. Ask about sprint load, on-call rotations, and how deadlines get set.',
  'fast paced':
    'Signals high urgency and shifting priorities. Ask about sprint load, on-call rotations, and how deadlines get set.',
  'wear many hats':
    "The role may span several jobs' worth of work. Ask what a typical week looks like and which responsibilities are core.",
  'always on':
    'Suggests after-hours expectations. Ask how the team protects off-hours time.',
  '24/7':
    'Round-the-clock language. Ask whether on-call or weekend coverage is part of the role.',
  'unlimited PTO':
    'Teams with unlimited PTO often take less time off than teams with a fixed allotment. Ask how many days the team actually took last year.',
  'unlimited vacation':
    'Teams with unlimited vacation often take less time off than teams with a fixed allotment. Ask how many days the team actually took last year.',
  'work hard play hard':
    'Culture framing often paired with long hours. Ask what a normal week looks like, not the highlight reel.',
  'do whatever it takes':
    'Open-ended commitment language. Ask for concrete examples of what this has meant recently.',
  'nights and weekends':
    'Explicitly names off-hours work. Ask how often it happens and whether it is compensated or comped.',
  hustle:
    'Ambition language that can mask overwork. Ask how success is measured — output, or hours.',
};

const BUZZWORDS = [
  'synergy',
  'synergies',
  'rockstar',
  'rock star',
  'ninja',
  'guru',
  'thought leader',
  'game changer',
  'game-changer',
  'paradigm',
];

/* Python: re.compile(r"^\s*(?:[-•*▪–>]|\d+[.)])\s+\S", re.MULTILINE).
 * Python's MULTILINE ^ matches at the start of the string and just after
 * \n only; JS multiline ^ also matches after \r, U+2028, U+2029, so the
 * anchor is spelled out and the m flag is dropped. */
const BULLET_RE = new RegExp(
  `(?:^|(?<=\\n))${PY_WS_STAR}(?:[-•*▪–>]|${PY_DIGIT}+[.)])${PY_WS_PLUS}[^${PY_SPACE_SRC}]`,
  'gu',
);

const GROWTH_SIGNALS: Array<[RegExp, string]> = [
  [new RegExp(`${PY_B}mentorship${PY_B}`, 'iu'), 'mentorship'],
  [new RegExp(`${PY_B}mentor(?:ing|ed|s)?${PY_B}`, 'iu'), 'mentoring'],
  [
    new RegExp(`${PY_B}learning${PY_WS_PLUS}(budget|stipend)${PY_B}`, 'iu'),
    'learning budget',
  ],
  [
    new RegExp(`${PY_B}professional development${PY_B}`, 'iu'),
    'professional development',
  ],
  [
    new RegExp(`${PY_B}career${PY_WS_PLUS}(path|growth|development)${PY_B}`, 'iu'),
    'career path',
  ],
  [
    new RegExp(
      `${PY_B}promotion${PY_WS_PLUS}(path|track|opportunit${PY_WORD}*)${PY_B}`,
      'iu',
    ),
    'promotion path',
  ],
  [
    new RegExp(`${PY_B}training${PY_WS_PLUS}budget${PY_B}`, 'iu'),
    'training budget',
  ],
  [
    new RegExp(`${PY_B}conference${PY_WS_PLUS}(budget|stipend)${PY_B}`, 'iu'),
    'conference budget',
  ],
];

const GREEN_FLAGS: Array<[RegExp, string]> = [
  [
    new RegExp(
      `${PY_B}remote(?:-first|-friendly)?${PY_B}|${PY_B}work from home${PY_B}` +
        `|${PY_B}distributed team${PY_B}`,
      'iu',
    ),
    'remote flexibility',
  ],
  [
    new RegExp(`${PY_B}flexible${PY_WS_PLUS}(hours|schedule|working)${PY_B}`, 'iu'),
    'flexible schedule',
  ],
  [
    new RegExp(
      `${PY_B}must[- ]haves?${PY_B}|${PY_B}required qualifications${PY_B}`,
      'iu',
    ),
    'must-haves listed',
  ],
  [
    new RegExp(
      `${PY_B}nice[- ]to[- ]haves?${PY_B}|${PY_B}bonus points${PY_B}`,
      'iu',
    ),
    'nice-to-haves listed',
  ],
];

/* ------------------------------------------------------------------ */
/* Types                                                                */
/* ------------------------------------------------------------------ */

export interface QuoteHit {
  match: string;
  quote: string;
}

export interface Transparency {
  score: number;
  salary_range: { low: string; high: string; raw: string; quote: string } | null;
  salary_mention: { raw: string; quote: string } | null;
  equity: { term: string; concrete: boolean; quote: string } | null;
}

export interface OverworkHit {
  phrase: string;
  quote: string;
  read: string;
}

export interface BuzzwordHit {
  buzzword: string;
  quote: string;
}

export interface Vagueness {
  score: number;
  buzzwords: BuzzwordHit[];
  buzzword_count: number;
  buzzword_density_per_100_words: number;
  responsibilities: number;
  word_count: number;
}

export interface GrowthHit {
  signal: string;
  quote: string;
}

export interface GreenFlag {
  flag: string;
  quote: string;
}

export interface DecodedJd {
  transparency: Transparency;
  overwork: OverworkHit[];
  vagueness: Vagueness;
  growth: GrowthHit[];
  green_flags: GreenFlag[];
  markdown: string;
}

export interface VerdictReason {
  impact: number;
  reason: string;
  quote: string | null;
}

export interface JdVerdict {
  verdict: 'strong' | 'mixed' | 'caution';
  score: number;
  reasons: VerdictReason[];
  /**
   * Absent on the empty-input path: the Python engine's jd_verdict('')
   * dict has no 'signals' key, and this port mirrors that shape exactly
   * (no cast). Callers that only pass non-blank text always see it.
   */
  signals?: DecodedJd;
  markdown: string;
}

/* ------------------------------------------------------------------ */
/* Helpers                                                              */
/* ------------------------------------------------------------------ */

function quote(text: string, start: number, end: number, window = 70): string {
  // Mirror Python's _quote exactly: all indexing is by code point, so
  // astral characters (emoji) count as one, like in Python. `start`/`end`
  // arrive as UTF-16 regex-match indices and are converted first.
  const cps = Array.from(text);
  let s = Math.max(0, utf16ToCp(text, start) - window);
  let e = Math.min(cps.length, utf16ToCp(text, end) + window);
  // Snap to word boundaries so the snippet reads cleanly.
  while (s > 0 && !pyIsSpace(cps[s])) {
    s -= 1;
  }
  while (e < cps.length && !pyIsSpace(cps[e - 1])) {
    e += 1;
  }
  const snippet = pySplitJoin(cps.slice(s, e).join(''));
  const prefix = s > 0 ? '… ' : '';
  const suffix = e < cps.length ? ' …' : '';
  return `${prefix}${snippet}${suffix}`;
}

function findAll(text: string, pattern: RegExp): QuoteHit[] {
  const re = new RegExp(pattern.source, pattern.flags.includes('g') ? pattern.flags : pattern.flags + 'g');
  const hits: QuoteHit[] = [];
  re.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    hits.push({ match: m[0], quote: quote(text, m.index, m.index + m[0].length) });
  }
  return hits;
}

function firstQuote(text: string, pattern: RegExp): string | null {
  const re = new RegExp(pattern.source, pattern.flags);
  const m = re.exec(text);
  return m ? quote(text, m.index, m.index + m[0].length) : null;
}

/* ------------------------------------------------------------------ */
/* Signal extractors                                                    */
/* ------------------------------------------------------------------ */

function transparency(text: string): Transparency {
  let score = 0;
  let salary_range: Transparency['salary_range'] = null;
  let salary_mention: Transparency['salary_mention'] = null;

  const m = SALARY_RANGE_RE.exec(text);
  if (m) {
    salary_range = {
      low: m[1],
      high: m[2],
      raw: pyTrim(m[0]),
      quote: quote(text, m.index, m.index + m[0].length),
    };
    score += 60;
  } else {
    const m2 = SALARY_SINGLE_RE.exec(text) ?? SALARY_WORDS_RE.exec(text);
    if (m2) {
      salary_mention = {
        raw: pyTrim(m2[0]),
        quote: quote(text, m2.index, m2.index + m2[0].length),
      };
      score += 25;
    }
  }

  let equity: Transparency['equity'] = null;
  const em = EQUITY_TERMS_RE.exec(text);
  if (em) {
    // Python slices by code point; convert the UTF-16 match index first.
    const cps = Array.from(text);
    const cpStart = utf16ToCp(text, em.index);
    const window = cps
      .slice(Math.max(0, cpStart - 80), cpStart + utf16ToCp(em[0], em[0].length) + 80)
      .join('');
    const concrete = EQUITY_DETAIL_RE.test(window);
    equity = {
      term: em[0],
      concrete,
      quote: quote(text, em.index, em.index + em[0].length),
    };
    score += concrete ? 40 : 15;
  }

  return {
    score: Math.min(100, score),
    salary_range,
    salary_mention,
    equity,
  };
}

function phraseRe(phrase: string): RegExp {
  // Python: r"\s+".join(re.escape(w) for w in phrase.split())
  return new RegExp(
    phrase.split(' ').map(escapeRegExp).join(PY_WS_PLUS),
    'iu',
  );
}

function overwork(text: string): OverworkHit[] {
  const hits: Array<OverworkHit & { _pos: number }> = [];
  const seenSpans: Array<[number, number]> = [];
  // Longest phrases first so "unlimited PTO" wins over any substring.
  const phrases = Object.keys(OVERWORK_PHRASES).sort(
    (a, b) => b.length - a.length,
  );
  for (const phrase of phrases) {
    const re = new RegExp(phraseRe(phrase).source, 'giu');
    let m: RegExpExecArray | null;
    while ((m = re.exec(text)) !== null) {
      const span: [number, number] = [m.index, m.index + m[0].length];
      if (
        seenSpans.some(
          ([s, e]) => (s <= span[0] && span[0] < e) || (s < span[1] && span[1] <= e),
        )
      ) {
        continue;
      }
      seenSpans.push(span);
      hits.push({
        phrase,
        quote: quote(text, span[0], span[1]),
        read: OVERWORK_PHRASES[phrase],
        _pos: span[0],
      });
    }
  }
  // Deterministic order: appearance in the text.
  hits.sort((a, b) => a._pos - b._pos);
  return hits.map(({ phrase, quote: q, read }) => ({ phrase, quote: q, read }));
}

function vagueness(text: string): Vagueness {
  const words = pySplitJoin(text).split(' ').filter((s) => s.length > 0).length;
  const buzzHits: BuzzwordHit[] = [];
  const seen: Array<[number, number]> = [];
  for (const word of [...BUZZWORDS].sort((a, b) => b.length - a.length)) {
    const pat = new RegExp(
      `${PY_B}${word.split(' ').map(escapeRegExp).join(PY_WS_PLUS)}s?${PY_B}`,
      'giu',
    );
    let m: RegExpExecArray | null;
    while ((m = pat.exec(text)) !== null) {
      const span: [number, number] = [m.index, m.index + m[0].length];
      if (
        seen.some(
          ([s, e]) => (s <= span[0] && span[0] < e) || (s < span[1] && span[1] <= e),
        )
      ) {
        continue;
      }
      seen.push(span);
      buzzHits.push({
        buzzword: word,
        quote: quote(text, span[0], span[1]),
      });
    }
  }
  BULLET_RE.lastIndex = 0;
  const responsibilities = (text.match(BULLET_RE) ?? []).length;
  const density = pyRound2((buzzHits.length / Math.max(words, 1)) * 100);
  const score = Math.max(0, Math.min(100, Math.round(50 + responsibilities * 6 - density * 8)));
  return {
    score,
    buzzwords: buzzHits,
    buzzword_count: buzzHits.length,
    buzzword_density_per_100_words: density,
    responsibilities,
    word_count: words,
  };
}

function growth(text: string): GrowthHit[] {
  const hits: GrowthHit[] = [];
  const seenLabels = new Set<string>();
  for (const [pattern, label] of GROWTH_SIGNALS) {
    for (const hit of findAll(text, pattern)) {
      if (seenLabels.has(label)) break;
      seenLabels.add(label);
      hits.push({ signal: label, quote: hit.quote });
      break;
    }
  }
  return hits;
}

function greenFlags(
  text: string,
  salary_range: Transparency['salary_range'],
): GreenFlag[] {
  const flags: GreenFlag[] = [];
  const seenLabels = new Set<string>();
  for (const [pattern, label] of GREEN_FLAGS) {
    const q = firstQuote(text, pattern);
    if (q && !seenLabels.has(label)) {
      seenLabels.add(label);
      flags.push({ flag: label, quote: q });
    }
  }
  if (salary_range) {
    flags.push({ flag: 'salary range disclosed', quote: salary_range.quote });
  }
  return flags;
}

/* ------------------------------------------------------------------ */
/* Public API                                                           */
/* ------------------------------------------------------------------ */

export function decodeJd(input: string | null | undefined): DecodedJd {
  const text = input || '';
  const t = transparency(text);
  const ow = overwork(text);
  const v = vagueness(text);
  const g = growth(text);
  const gf = greenFlags(text, t.salary_range);

  const lines = ['# JD decode', ''];
  lines.push(`## Transparency: ${t.score}/100`);
  if (t.salary_range) {
    lines.push(`- Salary range: ${t.salary_range.raw}`);
  } else if (t.salary_mention) {
    lines.push(`- Salary mentioned, no range: ${t.salary_mention.raw}`);
  } else {
    lines.push('- No compensation information listed');
  }
  if (t.equity) {
    const detail = t.equity.concrete ? 'concrete' : 'vague';
    lines.push(`- Equity (${detail}): ${t.equity.term}`);
  }
  lines.push('');
  lines.push(`## Overwork language: ${ow.length} flag(s)`);
  for (const hit of ow) {
    lines.push(`- ${pyRepr(hit.phrase)}: ${hit.read}`);
  }
  lines.push('');
  lines.push(
    `## Vagueness: ${v.score}/100 concrete (${v.buzzword_count} buzzwords, ${v.responsibilities} responsibilities)`,
  );
  lines.push('');
  lines.push(`## Growth signals: ${g.length}`);
  for (const gg of g) {
    lines.push(`- ${gg.signal}`);
  }
  lines.push('');
  lines.push(`## Green flags: ${gf.length}`);
  for (const f of gf) {
    lines.push(`- ${f.flag}`);
  }

  return {
    transparency: t,
    overwork: ow,
    vagueness: v,
    growth: g,
    green_flags: gf,
    markdown: lines.join('\n'),
  };
}

export function jdVerdict(input: string | null | undefined): JdVerdict {
  const text = input || '';
  if (!pyTrim(text)) {
    // Mirrors the Python engine: jd_verdict('') returns a dict with no
    // 'signals' key. Typed honestly via the optional property above.
    return {
      verdict: 'mixed',
      score: 50,
      reasons: [
        {
          impact: 0,
          reason: 'No job description text provided',
          quote: null,
        },
      ],
      markdown: '# JD verdict: mixed (50/100)\n\nNo job description text provided.',
    };
  }

  const decoded = decodeJd(text);
  const t = decoded.transparency;
  const v = decoded.vagueness;

  let score = 50;
  const factors: Array<[number, string, string | null]> = [];

  if (t.salary_range) {
    score += 25;
    factors.push([25, 'Salary range disclosed', t.salary_range.quote]);
  } else if (t.salary_mention) {
    score += 10;
    factors.push([10, 'Salary mentioned, but no range given', t.salary_mention.quote]);
  } else {
    score -= 10;
    factors.push([-10, 'No compensation information listed', null]);
  }

  if (t.equity) {
    if (t.equity.concrete) {
      score += 10;
      factors.push([10, 'Equity described concretely', t.equity.quote]);
    } else {
      score += 5;
      factors.push([5, 'Equity mentioned without details', t.equity.quote]);
    }
  }

  const overworkPenalty = Math.min(30, 8 * decoded.overwork.length);
  score -= overworkPenalty;
  for (const hit of decoded.overwork) {
    factors.push([-8, `Overwork-language flag: ${pyRepr(hit.phrase)}`, hit.quote]);
  }

  if (v.buzzword_density_per_100_words >= 3) {
    score -= 10;
    const first = v.buzzwords.length > 0 ? v.buzzwords[0].quote : null;
    factors.push([-10, 'High buzzword density, few concrete details', first]);
  } else if (v.buzzword_count === 0 && v.responsibilities >= 3) {
    score += 5;
    factors.push([5, 'Concrete responsibilities spelled out', null]);
  }

  const growthBonus = Math.min(15, 5 * decoded.growth.length);
  score += growthBonus;
  for (const gg of decoded.growth) {
    factors.push([5, `Growth signal: ${gg.signal}`, gg.quote]);
  }

  const greenBonus = Math.min(15, 5 * decoded.green_flags.length);
  score += greenBonus;
  for (const f of decoded.green_flags) {
    factors.push([5, `Green flag: ${f.flag}`, f.quote]);
  }

  score = Math.max(0, Math.min(100, score));
  const verdict: JdVerdict['verdict'] =
    score >= 70 ? 'strong' : score >= 40 ? 'mixed' : 'caution';

  // Top 3 reasons: quoted evidence first, then by absolute impact.
  // Stable sort, descending, exactly like Python's sorted(reverse=True).
  factors.sort((a, b) => {
    const aq = a[2] != null ? 1 : 0;
    const bq = b[2] != null ? 1 : 0;
    if (aq !== bq) return bq - aq;
    return Math.abs(b[0]) - Math.abs(a[0]);
  });
  const reasons: VerdictReason[] = factors
    .slice(0, 3)
    .map(([impact, reason, q]) => ({ impact, reason, quote: q }));

  const lines = [`# JD verdict: ${verdict} (${score}/100)`, ''];
  for (const r of reasons) {
    const sign = r.impact > 0 ? '+' : r.impact < 0 ? '-' : '';
    lines.push(`- [${sign}${Math.abs(r.impact)}] ${r.reason}`);
    if (r.quote) {
      lines.push(`  > ${r.quote}`);
    }
  }

  return {
    verdict,
    score,
    reasons,
    signals: decoded,
    markdown: lines.join('\n'),
  };
}

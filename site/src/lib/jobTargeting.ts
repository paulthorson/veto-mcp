/* Feature E: user-fed job targeting for the immersive grill demo.
 *
 * The user pastes a job posting (paste is primary; URL fetch is out of
 * scope). This module parses it into a JobContext, tailors the 5 grill
 * questions to the role, and drafts a fit note for the verdict.
 *
 * All functions are pure, deterministic, and never throw on bad input —
 * a pasted mess yields a best-effort JobContext, never an exception.
 * Additive by design: with no job fed in, callers fall back to the
 * default FULL_QUESTIONS text and the demo behaves exactly as today.
 */

import type { JobContext } from './chakraTypes';
import { FULL_QUESTIONS, type FullAnswer } from './demoGrill';

/* ------------------------------------------------------------------ */
/* Keyword lists                                                       */
/* ------------------------------------------------------------------ */

/** Broad requirement keywords: a line containing one of these (word
 *  boundary, case-insensitive) counts as a requirement line. */
export const KEYWORDS: string[] = [
  'years', 'experience', 'kubernetes', 'production', 'python', 'react',
  'typescript', 'javascript', 'node', 'java', 'go', 'rust', 'django',
  'flask', 'aws', 'gcp', 'azure', 'terraform', 'docker', 'kafka', 'redis',
  'postgres', 'graphql', 'microservices', 'distributed', 'scale',
  'backend', 'frontend', 'ci/cd', 'on-call', 'mentor', 'leadership',
  'agile', 'machine learning', 'sql', 'startup', 'fintech', 'eks', 'gke',
];

/** Stack subset: a requirements hit on one of these lets the 'k8s'
 *  question be re-pointed at the job's actual stack. */
export const STACK_KEYWORDS: string[] = [
  'python', 'react', 'typescript', 'javascript', 'node', 'java', 'go',
  'rust', 'django', 'flask', 'kubernetes', 'docker', 'terraform', 'aws',
  'gcp', 'azure', 'kafka', 'redis', 'postgres', 'graphql', 'microservices',
];

/** Display names for stack keywords in question text / fit notes. */
const DISPLAY_NAMES: Record<string, string> = {
  python: 'Python', react: 'React', typescript: 'TypeScript',
  javascript: 'JavaScript', node: 'Node.js', java: 'Java', go: 'Go',
  rust: 'Rust', django: 'Django', flask: 'Flask',
  kubernetes: 'Kubernetes', docker: 'Docker', terraform: 'Terraform',
  aws: 'AWS', gcp: 'GCP', azure: 'Azure', kafka: 'Kafka', redis: 'Redis',
  postgres: 'Postgres', graphql: 'GraphQL', microservices: 'Microservices',
};

const displayName = (kw: string): string =>
  DISPLAY_NAMES[kw] ?? kw.charAt(0).toUpperCase() + kw.slice(1);

/* ------------------------------------------------------------------ */
/* Parsing                                                             */
/* ------------------------------------------------------------------ */

const MAX_RAW = 2000;
const MAX_TITLE = 80;
const MAX_REQUIREMENTS = 8;

const BULLET_RE = /^\s*(?:[-*•–—]|\d+[.)])\s+(.+?)\s*$/;
const COMPANY_LABEL_RE = /company\s*:\s*(.+?)\s*$/i;
const COMPANY_AT_RE = /\bat\s+([A-Z][A-Za-z0-9&.'’\-]+(?:\s+[A-Z][A-Za-z0-9&.'’\-]+){0,3})/;
const YEARS_ASK_RE = /(\d+)\s*\+?\s*(?:years|yrs)\b/i;

const escapeRe = (s: string): string => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const keywordRe = (kw: string): RegExp => new RegExp(`\\b${escapeRe(kw)}\\b`, 'i');

/** Keyword regexes compiled once at module load (word boundary,
 *  case-insensitive) and reused by parsing and fit-note evidence checks,
 *  instead of recompiling per line. The regexes carry no 'g' flag, so
 *  reuse across .test calls is safe. */
const KEYWORD_RES: ReadonlyArray<{ kw: string; re: RegExp }> =
  KEYWORDS.map((kw) => ({ kw, re: keywordRe(kw) }));
/** Stack-keyword regexes, keyed by keyword, for fit-note evidence checks. */
const STACK_RES: ReadonlyMap<string, RegExp> =
  new Map(STACK_KEYWORDS.map((kw) => [kw, keywordRe(kw)]));

function extractCompany(lines: string[]): string {
  for (const line of lines) {
    const labeled = line.match(COMPANY_LABEL_RE);
    if (labeled && labeled[1].trim().length > 0) return labeled[1].trim();
  }
  for (const line of lines) {
    const at = line.match(COMPANY_AT_RE);
    if (at) return at[1].trim();
  }
  return 'the posting';
}

function extractRequirements(lines: string[], skipIdx: number): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  for (let i = 0; i < lines.length && out.length < MAX_REQUIREMENTS; i++) {
    if (i === skipIdx) continue;
    const line = lines[i].trim();
    if (line.length === 0) continue;
    let req: string | null = null;
    const bullet = line.match(BULLET_RE);
    if (bullet && bullet[1].trim().length > 0) {
      req = bullet[1].trim();
    } else if (line.length >= 4 && KEYWORD_RES.some(({ re }) => re.test(line))) {
      req = line;
    }
    if (req) {
      const key = req.toLowerCase();
      if (!seen.has(key)) {
        seen.add(key);
        out.push(req);
      }
    }
  }
  return out;
}

function extractRoleKeywords(text: string): string[] {
  const lower = text.toLowerCase();
  const hits: { kw: string; idx: number }[] = [];
  for (const { kw, re } of KEYWORD_RES) {
    const m = re.exec(lower);
    if (m) hits.push({ kw, idx: m.index });
  }
  hits.sort((a, b) => a.idx - b.idx || KEYWORDS.indexOf(a.kw) - KEYWORDS.indexOf(b.kw));
  return hits.map((h) => h.kw);
}

/** Deterministic extraction of a JobContext from pasted posting text.
 *  Empty/whitespace/non-string input yields a neutral JobContext
 *  (title "Pasted role", no requirements) — never throws. */
export function parseJobPosting(rawText: string): JobContext {
  try {
    const raw = typeof rawText === 'string' ? rawText : '';
    const truncated = raw.slice(0, MAX_RAW);
    const lines = truncated.split(/\r?\n/);
    const firstIdx = lines.findIndex((l) => l.trim().length > 0);
    if (firstIdx === -1) {
      return {
        title: 'Pasted role', company: 'the posting', rawText: '',
        requirements: [], roleKeywords: [], source: 'paste',
      };
    }
    const title = lines[firstIdx].trim().slice(0, MAX_TITLE);
    const company = extractCompany(lines);
    const requirements = extractRequirements(lines, firstIdx);
    const roleKeywords = extractRoleKeywords(truncated);
    return { title, company, rawText: truncated, requirements, roleKeywords, source: 'paste' };
  } catch {
    return {
      title: 'Pasted role', company: 'the posting', rawText: '',
      requirements: [], roleKeywords: [], source: 'paste',
    };
  }
}

/* ------------------------------------------------------------------ */
/* Question tailoring                                                  */
/* ------------------------------------------------------------------ */

export interface TailoredQuestion {
  qid: string;
  text: string;
}

const defaultText = (id: string): string =>
  FULL_QUESTIONS.find((q) => q.id === id)?.text ?? '';

const firstStackKeyword = (job: JobContext): string | null => {
  const stacks = new Set(STACK_KEYWORDS);
  return job.roleKeywords.find((kw) => stacks.has(kw)) ?? null;
};

const yearsAsk = (requirements: string[]): number | null => {
  for (const req of requirements) {
    const m = req.match(YEARS_ASK_RE);
    if (m) return parseInt(m[1], 10);
  }
  return null;
};

const hasRealJob = (job: JobContext): boolean =>
  job.title !== 'Pasted role' || job.company !== 'the posting' || job.requirements.length > 0;

/** The motivation question names the role and company, so it only gets
 *  tailored when the paste actually evidences a real job: an extracted
 *  company (not the 'the posting' fallback) or non-empty requirements.
 *  Junk like "n/a" keeps the FULL_QUESTIONS default text. */
const hasMotivationEvidence = (job: JobContext): boolean =>
  job.company !== 'the posting' || job.requirements.length > 0;

/** Map the grill qids (derived from FULL_QUESTIONS, in order) to
 *  job-tailored question text. Any question with no relevant requirement
 *  falls back to its FULL_QUESTIONS default text. Deterministic; null or
 *  undefined input yields all defaults — never throws. */
export function tailorQuestions(job: JobContext | null | undefined): TailoredQuestion[] {
  if (job == null) return FULL_QUESTIONS.map((q) => ({ qid: q.id, text: q.text }));
  const ids = FULL_QUESTIONS.map((q) => q.id);
  return ids.map((qid) => {
    if (!hasRealJob(job)) return { qid, text: defaultText(qid) };
    switch (qid) {
      case 'years': {
        const ask = yearsAsk(job.requirements);
        return {
          qid,
          text: ask != null
            ? `This ${job.title} role at ${job.company} asks for ${ask}+ years of experience. How many years do you have?`
            : defaultText(qid),
        };
      }
      case 'k8s': {
        const stack = firstStackKeyword(job);
        return {
          qid,
          text: stack
            ? `The posting lists ${displayName(stack)} as core to this ${job.title} role. What’s your ${displayName(stack)} experience in production?`
            : defaultText(qid),
        };
      }
      case 'motivation':
        return {
          qid,
          text: hasMotivationEvidence(job)
            ? `Why THIS ${job.title} role at ${job.company}? One honest sentence.`
            : defaultText(qid),
        };
      default:
        return { qid, text: defaultText(qid) };
    }
  });
}

/* ------------------------------------------------------------------ */
/* Fit note for the verdict                                            */
/* ------------------------------------------------------------------ */

/* The demo's quick-pick labels for the years question are bare numbers
 * ('3', '5', '8', '10+'), so the candidate's answer may be a bare number
 * or an N+ form with no "years"/"yrs" word. Accept all of them. */
const ANSWER_YEARS_RE = /(\d+)\s*\+?\s*(?:years?|yrs?)?/i;

function stackDisplayList(keywords: string[]): string {
  const names = keywords.map(displayName);
  if (names.length === 1) return names[0];
  return `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`;
}

/** 1–2 plain-English sentences assessing fit against THIS role's
 *  requirements. Deterministic; never throws — null input is treated as
 *  "no posting pasted". */
export function jobFitNote(job: JobContext | null | undefined, answers: FullAnswer[]): string {
  try {
    if (job == null || !hasRealJob(job)) {
      return 'No posting was pasted, so the verdict uses the default posting’s bar.';
    }
    const parts: string[] = [];
    const safeAnswers = Array.isArray(answers) ? answers : [];

    const ask = yearsAsk(job.requirements);
    if (ask != null) {
      const yearsAns = safeAnswers.find((a) => a.qid === 'years');
      const m = yearsAns?.text.match(ANSWER_YEARS_RE);
      const cand = m ? parseInt(m[1], 10) : null;
      if (cand != null && cand >= ask) parts.push(`Matches the posting’s ${ask}+ year ask.`);
      else if (cand != null) parts.push(`Under the posting’s ${ask}+ year ask.`);
      else parts.push(`The posting asks for ${ask}+ years; no number in the answer.`);
    }

    const stacks = new Set(STACK_KEYWORDS);
    const jobStacks = job.roleKeywords.filter((kw) => stacks.has(kw)).slice(0, 2);
    if (jobStacks.length > 0) {
      // Word-boundary matching: "JavaScript" must not evidence "Java",
      // and "40 nodes" must not evidence "Node.js".
      const answered = safeAnswers.map((a) => a.text.toLowerCase());
      const unmet = jobStacks.filter(
        (kw) => !answered.some((t) => STACK_RES.get(kw)!.test(t)),
      );
      if (unmet.length === 0) {
        parts.push(`The answers speak to the posting’s ${stackDisplayList(jobStacks)} ask.`);
      } else if (unmet.length === 1) {
        parts.push(`The posting’s ${stackDisplayList(unmet)} requirement isn’t evidenced in the answers.`);
      } else {
        parts.push(`The posting’s ${stackDisplayList(unmet)} requirements aren’t evidenced in the answers.`);
      }
    }

    if (parts.length === 0) {
      parts.push('The pasted posting had no extractable requirements, so fit is judged on the answers alone.');
    }
    return parts.slice(0, 2).join(' ');
  } catch {
    return 'Fit against the pasted posting could not be assessed from these answers.';
  }
}

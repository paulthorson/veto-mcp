/* Chakra feature G: resume-vs-job match scoring (Jobscan-style).
 *
 * Pure deterministic matching — no model calls, no randomness, no network.
 * The visitor pastes their OWN resume text (user-provided data only; the
 * scorer never invents resume content) and Veto scores it against the
 * posting keywords that feature E extracted from the fed job posting.
 *
 * Scoring: score = round(100 * matchedKeywords / roleKeywords.length).
 * Matching is case-insensitive with word boundaries, so "JavaScript"
 * does not count as "Java". Never throws: empty resume -> score 0 with a
 * "No resume text provided" gap; a posting with no keywords -> score 0
 * with a "The posting yielded no extractable keywords" gap.
 *
 * Missing keywords are the interesting output: they name the gaps the
 * grill drills the visitor on, via gapsToDrills() below.
 */
import type { JobContext, ResumeMatch } from './chakraTypes';

/** Grill question ids (see site/src/lib/demoGrill.ts). */
export type GrillQid = 'years' | 'k8s' | 'scale' | 'logistics' | 'motivation';

/** Max plain-English gap statements produced per match (panel stays short). */
const MAX_GAPS = 5;

/* Keyword -> closest grill question.
 *
 * Mapping rationale:
 *   - 'years': experience, seniority, and craft-breadth keywords. The grill
 *     opens on backend experience, so senior/staff/backend/frontend terms
 *     drill there.
 *   - 'k8s': infrastructure, containers, and cloud keywords. The grill's
 *     'k8s' question is the platform/production question, so anything about
 *     running services in the cloud drills there.
 *   - 'scale': throughput, data stores, and reliability keywords. The
 *     grill's 'scale' question asks for operating-at-scale numbers.
 *   - 'motivation': everything else (languages, frameworks, domains, soft
 *     skills). There is no dedicated language question in the grill, so a
 *     missing 'python' or 'react' is best probed via the motivation
 *     question: does the visitor care enough about this stack to sell it?
 *   - 'logistics': never a target. Work-authorization keywords do not
 *     appear in roleKeywords, so nothing maps here today.
 *
 * 'python' -> 'k8s' would be wrong (Python is not infrastructure); the rule
 * is: known keyword -> its mapped qid; unknown keyword -> 'k8s' only when it
 * looks infrastructure-ish (matches one of the infra hints), otherwise
 * 'motivation'.
 */
export const KEYWORD_TO_QID: Record<string, GrillQid> = {
  /* years: experience / seniority / craft breadth */
  years: 'years',
  experience: 'years',
  senior: 'years',
  staff: 'years',
  principal: 'years',
  lead: 'years',
  leadership: 'years',
  mentoring: 'years',
  mentor: 'years',
  backend: 'years',
  frontend: 'years',
  'full-stack': 'years',
  fullstack: 'years',
  architecture: 'years',
  /* k8s: infrastructure / platform / containers */
  kubernetes: 'k8s',
  k8s: 'k8s',
  docker: 'k8s',
  containers: 'k8s',
  containerization: 'k8s',
  eks: 'k8s',
  gke: 'k8s',
  aks: 'k8s',
  helm: 'k8s',
  terraform: 'k8s',
  ansible: 'k8s',
  cloud: 'k8s',
  aws: 'k8s',
  gcp: 'k8s',
  azure: 'k8s',
  devops: 'k8s',
  cicd: 'k8s',
  'ci/cd': 'k8s',
  infrastructure: 'k8s',
  microservices: 'k8s',
  serverless: 'k8s',
  sre: 'k8s',
  /* scale: throughput / data / reliability */
  scale: 'scale',
  kafka: 'scale',
  postgres: 'scale',
  postgresql: 'scale',
  mysql: 'scale',
  mongodb: 'scale',
  redis: 'scale',
  elasticsearch: 'scale',
  sql: 'scale',
  nosql: 'scale',
  database: 'scale',
  databases: 'scale',
  spark: 'scale',
  distributed: 'scale',
  performance: 'scale',
  monitoring: 'scale',
  observability: 'scale',
  prometheus: 'scale',
  grafana: 'scale',
  latency: 'scale',
};

/** Unknown-keyword fallback hints: a whole token matching one of these
 *  -> drill as 'k8s'. Token-matched (not substring) so 'props' does not
 *  trip on 'ops'. */
const INFRA_HINTS = [
  'infra',
  'infrastructure',
  'cloud',
  'devops',
  'ops',
  'deploy',
  'deployment',
  'container',
  'orchestration',
  'serverless',
  'sre',
  'platform',
];

/* Split a keyword into whole word tokens: 'fullstack developer' ->
 * ['fullstack', 'developer']; 'ci/cd' -> ['ci', 'cd']. Token matching
 * (not raw substrings) keeps short keywords honest: 'go' must not match
 * inside 'mongodb', 'c' must not match inside 'experience'. */
function tokensOf(keyword: string): string[] {
  return keyword.toLowerCase().split(/[^a-z0-9+#]+/).filter((t) => t.length > 0);
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/* Word-boundary match: "JavaScript" must not count as "Java". Keywords that
 * start/end with a non-word character (e.g. "ci/cd") match literally. */
function containsKeyword(text: string, keyword: string): boolean {
  const kw = keyword.trim();
  if (kw.length === 0) return false;
  const left = /^\w/.test(kw) ? '\\b' : '';
  const right = /\w$/.test(kw) ? '\\b' : '';
  return new RegExp(left + escapeRegExp(kw) + right, 'i').test(text);
}

/** Closest grill question for a posting keyword (exported for consumers/tests).
 *
 * Resolution order: exact map hit -> whole-token match against map keys
 * (deterministic: map insertion order) -> long-key substring match (the
 * keyword contains a map key of 4+ chars, e.g. 'cloudformation' holds
 * 'cloud') -> infra-hint whole-token match -> 'motivation'.
 * The 4-char floor on substring matching keeps short keywords honest:
 * 'go' must not trip on 'mongodb', 'c' must not trip on 'experience'.
 * Hints stay whole-token so 'props' does not trip on 'ops'. */
export function resolveQid(keyword: string): GrillQid {
  const kw = keyword.toLowerCase().trim();
  if (kw.length === 0) return 'motivation';
  const direct = KEYWORD_TO_QID[kw];
  if (direct) return direct;
  const tokens = new Set(tokensOf(kw));
  // Whole-token match against the known map, in a fixed (insertion) order
  // so the result is deterministic.
  for (const [key, qid] of Object.entries(KEYWORD_TO_QID)) {
    if (tokens.has(key.toLowerCase())) return qid;
  }
  // Compound fallback: the keyword contains a substantive map key.
  for (const [key, qid] of Object.entries(KEYWORD_TO_QID)) {
    if (key.length >= 4 && kw.includes(key.toLowerCase())) return qid;
  }
  // Unknown keyword: infra-ish -> 'k8s', everything else -> 'motivation'.
  if (INFRA_HINTS.some((hint) => tokens.has(hint))) return 'k8s';
  return 'motivation';
}

/** Score a pasted resume against the fed posting's keywords. Never throws.
 *  Keywords are deduped (case-insensitive) so a repeated keyword cannot
 *  produce duplicate gap statements or duplicate panel chips. */
export function scoreResumeMatch(resumeText: string, job: JobContext): ResumeMatch {
  const resume = (resumeText ?? '').toLowerCase();
  const seen = new Set<string>();
  const keywords: string[] = [];
  for (const raw of job?.roleKeywords ?? []) {
    const k = (raw ?? '').toLowerCase().trim();
    if (k.length > 0 && !seen.has(k)) {
      seen.add(k);
      keywords.push(k);
    }
  }

  if (resume.trim().length === 0) {
    return {
      score: 0,
      matchedKeywords: [],
      missingKeywords: [],
      gaps: ['No resume text provided'],
    };
  }
  if (keywords.length === 0) {
    return {
      score: 0,
      matchedKeywords: [],
      missingKeywords: [],
      gaps: ['The posting yielded no extractable keywords'],
    };
  }

  const matchedKeywords = keywords.filter((k) => containsKeyword(resume, k));
  const missingKeywords = keywords.filter((k) => !containsKeyword(resume, k));
  const score = Math.round((100 * matchedKeywords.length) / keywords.length);
  const gaps = missingKeywords
    .slice(0, MAX_GAPS)
    .map((k) => `Resume doesn't mention ${k}; the posting asks for it.`);

  return { score, matchedKeywords, missingKeywords, gaps };
}

/* Missing keywords -> the grill drill topics that cover them.
 * Deduped, in missing-keyword order. This is the consumption seam:
 * feature E feeds it into tailored questions, feature A into the
 * reasoning narrative (see INTEGRATION-G.md). */
export function gapsToDrills(match: ResumeMatch): string[] {
  const drills: string[] = [];
  const seen = new Set<string>();
  for (const kw of match?.missingKeywords ?? []) {
    const qid = resolveQid(kw);
    if (!seen.has(qid)) {
      seen.add(qid);
      drills.push(qid);
    }
  }
  return drills;
}

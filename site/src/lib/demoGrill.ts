/* Immersive demo grill logic: question bank, deterministic answer classification,
   value extraction, scoring, and verdict. Pure functions — no randomness, no
   model calls — so E2E tests can drive exact paths. Imported by pages/DemoPage.
   QA contract lives in the comment blocks below; keep it in sync with tests.
*/

export type AnswerClass = 'specific' | 'vague';
export type Level = 'friendly' | 'standard' | 'brutal';
export type QType = 'quantify' | 'gap' | 'logistics' | 'motivation';

/* ------------------------------------------------------------------ */
/* Answer classification — rule-based and fully deterministic. No      */
/* randomness, no model calls, so E2E tests can drive exact paths.     */
/*                                                                     */
/* QA CONTRACT (do not reorder without updating E2E):                  */
/*  1. Blank / whitespace-only            -> 'vague'                   */
/*  2. Quick-pick chosen                  -> the pick's recorded class  */
/*     (exact label match against FULL_QUESTIONS picks)                */
/*  3. Contains a digit AND a domain      -> 'specific'                */
/*     context word (year/yr, req/request/rps/qps, million/billion/    */
/*     thousand, node/cluster/pod/container/instance/server/machine,   */
/*     traffic/latency/percent, production/eks/gke/aks/helm/terraform/  */
/*     on-call, citizen/visa/green card, hybrid/office/relocate/nyc/    */
/*     new york, fintech/payment, user, day/week/month, salary/comp/   */
/*     dollar). The number must mean something — "5 years", "100M      */
/*     req/day", "40 nodes" are specific; "I have 2 dogs" is not.       */
/*  4. Contains a hedge word/phrase       -> 'vague'                   */
/*     (whole-word / whole-phrase match: some, kinda, familiar,         */
/*     exposure, decent, around, touched, basics, little, "sort of",    */
/*     "a bit", "-ish" — "bitcoin" is NOT a hedge). Runs AFTER rule 3,  */
/*     so "around 5 years" is specific (the number wins).              */
/*  5. A bare number means nothing        -> 'vague'                   */
/*     (a digit with no rule-3 domain word: "I have 2 dogs", "5").      */
/*     Only the digit+domain-word pair (rule 3) earns specific for     */
/*     number-bearing answers. Otherwise:                               */
/*       >= 12 chars                      -> 'specific'                */
/*       < 12 chars                       -> 'vague'                   */
/*                                                                     */
/* Deterministic E2E paths: use quick-picks for fixed outcomes, or     */
/* free text engineered against these rules: "some stuff" -> vague,    */
/* "9 years" -> specific, "idk" -> vague, "I have 2 dogs" -> vague,     */
/* "5" -> vague, "I ran a bitcoin startup" -> specific, "around 5       */
/* years" -> specific. The ONLY non-deterministic value in the whole   */
/* flow is the ledger timestamp (wall clock).                          */
/* ------------------------------------------------------------------ */

const CONTEXT_RE =
  /(year|yr|req|request|rps|qps|million|billion|thousand|node|cluster|pod|container|instance|server|machine|traffic|latency|percent|production|eks|gke|aks|helm|terraform|on-?call|citizen|visa|green card|hybrid|office|relocate|nyc|new york|fintech|payment|user|day|week|month|salary|comp|dollar)/;

const HEDGE_RE =
  /\b(some|kinda|familiar|exposure|decent|around|touched|basics|little|sort of|a bit|-ish)\b/;

export interface GrillPick {
  label: string;
  cls: AnswerClass;
}

export interface GrillQuestion {
  id: 'years' | 'k8s' | 'scale' | 'logistics' | 'motivation';
  type: QType;
  text: string;
  placeholder: string;
  picks: GrillPick[];
  /** Follow-up when the first answer classifies vague (standard). */
  followup: string;
  /** Sharper follow-up, brutal level, first push-back. */
  followupBrutal: string;
  /** Brutal level, final push-back before the answer is recorded vague. */
  followupBrutalLast: string;
}

/* The real grill's question types: quantify, gap, logistics, and       */
/* motivation ALWAYS last (see docs/grill.md). Up to 5 questions.       */
export const FULL_QUESTIONS: GrillQuestion[] = [
  {
    id: 'years',
    type: 'quantify',
    text: 'How many years of backend experience do you have?',
    placeholder: 'e.g. 9 years',
    picks: [
      { label: '3', cls: 'specific' },
      { label: '5', cls: 'specific' },
      { label: '8', cls: 'specific' },
      { label: '10+', cls: 'specific' },
    ],
    followup: 'Give me a number. Years of backend experience?',
    followupBrutal: "Give me a number. Not a range, not 'several'. A number.",
    followupBrutalLast: 'Last push: how many years? Dodge this and I file it vague and move on.',
  },
  {
    id: 'k8s',
    type: 'gap',
    text: 'The posting needs Kubernetes in production. What’s your Kubernetes experience?',
    placeholder: 'e.g. ran EKS daily for 3 years',
    picks: [
      { label: 'Production daily', cls: 'specific' },
      { label: 'Homelab only', cls: 'specific' },
      { label: 'None', cls: 'specific' },
    ],
    followup: 'That’s vague. Production, homelab, or none — which is it?',
    followupBrutal: 'Dodging. Production Kubernetes: yes or no?',
    followupBrutalLast: 'Final answer on Kubernetes. Production, homelab, or none?',
  },
  {
    id: 'scale',
    type: 'quantify',
    text: 'What’s the largest scale you’ve operated at? Rough numbers — requests per day, cluster size, whatever you have.',
    placeholder: 'e.g. ~50M req/day across 40 nodes',
    picks: [
      { label: '100M+ req/day', cls: 'specific' },
      { label: '10M req/day', cls: 'specific' },
      { label: '~10k req/day', cls: 'specific' },
      { label: 'Don’t track that', cls: 'vague' },
    ],
    followup: 'Give me a number — requests per day, node count, anything.',
    followupBrutal: 'Numbers. Now. Requests per day or cluster size — pick one.',
    followupBrutalLast: 'One number, or your scale claim is filed as unverified.',
  },
  {
    id: 'logistics',
    type: 'logistics',
    text: 'US work authorization? And can you do 3 days a week in the NYC office?',
    placeholder: 'e.g. US citizen, hybrid is fine',
    picks: [
      { label: 'US authorized + NYC hybrid ok', cls: 'specific' },
      { label: 'US authorized, remote only', cls: 'specific' },
      { label: 'No US authorization', cls: 'specific' },
    ],
    followup: 'Need a straight answer: US work authorization, yes or no?',
    followupBrutal: 'Yes or no. Work authorization.',
    followupBrutalLast: 'Authorization. Yes or no. Nothing else counts as an answer.',
  },
  {
    id: 'motivation',
    type: 'motivation',
    text: 'Why this role, at this fintech? One honest sentence.',
    placeholder: 'the real reason, not the pitch',
    picks: [
      { label: 'The payments-scale problem is exactly my thing', cls: 'specific' },
      { label: 'Honestly: the comp band', cls: 'specific' },
    ],
    followup: 'That’s a pitch, not a reason. What actually draws you to this one?',
    followupBrutal: 'Wrong answer. Why THIS job, not any job?',
    followupBrutalLast: 'Last try: one honest sentence about this specific role.',
  },
];

export function classifyAnswer(qid: string, raw: string): AnswerClass {
  const text = raw.trim();
  if (text.length === 0) return 'vague';
  const q = FULL_QUESTIONS.find((x) => x.id === qid);
  const pick = q?.picks.find((p) => p.label === text);
  if (pick) return pick.cls;
  const t = text.toLowerCase();
  const hasDigit = /\d/.test(t);
  if (hasDigit && CONTEXT_RE.test(t)) return 'specific';
  if (HEDGE_RE.test(t)) return 'vague';
  /* A bare number means nothing: only rule 3 (digit + domain-context
     word) earns specific for number-bearing answers. "I have 2 dogs"
     and "5" are vague — see QA contract rule 5. */
  if (hasDigit) return 'vague';
  return text.length >= 12 ? 'specific' : 'vague';
}

/* ---------------- Value extraction (deterministic) ---------------- */

export function parseYears(raw: string): number | null {
  const m = raw.replace(/,/g, '').match(/\d+/);
  return m ? parseInt(m[0], 10) : null;
}

export type K8sStance = 'prod' | 'home' | 'none' | 'unclear';

/* 'none' is checked before 'prod': "no production experience" is none. */
export function parseK8s(raw: string): K8sStance {
  const t = raw.toLowerCase();
  if (/\bnone\b|\bno\b|never|haven't|have not|not much|not really|zero/.test(t)) return 'none';
  if (/production|\bprod\b|daily|eks|gke|aks|on-?call|ran /.test(t)) return 'prod';
  if (/homelab|personal|side project|learning|stud/.test(t)) return 'home';
  return 'unclear';
}

export interface Logistics {
  auth: 'yes' | 'no' | 'unclear';
  nyc: 'yes' | 'no' | 'unclear';
}

/* QA CONTRACT — parseLogistics (do not reorder without updating E2E):
   auth: explicit eligibility is checked FIRST, so "No sponsorship
   needed, US citizen" -> yes (it contains "sponsor" but is not a
   denial). Yes: "no sponsorship needed|required", "(don't|do not|
   won't) need (a )?(visa|sponsorship)", citizen, green card, permanent resident,
   "have a visa", leading "yes". Then explicit denials: "not authorized",
   "not currently authorized", "no [us] authorization", "no auth", "need
   (a )?visa", "no visa", "(don't|do not) have (a )?visa", "(don't|do not)
   have authorization", "no, i don't have authorization". The yes-branch
   "have a visa" uses a negative lookbehind so a negated "don't/do not
   have a visa" is NOT read as eligibility — it falls through to the
   denial branch instead. Then bare "authorized" -> yes (only when no
   negated form matched). Then bare "sponsor" -> no. Else unclear.
   nyc: no-patterns are checked BEFORE yes-patterns, so "can't
   relocate" -> no even though it contains "relocate". No: "remote
   only", "can't/cannot relocate", "no relocation", "won't relocate",
   "not moving", "no move". Yes: hybrid, in-office, relocate, nyc,
   "new york", on-site, commute. Else unclear.
   Deterministic E2E pairs:
   "No sponsorship needed, US citizen"     -> {auth:'yes', nyc:'unclear'}
   "US citizen, no sponsorship required"   -> {auth:'yes', nyc:'unclear'}
   "I need sponsorship"                    -> {auth:'no',  nyc:'unclear'}
   "not authorized"                        -> {auth:'no',  nyc:'unclear'}
   "not currently authorized"              -> {auth:'no',  nyc:'unclear'}
   "I have no visa"                        -> {auth:'no',  nyc:'unclear'}
   "No, I don't have authorization"        -> {auth:'no',  nyc:'unclear'}
   "I do not have a visa"                  -> {auth:'no',  nyc:'unclear'}
   "can't relocate"                        -> {auth:'unclear', nyc:'no'}
   "happy to relocate to NYC"              -> {auth:'unclear', nyc:'yes'}
   pick "US authorized + NYC hybrid ok"     -> {auth:'yes', nyc:'yes'}
   pick "US authorized, remote only"        -> {auth:'yes', nyc:'no'}
   pick "No US authorization"              -> {auth:'no',  nyc:'unclear'} */
export function parseLogistics(raw: string): Logistics {
  const t = raw.toLowerCase();
  let auth: Logistics['auth'] = 'unclear';
  const authYes =
    /no sponsorship (needed|required)|(don't|do not|won't) need (a )?(visa|sponsorship)|citizen|green card|permanent resident|(?<!don't |do not |won't |no )have a visa\b|^yes\b/;
  const authNo = /\bnot authorized\b|no( us)? authorization\b|no auth\b|need (a )?visa|\bno visa\b|(don't|do not) have (a )?visa|(don't|do not) have authorization|no,? i don't have authorization|not (currently )?authorized/;
  if (authYes.test(t)) auth = 'yes';
  else if (authNo.test(t)) auth = 'no';
  else if (/\bauthorized\b/.test(t)) auth = 'yes';
  else if (/\bsponsor/.test(t)) auth = 'no';
  let nyc: Logistics['nyc'] = 'unclear';
  const nycNo = /remote only|can't relocate|cannot relocate|no relocation|won't relocate|not moving|no move/;
  const nycYes = /hybrid|in.?office|relocate|nyc|new york|on-?site|commute/;
  if (nycNo.test(t)) nyc = 'no';
  else if (nycYes.test(t)) nyc = 'yes';
  return { auth, nyc };
}

/* ---------------- Scoring + verdict (deterministic) ---------------- */

export interface FullAnswer {
  qid: string;
  text: string;
  cls: AnswerClass;
}

export interface Factor {
  label: string;
  pts: number;
  max: number;
  note: string;
}

export interface FullResult {
  level: 'standard' | 'brutal';
  score: number;
  bar: number;
  factors: Factor[];
  verified: number;
  unverified: number;
  checks: { ok: boolean; text: string }[];
  flags: string[];
  penalty: number;
  hardVeto: string | null;
  pass: boolean;
  reason: string;
  tailoringBefore: string;
  tailoringAfter: string;
  years: number | null;
  k8s: K8sStance;
}

const Q_TOPICS: Record<string, string> = {
  years: 'years of experience',
  k8s: 'Kubernetes',
  scale: 'scale numbers',
  logistics: 'work authorization',
  motivation: 'motivation',
};

/* QA CONTRACT: scoring is a pure function of (level, answers).
   - Experience (30): 8+ yrs -> 30, 6-7 -> 18, anything less or no
     number -> 0. No number, or under 8, is a HARD veto (not applying).
   - Skill coverage (30): production k8s -> 30, homelab -> 12,
     unclear -> 10, none -> 0. In brutal, none is a HARD veto.
   - Logistics (20): auth yes + NYC hybrid -> 20, auth yes -> 12,
     auth unclear -> 8, auth no -> 0. No authorization is a HARD veto.
   - Answer clarity (20): 4 points per specific answer (5 questions).
   - Brutal penalty: -5 per honesty cross-check flag (at most 2 can
     co-occur, so the penalty tops out at -10 with no explicit cap).
   - Pass bars: standard >= 55, brutal >= 75. Below the bar -> VETOED,
     weakest factor named in the reason.
   Hard vetoes beat score vetoes. Pass is reachable in both levels:
   all-strong answers score 100. */
export function computeFullResult(
  level: 'standard' | 'brutal',
  answers: FullAnswer[],
): FullResult {
  const byId = (id: string): FullAnswer => answers.find((a) => a.qid === id) ?? {
    qid: id, text: '(no answer)', cls: 'vague',
  };
  const yearsA = byId('years');
  const k8sA = byId('k8s');
  const scaleA = byId('scale');
  const logA = byId('logistics');
  const motA = byId('motivation');

  const years = parseYears(yearsA.text);
  const k8s = parseK8s(k8sA.text);
  const { auth, nyc } = parseLogistics(logA.text);

  const verified = answers.filter((a) => a.cls === 'specific').length;
  const unverified = answers.length - verified;

  const snippet = (s: string, n: number): string =>
    s.length > n ? `${s.slice(0, n)}…` : s;

  /* Experience */
  let expPts = 0;
  let expNote = 'no number given';
  if (years != null) {
    if (years >= 8) { expPts = 30; expNote = `${years} yrs reported`; }
    else if (years >= 6) { expPts = 18; expNote = `${years} yrs reported`; }
    else { expPts = 0; expNote = `${years} yrs reported`; }
  }

  /* Skill coverage */
  const k8sPts: Record<K8sStance, number> = { prod: 30, home: 12, unclear: 10, none: 0 };
  const k8sNote: Record<K8sStance, string> = {
    prod: 'production, kept',
    home: 'homelab only — gap noted',
    unclear: 'unclear — gap noted',
    none: 'none — gap noted',
  };

  /* Logistics */
  let logPts = 0;
  let logNote = 'authorization unclear';
  if (auth === 'no') { logPts = 0; logNote = 'no US authorization'; }
  else if (auth === 'yes' && nyc === 'yes') { logPts = 20; logNote = 'US authorized, hybrid NYC ok'; }
  else if (auth === 'yes') { logPts = 12; logNote = nyc === 'no' ? 'US authorized, remote only' : 'US authorized, NYC unclear'; }
  else { logPts = 8; logNote = 'authorization unclear'; }

  /* Clarity */
  const clarityPts = Math.round((20 * verified) / 5);

  const factors: Factor[] = [
    { label: 'Experience match', pts: expPts, max: 30, note: expNote },
    { label: 'Skill coverage', pts: k8sPts[k8s], max: 30, note: k8sNote[k8s] },
    { label: 'Logistics', pts: logPts, max: 20, note: logNote },
    { label: 'Answer clarity', pts: clarityPts, max: 20, note: `${verified}/5 specific` },
  ];

  /* Honesty check lines + cross-check flags */
  const checks = answers.map((a, i) => ({
    ok: a.cls === 'specific',
    text: a.cls === 'specific'
      ? `+ answer ${i + 1} (${Q_TOPICS[a.qid] ?? a.qid}): “${snippet(a.text, 40)}” — specific, kept`
      : `X answer ${i + 1} (${Q_TOPICS[a.qid] ?? a.qid}): vague — flagged unverified`,
  }));
  const flags: string[] = [];
  answers
    .filter((a) => a.cls === 'vague')
    .forEach((a) => flags.push(`X unverified: ${Q_TOPICS[a.qid] ?? a.qid} — no usable details given`));
  const scaleVague = scaleA.cls === 'vague';
  if (years != null && years >= 8 && k8s === 'none')
    flags.push('X cross-check: 8+ yrs backend, zero Kubernetes — claim under review');
  if (k8s === 'prod' && scaleVague)
    flags.push('X cross-check: claims production Kubernetes, gave no scale numbers — unverified');
  if (years != null && years >= 8 && scaleVague && k8s !== 'prod')
    flags.push('X cross-check: big-years claim, no scale numbers — unverified');

  const penalty = level === 'brutal' ? flags.filter((f) => f.startsWith('X cross-check')).length * 5 : 0;
  const score = Math.max(0, Math.min(100, factors.reduce((s, f) => s + f.pts, 0) - penalty));
  const bar = level === 'brutal' ? 75 : 55;

  /* Hard vetoes (beat the score) */
  let hardVeto: string | null = null;
  if (years == null)
    hardVeto = 'needs 8+ yrs backend, you never gave a number. Not applying.';
  else if (years < 8)
    hardVeto = `needs 8+ yrs backend, you reported ${years}. Not applying.`;
  else if (auth === 'no')
    hardVeto = 'requires US work authorization. Not applying.';
  else if (level === 'brutal' && k8s === 'none')
    hardVeto = 'requires production Kubernetes experience. You have none. Not applying.';

  const pass = hardVeto == null && score >= bar;
  let reason = '';
  if (hardVeto) reason = hardVeto;
  else if (!pass) {
    const weakest = [...factors].sort((a, b) => a.pts / a.max - b.pts / b.max)[0];
    reason = `score ${score}/100 — the bar is ${bar}. Weakest factor: ${weakest.label} (${weakest.pts}/${weakest.max}).`;
  }

  /* Tailoring preview: what the pipeline would do with these answers. */
  const tailoringBefore = 'Experienced backend engineer with Kubernetes skills.';
  const scaleSnippet = scaleA.cls === 'specific' ? snippet(scaleA.text, 48) : null;
  const motSnippet =
    motA.cls === 'specific' && motA.text !== '(no answer)' ? snippet(motA.text, 64) : null;
  const bits: string[] = [
    years != null ? `${years} yrs backend experience` : 'backend experience (years unverified)',
    k8s === 'prod'
      ? 'ran Kubernetes in production daily'
      : k8s === 'home'
        ? 'Kubernetes: homelab only (gap noted)'
        : k8s === 'none'
          ? 'no Kubernetes (gap noted)'
          : 'Kubernetes experience unclear (gap noted)',
    scaleSnippet ? `scale: ${scaleSnippet}` : 'scale unverified',
    auth === 'yes'
      ? `US authorized${nyc === 'yes' ? ', hybrid NYC ok' : nyc === 'no' ? ', remote only' : ''}`
      : auth === 'no'
        ? 'no US authorization'
        : 'authorization unclear',
  ];
  if (motSnippet) bits.push(`why this role: “${motSnippet}”`);

  return {
    level,
    score,
    bar,
    factors,
    verified,
    unverified,
    checks,
    flags,
    penalty,
    hardVeto,
    pass,
    reason,
    tailoringBefore,
    tailoringAfter: `${bits.join('. ')}.`,
    years,
    k8s,
  };
}

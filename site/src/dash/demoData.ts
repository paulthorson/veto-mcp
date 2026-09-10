/* Seeded demo dataset: two snapshots 7 days apart so the delta engine
   has real movement to report. Timestamps are relative to load time, so
   the demo never goes stale. Replace by storing JSON under VETO_DASH_KEY
   in localStorage (see types.ts). */
import type { Application, DashboardData, StageEvent, WatchHit } from './types';

const H = 3_600_000;
const D = 24 * H;

function ev(stage: StageEvent['stage'], daysAgo: number, note?: string): StageEvent {
  return { stage, at: new Date(Date.now() - daysAgo * D).toISOString(), note };
}

interface Seed {
  job_id: string;
  title: string;
  company: string;
  board: string;
  salary?: string;
  hist: [StageEvent['stage'], number, string?][];
  snapshot?: { salary?: string; requirements?: string[] };
}

/* Full current-week histories. */
const SEEDS: Seed[] = [
  { job_id: 'gh:001', title: 'Staff Backend Engineer', company: 'FintechCo', board: 'Greenhouse', salary: '$210k–$250k',
    hist: [['found', 20], ['grilled', 19], ['applied', 18], ['interviewing', 6, 'recruiter screen moved to hiring manager']],
    snapshot: { salary: '$210k–$250k', requirements: ['8+ yrs backend', 'k8s prod'] } },
  { job_id: 'le:002', title: 'Senior Platform Engineer', company: 'Datawise', board: 'Lever', salary: '$185k–$215k',
    hist: [['found', 22], ['grilled', 21], ['applied', 20], ['interviewing', 9], ['interviewing', 3, 'onsite scheduled']],
    snapshot: { salary: '$185k–$215k', requirements: ['5+ yrs platform', 'terraform'] } },
  { job_id: 'as:003', title: 'Backend Engineer II', company: 'Shipfast', board: 'Ashby', salary: '$160k–$185k',
    hist: [['found', 16], ['grilled', 15], ['applied', 14], ['offer', 1, 'verbal offer, written pending']],
    snapshot: { salary: '$160k–$185k', requirements: ['3+ yrs backend'] } },
  { job_id: 'gh:004', title: 'Engineering Manager', company: 'BigCorp', board: 'Greenhouse', salary: '$230k–$270k',
    hist: [['found', 25], ['grilled', 24], ['vetoed', 24, 'no prior management experience: refused']],
    snapshot: { salary: '$230k–$270k', requirements: ['2+ yrs managing'] } },
  { job_id: 'le:005', title: 'Staff SRE', company: 'Cloudnine', board: 'Lever', salary: '$200k–$240k',
    hist: [['found', 18], ['grilled', 17], ['applied', 16], ['rejected', 2, 'auto-rejection, no interview']],
    snapshot: { salary: '$200k–$240k', requirements: ['oncall exp'] } },
  { job_id: 'wd:006', title: 'Senior Backend Engineer', company: 'Healthtech', board: 'Workday', salary: '$175k–$205k',
    hist: [['found', 30], ['grilled', 29], ['applied', 28]],
    snapshot: { salary: '$175k–$205k', requirements: ['python', 'postgres'] } },
  { job_id: 'gh:007', title: 'Principal Engineer', company: 'Moonshot', board: 'Greenhouse', salary: '$260k–$300k',
    hist: [['found', 12], ['grilled', 11], ['vetoed', 11, 'staff-level scope mismatch: refused']],
    snapshot: { salary: '$260k–$300k', requirements: ['10+ yrs'] } },
  { job_id: 'as:008', title: 'Backend Engineer', company: 'FintechCo', board: 'Ashby', salary: '$145k–$175k',
    hist: [['found', 10], ['grilled', 9], ['applied', 8]],
    snapshot: { salary: '$145k–$175k', requirements: ['3+ yrs backend', 'fintech exp'] } },
  { job_id: 'le:009', title: 'DevOps Engineer', company: 'Datawise', board: 'Lever', salary: '$150k–$180k',
    hist: [['found', 9], ['grilled', 8], ['applied', 7], ['ghosted', 7, 'no response after 14d']],
    snapshot: { salary: '$150k–$180k', requirements: ['k8s'] } },
  { job_id: 'gh:010', title: 'Senior Backend Engineer', company: 'LogisticsCo', board: 'Greenhouse', salary: '$180k–$210k',
    hist: [['found', 6], ['grilled', 5], ['applied', 4]],
    snapshot: { salary: '$180k–$210k', requirements: ['go', 'aws'] } },
  { job_id: 'as:011', title: 'Platform Engineer', company: 'Shipfast', board: 'Ashby', salary: '$165k–$190k',
    hist: [['found', 5], ['grilled', 4], ['vetoed', 4, 'hybrid 5d onsite: refused']],
    snapshot: { salary: '$165k–$190k', requirements: ['onsite'] } },
  { job_id: 'le:012', title: 'Backend Engineer III', company: 'Cloudnine', board: 'Lever', salary: '$170k–$195k',
    hist: [['found', 4], ['grilled', 3], ['applied', 2]],
    snapshot: { salary: '$170k–$195k', requirements: ['python'] } },
  { job_id: 'gh:013', title: 'Staff Backend Engineer', company: 'AI Startup', board: 'Greenhouse', salary: '$220k–$260k',
    hist: [['found', 3], ['grilled', 2], ['applied', 1]],
    snapshot: { salary: '$220k–$260k', requirements: ['llm exp'] } },
  { job_id: 'wd:014', title: 'Senior SRE', company: 'BankCo', board: 'Workday', salary: '$170k–$200k',
    hist: [['found', 2], ['grilled', 1], ['applied', 0.4]],
    snapshot: { salary: '$170k–$200k', requirements: ['sre'] } },
];

const WATCHES: { watch: string; job_id: string; title: string; company: string; board: string; daysAgo: number }[] = [
  { watch: 'staff-backend-nyc', job_id: 'gh:020', title: 'Staff Backend Engineer', company: 'PaymentsCo', board: 'Greenhouse', daysAgo: 1.2 },
  { watch: 'staff-backend-nyc', job_id: 'le:021', title: 'Senior Backend Engineer', company: 'InfraCo', board: 'Lever', daysAgo: 0.5 },
  { watch: 'platform-remote', job_id: 'as:022', title: 'Platform Engineer', company: 'RemoteFirst', board: 'Ashby', daysAgo: 3 },
  { watch: 'platform-remote', job_id: 'gh:023', title: 'SRE II', company: 'OldWatch', board: 'Greenhouse', daysAgo: 9 },
];

function toApp(s: Seed, cutoffDays: number): Application | null {
  const hist = s.hist.filter(([, d]) => d >= cutoffDays);
  if (!hist.length) return null;
  const stage = hist[hist.length - 1][0];
  const applied = hist.find(([st]) => st === 'applied');
  // as:008's posting was edited during the week: salary cut + new requirement.
  const isEdited = s.job_id === 'as:008';
  const snapshot =
    isEdited && cutoffDays > 0
      ? { salary: '$150k–$175k', requirements: ['3+ yrs backend'] } // old
      : isEdited
        ? { salary: '$145k–$175k', requirements: ['3+ yrs backend', 'fintech exp'] } // new
        : s.snapshot;
  return {
    job_id: s.job_id,
    title: s.title,
    company: s.company,
    board: s.board,
    salary: s.salary,
    stage,
    applied_at: applied ? new Date(Date.now() - applied[1] * D).toISOString() : undefined,
    stage_history: hist.map(([st, d, note]) => ev(st, d, note)),
    posting_snapshot: snapshot,
  };
}

export function loadDashboardData(): DashboardData {
  const now = new Date();
  const applications = SEEDS.map((s) => toApp(s, 0)).filter((a): a is Application => !!a);
  const prev_applications = SEEDS.map((s) => toApp(s, 7)).filter((a): a is Application => !!a);
  const watch_hits: WatchHit[] = WATCHES.map((w) => ({
    watch: w.watch,
    job_id: w.job_id,
    title: w.title,
    company: w.company,
    board: w.board,
    first_seen: new Date(now.getTime() - w.daysAgo * D).toISOString(),
  }));
  return {
    generated_at: now.toISOString(),
    prev_snapshot_at: new Date(now.getTime() - 7 * D).toISOString(),
    applications,
    prev_applications,
    watch_hits,
  };
}

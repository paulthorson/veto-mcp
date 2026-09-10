/* Delta detection: diff two snapshots of the application lifecycle and
   surface what changed. Pure functions. No I/O, trivially testable. */
import type {
  Application,
  BoardStat,
  DashboardData,
  Delta,
  Kpis,
  Stage,
} from './types';

const DAY_MS = 86_400_000;
const STALE_DAYS = 14;

const TERMINAL: Stage[] = ['offer', 'rejected', 'withdrawn', 'vetoed', 'ghosted'];

function daysBetween(a: string, b: string): number {
  return (
    (new Date(b).getTime() - new Date(a).getTime()) / DAY_MS
  );
}

function lastChange(app: Application): string | null {
  const h = app.stage_history;
  return h.length ? h[h.length - 1].at : (app.applied_at ?? null);
}

const STAGE_LABEL: Record<Stage, string> = {
  found: 'found',
  grilled: 'grilled',
  vetoed: 'vetoed',
  applied: 'applied',
  interviewing: 'interviewing',
  offer: 'offer',
  rejected: 'rejected',
  withdrawn: 'withdrawn',
  ghosted: 'ghosted',
};

function stageDelta(app: Application, from: Stage, to: Stage, at: string): Delta {
  const good: Stage[] = ['interviewing', 'offer'];
  const bad: Stage[] = ['rejected', 'ghosted', 'withdrawn'];
  const tone = good.includes(to) ? 'go' : bad.includes(to) ? 'veto' : 'amber';
  const icon = to === 'offer' ? 'star' : to === 'interviewing' ? 'chat' : to === 'rejected' ? 'x' : 'warn';
  return {
    id: `stage-${app.job_id}-${at}`,
    kind: 'stage',
    at,
    title: `${app.title} @ ${app.company}`,
    detail: `${STAGE_LABEL[from]} > ${STAGE_LABEL[to]}`,
    tone,
    icon,
  };
}

/** Diff two snapshots; newest deltas first. */
export function detectDeltas(data: DashboardData): Delta[] {
  const prev = new Map(data.prev_applications.map((a) => [a.job_id, a]));
  const out: Delta[] = [];
  const now = new Date(data.generated_at).getTime();

  for (const app of data.applications) {
    const old = prev.get(app.job_id);
    if (!old) {
      // Brand-new row in this snapshot.
      if (app.stage === 'vetoed') {
        const at = lastChange(app) ?? data.generated_at;
        out.push({
          id: `veto-${app.job_id}`,
          kind: 'veto',
          at,
          title: `${app.title} @ ${app.company}`,
          detail: 'grill refused: below bar',
          tone: 'veto',
          icon: 'shield',
        });
      } else {
        out.push({
          id: `new-${app.job_id}`,
          kind: 'stage',
          at: lastChange(app) ?? data.generated_at,
          title: `${app.title} @ ${app.company}`,
          detail: `new application via ${app.board}`,
          tone: 'go',
          icon: 'bolt',
        });
      }
      continue;
    }
    if (old.stage !== app.stage) {
      const ev = app.stage_history[app.stage_history.length - 1];
      out.push(stageDelta(app, old.stage, app.stage, ev?.at ?? data.generated_at));
    }
    // Posting edits: salary or requirements changed under us.
    const ps = app.posting_snapshot;
    const ops = old.posting_snapshot;
    if (ps && ops) {
      if (ps.salary && ops.salary && ps.salary !== ops.salary) {
        out.push({
          id: `edit-${app.job_id}-salary`,
          kind: 'posting_edit',
          at: data.generated_at,
          title: `${app.title} @ ${app.company}`,
          detail: `salary changed: ${ops.salary} > ${ps.salary}`,
          tone: 'amber',
          icon: 'pencil',
        });
      }
      const oldReq = (ops.requirements ?? []).join('|');
      const newReq = (ps.requirements ?? []).join('|');
      if (oldReq !== newReq && (ops.requirements ?? []).length > 0) {
        out.push({
          id: `edit-${app.job_id}-reqs`,
          kind: 'posting_edit',
          at: data.generated_at,
          title: `${app.title} @ ${app.company}`,
          detail: 'posting requirements edited',
          tone: 'amber',
          icon: 'doc',
        });
      }
    }
  }

  // New watch matches since the previous snapshot.
  for (const hit of data.watch_hits) {
    if (new Date(hit.first_seen).getTime() > new Date(data.prev_snapshot_at).getTime()) {
      out.push({
        id: `watch-${hit.job_id}`,
        kind: 'new_match',
        at: hit.first_seen,
        title: `${hit.title} @ ${hit.company}`,
        detail: `new match: watch "${hit.watch}" · ${hit.board}`,
        tone: '',
        icon: 'search',
      });
    }
  }

  // Stale: applied long ago, no movement.
  for (const app of data.applications) {
    if (app.stage !== 'applied') continue;
    const last = lastChange(app);
    if (!last) continue;
    if ((now - new Date(last).getTime()) / DAY_MS >= STALE_DAYS) {
      out.push({
        id: `stale-${app.job_id}`,
        kind: 'stale',
        at: last,
        title: `${app.title} @ ${app.company}`,
        detail: `no movement for ${Math.floor((now - new Date(last).getTime()) / DAY_MS)}d: follow up?`,
        tone: 'amber',
        icon: 'hourglass',
      });
    }
  }

  out.sort((a, b) => +new Date(b.at) - +new Date(a.at));
  return out;
}

/* ---------------- KPIs ---------------- */

function median(xs: number[]): number | null {
  if (!xs.length) return null;
  const s = [...xs].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

export function computeKpis(apps: Application[]): Kpis {
  const byStage = (s: Stage) => apps.filter((a) => a.stage === s);
  const appliedBase = apps.filter((a) =>
    ['applied', 'interviewing', 'offer', 'rejected', 'ghosted', 'withdrawn'].includes(a.stage),
  );
  const vetoed = byStage('vetoed').length;
  const decided = vetoed + appliedBase.length;
  const responded = apps.filter((a) => ['interviewing', 'offer'].includes(a.stage)).length;
  const respDays: number[] = [];
  for (const a of apps) {
    if (!a.applied_at) continue;
    const first = a.stage_history.find((e) => ['interviewing', 'offer', 'rejected'].includes(e.stage));
    if (first) respDays.push(Math.max(0, daysBetween(a.applied_at, first.at)));
  }
  return {
    active: byStage('applied').length + byStage('interviewing').length,
    vetoRate: decided ? vetoed / decided : 0,
    responseRate: appliedBase.length ? responded / appliedBase.length : 0,
    interviews: byStage('interviewing').length,
    offers: byStage('offer').length,
    medianDaysToResponse: median(respDays),
    total: apps.length,
  };
}

export function funnelCounts(apps: Application[]): { label: string; count: number; tone: string }[] {
  const c = (ss: Stage[]) => apps.filter((a) => ss.includes(a.stage)).length;
  return [
    { label: 'found', count: apps.length, tone: '' },
    { label: 'grilled', count: c(['grilled', 'vetoed', 'applied', 'interviewing', 'offer', 'rejected', 'withdrawn', 'ghosted']), tone: '' },
    { label: 'vetoed', count: c(['vetoed']), tone: 'veto' },
    { label: 'applied', count: c(['applied', 'interviewing', 'offer', 'rejected', 'withdrawn', 'ghosted']), tone: 'go' },
    { label: 'interviewing', count: c(['interviewing', 'offer']), tone: 'go' },
    { label: 'offer', count: c(['offer']), tone: 'amber' },
  ];
}

export function boardStats(apps: Application[]): BoardStat[] {
  const map = new Map<string, { applied: number; responded: number }>();
  for (const a of apps) {
    if (!['applied', 'interviewing', 'offer', 'rejected', 'ghosted', 'withdrawn'].includes(a.stage)) continue;
    const e = map.get(a.board) ?? { applied: 0, responded: 0 };
    e.applied += 1;
    if (['interviewing', 'offer'].includes(a.stage)) e.responded += 1;
    map.set(a.board, e);
  }
  return [...map.entries()]
    .map(([board, e]) => ({ board, ...e, rate: e.applied ? e.responded / e.applied : 0 }))
    .sort((a, b) => b.applied - a.applied);
}

export function isTerminal(stage: Stage): boolean {
  return TERMINAL.includes(stage);
}

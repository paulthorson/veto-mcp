/* Feature F (BYOA daily companion loop): deterministic pipeline analysis.
 *
 * Pure functions, no randomness, no model calls. All time-based rules take
 * an explicit `nowIso` so tests and demos are fully deterministic.
 *
 * Concepts mirror the Python backend's network_crm.py:
 *  - analyzeProspects ≈ staleness/nudge logic (who needs attention)
 *  - warmPathTo      ≈ network_crm.warm_path_to (1st/2nd-degree warm paths,
 *    derived only from recorded contacts — never invented)
 */

import type {
  NetworkContact,
  Prospect,
  ProspectStage,
  WarmPath,
} from './companionTypes';

/** Whole days from `fromIso` to `toIso`, compared on calendar dates (UTC). */
export function daysBetween(fromIso: string, toIso: string): number {
  const from = new Date(fromIso);
  const to = new Date(toIso);
  const fromDay = Date.UTC(
    from.getUTCFullYear(),
    from.getUTCMonth(),
    from.getUTCDate(),
  );
  const toDay = Date.UTC(to.getUTCFullYear(), to.getUTCMonth(), to.getUTCDate());
  return Math.round((toDay - fromDay) / 86_400_000);
}

/** Stages that count as "live" pipeline.
 *
 * SEMANTICS (decided 2026-10-11): 'offer' means offer-RECEIVED — the
 * offer is still live until it is accepted or rejected, so it counts
 * here alongside the earlier stages. This is what the PipelineBoard's
 * Offer column renders, so every surface agrees: an offer on the board
 * is a live prospect in feedNudge ('pipeline is empty' only when there
 * are none), in checkInSummary ('everything fresh'), and in
 * liveProspectCount. Only 'rejected' is out. */
const LIVE_STAGES: ProspectStage[] = ['interested', 'applied', 'interviewing', 'offer'];

/** Late stages where recent activity means real momentum. */
const HOT_STAGES: ProspectStage[] = ['interviewing', 'offer'];

export interface ProspectAnalysis {
  /** Late-stage prospects with activity in the last 7 days. */
  heatingUp: Prospect[];
  /** Live prospects with no activity in 10+ days. */
  goingQuiet: Prospect[];
  /** Applied 5+ days ago with no recent activity. */
  needsFollowUp: Prospect[];
}

/**
 * Bucket prospects into staleness signals.
 *
 * heatingUp: a prospect is "heating up" when it sits in a late stage
 * (interviewing / offer) and saw activity in the last 7 days. The Prospect
 * type carries no stage-change history, so recent late-stage activity is
 * the deterministic proxy for "stage advanced recently" — documented here
 * so a future stageHistory field can replace it.
 *
 * goingQuiet: live prospect (interested / applied / interviewing /
 * offer-received) with no activity in 10+ days.
 *
 * needsFollowUp: applied 5+ days ago with no activity since — the nudge to
 * send the follow-up note.
 *
 * Rejected prospects appear in no bucket. A prospect may appear in both
 * goingQuiet and needsFollowUp; buckets are independent signals.
 */
export function analyzeProspects(
  prospects: Prospect[],
  nowIso: string = new Date().toISOString(),
): ProspectAnalysis {
  const heatingUp: Prospect[] = [];
  const goingQuiet: Prospect[] = [];
  const needsFollowUp: Prospect[] = [];

  for (const p of prospects) {
    /* Future-dated activity is clamped to today ("active today"),
       agreeing with PipelineCard's staleness display — it is never
       silently dropped from the analysis. */
    const days = Math.max(0, daysBetween(p.lastActivity, nowIso));
    if (HOT_STAGES.includes(p.stage) && days <= 7) heatingUp.push(p);
    if (LIVE_STAGES.includes(p.stage) && days >= 10) goingQuiet.push(p);
    if (p.stage === 'applied' && days >= 5) needsFollowUp.push(p);
  }

  const byRecentFirst = (a: Prospect, b: Prospect) =>
    daysBetween(a.lastActivity, nowIso) - daysBetween(b.lastActivity, nowIso);
  const byStalestFirst = (a: Prospect, b: Prospect) =>
    daysBetween(b.lastActivity, nowIso) - daysBetween(a.lastActivity, nowIso);

  heatingUp.sort(byRecentFirst);
  goingQuiet.sort(byStalestFirst);
  needsFollowUp.sort(byStalestFirst);

  return { heatingUp, goingQuiet, needsFollowUp };
}

/**
 * Find warm paths from the user's network toward `company`.
 *
 * 1st degree: a recorded contact works at the target company
 * (case-insensitive substring match, like the Python backend's
 * normalization) and is close enough to ask directly (closeness 1–2).
 *
 * 2nd degree: a weak tie (closeness 3) at the target company, reached via
 * a close colleague (closeness 1–2) at the same company. The colleague
 * link is the one documented inference here: people at the same company
 * know each other. "Same company" uses the same substring normalization
 * as the company filter (either name containing the other), so
 * 'Acme Robotics EU' still links to a colleague at 'Acme Robotics'.
 * A weak tie with no close colleague at the same company is still a
 * direct (1st-degree) contact — it stays in your network.
 *
 * RANK ORDER (pinned by tests): every 1st-degree path precedes every
 * 2nd-degree path, so a bridged weak tie can never outrank a direct
 * contact. Within a degree the closest contact comes first.
 *
 * Honesty contract (mirrors network_crm.py): paths come only from the
 * recorded contacts passed in. No path exists → empty array, and callers
 * should say so plainly instead of suggesting cold outreach as "warm".
 */
export function warmPathTo(
  company: string,
  network: NetworkContact[],
): WarmPath[] {
  const target = company.trim().toLowerCase();
  if (!target) return [];

  const atCompany = network.filter((c) =>
    c.company.toLowerCase().includes(target),
  );
  if (atCompany.length === 0) return [];

  const byClosenessThenName = (a: NetworkContact, b: NetworkContact) =>
    a.closeness - b.closeness || a.name.localeCompare(b.name);

  const close = atCompany
    .filter((c) => c.closeness <= 2)
    .sort(byClosenessThenName);
  const weak = atCompany
    .filter((c) => c.closeness === 3)
    .sort(byClosenessThenName);

  const first: WarmPath[] = close.map((contact) => ({ contact, degrees: 1 as const }));
  const second: WarmPath[] = [];

  for (const contact of weak) {
    // Closest colleague at the same company becomes the bridge.
    const bridge = close.find((c) => sameCompany(c.company, contact.company));
    if (bridge) {
      second.push({ contact, via: bridge, degrees: 2 as const });
    } else {
      first.push({ contact, degrees: 1 as const });
    }
  }

  return [...first, ...second];
}

/* Same substring normalization as the company filter: two company names
   are "the same company" when either contains the other. */
function sameCompany(a: string, b: string): boolean {
  const x = a.trim().toLowerCase();
  const y = b.trim().toLowerCase();
  return x.includes(y) || y.includes(x);
}

/**
 * The single warmest path toward `company`: 1st degree beats 2nd degree,
 * and within a degree the closest contact comes first. `warmPathTo`
 * already returns paths in that rank order, so the warmest is the first.
 * `undefined` when no path exists (honesty contract).
 */
export function warmestPathTo(
  company: string,
  network: NetworkContact[],
): WarmPath | undefined {
  return warmPathTo(company, network)[0];
}

/** Count live prospects. 'offer' is offer-received (still live); only
 *  'rejected' is excluded — see the LIVE_STAGES semantics note. */
export function liveProspectCount(prospects: Prospect[]): number {
  return prospects.filter((p) => LIVE_STAGES.includes(p.stage)).length;
}

function plural(n: number, one: string, many: string): string {
  return n === 1 ? one : many;
}

/**
 * 2–3 plain-English sentences summarizing the daily check-in.
 * Coach tone: warm, direct, never nagging.
 */
export function checkInSummary(analysis: ProspectAnalysis): string {
  const h = analysis.heatingUp.length;
  const q = analysis.goingQuiet.length;
  const f = analysis.needsFollowUp.length;

  const sentences: string[] = [];
  if (h > 0) {
    sentences.push(
      `${h} ${plural(h, 'prospect is', 'prospects are')} heating up — keep the momentum going while the thread is warm.`,
    );
  } else {
    sentences.push(
      'Nothing heating up right now — that is fine, pipelines breathe.',
    );
  }
  if (q > 0) {
    sentences.push(
      `${q} ${plural(q, 'has', 'have')} gone quiet for a while; a short check-in note can restart the conversation.`,
    );
  }
  if (f > 0) {
    sentences.push(
      `${f} ${plural(f, 'needs', 'need')} a follow-up this week — one polite nudge beats letting the application sit.`,
    );
  }
  if (q === 0 && f === 0) {
    sentences.push('Everything live has fresh activity. Nice steady cadence.');
  }
  return sentences.join(' ');
}

/**
 * A coaching (not nagging) prompt to feed more jobs into the pipeline.
 * References pipeline fullness so the ask feels proportional.
 */
export function feedNudge(prospects: Prospect[]): string {
  const live = liveProspectCount(prospects);
  if (live === 0) {
    return (
      'The pipeline is empty right now. Adding 2–3 prospects this week ' +
      'gives the daily loop something to work with.'
    );
  }
  const more = live >= 5 ? 1 : 2;
  return (
    `${live} live ${plural(live, 'prospect', 'prospects')} — feeding ` +
    `${more} more ${plural(more, 'job', 'jobs')} this week keeps the pipeline healthy.`
  );
}

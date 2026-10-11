/* Feature F: CompanionDashboard — the BYOA daily companion loop surface.
 *
 * Presentational only: takes prospects + network as props, derives the
 * check-in via companionLoop, renders the pipeline grouped by stage,
 * follow-up callouts, warm paths per prospect company, and the feed-more
 * nudge. Persistence and mounting are the integrator's job (see
 * INTEGRATION-F.md).
 */

import { useMemo } from 'react';
import type {
  NetworkContact,
  Prospect,
  ProspectStage,
  WarmPath,
} from '../../lib/companionTypes';
import {
  analyzeProspects,
  checkInSummary,
  feedNudge,
  warmestPathTo,
} from '../../lib/companionLoop';

export interface CompanionDashboardProps {
  prospects: Prospect[];
  network: NetworkContact[];
  /** ISO timestamp for deterministic rendering (defaults to now). */
  nowIso?: string;
}

const STAGE_ORDER: ProspectStage[] = [
  'interested',
  'applied',
  'interviewing',
  'offer',
  'rejected',
];

const STAGE_LABEL: Record<ProspectStage, string> = {
  interested: 'Wishlist', // matches the pipeline board column for this stage
  applied: 'Applied',
  interviewing: 'Interviewing',
  offer: 'Offer',
  rejected: 'Rejected',
};

function WarmPathLine({ path }: { path: WarmPath }) {
  const { contact, via, degrees } = path;
  return (
    <li data-testid="warm-path">
      {degrees === 1 ? (
        <span>
          <strong>{contact.name}</strong> ({contact.title}) works at{' '}
          {contact.company} — reach out directly.
        </span>
      ) : (
        <span>
          <strong>{contact.name}</strong> ({contact.title}) is at {contact.company};
          ask <strong>{via?.name}</strong> for a warm intro.
        </span>
      )}
    </li>
  );
}

function ProspectWarmPaths({
  prospect,
  network,
}: {
  prospect: Prospect;
  network: NetworkContact[];
}) {
  // One warmest path per prospect company: 1st degree beats 2nd, and
  // within a degree the closest contact comes first.
  const path = useMemo(
    () => warmestPathTo(prospect.job.company, network),
    [prospect.job.company, network],
  );
  return (
    <div data-testid="warm-paths">
      {path ? (
        <ul>
          <WarmPathLine key={path.contact.id} path={path} />
        </ul>
      ) : (
        <p data-testid="warm-path-none">
          No warm path into {prospect.job.company} in your network yet — this
          one goes in cold, or grow the network first.
        </p>
      )}
    </div>
  );
}

export default function CompanionDashboard({
  prospects,
  network,
  nowIso,
}: CompanionDashboardProps) {
  const analysis = useMemo(
    () => analyzeProspects(prospects, nowIso),
    [prospects, nowIso],
  );
  const summary = useMemo(() => checkInSummary(analysis), [analysis]);
  const nudge = useMemo(() => feedNudge(prospects), [prospects]);
  const followUpIds = useMemo(
    () => new Set(analysis.needsFollowUp.map((p) => p.id)),
    [analysis],
  );

  const byStage = useMemo(() => {
    const map = new Map<ProspectStage, Prospect[]>();
    for (const stage of STAGE_ORDER) map.set(stage, []);
    for (const p of prospects) map.get(p.stage)?.push(p);
    return map;
  }, [prospects]);

  return (
    <section
      data-testid="companion-dashboard"
      aria-label="Daily companion check-in"
      style={{
        border: '1px solid #2a2a3a',
        borderRadius: 12,
        padding: 20,
        background: '#14141c',
        color: '#f2f0e9',
        maxWidth: 720,
      }}
    >
      <h2>Daily check-in</h2>
      <p data-testid="checkin-summary">{summary}</p>

      {analysis.needsFollowUp.length > 0 && (
        <div
          data-testid="followup-callouts"
          style={{
            borderLeft: '3px solid #ffb000',
            padding: '8px 12px',
            margin: '12px 0',
            background: '#1d1a12',
          }}
        >
          <strong>Needs a follow-up:</strong>
          <ul>
            {analysis.needsFollowUp.map((p) => (
              <li key={p.id} data-testid="followup-callout">
                {p.job.title} at {p.job.company} — quiet since{' '}
                {p.lastActivity.slice(0, 10)}
              </li>
            ))}
          </ul>
        </div>
      )}

      {STAGE_ORDER.map((stage) => {
        const group = byStage.get(stage) ?? [];
        if (group.length === 0) return null;
        return (
          <div key={stage} data-testid={`prospect-group-${stage}`}>
            <h3>
              {STAGE_LABEL[stage]} ({group.length})
            </h3>
            <ul>
              {group.map((p) => (
                <li key={p.id} data-testid="prospect">
                  <strong>{p.job.title}</strong> at {p.job.company}
                  {followUpIds.has(p.id) && (
                    <span data-testid="prospect-followup-flag"> — follow up</span>
                  )}
                  <ProspectWarmPaths prospect={p} network={network} />
                </li>
              ))}
            </ul>
          </div>
        );
      })}

      <p
        data-testid="feed-nudge"
        style={{
          marginTop: 16,
          padding: '10px 12px',
          background: '#12241a',
          borderRadius: 8,
        }}
      >
        {nudge}
      </p>
    </section>
  );
}

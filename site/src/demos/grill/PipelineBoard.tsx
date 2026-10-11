/* Feature F: PipelineBoard — the "where do I stand" home view.
 *
 * Four columns (wishlist → applied → interviewing → offer) over the same
 * Prospect data model as the companion loop. Presentational only: props
 * in, board out. The integrator owns persistence and mounting (see
 * INTEGRATION-F.md).
 *
 * Column mapping choice (documented): ProspectStage 'interested' maps to
 * the Wishlist column — "wishlist" is the user's word for "on my radar,
 * not yet applied". No new stage was added, so ProspectStage stays stable
 * for every other consumer. 'rejected' prospects are not shown on the
 * board: the board is the live pipeline view.
 */

import { useMemo } from 'react';
import type { Prospect, ProspectStage } from '../../lib/companionTypes';
import { daysBetween } from '../../lib/companionLoop';

export interface PipelineBoardProps {
  prospects: Prospect[];
  /** ISO timestamp for deterministic rendering (defaults to now). */
  nowIso?: string;
}

interface BoardColumn {
  key: string;
  label: string;
  stages: ProspectStage[];
}

const COLUMNS: BoardColumn[] = [
  { key: 'wishlist', label: 'Wishlist', stages: ['interested'] },
  { key: 'applied', label: 'Applied', stages: ['applied'] },
  { key: 'interviewing', label: 'Interviewing', stages: ['interviewing'] },
  { key: 'offer', label: 'Offer', stages: ['offer'] },
];

/** Staleness at a glance: quiet prospects read as "quiet N days". */
export function stalenessLabel(days: number): string {
  if (days <= 0) return 'active today';
  if (days < 10) return `active ${days}d ago`;
  return `quiet ${days} days`;
}

function PipelineCard({
  prospect,
  nowIso,
}: {
  prospect: Prospect;
  nowIso: string;
}) {
  const days = Math.max(0, daysBetween(prospect.lastActivity, nowIso));
  return (
    <li
      data-testid="pipeline-card"
      data-prospect-id={prospect.id}
      style={{
        border: '1px solid #2a2a3a',
        borderRadius: 8,
        padding: '10px 12px',
        marginBottom: 8,
        background: '#1a1a24',
        listStyle: 'none',
      }}
    >
      <div>
        <strong>{prospect.job.title}</strong>
      </div>
      <div style={{ color: '#a9a7ba', fontSize: 14 }}>{prospect.job.company}</div>
      <div
        data-testid="pipeline-card-staleness"
        style={{
          marginTop: 6,
          fontSize: 13,
          color: days >= 10 ? '#ffb000' : '#6f6d84',
        }}
      >
        {stalenessLabel(days)}
      </div>
    </li>
  );
}

export default function PipelineBoard({
  prospects,
  nowIso = new Date().toISOString(),
}: PipelineBoardProps) {
  const columns = useMemo(() => {
    const live = prospects.filter((p) => p.stage !== 'rejected');
    return COLUMNS.map((col) => ({
      ...col,
      cards: live
        .filter((p) => col.stages.includes(p.stage))
        // Stalest first: the board surfaces what needs attention.
        .sort(
          (a, b) =>
            daysBetween(b.lastActivity, nowIso) -
            daysBetween(a.lastActivity, nowIso),
        ),
    }));
  }, [prospects, nowIso]);

  return (
    <section
      data-testid="pipeline-board"
      aria-label="Pipeline board"
      style={{
        border: '1px solid #2a2a3a',
        borderRadius: 12,
        padding: 20,
        background: '#14141c',
        color: '#f2f0e9',
        maxWidth: 960,
      }}
    >
      <h2>Pipeline</h2>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, minmax(0, 1fr))',
          gap: 12,
        }}
      >
        {columns.map((col) => (
          <div key={col.key} data-testid={`pipeline-column-${col.key}`}>
            <h3 style={{ fontSize: 15 }}>
              {col.label} ({col.cards.length})
            </h3>
            <ul style={{ padding: 0, margin: 0 }}>
              {col.cards.map((p) => (
                <PipelineCard key={p.id} prospect={p} nowIso={nowIso} />
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}

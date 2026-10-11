/* Feature F tests: PipelineBoard — column mapping, staleness display,
 * empty pipeline. Rendered with react-dom/server for deterministic HTML
 * assertions (no test renderer dependency).
 */

import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import PipelineBoard, { stalenessLabel } from '../../demos/grill/PipelineBoard';
import type { Prospect } from '../companionTypes';

const NOW = '2026-10-11T12:00:00.000Z';

function prospect(
  id: string,
  stage: Prospect['stage'],
  lastActivity: string,
  company = 'Acme Robotics',
): Prospect {
  return {
    id,
    job: {
      title: `Role ${id}`,
      company,
      rawText: `Role ${id} at ${company}`,
      requirements: [],
      roleKeywords: [],
      source: 'paste',
    },
    stage,
    notes: [],
    lastActivity,
    addedAt: '2026-09-01T09:00:00.000Z',
  };
}

function render(prospects: Prospect[]): string {
  return renderToStaticMarkup(
    <PipelineBoard prospects={prospects} nowIso={NOW} />,
  );
}

describe('stalenessLabel', () => {
  it('reads staleness at a glance', () => {
    expect(stalenessLabel(0)).toBe('active today');
    expect(stalenessLabel(3)).toBe('active 3d ago');
    expect(stalenessLabel(12)).toBe('quiet 12 days');
  });

  it('pins the 9/10 active-to-quiet boundary', () => {
    expect(stalenessLabel(9)).toBe('active 9d ago');
    expect(stalenessLabel(10)).toBe('quiet 10 days');
  });
});

describe('PipelineBoard', () => {
  it('maps stages to columns: interested -> wishlist', () => {
    const html = render([
      prospect('w1', 'interested', '2026-10-10T10:00:00Z'),
      prospect('a1', 'applied', '2026-10-10T10:00:00Z'),
      prospect('i1', 'interviewing', '2026-10-10T10:00:00Z'),
      prospect('o1', 'offer', '2026-10-10T10:00:00Z'),
    ]);
    expect(html).toContain('data-testid="pipeline-board"');
    for (const col of ['wishlist', 'applied', 'interviewing', 'offer']) {
      expect(html).toContain(`data-testid="pipeline-column-${col}"`);
    }
    // Each card sits under its column heading.
    const wishlistIdx = html.indexOf('pipeline-column-wishlist');
    const appliedIdx = html.indexOf('pipeline-column-applied');
    expect(html.indexOf('Role w1', wishlistIdx)).toBeLessThan(appliedIdx);
    expect(html.indexOf('Role a1', appliedIdx)).toBeGreaterThan(0);
  });

  it('shows staleness on cards ("quiet 12 days")', () => {
    const html = render([
      prospect('s1', 'applied', '2026-09-29T10:00:00Z'), // 12 days before NOW
    ]);
    expect(html).toContain('data-testid="pipeline-card"');
    expect(html).toContain('quiet 12 days');
  });

  it('renders future-dated activity as "active today" (agrees with analyzeProspects)', () => {
    const html = render([
      prospect('f1', 'applied', '2026-10-15T10:00:00Z'), // after NOW
    ]);
    expect(html).toContain('data-testid="pipeline-card"');
    expect(html).toContain('active today');
  });

  it('excludes rejected prospects from the live board', () => {
    const html = render([
      prospect('r1', 'rejected', '2026-09-01T10:00:00Z'),
    ]);
    expect(html).not.toContain('Role r1');
    expect(html).not.toContain('data-testid="pipeline-card"');
  });

  it('renders four empty columns for an empty pipeline', () => {
    const html = render([]);
    expect(html).toContain('data-testid="pipeline-board"');
    for (const col of ['wishlist', 'applied', 'interviewing', 'offer']) {
      expect(html).toContain(`data-testid="pipeline-column-${col}"`);
    }
    expect(html).not.toContain('data-testid="pipeline-card"');
  });

  it('sorts stalest first within a column', () => {
    const html = render([
      prospect('n1', 'applied', '2026-10-10T10:00:00Z'),
      prospect('n2', 'applied', '2026-09-20T10:00:00Z'),
    ]);
    expect(html.indexOf('Role n2')).toBeLessThan(html.indexOf('Role n1'));
  });
});

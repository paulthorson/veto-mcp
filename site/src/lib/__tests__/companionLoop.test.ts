/* Feature F tests: companionLoop — staleness buckets, warm paths, summaries.
 * All time-based tests pin `nowIso` so they are fully deterministic.
 */

import { describe, expect, it } from 'vitest';
import {
  analyzeProspects,
  checkInSummary,
  daysBetween,
  feedNudge,
  liveProspectCount,
  warmestPathTo,
  warmPathTo,
} from '../companionLoop';
import type { NetworkContact, Prospect } from '../companionTypes';
import { FIXTURE_NETWORK } from '../fixtures/network';

const NOW = '2026-10-11T12:00:00.000Z';

function job(company: string, title = 'Backend Engineer') {
  return {
    title,
    company,
    rawText: `${title} at ${company}`,
    requirements: ['3+ years backend'],
    roleKeywords: ['backend'],
    source: 'paste' as const,
  };
}

function prospect(
  id: string,
  stage: Prospect['stage'],
  lastActivity: string,
  company = 'Acme Robotics',
): Prospect {
  return {
    id,
    job: job(company),
    stage,
    notes: ['applied via careers page'],
    lastActivity,
    addedAt: '2026-09-01T09:00:00.000Z',
  };
}

describe('daysBetween', () => {
  it('counts whole calendar days', () => {
    expect(daysBetween('2026-10-01T00:00:00Z', '2026-10-11T23:59:59Z')).toBe(10);
    expect(daysBetween('2026-10-11T12:00:00Z', '2026-10-11T12:00:00Z')).toBe(0);
  });
});

describe('analyzeProspects', () => {
  it('buckets heatingUp for recent late-stage activity', () => {
    const ps = [
      prospect('p1', 'interviewing', '2026-10-09T10:00:00Z'),
      prospect('p2', 'offer', '2026-10-11T08:00:00Z'),
      prospect('p3', 'interviewing', '2026-09-20T10:00:00Z'), // stale late stage
    ];
    const a = analyzeProspects(ps, NOW);
    expect(a.heatingUp.map((p) => p.id).sort()).toEqual(['p1', 'p2']);
    expect(a.heatingUp.map((p) => p.id)).not.toContain('p3');
  });

  it('buckets goingQuiet for 10+ days without activity', () => {
    const ps = [
      prospect('q1', 'applied', '2026-10-01T10:00:00Z'), // exactly 10 days
      prospect('q2', 'interested', '2026-09-15T10:00:00Z'),
      prospect('q3', 'applied', '2026-10-05T10:00:00Z'), // 6 days: not quiet
      prospect('q4', 'rejected', '2026-08-01T10:00:00Z'), // rejected: never
    ];
    const a = analyzeProspects(ps, NOW);
    expect(a.goingQuiet.map((p) => p.id).sort()).toEqual(['q1', 'q2']);
  });

  it('buckets needsFollowUp for applied 5+ days idle', () => {
    const ps = [
      prospect('f1', 'applied', '2026-10-06T10:00:00Z'), // exactly 5 days
      prospect('f2', 'applied', '2026-10-09T10:00:00Z'), // 2 days: fresh
      prospect('f3', 'interviewing', '2026-10-01T10:00:00Z'), // wrong stage
    ];
    const a = analyzeProspects(ps, NOW);
    expect(a.needsFollowUp.map((p) => p.id)).toEqual(['f1']);
  });

  it('sorts stalest-first for quiet/followup, freshest-first for heating', () => {
    const ps = [
      prospect('s1', 'applied', '2026-09-01T10:00:00Z'),
      prospect('s2', 'applied', '2026-09-20T10:00:00Z'),
    ];
    const a = analyzeProspects(ps, NOW);
    expect(a.goingQuiet.map((p) => p.id)).toEqual(['s1', 's2']);
    expect(a.needsFollowUp.map((p) => p.id)).toEqual(['s1', 's2']);
  });

  it('sorts heatingUp most-recent-first', () => {
    const ps = [
      prospect('h1', 'interviewing', '2026-10-09T10:00:00Z'),
      prospect('h2', 'interviewing', '2026-10-11T08:00:00Z'),
      prospect('h3', 'offer', '2026-10-10T10:00:00Z'),
    ];
    const a = analyzeProspects(ps, NOW);
    expect(a.heatingUp.map((p) => p.id)).toEqual(['h2', 'h3', 'h1']);
  });

  it('pins the exactly-7-day heatingUp boundary', () => {
    const ps = [
      prospect('b7', 'interviewing', '2026-10-04T10:00:00Z'), // exactly 7 days: in
      prospect('b8', 'interviewing', '2026-10-03T10:00:00Z'), // 8 days: too stale
    ];
    const a = analyzeProspects(ps, NOW);
    expect(a.heatingUp.map((p) => p.id)).toEqual(['b7']);
  });

  it('clamps future-dated activity to today instead of dropping it', () => {
    /* Agrees with PipelineCard, which renders future-dated activity as
       'active today' — the two surfaces never disagree. */
    const ps = [prospect('fut', 'interviewing', '2026-10-15T10:00:00Z')];
    const a = analyzeProspects(ps, NOW);
    expect(a.heatingUp.map((p) => p.id)).toEqual(['fut']);
    expect(a.goingQuiet).toEqual([]);
    expect(a.needsFollowUp).toEqual([]);
  });

  it('handles empty input without throwing', () => {
    expect(analyzeProspects([], NOW)).toEqual({
      heatingUp: [],
      goingQuiet: [],
      needsFollowUp: [],
    });
  });

  it("offer means offer-received: it stays live on every surface", () => {
    const ps = [prospect('o1', 'offer', '2026-10-11T08:00:00Z')];
    expect(liveProspectCount(ps)).toBe(1);
    expect(feedNudge(ps)).toBe(
      '1 live prospect — feeding 2 more jobs this week keeps the pipeline healthy.',
    );
    const s = checkInSummary(analyzeProspects(ps, NOW));
    expect(s).toContain('1 prospect is heating up');
    expect(s).not.toContain('pipeline is empty');
  });

  it('an offer with fresh activity counts as fresh, live pipeline in the check-in', () => {
    const s = checkInSummary(analyzeProspects(
      [prospect('o1', 'offer', '2026-10-11T08:00:00Z')],
      NOW,
    ));
    expect(s).toContain('1 prospect is heating up');
    expect(s).toContain('Everything live has fresh activity');
  });

  it('a stale offer (10+ days idle) shows up in goingQuiet', () => {
    const ps = [prospect('o2', 'offer', '2026-09-20T10:00:00Z')]; // 21 days
    const a = analyzeProspects(ps, NOW);
    expect(a.goingQuiet.map((p) => p.id)).toEqual(['o2']);
    expect(feedNudge(ps)).not.toContain('pipeline is empty');
  });
});

describe('warmPathTo', () => {
  const net: NetworkContact[] = FIXTURE_NETWORK;

  it('finds 1st-degree contacts at the company (case-insensitive substring)', () => {
    const paths = warmPathTo('acme', net);
    expect(paths.length).toBe(2);
    expect(paths.every((p) => p.degrees === 1)).toBe(true);
    expect(paths.map((p) => p.contact.name).sort()).toEqual([
      'Jordan Ellis',
      'Priya Natarajan',
    ]);
  });

  it('finds a 2nd-degree path via a close colleague', () => {
    const paths = warmPathTo('Northwind Labs', net);
    const second = paths.find((p) => p.degrees === 2);
    expect(second).toBeDefined();
    expect(second!.contact.name).toBe('Dana Whitfield');
    expect(second!.via?.name).toBe('Sam Okafor');
  });

  it('returns an empty array when no path exists (honesty contract)', () => {
    expect(warmPathTo('Vandelay Industries', net)).toEqual([]);
    expect(warmPathTo('Nonexistent Corp', [])).toEqual([]);
    expect(warmPathTo('   ', net)).toEqual([]);
  });

  it('treats a weak tie with no close colleague as a direct contact', () => {
    const solo: NetworkContact[] = [
      { id: 'x1', name: 'Rae Kim', company: 'Solo Corp', title: 'Engineer', closeness: 3 },
    ];
    const paths = warmPathTo('solo', solo);
    expect(paths).toHaveLength(1);
    expect(paths[0].degrees).toBe(1);
    expect(paths[0].via).toBeUndefined();
  });

  it('ranks every 1st-degree path ahead of every 2nd-degree path', () => {
    /* Bob (close, TargetCo HQ) bridges Aaron (weak, TargetCo) into a
       2nd-degree path; Zoe (weak, TargetCo Labs) has no close colleague
       at her company, so she stays a direct 1st-degree contact. The old
       code emitted Aaron before Zoe — a bridged tie outranking a direct
       one. The rank contract: all 1st-degree first. */
    const net: NetworkContact[] = [
      { id: 'b1', name: 'Bob Bridge', company: 'TargetCo HQ', title: 'Eng', closeness: 1 },
      { id: 'a1', name: 'Aaron Weak', company: 'TargetCo', title: 'Eng', closeness: 3 },
      { id: 'z1', name: 'Zoe Direct', company: 'TargetCo Labs', title: 'Eng', closeness: 3 },
    ];
    const paths = warmPathTo('targetco', net);
    expect(paths.map((p) => p.degrees)).toEqual([1, 1, 2]);
    expect(paths.map((p) => p.contact.name)).toEqual([
      'Bob Bridge',
      'Zoe Direct',
      'Aaron Weak',
    ]);
    expect(paths[2].via?.name).toBe('Bob Bridge');
    expect(warmestPathTo('targetco', net)?.contact.name).toBe('Bob Bridge');
  });

  it('bridges with the same substring normalization as the company filter', () => {
    /* 'TargetCo HQ' contains 'TargetCo': the bridge lookup is not exact
       equality, so Aaron still links to Bob. */
    const net: NetworkContact[] = [
      { id: 'b1', name: 'Bob Bridge', company: 'TargetCo HQ', title: 'Eng', closeness: 2 },
      { id: 'a1', name: 'Aaron Weak', company: 'TargetCo', title: 'Eng', closeness: 3 },
    ];
    const paths = warmPathTo('targetco', net);
    expect(paths).toHaveLength(2);
    expect(paths[1].degrees).toBe(2);
    expect(paths[1].via?.name).toBe('Bob Bridge');
  });
});

describe('warmestPathTo', () => {
  it('returns the single warmest path: 1st degree beats 2nd', () => {
    const warmest = warmestPathTo('Northwind Labs', FIXTURE_NETWORK);
    expect(warmest?.contact.name).toBe('Sam Okafor');
    expect(warmest?.degrees).toBe(1);
  });

  it('ranks closer contacts first within a degree', () => {
    const warmest = warmestPathTo('acme', FIXTURE_NETWORK);
    expect(warmest?.contact.name).toBe('Jordan Ellis'); // closeness 1 beats 2
  });

  it('returns undefined when no path exists', () => {
    expect(warmestPathTo('Vandelay Industries', FIXTURE_NETWORK)).toBeUndefined();
  });
});

describe('checkInSummary', () => {
  it('mentions the counts in plain English, coach tone', () => {
    const s = checkInSummary({
      heatingUp: [prospect('p1', 'offer', '2026-10-11T08:00:00Z')],
      goingQuiet: [prospect('q1', 'applied', '2026-09-01T10:00:00Z')],
      needsFollowUp: [],
    });
    expect(s).toContain('1 prospect is heating up');
    expect(s).toContain('1 has gone quiet');
    expect(s).not.toMatch(/delve|unlock|elevate|seamless|robust|leverage|empower|journey|revolutionize|cutting-edge/i);
  });

  it('stays warm when nothing needs attention', () => {
    const s = checkInSummary({ heatingUp: [], goingQuiet: [], needsFollowUp: [] });
    expect(s).toContain('Nothing heating up right now');
    expect(s).toContain('fresh activity');
  });
});

describe('feedNudge', () => {
  it('references pipeline fullness for a healthy pipeline', () => {
    const ps = [
      prospect('a', 'applied', '2026-10-10T10:00:00Z'),
      prospect('b', 'interviewing', '2026-10-10T10:00:00Z'),
      prospect('c', 'interested', '2026-10-10T10:00:00Z'),
    ];
    const nudge = feedNudge(ps);
    expect(nudge).toBe(
      '3 live prospects — feeding 2 more jobs this week keeps the pipeline healthy.',
    );
  });

  it('coaches (not nags) on an empty pipeline', () => {
    const nudge = feedNudge([prospect('r', 'rejected', '2026-09-01T10:00:00Z')]);
    expect(nudge).toContain('pipeline is empty');
    expect(nudge).not.toMatch(/should have|you need to|failing|lazy/i);
  });

  it('asks for 1 more job at exactly 5 live prospects, 2 below', () => {
    const five = [1, 2, 3, 4, 5].map((i) =>
      prospect(`m${i}`, 'applied', '2026-10-10T10:00:00Z'),
    );
    expect(feedNudge(five)).toBe(
      '5 live prospects — feeding 1 more job this week keeps the pipeline healthy.',
    );
    const four = five.slice(0, 4);
    expect(feedNudge(four)).toBe(
      '4 live prospects — feeding 2 more jobs this week keeps the pipeline healthy.',
    );
  });

  it('handles empty input without throwing', () => {
    expect(() => feedNudge([])).not.toThrow();
    expect(liveProspectCount([])).toBe(0);
  });
});

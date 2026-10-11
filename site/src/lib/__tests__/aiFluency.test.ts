/* Feature B: AI fluency scoring tests. All deterministic — same in, same out. */
import { describe, expect, it } from 'vitest';
import {
  AI_FLUENCY_WEIGHTS,
  bandNote,
  scoreAiFluency,
  scoreFraming,
  scoreJudgment,
  scoreSteering,
} from '../aiFluency';
import type { FullAnswer } from '../demoGrill';
import type { JobContext } from '../chakraTypes';

const PRECISE: FullAnswer[] = [
  {
    qid: 'years',
    text: '9 years of backend experience, mostly fintech payments processing',
    cls: 'specific',
  },
  {
    qid: 'k8s',
    text: 'ran EKS in production daily for 3 years; however upgrades are a tradeoff between speed and stability, so we reviewed rollouts carefully',
    cls: 'specific',
  },
  {
    qid: 'scale',
    text: '~50M req/day across 40 nodes, p99 latency 120ms under peak traffic, budget constraint on new instances',
    cls: 'specific',
  },
  {
    qid: 'logistics',
    text: 'US citizen, no sponsorship needed; 3 days a week hybrid in the NYC office works for me',
    cls: 'specific',
  },
  {
    qid: 'motivation',
    text: 'the payments-scale problem is exactly my thing: 50M req/day is where my EKS tuning experience pays off, though I would have to check how the on-call rotation works',
    cls: 'specific',
  },
];

const HEDGY: FullAnswer[] = [
  { qid: 'years', text: 'some years, a bit, around that', cls: 'vague' },
  { qid: 'k8s', text: 'kinda familiar with stuff, sort of', cls: 'vague' },
  { qid: 'scale', text: 'probably big-ish, things and stuff', cls: 'vague' },
  { qid: 'logistics', text: 'maybe, kinda depends, not sure', cls: 'vague' },
  { qid: 'motivation', text: 'some stuff I guess, basically', cls: 'vague' },
];

const JOB: JobContext = {
  title: 'Staff Backend Engineer',
  company: 'Example Fintech Co',
  rawText: 'staff backend engineer posting',
  requirements: ['8+ years backend experience', 'Kubernetes in production'],
  roleKeywords: ['backend', 'kubernetes', 'eks', 'fintech'],
  source: 'paste',
};

describe('scoreAiFluency', () => {
  it('precise answers score high on every dimension', () => {
    const r = scoreAiFluency(PRECISE);
    expect(r.dimensions.framing).toBeGreaterThanOrEqual(70);
    expect(r.dimensions.judgment).toBeGreaterThanOrEqual(60);
    expect(r.dimensions.steering).toBeGreaterThanOrEqual(60);
    expect(r.score).toBeGreaterThanOrEqual(70);
    expect(r.note).toContain('AI fluency');
  });

  it('hedgy/vague answers score low, steering lowest', () => {
    const r = scoreAiFluency(HEDGY);
    expect(r.score).toBeLessThan(40);
    expect(r.dimensions.steering).toBeLessThan(r.dimensions.framing);
    expect(r.dimensions.steering).toBeLessThan(35);
  });

  it('is deterministic: same input always produces identical output', () => {
    const a = scoreAiFluency(PRECISE);
    const b = scoreAiFluency(PRECISE);
    const c = scoreAiFluency([...PRECISE.map((x) => ({ ...x }))]);
    expect(a).toEqual(b);
    expect(a).toEqual(c);
    expect(JSON.stringify(a)).toBe(JSON.stringify(c));
  });

  it('weights are documented and the overall follows them exactly', () => {
    // WEIGHTS contract: framing 40%, judgment 35%, steering 25%.
    expect(AI_FLUENCY_WEIGHTS.framing).toBe(0.4);
    expect(AI_FLUENCY_WEIGHTS.judgment).toBe(0.35);
    expect(AI_FLUENCY_WEIGHTS.steering).toBe(0.25);
    expect(AI_FLUENCY_WEIGHTS.framing + AI_FLUENCY_WEIGHTS.judgment + AI_FLUENCY_WEIGHTS.steering).toBe(
      1,
    );
    const r = scoreAiFluency(PRECISE);
    expect(r.score).toBe(
      Math.round(
        r.dimensions.framing * 0.4 + r.dimensions.judgment * 0.35 + r.dimensions.steering * 0.25,
      ),
    );
  });

  it('JobContext influences the note with role relevance', () => {
    const withJob = scoreAiFluency(PRECISE, JOB);
    const withoutJob = scoreAiFluency(PRECISE);
    expect(withJob.note).not.toBe(withoutJob.note);
    expect(withJob.note).toContain('Staff Backend Engineer');
    expect(withJob.note).toMatch(/reference 3\/4 of the role keywords/);
    expect(withJob.score).toBe(withoutJob.score); // note only — score unchanged
  });

  it('empty answers produce a zero score without crashing', () => {
    const r = scoreAiFluency([]);
    expect(r.score).toBe(0);
    expect(r.dimensions).toEqual({ framing: 0, judgment: 0, steering: 0 });
  });

  it('job with no keywords and no requirements notes the gap', () => {
    const emptyJob: JobContext = {
      title: 'Mystery Role',
      company: 'Unknown Co',
      rawText: '',
      requirements: [],
      roleKeywords: [],
      source: 'paste',
    };
    const r = scoreAiFluency(PRECISE, emptyJob);
    expect(r.note).toContain('no listed keywords');
    expect(r.score).toBe(scoreAiFluency(PRECISE).score);
  });

  it('bandNote boundaries are pinned', () => {
    expect(bandNote(75)).toContain('frames problems');
    expect(bandNote(74)).toContain('decent signal');
    expect(bandNote(50)).toContain('decent signal');
    expect(bandNote(49)).toContain('vague');
  });

  it('single blank-text answer documents the neutral-baseline behavior', () => {
    // Neutral baselines (framing 25, judgment 50, steering 40) mean a blank
    // answer scores 38, not 0 — this pins that behavior deliberately.
    const r = scoreAiFluency([{ qid: 'years', text: '', cls: 'vague' }]);
    expect(r.dimensions).toEqual({ framing: 25, judgment: 50, steering: 40 });
    expect(r.score).toBe(38);
  });
});

describe('per-answer dimension scorers', () => {
  it('framing rewards digit+context, constraints, and named tools', () => {
    // Deterministic pins: base 25 + 40 (digit+context) = 65; +20 constraint = 45.
    expect(scoreFraming('ran 40 nodes at 50M req/day')).toBe(65);
    expect(scoreFraming('shipped under a tight deadline with an sla')).toBe(45);
    expect(scoreFraming('some stuff')).toBe(25);
  });

  it('framing can reach exactly 100: substance + constraint + tool earns the bonus', () => {
    // 25 + 40 (digit+context) + 20 (constraint) + 10 (tool) + 5 (completeness) = 100.
    expect(
      scoreFraming('ran 40 nodes at 50M req/day under a budget constraint on EKS'),
    ).toBe(100);
    // Missing one booster: no completeness bonus, max 95 stays unreachable.
    expect(scoreFraming('ran 40 nodes at 50M req/day on EKS')).toBe(75);
    expect(scoreFraming('ran 40 nodes at 50M req/day under a budget constraint')).toBe(85);
  });

  it("ms only counts as the millisecond token, never as a word tail ('teams')", () => {
    // 'teams' ends in 'ms' but carries no timing context: no +40.
    expect(scoreFraming('we have 5 teams')).toBe(25);
    // Digit-attached '120ms' still counts as millisecond context.
    expect(scoreFraming('cut p99 latency to 120ms')).toBe(65);
    // Standalone 'ms' still counts.
    expect(scoreFraming('p99 latency 120 ms under load')).toBe(65);
  });

  it("'reviewed' counts once: no double-count across tradeoff and verify", () => {
    // Before the fix: 50 + 20 (tradeoff 'reviewed') + 15 (verify 'review') = 85.
    // After: VERIFY_RE's 'review' covers it; TRADEOFF_RE stays silent.
    expect(scoreJudgment('we reviewed the rollout carefully today')).toBe(65);
  });

  it('role keyword matching is documented substring matching', () => {
    // 'end' is a substring of 'backend' — the documented recall-favoring policy.
    const r = scoreAiFluency(PRECISE, { ...JOB, roleKeywords: ['end'] });
    expect(r.note).toMatch(/reference 1\/1 of the role keywords/);
    expect(r.score).toBe(scoreAiFluency(PRECISE).score); // note only — score unchanged
  });

  it('judgment rewards tradeoff/limit language and penalizes absolutes', () => {
    const withTradeoff = scoreJudgment('in production it is a tradeoff, however edge cases exist');
    const blind = scoreJudgment('this is always the best practice, obviously');
    expect(withTradeoff).toBeGreaterThan(blind);
    expect(scoreJudgment('I would verify and test the output')).toBeGreaterThanOrEqual(50);
  });

  it('steering punishes hedge words and rewards precise answers', () => {
    const crisp = scoreSteering('ran EKS in production daily for 3 years');
    const hedgy = scoreSteering('kinda around some stuff, sort of');
    expect(crisp).toBeGreaterThan(hedgy);
    expect(hedgy).toBeLessThan(40);
  });

  it('steering can reach 100 for a precisely-steered answer', () => {
    // Digit + domain context, length >= 30, zero hedge words: 40 + 25 + 10 + 25 = 100.
    expect(scoreSteering('ran EKS in production daily for 3 years')).toBe(100);
    // One hedge word removes the precision bonus.
    expect(scoreSteering('ran EKS in production daily for 3 years, basically')).toBeLessThan(100);
  });

  it('dimension scorers are deterministic and bounded', () => {
    const texts = ['9 years', 'some kinda stuff', 'tradeoff in production, verified'];
    for (const t of texts) {
      for (const fn of [scoreFraming, scoreJudgment, scoreSteering]) {
        const v = fn(t);
        expect(fn(t)).toBe(v);
        expect(v).toBeGreaterThanOrEqual(0);
        expect(v).toBeLessThanOrEqual(100);
      }
    }
  });
});

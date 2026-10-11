/* Feature C (Chakra): defend-your-answer flow — vitest.
 * Deterministic throughout: same inputs -> same outputs, every run.
 *
 * SELF-CONTAINMENT CONTRACT: these tests pin shouldDemandDefense's and
 * assessDefense's behavior, not demoGrill's. Classifications are passed
 * as explicit fixture literals ('specific' / 'vague') — the tests assert
 * what defendFlow does WITH a classification, never what classifyAnswer
 * computes. Pick-label strings ('Production daily', '10+') are used as
 * input data (they are verbatim labels in demoGrill's FULL_QUESTIONS),
 * but no test asserts classifyAnswer's output. */
import { describe, expect, it } from 'vitest';
import { FULL_QUESTIONS } from '../demoGrill';
import { assessDefense, getDefendPrompt, shouldDemandDefense } from '../defendFlow';

const QIDS = ['years', 'k8s', 'scale', 'logistics', 'motivation'] as const;

/* AI-slop ban (framework lock AI_SLOP_COPY_FAIL): none of these may
   appear in user-facing strings — prompts and assessment notes. */
const SLOP_RE = /\b(delve|unlock|elevate|seamless|robust|leverage|empower|journey|revolutionize|cutting-edge)\b/i;

describe('getDefendPrompt', () => {
  it('returns a non-empty, slop-free prompt for every question id', () => {
    for (const q of FULL_QUESTIONS) {
      const p = getDefendPrompt({ id: q.id, text: q.text }, 'ran EKS daily for 3 years');
      expect(p.length).toBeGreaterThan(20);
      expect(SLOP_RE.test(p)).toBe(false);
    }
  });

  it('has two distinct variants per question, picked by answer-length parity', () => {
    for (const qid of QIDS) {
      const even = getDefendPrompt({ id: qid, text: '' }, 'a'.repeat(20));
      const odd = getDefendPrompt({ id: qid, text: '' }, 'a'.repeat(21));
      expect(even).not.toBe(odd);
    }
  });

  it('is deterministic: same inputs -> same prompt', () => {
    const a = getDefendPrompt({ id: 'k8s', text: 'x' }, 'ran EKS daily');
    const b = getDefendPrompt({ id: 'k8s', text: 'x' }, 'ran EKS daily');
    expect(a).toBe(b);
  });

  it('k8s prompt echoes the answer and demands the 3am walkthrough', () => {
    /* 'ran EKS daily!' is 14 chars (even) -> variant 0, the 3am walkthrough. */
    const p = getDefendPrompt({ id: 'k8s', text: '' }, 'ran EKS daily!');
    expect(p).toContain('ran EKS daily!');
    expect(p).toContain('3am');
  });

  it('falls back to a generic demand for unknown question ids', () => {
    const p = getDefendPrompt({ id: 'nope', text: '' }, 'something');
    expect(p).toContain('something');
    expect(p.length).toBeGreaterThan(10);
  });
});

describe('shouldDemandDefense', () => {
  it('vague answers always trigger (R1)', () => {
    expect(shouldDemandDefense('years', 'some stuff', 'vague')).toBe(true);
    expect(shouldDemandDefense('k8s', 'idk', 'vague')).toBe(true);
    expect(shouldDemandDefense('motivation', '', 'vague')).toBe(true);
  });

  it('quick-pick verbatim triggers even when the pick classifies specific (R2a)', () => {
    /* 'Production daily' and '10+' are verbatim quick-pick labels in
       demoGrill's FULL_QUESTIONS — used here as input data. The pinned
       contract: verbatim label + specific classification -> trigger. */
    expect(shouldDemandDefense('k8s', 'Production daily', 'specific')).toBe(true);
    expect(shouldDemandDefense('years', '10+', 'specific')).toBe(true);
  });

  it('R2a is an exact label match: a near-miss with real length does not trigger', () => {
    /* 'production daily runbook' is not a verbatim label (case differs,
       extra word), is 23 chars (>= 20, so R2b stays quiet), and has no
       AI tell — so nothing fires. Pins the exact-match semantics. */
    expect(shouldDemandDefense('k8s', 'production daily runbook', 'specific')).toBe(false);
  });

  it('short specific answers (< 20 chars) trigger (R2b)', () => {
    expect(shouldDemandDefense('years', '9 years', 'specific')).toBe(true);
  });

  it('AI-tell phrases trigger (R2c)', () => {
    const ans = 'As an AI language model, I ran EKS for 5 years with deep expertise';
    expect(shouldDemandDefense('k8s', ans, 'specific')).toBe(true);
  });

  it('strong typed specific answers do not trigger', () => {
    const ans = 'I ran EKS in production for 6 years across 40 nodes, on-call weekly';
    expect(shouldDemandDefense('k8s', ans, 'specific')).toBe(false);
  });

  it('a typed answer near the length floor but real still does not trigger', () => {
    const ans = 'US citizen, hybrid NYC is fine';
    expect(shouldDemandDefense('logistics', ans, 'specific')).toBe(false);
  });
});

describe('assessDefense', () => {
  const good =
    'When a node goes NotReady in EKS, the kubelet stops heartbeating and pods get evicted after the toleration timeout. I would cordon and drain the node, read the kubelet logs, then replace it in the node group.';

  it('understands a specific defense tied to the original claim', () => {
    const r = assessDefense('k8s', 'ran EKS daily for 3 years', good);
    expect(r.understood).toBe(true);
    expect(r.score).toBeGreaterThanOrEqual(70);
    expect(r.note.length).toBeGreaterThan(10);
    expect(SLOP_RE.test(r.note)).toBe(false);
  });

  it('rejects "idk" as a defense', () => {
    const r = assessDefense('k8s', 'ran EKS daily for 3 years', 'idk');
    expect(r.understood).toBe(false);
    expect(r.score).toBeLessThan(40);
  });

  it('rejects a specific defense that dodges the original claim', () => {
    const dodge =
      'I led 2 teams shipping payments products with 99.9% uptime over 4 quarters';
    const r = assessDefense('k8s', 'ran EKS daily for 3 years', dodge);
    expect(r.understood).toBe(false);
    expect(r.note).toContain('dodged');
  });

  it('rejects a long but hedged non-answer', () => {
    const hedged =
      'I have some familiarity with container stuff and a bit of exposure to cloud basics';
    const r = assessDefense('k8s', 'ran EKS daily for 3 years', hedged);
    expect(r.understood).toBe(false);
  });

  it('rejects a substantive defense that still hedges (the raised bar is explicit)', () => {
    /* Digit+context would pass classifyAnswer alone — the local hedge
       list fails it anyway. Defenses are held to a higher bar. */
    const hedgedSubstantive =
      'I ran EKS for 5 years with some exposure to upgrades, sort of';
    const r = assessDefense('k8s', 'ran EKS daily for 3 years', hedgedSubstantive);
    expect(r.understood).toBe(false);
    expect(r.note).toContain('no detail');
  });

  it('score stays in 0-100 and is deterministic', () => {
    const r1 = assessDefense('years', '9 years', good);
    const r2 = assessDefense('years', '9 years', good);
    expect(r1).toEqual(r2);
    expect(r1.score).toBeGreaterThanOrEqual(0);
    expect(r1.score).toBeLessThanOrEqual(100);
  });
});

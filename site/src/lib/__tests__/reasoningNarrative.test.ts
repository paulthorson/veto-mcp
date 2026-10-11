/* Unit tests for buildReasoningNarrative (Chakra feature A).
 * Pure-function tests: all-specific, all-vague, mixed, empty, and
 * with/without JobContext. Determinism is asserted by calling the
 * builder twice and deep-comparing. */
import { describe, expect, it } from 'vitest';
import { buildReasoningNarrative } from '../reasoningNarrative';
import type { FullAnswer } from '../demoGrill';
import type { JobContext, ReasoningNarrative } from '../chakraTypes';

/* Same quick-pick answers the E2E drives through the page. */
const ALL_SPECIFIC: FullAnswer[] = [
  { qid: 'years', text: '10+', cls: 'specific' },
  { qid: 'k8s', text: 'Production daily', cls: 'specific' },
  { qid: 'scale', text: '100M+ req/day', cls: 'specific' },
  { qid: 'logistics', text: 'US authorized + NYC hybrid ok', cls: 'specific' },
  { qid: 'motivation', text: 'The payments-scale problem is exactly my thing', cls: 'specific' },
];

const ALL_VAGUE: FullAnswer[] = [
  { qid: 'years', text: 'some experience', cls: 'vague' },
  { qid: 'k8s', text: 'I have some familiarity with it', cls: 'vague' },
  { qid: 'scale', text: "Don't track that", cls: 'vague' },
  { qid: 'logistics', text: 'a bit complicated', cls: 'vague' },
  { qid: 'motivation', text: 'it seems like a great opportunity', cls: 'vague' },
];

const MIXED: FullAnswer[] = [
  { qid: 'years', text: '9 years', cls: 'specific' },
  { qid: 'k8s', text: 'Homelab only', cls: 'specific' },
  { qid: 'scale', text: "Don't track that", cls: 'vague' },
  { qid: 'logistics', text: 'US authorized + NYC hybrid ok', cls: 'specific' },
  { qid: 'motivation', text: 'it seems like a great opportunity', cls: 'vague' },
];

const JOB: JobContext = {
  title: 'Staff Backend Engineer',
  company: 'Acme Fintech',
  rawText: 'Staff Backend Engineer. Requirements: 8+ years backend, Kubernetes in production, 100M req/day scale.',
  requirements: ['8+ years backend', 'Kubernetes in production', '100M req/day scale'],
  roleKeywords: ['backend', 'kubernetes', 'scale'],
  source: 'paste',
};

const UNRELATED_JOB: JobContext = {
  ...JOB,
  requirements: ['embedded Rust', 'CAN bus'],
};

function sentenceCount(s: string): number {
  /* Sentence terminators followed by a space or end of string. */
  return (s.match(/[.!?](\s|$)/g) ?? []).length;
}

describe('buildReasoningNarrative', () => {
  it('is deterministic: same answers in -> same narrative out', () => {
    for (const answers of [ALL_SPECIFIC, ALL_VAGUE, MIXED, []]) {
      const a = buildReasoningNarrative(answers);
      const b = buildReasoningNarrative(answers);
      expect(a).toEqual(b);
    }
    expect(buildReasoningNarrative(MIXED, JOB)).toEqual(buildReasoningNarrative(MIXED, JOB));
  });

  it('all-specific: summary reads confident, per-answer covers all five in order', () => {
    const n: ReasoningNarrative = buildReasoningNarrative(ALL_SPECIFIC);
    expect(n.summary).toContain('every question head-on');
    expect(sentenceCount(n.summary)).toBeGreaterThanOrEqual(2);
    expect(n.perAnswer).toHaveLength(5);
    expect(n.perAnswer.map((p) => p.qid)).toEqual(['years', 'k8s', 'scale', 'logistics', 'motivation']);
    for (const p of n.perAnswer) {
      expect(p.narrative.endsWith('.')).toBe(true);
      expect(sentenceCount(p.narrative)).toBe(1);
    }
  });

  it('all-specific: narratives reference the actual answer content', () => {
    const n = buildReasoningNarrative(ALL_SPECIFIC);
    expect(n.perAnswer[0].narrative).toContain('10+');
    expect(n.perAnswer[1].narrative).toContain('Production daily');
    expect(n.perAnswer[2].narrative).toContain('100M+ req/day');
    expect(n.perAnswer[3].narrative).toContain('US authorized + NYC hybrid ok');
    expect(n.perAnswer[4].narrative).toContain('payments-scale problem');
  });

  it('all-vague: summary calls out the full dodge', () => {
    const n = buildReasoningNarrative(ALL_VAGUE);
    expect(n.summary).toContain('dodged the whole grill');
    expect(n.perAnswer).toHaveLength(5);
    expect(n.perAnswer[1].narrative).toContain('some familiarity');
    expect(n.perAnswer[4].narrative).toContain('pitch instead of a reason');
    for (const p of n.perAnswer) {
      expect(p.narrative.endsWith('.')).toBe(true);
      expect(sentenceCount(p.narrative)).toBe(1);
    }
  });

  it('mixed: summary names what was answered and what was dodged', () => {
    const n = buildReasoningNarrative(MIXED);
    expect(n.summary).toContain('3 for 5');
    expect(n.summary).toContain('scale');
    expect(n.summary).toContain('motivation');
    expect(n.perAnswer[2].narrative).toContain("nothing checkable");
    expect(n.perAnswer[4].narrative).toContain('pitch instead of a reason');
  });

  it('empty: no per-answer entries, summary says there is nothing to read', () => {
    const n = buildReasoningNarrative([]);
    expect(n.perAnswer).toEqual([]);
    expect(n.summary).toContain('No answers came back');
  });

  it('with JobContext: k8s answer ties to the posting requirement', () => {
    const withJob = buildReasoningNarrative(ALL_SPECIFIC, JOB);
    expect(withJob.perAnswer[1].narrative).toContain('Kubernetes in production');
    expect(withJob.perAnswer[1].narrative).toContain("posting's");
    expect(sentenceCount(withJob.perAnswer[1].narrative)).toBe(1);
    expect(withJob.summary).toContain('speaks to the posting');
    expect(withJob.summary).toContain('Kubernetes in production');
    expect(withJob.summary).not.toContain('maps directly');
    expect(withJob.perAnswer[1].narrative).toContain('speaks to the posting');
    expect(withJob.perAnswer[1].narrative).not.toContain('maps directly');
  });

  it('with JobContext but no matching requirement: no tie-in is forced', () => {
    const n = buildReasoningNarrative(ALL_SPECIFIC, UNRELATED_JOB);
    for (const p of n.perAnswer) expect(p.narrative).not.toContain("posting's");
    expect(n.summary).not.toContain('speaks to the posting');
  });

  it('without JobContext: no job language leaks in', () => {
    const n = buildReasoningNarrative(ALL_SPECIFIC);
    for (const p of n.perAnswer) expect(p.narrative).not.toContain('posting');
    expect(n.summary).not.toContain('posting');
  });
});

describe('job tie-in affirmative-stance gate', () => {
  /* The tie-in must never claim a requirement match for a negation or a
     dodge — only affirmative stances (specific + non-negative) qualify. */

  it('k8s "none" stance: no tie-in even when the keyword overlaps', () => {
    /* 'Kubernetes in production' shares the word 'kubernetes' with the
       answer, but the answer states a gap — no match may be claimed. */
    const answers: FullAnswer[] = [
      { qid: 'years', text: 'some experience', cls: 'vague' },
      { qid: 'k8s', text: 'I have no Kubernetes experience', cls: 'specific' },
      { qid: 'scale', text: "Don't track that", cls: 'vague' },
    ];
    const n = buildReasoningNarrative(answers, JOB);
    expect(n.perAnswer[1].narrative).toContain('clean no');
    expect(n.perAnswer[1].narrative).not.toContain("posting's");
    expect(n.summary).not.toContain('speaks to the posting');
  });

  it('k8s homelab stance: honest gap, no production-requirement tie-in', () => {
    const answers: FullAnswer[] = [
      { qid: 'k8s', text: 'Homelab only', cls: 'specific' },
    ];
    const n = buildReasoningNarrative(answers, JOB);
    expect(n.perAnswer[0].narrative).toContain('honest gap');
    expect(n.perAnswer[0].narrative).not.toContain("posting's");
  });

  it("logistics auth='no': no tie-in even when 'authorization' overlaps", () => {
    const authJob: JobContext = {
      ...JOB,
      requirements: ['US work authorization'],
    };
    const answers: FullAnswer[] = [
      { qid: 'logistics', text: 'No US authorization', cls: 'specific' },
    ];
    const n = buildReasoningNarrative(answers, authJob);
    expect(n.perAnswer[0].narrative).toContain('clean no closes the loop');
    expect(n.perAnswer[0].narrative).not.toContain("posting's");
    expect(n.summary).not.toContain('speaks to the posting');
  });

  it("logistics auth='yes' but nyc='no': ruled-out location is a negation", () => {
    const hybridJob: JobContext = {
      ...JOB,
      requirements: ['US authorized'],
    };
    const answers: FullAnswer[] = [
      { qid: 'logistics', text: 'US authorized, remote only', cls: 'specific' },
    ];
    const n = buildReasoningNarrative(answers, hybridJob);
    expect(n.perAnswer[0].narrative).toContain('left the NYC part loose');
    expect(n.perAnswer[0].narrative).not.toContain("posting's");
  });

  it('logistics auth=yes + nyc=yes: affirmative, tie-in fires', () => {
    const hybridJob: JobContext = {
      ...JOB,
      requirements: ['US authorized'],
    };
    const n = buildReasoningNarrative(ALL_SPECIFIC, hybridJob);
    expect(n.perAnswer[3].narrative).toContain("posting's");
    expect(n.perAnswer[3].narrative).toContain('US authorized');
  });

  it('years specific without a parseable number: still affirmative, tie-in fires', () => {
    const answers: FullAnswer[] = [
      { qid: 'years', text: 'Many years of backend work', cls: 'specific' },
    ];
    const n = buildReasoningNarrative(answers, JOB);
    /* The no-number branch (commits without digits), not the number branch. */
    expect(n.perAnswer[0].narrative).toContain('gave a direct answer on experience');
    expect(n.perAnswer[0].narrative).not.toContain('straight away');
    expect(n.perAnswer[0].narrative).toContain("posting's");
    expect(n.perAnswer[0].narrative).toContain('8+ years backend');
  });

  it('genericNarrative fallback: unknown qids still get narratives and gated tie-ins', () => {
    const cultureJob: JobContext = { ...JOB, requirements: ['culture fit'] };
    const specific = buildReasoningNarrative(
      [{ qid: 'culture', text: 'I fit the culture well here', cls: 'specific' }],
      cultureJob,
    );
    expect(specific.perAnswer[0].narrative).toContain('On culture they answered directly');
    expect(specific.perAnswer[0].narrative).toContain("posting's");
    const vague = buildReasoningNarrative(
      [{ qid: 'culture', text: 'whatever', cls: 'vague' }],
      cultureJob,
    );
    expect(vague.perAnswer[0].narrative).toContain('On culture they dodged');
    expect(vague.perAnswer[0].narrative).not.toContain("posting's");
  });

  it('snippets truncate beyond 48 chars with an ellipsis', () => {
    const long =
      '10+ years of backend experience at a large fintech company, mostly payments';
    expect(long.length).toBeGreaterThan(48);
    const n = buildReasoningNarrative([{ qid: 'years', text: long, cls: 'specific' }]);
    expect(n.perAnswer[0].narrative).toContain('…');
    expect(n.perAnswer[0].narrative).not.toContain('mostly payments');
  });
});

describe('negation-tie-in regression: negations and fuzzy logistics never get a tie-in', () => {
  /* Blind re-review 2026-10-11: these three paths still produced false
     tie-ins. The gate invariant is that only an affirmative stance —
     specific, and with no negation marker — may claim a requirement. */

  it('years negation "I have zero years of backend experience": no tie-in', () => {
    /* 'years' and 'backend' both overlap '8+ years backend', so the
       old default branch (specific -> affirmative) claimed the match. */
    const answers: FullAnswer[] = [
      { qid: 'years', text: 'I have zero years of backend experience', cls: 'specific' },
    ];
    const n = buildReasoningNarrative(answers, JOB);
    expect(n.perAnswer).toHaveLength(1);
    expect(n.perAnswer[0].narrative).not.toContain("posting's");
    expect(n.perAnswer[0].narrative).toContain('zero years of backend experience');
    expect(n.summary).not.toContain('speaks to the posting');
    expect(sentenceCount(n.perAnswer[0].narrative)).toBe(1);
  });

  it('motivation negation "I do not want a backend engineering role": no tie-in', () => {
    /* 'backend' overlaps '8+ years backend', so the old default branch
       claimed the match even though the answer rejects the role. */
    const answers: FullAnswer[] = [
      { qid: 'motivation', text: 'I do not want a backend engineering role', cls: 'specific' },
    ];
    const n = buildReasoningNarrative(answers, JOB);
    expect(n.perAnswer).toHaveLength(1);
    expect(n.perAnswer[0].narrative).not.toContain("posting's");
    expect(n.perAnswer[0].narrative).toContain('do not want a backend engineering role');
    expect(n.summary).not.toContain('speaks to the posting');
    expect(sentenceCount(n.perAnswer[0].narrative)).toBe(1);
  });

  it('curly-apostrophe negation "I don\u2019t have any backend years" (U+2019): no tie-in', () => {
    /* Phones and dictation emit U+2019, not ASCII '. The raw text
       bypassed NEGATION_RE entirely, so the years gap got a false
       tie-in on the '8+ years backend' overlap. */
    const answers: FullAnswer[] = [
      { qid: 'years', text: 'I don\u2019t have any backend years', cls: 'specific' },
    ];
    const n = buildReasoningNarrative(answers, JOB);
    expect(n.perAnswer).toHaveLength(1);
    expect(n.perAnswer[0].narrative).not.toContain("posting's");
    expect(n.perAnswer[0].narrative).toContain('don\u2019t have any backend years');
    expect(n.summary).not.toContain('speaks to the posting');
    expect(sentenceCount(n.perAnswer[0].narrative)).toBe(1);
  });

  it("k8s prod stance with negation 'Production daily, but I don\u2019t run on-call': guard holds, no tie-in", () => {
    /* The k8s affirmative branch requires prod AND no negation. This
       pins the guard itself: parseK8s sees 'prod', hasNegation sees
       the curly-apostrophe negation, so the tie-in must be withheld
       even though 'production' overlaps 'Kubernetes in production'. */
    const answers: FullAnswer[] = [
      { qid: 'k8s', text: 'Production daily, but I don\u2019t run on-call', cls: 'specific' },
    ];
    const n = buildReasoningNarrative(answers, JOB);
    expect(n.perAnswer).toHaveLength(1);
    expect(n.perAnswer[0].narrative).not.toContain("posting's");
    expect(n.perAnswer[0].narrative).toContain('don\u2019t run on-call');
    expect(n.summary).not.toContain('speaks to the posting');
    expect(sentenceCount(n.perAnswer[0].narrative)).toBe(1);
  });

  it("logistics unclear auth 'Paperwork in progress, NYC area': no tie-in", () => {
    /* "Paperwork" contains "work", so the 4-char heuristic matches 'US
       work authorization' — but fuzzy authorization contradicts the
       tie-in claim, so it must be withheld. */
    const authJob: JobContext = {
      ...JOB,
      requirements: ['US work authorization'],
    };
    const answers: FullAnswer[] = [
      { qid: 'logistics', text: 'Paperwork in progress, NYC area', cls: 'specific' },
    ];
    const n = buildReasoningNarrative(answers, authJob);
    expect(n.perAnswer).toHaveLength(1);
    expect(n.perAnswer[0].narrative).toContain('went fuzzy');
    expect(n.perAnswer[0].narrative).not.toContain("posting's");
    expect(n.summary).not.toContain('speaks to the posting');
    expect(sentenceCount(n.perAnswer[0].narrative)).toBe(1);
  });

  it('softened tie-in wording: "speaks to the posting", never "maps directly"', () => {
    /* The 4-char substring heuristic does not support "maps directly" —
       the wording must match the mechanism's evidence strength. */
    const n = buildReasoningNarrative(ALL_SPECIFIC, JOB);
    expect(n.summary).toContain('speaks to the posting');
    expect(n.summary).not.toContain('maps directly');
    for (const p of n.perAnswer) {
      expect(p.narrative).not.toContain('maps directly');
    }
    /* At least one per-answer tie-in still fires in the affirmative
       case, using the softened wording. */
    expect(n.perAnswer.some((p) => p.narrative.includes('speaks to the posting'))).toBe(true);
  });
});

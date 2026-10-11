/* Feature G unit tests: scoreResumeMatch, gapsToDrills, resolveQid.
 * Deterministic — same input always yields the same output.
 * Test resumes are fictional; no real people, no real companies.
 */
import { describe, expect, it } from 'vitest';
import {
  scoreResumeMatch,
  gapsToDrills,
  resolveQid,
} from '../resumeMatch';
import type { JobContext, ResumeMatch } from '../chakraTypes';

const jobWith = (roleKeywords: string[]): JobContext => ({
  title: 'Senior Platform Engineer',
  company: 'Acme Widgets',
  rawText: '',
  requirements: [],
  roleKeywords,
  source: 'paste',
});

const JOB_KEYWORDS = [
  'years',
  'experience',
  'backend',
  'kubernetes',
  'terraform',
  'python',
  'kafka',
  'aws',
  'scale',
];

const STRONG_RESUME = `Jordan Rivera — Backend Engineer

6 years of backend engineering experience building production services.
- Kubernetes on EKS: 40 services, daily deploys, Helm charts
- Terraform modules for all cloud infrastructure
- Python for fleet services, Kafka consumers at scale
- AWS in production for five years`;

const WEAK_RESUME = `Jordan Rivera — Backend Engineer

2 years of backend engineering experience.
- Python scripts for internal tooling`;

const keywordJob = () => jobWith(JOB_KEYWORDS);

describe('scoreResumeMatch', () => {
  it('scores a strong resume high and names every matched keyword', () => {
    const match = scoreResumeMatch(STRONG_RESUME, keywordJob());
    expect(match.score).toBe(100);
    expect(match.matchedKeywords).toEqual(JOB_KEYWORDS);
    expect(match.missingKeywords).toEqual([]);
    expect(match.gaps).toEqual([]);
  });

  it('scores a weak resume low and names the gaps in plain English', () => {
    const match = scoreResumeMatch(WEAK_RESUME, keywordJob());
    expect(match.matchedKeywords).toEqual(['years', 'experience', 'backend', 'python']);
    expect(match.missingKeywords).toEqual(['kubernetes', 'terraform', 'kafka', 'aws', 'scale']);
    expect(match.score).toBe(Math.round((100 * 4) / 9));
    expect(match.gaps[0]).toBe("Resume doesn't mention kubernetes; the posting asks for it.");
    expect(match.gaps[1]).toBe("Resume doesn't mention terraform; the posting asks for it.");
  });

  it('caps gap statements at 5', () => {
    const match = scoreResumeMatch('I like turtles.', jobWith([
      'kubernetes', 'terraform', 'kafka', 'aws', 'gcp',
      'docker', 'helm', 'prometheus',
    ]));
    expect(match.missingKeywords).toHaveLength(8);
    expect(match.gaps).toHaveLength(5);
    expect(match.score).toBe(0);
  });

  it('never throws on empty resume input — score 0, one plain gap', () => {
    for (const bad of ['', '   ', '\n\n  \n']) {
      const match = scoreResumeMatch(bad, keywordJob());
      expect(match.score).toBe(0);
      expect(match.matchedKeywords).toEqual([]);
      expect(match.missingKeywords).toEqual([]);
      expect(match.gaps).toEqual(['No resume text provided']);
    }
  });

  it('never throws on a posting with no extractable keywords — score 0', () => {
    const match = scoreResumeMatch(STRONG_RESUME, jobWith([]));
    expect(match.score).toBe(0);
    expect(match.gaps).toEqual(['The posting yielded no extractable keywords']);
  });

  it('never throws on empty resume AND empty keywords', () => {
    const match = scoreResumeMatch('', jobWith([]));
    expect(match.score).toBe(0);
    expect(match.gaps).toEqual(['No resume text provided']);
  });

  it('is deterministic — same input, byte-identical output', () => {
    const first = scoreResumeMatch(WEAK_RESUME, keywordJob());
    for (let i = 0; i < 3; i++) {
      expect(scoreResumeMatch(WEAK_RESUME, keywordJob())).toEqual(first);
    }
    expect(JSON.stringify(scoreResumeMatch(STRONG_RESUME, keywordJob())))
      .toBe(JSON.stringify(scoreResumeMatch(STRONG_RESUME, keywordJob())));
  });

  it('matches case-insensitively with word boundaries: JavaScript is not Java', () => {
    const match = scoreResumeMatch(
      'JavaScript and TypeScript for frontend work; React daily.',
      jobWith(['javascript', 'typescript', 'react', 'java']),
    );
    expect(match.matchedKeywords).toEqual(['javascript', 'typescript', 'react']);
    expect(match.missingKeywords).toEqual(['java']);
    expect(match.score).toBe(75);
  });

  it('matches "java" when it appears as its own word', () => {
    const match = scoreResumeMatch(
      'Java and JavaScript: 4 years of each.',
      jobWith(['java', 'javascript']),
    );
    expect(match.matchedKeywords).toEqual(['java', 'javascript']);
    expect(match.score).toBe(100);
  });

  it('score stays within 0–100 and is an integer', () => {
    const match = scoreResumeMatch(WEAK_RESUME, keywordJob());
    expect(Number.isInteger(match.score)).toBe(true);
    expect(match.score).toBeGreaterThanOrEqual(0);
    expect(match.score).toBeLessThanOrEqual(100);
  });
});

describe('resolveQid', () => {
  it('maps infra keywords to the k8s drill', () => {
    for (const kw of ['kubernetes', 'terraform', 'docker', 'aws', 'eks', 'helm']) {
      expect(resolveQid(kw)).toBe('k8s');
    }
  });

  it('maps throughput/data keywords to the scale drill', () => {
    for (const kw of ['kafka', 'postgres', 'redis', 'scale', 'prometheus']) {
      expect(resolveQid(kw)).toBe('scale');
    }
  });

  it('maps experience/seniority keywords to the years drill', () => {
    for (const kw of ['years', 'experience', 'senior', 'backend', 'leadership']) {
      expect(resolveQid(kw)).toBe('years');
    }
  });

  it('maps languages and frameworks to motivation — python is not infrastructure', () => {
    for (const kw of ['python', 'react', 'typescript', 'django', 'rust']) {
      expect(resolveQid(kw)).toBe('motivation');
    }
    expect(resolveQid('python')).not.toBe('k8s');
  });

  it('maps unknown infra-ish keywords to k8s, everything else to motivation', () => {
    expect(resolveQid('cloudformation')).toBe('k8s');
    expect(resolveQid('fintech')).toBe('motivation');
    expect(resolveQid('')).toBe('motivation');
  });
});

describe('gapsToDrills', () => {
  it('maps missing keywords to drill topics, deduped, in keyword order', () => {
    const match: ResumeMatch = {
      score: 33,
      matchedKeywords: ['years', 'experience', 'backend'],
      missingKeywords: ['kubernetes', 'terraform', 'kafka', 'python'],
      gaps: [],
    };
    // 'python' is not infrastructure: it maps to 'motivation'. The 'k8s'
    // hit from kubernetes+terraform collapses to one drill topic.
    expect(gapsToDrills(match)).toEqual(['k8s', 'scale', 'motivation']);
  });

  it('returns no drills when nothing is missing', () => {
    const match = scoreResumeMatch(STRONG_RESUME, keywordJob());
    expect(gapsToDrills(match)).toEqual([]);
  });

  it('is deterministic', () => {
    const match = scoreResumeMatch(WEAK_RESUME, keywordJob());
    expect(gapsToDrills(match)).toEqual(gapsToDrills(match));
    // kubernetes+terraform -> k8s, kafka -> scale, aws -> k8s (deduped), python is matched so not a drill
    expect(gapsToDrills(match)).toEqual(['k8s', 'scale']);
  });
});

describe('review rework: substring-fallback hardening (F1/F2)', () => {
  it("'go' routes to motivation, not scale (no mongodb substring trip)", () => {
    expect(resolveQid('go')).toBe('motivation');
  });

  it("single letters route to motivation, not years (no 'experience' trip)", () => {
    expect(resolveQid('c')).toBe('motivation');
    expect(resolveQid('r')).toBe('motivation');
  });

  it("'props' does not trip the ops infra hint", () => {
    expect(resolveQid('props')).toBe('motivation');
  });

  it('compound keywords still resolve via whole tokens', () => {
    expect(resolveQid('senior backend engineer')).toBe('years');
    expect(resolveQid('fullstack developer')).toBe('years');
    expect(resolveQid('infrastructure as code')).toBe('k8s');
  });

  it('genuine infra-ish unknowns still route to k8s', () => {
    expect(resolveQid('platform engineering')).toBe('k8s');
    expect(resolveQid('deployment automation')).toBe('k8s');
  });
});

describe('review rework: matching and robustness (F3/F4)', () => {
  it('special-char keywords match literally (C++, .NET, CI/CD)', () => {
    const job = jobWith(['c++', '.net', 'ci/cd']);
    const resume = 'C++ for ten years, .NET services, CI/CD with GitHub Actions';
    const r = scoreResumeMatch(resume, job);
    expect(r.matchedKeywords).toEqual(['c++', '.net', 'ci/cd']);
    expect(r.score).toBe(100);
  });

  it('never throws on null/undefined job or resume', () => {
    expect(() => scoreResumeMatch(null as any, null as any)).not.toThrow();
    expect(() => scoreResumeMatch(undefined as any, undefined as any)).not.toThrow();
    const r = scoreResumeMatch(null as any, null as any);
    expect(r.score).toBe(0);
    expect(r.gaps).toEqual(['No resume text provided']);
  });

  it('duplicate keywords are deduped: no duplicate gaps', () => {
    const job = jobWith(['python', 'python', 'PYTHON']);
    const r = scoreResumeMatch('java developer', job);
    expect(r.missingKeywords).toEqual(['python']);
    expect(r.gaps).toHaveLength(1);
  });

  it('gapsToDrills output is always a subset of FULL_QUESTIONS ids', async () => {
    const { FULL_QUESTIONS } = await import('../demoGrill');
    const ids: Set<string> = new Set(FULL_QUESTIONS.map((q) => q.id));
    const probes = ['go', 'c++', 'kubernetes', 'python', 'kafka', 'fintech', 'props', 'xyzzy'];
    for (const kw of probes) {
      const match: ResumeMatch = { score: 0, matchedKeywords: [], missingKeywords: [kw], gaps: [] };
      for (const drill of gapsToDrills(match)) {
        expect(ids.has(drill)).toBe(true);
      }
    }
  });
});

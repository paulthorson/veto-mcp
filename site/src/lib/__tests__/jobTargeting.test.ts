/* Feature E unit tests: parseJobPosting, tailorQuestions, jobFitNote.
 * Deterministic — same input always yields the same output.
 * Test postings use fictional companies (Acme Robotics, Brightline Labs).
 */
import { describe, expect, it } from 'vitest';
import {
  parseJobPosting,
  tailorQuestions,
  jobFitNote,
} from '../jobTargeting';
import { FULL_QUESTIONS, type FullAnswer } from '../demoGrill';

const ROBOTICS_POSTING = `Senior Platform Engineer

Acme Robotics builds autonomous warehouse robots. We are hiring for our fleet team.

Company: Acme Robotics

Requirements:
- 8+ years of backend engineering experience
- Kubernetes in production (EKS)
- Python for fleet services; Go a plus
- Terraform and AWS for our cloud
- Kafka at scale`;

const WEB_POSTING = `Backend Engineer (Python)

Join us at Brightline Labs to build our data platform.

Requirements:
- 5+ years of Python experience
- React for internal dashboards
- Postgres in production`;

const byId = (arr: { qid: string; text: string }[], qid: string) =>
  arr.find((q) => q.qid === qid)!.text;

describe('parseJobPosting', () => {
  it('extracts title, company, requirements, and role keywords', () => {
    const job = parseJobPosting(ROBOTICS_POSTING);
    expect(job.title).toBe('Senior Platform Engineer');
    expect(job.company).toBe('Acme Robotics');
    expect(job.requirements).toContain('8+ years of backend engineering experience');
    expect(job.requirements.length).toBeGreaterThanOrEqual(5);
    expect(job.requirements.length).toBeLessThanOrEqual(8);
    expect(job.roleKeywords).toContain('python');
    expect(job.roleKeywords).toContain('kubernetes');
    expect(job.roleKeywords).toContain('terraform');
    expect(job.roleKeywords).toContain('aws');
    expect(job.roleKeywords).toContain('kafka');
    expect(job.rawText.length).toBeLessThanOrEqual(2000);
    expect(job.source).toBe('paste');
    // roleKeywords are unique and lowercase
    expect(new Set(job.roleKeywords).size).toBe(job.roleKeywords.length);
    expect(job.roleKeywords.every((k) => k === k.toLowerCase())).toBe(true);
  });

  it('finds the company via the "at <Name>" pattern', () => {
    const job = parseJobPosting(WEB_POSTING);
    expect(job.title).toBe('Backend Engineer (Python)');
    expect(job.company).toBe('Brightline Labs');
  });

  it('truncates long titles and raw text', () => {
    const job = parseJobPosting(`${'A'.repeat(200)}\n- Python required`);
    expect(job.title.length).toBeLessThanOrEqual(80);
    expect(job.rawText.length).toBeLessThanOrEqual(2000);
  });

  it('never throws on empty / whitespace input, yielding the neutral context', () => {
    for (const bad of ['', '   ', '\n\n  \n']) {
      const job = parseJobPosting(bad);
      expect(job.title).toBe('Pasted role');
      expect(job.company).toBe('the posting');
      expect(job.requirements).toEqual([]);
      expect(job.roleKeywords).toEqual([]);
      expect(job.source).toBe('paste');
    }
  });

  it('never throws on garbage input, best-effort parsing the first line as title', () => {
    for (const bad of ['...', 'n/a', '???']) {
      const job = parseJobPosting(bad);
      expect(typeof job.title).toBe('string');
      expect(job.source).toBe('paste');
    }
  });

  it('is deterministic', () => {
    expect(parseJobPosting(ROBOTICS_POSTING)).toEqual(parseJobPosting(ROBOTICS_POSTING));
    expect(parseJobPosting(WEB_POSTING)).toEqual(parseJobPosting(WEB_POSTING));
  });
});

describe('tailorQuestions', () => {
  it('references the years ask in the years question', () => {
    const job = parseJobPosting(ROBOTICS_POSTING);
    const years = byId(tailorQuestions(job), 'years');
    expect(years).toContain('8+');
    expect(years).toContain('Acme Robotics');
  });

  it('re-points the k8s question at the job’s actual stack', () => {
    const robotics = byId(tailorQuestions(parseJobPosting(ROBOTICS_POSTING)), 'k8s');
    expect(robotics).toContain('Kubernetes');
    expect(robotics).not.toBe(FULL_QUESTIONS.find((q) => q.id === 'k8s')!.text);

    const web = byId(tailorQuestions(parseJobPosting(WEB_POSTING)), 'k8s');
    expect(web).toContain('Python');
    expect(web).not.toBe(FULL_QUESTIONS.find((q) => q.id === 'k8s')!.text);
  });

  it('references title and company in the motivation question', () => {
    const job = parseJobPosting(ROBOTICS_POSTING);
    const motivation = byId(tailorQuestions(job), 'motivation');
    expect(motivation).toContain('Senior Platform Engineer');
    expect(motivation).toContain('Acme Robotics');
  });

  it('falls back to default text when no relevant requirement exists', () => {
    const job = parseJobPosting('Warehouse associate\n\nNo specific skills listed. Lift boxes.');
    const tailored = tailorQuestions(job);
    const k8s = byId(tailored, 'k8s');
    expect(k8s).toBe(FULL_QUESTIONS.find((q) => q.id === 'k8s')!.text);
    const years = byId(tailored, 'years');
    expect(years).toBe(FULL_QUESTIONS.find((q) => q.id === 'years')!.text);
  });

  it('returns all defaults when no job was fed', () => {
    const tailored = tailorQuestions(parseJobPosting(''));
    for (const q of FULL_QUESTIONS) {
      expect(byId(tailored, q.id)).toBe(q.text);
    }
  });

  it('keeps qid order and is deterministic', () => {
    const job = parseJobPosting(ROBOTICS_POSTING);
    const a = tailorQuestions(job).map((q) => q.qid);
    expect(a).toEqual(['years', 'k8s', 'scale', 'logistics', 'motivation']);
    expect(tailorQuestions(job)).toEqual(tailorQuestions(parseJobPosting(ROBOTICS_POSTING)));
  });

  it('keeps the default motivation text for junk input like "n/a"', () => {
    for (const junk of ['n/a', '???', '...']) {
      const motivation = byId(tailorQuestions(parseJobPosting(junk)), 'motivation');
      expect(motivation).toBe(FULL_QUESTIONS.find((q) => q.id === 'motivation')!.text);
    }
  });

  it('returns all defaults and never throws on null/undefined job', () => {
    for (const job of [null, undefined]) {
      const tailored = tailorQuestions(job);
      expect(tailored.map((q) => q.qid)).toEqual(['years', 'k8s', 'scale', 'logistics', 'motivation']);
      for (const q of FULL_QUESTIONS) {
        expect(byId(tailored, q.id)).toBe(q.text);
      }
    }
  });

  it('does not assume a backend role or repeat "experience" in the tailored years question', () => {
    const years = byId(tailorQuestions(parseJobPosting(ROBOTICS_POSTING)), 'years');
    expect(years.toLowerCase()).not.toContain('backend');
    expect(years.match(/experience/gi)?.length ?? 0).toBe(1);
  });

  it('capitalizes the Microservices display name', () => {
    const posting = `Backend Engineer

Company: Acme Robotics

Requirements:
- Microservices in production
- Python services`;
    const k8s = byId(tailorQuestions(parseJobPosting(posting)), 'k8s');
    expect(k8s).toContain('Microservices');
  });
});

describe('jobFitNote', () => {
  const job = parseJobPosting(ROBOTICS_POSTING);

  const answersFor = (yearsText: string, k8sText: string): FullAnswer[] => [
    { qid: 'years', text: yearsText, cls: 'specific' },
    { qid: 'k8s', text: k8sText, cls: 'specific' },
    { qid: 'scale', text: '50M req/day across 40 nodes', cls: 'specific' },
    { qid: 'logistics', text: 'US citizen, hybrid fine', cls: 'specific' },
    { qid: 'motivation', text: 'I want to work on fleet robots', cls: 'specific' },
  ];

  it('assesses fit against THIS role when the answers meet the bar', () => {
    const note = jobFitNote(
      job,
      answersFor('9 years', 'ran Kubernetes on EKS daily for 3 years; Python fleet services'),
    );
    expect(note).toContain('8+');
    expect(note).toContain('Kubernetes');
    expect(note).toContain('Python');
  });

  it('flags unmet requirements plainly', () => {
    const note = jobFitNote(job, answersFor('4 years', 'homelab only'));
    expect(note).toContain('8+');
    expect(note.toLowerCase()).toContain('under');
  });

  it('references the role even without answers', () => {
    const note = jobFitNote(job, []);
    expect(note).toContain('8+');
  });

  it('falls back gracefully when nothing was fed', () => {
    const note = jobFitNote(parseJobPosting(''), answersFor('9 years', 'ran EKS daily'));
    expect(note.toLowerCase()).toContain('no posting was pasted');
  });

  it('is deterministic and never throws', () => {
    const a = answersFor('9 years', 'ran EKS daily');
    expect(jobFitNote(job, a)).toBe(jobFitNote(job, a));
    expect(() => jobFitNote(job, [])).not.toThrow();
    expect(() => jobFitNote(parseJobPosting(''), [])).not.toThrow();
  });

  it('accepts bare-number and N+ quick-pick answers for the years ask', () => {
    // ROBOTICS_POSTING asks for 8+ years; the demo's quick picks are
    // bare numbers ('3', '5', '8', '10+') with no "years" word.
    const ans = (t: string): FullAnswer[] => [{ qid: 'years', text: t, cls: 'specific' }];
    expect(jobFitNote(job, ans('10+'))).toContain('Matches');
    expect(jobFitNote(job, ans('8'))).toContain('Matches');
    expect(jobFitNote(job, ans('3'))).toContain('Under');
    expect(jobFitNote(job, ans('10+'))).not.toContain('no number in the answer');
  });

  it('does not let "JavaScript" evidence a Java requirement', () => {
    const javaJob = parseJobPosting(`Java Engineer

Company: Acme Robotics

Requirements:
- 3+ years of Java experience`);
    const note = jobFitNote(javaJob, [
      { qid: 'years', text: '5', cls: 'specific' },
      { qid: 'k8s', text: '5 years of JavaScript work', cls: 'specific' },
    ]);
    expect(note).toContain('evidenced');
    expect(note).not.toContain('speak to');
  });

  it('does not let "40 nodes" evidence a Node.js requirement', () => {
    const nodeJob = parseJobPosting(`DevOps Engineer

Company: Acme Robotics

Requirements:
- Node.js in production
- 4+ years of experience`);
    const note = jobFitNote(nodeJob, [
      { qid: 'years', text: '5', cls: 'specific' },
      { qid: 'scale', text: 'cluster ran 40 nodes', cls: 'specific' },
    ]);
    expect(note).toContain('evidenced');
    expect(note).not.toContain('speak to');
  });

  it('treats null/undefined job as no posting, without throwing', () => {
    expect(jobFitNote(null, [])).toContain('No posting was pasted');
    expect(jobFitNote(undefined, [])).toContain('No posting was pasted');
  });
});

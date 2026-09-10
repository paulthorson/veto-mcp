import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'fit-score',
  tag: 'Find · scoring',
  tagVariant: '',
  title: 'KNOW BEFORE YOU APPLY',
  lede: 'match.py scores every posting 0–100 against your profile: skills 50, seniority 15, salary 15, location 15, recency 5. Anything under 40 is vetoed with a concrete reason — before you spend a single minute on it.',
  interactive: 'radar',
  points: [
    {
      icon: 'target',
      tone: '',
      title: 'Weighted, not vibes',
      body: 'Skills carry half the score because skills decide interviews. Seniority, salary, and location split the rest; recency is a 5-point tiebreak. The weights are in the code, not in a prompt.',
    },
    {
      icon: 'x',
      tone: 'red',
      title: 'Veto under 40',
      body: 'A score below 40 blocks the application and says why: "seniority 25 — posting needs 8+ years, profile shows 3." No silent skips, no mystery.',
    },
    {
      icon: 'list',
      tone: '',
      title: 'Ranked shortlist',
      body: 'rank_jobs() returns every posting sorted and annotated, each with its score and the reasons behind it. You review the top of the list, not the whole haystack.',
    },
    {
      icon: 'shield',
      tone: 'red',
      title: 'Deterministic',
      body: 'Same profile, same posting, same score — every time. No LLM in the loop, so the score can never flatter you into a wasted application.',
    },
  ],
  demoTitle: 'Scoring a posting',
  demoLines: [
    { text: '$ veto score job:greenhouse:staff-backend', kind: 'cmd' },
    { text: '+ skills 85/100 (weight 50) — python, k8s, postgres match', kind: 'ok' },
    { text: '+ seniority 80 · salary 75 · location 90 · recency 100', kind: 'info' },
    { text: '+ FIT 84 — no veto trips. Proceed to grill.', kind: 'ok' },
    { text: '$ veto score job:lever:staff-sre', kind: 'cmd' },
    { text: 'X FIT 32 — VETOED: seniority 25, posting needs 8+ yrs, profile shows 3.', kind: 'veto' },
  ],
  limits: [
    'Keyword matching is textual, not semantic — exotic titles can score oddly.',
    'Salary scoring needs a listed range; postings without one score neutral, not zero.',
    'The weights are fixed, not learned — they encode judgment, not your history.',
    'A high score is not a guarantee. It means "worth your time," not "you will get it."',
  ],
  faq: [
    {
      q: 'Can I tune the weights?',
      a: 'Not yet — they are constants in match.py. The ranking is transparent enough that you can read the reasons and apply your own judgment on top.',
    },
    {
      q: 'Does a veto block me from applying manually?',
      a: 'No. Veto blocks the agent. You are a human; the score is advice, the veto is a guardrail for the automation.',
    },
  ],
};

export default spec;

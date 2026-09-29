import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'fit-score',
  tag: 'Find · scoring',
  tagVariant: '',
  title: 'KNOW BEFORE YOU APPLY',
  lede: 'Veto spends your five daily applications only on postings scoring 60+. match.py scores every posting 0–100 against your profile: skills 50, seniority 15, salary 15, location 15, recency 5. Anything under 60 is vetoed with a concrete reason, before you spend a single minute on it.',
  interactive: 'radar',
  points: [
    {
      icon: 'target',
      tone: '',
      title: 'Weighted, not vibes',
      body: 'Skills carry half the score because skills decide interviews. Seniority, salary, and location split 15 points each; recency is a 5-point tiebreak. The weights are constants in match.py, set deliberately, not learned from your history.',
    },
    {
      icon: 'x',
      tone: 'red',
      title: 'Veto under 60',
      body: 'A score below 60 blocks the application and says exactly why: "skill gap: missing rust, tokio required by this posting", pay below your floor, seniority mismatch. No silent skips, no mystery.',
    },
    {
      icon: 'list',
      tone: '',
      title: 'Ranked shortlist',
      body: 'rank_jobs() returns every posting sorted and annotated: score, reasons, matched and missing skills, a veto flag, veto_reason, and per-axis component scores. You review the top of the list, not the whole haystack.',
    },
    {
      icon: 'shield',
      tone: 'red',
      title: 'Deterministic',
      body: 'Same profile, same posting, same score, every time. No LLM in the loop. And neutral when data is absent: no salary listed means the salary axis scores neutrally, not zero; no skill keywords means neutral, not zero.',
    },
  ],
  demoTitle: 'Scoring a posting',
  demoLines: [
    { text: '$ veto score job:greenhouse:staff-backend', kind: 'cmd' },
    { text: '+ skills 85/100 (weight 50): python, k8s, postgres match', kind: 'ok' },
    { text: '+ seniority 80 · salary 75 · location 90 · recency 100', kind: 'info' },
    { text: '+ FIT 84: no veto trips. Proceed to grill.', kind: 'ok' },
    { text: '$ veto score job:lever:staff-sre', kind: 'cmd' },
    { text: 'X FIT 52: VETOED: 8 under the 60 bar: skill gap: missing rust, tokio required by this posting.', kind: 'veto' },
  ],
  limits: [
    'Keyword matching is textual, not semantic, exotic titles can score oddly.',
    'Postings without a listed salary score neutral on salary, not zero, recall-friendly at the cost of precision.',
    'The weights are fixed, not learned, they encode judgment, not your history.',
    'A high score is not a guarantee. It means "worth one of your five slots," not "you will get it."',
  ],
  faq: [
    {
      q: 'Why is the bar 60?',
      a: 'Because you get five applications a day. Each slot is precious, so the bar is "clearly worth one of your five slots" (60+), not "not terrible." A lower bar would let marginal postings burn slots that belonged to better ones.',
    },
    {
      q: 'Can I tune the weights?',
      a: 'They are constants in match.py. Change them deliberately if you want, the code is yours. Either way the ranking stays transparent: read the reasons, apply your own judgment on top.',
    },
    {
      q: 'Does a veto block me from applying manually?',
      a: 'No. Veto blocks the agent. You are a human; the score is advice, the veto is a guardrail for the automation.',
    },
    {
      q: 'What if the posting lists no salary?',
      a: 'It scores neutrally on the salary axis, not zero. Penalizing absent data would punish postings for formatting, not fit.',
    },
    {
      q: 'Why is recency only 5?',
      a: 'Freshness is a tiebreak, not fit. A stale posting that matches you perfectly should outrank a fresh one that does not.',
    },
    {
      q: 'Why deterministic, no LLM?',
      a: 'So the score can never flatter you into a wasted application. Same profile, same posting, same score, every time, and you can reproduce any number by hand.',
    },
  ],
};

export default spec;

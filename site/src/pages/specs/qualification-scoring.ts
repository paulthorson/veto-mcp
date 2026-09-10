import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'qualification-scoring',
  tag: 'Governance',
  tagVariant: 'amber',
  title: 'FIT CHECK',
  lede: 'Required skills and years are extracted from the job description and scored against your profile. \u22650.65 proceeds silently; 0.40\u20130.65 proceeds with a visible qualification_warning; below 0.40, or a severe experience gap, blocks with an explanation.',
  points: [
    {
      icon: 'search',
      tone: 'amber',
      title: 'Extraction',
      body: 'Requirements are pulled from the posting text itself, not the title, not wishful thinking. Skills and years, as stated by the employer.',
    },
    {
      icon: 'check',
      title: '\u22650.65: silent pass',
      body: 'You\u2019re a fit. The application proceeds with no ceremony and no nagging.',
    },
    {
      icon: 'warn',
      tone: 'amber',
      title: '0.40\u20130.65: warned',
      body: 'Proceeds with a visible qualification_warning. Eyes open: you know exactly which requirements you don\u2019t meet.',
    },
    {
      icon: 'x',
      tone: 'red',
      title: '<0.40: refused',
      body: 'Blocked with an explanation. Veto refuses to spend your daily application budget on a role you clearly don\u2019t fit.',
    },
  ],
  demoTitle: 'veto: zsh',
  demoLines: [
    { text: 'cli.py apply job:ashby:12 --resume ~/r.pdf --confirm', kind: 'cmd' },
    { text: '\u2192 requirements: python, k8s, 5+ yrs', kind: 'info' },
    { text: '\u2192 profile match: 0.52', kind: 'info' },
    { text: '\u26A0 qualification_warning: 2 of 3 requirements met', kind: 'warn' },
    { text: '  proceeding: your call, eyes open', kind: 'ok' },
    { text: 'cli.py apply job:lever:staff --resume ~/r.pdf --confirm', kind: 'cmd' },
    { text: '\u2192 profile match: 0.31: severe experience gap', kind: 'warn' },
    { text: '\u2715 BLOCKED: not applying to this one', kind: 'veto' },
  ],
  limits: [
    'Scoring is heuristic. Postings are vague; profiles are incomplete.',
    'Fail-open on framework errors, it warns, never blocks.',
    'Missing profile warns but never blocks. Run the wizard.',
    'It scores the posting, not the team, the comp, or the interview.',
  ],
  faq: [
    {
      q: 'Can I still apply on a warning?',
      a: 'Yes. Warnings inform; they don\u2019t block. A 0.52 with two of three requirements met might be your best shot, the point is you apply knowing the gap, not discovering it in the rejection.',
    },
    {
      q: 'Why did a good role score low?',
      a: 'Usually a thin profile or a keyword-stuffed posting. The fix is almost always the same: beef up the profile with the wizard, especially quantified achievements.',
    },
  ],
};

export default spec;

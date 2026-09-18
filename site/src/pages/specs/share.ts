import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'share',
  tag: 'Share · your progress',
  tagVariant: '',
  title: 'SHOW YOUR WORK. KEEP YOUR DATA.',
  lede: 'Shareable proof of your hunt — score cards, interview plans, progress snapshots — built privacy-first: anything that looks like resume text, a job description, or contact details kills the artifact before it exists. Plus honest onboarding with dark patterns banned by code, and product analytics that stay off until you opt in.',
  points: [
    {
      icon: 'net',
      tone: '',
      title: 'Share cards, scrubbed clean',
      body: 'Score cards, interview plans, and progress snapshots carry a methodology link and a what-is-included block. Every field passes a privacy scan: resume text, JD text, names, or contact details raise ContentDetected and the artifact is never built — then it is deep-frozen and re-scanned at render time.',
    },
    {
      icon: 'check',
      tone: '',
      title: 'Onboarding without dark patterns',
      body: 'Nine paths across a role-maturity × technical-comfort grid, assigned deterministically — never re-randomized. Every path and every line of copy passes check_dark_patterns: false urgency, fake scarcity, and confirm-shaming are banned by code, not by policy paragraph.',
    },
    {
      icon: 'chart',
      tone: '',
      title: 'Analytics off until you opt in',
      body: 'Product analytics default OFF. Opting in records consent with source and timestamp; every event is schema-allowlisted and content-scanned. If anything smuggled-looking is detected, the tripwire shuts analytics off immediately — and they stay off.',
    },
    {
      icon: 'doc',
      tone: '',
      title: 'A changelog that shows the no’s',
      body: 'Shipped, rejected, limited — every entry names the decision, the evidence behind it (a repo path, never an invented reference), and the current limitation. A changelog with no rejected or limited entries is treated as a defect.',
    },
  ],
  demoTitle: 'Building a share card',
  demoLines: [
    { text: '$ python -m initiatives.i12 share score-card --role "platform eng" --score 82 --markdown', kind: 'cmd' },
    { text: '+ privacy scan: clean · scores, factors, counts only', kind: 'ok' },
    { text: '+ artifact frozen · methodology link attached', kind: 'ok' },
    { text: '$ python -m initiatives.i12 share score-card --role "x" # with resume text in a field', kind: 'cmd' },
    { text: '! ContentDetected: artifact refused — raw content never ships', kind: 'warn' },
  ],
  limits: [
    'Share artifacts never embed raw resume or job-description text — only scores, factor names, counts, and short labels you approved.',
    'Analytics measure activation and workflow completion only. They cannot see your resume, your applications, or your messages — the schema has no fields for them.',
    'The tripwire writes the triggering payload to access-controlled quarantine for inspection. Consent changes are audited.',
    'Onboarding experiments measure qualified activation — a completed core workflow — never vanity counts.',
  ],
  faq: [
    {
      q: 'Can I share my fit score publicly?',
      a: 'Yes — the score card carries the score, the factor breakdown, and the methodology link. Your resume, the job description, and your contact details never leave your machine.',
    },
    {
      q: 'What data do you collect about me?',
      a: 'Nothing, unless you opt in — and then only allowlisted event shapes about feature usage. No resume content, no job-search content, ever. The schema rejects anything else before storage.',
    },
  ],
};

export default spec;

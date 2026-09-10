import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'referrals',
  tag: 'Find · warm intros',
  tagVariant: '',
  title: 'WARM BEATS COLD. EVERY TIME.',
  lede: 'referrals.py mines your LinkedIn Connections.csv for insiders at your target companies, matches them by role and seniority, and drafts the outreach. The networking CRM tracks every touch and nudges you before relationships go cold.',
  interactive: 'warm',
  points: [
    {
      icon: 'net',
      tone: '',
      title: 'Target-company matching',
      body: 'Point it at a company; it finds who you know there, what they do, and how senior they are — from your own exported connections, never scraped.',
    },
    {
      icon: 'chat',
      tone: '',
      title: 'Warm and cold drafts',
      body: 'Outreach drafts tuned to the relationship: a genuine warm note for real connections, an honest cold note otherwise. Relationship defaults to "connection" — never inflated.',
    },
    {
      icon: 'ledger',
      tone: '',
      title: 'The CRM nudge list',
      body: 'network_crm.py logs every interaction and ranks who needs attention: 21+ days silent, or a promised follow-up gone overdue. With a suggested next step per contact.',
    },
    {
      icon: 'search',
      tone: 'amber',
      title: 'Warm paths',
      body: 'Ask for a path to a company and it traces 1st- and 2nd-degree routes through your network — who to ask, and who they can introduce you to.',
    },
  ],
  demoTitle: 'Finding a warm path',
  demoLines: [
    { text: '$ veto referrals --company TargetCo --from Connections.csv', kind: 'cmd' },
    { text: '+ 3 insiders found at TargetCo', kind: 'ok' },
    { text: '  Maya R. — platform eng (ex-colleague, 2nd degree)', kind: 'info' },
    { text: '  J. Chen — hiring manager, platform (via Maya)', kind: 'info' },
    { text: '+ warm path: you > Maya R. > J. Chen', kind: 'ok' },
    { text: '+ draft ready: 240 chars, honest, no flattery', kind: 'ok' },
    { text: '! you send it yourself on LinkedIn — Veto never messages anyone', kind: 'warn' },
  ],
  limits: [
    'Reads your exported Connections.csv or manual entries — it does not scrape LinkedIn.',
    'Outreach is drafted only. You send every message yourself, on LinkedIn.',
    'Warm-path tracing is only as complete as your exported network.',
    'It will not invent a relationship you do not have. "Connection" is the honest default.',
  ],
  faq: [
    {
      q: 'How do I get my Connections.csv?',
      a: 'LinkedIn Settings > Data Privacy > Get a copy of your data > Connections. Export, then point referrals at the file. Your data never leaves your machine.',
    },
    {
      q: 'Does it message people for me?',
      a: 'Never. Drafting is the line. The send is always yours — that is what keeps it honest and your account safe.',
    },
  ],
};

export default spec;

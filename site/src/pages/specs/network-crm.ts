import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'network-crm',
  tag: 'Win · relationships',
  tagVariant: '',
  title: 'YOUR NETWORK, WITH A MEMORY',
  lede: 'network_crm.py is a CRM-lite for job seekers: validated contacts, timestamped interactions, warm paths to target companies, and a nudge list ranked by staleness. Referral radar finds the people; the CRM keeps the relationships alive.',
  points: [
    {
      icon: 'ledger',
      tone: '',
      title: 'Contacts with history',
      body: 'Name, company, role, industry, LinkedIn URL (validated), source, notes, plus every interaction logged: intro, call, coffee, email, follow-up with due dates.',
    },
    {
      icon: 'hourglass',
      tone: 'amber',
      title: 'The nudge list',
      body: 'Ranked by staleness: 21+ days of silence, or a promised follow-up gone overdue. Each contact ships with a suggested next step.',
    },
    {
      icon: 'net',
      tone: '',
      title: 'Warm paths to companies',
      body: 'Ask for a target company; it traces routes through your contacts, 1st and 2nd degree, reusing the referral radar\u2019s company matching.',
    },
    {
      icon: 'shield',
      tone: '',
      title: 'Yours alone',
      body: 'network.json lives on your machine. No sync, no cloud, no "growth hacking" your friends.',
    },
  ],
  demoTitle: 'Working the nudge list',
  demoLines: [
    { text: '$ veto network nudges', kind: 'cmd' },
    { text: '! Priya S.: 34 days silent. Last: coffee, "intro to platform team".', kind: 'warn' },
    { text: '  > suggested: thank-you + ask about the platform eng opening', kind: 'info' },
    { text: '! Dana K.: follow-up due 3 days ago (promised: "send resume").', kind: 'warn' },
    { text: '+ warm path to TargetCo: you > Priya S. > J. Chen (hiring mgr)', kind: 'ok' },
  ],
  limits: [
    'Only as complete as what you log, it cannot know about the coffee you forgot to record.',
    'Warm paths trace through your data; a sparse network gives sparse paths.',
    'Nudge timing is a default (21 days), not a science. Adjust it to your relationships.',
    'It reminds; it does not message. Every touch is yours.',
  ],
  faq: [
    {
      q: 'How is this different from referral radar?',
      a: 'Radar finds insiders at target companies from your LinkedIn export. The CRM tracks the relationships over time: touches, promises, staleness.',
    },
    {
      q: 'Where is my data?',
      a: 'network.json in your Veto directory. Back it up like anything else you care about.',
    },
  ],
};

export default spec;

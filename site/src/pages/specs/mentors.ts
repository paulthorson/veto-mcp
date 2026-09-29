import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'mentors',
  tag: 'Train · humans',
  tagVariant: '',
  title: 'FIND SOMEONE WHO HAS DONE IT',
  lede: 'mentors.py matches you with opt-in mentors by industry (40), role (25), topics (25), and availability (10). Weak drill areas trigger recommendations automatically; every match ships with a 30-minute first-session agenda and a sub-300-character intro draft you send yourself.',
  interactive: 'mentors',
  points: [
    {
      icon: 'team',
      tone: '',
      title: 'Deterministic matching',
      body: 'Industry 40, role 25, topics 25, availability 10. No black box. You can read exactly why a mentor matched you.',
    },
    {
      icon: 'target',
      tone: 'amber',
      title: 'Training-triggered recommendations',
      body: 'Bombing negotiation drills? The system suggests mentors strong in negotiation. Your weakest areas route you to humans.',
    },
    {
      icon: 'doc',
      tone: '',
      title: 'First-session agendas',
      body: 'Every match includes a 30-minute agenda and topic-specific prep, so the first call is useful, not awkward.',
    },
    {
      icon: 'shield',
      tone: '',
      title: 'Privacy-first, opt-in',
      body: 'Mentors choose display name or initials, set capacity, and can leave any time. Two-sided ratings keep quality honest.',
    },
  ],
  demoTitle: 'Getting matched',
  demoLines: [
    { text: '$ veto mentors match --topics negotiation --industry fintech', kind: 'cmd' },
    { text: '+ S.K.: staff eng, fintech, 92% (industry + role, 2 levels up)', kind: 'ok' },
    { text: '+ M.R.: eng manager, 84% (matches your weakest area: negotiation)', kind: 'ok' },
    { text: '+ agenda: 30-min first session, topic prep attached', kind: 'ok' },
    { text: '+ intro draft: 238 chars. You send it on LinkedIn: Veto never messages.', kind: 'warn' },
  ],
  limits: [
    'Mentors are opt-in humans with limited capacity, matches depend on who is available.',
    'Veto drafts the intro; the relationship is yours to build. No automation of humans.',
    'Matching is deterministic and explainable, which means it is also blunt.',
    'Two-sided ratings exist to protect both sides, low-effort mentees get rated too.',
  ],
  faq: [
    {
      q: 'Do I have to be technical to get a mentor?',
      a: 'No, industry, role, and topics drive matching. Career switchers match with people who switched.',
    },
    {
      q: 'Can I become a mentor?',
      a: 'Yes, opt in, set your topics, availability, and capacity. Privacy is your choice: name or initials.',
    },
  ],
};

export default spec;

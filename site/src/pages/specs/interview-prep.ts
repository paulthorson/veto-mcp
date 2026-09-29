import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'interview-prep',
  tag: 'Interview prep',
  title: 'KNOW THE ROOM',
  lede: 'Walk in already briefed. Veto researches the company and builds STAR stories from your real achievements, and marks anything it couldn\u2019t verify instead of inventing it.',
  points: [
    {
      icon: 'chat',
      title: 'Briefs, not bios',
      body: 'company_brief researches the company: site, careers page, news. Every field the fetch couldn\u2019t fill is marked "unverified". Funding numbers and headcount are never guessed.',
    },
    {
      icon: 'star',
      title: 'STAR from real wins',
      body: 'prep_interview builds stories only from achievements already in your profile. Metrics are preserved verbatim: "cut p99 by 38%" stays exactly that.',
    },
    {
      icon: 'check',
      title: 'Requirements mapped',
      body: 'The posting\u2019s requirements are pulled into the prep doc, so you know what they\u2019ll probe before they probe it.',
    },
    {
      icon: 'shield',
      title: 'No hallucinations',
      body: 'If web research returns nothing, the brief says so loudly, an honest gap, not a fabricated company.',
    },
  ],
  demoTitle: 'veto: zsh',
  demoLines: [
    { text: 'cli.py company-brief acme-corp', kind: 'cmd' },
    { text: '\u2192 fetching: site, careers page, news\u2026', kind: 'info' },
    { text: '\u2713 brief ready: 2 fields unverified', kind: 'ok' },
    { text: '  funding: unverified (no source found)', kind: 'warn' },
    { text: '  headcount: unverified (no source found)', kind: 'warn' },
    { text: 'cli.py prep-interview job:greenhouse:42', kind: 'cmd' },
    { text: '\u2713 4 STAR stories from your profile', kind: 'ok' },
    { text: '  metrics preserved verbatim: "cut p99 by 38%"', kind: 'info' },
    { text: '  mapped to requirements: python, k8s, on-call', kind: 'info' },
  ],
  limits: [
    'Briefs depend on public web data, thin companies get thin briefs.',
    'prep_interview only knows what\u2019s in your profile. Keep it updated.',
    'Stories are drafts, not scripts. Rehearse them out loud.',
    'No real-time intel, check the news the morning of the call.',
  ],
  faq: [
    {
      q: 'Does it ever invent company facts?',
      a: 'No. Every field is either verified from a fetched source or marked "unverified". If research returns nothing, you get an honest empty brief, not a confident fiction.',
    },
    {
      q: 'Where do the STAR stories come from?',
      a: 'Only from achievements in your saved profile. If a win isn\u2019t in your profile, it can\u2019t become a story, which is also why the wizard asks about quantified results.',
    },
  ],
};

export default spec;

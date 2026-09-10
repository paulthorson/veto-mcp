import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'skill-gaps',
  tag: 'WIN',
  tagVariant: 'amber',
  title: 'Skill-gap planner',
  lede: 'The misses that keep costing you — ranked by how often they appear in the postings you want, each one mapped to the lesson or track that closes it.',
  interactive: 'gaps',
  points: [
    {
      icon: 'chart',
      tone: 'amber',
      title: 'Frequency from your pipeline',
      body: 'Gap counts come from postings you actually saved and scored — not from a generic "hot skills" list.',
    },
    {
      icon: 'box',
      tone: '',
      title: 'Mapped to a fix',
      body: 'Each gap points at a concrete lesson, track, or mock-interview pack. Never just a label.',
    },
    {
      icon: 'check',
      tone: '',
      title: 'One-click close',
      body: 'Mark a gap "got it" and the frequency re-ranks instantly; your streak goal updates to match.',
    },
    {
      icon: 'scan',
      tone: '',
      title: 'Feeds the autopsy',
      body: 'Gaps flow into the rejection autopsy, which cites them when a stage keeps leaking.',
    },
  ],
  demoTitle: '$ veto gaps --role backend-engineer',
  demoLines: [
    { text: '$ veto gaps --role backend-engineer --from saved_jobs', kind: 'cmd' },
    { text: 'GAP FREQUENCY — postings saved last 90 days', kind: 'info' },
    { text: '  68%  Kubernetes (12/18)  -> track: "Cloud + AI infra"', kind: 'warn' },
    { text: '  44%  Terraform (8/18)     -> lesson: IaC for app engineers', kind: 'warn' },
    { text: '  39%  System design depth  -> mock-interview: senior pack', kind: 'info' },
    { text: '$ veto gaps close kubernetes', kind: 'cmd' },
    { text: '+ Added: 6-lesson track "Cloud + AI infra".', kind: 'ok' },
    { text: '+ Streak goal updated: 1 infra lesson / day.', kind: 'ok' },
    { text: 'Gaps come from YOUR saved postings — not a generic list.', kind: 'info' },
  ],
  limits: [
    'Frequency is only as good as your saved-postings sample — save more jobs, get better signal.',
    'Lesson mapping is curated per track; a niche stack may have no mapped lesson yet.',
  ],
  faq: [
    {
      q: 'Where do gap percentages come from?',
      a: 'From the requirements extracted from postings you saved and scored, matched against your profile skills. The denominator is your own pipeline.',
    },
    {
      q: 'Does closing a gap change my fit scores?',
      a: 'Yes — once you mark a skill "got it" and it is on your profile, future scores count it.',
    },
  ],
};

export default spec;

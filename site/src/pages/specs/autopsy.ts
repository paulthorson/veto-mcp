import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'autopsy',
  tag: 'Win · learn',
  tagVariant: 'amber',
  title: 'REJECTIONS ARE DATA',
  lede: 'rejection_autopsy.py records every outcome — rejected, ghosted, offer, withdrawn — at every stage, then finds where your funnel leaks: rejection rate by stage, ghosting rate, time-to-rejection. The diagnosis points at the exact module that fixes it.',
  interactive: 'autopsy',
  points: [
    {
      icon: 'chart',
      tone: '',
      title: 'Funnel leak detection',
      body: 'Rejection rate by stage, ghosting rate, common keywords in your notes, time-to-rejection stats. The leak is usually one stage — now you know which.',
    },
    {
      icon: 'target',
      tone: 'amber',
      title: 'Diagnosis, not blame',
      body: '"60% lost at screening" maps to a fix: run the grill on your resume, tighten tailoring. "Ghosted after finals" maps to the negotiation sim and mock interviews.',
    },
    {
      icon: 'ledger',
      tone: '',
      title: 'Outcome log',
      body: 'Every application\u2019s outcome recorded with stage and notes. The log is the dataset; the autopsy is the query.',
    },
    {
      icon: 'check',
      tone: '',
      title: 'Frank but kind',
      body: 'The copy is direct without being cruel. A 55% screening leak is a resume problem, not a you problem — and resume problems are fixable.',
    },
  ],
  demoTitle: 'Autopsying a month',
  demoLines: [
    { text: '$ veto autopsy', kind: 'cmd' },
    { text: '  applied 40 > screening 18 > interview 9 > final 3 > offer 1', kind: 'info' },
    { text: 'X LEAK: 55% lost at screening', kind: 'veto' },
    { text: '! ghosting rate: 22% (post-interview silence)', kind: 'warn' },
    { text: '+ diagnosis: grill your resume, tighten tailoring, then re-run.', kind: 'ok' },
  ],
  limits: [
    'Needs a real outcome log — ten applications is anecdote, forty is data.',
    'Diagnoses map to Veto modules; problems outside the tool\u2019s reach get named, not solved.',
    'Correlation, not causation: a leak at screening usually means the resume, but not always.',
    'Ghosting stats need honest logging — mark the silence, do not just delete the row.',
  ],
  faq: [
    {
      q: 'What counts as "ghosted"?',
      a: 'You log it. If a thread went silent past the point a reply was owed, record it as ghosted with the stage — the stats need your honesty.',
    },
    {
      q: 'Does it compare me to other users?',
      a: 'No. Your funnel against your history. Nobody else\u2019s data is involved.',
    },
  ],
};

export default spec;

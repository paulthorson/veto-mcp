import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'streaks',
  tag: 'Win · momentum',
  tagVariant: 'red',
  title: 'MAKE THE GRIND ADDICTIVE',
  lede: 'streaks.py gamifies the job hunt: log reps (applications, drills, mock interviews, negotiation rounds, AI lessons, networking touches), set daily goals, keep streaks alive, and export a share card built only from real logged reps. The viral loop, with the honesty contract baked in.',
  interactive: 'streaks',
  points: [
    {
      icon: 'flame',
      tone: 'red',
      title: 'Streaks per habit',
      body: 'Current and longest streaks per rep kind, plus an overall streak. A streak dies only after a full missed day. Today never kills you.',
    },
    {
      icon: 'gauge',
      tone: '',
      title: 'Daily goals',
      body: 'Set your own targets, 3 applications, 2 drills, 1 mock interview, and watch text progress bars fill through the day.',
    },
    {
      icon: 'chart',
      tone: '',
      title: 'Weekly recaps',
      body: 'Totals per kind, streaks gained and lost, and one encouraging line derived from your actual numbers. Empty weeks get an honest nudge, not fake praise.',
    },
    {
      icon: 'star',
      tone: 'amber',
      title: 'Share cards',
      body: 'A Markdown progress card for socials, "12-day drill streak, 20 brutal negotiation rounds", built only from logged reps. Zero reps, zero card. Virality without inflation.',
    },
  ],
  demoTitle: 'Checking today',
  demoLines: [
    { text: '$ veto streaks today', kind: 'cmd' },
    { text: '  drills [##########--] 12-day streak (longest 21)', kind: 'info' },
    { text: '  applications [####------] 2/3', kind: 'info' },
    { text: '  negotiation [##--------] 1/2', kind: 'info' },
    { text: '$ veto streaks card', kind: 'cmd' },
    { text: '+ card built from 47 logged reps. Nothing inflated.', kind: 'ok' },
  ],
  limits: [
    'Reps are self-logged, the system trusts you, which means it only works if you are honest.',
    'Streaks motivate; they do not hire. Do not let the game replace the goal.',
    'Share cards show counts, never private details (no company names, no salaries).',
    'A broken streak is information, not failure. The recap says so.',
  ],
  faq: [
    {
      q: 'What counts as a rep?',
      a: 'Applications, drills, mock interviews, negotiation rounds, AI lessons, networking touches, tailoring sessions. Log what you did; the streaks do the rest.',
    },
    {
      q: 'Can I fake a share card?',
      a: 'The card renders from your log. You could log fake reps, but then you would be lying to yourself on your own machine, which seems like a lot of work.',
    },
  ],
};

export default spec;

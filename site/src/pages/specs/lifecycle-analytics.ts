import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'lifecycle-analytics',
  tag: 'Tracking',
  title: 'THE SCOREBOARD',
  lede: 'Every application carries a pipeline stage \u2014 applied \u2192 interviewing \u2192 offer, plus rejected, withdrawn, and ghosted \u2014 with a full stage_history log. application_analytics turns it into a funnel you can actually learn from.',
  points: [
    {
      icon: 'chart',
      title: 'Pipeline stages',
      body: 'Every entry keeps a stage_history of {stage, at, note} events. Moving to interviewing sets a follow-up reminder 7 days out; terminal stages clear it.',
    },
    {
      icon: 'envelope',
      title: 'Follow-up nudges',
      body: 'Applications due for a check-in surface automatically. Stale ones \u2014 stuck in applied with no movement \u2014 get flagged so nobody falls through the cracks.',
    },
    {
      icon: 'chart',
      title: 'Real analytics',
      body: 'Funnel counts, response rate by board, median days to first response, and the stale list. Know which boards actually convert.',
    },
    {
      icon: 'doc',
      title: 'CSV export',
      body: 'Dump everything to a spreadsheet in one command. Your data stays portable \u2014 no lock-in, no dashboard hostage situations.',
    },
  ],
  demoTitle: 'veto — zsh',
  demoLines: [
    { text: 'cli.py applications', kind: 'cmd' },
    { text: '\u2713 12 applications tracked', kind: 'ok' },
    { text: '  applied: 7 \u00B7 interviewing: 3 \u00B7 offer: 1 \u00B7 ghosted: 1', kind: 'info' },
    { text: 'cli.py analytics', kind: 'cmd' },
    { text: '\u2192 response rate: 33% (best board: greenhouse)', kind: 'ok' },
    { text: '\u2192 median time to response: 6.5 days', kind: 'info' },
    { text: '\u2192 stale: 2 applications need a nudge', kind: 'warn' },
    { text: '\u2192 nudge list: 2 follow-ups due this week', kind: 'warn' },
  ],
  limits: [
    'Analytics are only as good as your tracking \u2014 update stages.',
    '"Ghosted" is a judgment call. Veto flags stale; you decide.',
    'Medians need samples. Tiny pipelines give noisy numbers.',
    'No ATS integration \u2014 stages move via you or the email sync.',
  ],
  faq: [
    {
      q: 'How do stages get updated?',
      a: 'Manually with update_application, or proposed by the email sync when a recruiter reply unambiguously matches an application. Proposals apply only on high-confidence matches.',
    },
    {
      q: 'What counts as stale?',
      a: 'Stuck in applied with no stage movement past the follow-up window. Veto flags them in analytics \u2014 you decide whether to nudge, withdraw, or mark ghosted.',
    },
  ],
};

export default spec;

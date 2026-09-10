import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'drip-queue',
  tag: 'Paced queue',
  tagVariant: '',
  title: 'THE DRIP QUEUE',
  lede: 'Queue up a week of applications and Veto works through them at human pace — max 5 a day, random 2\u20137 minute pauses between each. The whole run is risk-adjudicated before it starts, and anything still waiting on your grill answers stays queued.',
  points: [
    {
      icon: '\u2630',
      tone: '',
      title: 'A real queue, not a vibe',
      body: 'queue-add drops a job into the queue file; queue-list shows what\u2019s pending, due, or done. It persists across restarts and prints a JSON run report — cron-friendly by design.',
    },
    {
      icon: '\u25d4',
      tone: '',
      title: 'Human pace, enforced',
      body: 'Max 5 applications per day across all boards, with a randomized 2\u20137 minute pause between each. Not a suggestion — the compliance gate stops the run at the cap with cap_reached.',
    },
    {
      icon: '\u26e8',
      tone: 'red',
      title: 'Adjudicated before it starts',
      body: 'The entire run goes through the risk policy first. If policy says no, the run stops immediately with risk_blocked and nothing is attempted. Fail closed, always.',
    },
    {
      icon: '?',
      tone: 'amber',
      title: 'Grill-aware',
      body: 'Items still waiting on an incomplete grill report grill_pending and stay in the queue — never counted as applied, never skipped silently. Answer the grill and the next run picks them up.',
    },
  ],
  demoTitle: 'A queued morning run',
  demoLines: [
    { text: 'cli.py queue-add job:greenhouse:a1 --resume ~/resume.pdf', kind: 'cmd' },
    { text: 'cli.py queue-add job:lever:b2 --resume ~/resume.pdf', kind: 'cmd' },
    { text: 'cli.py queue-run', kind: 'cmd' },
    { text: '\u2192 risk adjudication: run allowed (2 due, cap 5/day)', kind: 'info' },
    { text: '\u2713 recorded: senior backend eng \u00b7 greenhouse', kind: 'ok' },
    { text: '\u2192 pacing: sleeping 214s (randomized 2\u20137 min)', kind: 'info' },
    { text: '\u2192 job:lever:b2: grill_pending (2/4) \u2014 stays queued', kind: 'warn' },
    { text: '\u2713 run done: 1 recorded \u00b7 1 queued \u00b7 0 failed', kind: 'ok' },
  ],
  limits: [
    '5 a day is a ceiling, not a target — quality beats quota.',
    'A per-item failure is recorded and the run continues; only the daily cap or a risk veto stops the whole run.',
    'Long runs need the process alive — pair queue-run with cron for daily runs.',
    'Grill-pending items wait on you. The queue holds them; it doesn\u2019t nag you.',
  ],
  faq: [
    {
      q: 'What happens when I hit the 5-a-day cap mid-run?',
      a: 'The run stops cleanly with cap_reached, remaining items stay queued, and the next run picks them up. The cap is the compliance gate\u2019s decision, not a crash.',
    },
    {
      q: 'Can I prioritize the queue?',
      a: 'Items are processed in due order; queue-add --scheduled-for pins an item to a future time. The queue file is plain JSON if you want to get hands-on.',
    },
    {
      q: 'Does the queue lower the bar per application?',
      a: 'No. Each item goes through the same pipeline as a manual apply — grill, honesty check, veto screen, fill-only rules. The queue paces the work; it doesn\u2019t lower the bar.',
    },
  ],
};

export default spec;

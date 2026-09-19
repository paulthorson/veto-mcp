import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'the-grill',
  tag: 'Apply-time grilling',
  tagVariant: 'red',
  title: 'THE GRILL',
  lede: 'Before Veto lets an application move, it interrogates you. Deterministic questions, generated from the gaps between the posting and your profile: missing skills, unquantified wins, salary, logistics, motivation. Answer on your phone; the application waits.',
  points: [
    {
      icon: 'question',
      tone: 'red',
      title: 'Gap-driven questions',
      body: 'No small talk. Each question maps to a real gap: a required skill your profile lacks, an achievement with no numbers, a missing salary expectation, an unanswered \u2018why this company\u2019. If there\u2019s no gap, there\u2019s no question.',
    },
    {
      icon: 'chat',
      tone: '',
      title: 'Channels that work',
      body: 'Chat is the default and works on a normal install. WhatsApp works when you bridge the side-chat. Gmail grill needs a private CLI not included in a normal install.',
    },
    {
      icon: 'list',
      tone: '',
      title: 'Parses lazy replies',
      body: 'Reply \u20181. yes 2. p99 -40% 3. 180k\u2019 in a single message and the parser splits it into answers, with a guard against decimals like \u20182.5 years\u2019. Terse is fine; the grill wants facts, not essays.',
    },
    {
      icon: 'lock',
      tone: '',
      title: 'Nothing moves until it\u2019s done',
      body: 'apply_to_job returns grill_pending while questions are unanswered. No tailoring, no recording, no submitting. Your answers feed straight into the resume tailoring, so the grill makes the application stronger, not just slower.',
    },
  ],
  demoTitle: 'Grilled over WhatsApp',
  demoLines: [
    { text: 'cli.py apply job:lever:9f2c --resume ~/resume.pdf --confirm', kind: 'cmd' },
    { text: '\u2192 grill started: 4 questions \u2192 WhatsApp', kind: 'warn' },
    { text: '  Q1: Go isn\u2019t on your profile: used it?', kind: 'info' },
    { text: '  Q2: biggest infra win has no numbers: metrics?', kind: 'info' },
    { text: '  Q3: salary expectations for this role?', kind: 'info' },
    { text: '  Q4: why this company, in one line?', kind: 'info' },
    { text: '  WhatsApp reply: "1. yes 2yrs 2. p99 -40% 3. 180k 4. blog"', kind: 'info' },
    { text: 'grill-ingest-reply job:lever:9f2c --body-file reply.txt', kind: 'cmd' },
    { text: '\u2713 grill complete: 4/4: tailoring resume', kind: 'ok' },
    { text: '\u2192 qualification 0.87 \u00b7 veto check passed', kind: 'ok' },
    { text: '\u2713 RECORDED: finish submitting at the apply link', kind: 'ok' },
  ],
  limits: [
    'The grill asks about gaps it can detect, it can\u2019t grill you on things neither the posting nor your profile mentions.',
    'WhatsApp delivery depends on the side-chat bridge; chat always works as the fallback.',
    'Gmail grill needs a private CLI not included in a normal install. When that CLI is present, matching needs the [grill:<id>] subject tag intact.',
    'Deterministic questions, not a conversation, it won\u2019t riff or follow up like a human interviewer would.',
  ],
  faq: [
    {
      q: 'Can I skip the grill?',
      a: 'It\u2019s a preference (grill_on_apply), not a mandate. But the grill feeds your tailoring, skipping it means a weaker application, and the honesty and veto checks still run regardless.',
    },
    {
      q: 'What if I don\u2019t know an answer?',
      a: 'Say so. \u2018Don\u2019t know\u2019 is a valid answer, it becomes a reported gap (missing_skills) instead of a padded lie. The grill\u2019s job is accuracy, not flattery.',
    },
    {
      q: 'Does the Gmail grill work on a normal install?',
      a: 'No. Gmail grill needs a private CLI not included in a normal install. Use chat (default) or WhatsApp when bridged. If you do have that CLI, replies match on the [grill:<id>] subject tag — keep the subject intact.',
    },
  ],
};

export default spec;

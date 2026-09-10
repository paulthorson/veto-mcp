import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'followups',
  tag: 'Win · follow through',
  tagVariant: '',
  title: 'NEVER LET A THREAD DIE QUIETLY',
  lede: 'followup.py watches your applied and interviewing entries, drafts stage-aware follow-ups when they go stale, and sends nothing without your explicit confirmation of the exact recipient, subject, and body.',
  points: [
    {
      icon: 'envelope',
      tone: '',
      title: 'Stage-aware drafts',
      body: 'A nudge after an application reads differently from a thank-you after a final. Drafts match the stage you are actually in.',
    },
    {
      icon: 'hourglass',
      tone: 'amber',
      title: 'Stale detection',
      body: 'Applied entries with no movement get flagged on a schedule. The CRM nudge list keeps the timing; the drafts keep the tone.',
    },
    {
      icon: 'shield',
      tone: 'red',
      title: 'Exact-approval sending',
      body: 'Sending needs confirmed=True plus the exact recipient, subject, and body. No "looks about right". The bytes you approve are the bytes that send.',
    },
    {
      icon: 'chat',
      tone: '',
      title: 'Your channels',
      body: 'Drafts go through your connected Gmail path, or render for chat and WhatsApp. Each downstream user connects their own accounts.',
    },
  ],
  demoTitle: 'Drafting a follow-up',
  demoLines: [
    { text: '$ veto followups due', kind: 'cmd' },
    { text: '! AcmeCo: applied 12 days ago, no movement', kind: 'warn' },
    { text: '+ draft: check-in, references your k8s migration bullet', kind: 'ok' },
    { text: '  to: hiring-manager@acmeco.example / re: Platform Engineer: follow-up', kind: 'info' },
    { text: 'X not sent: needs your explicit confirm of recipient, subject, body.', kind: 'veto' },
  ],
  limits: [
    'Drafts are starting points; a copy-paste nudge sent to 40 companies is still spam.',
    'Stale detection depends on your lifecycle tracking being up to date.',
    'Sending is Gmail-path only for now; other channels get rendered drafts.',
    'It will not follow up more often than the schedule allows, no pestering.',
  ],
  faq: [
    {
      q: 'What does "exact approval" mean?',
      a: 'You confirm the literal recipient, subject, and body. If any byte changes after approval, it needs approval again.',
    },
    {
      q: 'How stale is stale?',
      a: 'Stage-dependent, applications get nudged sooner than post-final thank-yous. The nudge list shows the reasoning.',
    },
  ],
};

export default spec;

import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'email-sync',
  tag: 'Recruiter email',
  tagVariant: '',
  title: 'INBOX RADAR',
  lede: 'When a private Gmail CLI is available, scan_recruiter_emails classifies recruiter mail and proposes stage updates on high-confidence matches, and draft_followup_email writes check-ins and thank-yous. That CLI is not included in a normal install, so these tools report it missing there. Nothing sends without your explicit confirm.',
  points: [
    {
      icon: 'envelope',
      tone: '',
      title: 'Classification, not guessing',
      body: 'Each thread is classified: new opportunity, interview invite, rejection, follow-up, with a confidence score. Stage updates are proposed only when the match is unambiguous and confidence is high (\u22650.8). Otherwise it shows you the thread and asks.',
    },
    {
      icon: 'list',
      tone: '',
      title: 'Stage sync',
      body: 'Confirmed matches move your applications through the pipeline: applied \u2192 interviewing \u2192 offer, or rejected. Every move is logged with the email that triggered it, so the audit trail survives your inbox.',
    },
    {
      icon: 'pencil',
      tone: '',
      title: 'Drafts, not sends',
      body: 'draft_followup_email writes check-in, thank-you, and nudge emails in your voice from the thread context. Sending needs confirm=True with the exact recipient, subject, and body, no blanket approvals, no \u2018always send\u2019 mode.',
    },
    {
      icon: 'lock',
      tone: 'amber',
      title: 'Not in a normal install',
      body: 'Gmail read/send needs a private CLI not included in a normal install. Without it, email sync is unavailable. No credential storage beyond your own connection when that CLI is present.',
    },
  ],
  demoTitle: 'A recruiter email, handled',
  demoLines: [
    { text: 'cli.py email-scan --days 7', kind: 'cmd' },
    { text: '\u2192 unavailable: private Gmail CLI not included in a normal install', kind: 'warn' },
    { text: '  email sync needs that CLI; chat grill and fill-only apply still work', kind: 'info' },
    { text: '  nothing sends without your confirm', kind: 'ok' },
  ],
  limits: [
    'Needs a private Gmail CLI not included in a normal install. Unavailable without it.',
    'Stage updates only fire on high-confidence unambiguous matches. Everything else waits for you.',
    'Drafts are starting points in your voice. Read before confirming.',
    'Sending requires explicit confirm of recipient, subject, and body every time. There is no auto-send.',
  ],
  faq: [
    {
      q: 'Will it reply to recruiters on its own?',
      a: 'Never. It drafts; you confirm the exact recipient, subject, and body. There is deliberately no auto-send mode. An email to a stranger is a consequential action, and those belong to you. And without the private Gmail CLI, it cannot reach Gmail at all.',
    },
    {
      q: 'Does this work out of the box?',
      a: 'No. Email sync needs a private Gmail CLI not included in a normal install. Chat grill and fill-only apply do not need it.',
    },
    {
      q: 'What does it do with rejections?',
      a: 'When the private Gmail CLI is available: classifies them, moves the application to rejected, and clears the follow-up reminder. Closure, automated. The dignified kind.',
    },
  ],
};

export default spec;

import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'email-sync',
  tag: 'Recruiter email',
  tagVariant: '',
  title: 'INBOX RADAR',
  lede: 'scan_recruiter_emails reads your Gmail, classifies recruiter mail, and proposes application stage updates — but only on high-confidence, unambiguous matches. draft_followup_email writes your check-ins and thank-yous. Nothing sends without your explicit confirm.',
  points: [
    {
      icon: 'envelope',
      tone: '',
      title: 'Classification, not guessing',
      body: 'Each thread is classified — new opportunity, interview invite, rejection, follow-up — with a confidence score. Stage updates are proposed only when the match is unambiguous and confidence is high (\u22650.8). Otherwise it shows you the thread and asks.',
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
      body: 'draft_followup_email writes check-in, thank-you, and nudge emails in your voice from the thread context. Sending needs confirm=True with the exact recipient, subject, and body — no blanket approvals, no \u2018always send\u2019 mode.',
    },
    {
      icon: 'lock',
      tone: 'amber',
      title: 'Gmail only, scoped',
      body: 'Reads and sends through Gmail only, and only the threads it needs. No credential storage beyond your own Gmail connection — the same rule as everything else Veto touches.',
    },
  ],
  demoTitle: 'A recruiter email, handled',
  demoLines: [
    { text: 'cli.py email-scan --days 7', kind: 'cmd' },
    { text: '\u2192 3 recruiter threads found', kind: 'info' },
    { text: '\u2713 "Interview invite \u2014 Staff SWE @ Initech" (0.94)', kind: 'ok' },
    { text: '  \u2192 proposes: job:lever:b2 \u2192 interviewing', kind: 'info' },
    { text: '? "Following up" \u2014 ambiguous (0.52), needs eyes', kind: 'warn' },
    { text: '  \u2192 no stage change proposed', kind: 'info' },
    { text: 'cli.py email-followup job:lever:b2 --kind nudge', kind: 'cmd' },
    { text: '\u2713 draft ready \u2014 review, then send with --confirm', kind: 'ok' },
  ],
  limits: [
    'Stage updates only fire on high-confidence unambiguous matches — everything else waits for you.',
    'Gmail only. Other providers aren\u2019t supported.',
    'Drafts are starting points in your voice — read before confirming.',
    'Sending requires explicit confirm of recipient, subject, and body every time. There is no auto-send.',
  ],
  faq: [
    {
      q: 'Will it reply to recruiters on its own?',
      a: 'Never. It drafts; you confirm the exact recipient, subject, and body. There is deliberately no auto-send mode — an email to a stranger is a consequential action, and those belong to you.',
    },
    {
      q: 'What does it do with rejections?',
      a: 'Classifies them, moves the application to rejected, and clears the follow-up reminder. Closure, automated — the dignified kind.',
    },
    {
      q: 'Can it find jobs in my inbox?',
      a: 'It classifies recruiter outreach, including new opportunities. But it\u2019s a radar, not a search engine — the boards are for hunting; the inbox is for handling.',
    },
  ],
};

export default spec;

import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'contribute',
  tag: 'Govern · opt-in data',
  tagVariant: '',
  title: 'GIVE BACK WITHOUT GIVING YOURSELF AWAY',
  lede: 'contribute.py is an opt-in training-data pipeline: your anonymized sessions (mock interviews, drills) can improve the system — but only after a PII scrubber, a mandatory exact preview, and your per-bundle confirmation. Nothing uploads automatically. Ever.',
  points: [
    {
      icon: 'shield',
      tone: '',
      title: 'Scrubbed first',
      body: 'Emails, URLs, phones, handles, known companies, heuristic name detection — stripped before you ever see the bundle. What remains is patterns, not people.',
    },
    {
      icon: 'doc',
      tone: 'amber',
      title: 'Preview is mandatory',
      body: 'You read the exact bundle before it goes anywhere. The bundle hash must match your preview — if a byte changed, the submission is rejected.',
    },
    {
      icon: 'check',
      tone: '',
      title: 'Per-bundle confirmation',
      body: 'Every submission is confirmed individually. No blanket consent, no "and all future sessions." Each bundle, each time.',
    },
    {
      icon: 'star',
      tone: '',
      title: 'The impact loop',
      body: 'Maintainers record when contributed data actually improves something, and you see your impact log — newest first. Only bundles genuinely cited count toward your impact.',
    },
  ],
  demoTitle: 'Contributing a session',
  demoLines: [
    { text: '$ veto contribute preview --session mock_042', kind: 'cmd' },
    { text: '+ scrubbed: 3 emails, 1 phone, 2 company names removed', kind: 'ok' },
    { text: '+ bundle hash: 9f2c…a41b — preview exactly what will send', kind: 'info' },
    { text: '> confirm bundle 9f2c…a41b? [y/N]', kind: 'cmd' },
    { text: '+ recorded to contributions/outbox. Nothing uploaded — maintainer pulls.', kind: 'ok' },
    { text: '+ impact: bundle cited in "negotiation sim v2" — see veto impact', kind: 'ok' },
  ],
  limits: [
    'Opt-in means opt-in: the default is that nothing leaves your machine.',
    'Scrubbing is heuristic — review the preview yourself before confirming.',
    'Contributions go to the local outbox; a maintainer pulls them. There is no auto-upload path by design.',
    'The impact log is maintainer-curated. Citations are earned, not automatic.',
  ],
  faq: [
    {
      q: 'Can I turn it all off?',
      a: 'Yes — a settings kill switch disables the pipeline entirely. It is off until you turn it on, per bundle.',
    },
    {
      q: 'What exactly is in a bundle?',
      a: 'Anonymized session patterns: question types, feedback categories, drill outcomes. The preview shows you literally every byte.',
    },
  ],
};

export default spec;

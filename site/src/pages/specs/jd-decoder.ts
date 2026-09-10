import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'jd-decoder',
  tag: 'Find · posting intel',
  tagVariant: 'amber',
  title: 'READ THE POSTING LIKE A CYNIC',
  lede: 'jd_decoder.py reads a job description the way a burned-out hiring manager would: salary transparency, overwork language, vagueness density, growth signals. Every flag ships with the exact quote: verdicts of strong, mixed, or caution.',
  interactive: 'jd',
  points: [
    {
      icon: 'scan',
      tone: '',
      title: 'Transparency score',
      body: 'Salary range listed? Equity stated concretely? Clear must-haves vs nice-to-haves? Scored 0–100 with the quotes that earned it.',
    },
    {
      icon: 'warn',
      tone: 'red',
      title: 'Overwork language',
      body: '"Fast-paced environment", "wear many hats", "work hard play hard", matched phrases quoted with a plain-English read of what they usually mean.',
    },
    {
      icon: 'doc',
      tone: 'amber',
      title: 'Vagueness density',
      body: 'Counts "rockstar", "ninja", "guru", "synergy" against concrete responsibilities. A posting that cannot describe the job cannot be a good job.',
    },
    {
      icon: 'check',
      tone: '',
      title: 'Green flags',
      body: 'Remote flexibility, salary transparency, mentorship, learning budgets, promotion paths, the signals that predict a posting worth your time.',
    },
  ],
  demoTitle: 'Decoding a posting',
  demoLines: [
    { text: '$ veto decode-jd posting.txt', kind: 'cmd' },
    { text: '+ GREEN: salary range $150-185k listed', kind: 'ok' },
    { text: '+ GREEN: remote-first, mentorship program, $3k learning budget', kind: 'ok' },
    { text: 'X CAUTION: "fast-paced environment": overwork language', kind: 'veto' },
    { text: 'X CAUTION: "wear many hats", "rockstar": vagueness flags', kind: 'veto' },
    { text: '! VERDICT: MIXED: 3 green signals, 4 caution flags', kind: 'warn' },
  ],
  limits: [
    'Phrase lists are curated, not exhaustive, novel euphemisms slip through.',
    'A "mixed" verdict is a starting point for your judgment, not a decision.',
    'Cannot detect lies, only language. A transparent-sounding scam is still a scam.',
    'English postings only for now.',
  ],
  faq: [
    {
      q: 'Does it moralize about companies?',
      a: 'No. It presents evidence, quotes and counts, and a verdict. The judgment call stays yours.',
    },
    {
      q: 'Can it decode a posting from a URL?',
      a: 'Give it text. Pair it with get_job_details to pull the posting first, then decode.',
    },
  ],
};

export default spec;

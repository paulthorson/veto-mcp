import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'honesty-check',
  tag: 'Governance',
  tagVariant: 'red',
  title: 'NO LYING',
  lede: 'The cover letter is veto-scanned before anything moves. Any skill or years-of-experience it claims that your profile can\u2019t back up blocks the application. Don\u2019t claim what you can\u2019t back up. Heuristic-layer misses warn rather than block.',
  points: [
    {
      icon: 'shield',
      tone: 'red',
      title: 'Claim scanning',
      body: 'Every concrete skill and years-of-experience claim in the cover letter is checked against your profile. Unsupported claims stop the application on the spot.',
    },
    {
      icon: 'check',
      title: 'Tailoring respects it',
      body: 'tailor_application reports gaps as missing_skills, it never adds them to your resume. The honesty check is the backstop for anything the tailoring wrote.',
    },
    {
      icon: 'warn',
      tone: 'amber',
      title: 'Heuristics warn',
      body: 'Fuzzy, paraphrased, or borderline matches warn rather than block. The gray area is for humans, not regex.',
    },
    {
      icon: 'check',
      title: 'Specific feedback',
      body: 'A block names the claim that tripped it: "5 yrs Rust, profile shows 2", so you know exactly what to fix.',
    },
  ],
  demoTitle: 'veto: zsh',
  demoLines: [
    { text: 'cli.py apply job:lever:9 --resume ~/r.pdf --confirm', kind: 'cmd' },
    { text: '\u2192 grill: 3/3 answered \u2713', kind: 'info' },
    { text: '\u2192 tailoring: 6 matched, 2 missing (reported, not added)', kind: 'info' },
    { text: '\u2192 honesty scan: "5 yrs Rust": profile shows 2', kind: 'warn' },
    { text: '\u2715 BLOCKED: unsupported claim in cover letter', kind: 'veto' },
    { text: '  fix the claim and re-run: no override switch', kind: 'info' },
    { text: '\u2192 qualification never ran: honesty gates first', kind: 'info' },
    { text: '  profile is the source of truth: update it, don\u2019t pad it', kind: 'info' },
  ],
  limits: [
    'It scans the cover letter, not your soul, keep the profile honest too.',
    'Paraphrased skills can slip past heuristics. They warn, not block.',
    'It checks claims against your profile, not against reality.',
    'Years math is fuzzy. Borderline cases warn instead of blocking.',
  ],
  faq: [
    {
      q: 'What exactly gets blocked?',
      a: 'Concrete skill and years-of-experience claims with no evidence in your profile. Vague enthusiasm ("passionate about distributed systems") isn\u2019t a claim, "5 years of Rust" is.',
    },
    {
      q: 'Does it rewrite the letter for me?',
      a: 'No. It blocks and tells you exactly which claim tripped it. You rewrite, the fix is a human judgment call, not an automated edit.',
    },
  ],
};

export default spec;

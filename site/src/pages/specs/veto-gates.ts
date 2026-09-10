import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'veto-gates',
  tag: 'Governance',
  tagVariant: 'red',
  title: 'THE VETO',
  lede: 'Every confirmed application passes a constitutional veto screen on a neutral summary of the planned action, plus an advisory adversarial review. A veto hit, or a failed veto check, blocks the action, fail-closed. Nothing is submitted and nothing is logged.',
  points: [
    {
      icon: 'x',
      tone: 'red',
      title: 'Veto screen',
      body: 'The framework screens a plain-language summary of the planned application (universal domain) before anything moves. A hit stops the action cold.',
    },
    {
      icon: 'lock',
      tone: 'red',
      title: 'Fail-closed',
      body: 'A veto hit or a failed veto check blocks, always. Nothing is submitted and nothing is written to applications.json. Caution wins over convenience.',
    },
    {
      icon: 'check',
      title: 'Humans clear it',
      body: 'Only a human clears a veto: fix the application or the profile and re-run. There is no bypass switch, no "do it anyway" flag.',
    },
    {
      icon: 'shield',
      tone: 'amber',
      title: 'Compliance-only mode',
      body: 'If the governance framework is unavailable, the deterministic compliance gates still hold. The decision is marked compliance-only, the guardrails don\u2019t take a day off.',
    },
  ],
  demoTitle: 'veto: zsh',
  demoLines: [
    { text: 'cli.py apply job:indeed:77 --resume ~/r.pdf --confirm', kind: 'cmd' },
    { text: '\u2192 grill: 4/4 answered \u2713', kind: 'info' },
    { text: '\u2192 honesty check: passed \u2713', kind: 'ok' },
    { text: '\u2192 veto screen: 1 hit: "mass-apply pattern"', kind: 'warn' },
    { text: '\u2715 VETOED: nothing submitted, nothing logged', kind: 'veto' },
    { text: '  fix the application or profile, then re-run', kind: 'info' },
    { text: '\u2192 adversarial review: advisory note attached', kind: 'info' },
    { text: '\u2192 ledger: verdict written, reason recorded', kind: 'info' },
  ],
  limits: [
    'Vetoes can false-positive. That\u2019s the price of fail-closed.',
    'Full screening needs the governance framework installed.',
    'The adversarial review is advisory, it warns, never blocks.',
    'A veto stops the action; it doesn\u2019t fix your resume for you.',
  ],
  faq: [
    {
      q: 'Can I override a veto?',
      a: 'No, by design. The only path is fixing whatever tripped it (the application, the cover letter, or your profile) and re-running. If vetoes could be clicked through, they wouldn\u2019t be vetoes.',
    },
    {
      q: 'What if governance itself is down?',
      a: 'The deterministic compliance gates (daily caps, tier rules, fill-only) still hold, and the decision is marked compliance-only. The framework being unavailable never means "no rules".',
    },
  ],
};

export default spec;

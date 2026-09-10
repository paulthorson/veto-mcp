import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'crew',
  tag: 'Govern · agentic team',
  tagVariant: 'red',
  title: 'AN ENTIRE JOB-SEARCH COMPANY, UNDER GOVERNANCE',
  lede: 'crew.py encodes eleven personas from the agentic-governance framework, CEO, chief of staff, PM, engineer, UX, QA, researcher, scout, tailor agent, coach, and Red, plus twenty red-team specialists. Every agent runs spawn > work > review > merge: veto-screened before work, adversarially reviewed after, human-gated where it matters.',
  interactive: 'crew',
  points: [
    {
      icon: 'team',
      tone: 'red',
      title: 'Eleven personas',
      body: 'CEO routes and resolves by precedent. PM owns the problem. Eng implements to spec. UX owns the design system. QA blocks on red. Researcher establishes what is true. Scout vets postings skeptically. Tailor agent never invents. Coach spars hard, reviews kindly. Red reports findings and never edits.',
    },
    {
      icon: 'shield',
      tone: 'red',
      title: 'Spawn > work > review > merge',
      body: 'Every governed job is veto-screened before work starts, runs, then faces adversarial review as an advisory pass. The verdict is written to a ledger. Confirmation gates are never bypassed.',
    },
    {
      icon: 'warn',
      tone: 'amber',
      title: 'Twenty red-team specialists',
      body: 'eng-critic, qa-critic, ux-critic, security adversaries, privacy adversaries, compliance adversaries, blind-spot search, counter-case. Red can call in the specialist for the job.',
    },
    {
      icon: 'ledger',
      tone: '',
      title: 'Personas from the framework',
      body: 'Each persona card is adapted from the agentic-governance harness files, identity, what it owns, what it never does, stop conditions, with the prohibitions intact.',
    },
  ],
  demoTitle: 'Planning with the crew',
  demoLines: [
    { text: '$ veto crew plan "land a platform eng role in 90 days"', kind: 'cmd' },
    { text: '+ ceo: routed to pm > researcher > ux > eng > qa', kind: 'ok' },
    { text: '+ researcher: evidence pack: 5 sources opened, 2 contradictions surfaced', kind: 'ok' },
    { text: '+ pm: brief with 2 genuinely different approaches', kind: 'ok' },
    { text: '+ qa: 34/34 checks green. red review: 2 findings, advisory.', kind: 'warn' },
    { text: '! verdict written. Human confirm gate: plan is yours to approve.', kind: 'warn' },
  ],
  limits: [
    'The crew orchestrates; it does not replace your judgment. The human confirm gate is structural.',
    'Adversarial review is advisory, it reports findings, it does not edit or block.',
    'Personas are deterministic role prompts, not separate models. Capability is shared; discipline is per-role.',
    'Governance vetoes fail closed. If the framework is unreachable, you get compliance-only mode, not freedom.',
  ],
  faq: [
    {
      q: 'Is this the mining bots again?',
      a: 'No. The worker-bot visuals were removed deliberately. The crew is a functional orchestration layer, personas with harnesses, review gates, and a verdict ledger, not animated characters.',
    },
    {
      q: 'Where do the personas come from?',
      a: 'The agentic-governance framework\u2019s harness files (ceo, pm, engineer, ux, qa, researcher, chief-of-staff), adapted to the job-search domain. The twenty red-team specialists are the framework\u2019s adversary agents.',
    },
  ],
};

export default spec;

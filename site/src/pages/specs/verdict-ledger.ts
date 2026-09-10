import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'verdict-ledger',
  tag: 'Audit',
  title: 'RECEIPTS',
  lede: 'Every allow/block decision is written to a verdict ledger \u2014 the framework\u2019s runs/verdicts.jsonl, or a local fallback when its checkout isn\u2019t writable. risk_status is the live audit surface: per-board tier and search-allowed state, daily cap usage, registered plugins.',
  points: [
    {
      icon: 'ledger',
      title: 'Every decision logged',
      body: 'Allow or block, with the reason, timestamped. Ask why anything happened \u2014 a search skipped, an application vetoed \u2014 and get an answer.',
    },
    {
      icon: 'doc',
      title: 'risk_status',
      body: 'The live audit surface: per-board tier, whether search is currently allowed, daily cap usage, and which plugins are registered.',
    },
    {
      icon: 'doc',
      title: 'compliance.json',
      body: 'Budgets, cooldowns, and your ToS-risk acknowledgment live here \u2014 local, gitignored, yours. The machine-readable version of the rules.',
    },
    {
      icon: 'lock',
      title: 'Ledger outage \u2260 action outage',
      body: 'If the ledger can\u2019t be written, that failure is logged \u2014 it never blocks or crashes the action itself.',
    },
  ],
  demoTitle: 'veto — zsh',
  demoLines: [
    { text: 'cli.py doctor', kind: 'cmd' },
    { text: '\u2713 profile: loaded (12 skills, 4 roles)', kind: 'ok' },
    { text: '\u2713 compliance: ToS acknowledged 2026-09-10', kind: 'ok' },
    { text: '\u2192 scraping budget: 31/40 searches left today', kind: 'info' },
    { text: '\u2192 applications today: 2/5', kind: 'info' },
    { text: '\u2192 plugins registered: 8 (mcp tools/list to verify)', kind: 'info' },
    { text: '$ tail -1 runs/governance-verdicts.jsonl', kind: 'cmd' },
    { text: '{"action":"apply","job":"lever:staff",\u2026"veto"}', kind: 'info' },
  ],
  limits: [
    'The ledger records decisions, not intent \u2014 it won\u2019t psychoanalyze you.',
    'Local fallback ledger lives on your machine. Back it up if you care.',
    'risk_status is an MCP tool \u2014 no CLI twin yet.',
    'Audit trails don\u2019t prevent mistakes; they make them reviewable.',
  ],
  faq: [
    {
      q: 'Where do the verdicts actually live?',
      a: 'In the governance framework\u2019s runs/verdicts.jsonl when its checkout is writable; otherwise in a local fallback file here. Either way, doctor tells you which one is active.',
    },
    {
      q: 'Who can read the ledger?',
      a: 'You. It\u2019s local and gitignored \u2014 budgets, cooldowns, and your acknowledgment never leave your machine.',
    },
  ],
};

export default spec;

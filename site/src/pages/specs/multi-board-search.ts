import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'multi-board-search',
  tag: 'Search',
  tagVariant: '',
  title: '8 BOARDS, 1 QUERY',
  lede: 'One search fans out to eight job boards: official APIs where they exist, polite budgeted scraping where they don\u2019t. Every result arrives tagged with its risk tier, deduped, and ranked. No tabs, no copy-paste, no 47 open windows.',
  points: [
    {
      icon: 'search',
      tone: '',
      title: 'Two tiers, one query',
      body: 'Greenhouse, Lever, and Ashby run on public JSON APIs: fast, free, no auth. LinkedIn, Indeed, and ZipRecruiter run on guest endpoints and HTML, which means ToS risk: you acknowledge it in the wizard before they\u2019re ever touched. Adzuna needs a free API key. Glassdoor is still a stub.',
    },
    {
      icon: 'bolt',
      tone: 'amber',
      title: 'Budgets + circuit breaker',
      body: 'Scraping-tier boards get 40 searches a day each; official boards get 1,000. A 403, 429, or CAPTCHA trips a cooldown: 1 hour, doubling, capped at 24. The agent backs off. It never retries aggressively and never touches a CAPTCHA.',
    },
    {
      icon: 'list',
      tone: '',
      title: 'Dedup that respects recall',
      body: 'The same posting on three boards collapses into one: exact URL match, exact company+title match, or fuzzy title match at \u22650.85 for the same company. Ambiguous matches are left alone, better a duplicate than a lost job.',
    },
    {
      icon: 'list',
      tone: '',
      title: 'Filters + watches',
      body: 'salary_min and seniority post-filter on listing text (\u2018$150k\u2019, \u2018$75/hr\u2019 annualized); jobs with no detectable salary are kept, never dropped. Save any search as a watch, the first check only sets a baseline, then watch.py diffs new postings on a cron.',
    },
  ],
  demoTitle: 'One query, eight boards',
  demoLines: [
    { text: 'cli.py search "backend engineer" --location remote --limit 8', kind: 'cmd' },
    { text: '\u2713 8 jobs: greenhouse \u00b7 lever \u00b7 ashby \u00b7 linkedin \u00b7 ziprecruiter', kind: 'ok' },
    { text: '  [official] platform eng \u00b7 devtools \u00b7 remote \u00b7 greenhouse', kind: 'info' },
    { text: '  [official] backend eng \u00b7 fintech \u00b7 remote \u00b7 lever', kind: 'info' },
    { text: '  [scraping] senior backend \u00b7 saas \u00b7 remote \u00b7 linkedin', kind: 'info' },
    { text: '  dedup: 3 dupes collapsed (same posting, 3 boards)', kind: 'warn' },
    { text: '  budgets: scraping 12/40 today \u00b7 official 31/1000', kind: 'info' },
    { text: '.venv/bin/python watch.py  # cron: 0 9 * * *', kind: 'cmd' },
    { text: '\u2713 watches checked: 2 new postings since baseline', kind: 'ok' },
  ],
  limits: [
    'Indeed 403s from datacenter IPs, run from a residential IP or use the browser hook with a logged-in session.',
    'LinkedIn\u2019s guest API rate-limits; the provider logs a warning and returns what it got.',
    'Glassdoor is a stub, JS-rendered and bot-walled, needs the browser hook.',
    'Scraping-tier results are snapshots; verify the posting on the live site before applying.',
  ],
  faq: [
    {
      q: 'Why two tiers?',
      a: 'Official APIs are ToS-clean and fast; scraping works until it doesn\u2019t. The tier tag on every result tells you which deal you\u2019re getting, and strict mode disables scraping entirely.',
    },
    {
      q: 'What happens when a board blocks me?',
      a: 'The circuit breaker trips: 1 hour cooldown, doubling on consecutive blocks, capped at 24 hours. The search continues on the other boards. No CAPTCHA solving, no hammering retries.',
    },
    {
      q: 'Do watches spam me?',
      a: 'No. The first check of a watch only records a baseline, you hear nothing until a genuinely new posting appears.',
    },
  ],
};

export default spec;

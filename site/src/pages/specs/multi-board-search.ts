import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'multi-board-search',
  tag: 'Search',
  tagVariant: '',
  title: 'OFFICIAL APIS, 1 QUERY',
  lede: 'One search fans out across the official-API boards — Greenhouse, Lever, Ashby, Adzuna — plus your own saved listings. Every result arrives tagged with its risk tier, deduped, and ranked. No tabs, no copy-paste, no 47 open windows.',
  points: [
    {
      icon: 'search',
      tone: '',
      title: 'Official APIs only',
      body: 'Greenhouse, Lever, and Ashby run on public JSON APIs: fast, free, no auth. Adzuna needs a free API key. Your own saved listings (paste text, URL, or HTML) are searchable via board="user". Glassdoor is a locked stub that performs no scraping.',
    },
    {
      icon: 'bolt',
      tone: 'amber',
      title: 'Budgets + circuit breaker',
      body: 'Official boards get 1,000 searches a day each. A 403, 429, or CAPTCHA trips a cooldown: 1 hour, doubling, capped at 24. The agent backs off. It never retries aggressively and never touches a CAPTCHA.',
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
  demoTitle: 'One query, every board',
  demoLines: [
    { text: 'cli.py search "backend engineer" --location remote --limit 8', kind: 'cmd' },
    { text: '\u2713 8 jobs: greenhouse \u00b7 lever \u00b7 ashby \u00b7 adzuna', kind: 'ok' },
    { text: '  [official] platform eng \u00b7 devtools \u00b7 remote \u00b7 greenhouse', kind: 'info' },
    { text: '  [official] backend eng \u00b7 fintech \u00b7 remote \u00b7 lever', kind: 'info' },
    { text: '  [official] senior backend \u00b7 saas \u00b7 remote \u00b7 ashby', kind: 'info' },
    { text: '  dedup: 3 dupes collapsed (same posting, 3 boards)', kind: 'warn' },
    { text: '  budgets: official 31/1000 today', kind: 'info' },
    { text: '.venv/bin/python watch.py  # cron: 0 9 * * *', kind: 'cmd' },
    { text: '\u2713 watches checked: 2 new postings since baseline', kind: 'ok' },
  ],
  limits: [
    'The LinkedIn, Indeed, and ZipRecruiter providers were removed in the post-hardening pass — no scraping, no logged-in sessions.',
    'Adzuna needs a free API key before it serves results; without one it reports itself as unavailable.',
    'Glassdoor is a locked stub: it reports itself as unavailable rather than scraping.',
    'All results are snapshots; verify the posting on the live site before applying.',
  ],
  faq: [
    {
      q: 'Why two tiers?',
      a: 'Official APIs are ToS-clean and fast. The scraping tier still exists in the risk model but has no live boards: Glassdoor is a locked stub, and LinkedIn, Indeed, and ZipRecruiter were removed. Strict mode restricts search to official-tier boards.',
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

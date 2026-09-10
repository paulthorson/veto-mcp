import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'fill-only-apply',
  tag: 'Applying',
  tagVariant: 'amber',
  title: 'FILLS. NEVER SUBMITS.',
  lede: 'Veto does the tedious part — driving the form, every field, the resume upload — and stops at the review screen. The final click is always yours. On boards where automation bends the rules, the restraint is policy, not preference.',
  points: [
    {
      icon: 'clipboard',
      tone: 'amber',
      title: 'Easy Apply, minus the apply',
      body: 'easy_apply_fill walks the LinkedIn Easy Apply modal (max 6 steps), clicking only Next, Continue, and Review. At the review screen it stops and hands you the window. Any automation attempt at the submit button raises a fill-only violation — the code refuses.',
    },
    {
      icon: 'list',
      tone: '',
      title: 'Official ATS only',
      body: 'apply_via_ats uses real, employer-issued ATS endpoints. We investigated anonymous submission and found no verified endpoint — so unsupported attempts return an honest error instead of guessing at someone\u2019s hiring API.',
    },
    {
      icon: 'globe',
      tone: '',
      title: 'Browser mode is opt-in',
      body: 'Full browser automation needs JOB_MCP_BROWSER_APPLY=1 plus your explicit confirm. Checkboxes and radio buttons (attestations, EEO) are deliberately left for the human, and every step is screenshotted for review.',
    },
    {
      icon: 'x',
      tone: 'red',
      title: 'Vetoed before filled',
      body: 'None of this starts until the governance precheck, the grill, and the risk adjudication pass. A vetoed application never opens a browser tab.',
    },
  ],
  demoTitle: 'Fill-only Easy Apply',
  demoLines: [
    { text: 'cli.py easy-apply job:linkedin:9f2c --confirm', kind: 'cmd' },
    { text: '\u2192 modal opened (saved session) \u00b7 max 6 steps', kind: 'info' },
    { text: '  [1/6] contact info \u2026 filled \u2713', kind: 'info' },
    { text: '  [2/6] experience \u2026 filled \u2713', kind: 'info' },
    { text: '  [3/6] screening Qs \u2026 filled \u2713', kind: 'info' },
    { text: '  [4/6] EEO questions \u2026 left for you (policy)', kind: 'info' },
    { text: '\u2192 review screen reached \u2014 STOPPING here', kind: 'warn' },
    { text: '\u2713 filled + resume uploaded + screenshots saved', kind: 'ok' },
    { text: '\u2715 submit is yours \u2014 automation will not click it', kind: 'veto' },
  ],
  limits: [
    'Easy Apply needs a saved LinkedIn session — you log in once, manually, in a headed browser. Passwords are never typed or stored.',
    'Sites change their markup; the modal walker is bounded and may bail with step_limit_reached.',
    'apply_via_ats only works where employers issued credentials — most of the time it will honestly tell you no.',
    'Browser automation can still trip anti-bot measures. Human pace, human review, always.',
  ],
  faq: [
    {
      q: 'Why won\u2019t it just click submit?',
      a: 'Because the final click is the consequential action — the one that sends your name to a stranger. Veto\u2019s contract is: automation does the tedious parts, humans make the consequential decisions. On scraping-tier boards it\u2019s a policy hard-block, not a preference.',
    },
    {
      q: 'What if the form asks something the profile can\u2019t answer?',
      a: 'Screening questions are filled from your profile and grill answers where possible. Anything ambiguous is left blank and flagged in the report — you\u2019d rather answer it yourself than have the bot guess.',
    },
    {
      q: 'Can it handle Workday / Taleo / custom ATS forms?',
      a: 'The generic browser filler handles standard visible inputs on any page. Site-specific quirks (multi-page Workday flows, I\u2019m looking at you) are best-effort — the screenshots show exactly where it got to.',
    },
  ],
};

export default spec;

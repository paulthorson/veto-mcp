import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'fill-only-apply',
  tag: 'Applying',
  tagVariant: 'amber',
  title: 'FILLS. NEVER SUBMITS.',
  lede: 'Veto does the tedious part: driving the form, every field, the resume upload, then stops at the review screen. The final click is always yours. The restraint is policy, not preference — there is no code path that submits.',
  points: [
    {
      icon: 'clipboard',
      tone: 'amber',
      title: 'Form fill, minus the submit',
      body: 'The browser hook opens the posting\u2019s apply_url, fills every visible field from your profile, uploads the resume, screenshots the completed form, and stops. There is no submit code path: no click on a submit control, no programmatic form submission, no application POST.',
    },
    {
      icon: 'list',
      tone: '',
      title: 'Official ATS only',
      body: 'apply_via_ats uses real, employer-issued ATS endpoints. We investigated anonymous submission and found no verified endpoint, so it returns a dry-run preview (zero network calls) instead of guessing at someone\u2019s hiring API.',
    },
    {
      icon: 'globe',
      tone: '',
      title: 'Browser mode is opt-in',
      body: 'Full browser form-filling is opt-in: set the browser-apply environment flag (see the README) and pass your explicit confirm. Checkboxes and radio buttons (attestations, EEO) are deliberately left for the human, and every step is screenshotted for review.',
    },
    {
      icon: 'x',
      tone: 'red',
      title: 'Vetoed before filled',
      body: 'None of this starts until the governance precheck, the grill, and the risk adjudication pass. A vetoed application never opens a browser tab.',
    },
  ],
  demoTitle: 'Fill-only apply',
  demoLines: [
    { text: 'cli.py apply job:greenhouse:9f2c --resume ~/resume.pdf --confirm', kind: 'cmd' },
    { text: '\u2192 form opened \u00b7 fields detected: 14', kind: 'info' },
    { text: '  contact info \u2026 filled \u2713', kind: 'info' },
    { text: '  experience \u2026 filled \u2713', kind: 'info' },
    { text: '  screening Qs \u2026 filled \u2713', kind: 'info' },
    { text: '  [4/4] EEO questions \u2026 left for you (policy)', kind: 'info' },
    { text: '\u2192 review screen reached: STOPPING here', kind: 'warn' },
    { text: '\u2713 filled + resume uploaded + screenshots saved', kind: 'ok' },
    { text: '\u2715 submit is yours: the software will not click it', kind: 'veto' },
  ],
  limits: [
    'Phase 2 never uses a logged-in session: you review the filled form and click submit yourself, in your own browser.',
    'Sites change their markup; the form walker is bounded and may bail with step_limit_reached.',
    'apply_via_ats only works where employers issued credentials, most of the time it will honestly tell you no.',
    'Browser automation can still trip anti-bot measures. Human pace, human review, always.',
  ],
  faq: [
    {
      q: 'Why won\u2019t it just click submit?',
      a: 'Because the final click is the consequential action, the one that sends your name to a stranger. Veto\u2019s contract is: automation does the tedious parts, humans make the consequential decisions. It\u2019s a policy hard-block, not a preference.',
    },
    {
      q: 'What if the form asks something the profile can\u2019t answer?',
      a: 'Screening questions are filled from your profile and grill answers where possible. Anything ambiguous is left blank and flagged in the report, you\u2019d rather answer it yourself than have the bot guess.',
    },
    {
      q: 'Can it handle Workday / Taleo / custom ATS forms?',
      a: 'The generic browser filler handles standard visible inputs on any page. Site-specific quirks (multi-page Workday flows, I\u2019m looking at you) are best-effort, the screenshots show exactly where it got to.',
    },
  ],
};

export default spec;

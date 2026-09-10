import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'tailoring',
  tag: 'Resume + cover letter',
  tagVariant: '',
  title: 'TAILORED, NOT FAKED',
  lede: 'tailor_application builds a per-job resume and a 3-paragraph cover letter from your saved profile. Keyword-matched bullets get front-loaded; the letter names the actual role and company. And it never, ever invents experience.',
  points: [
    {
      icon: 'pencil',
      tone: '',
      title: 'Keyword front-loading',
      body: 'Your real experience bullets are reordered and rephrased around the posting\u2019s keywords, so the match is visible in the first six seconds of a skim. What\u2019s on the page is always something you\u2019ve actually done.',
    },
    {
      icon: 'doc',
      tone: '',
      title: 'The 3-paragraph letter',
      body: 'Paragraph one: the role and why you. Paragraph two: your two or three most relevant wins, with metrics. Paragraph three: logistics and the ask. It references the actual company and role — no mad-libs.',
    },
    {
      icon: 'shield',
      tone: 'red',
      title: 'The honesty rule',
      body: 'Skills, titles, or years your profile can\u2019t back up are never added. They\u2019re reported as missing_skills instead — a to-do list, not a fabrication. The cover letter gets honesty-scanned before anything proceeds.',
    },
    {
      icon: 'question',
      tone: '',
      title: 'Grill answers plug in',
      body: 'Finish the grill and your answers strengthen the tailoring: quantified wins land in the bullets, motivation lands in the letter. The interrogation pays rent.',
    },
  ],
  demoTitle: 'Tailoring a resume',
  demoLines: [
    { text: '> tailor_application("job:greenhouse:stripe:42")', kind: 'info' },
    { text: '\u2713 matched: python, postgres, k8s, on-call', kind: 'ok' },
    { text: '! missing: go, terraform \u2014 reported, not padded', kind: 'warn' },
    { text: '  resume: 6 bullets reordered around posting keywords', kind: 'info' },
    { text: '  cover letter: 3 paragraphs, names the role + company', kind: 'info' },
    { text: '\u2713 honesty scan: no invented skills, titles, or years', kind: 'ok' },
    { text: '  grill answers folded in: p99 -40% \u2192 bullet #2', kind: 'info' },
    { text: '\u2713 tailored pack ready for review', kind: 'ok' },
  ],
  limits: [
    'Tailoring reorders and rephrases — it won\u2019t invent a job you never had.',
    'Keyword matching is textual, not semantic; exotic titles may match poorly.',
    'The letter is a strong draft, not a final — read it before it goes anywhere.',
    'Only as good as your profile: a thin profile produces a thin letter. Run the wizard properly.',
  ],
  faq: [
    {
      q: 'Will it add skills I don\u2019t have to match the posting?',
      a: 'No — that\u2019s the entire point of the honesty rule. Missing skills are reported as missing_skills so you know the gap; the application never claims them.',
    },
    {
      q: 'Does it rewrite my whole resume?',
      a: 'It reorders and rephrases your real bullets around the posting\u2019s keywords. Your history stays your history — the emphasis changes, the facts don\u2019t.',
    },
  ],
};

export default spec;

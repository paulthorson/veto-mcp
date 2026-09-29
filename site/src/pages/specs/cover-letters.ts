import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'cover-letters',
  tag: 'Tailor · cover letter',
  tagVariant: '',
  title: 'LETTERS THAT CAN BE FACT-CHECKED',
  lede: 'cover_letters.py drafts from profile facts only, hook line, two proof paragraphs mapped to the posting\u2019s requirements, an honest "eager to develop" paragraph for the gaps. Then honesty_scan interrogates every sentence before the draft proceeds.',
  interactive: 'cover',
  points: [
    {
      icon: 'doc',
      tone: '',
      title: 'Fact-grounded drafts',
      body: 'Hook (title + years + matched skills), two proof paragraphs each tied to a top requirement and a real profile bullet, a close. Facts are rephrased, never rewritten.',
    },
    {
      icon: 'scan',
      tone: 'red',
      title: 'The honesty scan',
      body: 'Every sentence is checked three ways: numbers against profile text, proper nouns against your real employers, skills against your real list. "I increased revenue by 300%" gets flagged. Hedged growth areas ("eager to develop") pass honestly.',
    },
    {
      icon: 'check',
      tone: '',
      title: 'Self-checking drafts',
      body: 'The draft runs honesty_scan on itself before you ever see it, the scan result must be empty. A letter that fails its own audit never reaches you.',
    },
    {
      icon: 'ledger',
      tone: '',
      title: 'Approval + persistence',
      body: 'Approve a letter and it is stored verbatim under cover_letters/<job>.txt. The exact text you approved is the exact text that exists.',
    },
  ],
  demoTitle: 'Scanning a cover letter',
  demoLines: [
    { text: '$ veto cover-letter draft --job job:lever:acme', kind: 'cmd' },
    { text: '+ hook: title + 5 yrs + python/k8s/postgres', kind: 'ok' },
    { text: '+ proof 1: k8s migration (bullet #2, verbatim facts)', kind: 'ok' },
    { text: '+ proof 2: on-call p99 ownership (bullet #4)', kind: 'ok' },
    { text: '+ gap paragraph: terraform: "eager to develop", honestly hedged', kind: 'ok' },
    { text: '+ honesty_scan: 0 flags. Draft is clean.', kind: 'ok' },
  ],
  limits: [
    'The scan is textual, a cleverly reworded invention can still slip past.',
    'Drafts are strong starting points, not finals. Read every letter before it goes out.',
    'Only as good as your profile: thin profiles produce thin letters.',
    'Hedged language ("eager to") is honest only if it is true, do not hedge what you have never touched.',
  ],
  faq: [
    {
      q: 'What exactly does honesty_scan flag?',
      a: 'Numbers and metrics not found in your profile text, multiword proper nouns (companies, titles) that are not yours or the target company\u2019s, and skill claims absent from both your skill list and profile text, unless the sentence is explicitly hedged.',
    },
    {
      q: 'What happens when a draft fails its scan?',
      a: 'You see the flags, sentence by sentence. Fix the profile (if the fact is real but missing) or accept the honest version.',
    },
  ],
};

export default spec;

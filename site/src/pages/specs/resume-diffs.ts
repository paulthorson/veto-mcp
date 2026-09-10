import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'resume-diffs',
  tag: 'Tailor · resume',
  tagVariant: '',
  title: 'EVERY EDIT, ON THE RECORD',
  lede: 'Tailored resume diffs show exactly what changed between your base resume and the per-job variant, line by line, and nothing is final until you approve it. Approved variants persist per job; unapproved ones never leave the diff view.',
  interactive: 'diff',
  points: [
    {
      icon: 'diff',
      tone: '',
      title: 'Unified diffs',
      body: 'Base resume on the left, tailored variant on the right, every added and reordered line marked. You see the whole surgery before it ships.',
    },
    {
      icon: 'check',
      tone: '',
      title: 'Approval gate',
      body: 'Approve a variant and it is saved under tailored/<job>.json, verbatim. Skip it and nothing is recorded. The default is caution.',
    },
    {
      icon: 'shield',
      tone: 'red',
      title: 'Missing skills stay missing',
      body: 'Skills the posting wants and you lack are reported as a gap list, never padded into the bullets. The diff only contains things you have actually done.',
    },
    {
      icon: 'chat',
      tone: '',
      title: 'Grill answers fold in',
      body: 'Finish the grill and your quantified wins land in the bullets automatically, p99 down 40% goes where a hiring manager will see it.',
    },
  ],
  demoTitle: 'Diffing a tailored resume',
  demoLines: [
    { text: '$ veto tailor job:greenhouse:acme-platform --diff', kind: 'cmd' },
    { text: '+ 6 bullets reordered around posting keywords', kind: 'ok' },
    { text: '+ k8s migration bullet promoted to #1 (posting: "k8s in production")', kind: 'ok' },
    { text: '! missing: go, terraform: reported, not padded', kind: 'warn' },
    { text: '> approve? [y/N]', kind: 'cmd' },
    { text: '+ APPROVED: variant saved to tailored/acme-platform.json', kind: 'ok' },
  ],
  limits: [
    'Reorders and rephrases your real bullets, it will not invent a job you never had.',
    'Keyword matching is textual; exotic titles can match poorly.',
    'The diff is only as good as your base resume. Garbage in, tailored garbage out.',
    'One variant per job, re-tailoring overwrites, so approve deliberately.',
  ],
  faq: [
    {
      q: 'Where do approved variants live?',
      a: 'Under tailored/<job-id>.json in your Veto directory, verbatim. Review them any time; they are yours.',
    },
    {
      q: 'Can I edit a variant after approving?',
      a: 'Yes, re-run tailoring and approve the new version. The old one is replaced, not merged.',
    },
  ],
};

export default spec;

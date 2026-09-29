import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'linkedin',
  tag: 'Tailor · profile',
  tagVariant: 'amber',
  title: 'YOUR PROFILE, OPTIMIZED HONESTLY',
  lede: 'linkedin_optimizer.py audits your profile section by section: headline, about, experience bullets, skills coverage, with a 0–100 score and specific fixes. Rewrites interpolate your facts only: no invented titles, employers, or numbers, enforced structurally and asserted in tests.',
  interactive: 'linkedin',
  points: [
    {
      icon: 'badge',
      tone: '',
      title: 'Section-by-section audit',
      body: 'Headline clarity, about-section voice and proof, bullet action-verb and quantification ratios, skills coverage against your target role. Each with the top fixes, ranked.',
    },
    {
      icon: 'pencil',
      tone: '',
      title: 'Headline rewrites',
      body: 'Built from your latest title, years, matching skills, latest employer. Trimmed to LinkedIn\u2019s 220 characters. No experience yet? It says "Aspiring", it never invents a job.',
    },
    {
      icon: 'doc',
      tone: '',
      title: 'About-section drafts',
      body: 'First-person, your quantified bullets reused verbatim, every claim listed in a provenance array. You can trace each sentence to the fact it came from.',
    },
    {
      icon: 'target',
      tone: 'amber',
      title: 'Keyword gaps',
      body: 'Missing keywords for your target role, ranked by importance, with placement tips that say "only if you genuinely have it." Gaps are a to-do list, not a shopping list.',
    },
  ],
  demoTitle: 'Auditing a profile',
  demoLines: [
    { text: '$ veto linkedin audit --target-role "backend engineer"', kind: 'cmd' },
    { text: '  headline 62: no years, no proof. Add both.', kind: 'info' },
    { text: '  about 45: no quantified results. No CTA.', kind: 'info' },
    { text: '  experience 78: strong verbs; 2 bullets unquantified.', kind: 'info' },
    { text: '  skills 81: missing: terraform, system design.', kind: 'info' },
    { text: '+ rewrite: "Backend Engineer (5 yrs): Python, K8s, Postgres | ex-FintechCo"', kind: 'ok' },
    { text: '+ every number in the rewrite appears in your profile. Verified.', kind: 'ok' },
  ],
  limits: [
    'Rewrites only interpolate profile facts, a thin profile gets a thin rewrite.',
    'Keyword sets cover six role families; exotic roles get a generic pass.',
    'It optimizes for recruiter search and human skim, not for gaming the algorithm.',
    'Veto drafts; you paste. It never touches your LinkedIn account.',
  ],
  faq: [
    {
      q: 'Will it make me sound like someone I am not?',
      a: 'Structurally impossible: rewrites only rearrange your facts, and tests assert trap facts (famous schools, FAANG employers) never appear unless they are yours.',
    },
    {
      q: 'Does it post to LinkedIn for me?',
      a: 'No. It produces text. You copy, you paste, you own it.',
    },
  ],
};

export default spec;

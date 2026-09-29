/* Data-driven drill-down page specs. Each feature page is a spec object;
   FeaturePage.tsx renders it in the pixel theme. */

export type TermKind = 'cmd' | 'ok' | 'info' | 'warn' | 'veto';

export interface SpecPoint {
  icon: string;
  tone?: '' | 'red' | 'amber';
  title: string;
  body: string;
}

export interface SpecFaq {
  q: string;
  a: string;
}

export interface SpecMethodBlock {
  title: string;
  body: string;
  rows?: [string, string][];
}

export interface SpecMethod {
  heading: string;
  intro: string;
  blocks: SpecMethodBlock[];
  /** Optional labeled link rendered under the method intro, e.g. to the source file. */
  source?: { label: string; href: string };
}

export interface PageSpec {
  /** URL fragment: #/features/<slug> */
  slug: string;
  /** Small tag above the title */
  tag: string;
  tagVariant?: '' | 'red' | 'amber';
  /** Pixel-display title (short) */
  title: string;
  /** Intro paragraph */
  lede: string;
  /** "How it works" cards */
  points: SpecPoint[];
  /** Terminal demo */
  demoTitle: string;
  demoLines: { text: string; kind: TermKind }[];
  /** Key into the interactive demo registry (src/demos). Optional. */
  interactive?: string;
  /** Optional "try it live" CTA rendered under the demo section, e.g.
      a link to a full interactive tool page for this feature. */
  tryIt?: { href: string; label: string };
  /** Honest limitations — the "boss fights" */
  limits: string[];
  faq?: SpecFaq[];
  /** Optional "under the hood" methodology section. Rendered between the
      demo and the limits section; specs without it render nothing extra. */
  method?: SpecMethod;
}

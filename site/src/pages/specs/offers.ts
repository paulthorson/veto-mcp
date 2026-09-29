import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'offers',
  tag: 'Win · decide',
  tagVariant: '',
  title: 'COMPARE OFFERS LIKE AN ADULT',
  lede: 'offer_compare.py validates your offers, computes four-year total compensation, and scores them on your weights, then tells you what would need to be true for each offer to win. Derived figures are labeled estimated; market data is never invented.',
  interactive: 'offers',
  points: [
    {
      icon: 'trophy',
      tone: '',
      title: 'Four-year totals',
      body: 'Base, bonus, signing, and equity projected over four years per offer: the number that actually matters, not the base-salary headline.',
    },
    {
      icon: 'gauge',
      tone: '',
      title: 'Your weights, your winner',
      body: 'Adjust cash vs growth vs balance and watch the winner change. The ranking follows your values, not a default.',
    },
    {
      icon: 'question',
      tone: 'amber',
      title: '"What would need to be true"',
      body: 'For each offer, a human-readable line: what would have to change for this one to win. Negotiation targets, generated.',
    },
    {
      icon: 'shield',
      tone: 'red',
      title: 'No invented market data',
      body: 'Every derived figure is labeled estimated. Veto never invents "market rate" numbers to make an offer look good or bad.',
    },
  ],
  demoTitle: 'Comparing three offers',
  demoLines: [
    { text: '$ veto offers compare', kind: 'cmd' },
    { text: '  A: FintechCo: 4-yr total $920k (base 165 + bonus 20 + equity)', kind: 'info' },
    { text: '  B: DevtoolsCo: 4-yr total $1,050k (base 150 + bonus 15 + equity 90)', kind: 'info' },
    { text: '  C: BigCo: 4-yr total $940k (base 180 + bonus 25 + equity 30)', kind: 'info' },
    { text: '+ winner (your weights 40/40/20): B: DevtoolsCo', kind: 'ok' },
    { text: '+ for A to win: equity would need to double, or base +15k.', kind: 'ok' },
  ],
  limits: [
    'Totals are estimates from the numbers you enter, garbage in, garbage out.',
    'Equity is valued at face; Veto does not predict startup outcomes.',
    'Non-monetary factors (team, mission, commute) are yours to weigh. The tool scores what it can count.',
    'Not financial advice. It is arithmetic with your inputs.',
  ],
  faq: [
    {
      q: 'How do I add an offer?',
      a: 'veto offers add with base, bonus, signing, equity, and vesting. Validation catches missing or inconsistent fields before anything is scored.',
    },
    {
      q: 'Can I share the comparison?',
      a: 'The breakdown is yours. Scrub company names before posting it anywhere. The tool will not do that for you.',
    },
  ],
};

export default spec;

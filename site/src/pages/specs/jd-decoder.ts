import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'jd-decoder',
  tag: 'Find · posting intel',
  tagVariant: 'amber',
  title: 'READ THE POSTING LIKE A CYNIC',
  lede: 'jd_decoder.py reads a job description the way a burned-out hiring manager would: salary transparency, overwork language, vagueness density, growth signals. Every flag ships with the exact quote: verdicts of strong, mixed, or caution.',
  interactive: 'jd',
  points: [
    {
      icon: 'scan',
      tone: '',
      title: 'Transparency score',
      body: 'Salary range listed? Equity stated concretely? Clear must-haves vs nice-to-haves? Scored 0–100 with the quotes that earned it.',
    },
    {
      icon: 'warn',
      tone: 'red',
      title: 'Overwork language',
      body: '"Fast-paced environment", "wear many hats", "work hard play hard", matched phrases quoted with a plain-English read of what they usually mean.',
    },
    {
      icon: 'doc',
      tone: 'amber',
      title: 'Vagueness density',
      body: 'Counts "rockstar", "ninja", "guru", "synergy" against concrete responsibilities. A posting that cannot describe the job cannot be a good job.',
    },
    {
      icon: 'check',
      tone: '',
      title: 'Green flags',
      body: 'Remote flexibility, salary transparency, mentorship, learning budgets, promotion paths, the signals that predict a posting worth your time.',
    },
  ],
  method: {
    heading: 'The full methodology',
    intro:
      'The decoder is jd_decoder.py: deterministic regex plus counting, stdlib only, no model, no vibes. Every signal carries the quote it came from. Nothing is inferred beyond what the posting literally says.',
    source: {
      label: 'jd_decoder.py on GitHub',
      href: 'https://github.com/paulthorson/job-apply-mcp/blob/main/jd_decoder.py',
    },
    blocks: [
      {
        title: 'Transparency score',
        body: 'Scans for salary ranges ($120k-$150k, $120,000 - $150,000, USD 100k to 130k, £60,000 to £75,000 formats), bare salary figures or salary-adjacent wording like "competitive salary", and equity terms (stock options, RSUs, ESOP, equity, ownership stake). Equity counts as concrete only when a vesting, grant, or amount detail sits within 80 characters of the term.',
        rows: [
          ['Salary range found', '+60'],
          ['Bare salary mention, no range', '+25'],
          ['Concrete equity detail', '+40'],
          ['Vague equity mention', '+15'],
          ['Hard cap', '100'],
        ],
      },
      {
        title: 'Overwork language',
        body: 'Eleven curated phrases matched case-insensitively, tolerating any whitespace between words. Longest phrase wins on overlap, then flags are sorted by appearance in the posting. Each flag carries its quote plus a plain-English read: what the phrase may signal, and a question to ask. Reads never moralize about the company.',
        rows: [
          ['fast-paced', 'Signals high urgency and shifting priorities. Ask about sprint load, on-call rotations, and how deadlines get set.'],
          ['fast paced', 'Signals high urgency and shifting priorities. Ask about sprint load, on-call rotations, and how deadlines get set.'],
          ['wear many hats', "The role may span several jobs' worth of work. Ask what a typical week looks like and which responsibilities are core."],
          ['always on', 'Suggests after-hours expectations. Ask how the team protects off-hours time.'],
          ['24/7', 'Round-the-clock language. Ask whether on-call or weekend coverage is part of the role.'],
          ['unlimited PTO', 'Teams with unlimited PTO often take less time off than teams with a fixed allotment. Ask how many days the team actually took last year.'],
          ['unlimited vacation', 'Teams with unlimited vacation often take less time off than teams with a fixed allotment. Ask how many days the team actually took last year.'],
          ['work hard play hard', 'Culture framing often paired with long hours. Ask what a normal week looks like, not the highlight reel.'],
          ['do whatever it takes', 'Open-ended commitment language. Ask for concrete examples of what this has meant recently.'],
          ['nights and weekends', 'Explicitly names off-hours work. Ask how often it happens and whether it is compensated or comped.'],
          ['hustle', 'Ambition language that can mask overwork. Ask how success is measured: output, or hours.'],
        ],
      },
      {
        title: 'Vagueness score',
        body: 'Counts ten buzzwords (longest matched first, overlap protected) against concrete responsibility lines: bullets or numbered lines. The score favors postings that spell out the actual job. Buzzword density is hits per 100 words.',
        rows: [
          ['Each responsibility line', '+6'],
          ['Each buzzword per 100 words', '-8'],
          ['Score', '50 + 6 x responsibilities - 8 x density, clamped 0-100'],
          ['The ten buzzwords', 'synergy, synergies, rockstar, rock star, ninja, guru, thought leader, game changer, game-changer, paradigm'],
        ],
      },
      {
        title: 'Verdict arithmetic',
        body: 'The verdict starts at 50 and moves with evidence. Reasons are ranked quoted evidence first, then by absolute impact, and the top three ship with the verdict. Absence notes carry quote: None, because there is nothing to quote. The final score is clamped to 0-100. Bands: strong at 70 and above, mixed from 40 to 69, caution below 40.',
        rows: [
          ['Salary range disclosed', '+25'],
          ['Salary mentioned, no range', '+10'],
          ['No compensation information listed', '-10'],
          ['Equity described concretely', '+10'],
          ['Equity mentioned without details', '+5'],
          ['Each overwork-language phrase', '-8 (capped at -30)'],
          ['Buzzword density at 3+ per 100 words', '-10'],
          ['Zero buzzwords and 3+ responsibilities', '+5'],
          ['Each growth signal (mentorship, mentoring, learning budget, professional development, career path, promotion path, training budget, conference budget)', '+5 (capped at +15)'],
          ['Each green flag (remote flexibility, flexible schedule, must-haves listed, nice-to-haves listed, salary range disclosed)', '+5 (capped at +15)'],
        ],
      },
      {
        title: 'Honesty gates',
        body: 'The decoder presents evidence, it never moralizes. Absence is reported as absence: "no salary range found" is never filled in with market data or assumptions. It cannot detect lies, only language: a transparent-sounding scam is still a scam. English postings only, and the phrase lists are curated, not exhaustive, so novel euphemisms slip through.',
      },
    ],
  },
  demoTitle: 'Decoding a posting',
  demoLines: [
    { text: '$ veto decode-jd posting.txt', kind: 'cmd' },
    { text: '+ TRANSPARENCY: 100/100, salary range $150k-$185k, equity concrete', kind: 'ok' },
    { text: '+ GREEN: remote flexibility, mentorship', kind: 'ok' },
    { text: 'X CAUTION: "fast-paced", "wear many hats", "unlimited PTO": overwork language', kind: 'veto' },
    { text: 'X CAUTION: buzzword density 3.41/100 words ("rockstar", "synergy", "ninja")', kind: 'veto' },
    { text: '! VERDICT: MIXED (66/100)', kind: 'warn' },
  ],
  limits: [
    'Phrase lists are curated, not exhaustive, novel euphemisms slip through.',
    'A "mixed" verdict is a starting point for your judgment, not a decision.',
    'Cannot detect lies, only language. A transparent-sounding scam is still a scam.',
    'English postings only for now.',
  ],
  faq: [
    {
      q: 'How is the transparency score built?',
      a: 'Salary range found is +60, a bare salary mention without a range is +25, concrete equity detail (a vesting, grant, or amount within 80 characters of the term) is +40, vague equity is +15. Capped at 100.',
    },
    {
      q: 'Does it moralize about companies?',
      a: 'No. Each overwork-language flag ships with a quote and a plain-English read: what the phrase may signal, and a question to ask. The judgment call stays yours.',
    },
    {
      q: 'Can it detect a lying posting?',
      a: 'No. It detects language, not lies. A transparent-sounding scam scores well on transparency. The honesty gates are explicit about this.',
    },
    {
      q: 'English only?',
      a: 'Yes, for now. The phrase lists, buzzwords, and salary patterns are English. Novel euphemisms slip through even in English: the lists are curated, not exhaustive.',
    },
    {
      q: 'What if no salary is listed?',
      a: 'It says so: "no salary range found" or "no compensation information listed", and the verdict drops 10 points. Absence is never filled in with market data or assumptions.',
    },
    {
      q: 'Can it read a posting from a URL?',
      a: 'Give it text. Pair it with get_job_details to pull the posting first, then decode. The engine analyzes only the text in front of it.',
    },
  ],
};

export default spec;

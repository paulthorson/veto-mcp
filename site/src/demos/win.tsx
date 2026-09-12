/* WIN-set demos: offers, skill gaps, JD decoder, autopsy, streaks. */
import { useState } from 'react';
import { DemoShell, Bar, Flag, PxSlider } from './shared';

/* ---------------- Offer comparison ---------------- */

const OFFERS = [
  { name: 'A: FintechCo', base: 165, bonus: 20, equity: 45, balance: 60, total4: 920 },
  { name: 'B: DevtoolsCo', base: 150, bonus: 15, equity: 90, balance: 80, total4: 1050 },
  { name: 'C: BigCo', base: 180, bonus: 25, equity: 30, balance: 50, total4: 940 },
];
// totals in $k over 4 years (mock)

export function OfferDemo() {
  const [wCash, setWCash] = useState(40);
  const [wGrowth, setWGrowth] = useState(40);
  const [wBalance, setWBalance] = useState(20);
  const scored = OFFERS.map((o) => {
    const cash = (o.base + o.bonus) / 205;
    const growth = o.equity / 90;
    const bal = o.balance / 100;
    const s = Math.round((cash * wCash + growth * wGrowth + bal * wBalance) / 100 * 100);
    return { ...o, score: s };
  }).sort((a, b) => b.score - a.score);
  const max = Math.max(...OFFERS.map((o) => o.total4));

  return (
    <DemoShell title="> offer compare demo" label="Offer comparison: four-year totals with adjustable weighted scoring">
      {scored.map((o, i) => (
        <div key={o.name} className={`offer-row ${i === 0 ? 'winner' : ''}`}>
          <p className="offer-name">
            {i === 0 ? <Flag tone="go">WINNER</Flag> : null} {o.name}
            <span className="offer-score">: score {o.score}</span>
          </p>
          <Bar label="4-yr total" value={o.total4} max={max} tone={i === 0 ? 'go' : ''} suffix="k" />
        </div>
      ))}
      <div className="offer-weights">
        <PxSlider label="cash weight" value={wCash} onChange={setWCash} />
        <PxSlider label="growth weight" value={wGrowth} onChange={setWGrowth} />
        <PxSlider label="balance weight" value={wBalance} onChange={setWBalance} />
      </div>
      <p className="idemo-foot">
        Drag the weights. The winner changes with your values, not ours.
        Derived figures are labeled estimated, never invented market data.
      </p>
    </DemoShell>
  );
}

/* ---------------- Skill gaps ---------------- */

const GAPS = [
  { skill: 'Kubernetes', jobs: 12, to: 'AI track: Engineer L4, containers in prod' },
  { skill: 'Go', jobs: 9, to: 'Project: rewrite one Python service in Go' },
  { skill: 'System design', jobs: 7, to: 'AI track: Engineer L6, design reviews' },
  { skill: 'Terraform', jobs: 6, to: 'Project: IaC your homelab' },
];

export function GapDemo() {
  return (
    <DemoShell title="> skill gap demo" label="Skill-gap planner: gap frequency bars mapped to lessons and projects">
      {GAPS.map((g) => (
        <div key={g.skill} className="gap-row">
          <Bar label={g.skill} value={g.jobs} max={12} tone="amber" suffix=" jobs" />
          <p className="gap-to">{'>'} {g.to}</p>
        </div>
      ))}
      <p className="idemo-foot">
        Gaps aggregate across your target jobs. Closing one needs your evidence.
        Not a checkbox.
      </p>
    </DemoShell>
  );
}

/* ---------------- JD decoder ---------------- */

// Sample posting fed to the real engine. Regen the numbers below with:
//   python3 - <<'EOF'
//   import json
//   from jd_decoder import jd_verdict
//   text = open('/tmp/jd_sample.txt', encoding='utf-8').read().rstrip('\n')
//   print(json.dumps(jd_verdict(text), indent=2, ensure_ascii=False))
//   EOF
// JD_SAMPLE is byte-identical to the text the engine decoded (no trailing newline).
// Exported so the interactive decoder page can load this exact sample.
export const JD_SAMPLE = `Senior Backend Engineer, StealthCo

We are hiring a senior backend engineer for our remote-first team. Salary range: $150k-$185k. Equity: RSUs that vest over 4 years.

What you will do:
- Own backend services end to end
- Design Postgres schemas that survive scale
- Run weekly on-call rotations
- Ship features with product and design

We need a rockstar who thrives on synergy and channels their inner ninja. We move in a fast-paced environment where everyone wear many hats. Unlimited PTO, obviously.

We offer mentorship from staff engineers.`;

// Exact jd_verdict(JD_SAMPLE) output, captured 2026-09-10. Every flag
// below carries the quote the engine produced for it.
const JD_RESULT = {
  verdict: 'mixed',
  score: 66,
  transparency: { score: 100, salaryRaw: '$150k-$185k', equityTerm: 'Equity', equityConcrete: true },
  overwork: [
    {
      phrase: 'fast-paced',
      quote: '… rockstar who thrives on synergy and channels their inner ninja. We move in a fast-paced environment where everyone wear many hats. Unlimited PTO, obviously. …',
      read: 'Signals high urgency and shifting priorities. Ask about sprint load, on-call rotations, and how deadlines get set.',
    },
    {
      phrase: 'wear many hats',
      quote: '… their inner ninja. We move in a fast-paced environment where everyone wear many hats. Unlimited PTO, obviously. We offer mentorship from staff engineers.',
      read: "The role may span several jobs' worth of work. Ask what a typical week looks like and which responsibilities are core.",
    },
    {
      phrase: 'unlimited PTO',
      quote: '… ninja. We move in a fast-paced environment where everyone wear many hats. Unlimited PTO, obviously. We offer mentorship from staff engineers.',
      read: 'Teams with unlimited PTO often take less time off than teams with a fixed allotment. Ask how many days the team actually took last year.',
    },
  ],
  buzzwords: ['rockstar', 'synergy', 'ninja'],
  buzzwordDensity: 3.41,
  responsibilities: 4,
  greenFlags: [
    {
      flag: 'remote flexibility',
      quote: '… Engineer, StealthCo We are hiring a senior backend engineer for our remote-first team. Salary range: $150k-$185k. Equity: RSUs that vest over 4 years. …',
    },
    {
      flag: 'salary range disclosed',
      quote: '… hiring a senior backend engineer for our remote-first team. Salary range: $150k-$185k. Equity: RSUs that vest over 4 years. What you will do: - Own backend …',
    },
  ],
  growth: [
    {
      signal: 'mentorship',
      quote: '… environment where everyone wear many hats. Unlimited PTO, obviously. We offer mentorship from staff engineers.',
    },
  ],
  reasons: [
    {
      impact: 25,
      reason: 'Salary range disclosed',
      quote: '… hiring a senior backend engineer for our remote-first team. Salary range: $150k-$185k. Equity: RSUs that vest over 4 years. What you will do: - Own backend …',
    },
    {
      impact: 10,
      reason: 'Equity described concretely',
      quote: '… backend engineer for our remote-first team. Salary range: $150k-$185k. Equity: RSUs that vest over 4 years. What you will do: - Own backend services …',
    },
    {
      impact: -10,
      reason: 'High buzzword density, few concrete details',
      quote: '… on-call rotations - Ship features with product and design We need a rockstar who thrives on synergy and channels their inner ninja. We move in a fast-paced …',
    },
  ],
};

export function JdDemo() {
  const r = JD_RESULT;
  return (
    <DemoShell title="> jd decoder demo" label="Job-description decoder: red and green flags called out on a sample posting">
      <div className="jd-paper">
        <p className="jd-title">Senior Backend Engineer, StealthCo</p>
        <p className="jd-text">
          We are hiring a senior backend engineer for our{' '}
          <span className="hl-green">remote-first</span> team. Salary range:{' '}
          <span className="hl-green">$150k-$185k</span>.{' '}
          <span className="hl-green">Equity</span>: RSUs that vest over 4 years.
        </p>
        <p className="jd-text">
          What you will do: own backend services end to end; design Postgres
          schemas that survive scale; run weekly on-call rotations; ship
          features with product and design.
        </p>
        <p className="jd-text">
          We need a <span className="hl-red">rockstar</span> who thrives on{' '}
          <span className="hl-red">synergy</span> and channels their inner{' '}
          <span className="hl-red">ninja</span>. We move in a{' '}
          <span className="hl-red">fast-paced</span> environment where everyone{' '}
          <span className="hl-red">wear many hats</span>.{' '}
          <span className="hl-red">Unlimited PTO</span>, obviously.
        </p>
        <p className="jd-text">
          We offer <span className="hl-green">mentorship</span> from staff engineers.
        </p>
        <div className="jd-flags">
          <p>
            <Flag tone="go">
              + TRANSPARENCY: {r.transparency.score}/100 (salary range {r.transparency.salaryRaw}, equity concrete)
            </Flag>
          </p>
          {r.overwork.map((o) => (
            <p key={o.phrase}>
              <Flag tone="red">X CAUTION: &quot;{o.phrase}&quot;</Flag>
              <span className="jd-quote">&quot;{o.quote}&quot;</span>
              <span className="jd-read"> {o.read}</span>
            </p>
          ))}
          {r.greenFlags.map((g) => (
            <p key={g.flag}>
              <Flag tone="go">+ GREEN: {g.flag}</Flag>
              <span className="jd-quote">&quot;{g.quote}&quot;</span>
            </p>
          ))}
          <p>
            <Flag tone="go">+ GROWTH: {r.growth[0].signal}</Flag>
            <span className="jd-quote">&quot;{r.growth[0].quote}&quot;</span>
          </p>
          <p>
            <Flag tone="red">
              X VAGUENESS: density {r.buzzwordDensity}/100 words ({r.buzzwords.map((b) => `“${b}”`).join(', ')}, {r.responsibilities} responsibilities)
            </Flag>
          </p>
        </div>
        <p className="jd-verdict amber">
          VERDICT: {r.verdict.toUpperCase()} ({r.score}/100)
        </p>
        {r.reasons.map((x) => (
          <p className="jd-verdict amber" key={x.reason}>
            [{x.impact > 0 ? '+' : ''}{x.impact}] {x.reason}
            <span className="jd-quote"> &quot;{x.quote}&quot;</span>
          </p>
        ))}
      </div>
      <p className="idemo-foot">
        Flags above were produced by the real jd_decoder.py on this exact
        sample text, not hand-picked. Highlights match the engine&apos;s quotes.
      </p>
    </DemoShell>
  );
}

/* ---------------- Rejection autopsy ---------------- */

const FUNNEL = [
  { stage: 'Applied', n: 40 },
  { stage: 'Screening', n: 18 },
  { stage: 'Interview', n: 9 },
  { stage: 'Final', n: 3 },
  { stage: 'Offer', n: 1 },
];

export function AutopsyDemo() {
  return (
    <DemoShell title="> autopsy demo" label="Rejection autopsy: funnel visualization showing where applications leak">
      {FUNNEL.map((f, i) => {
        const prev = i === 0 ? f.n : FUNNEL[i - 1].n;
        const leak = i === 0 ? 0 : Math.round((1 - f.n / prev) * 100);
        const bigLeak = leak >= 50;
        return (
          <div key={f.stage} className="funnel-row">
            <Bar label={f.stage} value={f.n} max={40} tone={bigLeak ? 'red' : ''} />
            {bigLeak ? (
              <p className="funnel-leak">
                <Flag tone="red">X LEAK: {leak}% lost here</Flag>
              </p>
            ) : null}
          </div>
        );
      })}
      <p className="autopsy-rx">
        {'>'} DIAGNOSIS: 55% die at screening: run the grill on your resume and
        tighten tailoring before the next batch.
      </p>
      <p className="idemo-foot">Frank, not cruel. Rejections are data.</p>
    </DemoShell>
  );
}

/* ---------------- Streaks ---------------- */

const WEEK = [
  { d: 'M', n: 4 }, { d: 'T', n: 2 }, { d: 'W', n: 5 },
  { d: 'T', n: 0 }, { d: 'F', n: 3 }, { d: 'S', n: 6 }, { d: 'S', n: 1 },
];

export function StreakDemo() {
  const [copied, setCopied] = useState(false);
  const card =
    '12-day drill streak\n20 negotiation rounds (brutal)\n8 AI lessons this week\nLogged with Veto. Every number is a real rep.';
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(card);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };
  return (
    <DemoShell title="> streaks demo" label="Streaks and gamification: weekly rep grid plus a shareable progress card">
      <div className="week-grid">
        {WEEK.map((w, i) => (
          <div key={i} className="week-day">
            <div className="week-bar-track">
              <div className="week-bar" style={{ height: `${(w.n / 6) * 100}%` }} />
            </div>
            <span className="week-d">{w.d}</span>
            <span className="week-n">{w.n}</span>
          </div>
        ))}
      </div>
      <p className="streak-line">drills [##########--] 12-day streak · longest 21</p>
      <div className="share-card">
        <p className="share-head">SHARE CARD</p>
        <p className="share-body">{card}</p>
        <button type="button" className="px-btn ghost share-btn" onClick={copy}>
          {copied ? '+ Copied' : 'Copy card'}
        </button>
      </div>
      <p className="idemo-foot">
        The viral loop: cards are built only from real logged reps. Zero reps,
        zero card.
      </p>
    </DemoShell>
  );
}

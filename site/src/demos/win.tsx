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

export function JdDemo() {
  return (
    <DemoShell title="> jd decoder demo" label="Job-description decoder: red and green flags called out on a sample posting">
      <div className="jd-paper">
        <p className="jd-title">Senior Backend Engineer, StealthCo</p>
        <p className="jd-text">
          We are hiring a <span className="hl-green">salary range $150–185k</span> senior
          backend engineer for our <span className="hl-green">remote-first</span> platform
          team. You will own services end to end. We move in a{' '}
          <span className="hl-red">fast-paced environment</span> where everyone{' '}
          <span className="hl-red">wears many hats</span>. We are looking for a{' '}
          <span className="hl-red">rockstar</span> who thrives under pressure.
          <span className="hl-green"> Mentorship program + $3k learning budget.</span>{' '}
          <span className="hl-red">Unlimited PTO</span> (use it, we dare you).
        </p>
        <div className="jd-flags">
          <p><Flag tone="go">+ GREEN: salary transparency</Flag></p>
          <p><Flag tone="go">+ GREEN: remote-first, mentorship, learning budget</Flag></p>
          <p><Flag tone="red">X CAUTION: "fast-paced", "wear many hats": overwork language</Flag></p>
          <p><Flag tone="red">X CAUTION: "rockstar", "unlimited PTO": vagueness flags</Flag></p>
        </div>
        <p className="jd-verdict amber">VERDICT: MIXED, 3 green signals, 4 caution flags</p>
      </div>
      <p className="idemo-foot">
        Every flag ships with the exact quote. Evidence, not vibes.
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

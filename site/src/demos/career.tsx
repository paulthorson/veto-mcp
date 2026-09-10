/* TRAIN-set demos: LinkedIn optimizer, mock interview, negotiation sim. */
import { useState } from 'react';
import { DemoShell, Bar, Flag } from './shared';

/* ---------------- LinkedIn optimizer ---------------- */

const AUDIT = [
  { label: 'Headline', value: 62, tone: 'amber' as const, fix: 'No years, no proof. Add both.' },
  { label: 'About', value: 45, tone: 'red' as const, fix: 'No quantified results. No CTA.' },
  { label: 'Experience', value: 78, tone: '' as const, fix: 'Strong verbs; 2 bullets unquantified.' },
  { label: 'Skills', value: 81, tone: '' as const, fix: 'Missing: terraform, system design.' },
];

export function LinkedinDemo() {
  return (
    <DemoShell title="> linkedin audit demo" label="LinkedIn profile audit with score bars and a fact-grounded headline rewrite">
      {AUDIT.map((a) => (
        <div key={a.label} className="audit-row">
          <Bar label={a.label} value={a.value} tone={a.tone} />
          <p className="audit-fix">{'>'} {a.fix}</p>
        </div>
      ))}
      <div className="rewrite">
        <p className="rewrite-label">BEFORE</p>
        <p className="rewrite-before">Software Engineer | Open to opportunities</p>
        <p className="rewrite-label">AFTER: built only from profile facts</p>
        <p className="rewrite-after">
          Backend Engineer (5 yrs): Python, K8s, Postgres | ex-FintechCo
        </p>
      </div>
      <p className="idemo-foot">
        Rewrites interpolate profile facts only. No job, title, or number is
        ever invented.
      </p>
    </DemoShell>
  );
}

/* ---------------- Mock interview ---------------- */

const QA = [
  {
    q: 'Q1: Tell me about a system you scaled.',
    a: 'I led the migration of 12 services to Kubernetes, which cut deploy time by 40% and reduced incidents by 30% over two quarters.',
    fb: [
      { t: 'go', x: '+ STAR complete: situation, task, action, result all present' },
      { t: 'go', x: '+ Two hard numbers (40%, 30%), keep them verbatim' },
      { t: 'amber', x: '! Name the blast radius: how many engineers relied on it?' },
    ] as { t: 'go' | 'amber'; x: string }[],
  },
  {
    q: 'Q2: A time you disagreed with your manager.',
    a: 'We disagreed on the rollout plan. I gathered the deploy-failure data, made the case for a canary, and we shipped it safely.',
    fb: [
      { t: 'go', x: '+ Ownership: "I" not "we" on the decision' },
      { t: 'amber', x: '! Add the outcome number: what did the canary catch?' },
    ] as { t: 'go' | 'amber'; x: string }[],
  },
  {
    q: 'Q3: Why this company?',
    a: 'Your platform team owns the deploy path end to end, which is exactly where I have spent five years. The fintech scale is the draw.',
    fb: [
      { t: 'go', x: '+ Company-specific, not generic flattery' },
    ] as { t: 'go' | 'amber'; x: string }[],
  },
  {
    q: 'Q4: Design a rate limiter.',
    a: 'Token bucket in Redis, per-user keys, sliding window for burst control. Backed by a Lua script so the check-and-decrement is atomic.',
    fb: [
      { t: 'go', x: '+ Correct core choice with a concrete consistency reason' },
      { t: 'amber', x: '! Say the failure mode: what happens when Redis is down?' },
    ] as { t: 'go' | 'amber'; x: string }[],
  },
  {
    q: 'Q5: Where do you want to be in 3 years?',
    a: 'Leading a small platform team, still close to the systems, owning reliability end to end.',
    fb: [
      { t: 'go', x: '+ Credible and specific to the role' },
    ] as { t: 'go' | 'amber'; x: string }[],
  },
];

export function InterviewDemo() {
  const [open, setOpen] = useState<number | null>(0);
  return (
    <DemoShell title="> mock interview demo" label="Mock interview: five questions with STAR feedback annotations">
      <div className="qa-list">
        {QA.map((item, i) => (
          <div key={i} className="qa-item">
            <button
              type="button"
              className="qa-q"
              onClick={() => setOpen(open === i ? null : i)}
              aria-expanded={open === i}
            >
              {item.q}
              <span aria-hidden="true">{open === i ? '[–]' : '[+]'}</span>
            </button>
            {open === i && (
              <div className="qa-a">
                <p className="qa-answer">{item.a}</p>
                {item.fb.map((f, j) => (
                  <p key={j} className="qa-fb">
                    <Flag tone={f.t === 'go' ? 'go' : 'amber'}>{f.x}</Flag>
                  </p>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      <p className="idemo-foot">
        Sessions persist locally. WhatsApp-compatible output. Practice from
        your phone.
      </p>
    </DemoShell>
  );
}

/* ---------------- Negotiation sim ---------------- */

const ROUNDS = [
  {
    who: 'ROUND 1: AI hiring manager (brutal)',
    lines: [
      { s: 'ai', t: '"We can do 150 base. That is already above band for this level."' },
      { s: 'you', t: '"Based on the scope, owning the deploy path for 200 engineers, I am targeting 175 base."' },
      { s: 'ai', t: '"Scope is aspirational until you prove it. 155, and we are being generous."' },
    ],
    coach: 'COACH: Good, you anchored on scope, not need. Do not defend; ask what 175 would need to look like. Make them name the gap.',
  },
  {
    who: 'ROUND 2: AI hiring manager (brutal)',
    lines: [
      { s: 'you', t: '"What would someone at 175 be delivering in the first two quarters that I am not promising now?"' },
      { s: 'ai', t: '"...A signed-off migration plan for the legacy monolith by Q2. Fine. 165 base, 20 signing, if you commit to that plan."' },
      { s: 'you', t: '"165 base, 25 signing, and the plan is my Q1 deliverable in writing."' },
    ],
    coach: 'COACH: Excellent, you turned their pushback into a written commitment and traded it for cash. That is the whole game.',
  },
];

export function NegotiationDemo() {
  return (
    <DemoShell title="> negotiation sim demo" label="Adversarial negotiation simulator: a brutal-difficulty exchange with coach feedback">
      {ROUNDS.map((r, i) => (
        <div key={i} className="nego-round">
          <p className="nego-who">{r.who}</p>
          {r.lines.map((l, j) => (
            <p key={j} className={`chat-line ${l.s}`}>
              {l.t}
            </p>
          ))}
          <p className="coach-note">{r.coach}</p>
        </div>
      ))}
      <p className="idemo-foot">
        Three rounds, three difficulties: firm, hardball, brutal. The AI attacks
        your arguments. Never you.
      </p>
    </DemoShell>
  );
}

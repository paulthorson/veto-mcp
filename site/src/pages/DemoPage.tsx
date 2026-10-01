import { useEffect, useMemo, useRef, useState } from 'react';
import { Card, Heading } from '@astryxdesign/core';
import { PxTag, PxBtn, SITE_URL } from '../px';

/* ------------------------------------------------------------------ */
/* Interactive demo: answer the grill for a fake posting. Most people  */
/* get vetoed. That's the point.                                       */
/*                                                                     */
/* Three levels, picked up front:                                      */
/* - friendly: the 60-second taste (the original 3-question grill).    */
/* - standard: the FULL untruncated run-through — 5 questions asked    */
/*   one at a time, chat-style, with follow-ups that react to answers, */
/*   then honesty check, scoring, tailoring preview, verdict, share,   */
/*   and the verdict-ledger entry.                                     */
/* - brutal: the same full pipeline, adversarial — sharper follow-ups, */
/*   inflated claims get flagged, the bar is higher.                   */
/*                                                                     */
/* Scroll anchoring: answering swaps in a shorter/taller block while   */
/* scrollY stays pinned, which used to flash the footer into view.     */
/* useSwapAnchor captures the block height before a stage swap and     */
/* compensates scrollY by the delta (instant), keeping content stable. */
/* ------------------------------------------------------------------ */

import {
  FULL_QUESTIONS,
  classifyAnswer,
  computeFullResult,
  type FullAnswer,
  type GrillQuestion,
  type Level,
} from "../lib/demoGrill";

type Verdict = { pass: false; reason: string } | { pass: true };

const JOB = {
  title: 'Staff Backend Engineer',
  company: 'Fintech (series C, definitely real)',
  location: 'New York, NY',
  needs: ['8+ years backend experience', 'Kubernetes in production', 'US work authorization'],
};

const YEAR_OPTIONS = ['0–2', '3–5', '6–7', '8+'];

/* ---------------- Share ---------------- */

function ShareLinks({
  level,
  vetoed,
  reason,
  score,
}: {
  level: Level;
  vetoed: boolean;
  reason: string;
  score?: number;
}) {
  const levelName = level === 'friendly' ? '' : level === 'brutal' ? 'BRUTAL ' : 'FULL ';
  const text = vetoed
    ? level === 'friendly'
      ? `I got VETOED by the job bot that says no: "${reason}" Think you can pass the grill? ${SITE_URL}/#/demo`
      : level === 'brutal'
        ? `The BRUTAL Veto grill said no: "${reason}" It's the one that says no. Think you can pass it? ${SITE_URL}/#/demo`
        : `I ran the FULL Veto grill — 5 questions, honesty check, scoring — and got VETOED: "${reason}" Think you can pass? ${SITE_URL}/#/demo`
    : level === 'friendly'
      ? `I survived the Veto grill with zero vetoes. Suspicious. Try it: ${SITE_URL}/#/demo`
      : `I survived the ${levelName}Veto grill: ${score ?? '?'}/100, zero vetoes. Suspicious. Think you can beat it? ${SITE_URL}/#/demo`;
  const xUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}`;
  return (
    <div className="demo-share">
      <PxBtn variant="secondary" href={xUrl} label="Share your verdict on X" target="_blank">
        Share on X
      </PxBtn>
    </div>
  );
}

/* ---------------- Job card (shared by all levels) ---------------- */

function JobCard() {
  return (
    <Card className="demo-job">
      <PxTag variant="amber">The posting</PxTag>
      <Heading level={2} className="demo-job-title">
        {JOB.title}
      </Heading>
      <p className="demo-job-meta">
        {JOB.company} · {JOB.location}
      </p>
      <ul className="demo-needs">
        {JOB.needs.map((n) => (
          <li key={n}>{'>'} {n}</li>
        ))}
      </ul>
    </Card>
  );
}

/* ---------------- Scroll-anchored stage swaps ---------------- */

function useSwapAnchor(dep: unknown) {
  const swapRef = useRef<HTMLDivElement | null>(null);
  const swapHeight = useRef<number | null>(null);
  useEffect(() => {
    const el = swapRef.current;
    const oldH = swapHeight.current;
    swapHeight.current = null;
    if (el && oldH != null) {
      const dh = el.offsetHeight - oldH;
      if (dh !== 0) window.scrollBy({ top: dh, behavior: 'instant' });
    }
  }, [dep]);
  return {
    swapRef,
    markSwap: () => {
      swapHeight.current = swapRef.current?.offsetHeight ?? null;
    },
  };
}

/* ---------------- Friendly: the 60-second taste ---------------- */
/* The original 3-question quick grill, behavior and copy preserved. */

function friendlyVerdict(years: string, k8s: boolean, auth: boolean): Verdict {
  if (years !== '8+')
    return {
      pass: false,
      reason: `needs 8+ yrs backend, you reported ${years}. Not applying.`,
    };
  if (!k8s)
    return {
      pass: false,
      reason: 'requires production Kubernetes experience. You have none. Not applying.',
    };
  if (!auth)
    return {
      pass: false,
      reason: 'requires US work authorization. Not applying.',
    };
  return { pass: true };
}

function FriendlyGrill({ onSwitchLevel }: { onSwitchLevel: () => void }) {
  const [step, setStep] = useState(0); // 0..2 questions, 3 = verdict
  const [years, setYears] = useState<string | null>(null);
  const [k8s, setK8s] = useState<boolean | null>(null);
  const [auth, setAuth] = useState<boolean | null>(null);

  const { swapRef, markSwap } = useSwapAnchor(step);
  const goStep = (next: number) => {
    markSwap();
    setStep(next);
  };

  const reset = () => {
    setYears(null);
    setK8s(null);
    setAuth(null);
    goStep(0);
  };

  const verdict: Verdict | null =
    step === 3 ? friendlyVerdict(years ?? '0–2', k8s ?? false, auth ?? false) : null;

  return (
    <>
      <JobCard />
      {step < 3 ? (
        <div className="demo-grill" ref={swapRef}>
          <p className="demo-step">Grill question {step + 1} of 3</p>

          {step === 0 && (
            <Card className="demo-q">
              <Heading level={3} className="feature-title">
                How many years of backend experience do you have?
              </Heading>
              <div className="demo-opts">
                {YEAR_OPTIONS.map((o) => (
                  <button
                    key={o}
                    className="demo-opt"
                    onClick={() => {
                      setYears(o);
                      goStep(1);
                    }}
                  >
                    {o}
                  </button>
                ))}
              </div>
            </Card>
          )}

          {step === 1 && (
            <Card className="demo-q">
              <Heading level={3} className="feature-title">
                Have you run Kubernetes in production?
              </Heading>
              <div className="demo-opts">
                <button
                  className="demo-opt"
                  onClick={() => {
                    setK8s(true);
                    goStep(2);
                  }}
                >
                  Yes
                </button>
                <button
                  className="demo-opt"
                  onClick={() => {
                    setK8s(false);
                    goStep(2);
                  }}
                >
                  No
                </button>
              </div>
            </Card>
          )}

          {step === 2 && (
            <Card className="demo-q">
              <Heading level={3} className="feature-title">
                Are you authorized to work in the US?
              </Heading>
              <div className="demo-opts">
                <button
                  className="demo-opt"
                  onClick={() => {
                    setAuth(true);
                    goStep(3);
                  }}
                >
                  Yes
                </button>
                <button
                  className="demo-opt"
                  onClick={() => {
                    setAuth(false);
                    goStep(3);
                  }}
                >
                  No
                </button>
              </div>
              <p className="demo-fine">
                (In the real grill these arrive over WhatsApp, and your answers shape the resume tailoring.)
              </p>
            </Card>
          )}
        </div>
      ) : (
        verdict && (
          <div className="demo-verdict" ref={swapRef}>
            {verdict.pass ? (
              <Card className="demo-pass">
                <div className="demo-verdict-mark go" aria-hidden="true">
                  +
                </div>
                <Heading level={3} className="feature-title">
                  No veto.
                </Heading>
                <p className="feature-body">
                  Veto found nothing to complain about. Suspicious. But clean. In the real tool you&rsquo;d
                  still review and confirm before anything is recorded.
                </p>
              </Card>
            ) : (
              <div className="demo-veto-term" role="img" aria-label={`Vetoed: ${verdict.reason}`}>
                <div className="terminal-bar">
                  <span className="dot r" />
                  <span className="dot y" />
                  <span className="dot g" />
                  <span className="terminal-title">veto - zsh</span>
                </div>
                <div className="terminal-body">
                  <div className="tline t-info">{'>'} grill: 3/3 answered +</div>
                  <div className="tline t-info">{'>'} friendly rules: 3 questions, instant veto on a miss +</div>
                  <div className="tline t-veto">X VETOED: {verdict.reason}</div>
                </div>
              </div>
            )}
            <ShareLinks level="friendly" vetoed={!verdict.pass} reason={!verdict.pass ? verdict.reason : ''} />
            <div className="demo-again">
              <button className="demo-opt" onClick={reset}>
                {'>'} Play again
              </button>
              <button className="demo-opt" onClick={onSwitchLevel}>
                {'>'} Switch level
              </button>
              <a className="demo-docs" href="#/features/the-grill">
                How the real grill works&nbsp;{'>'}
              </a>
            </div>
          </div>
        )
      )}
    </>
  );
}

/* ---------------- Standard / Brutal: the full untruncated run ---------------- */
/* Grill (5 questions, chat-style, one at a time, reactive follow-ups) ->      */
/* honesty check -> qualification scoring -> tailoring preview -> verdict ->    */
/* share -> verdict ledger. Brutal uses sharper follow-ups (2 deep), stricter  */
/* scoring, and more veto paths.                                               */

type Stage = 'grill' | 'honesty' | 'score' | 'tailor' | 'verdict' | 'ledger';

const STAGE_ORDER: Stage[] = ['grill', 'honesty', 'score', 'tailor', 'verdict', 'ledger'];
const STAGE_LABEL: Record<Stage, string> = {
  grill: 'The grill',
  honesty: 'Honesty check',
  score: 'Qualification scoring',
  tailor: 'Tailoring preview',
  verdict: 'Verdict',
  ledger: 'Verdict ledger',
};

interface ChatMsg {
  id: number;
  from: 'veto' | 'you';
  text: string;
  tag: string;
}

/* Double-submit throttle — the exact rule: a submit is dropped only if it
   is (1) within `ms` of the previous ACCEPTED submit, AND (2) carries the
   same prompt key, AND (3) carries the same normalized text (trimmed — the
   same normalization the classifier uses, where quick-picks match by exact
   label). The prompt key is `${qid}:${depth}`, where `depth` is the
   follow-up depth of the rendered prompt being answered (0 for the base
   question, 1 for follow-up #1, 2 for follow-up #2). Each rendered prompt
   is a distinct identity, so re-answering a NEW follow-up prompt with the
   same text is always accepted, even within `ms` — that is a legitimate,
   explicitly-supported interaction (the defiant path: the answer is
   recorded, "filed as unverified"), never an accidental double-click. The
   one dropped case is a true accidental double-click / double-Enter
   re-sending the same answer to the SAME rendered prompt. A different text,
   a different question, or a different follow-up depth is always accepted,
   no matter how fast it arrives, so rapid-but-distinct answers are never
   silently swallowed. Date.now() is only a timer — it never feeds scoring,
   which stays deterministic. */
function throttleSubmit(
  last: { current: { time: number; key: string; text: string } | null },
  ms: number,
  promptKey: string,
  text: string,
): boolean {
  const now = Date.now();
  const prev = last.current;
  if (prev !== null && now - prev.time < ms && prev.key === promptKey && prev.text === text) {
    return true;
  }
  last.current = { time: now, key: promptKey, text };
  return false;
}

function FullGrill({
  level,
  onSwitchLevel,
}: {
  level: 'standard' | 'brutal';
  onSwitchLevel: () => void;
}) {
  const [stage, setStage] = useState<Stage>('grill');
  const [qi, setQi] = useState(0);
  const [depth, setDepth] = useState(0);
  const [msgs, setMsgs] = useState<ChatMsg[]>([
    {
      id: 0,
      from: 'veto',
      text: FULL_QUESTIONS[0].text,
      tag: `Q1 · ${FULL_QUESTIONS[0].type}`,
    },
  ]);
  const [answers, setAnswers] = useState<FullAnswer[]>([]);
  const [draft, setDraft] = useState('');
  const idRef = useRef(1);

  const { swapRef, markSwap } = useSwapAnchor(stage);
  const chatRef = useRef<HTMLDivElement | null>(null);
  const lastSubmitRef = useRef<{ time: number; key: string; text: string } | null>(null);

  const maxDepth = level === 'brutal' ? 2 : 1;
  const q = FULL_QUESTIONS[qi];
  const done = answers.length === FULL_QUESTIONS.length;

  /* Keep the newest exchange in view as the conversation scrolls. */
  useEffect(() => {
    const el = chatRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [msgs.length]);

  const result = useMemo(
    () => (done ? computeFullResult(level, answers) : null),
    [done, level, answers],
  );

  const goStage = (next: Stage) => {
    markSwap();
    setStage(next);
  };

  const followupText = (fq: GrillQuestion, nd: number): string =>
    nd === 1 ? (level === 'brutal' ? fq.followupBrutal : fq.followup) : fq.followupBrutalLast;

  const submit = (raw: string) => {
    if (done) return;
    const text = raw.trim();
    /* Empty submit is a no-op: nothing recorded, nothing advanced,
       no follow-up consumed. */
    if (text === '') return;
    /* The prompt key is the rendered prompt's identity: question id plus
       the follow-up depth the player is currently answering (0 = base
       question). A re-answer to a NEW follow-up prompt always gets a new
       key, so it can never be mistaken for a double-click on the old one. */
    if (throttleSubmit(lastSubmitRef, 300, `${q.id}:${depth}`, text)) return;
    const cls = classifyAnswer(q.id, text);
    const nd = depth + 1;
    const youId = idRef.current++;
    const vetoId = idRef.current++;
    setMsgs((prev) => [...prev, { id: youId, from: 'you', text, tag: 'you' }]);
    if (cls === 'specific' || nd > maxDepth) {
      const rec: FullAnswer = { qid: q.id, text, cls };
      const nextAnswers = [...answers, rec];
      setAnswers(nextAnswers);
      if (qi + 1 < FULL_QUESTIONS.length) {
        const nq = FULL_QUESTIONS[qi + 1];
        setMsgs((prev) => [
          ...prev,
          { id: vetoId, from: 'veto', text: nq.text, tag: `Q${qi + 2} · ${nq.type}` },
        ]);
        setQi(qi + 1);
        setDepth(0);
      } else {
        setMsgs((prev) => [
          ...prev,
          {
            id: vetoId,
            from: 'veto',
            text: '> Grill complete. 5/5 answered. Running the honesty check next.',
            tag: 'system',
          },
        ]);
      }
    } else {
      setMsgs((prev) => [
        ...prev,
        { id: vetoId, from: 'veto', text: followupText(q, nd), tag: 'follow-up' },
      ]);
      setDepth(nd);
    }
    setDraft('');
  };

  const restart = () => {
    markSwap();
    setStage('grill');
    setQi(0);
    setDepth(0);
    setAnswers([]);
    setDraft('');
    /* Fresh run = fresh prompt identities: the throttle must not mistake
       the restarted base prompt for a double-submit of the old run. */
    lastSubmitRef.current = null;
    setMsgs([
      {
        id: idRef.current++,
        from: 'veto',
        text: FULL_QUESTIONS[0].text,
        tag: `Q1 · ${FULL_QUESTIONS[0].type}`,
      },
    ]);
  };

  const stageIdx = STAGE_ORDER.indexOf(stage);

  return (
    <>
      <JobCard />
      <div ref={swapRef}>
        <p className="demo-step">
          Stage {stageIdx + 1} of 6 — {STAGE_LABEL[stage]}
          {level === 'brutal' && ' · brutal rules in effect'}
        </p>

        {stage === 'grill' && (
          <div className="demo-chat-wrap">
            <div className="demo-chat" ref={chatRef} aria-label="Grill conversation">
              {msgs.map((m, i) => (
                /* Only the newest message is a live region: announcing the
                   whole log on every message re-reads the entire
                   conversation to screen readers. */
                <div
                  key={m.id}
                  className={`demo-msg ${m.from === 'veto' ? (m.tag === 'follow-up' ? 'q followup' : 'q') : 'a'}`}
                  aria-live={i === msgs.length - 1 ? 'polite' : undefined}
                >
                  <span className="demo-msg-tag">{m.from === 'veto' ? `veto · ${m.tag}` : m.tag}</span>
                  <span className="demo-msg-text">{m.text}</span>
                </div>
              ))}
            </div>
            {!done && (
              <>
                <div className="demo-opts demo-picks">
                  {q.picks.map((p) => (
                    <button key={p.label} className="demo-opt" onClick={() => submit(p.label)}>
                      {p.label}
                    </button>
                  ))}
                </div>
                <div className="demo-answer-row">
                  <input
                    className="demo-input"
                    type="text"
                    value={draft}
                    placeholder={q.placeholder}
                    aria-label={`Your answer to: ${q.text}`}
                    onChange={(e) => setDraft(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') submit(draft);
                    }}
                  />
                  <button className="demo-opt demo-send" onClick={() => submit(draft)} aria-label="Send answer">
                    Send
                  </button>
                </div>
                <p className="demo-fine">
                  {depth > 0
                    ? 'Veto pushed back — answer the follow-up.'
                    : '(In the real grill these arrive over WhatsApp, and your answers shape the resume tailoring.)'}
                </p>
              </>
            )}
            {done && (
              <div className="demo-opts">
                <button className="demo-opt" onClick={() => goStage('honesty')}>
                  {'>'} Run the honesty check
                </button>
              </div>
            )}
            <div className="demo-again">
              <button className="demo-opt" onClick={onSwitchLevel}>
                {'>'} Switch level
              </button>
            </div>
          </div>
        )}

        {stage === 'honesty' && result && (
          <>
            <div className="demo-honesty" role="img" aria-label={`Honesty check: ${result.verified} verified, ${result.unverified} unverified`}>
              <div className="terminal-bar">
                <span className="dot r" />
                <span className="dot y" />
                <span className="dot g" />
                <span className="terminal-title">veto — honesty check</span>
              </div>
              <div className="terminal-body">
                <div className="tline t-info">{'>'} honesty check: scanning 5 answers for invented skills…</div>
                {result.checks.map((c, i) => (
                  <div key={i} className={`tline ${c.ok ? 't-ok' : 't-veto'}`}>
                    {c.text}
                  </div>
                ))}
                {result.flags.map((f, i) => (
                  <div key={`f${i}`} className="tline t-warn">
                    {f}
                  </div>
                ))}
                <div className="tline t-info">
                  {'>'} honesty: {result.verified} verified, {result.unverified} unverified{' '}
                  {result.unverified === 0 ? '+' : 'X'}
                </div>
              </div>
            </div>
            <div className="demo-opts">
              <button className="demo-opt" onClick={() => goStage('score')}>
                {'>'} See the scoring
              </button>
            </div>
            <div className="demo-again">
              <button className="demo-opt" onClick={onSwitchLevel}>
                {'>'} Switch level
              </button>
            </div>
          </>
        )}

        {stage === 'score' && result && (
          <>
            <Card className="demo-score">
              {result.factors.map((f) => (
                <div className="demo-score-row" key={f.label}>
                  <span className="demo-score-label">{f.label}</span>
                  <span className="demo-score-pts">
                    {f.pts}/{f.max}
                  </span>
                  <div className="demo-score-bar" aria-hidden="true">
                    <div
                      className="demo-score-fill"
                      style={{ width: `${(f.pts / f.max) * 100}%` }}
                    />
                  </div>
                  <p className="demo-score-note">{f.note}</p>
                </div>
              ))}
              {result.penalty > 0 && (
                <p className="demo-score-note t-warn">
                  Brutal penalty: −{result.penalty} for unverified claims.
                </p>
              )}
              <p className="demo-score-total">
                Fit: {result.score}/100 <span className="demo-score-bar-note">(bar: {result.bar})</span>
              </p>
            </Card>
            <div className="demo-opts">
              <button className="demo-opt" onClick={() => goStage('tailor')}>
                {'>'} Preview the tailoring
              </button>
            </div>
            <div className="demo-again">
              <button className="demo-opt" onClick={onSwitchLevel}>
                {'>'} Switch level
              </button>
            </div>
          </>
        )}

        {stage === 'tailor' && result && (
          <>
            {!result.pass && (
              <p className="demo-fine">
                Vetoed applications don’t get tailored — this is what the pipeline skipped.
              </p>
            )}
            <Card className="demo-tailor">
              <p className="demo-tailor-label">Before — the generic bullet</p>
              <p className="demo-tailor-before">{result.tailoringBefore}</p>
              <p className="demo-tailor-label">After — tailored from your grill answers</p>
              <p className="demo-tailor-after">{result.tailoringAfter}</p>
            </Card>
            <div className="demo-opts">
              <button className="demo-opt" onClick={() => goStage('verdict')}>
                {'>'} Get the verdict
              </button>
            </div>
            <div className="demo-again">
              <button className="demo-opt" onClick={onSwitchLevel}>
                {'>'} Switch level
              </button>
            </div>
          </>
        )}

        {stage === 'verdict' && result && (
          <div className="demo-verdict">
            {result.pass ? (
              <Card
                className="demo-pass"
                role="img"
                aria-label={`No veto: passed the ${level} grill with fit score ${result.score} out of 100`}
              >
                <div className="demo-verdict-mark go" aria-hidden="true">
                  +
                </div>
                <Heading level={3} className="feature-title">
                  No veto.
                </Heading>
                <p className="feature-body">
                  Fit score {result.score}/100 — clears the {result.bar} bar. Veto found nothing to
                  complain about. Suspicious. But clean. In the real tool you&rsquo;d still review and
                  confirm before anything is recorded.
                </p>
              </Card>
            ) : (
              <div className="demo-veto-term" role="img" aria-label={`Vetoed: ${result.reason}`}>
                <div className="terminal-bar">
                  <span className="dot r" />
                  <span className="dot y" />
                  <span className="dot g" />
                  <span className="terminal-title">veto - zsh</span>
                </div>
                <div className="terminal-body">
                  <div className="tline t-info">{'>'} grill: 5/5 answered +</div>
                  <div className="tline t-info">
                    {'>'} honesty check: {result.verified} verified, {result.unverified} unverified{' '}
                    {result.unverified === 0 ? '+' : 'X'}
                  </div>
                  <div className="tline t-info">
                    {'>'} fit score: {result.score}/100 (bar: {result.bar}) +
                  </div>
                  <div className="tline t-veto">X VETOED: {result.reason}</div>
                </div>
              </div>
            )}
            <ShareLinks level={level} vetoed={!result.pass} reason={result.reason} score={result.score} />
            <div className="demo-opts">
              <button className="demo-opt" onClick={() => goStage('ledger')}>
                {'>'} Record the verdict
              </button>
            </div>
            <div className="demo-again">
              <button className="demo-opt" onClick={restart}>
                {'>'} Play again
              </button>
              <button className="demo-opt" onClick={onSwitchLevel}>
                {'>'} Switch level
              </button>
            </div>
          </div>
        )}

        {stage === 'ledger' && result && (
          <LedgerStage result={result} onRestart={restart} onSwitchLevel={onSwitchLevel} />
        )}
      </div>
    </>
  );
}

/* ---------------- Verdict ledger ---------------- */
/* The stamp is computed ONCE when this stage mounts (useState          */
/* initializer) — the actual verdict timestamp, not a value recomputed */
/* on every parent render.                                             */

function LedgerStage({
  result,
  onRestart,
  onSwitchLevel,
}: {
  result: ReturnType<typeof computeFullResult>;
  onRestart: () => void;
  onSwitchLevel: () => void;
}) {
  const [stamp] = useState(() =>
    new Date().toLocaleString('en-US', {
      timeZone: 'America/New_York',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    }),
  );
  return (
    <>
      <div className="demo-ledger" role="img" aria-label={`Verdict ledger entry: ${result.pass ? 'no veto' : 'vetoed'}, score ${result.score} out of 100`}>
        <div className="terminal-bar">
          <span className="dot r" />
          <span className="dot y" />
          <span className="dot g" />
          <span className="terminal-title">veto — verdict ledger</span>
        </div>
        <div className="terminal-body">
          <div className="tline t-info">{'>'} verdict ledger — appending entry…</div>
          <div className="tline t-cmd">ts: {stamp} ET</div>
          <div className="tline t-cmd">job: Staff Backend Engineer (fintech)</div>
          <div className="tline t-cmd">level: {result.level}</div>
          <div className="tline t-cmd">verdict: {result.pass ? 'NO VETO' : 'VETOED'}</div>
          <div className="tline t-cmd">score: {result.score}/100</div>
          <div className="tline t-cmd">reason: {result.pass ? '—' : result.reason}</div>
          <div className="tline t-ok">+ appended to verdict-ledger.jsonl</div>
        </div>
      </div>
      <p className="demo-fine">
        (Mock entry — the real ledger lives in the CLI. This is the end-to-end loop: grill →
        honesty → scoring → tailoring → verdict → recorded.)
      </p>
      <div className="demo-again">
        <button className="demo-opt" onClick={onRestart}>
          {'>'} Play again
        </button>
        <button className="demo-opt" onClick={onSwitchLevel}>
          {'>'} Switch level
        </button>
        <a className="demo-docs" href="#/features/the-grill">
          How the real grill works&nbsp;{'>'}
        </a>
      </div>
    </>
  );
}

/* ---------------- Level select ---------------- */

const LEVELS: {
  id: Exclude<Level, 'friendly'> | 'friendly';
  kicker: string;
  name: string;
  desc: string;
  len: string;
}[] = [
  {
    id: 'friendly',
    kicker: 'Teaser',
    name: 'Friendly',
    desc: 'The 60-second taste: 3 quick questions and the verdict. A teaser — nothing more.',
    len: '~1 minute',
  },
  {
    id: 'standard',
    kicker: 'Full run-through',
    name: 'Standard',
    desc: 'Nothing cut off: all 5 questions, chat-style, with follow-ups that react to your answers — then honesty check, scoring, tailoring preview, verdict, and the ledger entry.',
    len: '~4 minutes',
  },
  {
    id: 'brutal',
    kicker: 'Adversarial',
    name: 'Brutal',
    desc: 'The same full pipeline, but sharper: vague answers get interrogated, inflated claims get flagged, the bar is higher. This is the one that says no.',
    len: '~5 minutes',
  },
];

function LevelSelect({ onPick }: { onPick: (level: Level) => void }) {
  return (
    <>
      <div className="demo-levels">
        {LEVELS.map((l) => (
          <button key={l.id} className="demo-level" onClick={() => onPick(l.id)}>
            <span className="demo-level-kicker">{l.kicker}</span>
            <span className="demo-level-name">{l.name}</span>
            <span className="demo-level-desc">{l.desc}</span>
            <span className="demo-level-len">{l.len}</span>
          </button>
        ))}
      </div>
      <p className="demo-level-note">
        Standard and Brutal are the full, untruncated grill. Friendly is just the taste — the contrast
        is the point.
      </p>
    </>
  );
}

/* ---------------- Page ---------------- */

export default function DemoPage() {
  const [level, setLevel] = useState<Level | null>(null);
  const { swapRef, markSwap } = useSwapAnchor(level);

  const pick = (l: Level | null) => {
    if (l != null) {
      /* Entering a run: jump to the top; no anchor compensation wanted. */
      setLevel(l);
      window.scrollTo({ top: 0, behavior: 'instant' });
    } else {
      /* Back to the level select: anchor the swap so the footer never flashes. */
      markSwap();
      setLevel(l);
    }
  };

  return (
    <div className="page">
      <main>
        <section className="hero page-hero">
          <div className="wrap">
            <a className="back-link" href="#/">
              {'<'} Home
            </a>
            <PxTag variant="red">Interactive demo</PxTag>
            <Heading level={1} className="hero-title page-title">
              Get vetoed<span className="no">.</span>
            </Heading>
            <p className="hero-sub">
              Pick your pain. Three ways to take the grill — a 60-second taste, or the full
              untruncated run-through. Below is a fake posting with real standards. Answer
              honestly. Most people get vetoed. That&rsquo;s the product working.
            </p>
          </div>
        </section>

        <section className="section demo-sec">
          <div className="wrap narrow" ref={swapRef}>
            {level == null && <LevelSelect onPick={pick} />}
            {level === 'friendly' && <FriendlyGrill onSwitchLevel={() => pick(null)} />}
            {(level === 'standard' || level === 'brutal') && (
              <FullGrill level={level} onSwitchLevel={() => pick(null)} />
            )}
          </div>
        </section>

        <section className="section cta">
          <div className="wrap narrow cta-inner">
            <p className="game-over">- insert coin -</p>
            <Heading level={2} className="section-title">
              Now try it on real jobs.
            </Heading>
            <div className="hero-ctas center">
              <PxBtn variant="primary" href="#/install" label="Start with one job">
                {'>'} Start with one job
              </PxBtn>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

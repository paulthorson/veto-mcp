import { useState } from 'react';
import { Card, Heading } from '@astryxdesign/core';
import { PxTag, PxBtn, SITE_URL } from '../px';

/* ------------------------------------------------------------------ */
/* Interactive demo: answer the grill for a fake posting. Most people  */
/* get vetoed. That's the point.                                       */
/* ------------------------------------------------------------------ */

type Verdict =
  | { pass: false; reason: string }
  | { pass: true };

const JOB = {
  title: 'Staff Backend Engineer',
  company: 'Fintech (series C, definitely real)',
  location: 'New York, NY',
  needs: ['8+ years backend experience', 'Kubernetes in production', 'US work authorization'],
};

const YEAR_OPTIONS = ['0–2', '3–5', '6–7', '8+'];

function computeVerdict(years: string, k8s: boolean, auth: boolean): Verdict {
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

function ShareLinks({ vetoed, reason }: { vetoed: boolean; reason: string }) {
  const text = vetoed
    ? `I got VETOED by the job bot that says no: "${reason}" Think you can pass the grill? ${SITE_URL}/#/demo`
    : `I survived the Veto grill with zero vetoes. Suspicious. Try it: ${SITE_URL}/#/demo`;
  const xUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}`;
  return (
    <div className="demo-share">
      <PxBtn variant="secondary" href={xUrl} label="Share your verdict on X" target="_blank">
        Share on X
      </PxBtn>
    </div>
  );
}

export default function DemoPage() {
  const [step, setStep] = useState(0); // 0..2 questions, 3 = verdict
  const [years, setYears] = useState<string | null>(null);
  const [k8s, setK8s] = useState<boolean | null>(null);
  const [auth, setAuth] = useState<boolean | null>(null);

  const reset = () => {
    setStep(0);
    setYears(null);
    setK8s(null);
    setAuth(null);
  };

  const verdict: Verdict | null =
    step === 3 ? computeVerdict(years ?? '0–2', k8s ?? false, auth ?? false) : null;

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
              A real Veto grill, shrunk to three questions. Below is a fake
              posting with real standards. Answer honestly. Most people get
              refused. That&rsquo;s the product working.
            </p>
          </div>
        </section>

        <section className="section demo-sec">
          <div className="wrap narrow">
            {/* Job card */}
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

            {/* Grill */}
            {step < 3 ? (
              <div className="demo-grill">
                <p className="demo-step">
                  Grill question {step + 1} of 3
                </p>

                {step === 0 && (
                  <Card className="demo-q">
                    <Heading level={3} className="feature-title">
                      How many years of backend experience do you have?
                    </Heading>
                    <div className="demo-opts">
                      {YEAR_OPTIONS.map((o) => (
                        <button
                          key={o}
                          className={`demo-opt ${years === o ? 'sel' : ''}`}
                          onClick={() => {
                            setYears(o);
                            setStep(1);
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
                          setStep(2);
                        }}
                      >
                        Yes
                      </button>
                      <button
                        className="demo-opt"
                        onClick={() => {
                          setK8s(false);
                          setStep(2);
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
                          setStep(3);
                        }}
                      >
                        Yes
                      </button>
                      <button
                        className="demo-opt"
                        onClick={() => {
                          setAuth(false);
                          setStep(3);
                        }}
                      >
                        No
                      </button>
                    </div>
                    <p className="demo-fine">
                      (In the real grill these arrive over WhatsApp, and your
                      answers shape the resume tailoring.)
                    </p>
                  </Card>
                )}
              </div>
            ) : (
              verdict && (
                <div className="demo-verdict">
                  {verdict.pass ? (
                    <Card className="demo-pass">
                      <div className="demo-verdict-mark go" aria-hidden="true">
                        +
                      </div>
                      <Heading level={3} className="feature-title">
                        No veto.
                      </Heading>
                      <p className="feature-body">
                        Veto found nothing to complain about. Suspicious. But
                        clean. In the real tool you&rsquo;d still review and
                        confirm before anything is recorded.
                      </p>
                    </Card>
                  ) : (
                    <div className="demo-veto-term" role="img" aria-label={`Vetoed: ${verdict.reason}`}>
                      <div className="terminal-bar">
                        <span className="dot r" />
                        <span className="dot y" />
                        <span className="dot g" />
                        <span className="terminal-title">veto — zsh</span>
                      </div>
                      <div className="terminal-body">
                        <div className="tline t-info">{'>'} grill: 3/3 answered +</div>
                        <div className="tline t-info">{'>'} honesty check: no invented skills +</div>
                        <div className="tline t-veto">X VETOED: {verdict.reason}</div>
                      </div>
                    </div>
                  )}
                  <ShareLinks vetoed={!verdict.pass} reason={!verdict.pass ? verdict.reason : ''} />
                  <div className="demo-again">
                    <button className="demo-opt" onClick={reset}>
                      {'>'} Play again
                    </button>
                    <a className="demo-docs" href="#/features/the-grill">
                      How the real grill works {'>'}
                    </a>
                  </div>
                </div>
              )
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

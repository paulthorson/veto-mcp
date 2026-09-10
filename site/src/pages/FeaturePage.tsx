import { Card, CodeBlock, Heading } from '@astryxdesign/core';
import type { PageSpec } from './spec';
import { PixelIcon, resolveIcon } from '../px';
import { DEMO_COMPONENTS } from '../demos';

/* Static (non-animated) terminal for drill-down pages. */
function StaticTerminal({ lines, label }: { lines: PageSpec['demoLines']; label: string }) {
  return (
    <div className="terminal static-term" role="img" aria-label={label}>
      <div className="terminal-bar">
        <span className="dot r" />
        <span className="dot y" />
        <span className="dot g" />
        <span className="terminal-title">veto — zsh</span>
      </div>
      <div className="terminal-body">
        {lines.map((l, i) => (
          <div key={i} className={`tline t-${l.kind}`}>
            {l.kind === 'cmd' ? <span className="prompt">$ </span> : null}
            {l.text}
          </div>
        ))}
        <div className="tline t-cmd">
          <span className="prompt">$ </span>
          <span className="caret" />
        </div>
      </div>
    </div>
  );
}

function PxTag({ variant = '', children }: { variant?: '' | 'red' | 'amber'; children: React.ReactNode }) {
  return <span className={`px-tag ${variant}`}>{children}</span>;
}

export default function FeaturePage({ spec }: { spec: PageSpec }) {
  const InteractiveDemo =
    spec.interactive != null ? DEMO_COMPONENTS[spec.interactive] : undefined;
  return (
    <div className="page">
      <main>
        {/* PAGE HERO */}
        <section className="hero page-hero">
          <div className="wrap">
            <a className="back-link" href="#/">
              {'<'} All features
            </a>
            <div className="page-hero-inner">
              <div>
                <PxTag variant={spec.tagVariant ?? ''}>{spec.tag}</PxTag>
                <Heading level={1} className="hero-title page-title">
                  {spec.title}
                </Heading>
                <p className="hero-sub">{spec.lede}</p>
                <div className="hero-ctas">
                  <a className="px-btn primary" href="#/install" aria-label="Start with one job">
                    {'>'} Start with one job
                  </a>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* HOW IT WORKS */}
        <section className="section">
          <div className="wrap">
            <PxTag variant="amber">How it works</PxTag>
            <Heading level={2} className="section-title">
              Under the hood
            </Heading>
            <div className="grid">
              {spec.points.map((p) => (
                <Card key={p.title} className="feature-card">
                  <div className={`feature-icon ${p.tone ?? ''}`} aria-hidden="true">
                    <PixelIcon name={resolveIcon(p.icon)} />
                  </div>
                  <Heading level={3} className="feature-title">
                    {p.title}
                  </Heading>
                  <p className="feature-body">{p.body}</p>
                </Card>
              ))}
            </div>
          </div>
        </section>

        <div className="px-hr" aria-hidden="true" />

        {/* LIVE-ish DEMO */}
        <section className="section">
          <div className="wrap">
            <PxTag>Demo</PxTag>
            <Heading level={2} className="section-title">
              {spec.demoTitle}
            </Heading>
            {InteractiveDemo != null ? <InteractiveDemo /> : null}
            <div className="page-demo">
              <StaticTerminal lines={spec.demoLines} label={`Demo terminal: ${spec.demoTitle}`} />
            </div>
          </div>
        </section>

        <div className="px-hr" aria-hidden="true" />

        {/* HONEST LIMITATIONS */}
        <section className="section">
          <div className="wrap narrow">
            <PxTag variant="red">Boss fights</PxTag>
            <Heading level={2} className="section-title">
              Where it struggles
            </Heading>
            <p className="section-sub">
              No hype. Every tool has edges. Here are this one&rsquo;s, stated
              up front.
            </p>
            <div className="limits">
              {spec.limits.map((l, i) => (
                <div key={i} className="limit-item">
                  <span className="limit-n" aria-hidden="true">
                    X
                  </span>
                  <p>{l}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {spec.faq && spec.faq.length > 0 && (
          <>
            <div className="px-hr" aria-hidden="true" />
            <section className="section">
              <div className="wrap narrow">
                <PxTag variant="amber">FAQ</PxTag>
                <Heading level={2} className="section-title">
                  Questions
                </Heading>
                <div className="faq">
                  {spec.faq.map((f) => (
                    <details key={f.q} className="faq-item">
                      <summary className="faq-q">{f.q}</summary>
                      <p className="faq-a">{f.a}</p>
                    </details>
                  ))}
                </div>
              </div>
            </section>
          </>
        )}

        {/* CTA */}
        <section className="section cta">
          <div className="wrap narrow cta-inner">
            <p className="game-over">- continue? -</p>
            <Heading level={2} className="section-title">
              Try it on your search.
            </Heading>
            <div className="hero-ctas center">
              <a className="px-btn primary" href="#/install" aria-label="Start with one job">
                {'>'} Start with one job
              </a>
              <a className="px-btn secondary" href="#/" aria-label="Back to all features">
                All features
              </a>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

export function CodeDemo({ code, language }: { code: string; language: string }) {
  return (
    <div className="px-code">
      <CodeBlock code={code} language={language} hasCopyButton />
    </div>
  );
}

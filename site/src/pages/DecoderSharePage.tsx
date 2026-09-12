import { useMemo } from 'react';
import { Heading } from '@astryxdesign/core';
import { PxTag } from '../px';
import {
  decodeSharePayload,
  payloadFromHash,
  type SharePayload,
} from '../lib/jdShare';

/* ------------------------------------------------------------------ */
/* Shared JD decode: read-only result card at #/decoder/r/<payload>.   */
/* The link carries scores, verdict, and flags only. The posting text  */
/* never travels in the URL unless the sharer opted into an excerpt.   */
/* A bad hash or malformed payload renders an error, never a crash.    */
/* ------------------------------------------------------------------ */

const VERDICT_COPY: Record<SharePayload['ver'], string> = {
  strong: 'This one reads clean. Still verify everything yourself.',
  mixed: 'Some good, some bad. Read the flags before you apply.',
  caution: 'The language is waving red flags. Proceed with questions.',
};

function Quote({ text }: { text: string }) {
  return <p className="jdtry-quote">&ldquo;{text}&rdquo;</p>;
}

function ShareResults({ p }: { p: SharePayload }) {
  const tone = p.ver === 'strong' ? 'go' : p.ver === 'mixed' ? 'amber' : 'red';
  return (
    <div className="jdtry-results">
      <div className={`jdtry-verdict ${tone}`} role="status">
        <span className="jdtry-verdict-label px-font">{p.ver}</span>
        <span className="jdtry-verdict-score px-font">{p.sc}/100</span>
        <p className="jdtry-verdict-sub">{VERDICT_COPY[p.ver]}</p>
      </div>

      {p.x != null ? (
        <div className="jdtry-panel jdshare-excerpt-panel">
          <h3 className="jdtry-panel-title px-font">Sharer excerpt</h3>
          <Quote text={p.x} />
          <p className="jdtry-line">
            The sharer chose to include this snippet. It is the only posting
            text in this link.
          </p>
        </div>
      ) : null}

      <div className="jdtry-panel">
        <h3 className="jdtry-panel-title px-font">Why this verdict</h3>
        {p.rs.map((r, i) => (
          <div key={i} className="jdtry-reason">
            <span
              className={`jdtry-chip ${r.i > 0 ? 'go' : r.i < 0 ? 'red' : ''}`}
              aria-label={`impact ${r.i > 0 ? '+' : ''}${r.i}`}
            >
              {r.i > 0 ? '+' : ''}
              {r.i}
            </span>
            <div>
              <p className="jdtry-reason-text">{r.r}</p>
              {r.q != null ? <Quote text={r.q} /> : null}
            </div>
          </div>
        ))}
      </div>

      <div className="jdtry-panel">
        <h3 className="jdtry-panel-title px-font">Transparency {p.ts}/100</h3>
        {p.sal != null ? (
          <p className="jdtry-line">
            {p.salm ? 'Salary mentioned, no range: ' : 'Salary range: '}
            <strong>{p.sal}</strong>
          </p>
        ) : (
          <p className="jdtry-line">No compensation information listed.</p>
        )}
        {p.eq != null ? (
          <p className="jdtry-line">
            Equity ({p.eqc ? 'concrete' : 'vague'}): <strong>{p.eq}</strong>
          </p>
        ) : null}
      </div>

      <div className="jdtry-panel">
        <h3 className="jdtry-panel-title px-font">
          Overwork language ({p.ow.length})
        </h3>
        {p.ow.length === 0 ? (
          <p className="jdtry-line">None found. Suspiciously wholesome.</p>
        ) : (
          p.ow.map((o) => (
            <div key={o.p} className="jdtry-flag">
              <p className="jdtry-flag-phrase">&ldquo;{o.p}&rdquo;</p>
              <Quote text={o.q} />
              <p className="jdtry-line">{o.r}</p>
            </div>
          ))
        )}
      </div>

      <p className="jdtry-note">
        I decoded this from the posting language. The link carries scores and
        flag quotes, nothing else. The posting text never leaves the sharer's
        browser unless they included an excerpt.{' '}
        <a className="demo-docs" href="#/features/jd-decoder">
          How the scoring works&nbsp;{'>'}
        </a>
      </p>

      <div className="jdshare-cta">
        <a className="px-btn primary" href="#/decoder/try">
          {'>'} Decode your own posting
        </a>
      </div>
    </div>
  );
}

function BadLink() {
  return (
    <div className="jdshare-error" role="alert">
      <h2 className="jdshare-error-title px-font">Link looks broken</h2>
      <p className="jdshare-error-text">
        This link looks broken or tampered with, so I will not render it. Ask
        whoever shared it for a fresh link, or decode a posting yourself.
      </p>
      <a className="px-btn primary" href="#/decoder/try">
        {'>'} Decode a posting
      </a>
    </div>
  );
}

export default function DecoderSharePage() {
  const decoded = useMemo(() => {
    const seg = payloadFromHash(window.location.hash);
    if (seg == null) return { ok: false, error: 'malformed' } as const;
    return decodeSharePayload(seg);
  }, []);

  return (
    <div className="page">
      <main>
        <section className="hero page-hero">
          <div className="wrap">
            <a className="back-link" href="#/decoder/try">
              {'<'} Decoder
            </a>
            <PxTag variant="amber">Shared decode</PxTag>
            <Heading level={1} className="hero-title page-title">
              Someone shared a decode.
            </Heading>
            <p className="hero-sub">
              This is a read-only result. I did not re-run anything: the scores
              and flags arrived in the link, and I verified the link's
              integrity hash before rendering.
            </p>
          </div>
        </section>

        <section className="section">
          <div className="wrap narrow">
            {decoded.ok ? <ShareResults p={decoded.payload} /> : <BadLink />}
          </div>
        </section>
      </main>
    </div>
  );
}

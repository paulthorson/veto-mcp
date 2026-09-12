import { useState } from 'react';
import { Heading } from '@astryxdesign/core';
import { PxTag } from '../px';
import { jdVerdict, type JdVerdict } from '../lib/jdDecoder';
import { JD_SAMPLE } from '../demos/win';

/* ------------------------------------------------------------------ */
/* Interactive JD decoder: paste any posting, get the real verdict.    */
/* The engine is a faithful TS port of jd_decoder.py (regex + counting, */
/* no model), so these numbers match `cli.py decode-jd` exactly.       */
/* ------------------------------------------------------------------ */

const VERDICT_COPY: Record<JdVerdict['verdict'], string> = {
  strong: 'This one reads clean. Still verify everything yourself.',
  mixed: 'Some good, some bad. Read the flags before you apply.',
  caution: 'The language is waving red flags. Proceed with questions.',
};

function ImpactChip({ impact }: { impact: number }) {
  const sign = impact > 0 ? '+' : impact < 0 ? '-' : '';
  const tone = impact > 0 ? 'go' : impact < 0 ? 'red' : '';
  return (
    <span className={`jdtry-chip ${tone}`} aria-label={`impact ${sign}${Math.abs(impact)}`}>
      {sign}
      {Math.abs(impact)}
    </span>
  );
}

function Quote({ text }: { text: string }) {
  return <p className="jdtry-quote">&ldquo;{text}&rdquo;</p>;
}

function Results({ result }: { result: JdVerdict }) {
  const s = result.signals;
  // Unreachable: the page only calls jdVerdict on non-blank text, so the
  // empty-input verdict (which carries no signals, mirroring Python) is
  // never rendered. The check keeps the honest optional type sound.
  if (s == null) return null;
  const tone = result.verdict === 'strong' ? 'go' : result.verdict === 'mixed' ? 'amber' : 'red';
  return (
    <div className="jdtry-results">
      <div className={`jdtry-verdict ${tone}`} role="status">
        <span className="jdtry-verdict-label px-font">{result.verdict}</span>
        <span className="jdtry-verdict-score px-font">{result.score}/100</span>
        <p className="jdtry-verdict-sub">{VERDICT_COPY[result.verdict]}</p>
      </div>

      <div className="jdtry-panel">
        <h3 className="jdtry-panel-title px-font">Why this verdict</h3>
        {result.reasons.map((r, i) => (
          <div key={i} className="jdtry-reason">
            <ImpactChip impact={r.impact} />
            <div>
              <p className="jdtry-reason-text">{r.reason}</p>
              {r.quote != null ? <Quote text={r.quote} /> : null}
            </div>
          </div>
        ))}
      </div>

      <div className="jdtry-panel">
        <h3 className="jdtry-panel-title px-font">
          Transparency {s.transparency.score}/100
        </h3>
        {s.transparency.salary_range != null ? (
          <p className="jdtry-line">
            Salary range: <strong>{s.transparency.salary_range.raw}</strong>
          </p>
        ) : s.transparency.salary_mention != null ? (
          <p className="jdtry-line">
            Salary mentioned, no range: <strong>{s.transparency.salary_mention.raw}</strong>
          </p>
        ) : (
          <p className="jdtry-line">No compensation information listed.</p>
        )}
        {s.transparency.equity != null ? (
          <p className="jdtry-line">
            Equity ({s.transparency.equity.concrete ? 'concrete' : 'vague'}):{' '}
            <strong>{s.transparency.equity.term}</strong>
          </p>
        ) : null}
      </div>

      <div className="jdtry-panel">
        <h3 className="jdtry-panel-title px-font">
          Overwork language ({s.overwork.length})
        </h3>
        {s.overwork.length === 0 ? (
          <p className="jdtry-line">None found. Suspiciously wholesome.</p>
        ) : (
          s.overwork.map((o) => (
            <div key={o.phrase} className="jdtry-flag">
              <p className="jdtry-flag-phrase">&ldquo;{o.phrase}&rdquo;</p>
              <Quote text={o.quote} />
              <p className="jdtry-line">{o.read}</p>
            </div>
          ))
        )}
      </div>

      <div className="jdtry-panel">
        <h3 className="jdtry-panel-title px-font">
          Vagueness {s.vagueness.score}/100 concrete
        </h3>
        <p className="jdtry-line">
          {s.vagueness.buzzword_count} buzzword
          {s.vagueness.buzzword_count === 1 ? '' : 's'} (
          {s.vagueness.buzzword_density_per_100_words}/100 words),{' '}
          {s.vagueness.responsibilities} concrete responsibilities,{' '}
          {s.vagueness.word_count} words total.
        </p>
        {s.vagueness.buzzwords.map((b, i) => (
          <div key={i} className="jdtry-flag">
            <p className="jdtry-flag-phrase">&ldquo;{b.buzzword}&rdquo;</p>
            <Quote text={b.quote} />
          </div>
        ))}
      </div>

      <div className="jdtry-panel">
        <h3 className="jdtry-panel-title px-font">
          Growth signals ({s.growth.length})
        </h3>
        {s.growth.length === 0 ? (
          <p className="jdtry-line">None. Nobody is promising you a future here.</p>
        ) : (
          s.growth.map((g) => (
            <div key={g.signal} className="jdtry-flag">
              <p className="jdtry-flag-phrase">{g.signal}</p>
              <Quote text={g.quote} />
            </div>
          ))
        )}
      </div>

      <div className="jdtry-panel">
        <h3 className="jdtry-panel-title px-font">
          Green flags ({s.green_flags.length})
        </h3>
        {s.green_flags.length === 0 ? (
          <p className="jdtry-line">None. Noted.</p>
        ) : (
          s.green_flags.map((g) => (
            <div key={g.flag} className="jdtry-flag">
              <p className="jdtry-flag-phrase">{g.flag}</p>
              <Quote text={g.quote} />
            </div>
          ))
        )}
      </div>

      <p className="jdtry-note">
        This reads language, not lies. A transparent-sounding scam still
        scores well. That is a documented limit, not a bug.{' '}
        <a className="demo-docs" href="#/features/jd-decoder">
          How the scoring works {'>'}
        </a>
      </p>
    </div>
  );
}

export default function DecoderPage() {
  const [text, setText] = useState('');
  const [result, setResult] = useState<JdVerdict | null>(null);
  const [empty, setEmpty] = useState(false);

  const decode = () => {
    if (!text.trim()) {
      setEmpty(true);
      setResult(null);
      return;
    }
    setEmpty(false);
    setResult(jdVerdict(text));
  };

  return (
    <div className="page">
      <main>
        <section className="hero page-hero">
          <div className="wrap">
            <a className="back-link" href="#/features/jd-decoder">
              {'<'} JD decoder
            </a>
            <PxTag variant="amber">Interactive tool</PxTag>
            <Heading level={1} className="hero-title page-title">
              Paste a posting. I decode it.
            </Heading>
            <p className="hero-sub">
              This is the real decoder, running in your browser. Same regex,
              same arithmetic as jd_decoder.py. No model, no vibes. Paste a
              posting and I will tell you what the language is actually saying.
            </p>
          </div>
        </section>

        <section className="section">
          <div className="wrap narrow">
            <label className="jdtry-label px-font" htmlFor="jdtry-input">
              The posting
            </label>
            <textarea
              id="jdtry-input"
              className="jdtry-textarea"
              value={text}
              onChange={(e) => {
                setText(e.target.value);
                setEmpty(false);
              }}
              placeholder="Paste the full job posting here. The whole thing, not just the exciting paragraph."
              rows={10}
            />
            {empty ? (
              <p className="jdtry-error" role="alert">
                Nothing to decode. Paste a posting first, then hit Decode.
              </p>
            ) : null}
            <div className="jdtry-actions">
              <button type="button" className="px-btn primary" onClick={decode}>
                {'>'} Decode it
              </button>
              <button
                type="button"
                className="px-btn secondary"
                onClick={() => {
                  setText(JD_SAMPLE);
                  setEmpty(false);
                  setResult(null);
                }}
              >
                Load the sample posting
              </button>
              <button
                type="button"
                className="px-btn ghost"
                onClick={() => {
                  setText('');
                  setResult(null);
                  setEmpty(false);
                }}
              >
                Clear
              </button>
            </div>

            {result != null ? <Results result={result} /> : null}
          </div>
        </section>
      </main>
    </div>
  );
}

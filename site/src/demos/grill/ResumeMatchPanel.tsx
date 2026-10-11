/* Chakra feature G: resume-match panel. Presentational only — no logic,
 * no state. The integrator mounts this at the verdict stage with the
 * ResumeMatch computed by scoreResumeMatch() (see INTEGRATION-G.md in
 * this directory for the wiring).
 *
 * Visual language matches the other grill panels (e.g. AiFluencyPanel):
 * a red -> amber -> green gradient where low values sit on red and high
 * values sit on green. Styles are inline so no existing CSS file is touched.
 */
import type { ResumeMatch } from '../../lib/chakraTypes';

/* Same tri-color dataviz gradient as the radar: red core (low), amber mid,
   green rim (high). */
const GRADIENT = 'linear-gradient(90deg, #ff4d5e 0%, #ffb020 50%, #3dff73 100%)';

const FONT = 'VT323, monospace';

function toneFor(value: number): '#3dff73' | '#ffb020' | '#ff4d5e' {
  if (value >= 75) return '#3dff73';
  if (value >= 45) return '#ffb020';
  return '#ff4d5e';
}

function Chip({ label, kind }: { label: string; kind: 'matched' | 'missing' }) {
  const color = kind === 'matched' ? '#3dff73' : '#ff4d5e';
  return (
    <span
      style={{
        display: 'inline-block',
        fontFamily: FONT,
        fontSize: 17,
        color,
        border: `1px solid ${color}`,
        padding: '2px 8px',
        margin: '0 6px 6px 0',
      }}
    >
      {label}
    </span>
  );
}

export default function ResumeMatchPanel({ match }: { match: ResumeMatch }) {
  const { score, matchedKeywords, missingKeywords, gaps } = match;
  const pct = Math.max(0, Math.min(100, score));
  return (
    <div
      data-testid="resume-match-panel"
      role="region"
      aria-label={`Resume match: ${score} out of 100`}
      style={{
        fontFamily: FONT,
        background: '#14141c',
        border: '2px solid #2c2c3d',
        padding: '16px 18px',
        marginTop: 16,
      }}
    >
      <p style={{ fontSize: 20, color: '#e8e6f0', margin: '0 0 4px' }}>
        {'>'} Resume match{' '}
        <span
          data-testid="resume-match-score"
          style={{ color: toneFor(score) }}
        >
          {score}/100
        </span>
      </p>
      {/* Score bar: dim full-spectrum track, full-strength fill clipped to
          the value — the visible color always lands on the right zone of
          the red/amber/green gradient. The fill lives OUTSIDE the opacity
          container (track opacity layer and fill are siblings) so the fill
          renders at full strength. */}
      <div aria-hidden="true" style={{ height: 14, position: 'relative', marginTop: 8 }}>
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: GRADIENT,
            opacity: 0.22,
          }}
        />
        {pct > 0 && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              width: `${pct}%`,
              overflow: 'hidden',
            }}
          >
            <div style={{ height: 14, background: GRADIENT, width: `${10000 / pct}%` }} />
          </div>
        )}
      </div>
      {matchedKeywords.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <p style={{ fontSize: 18, color: '#a9a7ba', margin: '0 0 6px' }}>
            Matched ({matchedKeywords.length}):
          </p>
          <div>
            {matchedKeywords.map((k) => (
              <Chip key={k} label={k} kind="matched" />
            ))}
          </div>
        </div>
      )}
      {missingKeywords.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <p style={{ fontSize: 18, color: '#a9a7ba', margin: '0 0 6px' }}>
            Missing ({missingKeywords.length}) — the grill will drill these:
          </p>
          <div>
            {missingKeywords.map((k) => (
              <Chip key={k} label={k} kind="missing" />
            ))}
          </div>
        </div>
      )}
      {gaps.length > 0 && (
        <ul
          data-testid="resume-gaps"
          style={{
            fontSize: 18,
            color: '#e8e6f0',
            margin: '12px 0 0',
            paddingLeft: 20,
            lineHeight: 1.35,
          }}
        >
          {gaps.map((gap) => (
            <li key={gap}>{gap}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

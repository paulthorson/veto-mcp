/* Feature B: AI fluency panel. Presentational only — no logic, no state.
 * The integrator mounts this beside the fit-score factors at the verdict
 * stage (see INTEGRATION-B.md in this directory for the wiring).
 *
 * Visual language matches the fit-score radar (site/src/demos/radar.tsx):
 * a red -> amber -> green gradient where low values sit on red and high
 * values sit on green. Styles are inline so no existing CSS file is touched.
 */
import type { AiFluencyScore } from '../../lib/chakraTypes';

/* Same tri-color dataviz gradient as the radar: red core (low), amber mid,
   green rim (high). */
const GRADIENT = 'linear-gradient(90deg, #ff4d5e 0%, #ffb020 50%, #3dff73 100%)';

const FONT = 'VT323, monospace';

function toneFor(value: number): '#3dff73' | '#ffb020' | '#ff4d5e' {
  if (value >= 75) return '#3dff73';
  if (value >= 50) return '#ffb020';
  return '#ff4d5e';
}

function DimBar({ label, value }: { label: string; value: number }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div
      style={{ marginBottom: 8 }}
      data-testid={`ai-fluency-${label.toLowerCase()}`}
      role="img"
      aria-label={`${label}: ${value} out of 100`}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          fontFamily: FONT,
          fontSize: 18,
          color: '#a9a7ba',
        }}
      >
        <span>{label}</span>
        <span style={{ color: toneFor(value) }}>{value}/100</span>
      </div>
      {/* Dim full-spectrum track, full-strength fill clipped to the value —
          so the visible color always lands on the right zone of the
          red/amber/green gradient (red left, green right). The fill lives
          OUTSIDE the opacity container: opacity on a parent dims every
          child, so the track's opacity layer and the fill are siblings —
          the fill renders at full strength. */}
      <div aria-hidden="true" style={{ height: 14, position: 'relative', marginTop: 2 }}>
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
            {/* Child is scaled back up to the full track width so the
                gradient colors line up with value position: a low value
                shows only the red zone, a high value reaches the green. */}
            <div style={{ height: 14, background: GRADIENT, width: `${10000 / pct}%` }} />
          </div>
        )}
      </div>
    </div>
  );
}

export default function AiFluencyPanel({ fluency }: { fluency: AiFluencyScore }) {
  const { score, dimensions, note } = fluency;
  return (
    <div
      data-testid="ai-fluency-panel"
      role="region"
      aria-label={`AI fluency score ${score} out of 100`}
      style={{
        fontFamily: FONT,
        background: '#14141c',
        border: '2px solid #2c2c3d',
        padding: '16px 18px',
        marginTop: 16,
      }}
    >
      <p
        style={{
          fontSize: 20,
          color: '#e8e6f0',
          margin: '0 0 4px',
        }}
      >
        {'>'} AI fluency <span style={{ color: toneFor(score) }}>{score}/100</span>
      </p>
      <div style={{ marginTop: 12 }}>
        <DimBar label="Framing" value={dimensions.framing} />
        <DimBar label="Judgment" value={dimensions.judgment} />
        <DimBar label="Steering" value={dimensions.steering} />
      </div>
      <p
        style={{
          fontSize: 18,
          color: '#a9a7ba',
          margin: '10px 0 0',
          lineHeight: 1.3,
        }}
      >
        {note}
      </p>
    </div>
  );
}

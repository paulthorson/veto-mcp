/* Feature H: delivery coaching panel. Presentational only — no logic, no state.
 * The integrator mounts this at the verdict stage (see INTEGRATION-H.md
 * in this directory for the wiring).
 *
 * Visual language matches the fit-score radar (site/src/demos/radar.tsx)
 * and the AI-fluency panel, but INVERTED: hedging is bad-high, so the
 * meter gradient runs green -> amber -> red (green left, red right).
 * High hedging sits on red, low hedging on green — the number color,
 * the caption, and the meter's leading edge all agree. Styles are
 * inline so no existing CSS file is touched.
 */
import type { DeliveryFeedback } from '../../lib/chakraTypes';

/* Inverted tri-color dataviz gradient for the hedging meter: green left,
   red right. The clip trick shows the LEFT pct% of this gradient, so a
   low value shows only the green zone and a high value reaches the red. */
const HEDGE_GRADIENT = 'linear-gradient(90deg, #3dff73 0%, #ffb020 50%, #ff4d5e 100%)';

const FONT = 'VT323, monospace';

/* High hedging reads red; low hedging reads green. */
function toneFor(hedging: number): '#3dff73' | '#ffb020' | '#ff4d5e' {
  if (hedging >= 60) return '#ff4d5e';
  if (hedging >= 30) return '#ffb020';
  return '#3dff73';
}

function HedgingMeter({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div
      data-testid="delivery-hedging"
      role="img"
      aria-label={`Hedging: ${value} out of 100`}
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
        <span>Hedging</span>
        <span style={{ color: toneFor(value) }}>{value}/100</span>
      </div>
      {/* Dim full-spectrum track, full-strength fill clipped to the value —
          so the visible color always lands on the right zone of the
          inverted green/amber/red gradient (green left, red right). The
          fill lives OUTSIDE the opacity container (track opacity layer and
          fill are siblings) so the fill renders at full strength. */}
      <div aria-hidden="true" style={{ height: 14, position: 'relative', marginTop: 2 }}>
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: HEDGE_GRADIENT,
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
                shows only the green zone, a high value reaches the red. */}
            <div style={{ height: 14, background: HEDGE_GRADIENT, width: `${10000 / pct}%` }} />
          </div>
        )}
      </div>
      <p
        style={{
          fontFamily: FONT,
          fontSize: 16,
          color: '#a9a7ba',
          margin: '4px 0 0',
          lineHeight: 1.3,
        }}
      >
        {value >= 60
          ? 'Lots of hedging — the grill reads it as low confidence.'
          : value >= 30
            ? 'Some hedging — firm up the softest claims.'
            : 'Steady — your claims sound confident.'}
      </p>
    </div>
  );
}

export default function DeliveryPanel({ feedback }: { feedback: DeliveryFeedback }) {
  const { fillerWords, fillerTotal, hedgingScore, pacingNote, suggestions } = feedback;
  return (
    <div
      data-testid="delivery-panel"
      role="region"
      aria-label={`Delivery coaching: ${fillerTotal} filler words, hedging ${hedgingScore} out of 100`}
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
        {'>'} Delivery coaching <span style={{ color: '#a9a7ba' }}>— how you answer</span>
      </p>

      <div data-testid="delivery-fillers" style={{ marginTop: 12 }}>
        <p style={{ fontSize: 18, color: '#a9a7ba', margin: '0 0 4px' }}>
          Filler words — {fillerTotal} total
        </p>
        {fillerTotal === 0 ? (
          <p style={{ fontSize: 18, color: '#3dff73', margin: '0 0 8px' }}>
            None spotted — clean delivery.
          </p>
        ) : (
          <ul style={{ fontSize: 18, color: '#e8e6f0', margin: '0 0 8px', paddingLeft: 20 }}>
            {fillerWords.map((f) => (
              <li key={f.word}>
                '{f.word}' — {f.count} {f.count === 1 ? 'time' : 'times'}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div style={{ marginTop: 8 }}>
        <HedgingMeter value={hedgingScore} />
      </div>

      <p
        data-testid="delivery-pacing"
        style={{ fontSize: 18, color: '#a9a7ba', margin: '10px 0 0', lineHeight: 1.3 }}
      >
        Pacing — {pacingNote}
      </p>

      <div data-testid="delivery-suggestions" style={{ marginTop: 8 }}>
        <p style={{ fontSize: 18, color: '#e8e6f0', margin: '0 0 4px' }}>
          Coach's notes
        </p>
        <ol style={{ fontSize: 18, color: '#e8e6f0', margin: '0 0 4px', paddingLeft: 20 }}>
          {suggestions.map((s, i) => (
            <li key={i} style={{ marginBottom: 4 }}>
              {s}
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

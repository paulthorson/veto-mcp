/* Fit-score radar: five sliders recompute the match score live.
   Mirrors match.py: skills 50 / seniority 15 / salary 15 / location 15 / recency 5. */
import { useState } from 'react';
import { DemoShell, PxSlider } from './shared';

const AXES = ['skills', 'seniority', 'salary', 'location', 'recency'] as const;
type Axis = (typeof AXES)[number];

/* Weight in points-out-of-100 (matches match.py, shown as the x50 badges). */
const WEIGHT_PTS: Record<Axis, number> = {
  skills: 50,
  seniority: 15,
  salary: 15,
  location: 15,
  recency: 5,
};

const VETO_LINE = 40;

function pt(i: number, v: number, cx: number, cy: number, r: number): [number, number] {
  const a = (-90 + i * 72) * (Math.PI / 180);
  const d = (v / 100) * r;
  return [cx + d * Math.cos(a), cy + d * Math.sin(a)];
}
const fmt = ([x, y]: [number, number]) => `${x.toFixed(1)},${y.toFixed(1)}`;

export default function RadarDemo() {
  const [vals, setVals] = useState<Record<Axis, number>>({
    skills: 85,
    seniority: 80,
    salary: 75,
    location: 90,
    recency: 100,
  });

  const contrib = (a: Axis) => (vals[a] * WEIGHT_PTS[a]) / 100;
  const score = Math.round(AXES.reduce((s, a) => s + contrib(a), 0));
  const vetoed = score < VETO_LINE;
  const worst = AXES.reduce((w, a) => (vals[a] < vals[w] ? a : w), AXES[0]);
  const tone: 'go' | 'amber' | 'red' = vetoed ? 'red' : vals[worst] < 50 ? 'amber' : 'go';
  const accent = vetoed ? 'var(--veto)' : 'var(--go)';

  const cx = 170;
  const cy = 130;
  const r = 88;
  const rings = [25, 50, 75, 100];

  return (
    <DemoShell
      title="> live fit-score demo"
      label="Interactive radar chart: five sliders recompute the job fit score live"
    >
      <div className="radar-grid">
        <div className="radar-chart">
          <svg viewBox="0 0 340 260" className="radar-svg" aria-hidden="true">
            {/* concentric guide rings */}
            {rings.map((ring, ri) => (
              <polygon
                key={ring}
                points={AXES.map((_, i) => fmt(pt(i, ring, cx, cy, r))).join(' ')}
                fill={ri % 2 === 0 ? 'rgba(255,255,255,0.014)' : 'none'}
                stroke="#2c2c3d"
                strokeWidth="1"
              />
            ))}

            {/* spokes */}
            {AXES.map((_, i) => {
              const [x2, y2] = pt(i, 100, cx, cy, r);
              return <line key={i} x1={cx} y1={cy} x2={x2} y2={y2} stroke="#2c2c3d" strokeWidth="1" />;
            })}

            {/* live polygon (flat translucent fill, crisp stroke) */}
            <polygon
              className="radar-poly"
              points={AXES.map((a, i) => fmt(pt(i, vals[a], cx, cy, r))).join(' ')}
              fill={vetoed ? 'rgba(255,77,94,0.20)' : 'rgba(61,255,115,0.18)'}
              stroke={vetoed ? '#ff4d5e' : '#3dff73'}
              strokeWidth="3"
              strokeLinejoin="round"
            />

            {/* vertex markers; the weakest axis gets a warning ring */}
            {AXES.map((a, i) => {
              const [vx, vy] = pt(i, vals[a], cx, cy, r);
              const isWorst = a === worst;
              return (
                <g key={a}>
                  {isWorst && (
                    <circle
                      cx={vx}
                      cy={vy}
                      r="8"
                      fill="none"
                      stroke={vetoed ? '#ff4d5e' : '#ffb000'}
                      strokeWidth="2"
                    />
                  )}
                  <circle
                    cx={vx}
                    cy={vy}
                    r="4"
                    fill={vetoed ? '#ff4d5e' : '#3dff73'}
                    stroke="#08080c"
                    strokeWidth="2"
                  />
                </g>
              );
            })}

            {/* axis labels */}
            {AXES.map((a, i) => {
              const [lx, ly] = pt(i, 130, cx, cy, r);
              return (
                <text
                  key={a}
                  x={lx}
                  y={ly}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill={a === worst ? (vetoed ? '#ff4d5e' : '#ffb000') : '#a9a7ba'}
                  fontSize="18"
                  fontFamily="VT323, monospace"
                >
                  {a}
                </text>
              );
            })}
          </svg>
        </div>

        <div className="radar-side">
          <p className={`radar-score ${vetoed ? 'bad' : ''}`}>{score}</p>
          <p className="radar-score-label">fit score / 100</p>

          {/* threshold meter: shows how far the score sits above/below the veto line */}
          <div
            className="fit-meter"
            role="img"
            aria-label={`Fit score ${score} of 100, veto line at ${VETO_LINE}`}
          >
            <div className="fit-meter-track">
              <div
                className={`fit-meter-fill ${vetoed ? 'bad' : ''}`}
                style={{ width: `${score}%` }}
              />
              <div className="fit-meter-veto" style={{ width: `${VETO_LINE}%` }} />
            </div>
            <div className="fit-meter-scale">
              <span className="fit-meter-min">0</span>
              <span className="fit-meter-vetotag" style={{ left: `${VETO_LINE}%` }}>
                veto {VETO_LINE}
              </span>
              <span className="fit-meter-max">100</span>
            </div>
          </div>

          {vetoed ? (
            <p className="radar-verdict bad">X VETOED: {worst} {vals[worst]} {'<'} {VETO_LINE}</p>
          ) : (
            <p className="radar-verdict good">
              + PROCEED: {score - VETO_LINE} pts clear of the veto line
            </p>
          )}
        </div>
      </div>

      <div className="radar-sliders">
        {AXES.map((a) => (
          <PxSlider
            key={a}
            label={a}
            value={vals[a]}
            weight={WEIGHT_PTS[a]}
            tone={a === worst ? tone : 'go'}
            hint={`+${contrib(a).toFixed(1)} of ${WEIGHT_PTS[a]} pts`}
            onChange={(v) => setVals((s) => ({ ...s, [a]: v }))}
          />
        ))}
      </div>

      <p className="idemo-foot" style={{ borderTop: `2px solid var(--line)`, paddingTop: 16 }}>
        Drag the sliders and watch the score move. The weakest axis is ringed in{' '}
        <b style={{ color: accent }}>{vetoed ? 'red' : 'amber'}</b>; drop the score under{' '}
        {VETO_LINE} and the veto trips.
      </p>
    </DemoShell>
  );
}

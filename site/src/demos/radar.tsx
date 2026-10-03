/* Fit-score radar: five sliders recompute the match score live.
   Mirrors match.py: skills 50 / seniority 15 / salary 15 / location 15 / recency 5.
   Anything under the 60 veto bar is rejected. */
import { useId, useState } from 'react';
import { DemoShell, PxSlider } from './shared';

const AXES = ['skills', 'seniority', 'salary', 'location', 'recency'] as const;
const WEIGHTS: Record<(typeof AXES)[number], number> = {
  skills: 0.5,
  seniority: 0.15,
  salary: 0.15,
  location: 0.15,
  recency: 0.05,
};

const VETO_BAR = 60;

function pt(i: number, v: number, cx: number, cy: number, r: number): string {
  const a = (-90 + i * 72) * (Math.PI / 180);
  const d = (v / 100) * r;
  return `${(cx + d * Math.cos(a)).toFixed(1)},${(cy + d * Math.sin(a)).toFixed(1)}`;
}

/* Point at an arbitrary angle (degrees) and value, for the threshold label. */
function ptAt(angleDeg: number, v: number, cx: number, cy: number, r: number): string {
  const a = (angleDeg * Math.PI) / 180;
  const d = (v / 100) * r;
  return `${(cx + d * Math.cos(a)).toFixed(1)},${(cy + d * Math.sin(a)).toFixed(1)}`;
}

export default function RadarDemo() {
  const [vals, setVals] = useState<Record<string, number>>({
    skills: 85,
    seniority: 80,
    salary: 75,
    location: 90,
    recency: 100,
  });
  const score = Math.round(
    AXES.reduce((s, a) => s + vals[a] * WEIGHTS[a], 0),
  );
  const vetoed = score < VETO_BAR;
  const margin = vetoed ? VETO_BAR - score : score - VETO_BAR;

  const cx = 170;
  const cy = 130;
  const r = 88;
  const rings = [25, 50, 75, 100];
  const gradientId = useId();
  /* Label sits in the bottom gap (between the salary and location spokes,
     just outside the dashed ring), where no axis label sits. */
  const [barLabelX, barLabelY] = ptAt(90, 68, cx, cy, r).split(',').map(Number);

  return (
    <DemoShell title="> live fit-score demo" label="Interactive radar chart: five sliders recompute the job fit score live">
      {/* Verdict hero: the product decision, the score, and where it sits vs the bar. */}
      <div className={`fit-hero ${vetoed ? 'bad' : ''}`}>
        <div className="fit-hero-top">
          <p className="fit-verdict">{vetoed ? 'X VETOED' : '+ PROCEED'}</p>
          <p className="fit-score">
            <b>{score}</b>
            <span>/ 100</span>
          </p>
        </div>
        <div className="fit-bar">
          <div className="fit-bar-track">
            <div className="fit-bar-fill" style={{ width: `${score}%` }} />
            <div
              className="fit-bar-marker"
              style={{ left: `${VETO_BAR}%` }}
              title={`Veto bar: ${VETO_BAR}`}
            />
          </div>
          <div className="fit-bar-scale" aria-hidden="true">
            <span>0</span>
            <span>bar {VETO_BAR}</span>
            <span>100</span>
          </div>
        </div>
        <p className="fit-margin">
          {vetoed
            ? `${margin} under the bar — Veto skips this one.`
            : `${margin} over the bar — worth one of your five daily shots.`}
        </p>
      </div>
      <div className="radar-grid">
        <svg viewBox="0 0 340 260" className="radar-svg" aria-hidden="true">
          <defs>
            {/* Dataviz gradient: red at the core (low values) through amber
                at the veto bar to green at the rim (high values). */}
            <radialGradient
              id={gradientId}
              gradientUnits="userSpaceOnUse"
              cx={cx}
              cy={cy}
              r={r * 1.08}
            >
              <stop offset="0%" stopColor="#ff4d5e" stopOpacity="0.6" />
              <stop offset="56%" stopColor="#ffb020" stopOpacity="0.6" />
              <stop offset="100%" stopColor="#3dff73" stopOpacity="0.6" />
            </radialGradient>
          </defs>
          {rings.map((ring) => (
            <polygon
              key={ring}
              points={AXES.map((_, i) => pt(i, ring, cx, cy, r)).join(' ')}
              fill="none"
              stroke="#2c2c3d"
              strokeWidth="1"
            />
          ))}
          {/* Veto bar: dashed amber ring at value 60. */}
          <polygon
            points={AXES.map((_, i) => pt(i, VETO_BAR, cx, cy, r)).join(' ')}
            fill="none"
            stroke="#ffd166"
            strokeWidth="2"
            strokeDasharray="6 4"
          />
          <text
            x={barLabelX}
            y={barLabelY}
            textAnchor="middle"
            dominantBaseline="middle"
            fill="#ffd166"
            fontSize="18"
            fontFamily="VT323, monospace"
          >
            bar {VETO_BAR}
          </text>
          {AXES.map((_, i) => (
            <line
              key={i}
              x1={cx}
              y1={cy}
              x2={pt(i, 100, cx, cy, r).split(',')[0]}
              y2={pt(i, 100, cx, cy, r).split(',')[1]}
              stroke="#2c2c3d"
              strokeWidth="1"
            />
          ))}
          <polygon
            points={AXES.map((a, i) => pt(i, vals[a], cx, cy, r)).join(' ')}
            fill={`url(#${gradientId})`}
            stroke={vetoed ? '#ff4d5e' : '#3dff73'}
            strokeWidth="3"
          />
          {AXES.map((a, i) => {
            const [lx, ly] = pt(i, 128, cx, cy, r).split(',').map(Number);
            return (
              <text
                key={a}
                x={lx}
                y={ly}
                textAnchor="middle"
                dominantBaseline="middle"
                fill="#a9a7ba"
                fontSize="18"
                fontFamily="VT323, monospace"
              >
                {a}
              </text>
            );
          })}
        </svg>
        <div className="fit-factors">
          <p className="fit-factors-title">&gt; what moves the score</p>
          {AXES.map((a) => {
            const contrib = vals[a] * WEIGHTS[a];
            return (
              <div className="fit-factor" key={a}>
                <div className="fit-factor-head">
                  <span>{a}</span>
                  <span>
                    {vals[a]} x {WEIGHTS[a].toFixed(2)} = <b>{contrib.toFixed(1)}</b>
                  </span>
                </div>
                <div className="fit-factor-track">
                  <div
                    className="fit-factor-fill"
                    style={{ width: `${(contrib / 50) * 100}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
      <p className="fit-sliders-title">&gt; tune the signals</p>
      <div className="fit-sliders">
        {AXES.map((a) => (
          <PxSlider
            key={a}
            label={a}
            value={vals[a]}
            onChange={(v) => setVals((s) => ({ ...s, [a]: v }))}
          />
        ))}
      </div>
      <p className="idemo-foot">
        Drag the sliders and watch the score move. Veto spends your five daily applications only on postings scoring 60+.
      </p>
    </DemoShell>
  );
}

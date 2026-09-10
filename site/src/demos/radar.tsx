/* Fit-score radar: five sliders recompute the match score live.
   Mirrors match.py: skills 50 / seniority 15 / salary 15 / location 15 / recency 5. */
import { useState } from 'react';
import { DemoShell, PxSlider } from './shared';

const AXES = ['skills', 'seniority', 'salary', 'location', 'recency'] as const;
const WEIGHTS: Record<(typeof AXES)[number], number> = {
  skills: 0.5,
  seniority: 0.15,
  salary: 0.15,
  location: 0.15,
  recency: 0.05,
};

function pt(i: number, v: number, cx: number, cy: number, r: number): string {
  const a = (-90 + i * 72) * (Math.PI / 180);
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
  const vetoed = score < 40;
  const worst = AXES.reduce((w, a) => (vals[a] < vals[w] ? a : w), AXES[0]);

  const cx = 170;
  const cy = 130;
  const r = 88;
  const rings = [25, 50, 75, 100];

  return (
    <DemoShell title="> live fit-score demo" label="Interactive radar chart: five sliders recompute the job fit score live">
      <div className="radar-grid">
        <svg viewBox="0 0 340 260" className="radar-svg" aria-hidden="true">
          {rings.map((ring) => (
            <polygon
              key={ring}
              points={AXES.map((_, i) => pt(i, ring, cx, cy, r)).join(' ')}
              fill="none"
              stroke="#2c2c3d"
              strokeWidth="1"
            />
          ))}
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
            fill={vetoed ? 'rgba(255,77,94,.25)' : 'rgba(61,255,115,.22)'}
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
        <div className="radar-side">
          <p className={`radar-score ${vetoed ? 'bad' : ''}`}>{score}</p>
          <p className="radar-score-label">fit score / 100</p>
          {vetoed ? (
            <p className="radar-verdict bad">X VETOED — {worst} {vals[worst]} {'<'} 40</p>
          ) : (
            <p className="radar-verdict good">+ PROCEED — no veto trips</p>
          )}
          <p className="radar-note">
            skills 50 · seniority 15 · salary 15 · location 15 · recency 5
          </p>
        </div>
      </div>
      <div className="radar-sliders">
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
        Drag skills to zero and watch the veto trip. Scores below 40 never apply.
      </p>
    </DemoShell>
  );
}

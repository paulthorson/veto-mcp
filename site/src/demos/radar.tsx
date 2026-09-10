/* Fit-score radar: an ambient, self-animating radar chart with no controls.
   It eases between a "non-match" profile (score below the veto line -> red) and a
   strong "match" profile (green) — reaching each state on a ~3-second beat.
   Weights mirror match.py: skills 50 / seniority 15 / salary 15 / location 15 / recency 5. */
import { useEffect, useState } from 'react';
import { DemoShell } from './shared';

const AXES = ['skills', 'seniority', 'salary', 'location', 'recency'] as const;
type Axis = (typeof AXES)[number];

const WEIGHT_PTS: Record<Axis, number> = {
  skills: 50,
  seniority: 15,
  salary: 15,
  location: 15,
  recency: 5,
};

const VETO_LINE = 40;

/* The two poses the radar travels between. */
const MATCH: Record<Axis, number> = {
  skills: 92,
  seniority: 85,
  salary: 80,
  location: 90,
  recency: 96,
};
const NONMATCH: Record<Axis, number> = {
  skills: 18,
  seniority: 28,
  salary: 32,
  location: 36,
  recency: 44,
};

/* Seconds spent easing from one pose to the other; a full round trip is 2x. */
const LEG = 3;

const lerp = (a: number, b: number, p: number) => a + (b - a) * p;
/* smootherstep — dwells briefly at each pose so both states read clearly. */
const smoother = (x: number) => x * x * x * (x * (x * 6 - 15) + 10);

function pt(i: number, v: number, cx: number, cy: number, r: number): [number, number] {
  const a = (-90 + i * 72) * (Math.PI / 180);
  const d = (v / 100) * r;
  return [cx + d * Math.cos(a), cy + d * Math.sin(a)];
}
const fmt = ([x, y]: [number, number]) => `${x.toFixed(1)},${y.toFixed(1)}`;

export default function RadarDemo() {
  const [t, setT] = useState(0);
  const [reducedMotion] = useState(
    () =>
      typeof window !== 'undefined' &&
      !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches,
  );

  useEffect(() => {
    if (reducedMotion) return;

    let raf = 0;
    let start: number | null = null;
    const loop = (ts: number) => {
      if (start === null) start = ts;
      setT((ts - start) / 1000);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [reducedMotion]);

  // Triangle wave 0 -> 1 -> 0 over 2*LEG seconds, eased. Static match if reduced.
  const phase = (t % (LEG * 2)) / LEG; // 0..2
  const tri = phase <= 1 ? phase : 2 - phase; // 0..1..0
  const p = reducedMotion ? 1 : smoother(tri);

  const vals: Record<Axis, number> = Object.fromEntries(
    AXES.map((a) => [a, lerp(NONMATCH[a], MATCH[a], p)]),
  ) as Record<Axis, number>;

  const score = Math.round(AXES.reduce((s, a) => s + (vals[a] * WEIGHT_PTS[a]) / 100, 0));
  const vetoed = score < VETO_LINE;
  const stroke = vetoed ? '#ff4d5e' : '#3dff73';
  const fill = vetoed ? 'rgba(255,77,94,0.20)' : 'rgba(61,255,115,0.18)';

  const cx = 170;
  const cy = 130;
  const r = 88;
  const rings = [25, 50, 75, 100];

  return (
    <DemoShell
      title="> live fit-score radar"
      label="Animated radar chart cycling between a rejected candidate and a strong match"
    >
      <div className="radar-grid radar-grid--solo">
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

            {/* morphing polygon (flat translucent fill, crisp stroke) */}
            <polygon
              className="radar-poly"
              points={AXES.map((a, i) => fmt(pt(i, vals[a], cx, cy, r))).join(' ')}
              fill={fill}
              stroke={stroke}
              strokeWidth="3"
              strokeLinejoin="round"
            />

            {/* vertex markers */}
            {AXES.map((a, i) => {
              const [vx, vy] = pt(i, vals[a], cx, cy, r);
              return (
                <circle key={a} cx={vx} cy={vy} r="4" fill={stroke} stroke="#08080c" strokeWidth="2" />
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
                  fill="#a9a7ba"
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
          {vetoed ? (
            <p className="radar-verdict bad">X VETOED: under the line</p>
          ) : (
            <p className="radar-verdict good">+ PROCEED: strong match</p>
          )}
          <p className="radar-note">
            skills 50 · seniority 15 · salary 15 · location 15 · recency 5
          </p>
        </div>
      </div>
    </DemoShell>
  );
}

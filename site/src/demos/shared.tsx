/* Shared primitives for the interactive feature demos. Pixel-styled,
   client-side only, mock data. Follows DESIGN_SYSTEM.md. */
import type { ReactNode } from 'react';

export function DemoShell({
  title,
  children,
  label,
}: {
  title: string;
  children: ReactNode;
  label: string;
}) {
  return (
    <div className="idemo" role="region" aria-label={label}>
      <p className="idemo-title">{title}</p>
      {children}
    </div>
  );
}

export function Bar({
  label,
  value,
  max = 100,
  tone = '',
  suffix = '',
}: {
  label: string;
  value: number;
  max?: number;
  tone?: '' | 'red' | 'amber' | 'go';
  suffix?: string;
}) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className="bar-row">
      <span className="bar-label">{label}</span>
      <div className="bar-track" aria-hidden="true">
        <div className={`bar-fill ${tone}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="bar-val">
        {value}
        {suffix}
      </span>
    </div>
  );
}

export function Flag({
  tone,
  children,
}: {
  tone: 'red' | 'go' | 'amber';
  children: ReactNode;
}) {
  return <span className={`flag ${tone}`}>{children}</span>;
}

export function PxSlider({
  label,
  value,
  onChange,
  min = 0,
  max = 100,
  weight,
  hint,
  tone = 'go',
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  /** Optional weight badge, e.g. 50 renders "x50". */
  weight?: number;
  /** Optional small caption under the track (e.g. live contribution). */
  hint?: string;
  /** Fill colour of the track up to the thumb. */
  tone?: 'go' | 'amber' | 'red';
}) {
  const pct = Math.max(0, Math.min(100, ((value - min) / (max - min)) * 100));
  return (
    <label className={`px-range tone-${tone}`}>
      <span className="px-range-label">
        <span className="px-range-name">
          {label}
          {weight != null && <em className="px-range-wt">x{weight}</em>}
        </span>
        <b>{value}</b>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        aria-label={label}
        style={{ ['--pct' as string]: `${pct}%` }}
      />
      {hint && <span className="px-range-hint">{hint}</span>}
    </label>
  );
}

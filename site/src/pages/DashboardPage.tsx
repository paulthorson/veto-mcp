/* Mission-control dashboard: lifecycle deltas + analytics in the pixel
   visual language. Data comes from localStorage (VETO_DASH_KEY) when
   present, otherwise the seeded demo dataset. */
import { useMemo, useState } from 'react';
import { PxTag, PixelIcon, BotCrew } from '../px';
import {
  boardStats,
  computeKpis,
  detectDeltas,
  funnelCounts,
} from '../dash/deltas';
import { loadDashboardData } from '../dash/demoData';
import { VETO_DASH_KEY, type DashboardData, type Delta } from '../dash/types';

function loadData(): { data: DashboardData; live: boolean } {
  try {
    const raw = localStorage.getItem(VETO_DASH_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && Array.isArray(parsed.applications)) {
        return { data: parsed as DashboardData, live: true };
      }
    }
  } catch {
    /* fall through to demo data */
  }
  return { data: loadDashboardData(), live: false };
}

function timeAgo(iso: string): string {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 3600) return `${Math.max(1, Math.floor(s / 60))}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

function DeltaChip({ value, suffix = '' }: { value: number; suffix?: string }) {
  if (!value) return <span className="kpi-delta flat">—</span>;
  const up = value > 0;
  return (
    <span className={`kpi-delta ${up ? 'up' : 'down'}`}>
      {up ? '+' : ''}
      {value}
      {suffix} <span className="kpi-delta-sub">vs 7d</span>
    </span>
  );
}

/* 14-day activity: applied (green) vs vetoed (red) pixel bars. */
function ActivityChart({ data }: { data: DashboardData }) {
  const days = useMemo(() => {
    const out: { label: string; applied: number; vetoed: number }[] = [];
    const now = new Date();
    for (let i = 13; i >= 0; i--) {
      const d = new Date(now.getTime() - i * 86400000);
      const key = d.toISOString().slice(0, 10);
      out.push({
        label: i % 2 === 0 ? `${d.getMonth() + 1}/${d.getDate()}` : '',
        applied: 0,
        vetoed: 0,
      });
      void key;
    }
    for (const a of data.applications) {
      const at = a.applied_at ?? a.stage_history[0]?.at;
      if (!at) continue;
      const idx = 13 - Math.floor((now.getTime() - new Date(at).getTime()) / 86400000);
      if (idx < 0 || idx > 13) continue;
      out[idx].applied += 1;
    }
    for (const a of data.applications) {
      const v = a.stage_history.find((e) => e.stage === 'vetoed');
      if (!v) continue;
      const idx = 13 - Math.floor((now.getTime() - new Date(v.at).getTime()) / 86400000);
      if (idx < 0 || idx > 13) continue;
      out[idx].vetoed += 1;
    }
    return out;
  }, [data]);

  const max = Math.max(1, ...days.map((d) => d.applied + d.vetoed));
  const W = 560, H = 180, PAD = 8, AX = 26;
  const bw = (W - AX - PAD) / 14;
  const bh = (v: number) => (v / max) * (H - 44);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="dash-chart" shapeRendering="crispEdges" role="img"
      aria-label="Applications and vetoes per day, last 14 days">
      {days.map((d, i) => {
        const x = AX + i * bw + 2;
        const w = bw - 4;
        const ah = bh(d.applied), vh = bh(d.vetoed);
        return (
          <g key={i}>
            {d.applied > 0 && (
              <rect x={x} y={H - 30 - ah} width={w} height={ah} fill="#34d399" />
            )}
            {d.vetoed > 0 && (
              <rect x={x} y={H - 30 - ah - vh} width={w} height={vh} fill="#ff4d5e" />
            )}
            {d.label && (
              <text x={x + w / 2} y={H - 12} textAnchor="middle" className="chart-label">{d.label}</text>
            )}
          </g>
        );
      })}
      <line x1={AX} y1={H - 30} x2={W - PAD} y2={H - 30} stroke="#2a2a35" strokeWidth="2" />
    </svg>
  );
}

function SignalFeed({ deltas }: { deltas: Delta[] }) {
  const [filter, setFilter] = useState<string>('all');
  const kinds = ['all', 'stage', 'veto', 'new_match', 'posting_edit', 'stale'] as const;
  const labels: Record<string, string> = {
    all: 'all', stage: 'movement', veto: 'vetoes', new_match: 'new matches',
    posting_edit: 'posting edits', stale: 'stale',
  };
  const shown = filter === 'all' ? deltas : deltas.filter((d) => d.kind === filter);
  return (
    <div>
      <div className="feed-filters" role="group" aria-label="Filter signals">
        {kinds.map((k) => (
          <button key={k} className={`feed-filter ${filter === k ? 'on' : ''}`}
            onClick={() => setFilter(k)} aria-pressed={filter === k}>
            {labels[k]}
          </button>
        ))}
      </div>
      <ul className="signal-list">
        {shown.slice(0, 12).map((d) => (
          <li key={d.id} className={`signal tone-${d.tone || 'none'}`}>
            <span className="signal-icon"><PixelIcon name={d.icon} size={20} /></span>
            <span className="signal-body">
              <span className="signal-title">{d.title}</span>
              <span className="signal-detail">{d.detail}</span>
            </span>
            <span className="signal-at">{timeAgo(d.at)}</span>
          </li>
        ))}
        {shown.length === 0 && <li className="signal-empty">No signals in this bucket. All quiet.</li>}
      </ul>
    </div>
  );
}

export default function DashboardPage() {
  const [{ data, live }] = useState(loadData);
  const deltas = useMemo(() => detectDeltas(data), [data]);
  const kpis = useMemo(() => computeKpis(data.applications), [data]);
  const prevKpis = useMemo(() => computeKpis(data.prev_applications), [data]);
  const funnel = useMemo(() => funnelCounts(data.applications), [data]);
  const boards = useMemo(() => boardStats(data.applications), [data]);
  const maxFunnel = Math.max(1, ...funnel.map((f) => f.count));

  const cards = [
    { label: 'active pipeline', value: String(kpis.active), icon: 'bolt', delta: kpis.active - prevKpis.active, tone: '' },
    { label: 'veto rate', value: `${Math.round(kpis.vetoRate * 100)}%`, icon: 'shield', delta: Math.round((kpis.vetoRate - prevKpis.vetoRate) * 100), suffix: 'pts', tone: 'veto' },
    { label: 'response rate', value: `${Math.round(kpis.responseRate * 100)}%`, icon: 'chat', delta: Math.round((kpis.responseRate - prevKpis.responseRate) * 100), suffix: 'pts', tone: 'go' },
    { label: 'interviewing', value: String(kpis.interviews), icon: 'gauge', delta: kpis.interviews - prevKpis.interviews, tone: 'go' },
    { label: 'offers', value: String(kpis.offers), icon: 'star', delta: kpis.offers - prevKpis.offers, tone: 'amber' },
  ];

  return (
    <main id="top">
      <section className="page-hero">
        <div className="wrap">
          <a className="back-link" href="#/">{'<'} Home</a>
          <div className="page-hero-inner">
            <PxTag variant="red">Mission control</PxTag>
            <h1 className="page-title">Watch the machine.</h1>
            <p className="page-lede">
              Every application Veto touches, every posting edit it catches, every
              stage change — detected as deltas and tracked here.
              {live ? ' Showing your live export.' : ' Showing seeded demo data.'}
            </p>
          </div>
        </div>
      </section>

      {/* KPI CARDS */}
      <section className="section">
        <div className="wrap">
          <div className="kpi-grid">
            {cards.map((c) => (
              <div key={c.label} className={`kpi-card tone-${c.tone || 'none'}`}>
                <span className="kpi-icon"><PixelIcon name={c.icon} size={22} /></span>
                <span className="kpi-value">{c.value}</span>
                <span className="kpi-label">{c.label}</span>
                <DeltaChip value={c.delta} suffix={c.suffix ?? ''} />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ACTIVITY + FUNNEL */}
      <section className="section">
        <div className="wrap dash-grid">
          <div className="dash-card">
            <h2 className="dash-card-title"><PixelIcon name="chart" size={20} /> Activity · 14d</h2>
            <ActivityChart data={data} />
            <p className="dash-legend">
              <span className="sw go" /> applied <span className="sw veto" /> vetoed
              {kpis.medianDaysToResponse !== null &&
                <span className="dash-note"> · median {kpis.medianDaysToResponse.toFixed(0)}d to first response</span>}
            </p>
          </div>
          <div className="dash-card">
            <h2 className="dash-card-title"><PixelIcon name="ledger" size={20} /> Pipeline funnel</h2>
            <ul className="funnel">
              {funnel.map((f) => (
                <li key={f.label} className="funnel-row">
                  <span className="funnel-label">{f.label}</span>
                  <span className="funnel-track">
                    <span className={`funnel-fill tone-${f.tone || 'none'}`}
                      style={{ width: `${Math.max(3, (f.count / maxFunnel) * 100)}%` }} />
                  </span>
                  <span className="funnel-count">{f.count}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* SIGNAL FEED + BOARDS */}
      <section className="section">
        <div className="wrap dash-grid">
          <div className="dash-card">
            <h2 className="dash-card-title"><PixelIcon name="bolt" size={20} /> Signal feed · {deltas.length} deltas</h2>
            <SignalFeed deltas={deltas} />
          </div>
          <div className="dash-card">
            <h2 className="dash-card-title"><PixelIcon name="globe" size={20} /> Response rate by board</h2>
            <ul className="funnel">
              {boards.map((b) => (
                <li key={b.board} className="funnel-row">
                  <span className="funnel-label">{b.board}</span>
                  <span className="funnel-track">
                    <span className="funnel-fill tone-go" style={{ width: `${Math.max(3, b.rate * 100)}%` }} />
                  </span>
                  <span className="funnel-count">{Math.round(b.rate * 100)}%</span>
                </li>
              ))}
            </ul>
            <p className="dash-note">Share of applied that drew a response.</p>
          </div>
        </div>
      </section>

      {/* CREW */}
      <section className="section">
        <div className="wrap narrow" style={{ textAlign: 'center' }}>
          <p className="dash-card-title" style={{ justifyContent: 'center' }}>The crew keeps watch</p>
          <BotCrew />
        </div>
      </section>

      <section className="section">
        <div className="wrap narrow">
          <p className="dash-footnote">
            {'>'} demo data is seeded — to wire your own, export <code>analytics.generate_report()</code> +
            lifecycle entries as JSON and store under <code>{VETO_DASH_KEY}</code> in localStorage.
          </p>
        </div>
      </section>
    </main>
  );
}

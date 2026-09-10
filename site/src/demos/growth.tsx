/* Growth demos: AI proficiency tracks, mentor matchmaking, warm path. */
import { DemoShell, Flag } from './shared';

/* ---------------- AI proficiency tracks ---------------- */

const TRACKS = [
  { name: 'Engineer', lessons: 7, ex: 'Ship a PR reviewed by AI, then review the AI' },
  { name: 'Product', lessons: 6, ex: 'Draft a spec with AI as sparring partner' },
  { name: 'Data', lessons: 7, ex: 'Notebook analysis with AI-generated checks' },
  { name: 'Design', lessons: 6, ex: 'Critique an AI-generated mock honestly' },
  { name: 'Marketing', lessons: 6, ex: 'Write 10 variants, keep your voice' },
  { name: 'Sales', lessons: 6, ex: 'Role-play objections with AI' },
  { name: 'Generalist', lessons: 6, ex: 'Automate one weekly chore end to end' },
];

export function TracksDemo() {
  return (
    <DemoShell title="> ai proficiency demo" label="Seven AI proficiency tracks, each with hands-on lessons and an ethics module">
      <div className="tracks-grid">
        {TRACKS.map((t) => (
          <div key={t.name} className="track-card">
            <p className="track-name">{t.name}</p>
            <p className="track-lessons">{t.lessons} lessons</p>
            <p className="track-ex">{t.ex}</p>
            <p className="track-ethics">
              <Flag tone="amber">ETHICS INCLUDED</Flag>
            </p>
          </div>
        ))}
      </div>
      <p className="idemo-foot">
        Diagnostics place you; streaks keep you honest. Practice is practice —
        never presented as a credential.
      </p>
    </DemoShell>
  );
}

/* ---------------- Mentor matchmaking ---------------- */

const MENTORS = [
  {
    name: 'S.K. — Staff Eng, fintech',
    match: 92,
    why: 'Same industry + role, 2 levels up. Open to mock system-design sessions.',
    topics: 'system design · leveling',
  },
  {
    name: 'M.R. — Eng Manager, devtools',
    match: 84,
    why: 'Matched on "negotiation" and "executive presence" — your weakest drill areas.',
    topics: 'negotiation · presence',
  },
  {
    name: 'J.C. — Senior Eng, infra',
    match: 78,
    why: 'Career switcher like you. Strong on interview storytelling.',
    topics: 'storytelling · switching',
  },
];

export function MentorDemo() {
  return (
    <DemoShell title="> mentor match demo" label="Mentor matchmaking: sample match cards with scores and reasons">
      <div className="mentor-list">
        {MENTORS.map((m) => (
          <div key={m.name} className="mentor-card">
            <div className="mentor-top">
              <p className="mentor-name">{m.name}</p>
              <p className="mentor-match">{m.match}%</p>
            </div>
            <p className="mentor-why">{m.why}</p>
            <p className="mentor-topics">{m.topics}</p>
          </div>
        ))}
      </div>
      <p className="idemo-foot">
        Opt-in mentors, privacy your way (name or initials). Veto drafts the
        intro {'<'}300 chars — you send it yourself on LinkedIn.
      </p>
    </DemoShell>
  );
}

/* ---------------- Warm path ---------------- */

export function WarmPathDemo() {
  return (
    <DemoShell title="> warm path demo" label="Referral radar: a warm-path graph from you to the hiring manager">
      <svg viewBox="0 0 560 220" className="warm-svg" aria-hidden="true">
        <line x1="90" y1="110" x2="230" y2="110" stroke="#3dff73" strokeWidth="3" strokeDasharray="8 6" />
        <line x1="330" y1="110" x2="470" y2="110" stroke="#3dff73" strokeWidth="3" strokeDasharray="8 6" />
        <g>
          <rect x="30" y="80" width="120" height="60" fill="#14141c" stroke="#41e6ff" strokeWidth="3" />
          <text x="90" y="105" textAnchor="middle" fill="#f2f0e9" fontSize="16" fontFamily="VT323, monospace">YOU</text>
          <text x="90" y="126" textAnchor="middle" fill="#6f6d84" fontSize="13" fontFamily="VT323, monospace">2nd degree</text>
        </g>
        <g>
          <rect x="230" y="80" width="100" height="60" fill="#14141c" stroke="#3dff73" strokeWidth="3" />
          <text x="280" y="105" textAnchor="middle" fill="#f2f0e9" fontSize="16" fontFamily="VT323, monospace">MAYA R.</text>
          <text x="280" y="126" textAnchor="middle" fill="#6f6d84" fontSize="13" fontFamily="VT323, monospace">ex-colleague</text>
        </g>
        <g>
          <rect x="410" y="80" width="120" height="60" fill="#14141c" stroke="#ffb000" strokeWidth="3" />
          <text x="470" y="105" textAnchor="middle" fill="#f2f0e9" fontSize="16" fontFamily="VT323, monospace">J. CHEN</text>
          <text x="470" y="126" textAnchor="middle" fill="#6f6d84" fontSize="13" fontFamily="VT323, monospace">hiring mgr</text>
        </g>
        <text x="280" y="180" textAnchor="middle" fill="#a9a7ba" fontSize="15" fontFamily="VT323, monospace">
          TargetCo · platform eng — via your Connections.csv
        </text>
      </svg>
      <p className="idemo-foot">
        Referral radar mines your LinkedIn export for target-company insiders
        and drafts the ask. Warm beats cold, every time.
      </p>
    </DemoShell>
  );
}

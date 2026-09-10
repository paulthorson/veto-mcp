/* Governed AI crew demo: 11 personas + 20 red-team specialists. */
import { DemoShell, Flag } from './shared';

const PERSONAS = [
  { id: 'ceo', role: 'Routes work, resolves by precedent', never: 'Never invents policy' },
  { id: 'chief_of_staff', role: 'Funnels decisions to you, owns the queue', never: 'Never clears a veto' },
  { id: 'pm', role: 'Owns the problem, writes the brief', never: 'Never specifies the solution' },
  { id: 'eng', role: 'Implements to spec, tests first-class', never: 'Never ships without QA green' },
  { id: 'ux', role: 'Owns the design system and visual QA', never: 'Never drops accessibility' },
  { id: 'qa', role: 'Verifies against the story, hunts regressions', never: 'Never passes on vibes' },
  { id: 'researcher', role: 'Establishes what is true, cited', never: 'Never recommends or fills gaps' },
  { id: 'scout', role: 'Skeptical job search and vetting', never: 'Never trusts a posting at face value' },
  { id: 'tailor_agent', role: 'Honesty-first resume tailoring', never: 'Never invents experience' },
  { id: 'coach', role: 'Adversarial practice, supportive review', never: 'Never goes easy in the sim' },
  { id: 'red', role: 'Adversarial reviewer of everything', never: 'Never edits, reports only' },
];

const RED_TEAM = [
  'eng-critic', 'qa-critic', 'ux-critic', 'res-critic', 'res-evidence-advocate',
  'sec-security-adversary', 'sec-vuln-scan', 'sec-secret-exposure-scan',
  'comp-compliance-adversary', 'priv-privacy-adversary', 'prod-product-adversary',
  'ops-ops-adversary', 'doc-docs-adversary', 'prom-prompt-adversary',
  'univ-universal-adversary', 'univ-blind-spot-search', 'univ-counter-case',
  'ux-adversarial-ux', 'qa-edge-case-reviewer', 'eng-reliability-reviewer',
];

export default function CrewDemo() {
  return (
    <DemoShell title="> governed crew demo" label="The governed AI crew: eleven personas plus twenty red-team specialists">
      <p className="crew-lede">
        An entire job-search company working for you. Every agent spawned,
        reviewed, and merged under the agentic-governance framework. Veto
        screens before work, Red reviews after, and a human gates what matters.
      </p>
      <div className="persona-grid">
        {PERSONAS.map((p) => (
          <div key={p.id} className="persona-card">
            <p className="persona-id">{p.id}</p>
            <p className="persona-role">{p.role}</p>
            <p className="persona-never">
              <Flag tone="red">X {p.never}</Flag>
            </p>
          </div>
        ))}
      </div>
      <p className="crew-redhead">RED-TEAM SPECIALISTS (20)</p>
      <div className="red-list">
        {RED_TEAM.map((r) => (
          <span key={r} className="red-chip">{r}</span>
        ))}
      </div>
      <p className="idemo-foot">
        Personas come from the framework's own harnesses, adapted to the
        job-search domain, prohibitions intact.
      </p>
    </DemoShell>
  );
}

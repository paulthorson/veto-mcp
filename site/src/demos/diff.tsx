/* Resume diff + approval flow demo (client-side mock of tailor.py).
   Shows base vs tailored bullets as a diff, with an approve gate. */
import { useState } from 'react';
import { DemoShell } from './shared';

const BASE = [
  'Built internal tools for the data team',
  'Helped migrate a few services to the cloud',
  'Python, SQL, some shell scripting',
  'On-call rotation for backend services',
];

const TAILORED = [
  '+ Led migration of 12 services to Kubernetes — deploy time down 40%',
  '+ Built Python data tooling used by 200+ analysts daily',
  '+ Backend on-call: owned p99 latency, cut incidents 30%',
  '  Python · SQL · Kubernetes — front-loaded around posting keywords',
];

export default function DiffDemo() {
  const [approved, setApproved] = useState(false);
  return (
    <DemoShell title="> resume diff demo" label="Side-by-side resume diff with an approval gate">
      <div className="diff-cols">
        <div className="diff-pane">
          <p className="diff-head">BASE RESUME</p>
          {BASE.map((l, i) => (
            <p key={i} className="diff-line">
              {l}
            </p>
          ))}
        </div>
        <div className="diff-pane">
          <p className="diff-head go">TAILORED — platform eng @ fintech</p>
          {TAILORED.map((l, i) => (
            <p key={i} className={`diff-line ${l.startsWith('+') ? 'add' : ''}`}>
              {l}
            </p>
          ))}
        </div>
      </div>
      <p className="diff-missing">
        <span className="flag amber">MISSING</span> Go, Terraform — reported as
        gaps, never padded into the resume.
      </p>
      {approved ? (
        <p className="diff-approved">+ APPROVED — variant saved to tailored/acme-platform.json</p>
      ) : (
        <button
          type="button"
          className="px-btn primary diff-btn"
          onClick={() => setApproved(true)}
        >
          {'>'} Approve this variant
        </button>
      )}
      <p className="idemo-foot">
        Nothing is final until you approve. Unapproved variants never leave the
        diff view.
      </p>
    </DemoShell>
  );
}

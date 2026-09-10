/* Cover letter honesty scan demo: a flagged draft vs a clean draft. */
import { DemoShell, Flag } from './shared';

export default function CoverDemo() {
  return (
    <DemoShell title="> honesty scan demo" label="Cover letter honesty scan: a flagged invented claim versus a clean draft">
      <div className="diff-cols">
        <div className="diff-pane bad">
          <p className="diff-head red">DRAFT — SCAN FAILED</p>
          <p className="cover-text">
            Dear hiring manager, I am excited to apply for the platform engineer
            role. <span className="hl-bad">I increased revenue by 300% at my
            last company,</span> and I led a team of 40 engineers.
          </p>
          <p className="cover-flag">
            <Flag tone="red">X FLAG: "increased revenue by 300%"</Flag>
          </p>
          <p className="cover-flag">
            <Flag tone="red">X FLAG: "team of 40 engineers"</Flag>
          </p>
          <p className="cover-note">Neither claim traces to the profile. Blocked.</p>
        </div>
        <div className="diff-pane good">
          <p className="diff-head go">DRAFT — SCAN CLEAN</p>
          <p className="cover-text">
            Dear hiring manager, I am excited to apply for the platform engineer
            role. I led the migration of 12 services to Kubernetes, cutting
            deploy time 40%, and I carry the backend on-call rotation.
          </p>
          <p className="cover-flag">
            <Flag tone="go">+ CLEAN: every claim traces to a profile bullet</Flag>
          </p>
          <p className="cover-note">Gaps are named as gaps — never invented.</p>
        </div>
      </div>
      <p className="idemo-foot">
        honesty_scan checks numbers, proper nouns, and skills against your
        profile before any letter proceeds.
      </p>
    </DemoShell>
  );
}

/* Chakra feature G: the resume-input step of the immersive grill demo.
 *
 * Mounted AFTER the job-input step (feature E): the visitor pastes their
 * resume and Veto scores it against the fed posting's keywords
 * (Jobscan-style). Skipping keeps the verdict exactly as today — no
 * resume-match panel, no gap-driven drill focus.
 *
 * Contract (see INTEGRATION-G.md):
 *   - onSubmit(rawResumeText) on "Score my resume"
 *   - onSkip() on "Skip — grill me without my resume"
 *   - data-testid: resume-input-step, resume-paste-input, resume-submit, resume-skip
 *
 * The parent computes scoreResumeMatch(resumeText, job) at the verdict
 * stage; this step passes the raw text through untouched. Nothing here
 * invents resume content — user-provided data only.
 */
import { useState, type FormEvent } from 'react';

interface ResumeInputStepProps {
  onSubmit: (resumeText: string) => void;
  onSkip: () => void;
}

export function ResumeInputStep({ onSubmit, onSkip }: ResumeInputStepProps) {
  const [text, setText] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onSubmit(text);
  };

  return (
    <section
      className="resume-input-step"
      data-testid="resume-input-step"
      aria-labelledby="resume-input-heading"
    >
      <h2 id="resume-input-heading" className="resume-input-title">
        Paste your resume — Veto scores it against the posting
      </h2>
      <p id="resume-input-help" className="resume-input-help">
        The grill already knows the role&rsquo;s requirements. Give it your
        resume and it scores the match — then drills you on the gaps it
        finds, so the verdict speaks to <em>your</em> background. Prefer
        the classic? Skip and the demo grills you without it.
      </p>
      <form onSubmit={handleSubmit} className="resume-input-form">
        <label htmlFor="resume-paste" className="resume-input-label">
          Resume text
        </label>
        <textarea
          id="resume-paste"
          data-testid="resume-paste-input"
          className="resume-input-textarea"
          rows={10}
          value={text}
          onChange={(e) => setText(e.target.value)}
          aria-describedby="resume-input-help"
          placeholder="Paste your resume here — experience, skills, and the tools you’ve used…"
        />
        <div className="resume-input-actions">
          <button
            type="submit"
            data-testid="resume-submit"
            className="resume-input-submit"
            disabled={text.trim().length === 0}
          >
            Score my resume
          </button>
          <button
            type="button"
            data-testid="resume-skip"
            className="resume-input-skip"
            onClick={onSkip}
          >
            Skip — grill me without my resume
          </button>
        </div>
      </form>
    </section>
  );
}

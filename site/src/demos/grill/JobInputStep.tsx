/* Chakra feature E: the job-input step of the immersive grill demo.
 *
 * Mounted FIRST (before the level pick): the visitor pastes a job
 * posting and the grill tailors the interview to that role. Skipping
 * keeps the default fixed posting — the demo works exactly as today.
 *
 * Contract (see INTEGRATION-E.md):
 *   - onSubmit(parseJobPosting(text)) on "Tailor my grill"
 *   - onSkip() on "Skip — use the default posting"
 *   - data-testid: job-input-step, job-paste-input, job-submit, job-skip
 */
import { useState, type FormEvent } from 'react';
import type { JobContext } from '../../lib/chakraTypes';
import { parseJobPosting } from '../../lib/jobTargeting';

interface JobInputStepProps {
  onSubmit: (job: JobContext) => void;
  onSkip: () => void;
}

export function JobInputStep({ onSubmit, onSkip }: JobInputStepProps) {
  const [text, setText] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onSubmit(parseJobPosting(text));
  };

  return (
    <section
      className="job-input-step"
      data-testid="job-input-step"
      aria-labelledby="job-input-heading"
    >
      <h2 id="job-input-heading" className="job-input-title">
        Feed Veto the job you&rsquo;re targeting
      </h2>
      <p id="job-input-help" className="job-input-help">
        Paste a job posting below and the grill interviews you for{' '}
        <em>that</em> role — questions reference its requirements, the
        verdict scores you against them. Prefer the classic? Skip and the
        demo uses its default posting.
      </p>
      <form onSubmit={handleSubmit} className="job-input-form">
        <label htmlFor="job-paste" className="job-input-label">
          Job posting text
        </label>
        <textarea
          id="job-paste"
          data-testid="job-paste-input"
          className="job-input-textarea"
          rows={10}
          value={text}
          onChange={(e) => setText(e.target.value)}
          aria-describedby="job-input-help"
          placeholder="Paste the full job posting here — title, company, and requirements…"
        />
        <div className="job-input-actions">
          <button
            type="submit"
            data-testid="job-submit"
            className="job-input-submit"
            disabled={text.trim().length === 0}
          >
            Tailor my grill
          </button>
          <button
            type="button"
            data-testid="job-skip"
            className="job-input-skip"
            onClick={onSkip}
          >
            Skip — use the default posting
          </button>
        </div>
      </form>
    </section>
  );
}

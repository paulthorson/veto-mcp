/* Feature C (Chakra): DefendStep — the brutal grill's "defend your answer" stage.
 * Props contract (integrator: wire into DemoPage's brutal FullGrill flow):
 *   questionText   — the question the candidate answered
 *   candidateAnswer — the answer under fire
 *   defendPrompt   — from getDefendPrompt(question, candidateAnswer)
 *   onComplete     — called with the typed defense; the parent runs
 *                    assessDefense() and records the result.
 * Keyboard-operable: real <textarea> and <button>. The E2E script drives
 * it with a real type + click, and waits on the stable "Veto demands a
 * defense" kicker below.
 */
import { useState } from 'react';

export interface DefendStepProps {
  questionText: string;
  candidateAnswer: string;
  defendPrompt: string;
  onComplete: (defense: string) => void;
}

export default function DefendStep({
  questionText,
  candidateAnswer,
  defendPrompt,
  onComplete,
}: DefendStepProps) {
  const [defense, setDefense] = useState('');
  const ready = defense.trim().length > 0;

  const submit = () => {
    const text = defense.trim();
    if (text === '') return;
    onComplete(text);
  };

  return (
    <div data-testid="defend-step" role="group" aria-label="Defend your answer">
      <p className="demo-defend-kicker">Veto demands a defense</p>
      <div className="demo-defend-quote">
        <p className="demo-defend-q">{questionText}</p>
        <p className="demo-defend-a">
          <span className="demo-msg-tag">you said</span>
          <span className="demo-msg-text">“{candidateAnswer}”</span>
        </p>
      </div>
      <p className="demo-defend-demand">{defendPrompt}</p>
      <label className="demo-defend-label" htmlFor="defend-input">
        Your defense
      </label>
      <textarea
        id="defend-input"
        data-testid="defend-input"
        className="demo-textarea"
        rows={4}
        value={defense}
        placeholder="Explain it like you lived it."
        onChange={(e) => setDefense(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submit();
        }}
      />
      <div className="demo-opts">
        <button
          type="button"
          data-testid="defend-submit"
          className="demo-opt demo-send"
          disabled={!ready}
          onClick={submit}
        >
          Defend it
        </button>
      </div>
    </div>
  );
}

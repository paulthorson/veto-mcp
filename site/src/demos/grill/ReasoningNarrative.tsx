/* Feature A — reasoning narrative display for the grill verdict.
 * Presentational only: renders a ReasoningNarrative built by
 * buildReasoningNarrative (site/src/lib/reasoningNarrative.ts).
 * No interactivity beyond render; no data fetching; no side effects.
 *
 * Data-testid contract (used by site/e2e/chakra-a.e2e.mjs — keep stable):
 *   [data-testid="reasoning-narrative"]          the section
 *   [data-testid="reasoning-narrative-summary"]  the 2–3 sentence summary
 *   [data-testid="reasoning-narrative-item"]     one per answer, data-qid set
 * The heading text "How they approached it" is also asserted by E2E.
 */
import type { ReasoningNarrative as ReasoningNarrativeData } from '../../lib/chakraTypes';

export function ReasoningNarrative({ narrative }: { narrative: ReasoningNarrativeData }) {
  return (
    <section
      className="demo-reasoning-narrative"
      data-testid="reasoning-narrative"
      aria-label="How the candidate approached the grill"
    >
      <h3 className="feature-title">How they approached it</h3>
      <p className="feature-body" data-testid="reasoning-narrative-summary">
        {narrative.summary}
      </p>
      <ul className="demo-reasoning-list">
        {narrative.perAnswer.map((entry) => (
          <li
            key={entry.qid}
            className="demo-reasoning-item"
            data-testid="reasoning-narrative-item"
            data-qid={entry.qid}
          >
            {entry.narrative}
          </li>
        ))}
      </ul>
    </section>
  );
}

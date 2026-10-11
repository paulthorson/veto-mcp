/* Feature D: presentational view for a repository task.
 * Pure display — no state, no fetching. Integrator mounts this in DemoPage
 * (see INTEGRATION-D.md). Contract: data-testid="repo-task-view" on the root,
 * with title, file tree, and check description inside.
 */
import type { RepoTask } from '../../lib/chakraTypes';

/** File tree of the acme-api fixture — must match site/public/fixtures/acme-api. */
export const FILES: string[] = [
  'package.json',
  'README.md',
  'src/server.js',
  'src/routes/orders.js',
  'src/db/memory.js',
  'tests/smoke.test.js',
];

const box: React.CSSProperties = {
  border: '1px solid #e5e7eb',
  borderRadius: 12,
  padding: '1.25rem 1.5rem',
  margin: '1rem 0',
  background: '#fafafa',
  color: '#1f2937', // explicit dark text: the site body color (#d7e0e6) is ~1.3:1 on this light box
  textAlign: 'left',
  maxWidth: 640,
};

export function RepoTaskView({ task }: { task: RepoTask }) {
  return (
    <section data-testid="repo-task-view" aria-label={task.title} style={box}>
      <h3 data-testid="repo-task-title" style={{ marginTop: 0 }}>
        {task.title}
      </h3>
      <p data-testid="repo-task-description" style={{ color: '#1f2937' }}>{task.taskDescription}</p>
      <p data-testid="repo-task-repo" style={{ color: '#555' }}>
        Repo: <code>{task.repoPath}</code>
      </p>
      <h4 style={{ marginBottom: '0.25rem' }}>Files</h4>
      <ul data-testid="repo-task-files" style={{ marginTop: 0, paddingLeft: '1.25rem' }}>
        {FILES.map((f) => (
          <li key={f}>
            <code>{f}</code>
          </li>
        ))}
      </ul>
      <h4 style={{ marginBottom: '0.25rem' }}>How the grill will check your work</h4>
      <p data-testid="repo-task-check" style={{ marginTop: 0, color: '#1f2937' }}>
        {task.checkDescription}
      </p>
    </section>
  );
}

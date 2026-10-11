/* Feature D: tasks against a real repository fixture (the Acme API).
 * getRepoTasks() returns the task set the grill offers; see
 * src/demos/grill/INTEGRATION-D.md for wiring and future fixture selection.
 */
import type { JobContext, RepoTask } from './chakraTypes';

/** Keywords that make an API fixture a natural fit for a fed job. */
const API_FIT = ['backend', 'api', 'node', 'node.js', 'express', 'server', 'rest'];

export function getRepoTasks(job?: JobContext): RepoTask[] {
  const keywords = (job?.roleKeywords ?? []).map((k) => k.toLowerCase());
  const fitsApi = keywords.some((k) => API_FIT.some((a) => k.includes(a)));
  // The Acme API tasks are the default set: returned for every job (or none).
  // `fitsApi` only matters once more fixtures exist — see INTEGRATION-D.md.
  void fitsApi;
  return [
    {
      id: 'acme-api-pagination-fix',
      title: 'Fix the pagination bug',
      repoPath: 'fixtures/acme-api',
      taskDescription:
        'The order list pages overlap: GET /orders?page=2 repeats the last item from page 1. ' +
        'Find the off-by-one in src/routes/orders.js and fix it so the pages line up back to back.',
      checkDescription:
        'GET /orders?page=2 returns exactly 10 items, with no duplicates against page 1; ' +
        'page 3 returns the remaining 5.',
    },
    {
      id: 'acme-api-order-detail',
      title: 'Add GET /orders/:id',
      repoPath: 'fixtures/acme-api',
      taskDescription:
        'The single-order endpoint is a stub that returns 501 for every id. ' +
        'Implement GET /orders/:id in src/routes/orders.js: return the order when the id exists, ' +
        'and a 404 when it does not.',
      checkDescription: 'GET /orders/3 returns the order with id 3; GET /orders/999 returns 404.',
    },
  ];
}

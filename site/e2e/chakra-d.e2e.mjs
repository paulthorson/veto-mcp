/* Feature D (real-repo tasks) E2E.
 *
 * Drives the REAL demo page via CDP and asserts the repo-task view renders
 * with title + file tree + check description.
 *
 * Intended mount point (NOT yet wired — see src/demos/grill/INTEGRATION-D.md):
 *   DemoPage, standard/brutal run, as an alternative to grill question 3
 *   ("scale") or as a bonus stage, via <RepoTaskView task={task} /> from
 *   src/demos/grill/RepoTaskView.tsx. The view root carries
 *   data-testid="repo-task-view", with data-testid="repo-task-title",
 *   "repo-task-files", and "repo-task-check" inside.
 *
 * Until the integrator wires the mount, this script exits 1 reporting the
 * pending contract instead of failing silently. After wiring, it asserts the
 * rendered view and screenshots to /tmp/chakra-d-repotask.png.
 */
import { launch, newPage, serveDist } from './cdp-helper.mjs';

const SHOT = '/tmp/chakra-d-repotask.png';
const MOUNT_POINT =
  'DemoPage standard/brutal run — alternative to question 3 ("scale") or bonus stage, ' +
  '<RepoTaskView task={getRepoTasks()[0]} /> (see INTEGRATION-D.md)';

async function main() {
  const { url, stop } = await serveDist(4173);
  const browser = await launch();
  try {
    const page = await newPage(browser, `${url}/#/demo`);
    // NOTE: the site's headings are CSS-uppercased, so innerText comes
    // back uppercase for the task title and the check heading.
    const hasTitle = await page.hasText('FIX THE PAGINATION BUG');

    if (!hasTitle) {
      throw new Error(
        '[chakra-d] repo-task view NOT rendered on #/demo.\n' +
          'Intended mount point: ' + MOUNT_POINT + '\n' +
          'Selectors to wire: [data-testid="repo-task-view"] containing ' +
          '"Fix the pagination bug", "src/routes/orders.js", "no duplicates".'
      );
    }

    const body = await page.text();
    for (const expected of [
      'FIX THE PAGINATION BUG',
      'src/routes/orders.js',
      'HOW THE GRILL WILL CHECK YOUR WORK',
      'no duplicates',
    ]) {
      if (!body.includes(expected)) throw new Error(`[chakra-d] missing expected text: ${expected}`);
    }

    await page.screenshot(SHOT);
    console.log(`[chakra-d] repo-task view rendered OK; screenshot: ${SHOT}`);
  } finally {
    await browser.close();
    stop();
  }
}

main().catch((e) => {
  console.error(e.message);
  process.exit(1);
});

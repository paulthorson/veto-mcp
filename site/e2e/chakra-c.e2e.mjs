/* Feature C (Chakra) E2E: brutal defend-your-answer flow.
 *
 * Drive: serve dist -> #/demo -> pick Brutal -> answer the years question
 * with "9 years" (specific but < 20 chars, so shouldDemandDefense R2b fires)
 * -> DefendStep appears -> REALLY type a defense into the textarea and click
 * "Defend it" (FC-005: genuine interaction) -> assert the assessment verdict
 * appears -> screenshot /tmp/chakra-c-defend.png.
 *
 * PREREQUISITES:
 *   1. `npm run build` in site/ (this script serves site/dist).
 *   2. DefendStep must be wired into DemoPage's brutal FullGrill flow per
 *      site/src/demos/grill/INTEGRATION-C.md. Until then the script fails
 *      loudly at the defend-step wait with a pointer to that doc.
 *
 * Run:  cd site && node e2e/chakra-c.e2e.mjs
 * AGENTS.md: never run two CDP scripts against the same page target in
 * parallel — run E2E serially.
 */
import { launch, newPage, serveDist } from './cdp-helper.mjs';
import { setTimeout as sleep } from 'node:timers/promises';
import { existsSync } from 'node:fs';

const SHOT = '/tmp/chakra-c-defend.png';
const DEFENSE =
  'Those 9 years were mostly on-call for payments APIs; year six taught me more than the first five — I debugged a split-brain failover at 3am and rewrote the runbook.';

async function waitForText(page, substr, timeoutMs, what) {
  const t0 = Date.now();
  for (;;) {
    if (await page.hasText(substr)) return;
    if (Date.now() - t0 > timeoutMs)
      throw new Error(`timeout waiting for: ${what} (no text matching "${substr}")`);
    await sleep(500);
  }
}

function fail(msg) {
  console.error(`\nCHAKRA-C E2E FAILED: ${msg}`);
  process.exitCode = 1;
}

async function main() {
  if (!existsSync(new URL('../dist/index.html', import.meta.url).pathname)) {
    throw new Error('site/dist missing — run `npm run build` in site/ first.');
  }
  const server = await serveDist(4174);
  const browser = await launch();
  try {
    const page = await newPage(browser, `${server.url}/#/demo`);

    // Features E/G mount the job + resume input steps before the level
    // select: skip through them to reach the classic demo flow.
    for (const sel of ['[data-testid="job-skip"]', '[data-testid="resume-skip"]']) {
      try {
        await page.click(sel);
      } catch (e) {
        if (!/no such element/.test(String(e && e.message))) throw e;
      }
    }

    /* Pick the Brutal level (3rd .demo-level card). */
    await page.click('button.demo-level:nth-of-type(3)');
    await waitForText(page, 'How many years of backend experience', 10000, 'years question');

    /* Answer "9 years": specific per classifyAnswer, but < 20 chars, so
       shouldDemandDefense R2b must fire in the brutal flow. */
    await page.type('.demo-input', '9 years');
    await page.click('.demo-send');

    /* The grill must now demand a defense instead of moving on. */
    await waitForText(
      page,
      'Veto demands a defense',
      15000,
      'defend step — is DefendStep wired into DemoPage brutal flow? See src/demos/grill/INTEGRATION-C.md',
    );
    /* Deterministic prompt check: "9 years".length is 7 (odd) -> variant 1. */
    if (!(await page.hasText('Convince me'))) {
      throw new Error('defend prompt variant mismatch: expected the odd-length variant for "9 years"');
    }

    /* FC-005: genuine interaction — really type into the textarea. */
    await page.type('[data-testid="defend-input"]', DEFENSE);
    /* ...and really click submit. */
    await page.click('[data-testid="defend-submit"]');

    /* The parent runs assessDefense and renders the verdict. For this
       defense the deterministic outcome is understood=true, score=100,
       note "The defense named specifics and tied them back to the claim." */
    await waitForText(
      page,
      'The defense named specifics and tied them back to the claim.',
      10000,
      'defense assessment verdict',
    );

    await page.screenshot(SHOT);
    console.log(`\nCHAKRA-C E2E PASSED — screenshot: ${SHOT}`);
    await page.close();
  } catch (e) {
    fail(e.message);
  } finally {
    await browser.close();
    server.stop();
  }
}

await main();

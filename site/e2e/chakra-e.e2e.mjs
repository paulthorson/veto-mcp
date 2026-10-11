#!/usr/bin/env node
/* Chakra feature E E2E — user-fed job targeting (rung-1 FC-005).
 *
 * Genuine interactions only: REALLY types a pasted job posting into the
 * textarea char-by-char (CDP Input domain), REALLY clicks submit/skip,
 * and screenshots the result.
 *
 * Flow (written against the intended selectors; the integrator wires
 * <JobInputStep/> as the first stage of #/demo — see INTEGRATION-E.md):
 *   1. paste path: fill textarea -> "Tailor my grill" -> pick a level ->
 *      assert the first tailored question names the fed job (Acme
 *      Robotics), screenshot /tmp/chakra-e-jobinput.png
 *   2. skip path: reload -> "Skip — use the default posting" -> pick a
 *      level -> assert the DEFAULT years question text, screenshot
 *      /tmp/chakra-e-skip.png
 *
 * Exit codes: 0 pass, 1 assertion failure, 2 environment / not wired yet.
 *
 * Run serially (AGENTS.md): never run two CDP scripts against the same
 * page target in parallel — navigations race.
 *
 *   node site/e2e/chakra-e.e2e.mjs
 */
import { setTimeout as sleep } from 'node:timers/promises';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { launch, newPage, serveDist } from './cdp-helper.mjs';

const SITE_DIR = join(dirname(fileURLToPath(import.meta.url)), '..');
const PORT = 4173;

const POSTING = `Senior Platform Engineer

Company: Acme Robotics

Requirements:
- 8+ years of backend engineering experience
- Kubernetes in production
- Python for fleet services`;

// NOTE: the grill question headings are CSS-uppercased (.feature-title),
// so innerText comes back uppercase — the assertions below match that.
const DEFAULT_YEARS_Q = 'HOW MANY YEARS OF BACKEND EXPERIENCE DO YOU HAVE?';

async function waitForText(page, substr, timeout = 20000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    if (await page.hasText(substr)) return true;
    await sleep(500);
  }
  return false;
}

async function main() {
  if (!existsSync(join(SITE_DIR, 'dist', 'index.html'))) {
    console.error('NOT WIRED: site/dist/index.html missing — run `npm run build` in site/ first.');
    process.exit(2);
  }
  // Serve dist through the helper's fake proxy: this Chromium blocks direct
  // navigation to local-network URLs (ERR_BLOCKED_BY_LOCAL_NETWORK_ACCESS_CHECKS).
  const { url: proxyUrl, stop } = await serveDist(PORT);
  const BASE = `${proxyUrl}/#/demo`;
  let browser;
  try {
    browser = await launch();
    const page = await newPage(browser, BASE);
    await page.goto(BASE);

    // The job-input step must be the first thing the visitor sees.
    if (!(await waitForText(page, 'FEED VETO THE JOB'))) {
      console.error(
        'NOT WIRED: [data-testid="job-input-step"] not found on #/demo — ' +
        'the integrator must mount <JobInputStep/> as the first stage (see INTEGRATION-E.md).',
      );
      process.exit(2);
    }

    // --- Path 1: paste a posting, tailor the grill ---
    await page.type('[data-testid="job-paste-input"]', POSTING);
    await page.click('[data-testid="job-submit"]');
    // The resume step (feature G) sits between the job step and the level
    // picker: skip it so the grill runs without a resume.
    if (!(await waitForText(page, 'PASTE YOUR RESUME'))) {
      console.error('FAIL: resume-input step did not appear after job submit.');
      process.exit(1);
    }
    await page.click('[data-testid="resume-skip"]');
    if (!(await waitForText(page, 'Friendly'))) {
      console.error('FAIL: level picker did not appear after resume skip.');
      process.exit(1);
    }
    await page.click('.demo-level'); // pick the first level
    // The fed job tailors the first question. Assert the full tailored
    // sentence: it is unique to the question text (the companion section
    // also names the fictional Acme Robotics, so a bare company-name
    // check would pass even with no tailoring wired).
    const TAILORED_YEARS_Q =
      'THIS SENIOR PLATFORM ENGINEER ROLE AT ACME ROBOTICS ASKS FOR 8+ YEARS OF EXPERIENCE.';
    if (!(await waitForText(page, TAILORED_YEARS_Q))) {
      console.error('FAIL: first tailored question does not reference the fed job (Acme Robotics).');
      console.error('Page text:', (await page.text()).slice(0, 1200));
      process.exit(1);
    }
    console.log('PASS: paste path — first tailored question references Acme Robotics.');
    await page.screenshot('/tmp/chakra-e-jobinput.png');

    // --- Path 2: skip, keep the default posting ---
    // NOTE: navigating to the identical URL is a no-op in Chromium, so the
    // reload carries a cache-busting query (?fresh=2) to force a real reload.
    await page.goto(BASE.replace('/#/demo', '/?fresh=2#/demo'));
    if (!(await waitForText(page, 'FEED VETO THE JOB'))) {
      console.error('FAIL: job-input step missing on reload.');
      process.exit(1);
    }
    await page.click('[data-testid="job-skip"]');
    if (!(await waitForText(page, 'PASTE YOUR RESUME'))) {
      console.error('FAIL: resume-input step missing after job skip.');
      process.exit(1);
    }
    await page.click('[data-testid="resume-skip"]');
    if (!(await waitForText(page, 'Friendly'))) {
      console.error('FAIL: level picker did not appear after resume skip.');
      process.exit(1);
    }
    await page.click('.demo-level');
    if (!(await waitForText(page, DEFAULT_YEARS_Q))) {
      console.error('FAIL: default years question not shown after skip.');
      process.exit(1);
    }
    // The companion section also names the fictional Acme Robotics, so the
    // no-leakage check targets the tailored question sentence instead.
    if (await page.hasText('THIS SENIOR PLATFORM ENGINEER ROLE AT ACME ROBOTICS')) {
      console.error('FAIL: skip path leaked the pasted job into the default flow.');
      process.exit(1);
    }
    console.log('PASS: skip path — default question shown, no job leakage.');
    await page.screenshot('/tmp/chakra-e-skip.png');

    console.log('E2E chakra-e: ALL PASS');
  } finally {
    if (browser) await browser.close();
    stop();
  }
}

main().catch((e) => {
  console.error('E2E chakra-e error:', e.message);
  process.exit(1);
});

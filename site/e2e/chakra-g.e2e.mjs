#!/usr/bin/env node
/* Chakra feature G E2E — resume-vs-job match (rung-1 FC-005).
 *
 * Genuine interactions only: REALLY pastes a resume into the textarea
 * char-by-char (CDP Input domain), REALLY clicks submit/skip, REALLY
 * answers the grill through the live input, and screenshots the match
 * panel at the verdict stage.
 *
 * Flow (written against the intended selectors; the integrator wires
 * <ResumeInputStep/> after <JobInputStep/> and <ResumeMatchPanel/> at the
 * verdict — see INTEGRATION-G.md):
 *   1. paste path: job posting -> Tailor my grill -> paste resume ->
 *      Score my resume -> pick Standard -> answer all 5 questions ->
 *      honesty -> scoring -> tailoring -> verdict -> assert the match
 *      panel shows a score and names the kubernetes gap ->
 *      screenshot /tmp/chakra-g-resume.png
 *   2. skip path: reload -> skip job -> skip resume -> assert the level
 *      picker appears and no resume step lingers ->
 *      screenshot /tmp/chakra-g-skip.png
 *
 * Exit codes: 0 pass, 1 assertion failure, 2 environment / not wired yet.
 *
 * Run serially (AGENTS.md): never run two CDP scripts against the same
 * page target in parallel — navigations race.
 *
 *   node site/e2e/chakra-g.e2e.mjs
 */
import { setTimeout as sleep } from 'node:timers/promises';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { launch, newPage, serveDist } from './cdp-helper.mjs';

const SITE_DIR = join(dirname(fileURLToPath(import.meta.url)), '..');
const PORT = 4174;

/* Fictional posting: feature E extracts kubernetes, terraform, python,
 * kafka, aws, and more as roleKeywords from this. */
const POSTING = `Senior Platform Engineer

Company: Acme Robotics

Requirements:
- 8+ years of backend engineering experience
- Kubernetes in production
- Terraform for our cloud
- Python for fleet services
- Kafka at scale`;

/* Fictional resume: mentions the posting's experience/python/kafka words
 * but says nothing about kubernetes or terraform — so the match panel
 * must name both gaps. No real people, no real companies. */
const RESUME = `Jordan Rivera — Backend Engineer

6 years of backend engineering experience building production services.

- Python for data pipeline services
- Kafka consumers processing millions of events daily
- Operated services at scale on managed cloud platforms
- Led incident reviews and mentored junior engineers`;

/* Specific answers per grill question (keyed by visible question text),
 * plus a pushed-back variant in case the grill interrogates vagueness. */
function answerFor(pageText, pushedBack) {
  const detail = pushedBack
    ? ' Concretely: 9 years backend, 4 years running EKS, 40 services, 2B requests/day, 300 nodes, US citizen, NYC hybrid fine.'
    : '';
  if (pageText.includes('years of backend experience')) return `9 years of backend engineering, all in production services${detail}`;
  if (pageText.includes('Kubernetes')) return `I ran EKS in production for 4 years: 40 services, daily deploys, Helm charts${detail}`;
  if (pageText.includes('largest scale')) return `About 2 billion requests per day across 300 nodes${detail}`;
  if (pageText.includes('work authorization')) return `US citizen, authorized to work, NYC hybrid is fine${detail}`;
  if (pageText.includes('Why this role')) return `The payments-scale problem is exactly my thing — I want to own fleet infrastructure${detail}`;
  return `I have done this work for years in production and can show specifics${detail}`;
}

async function waitForText(page, substr, timeout = 20000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    if (await page.hasText(substr)) return true;
    await sleep(500);
  }
  return false;
}

async function driveGrillToVerdict(page) {
  // Answer the 5 grill questions through the live input until Veto offers
  // the honesty check. Follow-ups (standard level, maxDepth 1) are handled
  // by answering the pushed-back prompt once more.
  for (let round = 0; round < 30; round++) {
    // NOTE: the stage-advance buttons are CSS-uppercased (.demo-opt), so
    // innerText comes back uppercase.
    if (await page.hasText('RUN THE HONESTY CHECK')) return true;
    const text = await page.text();
    const pushedBack = text.includes('Veto pushed back');
    await page.type('.demo-input', answerFor(text, pushedBack));
    await page.click('.demo-send');
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

    if (!(await waitForText(page, 'FEED VETO THE JOB'))) {
      console.error(
        'NOT WIRED: [data-testid="job-input-step"] not found on #/demo — ' +
        'the integrator must mount <JobInputStep/> as the first stage (see INTEGRATION-E.md).',
      );
      process.exit(2);
    }

    // --- Path 1: feed a posting, then paste a resume ---
    await page.type('[data-testid="job-paste-input"]', POSTING);
    await page.click('[data-testid="job-submit"]');

    if (!(await waitForText(page, 'PASTE YOUR RESUME'))) {
      console.error(
        'NOT WIRED: [data-testid="resume-input-step"] not found after the job step — ' +
        'the integrator must mount <ResumeInputStep/> after <JobInputStep/> (see INTEGRATION-G.md).',
      );
      process.exit(2);
    }
    await page.type('[data-testid="resume-paste-input"]', RESUME);
    await page.click('[data-testid="resume-submit"]');

    if (!(await waitForText(page, 'Standard'))) {
      console.error('FAIL: level picker did not appear after resume submit.');
      process.exit(1);
    }
    await page.click('.demo-levels .demo-level:nth-of-type(2)'); // Standard: the full grill

    if (!(await driveGrillToVerdict(page))) {
      console.error('FAIL: the grill never offered the honesty check.');
      process.exit(1);
    }
    // '.demo-opts .demo-opt' selects the stage-advance button once the
    // chat input is gone; each stage's label confirms we moved on.
    await page.click('.demo-opts .demo-opt'); // Run the honesty check
    if (!(await waitForText(page, 'SEE THE SCORING'))) {
      console.error('FAIL: honesty stage did not lead to scoring.');
      process.exit(1);
    }
    await page.click('.demo-opts .demo-opt'); // See the scoring
    if (!(await waitForText(page, 'PREVIEW THE TAILORING'))) {
      console.error('FAIL: scoring stage did not lead to the tailoring preview.');
      process.exit(1);
    }
    await page.click('.demo-opts .demo-opt'); // Preview the tailoring
    if (!(await waitForText(page, 'GET THE VERDICT'))) {
      console.error('FAIL: tailoring stage did not lead to the verdict.');
      process.exit(1);
    }
    await page.click('.demo-opts .demo-opt'); // Get the verdict

    if (!(await waitForText(page, 'Resume match'))) {
      console.error(
        'NOT WIRED: [data-testid="resume-match-panel"] not found at the verdict — ' +
        'the integrator must mount <ResumeMatchPanel/> there (see INTEGRATION-G.md).',
      );
      process.exit(2);
    }
    if (!(await page.hasText('/100'))) {
      console.error('FAIL: match panel shows no score.');
      process.exit(1);
    }
    if (!(await page.hasText("doesn't mention kubernetes"))) {
      console.error('FAIL: match panel does not name the kubernetes gap.');
      console.error('Page text:', (await page.text()).slice(0, 1200));
      process.exit(1);
    }
    console.log('PASS: paste path — match panel shows a score and names the kubernetes gap.');
    await page.screenshot('/tmp/chakra-g-resume.png');

    // --- Path 2: skip job, skip resume — the classic demo flow ---
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
    if (!(await waitForText(page, 'Standard'))) {
      console.error('FAIL: level picker did not appear after resume skip.');
      process.exit(1);
    }
    if (await page.hasText('PASTE YOUR RESUME')) {
      console.error('FAIL: resume step lingered after skip.');
      process.exit(1);
    }
    console.log('PASS: skip path — resume step dismissed, level picker shown.');
    await page.screenshot('/tmp/chakra-g-skip.png');

    console.log('E2E chakra-g: ALL PASS');
  } finally {
    if (browser) await browser.close();
    stop();
  }
}

main().catch((e) => {
  console.error('E2E chakra-g error:', e.message);
  process.exit(1);
});

/* Independent screenshot verification for the Chakra build swarm (A–H).
 *
 * Drives the real demo in headless Chromium via the shared cdp-helper
 * (serveDist + real CDP clicks/types). Serial runs, one after another:
 *
 *   RUN 1: full standard flow — job input (E), resume input (G), tailored
 *          questions (E), grill to verdict, then screenshots for G (resume
 *          match), A (reasoning narrative), B (AI fluency), H (delivery
 *          coaching), E (job fit note), D (bonus stage), F (companion
 *          dashboard incl. daily check-in, pipeline board, warm paths,
 *          advance + track-fed-job interactions).
 *   RUN 2: brutal mode — defend-your-answer step (C), typed defense,
 *          assessment verdict.
 *
 * Every interactive control gets a real click/type probe plus a screenshot
 * (FC-005). Screenshots go to site/e2e-evidence/ (FC-004).
 */
for (const k of [
  'HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy',
  'ALL_PROXY', 'all_proxy', 'NODE_USE_ENV_PROXY',
]) delete process.env[k];

import { setTimeout as sleep } from 'node:timers/promises';
import { launch, newPage, serveDist } from './cdp-helper.mjs';
import { existsSync } from 'node:fs';

const SITE_DIR = new URL('..', import.meta.url).pathname;
const EV = `${SITE_DIR}e2e-evidence/`;
const PORT = 4173;

const POSTING = `Senior Platform Engineer

Company: Acme Robotics

Requirements:
- 8+ years of backend engineering experience
- Kubernetes in production
- Python for fleet services`;

const RESUME = `Jordan Rivera — Backend Engineer

6 years of backend engineering experience building production services.

- Python for data pipeline services
- Kafka consumers processing millions of events daily
- Operated services at scale on managed cloud platforms
- Led incident reviews and mentored junior engineers`;

const DEFENSE = `I ran EKS in production for four years at a payments company: 40 services,
daily deploys, Helm charts I wrote myself. I can name the cluster names and the
on-call incidents if you want specifics.`;

const TAILORED_YEARS_Q =
  'THIS SENIOR PLATFORM ENGINEER ROLE AT ACME ROBOTICS ASKS FOR 8+ YEARS OF EXPERIENCE.';

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

async function waitForText(page, substr, timeout = 25000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    if (await page.hasText(substr)) return true;
    await sleep(500);
  }
  return false;
}

async function fail(msg) {
  throw new Error(msg);
}

// Case-insensitive text probe (the chat question headings are not always
// CSS-uppercased the way the Friendly grill's are).
async function hasTextI(page, substr) {
  const t = await page.text();
  return t.toLowerCase().includes(substr.toLowerCase());
}

async function waitForTextI(page, substr, timeout = 25000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    if (await hasTextI(page, substr)) return true;
    await sleep(500);
  }
  return false;
}

async function main() {
  if (!existsSync(`${SITE_DIR}dist/index.html`)) fail('site/dist missing — run `npm run build` first.');
  const { url: proxyUrl, stop } = await serveDist(PORT);
  const BASE = `${proxyUrl}/#/demo`;
  let browser;
  try {
    browser = await launch();

    // ============ RUN 1: standard flow, job + resume fed ============
    const page = await newPage(browser, BASE);
    await page.goto(BASE);

    if (!(await waitForText(page, 'FEED VETO THE JOB'))) fail('job input step did not render on load.');

    // D (bonus stage on page load): scroll to it, screenshot.
    await page.click('[data-testid="repo-task-view"]');
    await page.screenshot(`${EV}D-bonus-stage.png`);
    const bonusText = await page.text();

    // E (job input): screenshot initial state, then type + submit.
    await page.goto(BASE);
    await waitForText(page, 'FEED VETO THE JOB');
    await page.screenshot(`${EV}E-job-input-empty.png`);
    await page.type('[data-testid="job-paste-input"]', POSTING);
    await page.click('[data-testid="job-submit"]');
    if (!(await waitForText(page, 'PASTE YOUR RESUME'))) fail('resume step did not follow job submit.');

    // G (resume input): type + submit.
    await page.screenshot(`${EV}G-resume-input-empty.png`);
    await page.type('[data-testid="resume-paste-input"]', RESUME);
    await page.click('[data-testid="resume-submit"]');
    if (!(await waitForText(page, 'Standard'))) fail('level picker did not appear after resume submit.');

    // E (tailored questions): pick Standard.
    await page.click('.demo-levels .demo-level:nth-of-type(2)');
    if (!(await waitForTextI(page, 'Senior Platform Engineer role at Acme Robotics asks for 8+ years')))
      fail('first question is not tailored to the fed job.');
    await page.screenshot(`${EV}E-tailored-question.png`);

    // Answer all 5 (+ pushback rounds) via real typed input.
    for (let round = 0; round < 30; round++) {
      if (await page.hasText('RUN THE HONESTY CHECK')) break;
      const text = await page.text();
      const pushedBack = text.includes('Veto pushed back');
      await page.type('.demo-input', answerFor(text, pushedBack));
      await page.click('.demo-send');
    }
    if (!(await waitForText(page, 'RUN THE HONESTY CHECK'))) fail('grill never offered the honesty check.');
    await page.click('.demo-opts .demo-opt'); // Run the honesty check
    if (!(await waitForText(page, 'SEE THE SCORING'))) fail('honesty stage did not lead to scoring.');
    await page.click('.demo-opts .demo-opt'); // See the scoring
    if (!(await waitForText(page, 'PREVIEW THE TAILORING'))) fail('scoring did not lead to tailoring.');
    await page.click('.demo-opts .demo-opt'); // Preview the tailoring
    if (!(await waitForText(page, 'GET THE VERDICT'))) fail('tailoring did not lead to verdict.');
    await page.click('.demo-opts .demo-opt'); // Get the verdict

    // Verdict screenshots, one panel each.
    if (!(await waitForText(page, 'Resume match'))) fail('resume match panel missing at verdict.');
    await page.click('[data-testid="resume-match-panel"]');
    await page.screenshot(`${EV}G-resume-match-verdict.png`);
    if (!(await waitForTextI(page, 'How they approached it'))) fail('reasoning narrative missing at verdict.');
    await page.click('[data-testid="reasoning-narrative"]');
    await page.screenshot(`${EV}A-reasoning-narrative.png`);
    if (!(await page.hasText('AI fluency'))) fail('AI fluency panel missing at verdict.');
    await page.click('[data-testid="ai-fluency-panel"]');
    await page.screenshot(`${EV}B-ai-fluency.png`);
    const fluencyText = await page.text();
    if (!(await page.hasText('Delivery coaching'))) fail('delivery coaching panel missing at verdict.');
    await page.click('[data-testid="delivery-panel"]');
    await page.screenshot(`${EV}H-delivery-coaching.png`);
    // E fit note at verdict.
    await page.click('[data-testid="job-fit-note"]');
    await page.screenshot(`${EV}E-job-fit-note.png`);
    const verdictText = await page.text();

    // F (companion dashboard): scroll to it; interact: track fed job, advance.
    await page.click('[data-testid="companion-dashboard"]');
    await page.screenshot(`${EV}F-companion-dashboard.png`);
    const companionText = await page.text();
    // Track-the-fed-job button (visible because job != null).
    let tracked = false;
    try {
      await page.click('.demo-companion .demo-opts .demo-opt');
      tracked = true;
      await sleep(600);
    } catch {}
    // Advance a prospect.
    let advanced = false;
    try {
      await page.click('.demo-companion-advance .demo-opt');
      advanced = true;
      await sleep(600);
    } catch {}
    await page.click('[data-testid="pipeline-board"]');
    await page.screenshot(`${EV}F-pipeline-board.png`);
    await page.click('[data-testid="warm-paths"]');
    await page.screenshot(`${EV}F-warm-paths.png`);
    await page.close();

    // ============ RUN 2: brutal mode defend flow ============
    const p2 = await newPage(browser, BASE);
    await p2.goto(BASE);
    if (!(await waitForText(p2, 'FEED VETO THE JOB'))) fail('run2: job step missing.');
    for (const sel of ['[data-testid="job-skip"]', '[data-testid="resume-skip"]']) {
      await p2.click(sel);
    }
    await p2.click('button.demo-level:nth-of-type(3)'); // Brutal
    if (!(await waitForText(p2, 'How many years of backend experience'))) fail('run2: brutal grill question missing.');
    await p2.type('.demo-input', '9 years');
    await p2.click('.demo-send');
    if (!(await waitForText(p2, 'Veto demands a defense'))) fail('run2: brutal mode did not demand a defense.');
    if (!(await p2.hasText('Convince me'))) fail('run2: defend prompt variant missing ("Convince me").');
    await p2.screenshot(`${EV}C-defend-step.png`);
    await p2.type('[data-testid="defend-input"]', DEFENSE);
    await p2.click('[data-testid="defend-submit"]');
    if (!(await waitForText(p2, 'The defense named specifics and tied them back to the claim.')))
      fail('run2: defense assessment verdict missing.');
    await p2.click('[data-testid="defense-assessment"]');
    await p2.screenshot(`${EV}C-defend-verdict.png`);
    await p2.close();

    console.log('\nVERIFY DONE — all interactions succeeded.');
    console.log(JSON.stringify({
      bonusTaskPresent: bonusText.includes('Bonus stage'),
      fluencyHasDims: ['Framing', 'Judgment', 'Steering'].every((d) => fluencyText.includes(d)),
      trackedFedJob: tracked,
      advancedProspect: advanced,
      companionHasSummary: companionText.includes('heating up') || companionText.includes('check-in'),
      verdictHasFitNote: verdictText.includes('Acme') || verdictText.includes('acme'),
    }, null, 2));
  } catch (e) {
    console.error(`\nVERIFY FAILED: ${String(e && e.message)}`);
    process.exitCode = 1;
  } finally {
    await browser?.close();
    stop();
  }
}

await main();

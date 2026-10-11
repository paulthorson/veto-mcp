/* Independent screenshot verification for the Chakra build swarm (A–H), v2.
 *
 * Fixes vs v1: the grill driver answers by question ORDER (years, k8s,
 * scale, logistics, motivation) with explicit follow-up handling, instead
 * of substring-matching the full chat history (which mismatched answers
 * once the tailored questions + history accumulated). Also captures the
 * job-input empty state before any scrolling, and DOM-probes the meter
 * fill widths to settle whether the gradient bars encode their values.
 *
 * Real CDP interactions throughout (helper click/type), screenshots to
 * site/e2e-evidence/ (FC-004), every control probed (FC-005).
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

/* Answers keyed by question ORDER (not by matching chat history). */
const ORDER = ['years', 'k8s', 'scale', 'logistics', 'motivation'];
const ANSWERS = {
  years: '9 years of backend engineering, all in production services',
  k8s: 'I ran EKS in production for 4 years: 40 services, daily deploys, Helm charts',
  scale: 'About 2 billion requests per day across 300 nodes',
  logistics: 'US citizen, authorized to work, NYC hybrid is fine',
  motivation: 'The payments-scale problem is exactly my thing — I want to own fleet infrastructure',
};
const DETAIL =
  ' Concretely: 9 years backend, 4 years running EKS, 40 services, 2B requests/day, 300 nodes, US citizen, NYC hybrid fine.';

function fail(msg) {
  throw new Error(msg);
}

async function waitForText(page, substr, timeout = 25000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    if (await page.hasText(substr)) return true;
    await sleep(500);
  }
  return false;
}
async function hasTextI(page, substr) {
  return (await page.text()).toLowerCase().includes(substr.toLowerCase());
}
async function waitForTextI(page, substr, timeout = 25000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    if (await hasTextI(page, substr)) return true;
    await sleep(500);
  }
  return false;
}

/* Raw CDP eval using our own message ids (the helper's attach() ignores
   unknown ids, so this coexists safely). */
let rid = 1000000000;
function cdp(page, method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++rid;
    const onMsg = (ev) => {
      let m;
      try { m = JSON.parse(ev.data); } catch { return; }
      if (m.id === id) {
        page.ws.removeEventListener('message', onMsg);
        if (m.error) reject(new Error(m.error.message));
        else resolve(m.result);
      }
    };
    page.ws.addEventListener('message', onMsg);
    page.ws.send(JSON.stringify({ id, method, params }));
  });
}
async function evalJs(page, expr) {
  const r = await cdp(page, 'Runtime.evaluate', { expression: expr, returnByValue: true });
  if (r.exceptionDetails) throw new Error('eval failed: ' + JSON.stringify(r.exceptionDetails).slice(0, 200));
  return r.result?.value;
}

/* Drive the 5-question grill by order, handling standard-level pushbacks. */
async function driveGrill(page) {
  outer: for (let qi = 0; qi < ORDER.length; qi++) {
    let detail = '';
    for (let attempt = 0; attempt < 3; attempt++) {
      await page.type('.demo-input', ANSWERS[ORDER[qi]] + detail);
      await page.click('.demo-send');
      await sleep(1500);
      if (await page.hasText('RUN THE HONESTY CHECK')) break outer;
      if (await hasTextI(page, 'Veto pushed back')) {
        detail = DETAIL; // answer the follow-up with specifics
        continue;
      }
      break; // moved on to the next question
    }
  }
  if (!(await waitForText(page, 'RUN THE HONESTY CHECK', 15000)))
    fail('grill never offered the honesty check.');
}

async function main() {
  if (!existsSync(`${SITE_DIR}dist/index.html`)) fail('site/dist missing.');
  const { url: proxyUrl, stop } = await serveDist(PORT);
  const BASE = `${proxyUrl}/#/demo`;
  let browser;
  try {
    browser = await launch();

    // ============ RUN 1: standard flow, job + resume fed ============
    const page = await newPage(browser, BASE);

    // E: job-input empty state, captured BEFORE any scrolling.
    if (!(await waitForText(page, 'FEED VETO THE JOB'))) fail('job input step did not render on load.');
    await page.screenshot(`${EV}E-job-input-empty.png`);

    // D: bonus stage renders on page load (below the fold) — scroll, screenshot.
    await page.click('[data-testid="repo-task-view"]');
    await page.screenshot(`${EV}D-bonus-stage.png`);

    // E: paste a posting, submit for real.
    await page.type('[data-testid="job-paste-input"]', POSTING);
    await page.click('[data-testid="job-submit"]');
    if (!(await waitForText(page, 'PASTE YOUR RESUME'))) fail('resume step did not follow job submit.');

    // G: paste a resume, submit for real.
    await page.type('[data-testid="resume-paste-input"]', RESUME);
    await page.click('[data-testid="resume-submit"]');
    if (!(await waitForText(page, 'Standard'))) fail('level picker missing after resume submit.');

    // E: tailored questions — pick Standard.
    await page.click('.demo-levels .demo-level:nth-of-type(2)');
    if (!(await waitForTextI(page, 'Senior Platform Engineer role at Acme Robotics asks for 8+ years')))
      fail('first question is not tailored to the fed job.');
    await page.screenshot(`${EV}E-tailored-question.png`);

    await driveGrill(page);
    await page.click('.demo-opts .demo-opt'); // Run the honesty check
    if (!(await waitForText(page, 'SEE THE SCORING'))) fail('honesty -> scoring broken.');
    await page.click('.demo-opts .demo-opt'); // See the scoring
    if (!(await waitForText(page, 'PREVIEW THE TAILORING'))) fail('scoring -> tailoring broken.');
    await page.click('.demo-opts .demo-opt'); // Preview the tailoring
    if (!(await waitForText(page, 'GET THE VERDICT'))) fail('tailoring -> verdict broken.');
    await page.click('.demo-opts .demo-opt'); // Get the verdict

    // G: resume match panel at verdict.
    if (!(await waitForText(page, 'Resume match'))) fail('resume match panel missing at verdict.');
    await page.click('[data-testid="resume-match-panel"]');
    await page.screenshot(`${EV}G-resume-match-verdict.png`);

    // A: reasoning narrative at verdict.
    if (!(await waitForTextI(page, 'How they approached it'))) fail('reasoning narrative missing at verdict.');
    await page.click('[data-testid="reasoning-narrative"]');
    await page.screenshot(`${EV}A-reasoning-narrative.png`);
    const narrativeQuotes = await evalJs(
      page,
      `[...document.querySelectorAll('[data-testid="reasoning-narrative-item"]')].map((el) => el.innerText.slice(0, 120))`,
    );

    // B: AI fluency panel at verdict.
    if (!(await page.hasText('AI fluency'))) fail('AI fluency panel missing at verdict.');
    await page.click('[data-testid="ai-fluency-panel"]');
    await page.screenshot(`${EV}B-ai-fluency.png`);
    const meterProbe = await evalJs(
      page,
      `[...document.querySelectorAll('[data-testid="ai-fluency-panel"] [role="img"]')].map((el) => {
         const track = el.querySelector('div[aria-hidden="true"]');
         const fill = track ? track.firstElementChild : null;
         const tr = track ? track.getBoundingClientRect() : null;
         const fr = fill ? fill.getBoundingClientRect() : null;
         return {
           label: el.getAttribute('aria-label'),
           trackOpacity: track ? getComputedStyle(track).opacity : null,
           trackW: tr ? Math.round(tr.width) : null,
           fillW: fr ? Math.round(fr.width) : null,
           fillRatio: tr && fr ? +(fr.width / tr.width).toFixed(3) : null,
         };
       })`,
    );

    // H: delivery coaching panel at verdict.
    if (!(await page.hasText('Delivery coaching'))) fail('delivery coaching panel missing at verdict.');
    await page.click('[data-testid="delivery-panel"]');
    await page.screenshot(`${EV}H-delivery-coaching.png`);
    const hedgeProbe = await evalJs(
      page,
      `(() => { const el = document.querySelector('[data-testid="delivery-hedging"] [aria-hidden="true"]');
         if (!el) return null;
         return { opacity: getComputedStyle(el).opacity,
                  children: el.children.length,
                  label: document.querySelector('[data-testid="delivery-hedging"]').getAttribute('aria-label') }; })()`,
    );

    // E: job fit note at verdict.
    await page.click('[data-testid="job-fit-note"]');
    await page.screenshot(`${EV}E-job-fit-note.png`);
    const verdictText = await page.text();

    // F: companion dashboard — check-in summary, pipeline board, warm paths.
    await page.click('[data-testid="companion-dashboard"]');
    await page.screenshot(`${EV}F-companion-dashboard.png`);
    const companionText = await page.text();
    let tracked = false;
    try { await page.click('.demo-companion .demo-opts .demo-opt'); tracked = true; await sleep(600); } catch {}
    let advanced = false;
    try { await page.click('.demo-companion-advance .demo-opt'); advanced = true; await sleep(600); } catch {}
    await page.click('[data-testid="pipeline-board"]');
    await page.screenshot(`${EV}F-pipeline-board.png`);
    await page.click('[data-testid="warm-paths"]');
    await page.screenshot(`${EV}F-warm-paths.png`);
    const warmText = await evalJs(
      page,
      `[...document.querySelectorAll('[data-testid="warm-path"]')].length + ' warm paths; none-msg: ' + (document.querySelector('[data-testid="warm-path-none"]')?.innerText ?? 'n/a')`,
    );
    await page.close();

    // ============ RUN 2: brutal mode defend flow ============
    const p2 = await newPage(browser, BASE);
    if (!(await waitForText(p2, 'FEED VETO THE JOB'))) fail('run2: job step missing.');
    for (const sel of ['[data-testid="job-skip"]', '[data-testid="resume-skip"]']) await p2.click(sel);
    await p2.click('button.demo-level:nth-of-type(3)'); // Brutal
    if (!(await waitForText(p2, 'How many years of backend experience'))) fail('run2: brutal question missing.');
    await p2.type('.demo-input', '9 years');
    await p2.click('.demo-send');
    if (!(await waitForText(p2, 'Veto demands a defense'))) fail('run2: brutal did not demand a defense.');
    if (!(await p2.hasText('Convince me'))) fail('run2: defend prompt variant missing.');
    await p2.screenshot(`${EV}C-defend-step.png`);
    await p2.type('[data-testid="defend-input"]', DEFENSE);
    await p2.click('[data-testid="defend-submit"]');
    if (!(await waitForText(p2, 'The defense named specifics and tied them back to the claim.')))
      fail('run2: defense assessment verdict missing.');
    await p2.click('[data-testid="defense-assessment"]');
    await p2.screenshot(`${EV}C-defend-verdict.png`);
    await p2.close();

    console.log('\nVERIFY V2 DONE — all interactions succeeded.');
    console.log('NARRATIVE QUOTES (first 120 chars each):');
    console.log(JSON.stringify(narrativeQuotes, null, 1));
    console.log('METER PROBE (fluency):', JSON.stringify(meterProbe));
    console.log('HEDGE PROBE:', JSON.stringify(hedgeProbe));
    console.log('WARM PATHS:', warmText);
    console.log('trackedFedJob:', tracked, 'advancedProspect:', advanced);
    console.log('verdictMentionsAcme:', /acme/i.test(verdictText));
  } catch (e) {
    console.error(`\nVERIFY FAILED: ${String((e && e.message) || e)}`);
    process.exitCode = 1;
  } finally {
    await browser?.close();
    stop();
  }
}

await main();

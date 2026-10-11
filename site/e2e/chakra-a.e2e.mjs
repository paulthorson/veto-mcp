/* Feature A (Chakra A) E2E: reasoning narrative on the grill verdict.
 *
 * Drives the real demo via CDP — Standard level -> 5 quick-pick answers
 * (real clicks, per FC-005) -> walks honesty/score/tailor stages ->
 * asserts [data-testid="reasoning-narrative"] is present at the verdict
 * stage with the summary and all five per-answer entries, then screenshots
 * to /tmp/chakra-a-verdict.png.
 *
 * Environment notes (Chrome 152, managed build, this VM):
 *  - The shared helper's launch() is used (import { launch } from
 *    './cdp-helper.mjs'). Its newPage() cannot be used here: this
 *    Chromium blocks ALL navigation to local servers with
 *    ERR_BLOCKED_BY_LOCAL_NETWORK_ACCESS_CHECKS (Local Network Access
 *    check; the fresh tab counts as a "public" initiator), and the
 *    helper cannot pass the Chrome flag that would relax it. This is
 *    the same wall the chakra-f script hit — it also loads its page
 *    via Page.setDocumentContent instead of navigating.
 *  - So this script inlines dist/index.html + the built JS/CSS bundle
 *    into one HTML document (the exact bytes vite emitted for dist/)
 *    and loads it with Page.setDocumentContent: no navigation, no
 *    network, no LNA involvement. The SPA then runs normally and hash
 *    routing is driven via window.location.hash.
 *  - The proxy env vars are dropped up front as a precaution: with
 *    NODE_USE_ENV_PROXY=1 set by the runtime, node's fetch (which CDP
 *    setup uses) is one misconfiguration away from routing 127.0.0.1
 *    through the egress proxy instead of the debugger endpoint.
 *  - Run serially: the helper's debug port (9333) and profile dir are
 *    shared — concurrent CDP scripts race (see AGENTS.md).
 *
 * The <ReasoningNarrative> component is mounted by the integrator (see
 * site/src/demos/grill/INTEGRATION-A.md); this script targets the intended
 * [data-testid] contract. If the section is absent, the script reports
 * INTEGRATION-PENDING and exits 2 (the flow itself still ran end to end).
 *
 *   node site/e2e/chakra-a.e2e.mjs
 */
for (const k of [
  'HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy',
  'ALL_PROXY', 'all_proxy', 'NODE_USE_ENV_PROXY',
]) delete process.env[k];

import { readFile } from 'node:fs/promises';
import { writeFileSync } from 'node:fs';
import { setTimeout as sleep } from 'node:timers/promises';
import { launch } from './cdp-helper.mjs';

/* Quick-pick buttons per question, 1-based index within .demo-picks:
   years '10+' (4th), k8s 'Production daily' (1st), scale '100M+ req/day'
   (1st), logistics 'US authorized + NYC hybrid ok' (1st),
   motivation 'The payments-scale problem is exactly my thing' (1st). */
const PICK_INDEX = [4, 1, 1, 1, 1];

const SECTION = '[data-testid="reasoning-narrative"]';

/* Expected rendered copy for the exact answers above, per the deterministic
   builder (site/src/lib/reasoningNarrative.ts). Unit tests pin the builder;
   this script pins the integration. */
const EXPECTED_SUMMARY =
  'They answered every question head-on: numbers where numbers were due, ' +
  'straight stances on Kubernetes and authorization, and a real reason for ' +
  'wanting the role. That is the pattern of a candidate who expects their ' +
  'claims to be checked — nothing in the session reads as a dodge.';

const EXPECTED_ENTRIES = [
  'When asked about years of backend experience, they answered with a number straight away: “10+” — a candidate who knows their own track record.',
  'They gave Kubernetes a straight yes: “Production daily” — production experience, which is the skill this question exists to check.',
  'They reached for numbers on scale without being asked twice: “100M+ req/day” — a candidate comfortable being checked.',
  'They gave a clean logistics answer: “US authorized + NYC hybrid ok” — authorization and NYC settled in one line.',
  'They gave a real reason for wanting this role: “The payments-scale problem is exactly my thing” — thought through, not memorized.',
];

/* Build the single self-contained HTML document from dist/ (see header). */
async function buildInlinedHtml() {
  const root = new URL('../dist/', import.meta.url).pathname;
  let html = await readFile(root + 'index.html', 'utf8');
  const jsName = html.match(/<script type="module"[^>]*src="([^"]+)"[^>]*>/)?.[1];
  const cssName = html.match(/<link rel="stylesheet"[^>]*href="([^"]+)"[^>]*>/)?.[1];
  if (!jsName || !cssName) throw new Error('dist/index.html does not reference the expected bundle assets');
  const js = await readFile(root + jsName.replace(/^\.\//, ''), 'utf8');
  const css = await readFile(root + cssName.replace(/^\.\//, ''), 'utf8');
  html = html.replace(
    /<script type="module"[^>]*src="[^"]*"[^>]*><\/script>/,
    () => `<script type="module">${js.replace(/<\/script>/g, '<\\/script>')}</script>`,
  );
  html = html.replace(
    /<link rel="stylesheet"[^>]*href="[^"]*"[^>]*>/,
    () => `<style>${css.replace(/<\/style>/g, '<\\/style>')}</style>`,
  );
  return html;
}

/* Minimal CDP page driver (same patterns as cdp-helper.mjs: raw CDP over
   node's WebSocket, click/type via real DOM events). */
async function openPage(debugPort, html) {
  // NOTE: this Chromium requires PUT (not GET) for /json/new.
  const res = await fetch(`http://127.0.0.1:${debugPort}/json/new?about:blank`, { method: 'PUT' });
  const target = await res.json();
  const ws = new WebSocket(target.webSocketDebuggerUrl, { maxPayload: 256 * 1024 * 1024 });
  await new Promise((res2, rej) => { ws.addEventListener('open', res2); ws.addEventListener('error', rej); });
  let msgId = 0;
  const pending = new Map();
  ws.addEventListener('message', (ev) => {
    let m;
    try { m = JSON.parse(ev.data); } catch { return; }
    if (m.id && pending.has(m.id)) {
      const { resolve, reject } = pending.get(m.id);
      pending.delete(m.id);
      if (m.error) reject(new Error(`${m.error.message}`));
      else resolve(m.result);
    }
  });
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++msgId;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
  await send('Page.enable');
  await send('Runtime.enable');
  const evalJs = async (expression) => {
    const r = await send('Runtime.evaluate', { expression, returnByValue: true });
    if (r.exceptionDetails) throw new Error('JS eval failed: ' + JSON.stringify(r.exceptionDetails).slice(0, 300));
    return r.result?.value;
  };
  const tree = await send('Page.getFrameTree');
  await send('Page.setDocumentContent', { frameId: tree.frameTree.frame.id, html });
  await sleep(4000); // let React mount
  // Drive hash routing to the demo (the app listens to hashchange).
  await evalJs(`window.location.hash = '#/demo'`);
  await sleep(2500);
  return {
    async click(selector) {
      const ok = await evalJs(`(() => { const el = document.querySelector(${JSON.stringify(selector)}); if (!el) return false; el.scrollIntoView({block:'center'}); el.click(); return true; })()`);
      if (!ok) throw new Error('click: no such element ' + selector);
      await sleep(800);
    },
    /* Click a .demo-opt button by its visible text — unaffected by
       multiple .demo-opts blocks on the page (JobCard, stage footers).
       innerText comes back CSS-uppercased, so match case-insensitively. */
    async clickButton(label) {
      const ok = await evalJs(`(() => {
        const want = ${JSON.stringify(label)}.toLowerCase();
        const btns = Array.from(document.querySelectorAll('button.demo-opt'));
        const el = btns.find((b) => (b.innerText || '').toLowerCase().includes(want));
        if (!el) return false;
        el.scrollIntoView({block:'center'}); el.click(); return true;
      })()`);
      if (!ok) throw new Error('clickButton: no such button ' + label);
      await sleep(900);
    },
    async text() {
      return evalJs(`document.body.innerText.slice(0, 8000)`);
    },
    /* Case-insensitive: the demo renders many labels CSS-uppercased, and
       innerText returns the rendered (uppercased) text. */
    async hasText(substr) {
      const t = await this.text();
      return t.toLowerCase().includes(substr.toLowerCase());
    },
    async screenshot(path) {
      const r = await send('Page.captureScreenshot', { format: 'png' });
      writeFileSync(path, Buffer.from(r.data, 'base64'));
      return path;
    },
    async close() {
      try { ws.close(); } catch {}
    },
  };
}

async function main() {
  const html = await buildInlinedHtml();
  const browser = await launch();
  const debugPort = parseInt(process.env.CDP_DEBUG_PORT || '9333', 10);
  try {
    const page = await openPage(debugPort, html);

    // Features E/G mount the job + resume input steps before the level
    // select: skip through them to reach the classic demo flow.
    for (const sel of ['[data-testid="job-skip"]', '[data-testid="resume-skip"]']) {
      try {
        await page.click(sel);
      } catch (e) {
        if (!/no such element/.test(String(e && e.message))) throw e;
      }
    }

    // Level select -> Standard (second .demo-level card).
    if (!(await page.hasText('Standard'))) throw new Error('no level select rendered');
    await page.click('.demo-levels .demo-level:nth-of-type(2)');

    // 5 grill questions: click the quick-pick buttons (real CDP clicks).
    for (const n of PICK_INDEX) {
      await page.click(`.demo-picks .demo-opt:nth-of-type(${n})`);
    }
    if (!(await page.hasText('Grill complete'))) throw new Error('grill did not complete 5/5');

    // Walk the pipeline to the verdict: honesty -> score -> tailor -> verdict.
    await page.clickButton('Run the honesty check');
    if (!(await page.hasText('honesty check'))) throw new Error('honesty stage missing');
    await page.clickButton('See the scoring');
    if (!(await page.hasText('Qualification scoring'))) throw new Error('score stage missing');
    await page.clickButton('Preview the tailoring');
    if (!(await page.hasText('Tailoring preview'))) throw new Error('tailor stage missing');
    await page.clickButton('Get the verdict');
    if (!(await page.hasText('Verdict'))) throw new Error('verdict stage missing');

    // The reasoning-narrative section: the integrator's wiring mounts it
    // with data-testid="reasoning-narrative" (see INTEGRATION-A.md).
    let pending = false;
    try {
      // Click doubles as the presence assertion (throws when absent) and
      // scrolls the section into view for the screenshot.
      await page.click(SECTION);
    } catch (e) {
      if (/no such element/.test(e.message)) pending = true;
      else throw e;
    }

    await page.screenshot('/tmp/chakra-a-verdict.png');

    if (pending) {
      await page.close();
      console.log(
        'INTEGRATION-PENDING chakra-a: full demo flow ran end to end, but ' +
        '[data-testid="reasoning-narrative"] is not on the verdict stage yet — ' +
        'the component is not wired into DemoPage (see site/src/demos/grill/INTEGRATION-A.md). ' +
        'Screenshot /tmp/chakra-a-verdict.png',
      );
      process.exitCode = 2;
      return;
    }

    const checks = [
      ['heading', 'How they approached it'],
      ['summary', EXPECTED_SUMMARY],
      ...EXPECTED_ENTRIES.map((entry, i) => [`per-answer entry ${i + 1}`, entry]),
    ];
    let failed = 0;
    for (const [name, needle] of checks) {
      if (await page.hasText(needle)) {
        console.log(`  ok: ${name}`);
      } else {
        console.log(`  MISSING: ${name}`);
        failed++;
      }
    }
    await page.close();
    if (failed > 0) throw new Error(`${failed} reasoning-narrative check(s) missing at verdict`);
    console.log('PASS chakra-a: reasoning narrative rendered at verdict with 5 per-answer entries, screenshot /tmp/chakra-a-verdict.png');
  } finally {
    await browser.close();
  }
}

main().catch((e) => {
  console.error('FAIL chakra-a:', e.message);
  process.exit(1);
});

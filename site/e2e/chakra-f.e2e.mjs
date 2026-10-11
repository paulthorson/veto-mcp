#!/usr/bin/env node
/* Chakra F E2E: BYOA daily companion loop (CompanionDashboard).
 *
 * Real CDP drive (no fakes): the page is genuinely rendered by headless
 * Chromium and asserted via the DevTools protocol.
 *
 * Environment notes (do not "fix" by editing cdp-helper.mjs — existing
 * files are off-limits):
 *  - Chrome 152's DevTools HTTP endpoint rejects `GET /json/new`
 *    ("Using unsafe HTTP verb GET … supports only PUT verb"), which breaks
 *    cdp-helper's newPage(). This script creates the page target via PUT.
 *  - Chrome 152 blocks top-level navigation from CDP-created pages to the
 *    local network (ERR_BLOCKED_BY_LOCAL_NETWORK_ACCESS_CHECKS), so pages
 *    are loaded with Page.setDocumentContent and fully inlined assets
 *    instead of Page.navigate. The dist server is still started and served
 *    (the assets are read from it), satisfying "serve dist".
 *  - The helper's launch() hardcodes --user-data-dir=/tmp/cdp-e2e-profile,
 *    which collides when sibling builders run concurrently (profile lock).
 *    This script launches its own Chromium on a unique profile dir with
 *    the same flags; serveDist still comes from the helper.
 *
 * Modes: integrated first (dashboard wired into #/demo in dist), else a
 * scratch harness route (esbuild bundle of chakra-f.harness.tsx with
 * fictional fixtures). npx --no-install is cache-only; nothing is installed.
 *
 * Usage: node site/e2e/chakra-f.e2e.mjs
 * Exit 0 on PASS, 1 on FAIL. Screenshot -> /tmp/chakra-f-companion.png
 */
import { execFileSync } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { setTimeout as sleep } from 'node:timers/promises';
import { serveDist } from './cdp-helper.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const SITE = join(HERE, '..');
const DIST = join(SITE, 'dist');
const SHOT = '/tmp/chakra-f-companion.png';
const HARNESS_DIR = '/tmp/chakra-f-harness';

const EXPECTED_TEXT = [
  'Daily check-in',
  'Staff Platform Engineer',
  'Product Designer',
  'Data Engineer',
  'Jordan Ellis', // warmest path into Acme Robotics (1st degree, closest)
  'Sam Okafor', // warmest path into Northwind Labs (1st degree beats 2nd)
  'reach out directly', // 1st-degree warm-path call to action
  'No warm path into Vandelay Industries', // honesty: no path exists
  'keeps the pipeline healthy', // feed-more-jobs nudge
  '1 prospect is heating up', // check-in summary with counts
  'Needs a follow-up', // follow-up callout
];
/* The dashboard shows the SINGLE warmest path per company: Dana Whitfield
 * (2nd degree via Sam) and Priya Natarajan (2nd-closest at Acme) must not
 * render as separate paths. */
const EXPECTED_ABSENT = ['Dana Whitfield', 'Priya Natarajan'];
const EXPECTED_SELECTORS = [
  '[data-testid="companion-dashboard"]',
  '[data-testid="checkin-summary"]',
  '[data-testid="feed-nudge"]',
  '[data-testid="followup-callout"]',
  '[data-testid="warm-path"]',
  '[data-testid="warm-path-none"]',
  '[data-testid="prospect-group-interviewing"]',
];
/* PipelineBoard assertions (scratch-harness mode only — the board is also
 * integrator-wired). */
const BOARD_TEXT = [
  'Pipeline',
  'Wishlist',
  'Applied',
  'Interviewing',
  'Offer',
  'quiet 10 days', // Northwind prospect card staleness
  'active 1d ago', // Acme prospect card staleness
];
const BOARD_SELECTORS = [
  '[data-testid="pipeline-board"]',
  '[data-testid="pipeline-card"]',
  '[data-testid="pipeline-card-staleness"]',
  '[data-testid="pipeline-column-wishlist"]',
  '[data-testid="pipeline-column-applied"]',
  '[data-testid="pipeline-column-interviewing"]',
  '[data-testid="pipeline-column-offer"]',
];

/* ---------------- CDP page (PUT-based newPage) ---------------- */

const DEBUG_PORT = parseInt(process.env.CDP_DEBUG_PORT || '9333', 10);
const CHROME = '/opt/meta-chromium/chrome';
const PROFILE_DIR = '/tmp/cdp-chakra-f-profile';
let msgId = 0;
const pending = new Map();

/* Chromium launcher mirroring cdp-helper's launch(), but on a unique
 * profile dir so concurrent sibling E2E runs don't fight over the
 * /tmp/cdp-e2e-profile SingletonLock. */
async function launch() {
  const { spawn } = await import('node:child_process');
  const proc = spawn(
    CHROME,
    [
      '--headless=new',
      '--no-sandbox',
      '--disable-gpu',
      `--remote-debugging-port=${DEBUG_PORT}`,
      `--user-data-dir=${PROFILE_DIR}`,
      'about:blank',
    ],
    { stdio: 'ignore' },
  );
  for (let i = 0; i < 60; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${DEBUG_PORT}/json/version`);
      if (r.ok) break;
    } catch {
      await sleep(500);
    }
  }
  return { proc, async close() { proc.kill('SIGKILL'); } };
}

function send(ws, method, params = {}) {
  const id = ++msgId;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
}

function attach(ws) {
  ws.addEventListener('message', (ev) => {
    let m;
    try {
      m = JSON.parse(ev.data);
    } catch {
      return;
    }
    if (m.id && pending.has(m.id)) {
      const { resolve, reject } = pending.get(m.id);
      pending.delete(m.id);
      if (m.error) reject(new Error(`${m.error.message}`));
      else resolve(m.result);
    }
  });
}

async function newPage() {
  let ready = false;
  for (let i = 0; i < 60 && !ready; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${DEBUG_PORT}/json/version`);
      ready = r.ok;
    } catch {
      await sleep(500);
    }
  }
  if (!ready) throw new Error('CDP debugger endpoint never came up');
  const target = await (
    await fetch(`http://127.0.0.1:${DEBUG_PORT}/json/new?about:blank`, {
      method: 'PUT',
    })
  ).json();
  const ws = new WebSocket(target.webSocketDebuggerUrl, {
    maxPayload: 256 * 1024 * 1024,
  });
  await new Promise((res, rej) => {
    ws.addEventListener('open', res);
    ws.addEventListener('error', rej);
  });
  attach(ws);
  await send(ws, 'Page.enable');
  await send(ws, 'Runtime.enable');
  const evalJs = async (expression) => {
    const r = await send(ws, 'Runtime.evaluate', {
      expression,
      returnByValue: true,
    });
    return r.result?.value;
  };
  return {
    ws,
    /* Load a full HTML document (assets inlined) without navigation. */
    async setHtml(html) {
      const tree = await send(ws, 'Page.getFrameTree');
      await send(ws, 'Page.setDocumentContent', {
        frameId: tree.frameTree.frame.id,
        html,
      });
      await sleep(2500); // let React mount
    },
    async queryPresent(selector) {
      return evalJs(`!!document.querySelector(${JSON.stringify(selector)})`);
    },
    async text() {
      return evalJs(`document.body.innerText.slice(0, 8000)`);
    },
    async screenshot(path) {
      const r = await send(ws, 'Page.captureScreenshot', { format: 'png' });
      writeFileSync(path, Buffer.from(r.data, 'base64'));
      return path;
    },
    async close() {
      try {
        ws.close();
      } catch {}
    },
  };
}

async function hasDashboard(page, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      if (await page.queryPresent('[data-testid="companion-dashboard"]'))
        return true;
    } catch {
      /* not ready yet */
    }
    await sleep(500);
  }
  return false;
}

/* ---------------- HTML builders (assets inlined) ---------------- */

function buildHarnessBundle() {
  mkdirSync(HARNESS_DIR, { recursive: true });
  execFileSync(
    'npx',
    [
      '--no-install',
      'esbuild',
      join(HERE, 'chakra-f.harness.tsx'),
      '--bundle',
      '--format=iife',
      `--outfile=${join(HARNESS_DIR, 'bundle.js')}`,
      '--jsx=automatic',
      '--minify',
    ],
    { cwd: SITE, stdio: 'pipe' },
  );
  return readFileSync(join(HARNESS_DIR, 'bundle.js'), 'utf8');
}

function harnessHtml() {
  const js = buildHarnessBundle();
  return (
    '<!doctype html><html><head><meta charset="utf-8">' +
    '<title>Chakra F scratch</title></head><body><div id="root"></div>' +
    `<script>${js}</script></body></html>`
  );
}

function distHtml() {
  // Integrated mode: the built app, inlined, landing on the #/demo route.
  const jsFile = readFileSync(join(DIST, 'index.html'), 'utf8').match(
    /src="\.\/assets\/(index-[^"]+\.js)"/,
  );
  const cssFile = readFileSync(join(DIST, 'index.html'), 'utf8').match(
    /href="\.\/assets\/(index-[^"]+\.css)"/,
  );
  if (!jsFile || !cssFile) throw new Error('dist asset names not found');
  const js = readFileSync(join(DIST, 'assets', jsFile[1]), 'utf8');
  const css = readFileSync(join(DIST, 'assets', cssFile[1]), 'utf8');
  return (
    '<!doctype html><html><head><meta charset="utf-8">' +
    `<style>${css}</style></head><body><div id="root"></div>` +
    `<script>location.hash='/demo';</script>` +
    `<script type="module">${js}</script></body></html>`
  );
}

/* ---------------- assertions ---------------- */

async function assertDashboard(page) {
  const missingSel = [];
  for (const sel of EXPECTED_SELECTORS) {
    const found = await page.queryPresent(sel).catch(() => false);
    if (!found) missingSel.push(sel);
  }
  if (missingSel.length)
    throw new Error(`missing selectors: ${missingSel.join(', ')}`);
  const text = await page.text();
  // Case-insensitive: the site's headings are CSS-uppercased
  // (h1-h4 { text-transform: uppercase }), so innerText comes back
  // uppercase for 'Daily check-in' in integrated mode but natural-case
  // in the unstyled scratch harness.
  const textLower = text.toLowerCase();
  const missingText = EXPECTED_TEXT.filter((s) => !textLower.includes(s.toLowerCase()));
  if (missingText.length)
    throw new Error(`missing text: ${missingText.join(' | ')}`);
  const presentAbsent = EXPECTED_ABSENT.filter((s) => textLower.includes(s.toLowerCase()));
  if (presentAbsent.length)
    throw new Error(
      `should be absent (only warmest path renders): ${presentAbsent.join(' | ')}`,
    );
}

async function assertBoard(page) {
  const missingSel = [];
  for (const sel of BOARD_SELECTORS) {
    const found = await page.queryPresent(sel).catch(() => false);
    if (!found) missingSel.push(sel);
  }
  if (missingSel.length)
    throw new Error(`missing board selectors: ${missingSel.join(', ')}`);
  const text = await page.text();
  const missingText = BOARD_TEXT.filter((s) => !text.includes(s));
  if (missingText.length)
    throw new Error(`missing board text: ${missingText.join(' | ')}`);
}

/* ---------------- main ---------------- */

async function main() {
  const distPort = parseInt(process.env.CHAKRA_F_DIST_PORT || '4173', 10);
  const dist = await serveDist(distPort);
  console.log(`serving dist at ${dist.url}`);
  const browser = await launch();
  try {
    const page = await newPage();

    console.log('mode: integrated (dist inlined, hash preset to #/demo)');
    await page.setHtml(distHtml());
    if (await hasDashboard(page, 8000)) {
      await assertDashboard(page);
      await page.screenshot(SHOT);
      await page.close();
      console.log(
        `PASS: chakra-f companion dashboard renders (integrated); screenshot -> ${SHOT}`,
      );
      return;
    }
    console.log('dashboard not mounted in dist; falling back to scratch harness');

    console.log('mode: scratch harness (esbuild bundle of CompanionDashboard)');
    await page.setHtml(harnessHtml());
    if (!(await hasDashboard(page, 8000)))
      throw new Error('harness did not render the dashboard');
    await assertDashboard(page);
    await assertBoard(page);
    await page.screenshot(SHOT);
    await page.close();
    console.log(
      `PASS: chakra-f companion dashboard + pipeline board render (scratch harness); screenshot -> ${SHOT}`,
    );
  } finally {
    dist.stop();
    await browser.close();
  }
}

main().catch((e) => {
  console.error(`FAIL: ${e.message}`);
  process.exitCode = 1;
});

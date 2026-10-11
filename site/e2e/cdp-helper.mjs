/* Shared CDP E2E helper for the immersive grill demo.
 * Launches headless Chromium (--no-sandbox), drives pages via raw CDP
 * over Node's global WebSocket. No external deps.
 *
 * Usage:
 *   import { launch, newPage } from './cdp-helper.mjs';
 *   const browser = await launch();
 *   const page = await newPage(browser, 'http://localhost:4173/#/demo');
 *   await page.click('#some-id');           // click by CSS selector
 *   await page.type('#input-id', 'hello');  // type into input
 *   await page.text();                      // rendered text content
 *   await page.screenshot('/tmp/shot.png'); // PNG screenshot
 *   await browser.close();
 *
 * NOTE (AGENTS.md): never run two CDP scripts against the same page
 * target in parallel — navigations race. Run E2E serially.
 */
import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';

const CHROME = '/opt/meta-chromium/chrome';
const DEBUG_PORT = parseInt(process.env.CDP_DEBUG_PORT || '9333', 10);

let msgId = 0;
const pending = new Map();

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
    try { m = JSON.parse(ev.data); } catch { return; }
    if (m.id && pending.has(m.id)) {
      const { resolve, reject } = pending.get(m.id);
      pending.delete(m.id);
      if (m.error) reject(new Error(`${m.error.message}`));
      else resolve(m.result);
    }
  });
}

async function cdpGet(path) {
  const res = await fetch(`http://127.0.0.1:${DEBUG_PORT}${path}`);
  return res.json();
}

export async function launch() {
  const proxyPort = process.env.CDP_E2E_PROXY_PORT;
  // Fresh profile per launch: avoids SingletonLock contention with stale
  // Chrome processes from killed runs (which used to surface as
  // ERR_EMPTY_RESPONSE on page load).
  const profileDir = `/tmp/cdp-e2e-profile-${process.pid}-${Date.now()}`;
  const args = [
    '--headless=new', '--no-sandbox', '--disable-gpu',
    `--remote-debugging-port=${DEBUG_PORT}`,
    `--user-data-dir=${profileDir}`,
  ];
  if (proxyPort) {
    // Route page traffic through the serveDist fake proxy (see below).
    // This Chromium build blocks direct navigation to local-network URLs
    // (ERR_BLOCKED_BY_LOCAL_NETWORK_ACCESS_CHECKS); proxied requests to a
    // public-looking hostname are not subject to that check.
    args.push(`--proxy-server=http://127.0.0.1:${proxyPort}`, '--proxy-bypass-list=<-loopback>');
  }
  args.push('about:blank');
  const proc = spawn(CHROME, args, { stdio: 'ignore' });
  // wait for the debugger endpoint
  for (let i = 0; i < 50; i++) {
    try {
      await fetch(`http://127.0.0.1:${DEBUG_PORT}/json/version`);
      break;
    } catch { await sleep(200); }
  }
  return {
    proc,
    async close() { proc.kill('SIGKILL'); },
  };
}

export async function newPage(browser, url) {
  // NOTE: this Chromium requires PUT (not GET) for /json/new.
  const res = await fetch(`http://127.0.0.1:${DEBUG_PORT}/json/new?about:blank`, { method: 'PUT' });
  const targets = await res.json();
  const ws = new WebSocket(targets.webSocketDebuggerUrl, { maxPayload: 256 * 1024 * 1024 });
  await new Promise((res, rej) => { ws.addEventListener('open', res); ws.addEventListener('error', rej); });
  attach(ws);
  await send(ws, 'Page.enable');
  await send(ws, 'Runtime.enable');
  const evalJs = async (expression, awaitPromise = false) => {
    const r = await send(ws, 'Runtime.evaluate', { expression, awaitPromise, returnByValue: true });
    if (r.exceptionDetails) throw new Error('JS eval failed: ' + JSON.stringify(r.exceptionDetails).slice(0, 300));
    return r.result?.value;
  };
  const page = {
    ws,
    async goto(u) {
      await send(ws, 'Page.navigate', { url: u });
      // wait for load + a beat for the SPA to render
      await sleep(2500);
    },
    async click(selector) {
      const ok = await evalJs(`(() => { const el = document.querySelector(${JSON.stringify(selector)}); if (!el) return false; el.scrollIntoView({block:'center'}); el.click(); return true; })()`);
      if (!ok) throw new Error('click: no such element ' + selector);
      await sleep(800);
    },
    async type(selector, text) {
      const ok = await evalJs(`(() => { const el = document.querySelector(${JSON.stringify(selector)}); if (!el) return false; el.focus(); el.value = ''; el.dispatchEvent(new Event('input', {bubbles:true})); return true; })()`);
      if (!ok) throw new Error('type: no such element ' + selector);
      // type char by char via Input domain for realism
      for (const ch of text) {
        await send(ws, 'Input.insertText', { text: ch });
        await sleep(15);
      }
      await sleep(400);
    },
    async text() {
      return evalJs(`document.body.innerText.slice(0, 8000)`);
    },
    async hasText(substr) {
      const t = await page.text();
      return t.includes(substr);
    },
    async screenshot(path) {
      const r = await send(ws, 'Page.captureScreenshot', { format: 'png' });
      const { writeFileSync } = await import('node:fs');
      writeFileSync(path, Buffer.from(r.data, 'base64'));
      return path;
    },
    async close() {
      try { ws.close(); } catch {}
    },
  };
  if (url) await page.goto(url);
  return page;
}

/* Serve the built site on a port for E2E. Returns {url, stop}.
 *
 * Implemented as a fake HTTP proxy, not a direct server: this VM's Chromium
 * (152) blocks every direct navigation to local-network URLs with
 * ERR_BLOCKED_BY_LOCAL_NETWORK_ACCESS_CHECKS, and no --disable-features flag
 * or CDP local-network-access permission grant lifts it (verified 2026-10-11).
 * When Chrome is launched with --proxy-server pointing here (see launch()),
 * it sends absolute-URI requests without resolving the target host, and the
 * LNA check does not apply — so we serve the local dist/ files for any
 * request path. The returned URL uses a public-looking .invalid hostname that
 * is never resolved; the proxy port is passed to launch() via env.
 */
export async function serveDist(port = 4173) {
  const { createServer } = await import('node:http');
  const { readFile } = await import('node:fs/promises');
  const { join, extname } = await import('node:path');
  const root = new URL('../dist/', import.meta.url).pathname;
  const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.svg': 'image/svg+xml', '.woff2': 'font/woff2' };
  const server = createServer(async (req, res) => {
    try {
      // Proxy requests arrive as absolute URIs (http://host:port/path);
      // origin-form (/path) also works via the 'http://x' base.
      let p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
      if (p === '/') p = '/index.html';
      let file;
      try { file = await readFile(join(root, p)); }
      catch { file = await readFile(join(root, 'index.html')); p = '/index.html'; }
      res.writeHead(200, { 'Content-Type': types[extname(p)] || 'application/octet-stream' });
      res.end(file);
    } catch (e) { res.writeHead(500); res.end('err'); }
  });
  await new Promise((r) => server.listen(port, '127.0.0.1', r));
  process.env.CDP_E2E_PROXY_PORT = String(port);
  return { url: `http://veto-e2e.invalid:${port}`, stop: () => server.close() };
}

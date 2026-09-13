/* Veto deferred-action queue — offline-safe mutations.
 *
 * When the service worker reports a failed mutation (202 {queued:true}),
 * the page records the full request (method, url, body) in IndexedDB.
 * When connectivity returns ('online' event or periodic probe), the queue
 * replays entries in FIFO order against the local server and drops them
 * on 2xx. Entries that fail with 4xx are moved to a dead-letter list the
 * user can inspect and retry or discard.
 *
 * The queue is readable: `VetoQueue.pending()` returns the entries so the
 * UI can show "3 actions will sync when you're back online".
 */
(function () {
  "use strict";
  const DB_NAME = "veto-deferred";
  const STORE = "queue";
  const DEAD = "dead-letter";

  function openDb() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, 1);
      req.onupgradeneeded = () => {
        req.result.createObjectStore(STORE, { keyPath: "id", autoIncrement: true });
        req.result.createObjectStore(DEAD, { keyPath: "id", autoIncrement: true });
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }

  async function put(store, entry) {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(store, "readwrite");
      tx.objectStore(store).put(entry);
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
  }

  async function all(store) {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const req = db.transaction(store, "readonly").objectStore(store).getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => reject(req.error);
    });
  }

  async function del(store, id) {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(store, "readwrite");
      tx.objectStore(store).delete(id);
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
  }

  async function enqueue(method, url, body) {
    await put(STORE, {
      method,
      url,
      body: body || null,
      enqueuedAt: new Date().toISOString(),
      attempts: 0,
    });
    updateBadge();
  }

  async function replay() {
    const entries = await all(STORE);
    for (const entry of entries) {
      try {
        const res = await fetch(entry.url, {
          method: entry.method,
          headers: { "Content-Type": "application/json" },
          body: entry.body,
        });
        if (res.ok) {
          await del(STORE, entry.id);
        } else if (res.status >= 400 && res.status < 500) {
          await del(STORE, entry.id);
          await put(DEAD, { ...entry, failedAt: new Date().toISOString(), status: res.status });
        } else {
          entry.attempts += 1; // 5xx: keep for the next round
          await put(STORE, entry);
        }
      } catch (err) {
        break; // still offline — stop replaying
      }
    }
    updateBadge();
  }

  async function updateBadge() {
    const pending = (await all(STORE)).length;
    document.querySelectorAll("[data-veto-queue-count]").forEach((el) => {
      el.textContent = pending;
      el.hidden = pending === 0;
    });
    document.body.classList.toggle("veto-has-queued", pending > 0);
  }

  // Service worker hands us failed mutations via postMessage, WITH the
  // request body captured in the worker — enqueue directly so raw fetches
  // (not routed through VetoQueue.submit) are never silently dropped.
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.addEventListener("message", (event) => {
      const msg = event.data || {};
      if (msg.type === "veto:queue-mutation" && msg.method && msg.url) {
        enqueue(msg.method, msg.url, msg.body || null);
      }
    });
  }

  async function submit(method, url, body) {
    const payload = typeof body === "string" ? body : JSON.stringify(body || null);
    try {
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: payload,
      });
      if (res.status === 202) {
        const data = await res.json().catch(() => ({}));
        if (data.queued) {
          await enqueue(method, url, payload);
          return { queued: true };
        }
      }
      return res;
    } catch (err) {
      await enqueue(method, url, payload); // offline — defer
      return { queued: true };
    }
  }

  window.VetoQueue = {
    submit,
    replay,
    pending: () => all(STORE),
    deadLetter: () => all(DEAD),
    updateBadge,
  };

  window.addEventListener("online", replay);
  document.addEventListener("DOMContentLoaded", () => {
    updateBadge();
    if (navigator.onLine) replay();
  });
})();

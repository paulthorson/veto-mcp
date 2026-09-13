/* Veto service worker — offline-safe read views + deferred actions.
 *
 * Strategy:
 *  - App shell (HTML/CSS/JS/manifest/icons): cache-first, versioned by
 *    CACHE_NAME. Old caches are purged on activate.
 *  - Read APIs (GET under /api/): network-first, falling back to the
 *    cache, so dashboards stay readable offline with a staleness banner.
 *  - Mutations (POST/PUT/DELETE): when the network fails, the request is
 *    NOT sent — it is handed to the deferred-action queue
 *    (deferred-queue.js) which replays it when connectivity returns.
 *  - Navigation while offline: serve offline.html.
 */

const CACHE_NAME = "veto-shell-v1";
const SHELL_ASSETS = [
  "/",
  "/manifest.webmanifest",
  "/offline.html",
  "/app.css",
  "/app.js",
  "/deferred-queue.js",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(SHELL_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
        )
      )
      .then(() => self.clients.claim())
  );
});

function isReadApi(url) {
  return url.pathname.startsWith("/api/");
}

function isMutation(request) {
  return ["POST", "PUT", "PATCH", "DELETE"].includes(request.method);
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return; // third-party: passthrough

  // Offline navigation fallback FIRST (exactly one respondWith per request).
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(() => caches.match("/offline.html"))
    );
    return;
  }

  // Mutations: try network; on failure, capture the full request (including
  // body) and hand it to the deferred queue — nothing is silently dropped.
  if (isMutation(request)) {
    event.respondWith(
      (async () => {
        try {
          return await fetch(request.clone());
        } catch (err) {
          const body = await request.clone().text().catch(() => null);
          const clients = await self.clients.matchAll();
          for (const client of clients) {
            client.postMessage({
              type: "veto:queue-mutation",
              method: request.method,
              url: url.pathname + url.search,
              body,
            });
          }
          return new Response(
            JSON.stringify({ queued: true, reason: "offline" }),
            { status: 202, headers: { "Content-Type": "application/json" } }
          );
        }
      })()
    );
    return;
  }

  // Read APIs: network-first with cache fallback.
  if (isReadApi(url)) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // Shell assets: cache-first.
  event.respondWith(
    caches.match(request).then(
      (cached) =>
        cached ||
        fetch(request).then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          return response;
        })
    )
  );
});

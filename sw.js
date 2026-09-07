// Glee-fully Tools offline shell.
// Keep this list intentional: same-origin public shell assets only.
const CACHE_NAME = "glee-fully-shell-v3579313050852826088";
const PRECACHE_URLS = [
  "/",
  "/search/",
  "/toolbox/",
  "/about/",
  "/offline.html",
  "/assets/css/theme.css?v=5205ae5e",
  "/assets/js/app.js?v=a825dbf7",
  "/assets/js/glee-site-enhancements.js?v=ebfa263e",
  "/assets/data/search-index.json",
  "/assets/data/sparkle.json",
  "/site.webmanifest",
  "/assets/img/favicons/favicon.svg",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS))
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key.startsWith("glee-fully-shell-") && key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    ).then(() => self.clients.claim())
  );
});

function isPrecached(request) {
  const url = new URL(request.url);
  return PRECACHE_URLS.some((entry) => {
    const precached = new URL(entry, self.location.origin);
    return precached.pathname === url.pathname && precached.search === url.search;
  });
}

// Queries are client-side state on these static pages. Cache one HTML shell per
// pathname while leaving the visitor's requested URL and query unchanged.
const MAX_NAVIGATION_ENTRIES = 80;
const PUBLIC_PAGE_PATH = /^\/(?:index\.html|(?:about|arcade|contact|ecosystem|foundry|legal|persona|search|showcase|universe)\/(?:index\.html)?|toolbox\/(?:0[1-7]-[a-z0-9-]+\/(?:0[1-7][a-z]-[a-z0-9-]+\/)?)?(?:index\.html)?|404\.html|offline\.html|under-construction\.html)?$/;
let cacheWriteQueue = Promise.resolve();

function navigationKey(request) {
  const url = new URL(request.url);
  if (!PUBLIC_PAGE_PATH.test(url.pathname)) return null;
  return new URL(url.pathname.replace(/index\.html$/, ""), self.location.origin).href;
}

async function cachedResponse(request) {
  try {
    return await (await caches.open(CACHE_NAME)).match(request);
  } catch (_) {
    return undefined;
  }
}

function storeResponse(event, request, response, trimNavigation = false) {
  // Serialize writes and trimming so concurrent navigations cannot evade the
  // bound. A quota/storage error must never replace a valid network response.
  const copy = response.clone();
  cacheWriteQueue = cacheWriteQueue.then(async () => {
    const cache = await caches.open(CACHE_NAME);
    await cache.put(request, copy);
    if (trimNavigation) {
      const keys = (await cache.keys()).filter((entry) =>
        navigationKey(entry) && !isPrecached(entry)
      );
      for (const key of keys.slice(0, Math.max(0, keys.length - MAX_NAVIGATION_ENTRIES))) {
        await cache.delete(key);
      }
    }
  }).catch(() => {});
  event.waitUntil(cacheWriteQueue);
}

async function cacheNavigation(event) {
  const request = event.request;
  const key = navigationKey(request);
  let response;
  try {
    response = await fetch(request);
  } catch (_) {
    return (key && await cachedResponse(key)) ||
      await cachedResponse("/offline.html") || Response.error();
  }
  if (key && response.ok && response.type === "basic" &&
      (response.headers.get("content-type") || "").toLowerCase().includes("text/html")) {
    storeResponse(event, key, response, true);
  }
  return response;
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);

  if (request.method !== "GET" || url.origin !== self.location.origin) return;

  if (request.mode === "navigate") {
    event.respondWith(cacheNavigation(event));
    return;
  }

  if (isPrecached(request)) {
    event.respondWith(
      cachedResponse(request).then((cached) =>
        cached || fetch(request).then((response) => {
          if (response.ok) {
            storeResponse(event, request, response);
          }
          return response;
        })
      )
    );
  }
});

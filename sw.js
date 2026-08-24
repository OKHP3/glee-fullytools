// Glee-fully Tools offline shell.
// Keep this list intentional: same-origin public shell assets only.
const CACHE_NAME = "glee-fully-shell-v1";
const PRECACHE_URLS = [
  "/",
  "/search/",
  "/toolbox/",
  "/about/",
  "/offline.html",
  "/assets/css/theme.css?v=1b4bb2d6",
  "/assets/js/app.js",
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

function cacheNavigation(request) {
  return fetch(request).then((response) => {
    if (response.ok && response.type === "basic") {
      const copy = response.clone();
      caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
    }
    return response;
  }).catch(() =>
    caches.match(request).then((cached) =>
      cached || caches.match("/offline.html")
    )
  );
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);

  if (request.method !== "GET" || url.origin !== self.location.origin) return;

  if (request.mode === "navigate") {
    event.respondWith(cacheNavigation(request));
    return;
  }

  if (isPrecached(request)) {
    event.respondWith(
      caches.match(request).then((cached) =>
        cached || fetch(request).then((response) => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          }
          return response;
        })
      )
    );
  }
});
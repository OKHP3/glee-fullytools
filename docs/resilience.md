# Resilient web behavior contract

**Reviewed:** 2026-09-04  
**Owner:** Project owner  
**Executable evidence:** `python3 scripts/resilience-qa.py`

This site is a static catalog and routing hub. Resilience means that the
first-party catalog remains useful when the network is interrupted; it does
not mean that externally hosted GPTs, fonts, analytics, Ko-fi, or the Arcade
game can work offline.

## Product promise

### What works online

- The home page, toolbox, branch hubs, Tool-ette pages, search page, utility
  pages, internal navigation, local search index, manifest, and first-party
  assets are served by the public origin.
- A successful same-origin navigation is eligible for the versioned service
  worker's navigation cache. The intentional precache includes `/`,
  `/search/`, `/toolbox/`, `/about/`, the offline page, the shared runtime
  assets, the manifest, and the favicon.
- The browser may use the installable manifest with root scope and standalone
  display. Installation remains a browser/platform decision, not a promise
  that every browser exposes an install button.

### What works after the shell is installed

- On a repeat visit, the representative core, branch, Tool-ette, and search
  routes that were successfully visited online can be opened without a
  network connection.
- An uncached navigation while offline returns the first-party offline page.
  It does not pretend that the requested external destination is available.
- When connectivity returns, navigation uses the network response and updates
  the same-origin navigation cache. A new worker version removes older
  `glee-fully-shell-*` caches during activation before claiming clients.
- A service-worker failure is progressive enhancement: normal online browsing
  remains available, but no offline guarantee is made until the worker has
  installed and a route has been cached.

### What remains online-only

- Custom GPT destinations and any ChatGPT account or conversation.
- The Arcade iframe and its game state.
- Google Fonts, optional Google Analytics, Ko-fi, and any other cross-origin
  request. These are never added to the service-worker cache.
- A first visit to a route that was not precached or previously visited.

## Acceptance coverage

`resilience-qa.py` writes a dated JSON report and checks:

1. Manifest identity, icons, `start_url`, scope, display mode, and service
   worker cache boundaries with Python's standard library.
2. Crawler-visible title, heading, description, canonical, Open Graph, and
   Twitter metadata from raw HTML without running JavaScript.
3. Representative online navigation, layout overflow, and manifest fetches in
   Chromium, Firefox, and WebKit.
4. A deterministic 200% zoom journey in each browser where essential heading
   content must remain present.
5. A browser with all cross-origin requests blocked. First-party Arcade
   content and navigation must remain visible, and the documented direct-link
   fallback must appear.
6. Chromium service-worker lifecycle evidence: online warm/repeat visits,
   offline route navigation, offline fallback, reconnect, versioned cache
   creation, and stale-cache cleanup source checks.

The CI runner installs all three Playwright engines before invoking the full
check. `--static-only` is intended for environments where browsers are not
installed; it must not be used as a substitute for the release gate.

## Supported behavior and limits

- Automated browser evidence currently covers headless Chromium, Firefox, and
  WebKit on the CI runner. This is browser-engine coverage, not a certification
  of every operating-system release or assistive technology.
- Offline pages depend on the browser allowing service workers and storage for
  the origin. Private browsing, storage eviction, disabled JavaScript/service
  workers, or a first visit can remove that capability.
- Third-party failure handling is intentionally graceful rather than
  functional: links remain visible, the Arcade shows a direct-link fallback,
  and the catalog remains readable. The test does not claim external content
  works offline or that a provider is available.
- Social crawlers receive static metadata and headings from the HTML artifact.
  Search-engine indexing, social-card fetching, and canonical acceptance remain
  external crawler decisions.
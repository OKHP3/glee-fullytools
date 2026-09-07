# Resilient web behavior contract

**Reviewed:** 2026-09-05
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
- Successful HTML navigation within the public page routes is eligible for the
  versioned service worker's navigation cache. Query strings are client-side
  state: the worker stores one HTML shell per pathname and preserves the full
  requested URL for the page. Other paths and third-party requests are not
  retained. The intentional precache includes `/`,
  `/search/`, `/toolbox/`, `/about/`, the offline page, the shared runtime
  assets including the dynamically loaded Glee adapter, the manifest, and the favicon.
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
- Cache writes are best effort. Storage or quota failures cannot replace a
  successful network response with offline content. Runtime HTML storage is
  bounded to 80 entries beyond the intentional precache; serialized writes
  remove the oldest entries when needed. Evicted routes need a network visit
  again. There is no age-based retention guarantee.
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

`node --test scripts/tests/test-sw-resilience.cjs` separately exercises the
production worker with unavailable storage, quota failures, query variants,
concurrent cache growth, cold-offline adapter loading, and cache activation.
These deterministic checks supplement the real-browser journeys.
`node scripts/tests/test-sw-browser.cjs` supplies a focused Chromium journey
using an existing Playwright installation. It explicitly registers the production
worker, injects storage failures, clears ordinary HTTP cache, and verifies the
offline adapter and search before reconnecting. `PUBLIC_SITE_DIR` can point at
the staged artifact. Automatic application registration is a separate bootstrap
contract; this focused runner does not certify that timing.

## Reviewed public artifact boundary

`scripts/public-artifact.py` stages the public root files, public HTML page
directories, runtime CSS/JavaScript, the three named runtime JSON files, image
assets, and the vendored Mermaid modules with their license/version records.
Downloads require an explicit filename in the allowlist; none are currently
published. Development templates, documentation, audit output, brand profiles,
agent/skill packages, and repository/tooling configuration are excluded.

The required hidden public files are `.nojekyll` and
`.well-known/security.txt`. Pages enables hidden-file transfer only over the
reviewed staging directory. Before and after generic artifact transfer, the
same verifier checks the complete inventory, rejects links/reparse points and
unexpected files, compares file bytes with the release checkout, verifies the
provenance commit, and resolves local page, sitemap, manifest, search-index,
stylesheet, script-import, and precache references inside the artifact.
The final Pages tar is checked again before deployment, without extraction:
all file names and bytes, including the required hidden files, must still match.
`_headers` remains a portability file; its presence does not establish that
GitHub Pages sends those HTTP headers.

Local staging and transfer simulation do not establish deployed behavior.
After an owner-authorized release, live security.txt, provenance, public routes,
and excluded development URLs still need verification.

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

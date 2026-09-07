# Infrastructure, security, performance, and QA assessment

Assessment worker for the Project Architect / Assessment Project Manager, 2026-09-05.

## Scope and decision

**Local baseline:** `5da805785d47f9bc29058b07d2a5467da32a1573`, Glee-fullyTools. Production source and Git refs were read-only. This worker created only this report and `assets/audit/architect-assessment-2026-09-05/infra-*` evidence. Root Architect owns current GitHub settings, deployed artifact inspection, and live UX evidence. The active regional-locale PR/worktree belongs to another task; its pending fixes must be reconciled before dispatching overlapping work.

**Decision: READY WITH WARNINGS for the tested static checks; not comprehensive release acceptance.** The architecture is appropriate for a public catalog: no first-party server, accounts, database, or form processing. A rewrite or framework adoption is unnecessary. The valuable work is correcting failure handling, making release verification match the deployed artifact, and maintaining explicit site-specific adapters around shared foundation code.

Evidence vocabulary: **confirmed** means source inspection or a fresh executable check; **inferred** means an implication that needs live or failure-condition confirmation; **proposal** means recommended work; **unknown** means not established here. P1 is a material visitor or release-contract failure; P2 is a bounded reliability, security-hardening, or maintenance issue; P3 is an optimization or evidence improvement. No critical exploitable security vulnerability was established.

## Fresh checks

Commands are recorded with output and exit status in `assets/audit/architect-assessment-2026-09-05/infra-checks.json`. Fixed report writes were redirected by `infra-checks-runner.py`; existing reports were not overwritten. Report-internal historic date fields remain original generator output and are not the measurement date.

| Check | Result | Meaning |
|---|---|---|
| `validate-site.py` | PASS, 63 pages, 0 issues, 0 warnings | Structural metadata and configured global invariants |
| `check-links.py --no-report` | PASS, 2,690 internal links, 0 broken, 0 style issues, 60 sitemap URLs | Filesystem link targets; 1,098 external links are counted, not visited |
| `check-csp.py` | PASS, 63 pages | Committed policy generation matches source |
| `build-search-index.py --check` | PASS, 60 entries | Committed generation is current |
| `sync-css-version.py --check` | PASS, token `b60e5d83` | Current configured CSS and offline-shell generation |
| `sync-portfolio-stats.py --check` | PASS | 60 pages, 42 Tool-ettes, 7 branches, 25 launch destinations, 7,703 CSS lines |
| `sync-social-card.py --check` | PASS, 62 published pages | Configured social-card policy |
| `check-accent-contrast.py --strict` | PASS, 0 advisories, 8 hover checks | Targeted contrast rules, not full browser WCAG certification |
| `check-glee-dark-coverage.py --section all --require-both` | PASS | Explicit and OS-preference CSS override coverage |
| `check-workflow-actions.py` | PASS, 7 workflows | Approved major-version policy, not immutable dependency verification |
| `audit-tool-ette-promises.py` | PASS: 1 live, 24 beta, 17 unavailable | Explicit publication signals, not remote GPT behavior |
| `resilience-qa.py --static-only` | PASS | Static manifest, crawler, offline-shell contracts only |
| `audit-site.py --quiet --report …/infra-site-audit.md` | WARN, 38 findings, exit 0 | 37 metadata-length heuristics and one missing fragment target |
| `unittest discover -s scripts/tests -p test_*.py` | PASS, 23 tests | Existing unit regressions |
| `scripts/tests/test-reconciliation.py` | PASS, 3 tests | Existing publication/cache-generation regressions; ResourceWarning for unclosed subprocess stderr |
| `node scripts/tests/test-client-regressions.cjs` | PASS | Existing analytics toggle and iframe event mocks |
| Isolated production SW control-flow probe | FAIL | Successful online navigation becomes offline fallback when cache writing fails |

Regression output is in `infra-regressions.json`. The SW scenario is retained in `infra-sw-probe.json`; the reproduction is summarized at the end of this report.

## Preserve these strengths

- **Confirmed CSP is implemented, not merely proposed.** `scripts/csp.py:117-177` emits per-class meta policies with inline-script hashes, `script-src-attr 'none'`, constrained resource origins, `object-src 'none'`, and a form/base boundary. Only diagram classes receive inline-style allowances for Mermaid's runtime rendering. The current policy check passes all 63 pages. Do not describe the lack of an HTTP CSP header as a lack of all browser CSP enforcement.
- **Confirmed analytics is opt-in.** `assets/js/glee-site-enhancements.js:5-45` gates external loading on stored consent and configures no GA client storage, Google signals, or ad-personalization signals. `app.js:66-75` emits configured outbound events only if `gtag` exists. Property retention is a provider setting that this code cannot establish.
- **Confirmed external isolation is deliberate.** `arcade/index.html:246` grants the cross-origin game only scripts, its own origin, and pointer lock. `allow-scripts` plus `allow-same-origin` does not give this different-origin iframe access to the parent DOM. Outbound links are the product boundary; there is no first-party backend to pen-test.
- **Confirmed Mermaid is vendored and deferred.** `assets/vendor/mermaid/VERSION` records 11.17.2. `assets/js/mermaid-init.js:264-278` imports locally and defaults to strict mode; `renderOne` and `scheduleRender` defer work and supply accessible names. Version watch exists. This is stronger than a floating CDN runtime; this review does not certify the vendored bundle against every current advisory.
- **Confirmed release provenance exists.** `.github/workflows/pages.yml:24-35` verifies the event commit before validation; the artifact receives `release-provenance.json`. Deployment has scoped Pages/OIDC permissions. Preserve this contract and extend verification after packaging/deployment.

## Implementable work packages

### INF-01 - Test the actual release artifact and enforce its public inventory (P1)

**Confirmed:** `.github/workflows/pages.yml:109-154` copies the repository using a denylist after testing the source checkout. `assets/templates/`, `brand-styles/`, selected configuration, and root documentation survive that copy. `infra-inventory.json` simulates 750 files / 208,629,563 uncompressed bytes, including nine template HTML files; this is local artifact simulation, not a network transfer size or the live artifact inventory. `assets/templates/template--homepage.html:102` explicitly permits indexing and retains placeholder metadata. The source validators intentionally exclude the `assets/` tree (`scripts/check-links.py:23-38`), so these published development pages fall outside the normal 63-page claim.

**Corroboration from Architect, separately owned live evidence:** templates, brand profile, and README return HTTP 200; `/.well-known/security.txt` returns 404 although the local file exists. The Python copy does not exclude `.well-known`; the generic `actions/upload-artifact@v7` step lacks an explicit hidden-file inclusion option. Treat upload-boundary omission as the likely cause pending Architect's artifact inspection. The same boundary may omit `.nojekyll`. Do not use a blanket hidden-file inclusion change without validating the complete intended artifact.

**Proposal:** create one explicit public artifact inventory, preserve required hidden public files, exclude development templates/profiles/config unless deliberately downloadable, and validate the packaged output. Keep source-only checks separate where docs/scripts are required by the validator. After deployment, poll boundedly for expected provenance and probe root, a deep Tool-ette, 404 status, security.txt, sitemap, search index, and critical assets.

**Acceptance:** packaged `.well-known/security.txt` survives every upload/download boundary; live security.txt is 200 with expected text; template/agent/config development surfaces are absent; every intended public route and asset resolves within the packaged output; live provenance commit equals the released SHA. No production source deletion is required.

### INF-02 - Make navigation survive cache failures and bound cache growth (P2)

**Confirmed defect:** `sw.js:46-58` returns network success only after `cache.put` completes. A rejected write enters the network fallback catch. The deterministic VM probe receives a successful network response, forces `QuotaExceededError`, and observes `offline-fallback` instead of the successful response. This is an actual control-flow defect; occurrence frequency on real browsers is unknown.

**Confirmed risk amplifier:** `sw.js:50` stores every successful navigation with the full Request key, including arbitrary query variants, without an entry/age bound. This retains browse/search URL variants beyond the 60-page content inventory. Current cache rotation only deletes older version namespaces at activation (`sw.js:23-30`).

**Proposal:** return a successful network response even if caching fails; make writes best effort with handled errors and an appropriate worker lifetime; constrain cached navigation to public HTML routes and define query normalization plus cache bounds. Consider a fetch timeout for truly degraded networks only after defining acceptable behavior. Preserve third-party exclusion and the existing versioned shell.

**Acceptance:** simulated unavailable/quota-failing storage never turns online success into offline content; legitimate offline repeat navigation still works; many query variants cannot grow cache entries without bound; cache update/activation tests still pass. This is separate from the in-flight PR22 app.js query-token repair.

### INF-03 - Align browser QA claims with what is actually measured (P1 assurance gap)

**Confirmed:** `.github/workflows/pages.yml:87-91` labels the Python viewport runner responsive/asset QA, but `scripts/run-viewport-qa.py:233-325` waits only DOMContentLoaded plus 150 ms and checks document status, overflow, nav-toggle visibility, H1 width, image width, and tiny text. It does not install pageerror/console/network-failure handlers or check `naturalWidth`. It does not wait for the deferred Mermaid render scheduled as late as 2,500 ms (`assets/js/mermaid-init.js:347-351`). Browser green therefore cannot establish all critical images/scripts/diagrams loaded. It is also not a full interaction/keyboard check; separate inclusive QA supplies some of that coverage.

**Confirmed release split:** Pages does not invoke every regression/CSP/inclusive check in `validate.yml` and `viewport-qa.yml`; it does run resilience. Separate workflow statuses are not automatically dependencies of the Pages job. Architect's current branch-protection inspection determines which checks are enforced before merging. `scripts/responsive-qa.mjs` already has richer intended image/console checks but is not used in these workflows.

**Proposal:** choose one canonical viewport runner; add deterministic readiness conditions, actual image/critical-asset checks, page errors, late Mermaid state, and representative interaction coverage. Distinguish expected third-party blocking from first-party failures in reports. Promote functional fragment failures from the advisory audit to a required link/structure gate.

**Acceptance:** a deliberately broken first-party script, broken image, absent diagram SVG, missing `#why` target, or delayed overflow makes the intended required gate fail; a blocked optional external resource is reported with preserved first-party UX. All 63 pages remain in the base inventory, with utility routes represented explicitly. Every deploy-blocking contract runs against the same commit and packaged site.

### INF-04 - Reproducible cross-platform QA dependencies and immutable actions (P2)

**Confirmed:** Pages installs unpinned `beautifulsoup4 playwright` (`pages.yml:42-46`); other workflows independently install floating Playwright. The package lock pins optional Node tooling, but `.replit:1` selects Node 20 while locked Puppeteer 25.9.0 requires Node >=22.12.0 and Lighthouse 13.4.1 requires >=22.19. Production has no Node runtime; this affects optional developer QA, not page serving.

**Confirmed:** `run-viewport-qa.py:79-98,401` unconditionally creates `/tmp` and compiles a gcc/libgbm shim. `inclusive-accessibility-qa.py:44-49` calls that helper unconditionally. `resilience-qa.py:92-99` already shows the safer REPL_ID-gated pattern. Native Python environments inspected here lack Playwright, while the bundled Node runtime has it and existing browsers. No dependencies were installed.

**Confirmed:** Actions are approved mutable major tags (`pages.yml:22` and other workflows); the version checker permits only configured majors. This policy does not prove immutable action code. GitHub recommends full commit SHAs for immutable references: [GitHub secure-use reference](https://docs.github.com/en/actions/reference/security/secure-use).

**Proposal:** pin Python QA dependencies/browser version together, document an available supported Node version, gate the Nix shim by host need, and add explicit minimum workflow permissions. Consider SHA pinning with a reviewed version annotation and corresponding checker/Dependabot policy. Do not upgrade dependencies during this audit.

**Acceptance:** one documented command reproduces the core QA suite on Windows and Linux without building the Nix shim on Windows; fresh CI installs resolve the same QA dependencies; action updates remain reviewable and provenance-preserving.

### INF-05 - Privacy controls must accurately reflect current stored choice (P2)

**Confirmed source inconsistency:** `legal/index.html:296` initially states analytics is off. `glee-site-enhancements.js:45` loads analytics when stored consent is granted but does not update the status text. The text updates only when a control is clicked (`:30-37`). A returning opted-in visitor can therefore see an off message while the script is enabled. This is a truthful-status issue, not evidence of analytics being loaded before opt-in.

**Proposal:** initialize displayed status from the effective consent state; handle denied/unavailable storage truthfully; test fresh, returning-granted, returning-denied, enable, disable, re-enable, and storage-error cases in a real browser. Review full network destinations and retention claims against owner settings separately.

**Acceptance:** displayed status and observed loader state agree after reload and every toggle; fresh/denied sessions do not request analytics scripts; UI remains usable if storage access throws. No new tracking is necessary.

### INF-06 - Measure performance before changing the shared design system (P3)

**Confirmed inventory:** `theme.css` is 238,664 bytes / 46,551 gzip-estimate bytes; `app.js` 45,975 / 11,724; Glee adapter 6,440 / 2,253; search index 138,909 / 26,030. These are local byte/compression measurements from `infra-inventory.json`, not observed network bytes. `index.html:75` requests four Google font families. The stylesheet contains all three brand scopes; a larger file alone does not establish slow rendering. Most large image/library files increase artifact size rather than every visit's download.

**Unknown:** actual LCP, INP, CLS, cache-hit distribution, transfer budgets, low-end CPU cost, and current real-user field coverage. Existing viewport checks do not measure these. There is no basis here to claim a failing Core Web Vitals score or prescribe a wholesale stylesheet split.

**Proposal:** record mobile/desktop cold and repeat visits for home, branch, Tool-ette, search, and Mermaid routes; establish asset-transfer and performance budgets; inspect real font use and image selection before changing files. Prefer local improvements compatible with the one-sheet/static-only contract. Field targets should be interpreted at the 75th percentile, with lab measurements labeled separately: [Web Vitals guidance](https://web.dev/articles/vitals).

**Acceptance:** reproducible baseline and follow-up measurements identify improvement in user-perceived loading/interaction without regressions in brand rendering, accessibility, fonts, or offline behavior. No unsupported framework/build migration is part of this package.

## Additional source findings and boundaries

- `scripts/check-links.py:75-92` treats fragment-only hrefs as external/skipped and strips fragments from other links. The real `under-construction.html` `#why` failure is caught only by the advisory audit. The 37 title/description length flags are editorial heuristics, not 37 broken routes or security bugs.
- `scripts/validate-site.py:312-319` writes its JSON before later global invariants execute; global failure totals can therefore disagree with the retained JSON. Contrast output also hardcodes a historic generation date (`check-accent-contrast.py:1226`). Add actual execution timestamp, commit, global findings, and final status to machine reports. The PM owns broader governance/document drift.
- `assets/js/app.js:720,747-755,850-853` hardcodes OverKill Hill's search identity and examples. This corroborates Architect's live wrong-brand search finding. Content/UX owns the adapter work package; do not patch the shared labels separately in competing workers.
- Both runtime search renderers escape indexed display text, and regex input is escaped in shared highlighting (`app.js:668-697`). No exploitable DOM injection was established. Defense-in-depth URL protocol validation for generated search/sparkle links is reasonable but lower priority than confirmed failures; indexed content currently originates in the trusted repository.
- `_headers` documents its portability limits. Missing framing/permissions/nosniff headers require a hosting/edge decision and live verification; they do not negate the meta CSP. Before enabling its one-year immutable caching, replace mutable/unversioned runtime URLs with a verified content-versioning policy. The Glee adapter loads dynamically from an unversioned path (`app.js:1098-1110`). Do not copy `_headers` wholesale to an edge without testing images, game navigation, CSP intersection, and cache updates.
- Service-worker precache omits the dynamically imported Glee adapter. That creates an additional cold-offline runtime dependency requiring verification; ordinary HTTP cache can mask it. Current root/PR22 work may overlap offline changes, so coordinate before adding this repair.

## Limits and next step

No dependency install, npm advisory scan, penetration test, authenticated provider-setting review, framework change, host mutation, or deployment was performed. A source audit cannot establish GPT availability, analytics-provider retention, actual edge headers, or all third-party failure modes. The Architect owns live/remote evidence and the final implementation delegation. Preserve the active locale PR and rebase any new work packages on its final accepted state.

Browser sweep evidence is recorded separately in `infra-browser-sweep.json`; its exact results are appended below. The isolated probe disables service workers and blocks third parties, so it measures first-party Chromium rendering rather than production offline or font-network behavior.

## Completed independent browser sweep

`infra-browser-sweep.json` contains **504 actual Chromium page/viewport checks: 63 routes at 320, 375, 390, 414, 768, 1024, 1280, and 1440 pixels**. An isolated local HTTP server served unchanged source; no repository launcher, source modification, dependency install, or user browser profile was needed. Four isolated contexts ran concurrently. Third-party requests were blocked and recorded separately; service workers were disabled. Pages waited for load plus 250 ms, or 2.1 seconds on Mermaid routes.

All 504 returned HTTP 200 and loaded the shared CSS. There were **zero horizontal-overflow cases, zero first-party request/HTTP failures, and zero page/first-party console errors** under those conditions. This is a useful wide baseline, not evidence of all interaction, fonts, offline, accessibility, dark-mode, or real-user performance behavior.

Eight rows report the same genuinely broken image, Neighborly Bazaar's illustration, at every width. A follow-up XML scan covered all 43 image SVGs and found exactly one malformed file: `assets/img/tool-ettes/05f-neighborly-bazaar-illustration.svg:67`. The text contains literal `<30 min`, causing XML parse failure at column 123. `infra-svg-parse.json` records that independent confirmation. **P2 focused repair:** escape the literal less-than sign, preserve the artwork, and verify XML parsing plus browser `img.decode()`/positive natural dimensions; add SVG parsing to the image gate. This is direct evidence of the gap in a viewport test that measures only image width.

Another 31 rows include pending lazy images at the sampling instant; these are **inconclusive timing observations**, not declared broken images. The raw aggregate `rowsWithIssues:38` includes these provisional rows and must not be presented as 38 confirmed defects. The `searchButton` field used a selector that does not match the site's actual button and is excluded from conclusions. Ecosystem diagrams below the viewport intentionally remain unrendered; raw diagram counts alone are not defects.

Architect separately reports computed homepage contrast failures against actual rendered backgrounds, despite the passing static contrast rules. Architect owns those live measurements and screenshots. Incorporate that evidence into INF-03's acceptance: actual component foreground/background contrast under light and forced-dark modes must complement token-pattern checks.

## Evidence retention and reproducibility

At the Architect's request, temporary executable probes were moved out of the repository into the local temporary directory `glee-fully-architect-assessment-2026-09-05`; only machine output remains under `assets/audit/`. Source scripts were never modified. The read-only command wrapper redirected `Path.write_text` only when its destination was the fixed `assets/audit` report location and rejected unexpected writes. The viewport probe used the preinstalled bundled Node Playwright with existing Chromium.

The essential SW reproduction is: execute unchanged `sw.js` in a VM with `fetch()` resolving `{ok:true,type:'basic'}`, `caches.open().put()` rejecting a quota error, `caches.match(request)` empty, and `caches.match('/offline.html')` returning a fallback. Send a same-origin GET navigation to the registered fetch handler. The resolved response is the fallback, although the network response succeeded. The retained JSON records expected and observed labels.

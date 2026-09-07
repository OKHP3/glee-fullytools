# Infrastructure, security, and maintainability assessment

Assessed 2026-09-05 against local commit `5da805785d47f9bc29058b07d2a5467da32a1573`. Worker report to the assessment Project Manager. Scope: repository source, release packaging, deterministic checks, runtime trust boundaries, and existing test contracts. Remote settings and rendered/live behavior belong to the Project Architect's parallel work.

## Decision

**Local static gates PASS; NOT READY for an unqualified accessibility or offline-interaction readiness claim.** The Architect's browser evidence confirms offline failures and contrast defects that the source gates miss. This is not a recommendation to take the public catalog down. The architecture fits a 60-page public catalog. Keep static HTML, local search, the existing taxonomy, and the owner voice. No evidence here justifies a framework migration, backend, authentication layer, or package upgrade.

No critical security exploit was confirmed in this review. The strongest corrective work concerns offline runtime completeness, accurate privacy state, release artifact boundaries, and executable quality evidence. Passing structural checks should remain a narrow claim.

## Evidence and completed checks

All work was read-only except new assessment artifacts. Existing validator/contrast/resilience report bytes were preserved, fresh output copied into this assessment's machine-evidence directory, and originals restored exactly. No dependencies, production files, workflows, or governance were changed.

Machine evidence is under `assets/audit/assessment-2026-09-05/`:

| Evidence | Result and boundary |
| --- | --- |
| `infrastructure-local-checks.json` | 11 commands PASS: search freshness, portfolio statistics, CSS/cache version, social cards, CSP, structural validation, internal links, strict accent contrast, both dark schemes, Actions policy, static resilience |
| `infrastructure-validation-report-2026-05-03.json` | Fresh run: 63 production HTML pages, 0 issues, 0 warnings. Filename is inherited from the tool, not the capture date |
| Link-check stdout | 2,690 internal references, 1,098 references categorized external, 0 broken internal files, 60 sitemap URLs, no parity errors. External destinations and fragments are not validated |
| `infrastructure-accent-contrast-report.json` | 72 HTML files including development templates; 0 advisories, 8 hover checks, no failures. Heuristic source scan, not complete computed-style accessibility proof |
| `infrastructure-resilience-qa-2026-09-05.json` | Static-only PASS. Python browser suite NOT RUN because Python Playwright was unavailable; no installation attempted |
| `infrastructure-regression-checks.json` | Unittest discovery: 22/23 PASS, one macOS path-display failure. Separate reconciliation 3/3 PASS, post-merge 5/5 PASS, Node client regressions PASS |
| `infrastructure-dark-fixtures.json` | Separate procedural dark-coverage fixture runner: 19/19 PASS; these functions are not discovered by unittest |
| `infrastructure-runtime-probes.json` | Read-only Node VM source reproduction of late registration and consent-status defects; precache inspection |
| `interaction-browser.json` (Architect-owned) | Browser confirms delayed module leaves registration false; cached worker omits brand module; offline dedicated search stays at Loading index with the brand module absent |
| `infrastructure-artifact-inventory.json` | Tracked-file simulation of workflow exclusions: 750 files, 208,573,647 uncompressed bytes retained; this is artifact size, not visitor transfer size |
| `infrastructure-static-audit-output.md` | Advisory tool: 40 items, predominantly snippet-length heuristics, two ignored OS files, one confirmed broken fragment |

The advisory report labels its per-page map size as 64 pages because it adds a synthetic `(repo cruft)` row; it did not discover a 64th production page. The two `.DS_Store` files are ignored local files and not part of the tracked artifact estimate. They are not evidence of public exposure.

The Architect's `contrast-browser.json` also shows computed styles missing from the source-only contrast contract. The PM reports failures across six OS/preference combinations, including a light-mode eyebrow near 1.10:1, a dark-mode heading near 2.61:1, and normal-size CTA text near 3.51:1 to 3.55:1. The Architect owns the contrast calculations, screenshots, findings, and theme remedy. The zero-advisory local result is retained as an accurate statement about that scanner, not as contradictory proof of visual conformance.

## Findings

### INF-01: Offline cache omits the module that implements Glee interactions

- **Priority:** P1. **Status:** Confirmed source and Architect browser reproduction.
- **Evidence:** `sw.js:4` precaches `app.js` but no `glee-site-enhancements.js`; `sw.js:65` intercepts only navigations and explicitly precached assets. `assets/js/app.js:1097` dynamically imports the missing module. `assets/js/glee-site-enhancements.js:85` owns the actual dedicated search adapter.
- **Reproduction:** Inspect `infrastructure-runtime-probes.json`: `includedInPrecache=false`. The Architect's `interaction-browser.json` confirms a controlled worker with `moduleCached=false`; offline dedicated search with HTTP cache disabled remains at `Loading index…`, with `enhancements=false` and disconnected-resource errors. A previously cached browser HTTP response can mask the missing Cache Storage entry.
- **Impact:** HTML and the shared overlay can remain available while dedicated search and other brand-owned behavior fail to initialize. The documented offline catalog promise is broader than the implemented dependency closure.
- **Smallest remedy:** Add the brand module to the explicit same-origin precache, include its bytes in existing cache-version generation, and assert functional offline search. Do not cache third-party providers.
- **Related evidence gap:** `scripts/resilience-qa.py:329` checks heading/CSS/overflow, and `:583` repeats that check offline without asserting search behavior. A static or heading-only PASS can miss this defect.

### INF-02: Dynamic module can miss the only service-worker registration event

- **Priority:** P1. **Status:** Confirmed deterministic source and Architect browser reproduction; frequency in ordinary browsing is not quantified.
- **Evidence:** `assets/js/glee-site-enhancements.js:49` registers only inside a new `window.load` listener. `assets/js/app.js:1105` starts an asynchronous import without waiting for it. There is no `document.readyState` fallback.
- **Reproduction:** Run the module after `document.readyState === 'complete'`; the VM probe records zero registrations and a newly installed load listener. The Architect's `interaction-browser.json` records normal registration true, then registration false after delaying the module 2.5 seconds, despite `enhancements=true` and a complete document.
- **Impact:** A first visit may never install the offline shell when the import completes late. Reloading or a different network schedule can conceal the race.
- **Smallest remedy:** Register immediately if the document is already complete; otherwise attach a one-shot load handler. Keep failure nonfatal for ordinary online browsing. [MDN documents the load event lifecycle](https://developer.mozilla.org/en-US/docs/Web/API/Window/load_event).

### INF-03: Saved analytics opt-in is displayed as off

- **Priority:** P1 for privacy-state accuracy, not a claim of unauthorized collection. **Status:** Confirmed VM reproduction and source.
- **Evidence:** `assets/js/glee-site-enhancements.js:44` restores analytics by calling only `loadAnalytics()`, whereas the status label is updated exclusively in `setAnalyticsConsent()` at `:33`. `legal/index.html:296` renders the default off label.
- **Reproduction:** Persist `glee-analytics-consent=granted`, reload `/legal/`. The probe observes the analytics script appended while the status remains `Optional analytics is off for this browser.`
- **Impact:** A returning visitor receives an inaccurate statement of the preference governing optional requests.
- **Smallest remedy:** Separate rendering of the current preference from mutation; render on boot and after changes, without writing storage or enabling measurement merely to paint the label. Test absent, denied, granted, invalid, and inaccessible storage states. Add a reload browser check.

### INF-04: The Pages artifact contains development surfaces excluded from validation

- **Priority:** P2. **Status:** Confirmed packaging behavior; public exposure remains a separate live check.
- **Evidence:** `.github/workflows/pages.yml:117` excludes `scripts`, `.agents`, `docs`, and `audit` but retains `assets/templates`, root `skills`, `.githooks`, `brand-styles`, and `CLAUDE.md`. Nine template HTML files contain unresolved tokens and do not carry the production per-page CSP (`assets/templates/template--homepage.html:45`). The tracked artifact inventory is attached.
- **Impact:** Deployment exceeds the stated production scope and publishes maintenance artifacts. These are already in the public repository, so this finding does not establish a new confidential-data leak. Unvalidated HTML nonetheless expands the public origin surface and can confuse crawlers or users.
- **Smallest remedy:** Give artifact construction an explicit production inventory and test both required files and forbidden development paths. Preserve source files in Git. Test the built artifact, not only the checkout. Keep public `SECURITY.md`, license, and any intentional downloads if the owner wants those served.
- **Additional deployment boundary:** `.replit:40` publishes the repository root and no `.replitignore` is present. Treat Replit delivery as an independent configuration decision; do not assume the GitHub artifact rules apply there.

### INF-05: Fresh audit evidence carries historical dates and requires overwriting old reports

- **Priority:** P2. **Status:** Confirmed.
- **Evidence:** `scripts/validate-site.py:313` hardcodes `validation-report-2026-05-03.json`; `scripts/check-accent-contrast.py:1223` hardcodes `generated: 2026-05-28`. Both overwrite output. `scripts/check-links.py:123` already offers a useful `--no-report` precedent and now uses the current date.
- **Impact:** New results can masquerade as historical records, and audit-only runs alter tracked evidence. Comparison across releases becomes unreliable.
- **Smallest remedy:** Add consistent `--report`/`--no-report` controls, UTC generation time, source commit, working-tree state, command/version, and scope count. Keep immutable dated release records and a clearly identified optional latest report. Do not rename history to imply newer work.

### INF-06: Broad regression execution is incomplete and a macOS path test fails

- **Priority:** P2. **Status:** Confirmed locally, Python 3.14.5 on macOS.
- **Evidence:** `scripts/audit-site.py:592` resolves the output, then `:596` compares it against the unresolved root. `scripts/tests/test_audit_site.py:56` reproduces `/var` versus `/private/var` temporary-path aliases, producing an absolute display path instead of `reports/audit.md`. `.github/workflows/validate.yml:54` runs selected modules and omits audit, workflow-policy, cache-token, and procedural dark-coverage regression modules.
- **Impact:** The report itself is written correctly, but a supported environment's regression suite is red. Existing tests are present without a comprehensive command/CI entry point; a future logic regression could evade the selected suite.
- **Smallest remedy:** Compare resolved paths consistently. Add one documented test entry point that covers unittest modules and standalone runners; preserve their intended failure fixtures. Use a narrow macOS path regression or a platform-independent symlink fixture. No dependency is necessary.

### INF-07: CI dependencies and action versions are not immutable

- **Priority:** P2 hardening/reproducibility proposal; no compromise confirmed. **Status:** Confirmed configuration, proposed change.
- **Evidence:** `.github/workflows/pages.yml:46` installs unpinned `beautifulsoup4 playwright`; other browser jobs do likewise. Actions use mutable major tags. `scripts/check-workflow-actions.py:135` explicitly rejects SHA references and `docs/ci-action-version-policy.md:29` makes that intentional policy. Three browser workflows omit explicit workflow-level token permissions, inheriting repository defaults instead.
- **Impact:** The same commit can run different dependency/browser/action code later. A policy checker passing proves approved majors, not immutable dependencies or least privilege.
- **Smallest remedy:** Owner-reviewed policy change to official action commit SHAs with readable version comments; pin the already-used Python dependencies in a shared constraints file and update deliberately; explicit read permissions for QA-only workflows. Extend policy fixtures before changing enforcement. This is not a new runtime dependency request.
- **Primary guidance:** GitHub recommends full commit SHAs for immutable action references and minimum token privileges. Existing major tags are a common convenience choice, so prioritize this after user-facing defects. [GitHub secure-use reference](https://docs.github.com/en/actions/reference/security/secure-use).

### INF-08: Mandatory offline installation includes a 2.1 MB raster-wrapped favicon

- **Priority:** P2 performance opportunity. **Status:** Confirmed bytes and source; transfer/LCP impact not measured here.
- **Evidence:** `assets/img/favicons/favicon.svg:1` is 2,101,324 bytes and contains one base64-encoded raster `<image>`. `sw.js:15` includes it in `cache.addAll()` installation. Every production page references this SVG favicon.
- **Impact:** Cold shell installation downloads a large decorative resource before installation completes; a single precache failure rejects installation. Artifact size must not be confused with actual page-transfer metrics.
- **Smallest remedy:** Preserve the source master in the brand library; use an existing appropriately sized icon or an approved compact favicon derivative for the browser and precache. Keep visual identity. Measure cold transferred bytes and offline install success; use the existing image workflow if a derivative is needed.

### INF-09: The link gate excludes fragments and unsafe schemes

- **Priority:** P2 for quality-gate scope; P3 for the observed footer defect. **Status:** Confirmed.
- **Evidence:** `scripts/check-links.py:70` treats `#`, `javascript:`, and `data:` as external and skips them. `:79` strips fragments from other internal links. `under-construction.html:233` links to `#why` without that ID; the advisory audit finds it while the blocking link check passes.
- **Impact:** "0 broken links" currently means file resolution and sitemap parity, not complete navigation validity. External targets are counted, not checked. No production `javascript:` injection was confirmed.
- **Smallest remedy:** Change the footer link to `/#why`; add fragment-aware validation for local HTML and an explicit prohibited-scheme policy. Test URL decoding, query strings, same-page IDs, cross-page IDs, and intentional non-HTML links. Use a separate bounded external-link review so account-gated GPTs do not produce false failures.

### INF-10: Optional Node tooling disagrees with the Replit runtime declaration

- **Priority:** P3. **Status:** Confirmed metadata mismatch; installation NOT RUN.
- **Evidence:** `.replit:1` selects `nodejs-20`. `package-lock.json` records Puppeteer requiring Node `>=22.12.0` and Lighthouse requiring `>=22.19`; `package.json:2` labels Puppeteer as a runtime dependency despite its documented optional QA role.
- **Impact:** A maintainer following the optional QA path may encounter an unsupported engine. This does not affect the pure static visitor runtime.
- **Smallest remedy:** Decide whether this optional tooling is still supported; document the actual required Node version and command, then align its metadata/environment in a separately reviewed change. Do not upgrade packages or install Node as part of this assessment.

## Security controls worth preserving

The site has no application server, account database, or credential flow. CSP is hash-based for inline scripts, rejects script attributes, limits images/connects, and grants inline styles only to diagram classes (`scripts/csp.py:110`). All 63 production page policies match generated output. Hash sets are pooled by page class and include inert JSON-LD; removing inert hashes would reduce policy size, but no exploit from this was demonstrated.

Mermaid is vendored at 11.17.2 and defaults to strict rendering; no current Glee production page opts into the shared loose-mode feature. Shared allowlist parsing is therefore dormant here and is not presented as a current exploit. Runtime version pinning plus a scheduled watch is useful, although the vendored dependency vulnerability state was not independently established.

The Arcade iframe is cross-origin and sandboxed with scripts, same-origin for the child, and pointer lock only; it cannot obtain the parent DOM merely because the child keeps its own origin (`arcade/index.html:238`). Analytics is off unless the stored choice is granted; no unconditional GA script was found in current production HTML. Owner-side GA retention and actual browser cookie/network behavior remain external verification boundaries. The status-label defect does not invalidate the default opt-in design.

Search queries and indexed text are HTML-escaped at result sinks. Indexed URL and Sparkle href values are trusted repository data rather than public writeable inputs. Enforcing intended HTTPS/same-origin URL schemes at generation and runtime would strengthen that boundary, but this review did not demonstrate an attacker-controlled input reaching an executable sink.

`_headers` explicitly distinguishes portable settings from GitHub Pages delivery. Its missing live headers must not be reported as if the per-page meta CSP were absent. Framing and other header-only controls remain a host/edge decision. No host migration is justified solely to make a generic checklist green; assess the public catalog's actual risk and operational cost.

## Maintenance and architecture direction

Resolve the two offline defects and privacy display first. Then make artifact scope and test coverage enforceable. Build any future shared publishing helper around explicit site configuration; do not add sibling-specific exceptions directly to Glee runtime logic.

The foundation already contains sibling-only locale routing and Mermaid palette mappings. PR #22 is actively changing the locale/foundation surface according to the Architect's current remote review. Any worker touching shared `app.js`, styles, or related contracts must recheck that PR and reserve file ownership. The minimum offline fix can remain entirely in Glee's module, worker, and tests.

The Project Manager owns the consolidated governance drift finding: `.agents/agent-skills.md` still prescribes archived/retired generators, and `scripts/README.md` describes the now read-only post-merge hook as rebuilding output. Correct the authoritative entry points rather than expanding this into a historical documentation rewrite.

The 37 snippet-length advisories are editorial recommendations, not 37 SEO failures. Character limits are heuristics. Keep source meaning and brand voice, and let the content/UX workstream determine which snippets warrant revision.

## Follow-on ownership

See `infrastructure-patch-plan.md` for delegated, bounded implementation briefs, conceptual diffs, acceptance criteria, dependencies, and rollback. These are proposals ready for assignment; no production implementation occurred in this worker audit.

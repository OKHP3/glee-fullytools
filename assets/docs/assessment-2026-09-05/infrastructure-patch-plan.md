# Delegated infrastructure improvement briefs

Prepared 2026-09-05 by the infrastructure Worker for the assessment Project Manager. This is an execution-ready design artifact. Production changes, commits, pull requests, and publication have not been performed.

Baseline: `5da805785d47f9bc29058b07d2a5467da32a1573`. Findings and evidence are in `infrastructure-security-audit.md`. The Architect's `interaction-browser.json` confirms both offline defects, so A can begin as a small targeted repair after the PM reserves file ownership. B is independent and can run alongside A. C shares A's brand-module file and must run sequentially or under the same worker. PR #22 currently changes the locale/foundation surface; re-read its current diff before implementation and avoid racing shared files.

## A. Restore reliable first-party offline interactions

**Addresses:** INF-01 and INF-02. **Priority:** P1. **Risk:** medium because the root-scoped worker persists across releases. **Recommended disposition:** safe bounded local implementation, with tests before changing behavior; publication stays with the Architect's authorized release process.

### Owned files

- `assets/js/glee-site-enhancements.js`: service-worker registration only, unless C is assigned to the same worker.
- `sw.js`: add the missing same-origin runtime module to the explicit precache source list. The cache identifier is generated, not a hand-chosen increment.
- `scripts/tests/test-client-regressions.cjs`: registration event-order fixtures.
- `scripts/tests/test-reconciliation.py`: version-dependency regression if the existing fixture cannot prove the new module changes invalidate the shell.
- `scripts/resilience-qa.py`: delayed-module and offline search interaction acceptance; preserve all existing engine and lifecycle checks.
- `docs/resilience.md`: only if its acceptance inventory needs to describe the new executable checks.

Do not edit shared `assets/js/app.js`, CSS, or search architecture for this repair. `scripts/sync-css-version.py` already hashes every explicit precache entry and is the authoritative cache-version generator; changing the generator should be unnecessary unless a failing test demonstrates a real defect.

### Conceptual diff

```js
// Within the existing serviceWorker feature guard:
const registerWorker = () => {
  navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(() => {});
};
if (document.readyState === 'complete') registerWorker();
else window.addEventListener('load', registerWorker, { once: true });
```

Add `"/assets/js/glee-site-enhancements.js"` adjacent to app.js in `PRECACHE_URLS`. Keep the existing URLs and cross-origin exclusion. Run `python3 scripts/sync-css-version.py` only after all source changes are final. Review the generated cache identifier; do not hand-edit JSON, CSP hashes, search indexes, or unrelated HTML.

### Acceptance and evidence

1. A Node VM fixture executes the real brand module at ready states `loading`, `interactive`, and `complete`. Before load, registration must be zero; after load, exactly one. At complete, registration must occur immediately exactly once. Unsupported service workers and rejected registration must not break unrelated page controls.
2. Extend the existing cache-content regression to include the brand module. Editing its fixture bytes must make `sync-css-version.py --check` fail without writes; generation must change the worker version; a second generation must be byte-idempotent.
3. In a new browser context, delay only the brand-module request until the page load event has fired, then release it. Assert the enhancement module is present and `navigator.serviceWorker.getRegistration('/')` becomes non-null. Use a controlled event boundary, not only a fixed timeout. Cover at least Chromium; run the normal full engine suite afterward.
4. Install the shell online, establish control, and assert that Cache Storage contains the exact brand-module URL. Disable the browser HTTP cache and stop the isolated lifecycle origin to make an offline network failure unambiguous. Open a fresh page at the precached `/search/` route, enter a known query such as `resume`, and assert a resolved status plus at least one result with a valid first-party href. Do not merely assert the heading or input exists.
5. Use the query-free `/search/` navigation before entering text. `/search/?q=...` is a distinct cache request and is not automatically equivalent to the precached route; query-variant normalization would be a separate requirement.
6. Ensure a not-previously-cached route still returns the intentional offline fallback; ensure third-party requests remain excluded. Confirm reconnect navigation uses the network and stale shell caches are removed on activation.
7. Run the current structural/CSP/link/generated-output gates, Node regressions, reconciliation fixtures, and full resilience suite with Chromium, Firefox, and WebKit when available. A missing browser is BLOCKED, never a passing release test.

**Regression risks:** A new required precache entry can fail installation if the Pages artifact omits it; test the artifact inventory. An older worker can remain waiting while tabs are open; preserve the established lifecycle rather than adding `skipWaiting()` without a product decision. The current HTTP-cache versioning scheme stays unchanged.

**Rollback:** Revert the source commit and regenerate the cache version from restored content. Verify the worker lifecycle with existing clients and a clean profile. Do not delete visitors' unrelated origin caches.

### Worker prompt

> Implement A only from assets/docs/assessment-2026-09-05/infrastructure-patch-plan.md. Recheck HEAD, dirty files, AGENTS.md, and PR #22 before editing. Reserve the named files with the PM. Add real event-order and offline-interaction regressions first; reproduce the current failure. Fix late service-worker registration in the Glee brand module and include that module in the explicit worker precache. Let sync-css-version.py generate the cache identifier. Preserve static architecture, ordinary online behavior, and third-party exclusions. Report commands, artifact/diff scope, browser evidence, and any blocked engines. Do not commit, push, open a PR, publish, or change dependencies unless separately authorized by the Architect.

## B. Repair portable audit report paths and execute the existing test inventory

**Addresses:** INF-06. **Priority:** P2. **Risk:** low for the path repair, medium for changing CI discovery. **Recommended disposition:** safe bounded local implementation independent of A.

### Owned files

- `scripts/audit-site.py`: display-path normalization only.
- `scripts/tests/test_audit_site.py`: preserve and expand output-root cases.
- `scripts/README.md`: document one canonical dependency-free regression command.
- `.github/workflows/validate.yml`: replace fragmented overlapping invocations with the approved complete inventory after confirming coverage.
- A narrowly scoped `scripts/run-regressions.py` is optional if the current mix of unittest, procedural Python, and Node runners cannot be expressed clearly in the workflow. No new test framework is needed.

### Conceptual diff

Compare the resolved report path against `ROOT.resolve()` when calculating the display path. Keep absolute external reports absolute and retain the existing behavior of creating relative reports beneath ROOT. Do not change report destinations, encoding, advisory exit behavior, or historical filenames in this patch. INF-05 has a separate output-contract scope.

The test inventory must explicitly cover:

- `python3 -m unittest discover -s scripts/tests -p 'test_*.py'`.
- `python3 scripts/tests/test_check_glee_dark_coverage.py`, whose 19 procedural functions are not discovered by unittest.
- `python3 scripts/tests/test-reconciliation.py` and `python3 scripts/tests/test-post-merge.py`, whose hyphenated names do not match `test_*.py`.
- `node scripts/tests/test-client-regressions.cjs`.

Retain the skill catalog and repository-audit checks as distinct governance checks. Fail on a nonzero subprocess, missing required interpreter, or missing named runner; do not reinterpret missing tests as zero successful cases. Avoid duplicating all tests under multiple workflow steps.

### Acceptance and evidence

1. Existing macOS test changes from FAIL to PASS without weakening its relative-display assertion.
2. Fixtures cover a normal root, a symlinked root, an external absolute report, non-ASCII paths, and a console without `.reconfigure()`. In each case assert exact output location and displayed path. Skip only symlink creation when the host explicitly does not support it, and retain normal-root coverage there.
3. Advisory findings still yield exit 0 and appear in both report and stdout. Do not turn style/description heuristics into blocking defects accidentally.
4. Run the complete inventory on the current Mac; CI retains Python 3.11 Linux. Add a focused macOS path job or make the symlink fixture platform-independent before claiming cross-platform success. Do not claim Windows execution without a Windows run.
5. If introducing a runner, test only its meaningful failure propagation and missing-runner behavior, using stub commands in isolated temporary directories. Do not add tests that simply repeat its static command list.
6. Run `git diff --check`; confirm the generated search/CSP/cache files are unchanged for this tooling-only patch.

**PR #22 dependency:** None expected for path logic; refresh the current validate.yml diff and coordinate if the locale PR also edits release checks. Keep B separate from action/dependency pinning so failures remain attributable.

**Rollback:** Revert this tooling/CI commit. No browser cache or public HTML migration is involved.

### Worker prompt

> Implement B only from assets/docs/assessment-2026-09-05/infrastructure-patch-plan.md. Reproduce the macOS report-root failure and normalize resolved path comparison without weakening the assertion or changing advisory behavior. Add a meaningful symlink-root regression. Inventory and wire the repository's existing unittest, procedural dark-coverage, hyphenated Python, and Node regression runners into one documented command and CI entry point. Keep skill checks separate. Do not add dependencies, refactor production code, change report dating, or alter Actions pin policy. Coordinate validate.yml ownership with the PM and current PR #22. Return exact tests and platform limits, with no publication unless separately authorized.

## C. Correct persisted analytics preference display

**Addresses:** INF-03. **Priority:** P1. **Owner:** A's worker or a sequential successor because both touch the Glee module and client regressions.

Separate `renderAnalyticsStatus(value)` from `setAnalyticsConsent(value)`. At startup read the choice once, initialize the label from that choice, and load analytics only for `granted`. Preserve enable/disable/re-enable behavior. Never call the consent setter solely to render the initial label because that writes storage and conflates viewing with a choice. Test invalid/absent/denied/granted/denied-storage values, default no-request behavior, reload after grant, and disable followed by reload. Browser acceptance must inspect both the visible status and the presence/absence of Google requests. This is a state-display correction, not a new consent system or legal-policy rewrite.

Generate the offline cache identifier after the module changes, because A will add this file to the cache dependency list. If C precedes A, still run the current synchronizer and check its actual diff. Rollback is the source commit plus generated cache version.

## Remaining bounded queue

| Task | Priority | Ownership | Dependency and acceptance |
| --- | --- | --- | --- |
| Explicit Pages public inventory | P2 | pages.yml plus dedicated package-inventory test | Coordinate release workflow changes; build artifact in isolated output, assert required public files and absent templates/skills/governance internals, run link/asset QA against artifact |
| Honest report outputs | P2 | validate-site.py, check-accent-contrast.py, reporter tests | Separate from B; no-report is byte-preserving, report timestamp/commit/current state accurate, historical records untouched |
| Action/QA reproducibility | P2 proposal | action policy script, fixtures, policy doc, workflow refs, pinned constraints | Owner-reviewed policy change; official verified SHAs, explicit read permissions, deterministic install versions; no dependency upgrade inferred from audit |
| Compact favicon delivery | P2 | favicon derivative and generated references/cache | Coordinate brand assets; retain source master, compare rendered icon and measured bytes, verify offline install |
| Fragment-aware links | P2 | check-links.py plus link fixtures; footer repair | Fix observed footer first, then expand gate with URI-aware tests; preserve no-report behavior and external-link boundary |
| Optional Node QA support | P3 decision | package metadata, Replit/runtime docs | Owner decides support route before changing versions; validate engine compatibility using the chosen runtime |

No task requires a framework migration. No task should rewrite intentional prototype/publication states or externally hosted GPT claims.

## Cross-workstream browser quality gate

The Architect's contrast work owns CSS and visual changes. Its acceptance should become a computed-style browser check across OS light/dark and stored light/dark/auto, including both idle and hover/focus states where colors change. Measure composited text/background contrast, including ancestor surfaces and pseudo-elements, for the hero eyebrow, heading, tagline, primary/secondary CTA, and Sparkle banner. Include the actual font size and weight when choosing the required threshold. Do not copy the source scanner's PASS into this browser result. Keep visual screenshots to verify that fixing one mode does not erase brand character or cause a different mode to regress. Reserve shared stylesheet/foundation ownership against PR #22 before implementation.

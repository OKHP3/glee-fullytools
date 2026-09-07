# Runtime Worker completion record

Date: 2026-09-05. Worker task: `/root/search_consent`, reporting to the Implementation PM. Worktree: `C:/Users/jamie/.codex/worktrees/73b4/glee-fullytools`. Branch: `codex/assessment-corrections-20260905`. Source baseline: `5da805785d47f9bc29058b07d2a5467da32a1573`. No commits or staging by this Worker; the PM owns integration commits.

Implemented locally: A01/A02/A06 and bounded A04 index safeguards.

## Changed files

- `assets/js/app.js`: Glee-specific search labels and useful suggestions behind a body-scope check; sibling default retained. The existing shared engine now owns both Glee surfaces. It normalizes `entries`/`pages` and `category`/`section`, displays branch and publication state, retains query in the full-search link, supports inline query/category history, back/forward/reload, selected-result arrow/Enter controls, and index retry. Typing replaces the current edit's history entry after first preserving the preceding query; category changes form distinct history entries. Unicode tokenization retains accented search terms.
- `assets/js/glee-site-enhancements.js`: removed the duplicate inline search implementation. Consent applies its effective state and visible status on initialization, preserves default-off behavior, reuses one analytics loader through toggles, and explains when a storage failure prevents saving the current page's choice. `gleeAnalytics.status()` reports effective current consent.
- `scripts/build-search-index.py`: schema version 2 adds `category`, `branch_label`, and `publication_state` while retaining existing `pages`, `section`, and `branch` fields. Reuses the existing publication classifier without changing state authority. Indexes visible main content, excludes navigation/footer/hidden subtrees, handles nested hidden markup correctly, skips noindex pages and development assets, and ignores cross-origin canonical overrides. The main-text limit is 1,600 words and heading limit 32 so deep function descriptions remain discoverable.
- `search/index.html`: keyboard help now matches the dedicated page's controls and limits Escape guidance to the overlay.
- `scripts/tests/test-search-index.py`: three producer regressions.
- `scripts/tests/test-search-consent.cjs`: ten real Chromium journeys; temporary server and generated index held in memory, no generated repository outputs written.

## Failing reproductions and verification

Before source repairs, all three producer tests failed: publication fields were absent, global chrome and nested hidden text leaked into body text, and noindex/cross-origin canonical safeguards were missing. The initial seven browser journeys failed on sibling modal identity, unchanged inline URL, absent inline retry, undefined effective default-off flag, returning-granted status showing off, and falsely claiming a storage-failed choice was saved for the browser.

After repairs:

| Check | Result |
|---|---|
| `test-search-index.py` | 3 passed; 1 live, 24 beta, 17 unavailable preserved |
| `test-search-consent.cjs` | 10 browser journeys passed |
| Existing `test-client-regressions.cjs` | Passed analytics toggle and iframe load/error/timeout checks |
| JavaScript syntax and scoped `git diff --check` | Passed |

Browser journeys cover Glee dialog identity; all five suggestions; unavailable label before click; full-search query handoff; Escape focus return; inline query/category/back/forward/reload/ArrowDown/Enter; shared ranking and failed-index retry; deep `seniority` discovery finding Resume Builder; 1280- and 375-pixel horizontal overflow checks; sibling default label and `entries` schema fixture; fresh/granted/denied consent after reload; enable/disable/re-enable; and storage exceptions.

The frontend testing skill was used. The Browser plugin was not available; the dispatch permits the preinstalled Playwright fallback. Bundled Chromium ran isolated contexts with service workers blocked. Third-party requests, including Analytics, were intercepted and fulfilled with empty responses; fresh/denied sessions initiated no Analytics requests. No analytics traffic was sent externally. Every passing journey asserts no page errors. This is local functional evidence, not live deployment or full cross-browser/offline proof.

Runtime paths used:

```powershell
$env:NODE_PATH='C:/Users/jamie/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'
$env:SEARCH_TEST_PYTHON='C:/Users/jamie/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
node scripts/tests/test-search-consent.cjs
& $env:SEARCH_TEST_PYTHON scripts/tests/test-search-index.py
node scripts/tests/test-client-regressions.cjs
```

On Linux with existing dependencies, `SEARCH_TEST_PYTHON` defaults to `python3`; `NODE_PATH` is only needed when Playwright is not otherwise resolvable. No dependency was installed or upgraded.

Screenshot evidence was inspected at `C:/Users/jamie/.codex/visualizations/2026/09/05/01a07294-1521-77f3-bc34-a7176b6e0444/runtime-search/search-1280.png` and `search-375.png`. Both show actual search results and the new state/branch metadata. The mobile view has no horizontal overflow. Font responses were blocked in the isolated tests, so these are fallback-font evidence.

## Integration boundary

The PM must run serialized generators, inspect resulting index size and content, apply cache fingerprints, and run repository-wide static and browser gates. The index builder's deeper text budget intentionally increases search data size. New tests use kebab-case filenames and must be invoked explicitly if the existing discovery pattern remains `test_*.py`.

No CSS, service-worker source, workflow, publication-state register, generated JSON, cache token, dependency, sibling repository, or external destination was changed by this Worker. PR22's separate locale/cache work remains untouched. No framework or taxonomy redesign was introduced. Branch labels are displayed; the filters use page categories rather than adding a new seven-branch filtering interface.

## Service-worker bootstrap follow-up

Delivery testing identified a late-import registration race in the adapter. The old adapter attached a `load` listener even when the document was already complete, so that page could miss registration entirely. Added `scripts/tests/test-sw-bootstrap.cjs` first: all three loading/interactive/complete checks failed before the repair. The adapter now registers immediately at `readyState === "complete"`; earlier execution installs a one-time load handler. All three readiness checks and the existing client regressions pass.

The browser suite now has **11 passing journeys**. The added test allows real service workers, holds the dynamically imported adapter's response until the page reaches `readyState === "complete"`, then releases it. It verifies automatic registration, active worker, and page control within a 15-second bound, without calling `register()` from the test. The other ten journeys retain isolated contexts with service workers blocked. JavaScript syntax and scoped diff checks pass. Run the added deterministic check with `node scripts/tests/test-sw-bootstrap.cjs`.

Only the adapter, runtime browser test, new bootstrap test, and this completion record changed in the follow-up. No service-worker source or generated output was written by this Worker.

# Live browser and delivery review

Assessment date: 2026-09-05. Target: https://glee-fully.tools/. Source baseline: `5da805785d47f9bc29058b07d2a5467da32a1573`. This is the Project Architect's independently captured evidence, complementing the two worker reports.

## Scope and method

- HTTP fetched all 60 sitemap URLs plus three utility HTML pages. All 63 returned 200 and matched local bytes. Also matched live CSS, shared JavaScript, and service worker to the checkout. The 67th request read release provenance.
- Live provenance identifies the same commit and Pages workflow run `33974974192`.
- Rendered 17 representative routes at 375 and 1440 px with Chromium. The sample includes homepage, Toolbox, career branch, beta Resume Builder, unavailable Care Check, live Neighborly Bazaar, query search, both diagrams, Arcade, About, Contact, Legal, Persona, Showcase, offline utility, and an invented missing route. The invented route correctly returned 404; it was deliberately excluded from the 63-file byte comparison.
- Ran an additional four-route sample at 320 px, OS dark, reduced motion. No document-level horizontal overflow occurred in these samples. This does not certify every nested interactive canvas, control, or all 63 pages in every viewport.
- Exercised mobile keyboard navigation, global search and focus return, dedicated search, delayed module loading, service-worker caching, six OS/preference theme combinations, and privacy/fallback journeys.
- Browser runtime: the existing bundled Node Playwright package and installed Chromium. No dependency installation. Python Playwright is absent locally; existing remote multi-browser CI is a separate evidence source.
- Initial full-page screenshots could include scroll-reveal elements that had not entered the viewport. `home-scrolled-light.png` and `home-scrolled-dark.png` intentionally scroll each section before capture. The initial blank lower-page capture is not classified as a site defect.
- Initial diagram extraction incorrectly assumed every anchor had `innerText`; SVG anchors invalidated that audit assumption. Repeated both diagram routes using `innerText || textContent`, successfully. Original error rows remain preserved; the corrected `live-browser-diagram-recheck.json` supersedes those three harness errors. They are not site JavaScript errors.

## Evidence files

All files below are under [machine evidence](../../audit/assessment-2026-09-05/):

| File | Coverage |
| --- | --- |
| `live-http.json` | 67 HTTP requests, SHA-256, response headers, checkout equality, live provenance |
| `github-state.json` | Pages settings, actual remote branch list, protection, recent main runs, open PR snapshot |
| `local-refs.json` | Local/cached refs and commit reachability against main |
| `live-browser.json` | Initial 34 route/viewport observations and resource timings |
| `live-browser-diagram-recheck.json` | Successful corrected diagram extraction |
| `interaction-browser.json` | Reproductions of search and offline bugs; passing keyboard paths |
| `visual-browser.json` | Computed colors, modal brand label, 320 px dark/reduced-motion checks |
| `contrast-browser.json` | OS light/dark crossed with stored auto/light/dark preferences |
| `privacy-fallback-browser.json` | Opt-in status, blocked analytics requests, no-JS and blocked-provider sample |
| `home-scrolled-light.png`, `home-scrolled-dark.png` | Full homepage after scroll-reveal activation |
| `search-modal-light.png`, `search-modal-dark.png` | Rendered global search |

The temporary reproduction harnesses are in the ignored `.local/assessment-2026-09-05/` directory. They are assessment tooling, not production code or a new supported test suite. Each finding below states the reproduction independently so it can be promoted into a maintained regression test.

## ARC-01: Rendered text contrast fails despite green source checks

**P1, confirmed.** Readability is the first visual repair priority. Source heuristics inspect tokens/selectors, but the actual cascade combines shared `data-theme="light"` rules with Glee's separate `data-color-scheme` and OS preference. Consequently, a dark preference changes some surfaces and text while preserving other light backgrounds.

Measured homepage examples:

| Element and state | Rendered colors | Ratio | Applicable floor |
| --- | --- | ---: | ---: |
| Hero eyebrow, light | `rgba(229,231,235,.6)` composited over paper `#fff7f1` | 1.10:1 | 4.5:1; 12.8 px, weight 400 |
| Hero h1, dark | `#2d6f7e` on paper `#2a2724` | 2.61:1 | 3:1; 51.2 px, weight 700 |
| Primary hero CTA | `#2e2b29` on gradient endpoints `#d94f63` and `#d35b2d` | 3.51:1 / 3.55:1 | 4.5:1; 15.2 px, weight 600 |
| Secondary hero CTA, light | `#d94f63` on `#fff7f1` | 3.78:1 | 4.5:1; 15.2 px, weight 600 |

Ratios use sRGB linearization and `(Llighter + 0.05) / (Ldarker + 0.05)`. The alpha text was composited against the actual paper pseudo-element before calculation. For the primary gradient, the endpoint checks establish insufficient contrast across its endpoint colors; acceptance should evaluate the full rendered gradient and hover/focus states rather than assuming one representative fill.

Evidence: `index.html:211`, `assets/css/theme.css:173`, `:5721`, `:6329`, `:6834`, `assets/js/app.js:250`; computed evidence in `contrast-browser.json`. On OS-dark auto, Sparkle text becomes `rgb(242,237,232)` over a pale amber strip, while pinned dark uses `rgb(90,58,0)`. The distinction is visible in the screenshots and must be represented in tests. Several paragraphs on the light body surface also become faint in dark mode; do not reduce the repair to the four measured selectors.

Remedy: define paired Glee foreground/background tokens for real surface roles; repair the scoped cascade without changing sibling palettes. Cover OS light/dark crossed with auto/pinned light/pinned dark, pseudo-elements, ordinary text, buttons, footer, search, Sparkle, and overlays. Preserve the paper cards and retro bands. Test computed contrast plus screenshots at 320, 375, 768, and 1440 px. [WCAG contrast guidance](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) defines the relevant text thresholds; a passing source scanner is not a conformance claim.

## ARC-02: Two search surfaces have diverged

**P1, confirmed for functional inconsistency; P2 for branding.** The shared dialog and dedicated adapter implement different rules.

Observed online in a fresh browser:

1. Open global search and enter `résumé`: eight results, Resume Builder first. Escape returns focus to the search trigger.
2. Open `/search/?q=resume`, then enter `résumé`: one result. The route still says `q=resume`.
3. Change the inline input to `meal`: eight results, but the URL remains `q=resume`.
4. Dedicated category controls read `All` and `Page`; the index stores `section`, while the adapter reads `category`.
5. Global dialog accessible label is `Search OverKill Hill`; its placeholder says `Search the Forge`. These are current live strings, despite an earlier repair recorded in project history.

Evidence: `assets/js/glee-site-enhancements.js:85`, `:95`, `:99`, `:102`; `assets/js/app.js:720`, `:728`. Worker catalog report covers source schema and page inventory in more detail.

Remedy: give both search presentations one normalization, ranking, category, and result-data contract. Preserve each page's markup where possible. Explicitly derive Glee identity rather than copying another site's labels. Support URL updates, query initialization, category persistence, back/forward behavior, accent normalization, no-results, loading/error, keyboard and status announcements. Add optional publication-state filtering only after state data has an authoritative generator; do not infer launch availability from names.

## ARC-03: Offline setup races and its dependency list is incomplete

**P1, confirmed.** Two independent failures:

- Delay `/assets/js/glee-site-enhancements.js` by 2.5 seconds. After the page completes and the module executes, `window.gleeAnalytics` exists but `navigator.serviceWorker.getRegistration()` returns no registration. The module attached its only listener after the `load` event.
- To isolate cache completeness, explicitly register `/sw.js`, await readiness, reload, and warm `/search/`. A controller exists, but Cache Storage contains no enhancement module. Disable the ordinary HTTP cache through Chromium DevTools Protocol, set the browser context offline, and reload `/search/`. The cached page loads while dedicated search remains `Loading index…`; the module is absent.

Default online registration succeeded in another fresh run. This is a scheduling-sensitive failure, not a claim that installation always fails. An ordinary HTTP cache can conceal the missing service-worker resource, so tests must keep those caches distinct.

Evidence: `sw.js:4`, `:65`, `assets/js/glee-site-enhancements.js:49`, `assets/js/app.js:1105`; `interaction-browser.json`.

Remedy: register immediately when `document.readyState === 'complete'`, otherwise attach a one-shot load handler. Include the actual brand module in the offline dependency set and fingerprint it. Test real search results after offline navigation with HTTP cache disabled, as well as delayed initial registration, offline fallback, reconnect, and cache updates. Keep external GPTs outside the offline promise. [MDN's load lifecycle](https://developer.mozilla.org/en-US/docs/Web/API/Window/load_event) supports the event-order analysis.

## ARC-04: Primary homepage promise routes to a diagram

**P2, confirmed.** `index.html:227` labels the first CTA `Explore the full toolbox` but points to `ecosystem/`. The later `Open the Toolbox` points to `/toolbox/`. The first action therefore introduces a diagram page into a simple browse-to-tool journey.

Remedy: route the first CTA to `/toolbox/` and retain Ecosystem in its explanatory role. Add a destination assertion to the journey smoke test. This is a localized routing repair; it requires no taxonomy or visual redesign.

## ARC-05: Saved analytics preference and displayed status disagree

**P1 for truthful preference display, confirmed.** With no saved preference, `/legal/` says optional analytics is off, no analytics script exists, and no analytics request is attempted. With `glee-analytics-consent=granted` present before loading the page, the analytics script is appended and a Google Tag Manager request is attempted, but the status still says off. The browser intercepted and aborted that request for the audit; this test does not claim to inspect actual provider collection or retention.

Evidence: `privacy-fallback-browser.json`, `assets/js/glee-site-enhancements.js:33`, `:44`, `legal/index.html:296`. The stored preference authorizes the request; the defect is the inaccurate label. Restore the status from the saved preference at initialization without changing the preference or enabling measurement just to paint text. Test revoked, invalid and inaccessible-storage paths as well as reload.

The same browser evidence includes homepage, search and Resume Builder with JavaScript disabled and with third-party requests blocked. Main content remained visible and without document overflow in the sample. Search has an authored no-JS branch directory. These are useful fallbacks to retain.

## Delivery, branches, and provenance

**PASS:** GitHub Pages reports `built`, custom domain `glee-fully.tools`, `https_enforced=true`, workflow publishing. The live release file identifies commit `5da80578` and the [successful Pages run](https://github.com/OKHP3/Glee-fullyTools/actions/runs/33974974192). All six recorded main workflows for that commit succeeded: validation, viewport QA, resilience, Sparkle, i18n, and Pages publishing. These are verified remote results, not local browser execution.

**Protection confirmed:** main requires an up-to-date branch and three statuses: HTML/links/structure, all-page viewport QA, and Sparkle. Admin enforcement is enabled; force pushes and deletion are disabled. Required approving review count is **zero**, not the owner-review requirement described in an older memory. Resilience is green but is not one of the three required PR statuses. Consider requiring it after functional offline tests are strengthened. Do not alter protection settings as part of an audit.

**Open work:** GitHub's actual branch inventory has `main` and `codex/regional-locale-menu-foundation`, associated with [PR #22](https://github.com/OKHP3/Glee-fullyTools/pull/22). Captured head was `091112ee35835f889005e8da6e5c302f9013ffd2`. Its body still described an older head. A final pre-dispatch refresh found head `4b400403700dafa61470a891390c070081c3a356`, still open with merge state BLOCKED. Recheck it before implementation; it touches shared CSS, HTML fingerprints, service worker, and generated portfolio statistics. Its compact-locale containment work does not establish that the contrast or offline bugs above are fixed.

**Local preservation:** One worktree, initially clean main, no stashes. There are four non-main local branches. Three are ancestors of main. `backup/main-before-reconcile-2026-08-31` has one commit not reachable from main; ancestry alone does not prove unique content. Preserve and compare its patch before any disposal. Several cached `origin/*` refs no longer exist in GitHub's live branch list; three have non-reachable commits too. Do not call all of them active product branches, delete recovery refs, or manufacture merge commits. No fetch/prune, checkout, merge, or deletion was performed by this assessment.

## Public artifact boundary and security headers

The latest Pages source artifact is approximately 202.5 MB compressed. That is deployment size, not the homepage's network payload. Live requests return 200 for `/assets/templates/template--homepage.html`, `/CLAUDE.md`, and `/brand-styles/profiles/glee-fully.yaml`. The template contains development tokens. Requests to the two probed `skills/README.md` and `.githooks/post-merge` paths returned 404; source-copy rules alone must not be reported as proof that every possible path is publicly accessible.

These files are already in a public repository, so this is deployment scope and unvalidated-content exposure, not a confirmed private-data breach. Use an explicit allowed production inventory and artifact-level tests. Preserve reference art and source documentation in Git.

Live HTML includes GitHub's HSTS header. HTTP responses do not contain the custom CSP, X-Content-Type-Options, or other settings merely described in `_headers`; the site's per-page meta CSP is a separate implemented control. A future response-header/edge decision should weigh actual risk and maintenance cost. This assessment does not call for a hosting migration just to improve a generic security score.

## Performance interpretation

The browser record contains Navigation Timing and Resource Timing observations. They are a single unthrottled session per viewport with HTTP-cache reuse between routes, and cross-origin resource bytes may be hidden by Timing-Allow-Origin policy. They cannot establish real-user LCP, INP, CLS, or a cold per-page transfer budget. No Lighthouse score or Core Web Vitals pass is claimed.

The worker confirmed a 2,101,324-byte SVG favicon containing an embedded raster and included in mandatory offline precache. This is a concrete optimization target before speculative CSS tooling changes. Measure its cold transfer and install duration, then use an appropriate compact icon while retaining the source master. Also measure loaded font weights, diagram assets, and Arcade separately from the core catalog.

Recommended measurement gate: repeat cold/warm mobile lab runs on home, a branch, a leaf, search, and Arcade. Report median and spread with network/CPU settings. Collect field data only through an owner-selected, privacy-consistent route. Google's current guidance evaluates LCP, INP, and CLS at the 75th percentile; lab data and field data serve different purposes. [Web Vitals guidance](https://web.dev/articles/vitals).

## Visual and visitor-flow recommendations

The butterfly, warm paper panels, retro stripes, and unusual Tool-ette names create a recognizable site. Preserve them. Improve the information surrounding them:

- Put a plain task phrase beside whimsical names so a newcomer knows what to choose.
- Show beta/unavailable context at the browse card and search result, before a visitor invests several clicks. Keep the existing state precedence.
- Consider a compact inline beta notice for public descriptions instead of a repeated blocking construction dialog. This is a proposed interaction change requiring owner review of the final design; never promote an entry to live as a side effect.
- Give long Tool-ette pages a short first-screen summary: task, available status, inputs, expected output, and next action. Keep detailed function names and model behavior notes in expandable or later sections if they remain useful.
- Keep the Arcade as an intentional adjacent experience. Preserve the main catalog route so its promotion does not become the only obvious starting point.
- Use the existing Keep exploring trays and branch hierarchy; the site already has onward navigation. Do not add a redundant navigation system simply to increase feature count.
- Test comprehension with a small set of newcomer tasks before authoring a broad rewrite. Record completion, wrong turns, and misunderstood availability, rather than inventing conversion percentages.

## Limits

No manual screen-reader speech review, field analytics, authenticated Search Console, external GPT configuration/behavior audit, exhaustive external-link session, penetration test, account-side analytics retention audit, or live Replit deployment inspection occurred. The referenced OverKill-Hill thread was unreadable on this host. Repository documentation and public evidence support the assessment without treating that missing thread as retrieved context.

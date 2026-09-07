# Visitor experience and performance evidence

Date: September 5, 2026. Worker: `/root/search_consent`, reporting to the implementation PM. Scope: residual A09 experience checks, A19 local measurements, and a reversible browsing prototype. Baseline commit: `f5f33986e6ee287fb165c75e82ef01e5d3ed1f99`; later source changes belong to the coordinated remaining program. The corrected performance rows record each served HTML and runtime SHA-256, and the report records CSS/index/adapter hashes.

## Result

The representative site journeys load and decode correctly in Chromium. A real skip-link focus defect was reproduced and delegated to the platform Worker, whose correction passes the follow-up experience checks. The enlarged index preserves useful discovery without a demonstrated need to reduce its content budget. Search layout stability and homepage image selection have concrete, bounded optimization evidence. The local design prototype is complete; no broad production redesign was applied.

## Measurement method and limits

The new `scripts/tests/test-experience-performance.cjs` uses the existing Playwright runtime and a temporary local static server. It runs home, Discovered Careers, Neighborly Bazaar, search with `q=seniority`, and Ecosystem. Each has cold and repeat navigation under two profiles, with two samples per condition: **40 performance/readiness cases**. The repeat visit uses the identical URL in the same browser context.

- Desktop: 1440 x 1000, normal CPU and local network.
- Constrained mobile: 390 x 844, 4x CPU slowdown, 150 ms request latency, 1.6 Mbps download and 0.75 Mbps upload.
- Service workers are disabled to isolate HTTP caching. The local server gzips text, uses a ten-minute asset cache and revalidates HTML. These are explicit lab conditions, not measured production headers.
- Resource sizes are actual Chromium Network `encodedDataLength` observations, including response overhead where reported. Source bytes/gzip sizes and hashes are also retained.
- Google Fonts was allowed by the test but failed with **`net::ERR_NETWORK_ACCESS_DENIED`** in this environment. Raw errors are preserved. These measurements use fallback fonts, and no successful font-transfer or font-optimization claim is made. Analytics requests were blocked.
- LCP and layout-shift observations cover the initial viewport observation window. The original runner mislabeled a lifetime layout-shift total as CLS; its nonzero historical values are described below as legacy totals. The corrected runner reports maximum session-window CLS separately from that total. Subsequent scrolling forces lazy images and diagrams to complete for separate readiness checks. This is not field p75, Lighthouse scoring, INP, or full browser-zoom/assistive-technology acceptance. The machine may be shared with other work, and two samples are too few for strong percentile or improvement claims.

## Observed transfer and timing

The table uses the corrected comparison run. KB below are decimal bytes / 1,000. Constrained cold LCP is the two observed values, not a performance promise.

| Route | Desktop cold initial transfer | Desktop repeat transfer | Constrained cold LCP |
|---|---:|---:|---:|
| Home | 366.0 KB | 8.1 KB | 2.09 / 2.04 s |
| Discovered Careers | 206.7 KB | 10.5 KB | 2.63 / 2.12 s |
| Neighborly Bazaar | 83.8 KB | 11.3 KB | 2.72 / 3.88 s |
| Search, `seniority` | 189.5 KB | 4.8 KB | 2.22 / 2.20 s |
| Ecosystem | 319.9 KB | 9.3 KB | See raw observations; diagram loading depends on viewport intersection |

Desktop home cold LCP varied from 0.316 to 3.076 seconds despite equal transferred bytes. That variance is retained and prevents a strong timing conclusion from these samples. Repeat asset cache hits were actually observed. Mobile Ecosystem initially loads much less diagram code because diagrams below the viewport are deferred; the runner subsequently scrolls every diagram into view and waits for a non-error SVG.

The shared stylesheet is **239,606 source bytes / 47,027 gzip bytes** at the initial baseline. The index is **436,530 bytes / 120,673 gzip bytes**, representing approximately 64% of the measured cold search transfer. Under the configured 200,000-byte/s download limit, the compressed index body alone represents about 0.60 seconds of transfer capacity, before latency and contention.

Each search sample parses the actual JSON 50 times and retains every duration. The median of those measurements was about **0.6-0.8 ms desktop and 8.7-13.9 ms under the constrained profile**. Synthetic query dispatch plus forced layout ranged from 3.8 to 15.9 ms in desktop cold samples, and 48.9 to 246.2 ms across the constrained observations. These probes are not human input-to-paint INP measurements. Their relative scale points to rendering/transfer investigation before sacrificing deep function text. No index budget reduction, dependency, or hosted search service is justified by this evidence.

After the PM's final generation checkpoint, the limited affected-route run completed **16 home/search cold/repeat cases**, with the same two profiles and two samples. All readiness checks pass. Final index size is 437,527 source bytes / 113,726 gzip bytes; final CSS is 240,252 / 47,167 bytes. The refreshed index SHA-256 is `4166767535f779991a489744a46517863e01af25d27750ed8fdd3732d5d72c62`.

Desktop cold homepage transfer decreased from 366,006 to 265,297 bytes, with the selected hero alone saving 100,926 source bytes. Repeat home transfer was 8,213 bytes. Chai still loaded within the browser's lazy proximity threshold, so this run demonstrates no additional Chai transfer saving. Cold search transfer decreased from 189,492 to 182,697 bytes, repeat 4,821 bytes; that difference includes the reviewed content/index refresh and small CSS additions, not solely the spacing fix. Seven final search observations contain complete empty shift arrays, supporting a zero session-window score. The remaining desktop cold sample has a legacy layout-shift total of 0.00244 from header navigation insertion, with insufficient timestamps to certify CLS. No final raw shift is attributed to the former results/categories movement.

One constrained homepage repeat observation records a legacy layout-shift total of **0.20863**, attributed by Chromium to a `::before` rectangle growing from about 199 x 200 to 390 x 681 pixels. It lacks the timestamps required to certify current CLS. The other seven home observations have complete empty shift arrays. This is a retained unresolved intermittent pseudo-element/layout observation, not a clean layout-stability claim for the whole homepage. Final desktop home cold LCP again varied from 0.300 to 3.072 seconds. No speed or field-percentile claim is made from these timings.

A bounded follow-up ran three additional constrained home cold/repeat pairs after the completed PM browser artifacts. All six readiness cases pass; their complete empty shift arrays support a derived session-window score of zero. That follow-up added shift time, document readiness, parent markup and candidate pseudo-element geometry capture for a future recurrence. Source inspection identifies the absolute, inset-zero, rotated `.glee-hero-card::before` paper as a plausible owner; it has no animation, and mobile scroll-reveal transforms are disabled. The original exact owning element and load state were not captured and could not be confirmed because the shift did not recur. No source change is justified from this isolated, unattributed observation. The original outlier remains open for future reproduction.

## Experience checks and correction

### Session-window measurement correction

Architect review found that the original `cls` field accumulated all non-input shifts instead of selecting the maximum session-window sum. Current CLS groups shifts using a gap strictly below 1,000 milliseconds and elapsed time strictly below 5,000 milliseconds from the window start. Recent-input entries are excluded and do not extend a window. The largest window sum is the score. This supersedes lifetime summation. [Current CLS definition](https://web.dev/articles/cls), [metric evolution](https://web.dev/blog/evolving-cls).

The QA runner now exports a pure accumulator and injects that same implementation into the browser observer. `cls` is the maximum session-window score; `layoutShiftTotal` separately preserves the sum of all non-input shifts in the observed lifetime. Raw shift records retain `value`, `startTime`, `hadRecentInput`, source rectangles and available owner/load-state context. These are foreground local-navigation observations, not complete page-lifetime, cross-frame or field-p75 measurements.

The new `scripts/tests/test-cls-session-window.cjs` reproduced five failures with the prior summation behavior, then all six tests passed after correction. Cases cover separated bursts, exact 1-second and 5-second boundaries, recent-input exclusion without bridging, later smaller/larger windows, and empty/input-only observations. A single constrained-home cold/repeat smoke pair passes with zero `cls`, zero `layoutShiftTotal` and complete empty shift arrays. No broad measurement rerun was performed for this correction.

`experience-cls-reassessment-2026-09-05.json` preserves references and SHA-256 hashes for every inspected original. Among 152 retained rows, including overlapping runs and the duplicated initial report, 55 have complete empty shift arrays and consistently zero totals, supporting derived session-window scores of zero. The remaining 97 are labeled `legacy-total-insufficient-timestamps`: 80 have no raw shift array, and 17 nonzero records lack timestamps. No retained nonzero timestamped record was available to recompute. Those legacy values are not certified CLS, including the 0.20863 home outlier and the pre-spacing search totals. The observed rectangles remain evidence of movement; the magnitude of a CLS improvement cannot be established from those old totals.

This correction owns only `scripts/tests/test-experience-performance.cjs`, `scripts/tests/test-cls-session-window.cjs`, this report and two new dated evidence files. It changes no public source, generated index/stat/CSP/cache output, dependency, stage or commit. Prior raw evidence remains byte-for-byte preserved. Default browser-run output now uses a unique timestamped filename. Reassessment requires a new output path and refuses to overwrite an existing file:

```powershell
node --test scripts/tests/test-cls-session-window.cjs
node scripts/tests/test-experience-performance.cjs --reassess-cls assets/audit/remaining-program-2026-09-05/experience-cls-reassessment-new.json
```

The runner exercises six routes, adding Universe, under 320 CSS-pixel reflow; a 640 x 450 viewport with 2x device scale as a **200% equivalent viewport approximation**; reduced motion; and forced colors. It checks decoded images, delayed non-error Mermaid SVGs, document overflow, skip-link behavior, keyboard menu/search handling, focus return, and named forced-color controls. It is not actual browser zoom or a screen-reader session.

The first run's hash-based skip assertion was too narrow. A strengthened reproduction then confirmed the actual defect in all 24 route/condition cases: after Enter on the skip link, focus remained on the anchor; the next Tab focused the header home link instead of main content. The platform Worker owns the `app.js` fix. The follow-up **24 cases pass**, including main/next-Tab focus. No first-party image decode, page-error, or late-diagram failure was observed in these cases. The initial raw failures remain unchanged.

The final 24-case run also passes computed reduced-motion duration/scroll-style assertions and unexpected first-party console-error checks, so completed initial animations cannot alone imply preference support. The final run is preserved separately in `experience-accessibility-final.json`.

Visual review of the search no-results state exposed a separate residual contrast defect. The initial layout runner incorrectly changed `data-theme` directly; those geometry results are preserved but are not valid dark-appearance evidence. The corrected runner uses the visible Glee color toggle and records both theme attributes. Its geometry passes, but the screenshot exposed pale body gradients behind dark-scheme light text and a later light-footer rule overriding pinned-dark text. A focused reproduction records 14 failing text samples across 12 home/search, OS-light/dark and auto/pinned-light/pinned-dark combinations.

With PM approval, the search body now uses the existing Glee background token, and the existing light-footer selectors exclude explicit dark mode using a zero-specificity guard. No palette or sibling rule changed. All 12 contrast cases pass: dark search heading/lede improved from 1.04:1 to 14.73:1; the affected pinned-dark footer text/headings from 1.26:1 to 15.22:1; links from 2.11:1 to 6.97:1; footer-bottom text from 2.84:1 to 6.97:1. These ratios concern the tested opaque text/background samples, not a claim that every element or browser has been audited.

The final post-generation 12-case run passes and its pinned-dark search screenshot was visually inspected. The strict accent checker originally expected the old literal footer selector and mistook the exclusion of dark mode for a positive dark selector. Two newly added fixtures first failed; the exact guarded expected selector and negation-aware mode classification now pass all six hover tests, including missing-rule and white-on-cream negative cases. Required hover checks were retained. The existing rendered-acceptance runner's initial attempt hit an unavailable local preview port; PM's subsequent `pm-rendered-final.json` confirms all four existing hero theme contrast cases pass.

## Bounded optimization evidence

**Search reserved-space correction:** the same-URL `seniority` run records legacy layout-shift totals of 0.09633 desktop and 0.13837 constrained mobile in both cold and repeat observations. These records lack shift timestamps and cannot establish the magnitude of a CLS improvement. Their LayoutShift sources still identify actual results-container, keyboard-help and footer movement when the index supplies categories/results. A local-response-only CSS experiment reserves 4rem for categories, 8rem below 600px, and 22rem for results. All eight candidate cases have complete empty shift arrays, supporting zero session-window scores, and pass readiness checks. The exact experimental CSS is retained in `experience-search-space-candidate.json`. The PM approved these Glee-scoped rules and this Worker applied them to `theme.css`. All 60 empty/no-result/query/category/reset layout cases pass at 320/390/820/980/1024/1440px in light and dark mode, with no document overflow or overlapping result/help/footer regions. The source correction preserves search content.

**Homepage image correction:** the original hero declared `sizes="100vw"` but its desktop CSS caps the image at 520px. At 1440px/DPR1 Chromium selected the 152,834-byte 1536w WebP for a rendered width of 450px. The existing 768w file is 51,908 bytes. The Content Worker applied CSS-derived responsive `sizes`, preserving all candidates and the hero's eager/high priority. The 140,845-byte Chai image now uses lazy/auto loading: its measured top is 1,140-1,734px at the six tested widths with a 900px viewport height. Native lazy-load proximity may still fetch it, so a guaranteed transfer saving is not claimed. Source bounding boxes are recorded in `experience-search-layout-final.json`.

## Completed local prototype

Open the self-contained local artifact:

[Catalog prototype](C:/Users/jamie/.codex/visualizations/2026/09/05/01a07294-1521-77f3-bc34-a7176b6e0444/remaining-program/catalog-prototype/index.html)

It provides a homepage, seven original branch filters, task search, availability filtering, status guide, concise detail dialog, light/dark mode, and internal next routes. All 42 entries and 1 live / 24 beta / 17 unavailable states come from the final PM-generated index snapshot. Unavailable details have no external GPT launch. The prototype uses the Glee-fully brand profile 1.1.0, existing butterfly art and declared font fallbacks; no font was downloaded. The snapshot was refreshed after the final content pass; its exact source hash, generation time, snapshot time and working-tree provenance are retained in catalog-data.js. Focused prototype tests pass after refresh.

`prototype-qa.json` records passing Chromium checks for 42 entries, seven branches, the 17-entry unavailable filter, Scheduling Wizard detail, Escape focus return, six Organized Life entries, theme/status controls, and document reflow at 320/375/640/1440. Desktop homepage/detail and mobile light/dark screenshots were captured and visually inspected. This demonstrates a concrete design option; user task success and wholesale production adoption remain owner decisions.

The representative Scheduling Wizard dialog brings inputs and intended output forward, using the current reviewed detail page: tasks, bill dates, events and available time; a calendar-ready plan to review yourself. It explicitly describes a concept and does not promise calendar integration, reminders or exports. Selecting Explore this branch now focuses the catalog heading after the result buttons are replaced; a dedicated browser assertion passes.

## Proposed regression budgets and task study

These are reviewable proposals, not already enforced release policy. Establish the final generated index as the accepted baseline, then require review for more than 5% growth in gzip index or shared CSS bytes. The final measured starting points are 113,726 and 47,167 bytes respectively; a larger budget can be justified by useful new indexed content rather than truncating it. For the measured 1440px/DPR1 homepage condition, require selection of an existing hero candidate no larger than 768w/51,908 bytes. Do not apply that cap to DPR2.

Use structural gates with the existing lab profiles: zero first-party request/decode/page errors, every deferred diagram renders a non-error SVG after intersection, no more than 1 CSS pixel of horizontal overflow at 320px, and keyboard skip/next-Tab/modal focus assertions pass. The earlier proposed 0.02 CLS budget is withdrawn from measurement acceptance: the legacy totals cannot validate that threshold. Establish a representative baseline with the corrected session-window calculation and consistent font availability before approving any CLS regression budget. Record cold/repeat wire bytes with the same URL and cache policy; review an increase above 5% before acceptance. Preserve all timing samples, but do not gate LCP/INP on two noisy local observations. Field thresholds require separately authorized field evidence.

Propose a small moderated study with five or six consenting participants, including at least two who primarily use the keyboard and a desktop/mobile mix. Counterbalance current site and prototype task order. Use neutral, fictional tasks: find a suitable everyday helper by browsing; identify that Scheduling Wizard is unavailable and choose an internal alternative; locate a tool through seniority or scheduling search; explain what opens outside the catalog and the access/privacy boundary before proceeding. Do not require a ChatGPT account or opening a private workspace.

Record completion without help, incorrect launch attempts from unavailable entries, correct status interpretation, search reformulations, assistance and reported next-step confidence. Target zero mistaken unavailable launch attempts and at least four of five independent completions per task as an initial design decision rule, not a statistically generalizable success rate. Treat completion times descriptively. Use deidentified observation notes and tallies, no new tracking code, personal search content or recording by default. Agree consent and short retention before sessions. Platform's report owns the distinction between documented site consent behavior and unverified provider retention settings. Real zoom and NVDA/VoiceOver sessions remain separate accessibility acceptance work.

## Evidence and reproduction

Machine evidence under `assets/audit/remaining-program-2026-09-05/`:

- `experience-performance-initial.json`: original 40-case data and 24 initial accessibility failures. Its repeat-search rows changed to `scheduling` after the cost probe; those rows are excluded from comparison conclusions.
- `experience-accessibility-focus-reproduction.json`: strengthened, actual focus/next-Tab failures.
- `experience-accessibility-after.json`: 24 passing cases after the platform correction.
- `experience-accessibility-final.json`: 24 passing cases including stronger computed reduced-motion checks.
- `experience-search-layout-final.json`: 60 passing search layout/state cases plus six homepage image measurements.
- `experience-search-layout-scheme-final.json`: supersedes the first layout run for valid theme control behavior, 60 geometry passes plus six homepage records; appearance defects are separately documented.
- `experience-home-images-after.json`: 12 actual image-selection records across six widths at DPR1 and DPR2.
- `experience-contrast-before.json` / `experience-contrast-after.json`: 14 failing samples before the focused cascade fix; all 12 case combinations pass afterward.
- `experience-performance-corrected.json`: 40 passing same-URL performance/readiness cases, with actual URLs, source hashes and LayoutShift sources.
- `experience-performance-final.json`: 16 post-generation affected home/search cases; readiness passes, one retained home pseudo-element legacy layout-shift total outlier.
- `experience-home-repeat-investigation.json`: six additional constrained-home observations, no recurrence of the original pseudo-element shift.
- `experience-contrast-final.json`: post-generation 12-case contrast verification with a visually inspected dark-search screenshot.
- `experience-cls-session-smoke-2026-09-05.json`: one corrected constrained-home cold/repeat pair, two readiness passes and zero session-window scores.
- `experience-cls-reassessment-2026-09-05.json`: derived classifications and source hashes; 55 complete empty observations and 97 legacy totals lacking sufficient timestamps.
- `experience-search-space-candidate.json`: eight passing controlled response-only CSS experiment cases.

```powershell
$env:NODE_PATH='C:/Users/jamie/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'
$env:EXPERIENCE_OUTPUT='assets/audit/remaining-program-2026-09-05/experience-performance-new-session-run.json'
node scripts/tests/test-experience-performance.cjs
```

Optional `EXPERIENCE_PERFORMANCE_ONLY=1` or `EXPERIENCE_ACCESSIBILITY_ONLY=1` limits the run. `EXPERIENCE_ROUTES=search` selects a performance route; `EXPERIENCE_SEARCH_SPACE=1` enables only the explicitly recorded local-response CSS experiment. No dependencies are installed. No production HTML, runtime, generated index/stat/CSP/cache outputs, commits, staging, or external publication was performed by this Worker in this package.

Exact source ownership delivered: `assets/css/theme.css` (approved search spacing/background and Glee footer guard only), `scripts/tests/test-experience-performance.cjs` (new QA runner), `scripts/check-accent-contrast.py` (guarded hover selector and negation classification), and `scripts/tests/test_check_accent_contrast.py` (three focused fixtures added). This report and dated machine evidence are the repository deliverables; the independent interactive prototype resides in the authorized local visualization directory. PM owns generated outputs, source integration and final acceptance.

Remaining limits: branded-font measurements require an environment that can load the existing font services; actual zoom, NVDA/VoiceOver and representative user sessions remain unperformed; live HTTP/cache behavior and released provenance require publication-stage verification. These are explicitly open, not inferred from local green checks.

# Architect review of the remaining-program submission

Review date: September 5, 2026. Status: **Approved for the bounded local implementation and delivered proposals. AR01 is closed after correction and independent verification. Release, live acceptance and proposal adoption remain open.**

## Submission and scope

The implementation PM submitted source commit `6f5d4d5c472c4e2bc66bf1a29e58464e692463a8` and evidence commit `b15257b6d6177b7d900a5eacd27187903f6a2567` on `codex/assessment-corrections-20260905`, at `C:/Users/jamie/.codex/worktrees/73b4/glee-fullytools`. The clean branch preserves the earlier corrective commits and PR #22; it is four commits ahead of the recorded main baseline `9b4ade05`.

The subsequent QA correction is `f782ba8097a17d3d0bb6bca8746fe9926f5915d1`, the clean branch HEAD at final review. Its nine changed files are two QA scripts, four Markdown records and three new JSON evidence files. Public source and existing artifact provenance remain at `6f5d4d5c`; no accepted commit or historical raw report was rewritten.

The submission implements the remaining authorized local corrections and supplies prototypes and policy proposals for decisions outside that implementation scope. Its assignment register accounts for A01-A20, R01-R16, D01-D09 and G01-G08. Completing a proposal is not implementing that proposal, and neither constitutes release or live acceptance.

## Review findings

**AR01, P2, CLOSED: reusable layout-shift calculation and evidence claims corrected.** The submitted `scripts/tests/test-experience-performance.cjs` added every non-input layout-shift value to a field named `cls`. Current CLS is the largest session-window score, using the one-second gap and five-second window boundaries, rather than the total of all observation-window shifts. Multiple separated bursts could therefore be overstated. This was a test-instrumentation defect, not an established production regression.

The PM delegated the correction and independently reviewed it. The corrected shared accumulator selects the maximum qualifying window, excludes recent-input shifts without letting them extend a window, and separately retains the raw non-input total and timed shift records. Definition: [Chrome's CLS guidance](https://web.dev/articles/cls).

The Architect freshly ran all six tests covering separate bursts, strict one-second/five-second boundaries, input exclusion, maximum-window selection and empty observations; all passed. Runner syntax passes. The Architect reproduced all 152 derived rows exactly and checked every retained source hash. These rows include overlapping runs and a duplicate report, not 152 independent samples. Fifty-five complete empty observations support zero scores; 97 rows lack sufficient timing evidence (80 lack raw arrays; 17 nonzero records lack timestamps). No nonempty historical sequence could be recomputed. Numerical before/after CLS improvement and acceptance of the proposed 0.02 budget have therefore been withdrawn. Movement evidence and measured image-byte savings remain supported; the historical homepage 0.20863 value is a legacy total, not certified CLS. The PM's bounded two-visit smoke with the corrected observer passes; no broad rerun was necessary.

Independent derived evidence: `C:/Users/jamie/.codex/visualizations/2026/09/05/01a07280-c6e5-7d70-8aa1-feba93994a47/architect-cls-reassessment.json`. The method note, assignment register, integration record and PR draft reflect the corrected interpretation. The intermittent homepage movement remains unresolved rather than being erased by the metric repair.

No other actionable introduced production defect was identified in this review. The Architect inspected content/schema changes, significant-date evidence, governance and proposals. A separate read-only Assessment PM reviewed modal opener capture and timer cancellation, fragment focus/history/reduced motion, dark-theme selector precedence, responsive homepage image sizes, and reserved search space. That review found no introduced production blocker.

## Fresh Architect verification

| Evidence | Result |
| --- | --- |
| Unit discovery | 54 tests: 53 pass, one Windows symlink-creation skip |
| Internal links and sitemap | 63 pages; 2,719 internal links; zero broken links or style issues; 60 sitemap URLs. External links counted only |
| Generated search | Current, 60 entries |
| Cross-engine browser journeys | 13 Chromium and 13 WebKit checks pass on HEAD `b15257b6`; actual committed search JSON served, external requests and SW blocked in this fixture |
| Packaged artifact and final tar | Verified against source `6f5d4d5c`: 711 files, 63 HTML pages, 208,684,194 bytes; required hidden public files retained |
| Git preservation | Earlier accepted commits remain ancestors; clean implementation branch; whitespace check passes |

Fresh browser evidence is `C:/Users/jamie/.codex/visualizations/2026/09/05/01a07280-c6e5-7d70-8aa1-feba93994a47/architect-continuation-browser.json`. The PM's separate full 504/504 Chromium sweep, 13 rendered checks, seven packaged service-worker checks, before/after defect reproductions, date ledger and source fingerprints were reviewed as PM evidence; they are not mislabeled as new Architect runs.

## Assessment of deliverables

Content corrections replace unsupported application/pricing/screenshot assertions with canonical WebPage identities across 42 details. The catalog's 1 live, 24 beta and 17 unavailable states remain unchanged. The Showcase and public instructions better distinguish intended uses from verified external behavior. All 38 advisories have individual dispositions; the broken `#why` route is repaired. Removing unsupported assertions does not verify any external GPT.

The sitemap retains 60 URLs with 57 supported modification dates and three optional omissions. The ledger distinguishes substantive content/schema changes from cache-token maintenance and cites inspected historical diffs. The old feed remains an acknowledged limitation with a concrete maintenance proposal. It has not been silently regenerated or accepted as current.

The representative catalog prototype supplies a homepage, branch/task/status discovery and a concise detail pattern. The Architect inspected its desktop and mobile dark captures and source inventory. This establishes delivery of a reviewable design option, not production-rollout approval or proven user-task improvement. Broader adoption should use the proposed representative task study and brand/interaction review.

Platform materials provide actionable source/target promotion rules, dependency/runtime candidates, hosting options, observed-versus-desired review settings, and a local PR draft. Candidate versions and historical observations require revalidation at adoption. No sibling promotion, dependency change, hosting change, review-setting change, external PR or deployment has occurred.

## Open limits and approval boundary

Python browser CI, actual GitHub transfer, publication and live checks remain open. Installed Firefox fails before website navigation; WebKit native next-link Tab, actual browser zoom, human assistive technology, loaded Google Fonts, provider settings and field outcomes remain unverified. The lab's retained homepage shift outlier remains unattributed after six nonreproducing observations; there is no basis to erase it or claim zero homepage layout shift.

**Architect decision:** accept the completed bounded local corrections, their stated local verification, and delivery of the reviewable prototypes and policy proposals. No actionable introduced defect remains open from this review. This accepts proposal delivery, not adoption. Final owner/release approval, actual CI and artifact transfer, deployment/live acceptance, human accessibility evidence and the separately enumerated policy decisions remain outstanding. The overall improvement program is not declared complete.

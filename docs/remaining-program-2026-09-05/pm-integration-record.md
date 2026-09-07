# PM integration and local acceptance record

Date: September 5, 2026. Local implementation is accepted for Architect review; the overall program and release remain open at the explicit decisions and gates below.

Release continuation: the subsequent owner/Architect instruction authorizes publication and verified cleanup. [Current release dispositions](release-dispositions-2026-09-06.md) supersede historical pending authorization labels in this record. The original assessment history is preserved in merge `547d1c12`; the portable proposal is now committed with release preparation. Native browser and CLS gates are wired into PR CI before publication. Git-backed preflight passes 63-page validation and CSP checks; the earlier archive/sandbox failures remain environment evidence. Both temporary QA copies and their source tar were removed after preserving results. See `assets/audit/release-2026-09-06/` for the preservation, preflight, and cleanup records.

## Identity and preservation

- Worktree: `C:/Users/jamie/.codex/worktrees/73b4/glee-fullytools`.
- Branch: `codex/assessment-corrections-20260905`.
- Continuation implementation: `6f5d4d5c472c4e2bc66bf1a29e58464e692463a8`.
- Preserved initial source/evidence: `8dea009c7b1887b129a1c5540ec1a39f6c028841` and `f5f33986e6ee287fb165c75e82ef01e5d3ed1f99`.
- Main and fetched origin/main remained `9b4ade05dbe6f8c755f20c2e7bc2e19b03da1b47`; no accepted commit was rewritten.
- Original clone tracked source is unchanged. Its two untracked assessment directories remain intact. No other worktree was edited.
- This final record and artifact evidence are recorded in a subsequent evidence-only commit. Public source and packaged bytes remain those of the implementation commit.

The [assignment register](assignment-register.md) accounts for every A01-A20 finding, 16 broader recommendations, nine owner decisions, and eight release gates. It records actual Worker IDs, exclusive file ownership, source freezes, dependencies, and final local dispositions. Content and dates were sequenced under one Worker to prevent overlapping HTML edits; experience/performance and platform/release had separate Workers. PM reviewed and integrated source, ran shared generators serially, and committed. Experience Worker independently reviewed the Content Worker's final source and found no actionable introduced defect in the recorded scope.

## What changed and why

The continuation reconciles unsupported catalog/Showcase claims, all 38 advisory findings, and meaningful source dates. The 42 details now describe canonical WebPage identities without unsupported application pricing or screenshots; all seven branch hubs and affected detail copy distinguish intended uses from unverified external behavior. Specific model, memory, routing, integration, and health assertions were corrected. Publication states remain 1 live, 24 beta, and 17 unavailable, with seven branches and 60 unchanged sitemap URLs.

Sitemap dates now have 57 supported values; Contact, Ecosystem, and Universe omit optional dates after bounded history review did not establish reliable significant updates. Legal reflects its actual disclosure correction. The 49-entry historical feed is unchanged, and its maintenance proposal is concrete and awaiting an owner decision.

Expanded browser checks found actual focus and contrast defects. The shared script now restores the explicit pointer opener, prevents deferred focus from targeting a closed dialog, moves focus with fragment navigation, and respects reduced motion. Scoped CSS corrects search's exposed light background and prevents light footer rules from overriding pinned dark mode. The strict hover checker recognizes the guarded selector while continuing to reject missing or low-contrast rules.

Measurement justified two small optimizations: reserve space for fetched search categories/results, and select an existing homepage hero size that matches its rendered width. The desktop DPR1 hero body is 100,926 bytes smaller; higher-resolution candidates remain available at DPR2. The below-fold game image is lazy/auto, but browser proximity can still load it early. No font or framework migration, index truncation, new dependency, or broad production redesign was introduced.

A refreshed, interactive local catalog prototype demonstrates task/status/branch filtering and a concise source-grounded detail pattern. Platform deliverables include exact-source sibling-promotion requirements, dependency/action/runtime candidates, hosting/header options, retention evidence requirements, a no-new-tracking task-study proposal, corrected runbooks, and a [finished local PR draft](pr-draft.md). No external PR was created.

## Integration and verification

PM ran search generation, portfolio statistics, search regeneration, CSP generation, and final CSS/SW fingerprint synchronization in dependency order. The final CSS token is `10030d12`, with 7,745 stylesheet lines. Check-only runs confirm current generated output.

| Check | Result and practical limit |
| --- | --- |
| Structural validation | PASS: 63 production pages, zero issues, zero warnings. |
| Internal links and sitemap | PASS: 2,719 internal links, zero broken/style issues; 60 URLs. The 1,087 external links were counted, not all visited. |
| Advisory audit | PASS: zero findings; all 38 starting findings individually disposed. |
| Index/stats/CSP/fingerprints/social metadata | PASS: 60 search entries, 42 details, seven branches, 25 non-placeholder destinations; CSP63 and all tokens current. |
| Strict contrast and both brand scope guards | PASS: zero advisories, all eight required hover checks; Glee and AskJamie coverage retained. Initial selector-guard failure preserved, then corrected with negative fixtures. |
| Python unit discovery | PASS: 54 tests, 53 pass / one Windows symlink-privilege skip. |
| Additional focused Python suites | PASS: nine visitor, three search producer, five hook, three reconciliation tests. Existing reconciliation ResourceWarning remains recorded. |
| Client/SW regressions | PASS: analytics/iframe regressions, nine SW cache/fault tests and three bootstrap states. |
| Independent search/consent browser suite | PASS: 11 Chromium journeys, including sibling fixture, history, retry, focus and storage exceptions. |
| Independent cross-engine release journeys | PASS: 26 Chromium/WebKit named checks; WebKit native next-link Tab coverage remains explicitly NOT RUN. |
| Independent rendered checks | PASS: 13, including four hero themes, decoded SVG and eight Resume Builder widths. |
| Full actual Chromium sweep | PASS: 504/504 cases across 63 pages and eight widths. This supersedes no prior raw failure report; earlier evidence remains intact. |
| Supplemental experience evidence | PASS for scoped assertions: 24 inclusive condition/route cases, 60 valid-theme search layout cases, 12 theme/contrast cases, 40 corrected baseline measurements, 16 final affected-route measurements. These are lab observations, not field or conformance certification. |
| Source fingerprint continuity | PASS: all 23 source files fingerprinted by the PM browser runner still match after the local implementation commit. |
| Packaged service-worker browser tests | PASS: seven Chromium checks on the final staged directory, including rejected storage, offline adapter/search, fallback and reconnect. |
| Local public artifact and final tar | PASS: 711 files, 63 HTML pages, 208,684,194 bytes; exact local source/provenance checks pass, required hidden files retained and development content excluded. |

Raw before/failure and after evidence lives under `assets/audit/remaining-program-2026-09-05/`. [PM integration checks](../../assets/audit/remaining-program-2026-09-05/pm-integration-checks.json), [full browser sweep](../../assets/audit/remaining-program-2026-09-05/pm-responsive-final.json), and [artifact verification](../../assets/audit/remaining-program-2026-09-05/pm-artifact-final.json) identify execution and limits. Fixed historical report files were restored after preserving task results in this dated packet. A Markdown audit copy's generated trailing spaces were preserved as raw text inside JSON rather than committed as a whitespace defect.

The Node fallback in PM runs resolved to system Node 24.11.1 with the existing Playwright 1.62.1 package; the platform inventory separately verified bundled Node 24.19.0. The report records actual runtime versions, not a claim that those executables are interchangeable. Python was the bundled 3.12.14 runtime.

## CLS measurement correction after Architect inspection

The Architect identified that the experience runner's original `cls` field summed all non-input shifts over the observation lifetime. The corrected runner uses the maximum session-window sum, joining shifts only when the gap is less than 1,000 ms and the elapsed window duration is less than 5,000 ms. `layoutShiftTotal` separately retains the lifetime total, and raw shifts retain timestamps and recent-input flags. The implementation follows the [CLS method](https://web.dev/articles/cls) and [session-window rationale](https://web.dev/blog/evolving-cls).

Experience Worker implemented the bounded QA change. PM independently reviewed the logic, reran all six synthetic tests and syntax validation, checked each derived historical row against its original, and verified all 23 prior public source fingerprints. The six tests exercise separated bursts, both exact boundaries and just-below cases, input-shift exclusion without bridging, maximum selection, and empty/input-only observations. One new constrained-home cold/repeat smoke pair records CLS 0 and raw total 0 in both visits, with no failed readiness assertions. The broad suites above were not rerun for this QA-only correction.

[Reassessment evidence](../../assets/audit/remaining-program-2026-09-05/experience-cls-reassessment-2026-09-05.json) preserves source hashes and identifies 152 rows across seven overlapping reports: 55 complete empty observations support zero, while 97 lack enough timestamps or raw entries to reconstruct CLS. No nonempty timestamped historical sequence was available to recalculate. The historical nonzero search values and homepage 0.20863 are now explicitly legacy totals. Their recorded movement and the separate image-byte savings remain valid observations, but numerical before/after CLS improvement and compliance with the proposed 0.02 CLS budget are not established. The new smoke does not resolve the intermittent historical homepage movement.

[PM independent review](../../assets/audit/remaining-program-2026-09-05/pm-cls-review-2026-09-05.json) records the checks; [new smoke evidence](../../assets/audit/remaining-program-2026-09-05/experience-cls-session-smoke-2026-09-05.json) records the current runner's output. All historical raw reports remain unchanged. Public implementation remains `6f5d4d5c472c4e2bc66bf1a29e58464e692463a8`, with the same staged directory and tar provenance; neither was rebuilt. The correction adds a focused QA/evidence commit after `b15257b6d6177b7d900a5eacd27187903f6a2567` and rewrites no accepted commit. No new dependency or external publication occurred.

## Reviewable artifacts

- [Content, all advisory dispositions, meaningful dates, and feed policy](content-and-dates.md).
- [Experience, contrast/performance evidence, budgets, and task study](experience-performance.md).
- [Platform decisions and executable release handoff](platform-release.md).
- [Local PR draft](pr-draft.md).
- [Interactive catalog prototype](C:/Users/jamie/.codex/visualizations/2026/09/05/01a07294-1521-77f3-bc34-a7176b6e0444/remaining-program/catalog-prototype/index.html).
- Local staged source: `C:/Users/jamie/.codex/visualizations/2026/09/05/01a07294-1521-77f3-bc34-a7176b6e0444/remaining-program/public-site-6f5d4d5c`.
- Local final archive: `C:/Users/jamie/.codex/visualizations/2026/09/05/01a07294-1521-77f3-bc34-a7176b6e0444/remaining-program/public-site-6f5d4d5c.tar`.

## Open decisions and release gates

G01/G02/G04 pass for the stated local scope. G03 exact-SHA Python/browser CI, G05 actual GitHub artifact transfer, G06 human assistive technology, G07 deployment/live acceptance, and G08 final Architect/owner release review remain open. No push, external PR, merge, deployment, settings, hosting/DNS change, dependency installation/upgrade, sibling synchronization, or publication-state upgrade occurred.

D01-D09 remain individual decisions: broad prototype rollout; maintained feed policy; sibling promotion; dependency/action/runtime adoption; external GPT evidence; hosting/header controls; provider/field/research evidence; remote review/check settings; and publication authorization. Each has a concrete deliverable in the register. A local correction does not make the external GPT catalog behavior verified.

Known limits remain explicit:

- Bundled Python lacks Playwright. Installed Firefox fails before page creation. Node fallback does not execute the Python CI suites; WebKit native Tab excludes ordinary links in the isolated fixture.
- True browser zoom, NVDA/VoiceOver and representative user studies were not performed. Reflow and emulated motion/colors are narrower evidence.
- Google Fonts requests are denied in the lab environment, so loaded branded-font performance and appearance require later verification.
- One constrained homepage repeat sample recorded a legacy layout-shift total of 0.20863. Its raw shifts lack timestamps, so corrected session-window CLS cannot be recovered. Six isolated follow-up observations recorded no shifts. The original movement remains an intermittent, unattributed lab finding; no safe source correction or broad zero-homepage-CLS claim is justified.
- An optional upstream inventory refresh failed and its escalated approval/tool wait was interrupted. The packet distinguishes earlier individually observed candidate pins from the failed refreshed evidence. No upgrade or successful refresh is claimed.
- Historical feed summaries/dates and provider-side retention remain known decision/evidence gaps. Hosted headers, actual transferred bytes, deployed provenance, live routes and external services require release-stage checks.

The bounded local implementation and proposals are ready for Architect review. The register remains the source for unfinished decisions and release work; this record does not mark the overall program complete.

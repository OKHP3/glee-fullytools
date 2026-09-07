# Remaining corrective program assignment register

Date: September 5, 2026. Accountable integrator: Implementation PM task `01a07294-1521-77f3-bc34-a7176b6e0444`. Architect: `01a07280-c6e5-7d70-8aa1-feba93994a47`.

## Authorized release continuation and agent configuration

The owner's subsequent consolidation instruction authorizes this reviewed program's PR, CI, squash merge, deployment, live verification, and verified cleanup. D09 is authorized. [Release dispositions](release-dispositions-2026-09-06.md) supersede the historical pending authorization labels below and account for all 53 A/R/D/G rows. Optional policy/prototype adoption and external human evidence retain their separate limits.

The operating model is Architect approval, PM planning/delegation/review/integration, and bounded Worker execution. The Architect confirmed an app dispatch requesting PM `gpt-5.6-luna` with `medium` reasoning for this continuation. Runtime model identity is not independently exposed to the PM. Earlier Workers inherited settings; their actual model and effort are unknown and are not retroactively labeled Luna. Those Workers completed their active assignments and will not receive new work under unverified inherited settings. Future Workers use an explicit `gpt-5.6-luna` dispatch with `low` reasoning for mechanical work, or `medium` for evidenced CI/logic diagnosis, with concise task context.

The Architect's separate read-only acceptance Worker `01a074ba-1396-72c2-832c-8dc0ff211dea` was requested as Luna/low and found no actionable release-preparation defect. Its conflicting self-description is not runtime metadata. That review did not execute CI or deployment. The original three Workers' final release-preparation roles were: platform workflow wiring/runbook correction; experience portable-prototype preservation; and content all-row disposition plus independent merge preservation. PM retains sole mutation/integration ownership.

| Release Worker | Confirmed dispatch configuration | Bounded assignment |
| --- | --- | --- |
| `/root/release_live_luna` | `gpt-5.6-luna`, low, no history fork | Prepared an external live verifier. PM review found inadequate offline/error assertions, missing provenance comparison and resource-navigation handling; preparation alone was not accepted as live proof. |
| `/root/release_live_fix` | `gpt-5.6-luna`, medium, no history fork | Correct those specific verifier defects and produce meaningful failure behavior. Medium reasoning is limited to the evidenced QA logic gaps. No public source ownership. |
| `/root/release_ci_luna` | `gpt-5.6-luna`, medium, no history fork | Diagnose the actual failed native visitor acceptance step in PR #23 run `34009841226`; own only focused QA correction and unique evidence. No speculative production/CSP change or weaker gate. |
| `/root/release_assets_luna` | `gpt-5.6-luna`, medium, no history fork | Align the four Arcade metadata names and correct JavaScript fingerprint generation through the actual dynamic adapter import, HTML, and service worker consumers. PM retains shared generator execution. |

These entries record accepted tool dispatch parameters, not unverifiable model self-descriptions. Workers do not poll CI while idle. The PM reviews results and serializes Git, shared generation, PR, and release actions.

At PR #23 commit `e2274b22ce2d7ee6d31777908af4188b66e2a40a`, Site Validation, Sparkle, and i18n checks passed. The 504-combination viewport sweep passed, but inclusive accessibility passed only 15 of 16 checks because accented search did not return Resume Builder first. Native visitor acceptance failed in all three engines at a CSP-incompatible test polling helper. Existing three-engine resilience checks passed. Full failed job logs and native report artifacts are retained under `assets/audit/release-2026-09-06/`. These results are failed release gates, not release acceptance.

PM review rejected the first cache-generator proposal after reproducing a fragment parsing exception and finding that the real dynamic adapter import still used an unversioned URL. The revised dependency order is adapter hash, adapter URL in the main script, main-script hash, HTML references, and service-worker cache version. Five fingerprint/reconciliation regressions and nine service-worker fault tests passed independently after that correction. Final generated-tree and exact-commit CI acceptance remain required.

The inclusive failure was a confirmed regression: `41de445b` introduced accent folding and its visitor expectation; `8dea009c` removed the normalizer. The Architect approved restoring that behavior. The CI Worker restored consistent NFKD normalization while retaining Unicode tokenization, ranking weights, and category filtering. PM independently passed the composed/decomposed accent, Japanese, multiword, and category browser cases, all 11 search/consent scenarios, and seven real service-worker journeys after final fingerprint generation. The original inclusive expectation remains intact. Check-only search/stats/fingerprint/CSP validation passed; 63 pages have zero validation issues or warnings, 2,719 internal links have zero broken targets, and all 42 catalog claim checks pass. The fingerprint generator repeat made no changes. Evidence: `assets/audit/release-2026-09-06/pm-corrective-preflight.json`. These local passes do not substitute for final-head CI or deployment evidence.

At `d3f460ae609973c7c6d1ad4e73851d9f1d59c5c2`, Validation, Sparkle, i18n, and the complete Viewport job passed. Native acceptance passed all nine cases in Chromium and Firefox; WebKit timed out because the shipped transport directive upgraded loopback HTTP resources to HTTPS. The Architect accepted the established local fixture correction: only same-origin localhost/127.0.0.1 HTTP navigation HTML omits `upgrade-insecure-requests`; production HTTPS, external/non-HTML responses, resource allowlists, and native assertions remain unchanged. Five helper boundary tests pass, and PM independently observed the adapted WebKit page load the versioned main script and adapter successfully. Raw before/after request evidence is retained in `assets/audit/release-2026-09-06/ci-native-acceptance/`. Final-head CI remains the release gate. Live HTTPS verification receives no fixture transformation.

This is the durable assignment and acceptance ledger for the owner's continuation. Assignment is not completion. Initial implementation and evidence commits `8dea009c7b1887b129a1c5540ec1a39f6c028841` and `f5f33986e6ee287fb165c75e82ef01e5d3ed1f99` were accepted locally. The starting worktree is clean; main is `9b4ade05dbe6f8c755f20c2e7bc2e19b03da1b47`. Accepted commits, other worktrees, and the original assessment remain preserved.

## Owners and exclusive assignments

| Owner | Actual Worker ID | Bounded deliverable and file ownership | Dependencies |
| --- | --- | --- | --- |
| C: Content and dates (`/root/visitor_truth`) | `01a07295-f8c7-7dc1-ad71-41df7036f055` | Packages 1 and 2, sequenced: production HTML claims/schema/advisories first, then meaningful dates and sitemap; unique catalog claim gate/tests; `content-and-dates.md` and content/date JSON evidence. | Preserve 42 leaves, seven branches, 63 validator pages, 60 indexable pages and publication counts 1/24/17; no feed or shared generators. |
| X: Experience and performance (`/root/search_consent`) | `01a07296-3a57-72f3-9cb1-c0a7b5a47652` | Package 3: unique experience QA runner, representative lab evidence, `experience-performance.md`, and reversible local prototype outside production. CSS only after exact focused proposal accepted by PM. | Read-only production baseline; coordinate content changes; no invented capability or broad design rollout. |
| P: Platform and release (`/root/delivery_resilience`) | `01a07296-7be4-7280-83a5-562ee25ab0b2` | Package 4 plus operational A16: assigned active governance/runbooks including deployment guide, `platform-release.md`, local `pr-draft.md`, unique readiness evidence. Added exclusive `assets/js/app.js` for reproduced focus corrections and one validation-workflow line for the catalog regression. | No dependency/action-pin edits, settings, or sibling writes. Existing installed runtimes only. |
| PM | `01a07294-1521-77f3-bc34-a7176b6e0444` | Independent review, register, serialized generated index/stats/CSP/fingerprints/SW versions, integration tests and commits. | Workers never stage, commit, run shared generators, or overwrite another owner's files. |
| Owner / Architect | Jamie / Architect task above | Decisions and separate release authorization; review proposed rollout and policies. | Decision-dependent rows stay pending while unrelated authorized local work continues. |

## All assessed findings

Prior accepted evidence is in `assets/docs/implementation-2026-09-05/implementation-record.md` and the associated dated audit directory. New report paths below are relative to this directory and are pending until delivered and reviewed.

| ID | Accountable owner | Deliverable and acceptance evidence | Starting disposition / dependency |
| --- | --- | --- | --- |
| A01 | PM; X regression | Glee search identity remains correct in modal and inline browser journeys. | Accepted locally; retain through integration and release gates. |
| A02 | PM; X regression | Category/branch labels, ranking, history, keyboard and generated corpus remain functional; measure enlarged index. | Accepted locally; seven-branch filter expansion is proposal R03. |
| A03 | C | All unavailable destinations route through accurate internal status; re-audit every leaf and preserve counts. | Accepted locally; residual claim review assigned. |
| A04 | C | Scheduling and remaining detail copy contain no author scaffold; catalog tests and full text review. | Accepted locally; protect during metadata edits. |
| A05 | X | Retain rendered contrast in four themes; assess reflow/focus/motion/color modes beyond initial checks. | Accepted correction; broader accessibility evidence in progress. |
| A06 | PM; X regression | Consent reload reflects effective stored choice, including storage failure; fresh-session analytics remains off. | Accepted locally; provider settings not verified. |
| A07 | P / PM | Hidden public security file survives local stage and tar validation; exact transfer and live URL checked at release. | Local mechanism accepted; actual transfer/live pending authorization. |
| A08 | P / PM | Explicit public inventory excludes development content; stage/tar negative cases and future live exclusions. | Local mechanism accepted; deployment proof pending. |
| A09 | X and P; PM integrates | Behavioral, delayed Mermaid, asset decode/network, browser engine and available runtime checks with honest coverage matrix. | Residual local coverage in progress; Python CI and manual assistive technology remain separate gates. |
| A10 | PM regression | Successful network responses survive rejected cache writes in VM and real browser fault injection. | Accepted locally; rerun relevant integration gates. |
| A11 | PM regression | Query/cache bound, offline shell and adapter/late registration remain verified. | Accepted locally; rerun relevant integration gates. |
| A12 | C | Reconcile remaining identity/model/privacy/memory claims against approved source evidence without upgrading tool states. | Broad residual review in progress; unsupported external behavior remains unknown. |
| A13 | C and X | Preserve corrected Toolbox CTA; assess remaining navigation/content issues and deliver representative hierarchy prototype. | Corrected CTA accepted; proposal and focused findings in progress. |
| A14 | C | Remove unsupported price/free offer/application/screenshot schema assertions and Showcase eligibility claims; parse and audit 42 details. | In progress; no manufactured rating or product evidence. |
| A15 | C | Evidence-backed sitemap dates or justified omission; truthful Legal label; concrete maintained feed/date policy proposal. | In progress; no mass stamping or archived generator; feed policy owner decision D02. |
| A16 | C dates; P governance | Correct active factual drift and current executable runbook; desired four checks distinguished from observed three. | Initial runbook accepted; remaining active governance in progress. |
| A17 | P | Explicit reviewed source/hash promotion proposal with target compatibility, rejection cases and rollback, no latest-touch selection. | Proposal in progress; sibling execution needs D03. |
| A18 | P | Current versions/provenance and concrete proposed pin/host-aware runtime policy; installed engine results and missing-runtime boundary. | Proposal and local verification in progress; changes/install need D04. |
| A19 | X | Home/branch/detail/search/diagram cold, repeat and constrained lab measurements; bytes/index parse cost and justified budgets. | In progress; no field or conversion claim. |
| A20 | X regression | All SVG XML parse; affected illustration actually decodes at representative widths. | Accepted locally; retain through full asset assessment. |

## Broader recommendations and decisions

| ID | Owner | Bounded result / evidence | Disposition and next dependency |
| --- | --- | --- | --- |
| R01 | X | Local homepage prototype: concise purpose, primary browse/task entry, warm butterfly brand and familiar tree. | Assigned; broad rollout D01. |
| R02 | X with C facts | Representative detail prototype: purpose, status, inputs/outputs, external boundaries and optional deeper content. | Assigned; broad rollout D01, no new capability claims. |
| R03 | X | Status before click, unavailable discoverability, long/mobile navigation labels and optional seven-branch filters. | Assigned prototype; taxonomy/state preserved, rollout D01. |
| R04 | C | External GPT evidence gap list covering configuration/model/account/privacy/memory and verified destinations. | Assigned; owner sanitized evidence D05, no availability upgrade. |
| R05 | C | Review existing health guardrails and professional-care boundaries without adding medical guidance. | Assigned source/copy review. |
| R06 | C | Reconcile Showcase/portfolio proof, launch claims, package metadata claims, Ko-fi overlay, search-weight and under-50-ms assertions. | Assigned; remove unsupported assertions rather than invent proof. |
| R07 | C | Individually dispose all 38 advisory findings: 37 length heuristics and the actual under-construction `#why` link defect. | Assigned; preserve evidence for retain/change decisions. |
| R08 | C | Schema syntax versus rich-result eligibility clearly distinguished; no invented ratings, offers or screenshots. | Assigned with A14. |
| R09 | C | Meaningful change provenance, sitemap/feed lifecycle, Legal date and archived-generator boundary. | Assigned with A15; maintained feed policy D02. |
| R10 | X / P | 320-pixel reflow, 200% zoom, keyboard/focus, reduced motion, forced colors and target-size review; accessible-name evidence. | Assigned installed-browser checks; manual NVDA/VoiceOver G06. |
| R11 | X | Font/CSS/image/index transfer and CPU budgets from representative runs, raw failures retained. | Assigned with A19; framework/build migration not authorized. |
| R12 | P | Active meta CSP versus response-header limits; concrete hosting/edge options and testable acceptance. | Proposal assigned; hosting/settings D06. |
| R13 | P | Analytics retention policy versus unverified provider setting; field measurement/user research plan without new tracking. | Proposal assigned; provider evidence or instrumentation D07. |
| R14 | P | Explicit-source sibling promotion, source hash and per-target semantic compatibility. | Proposal assigned with A17; D03. |
| R15 | P | Immutable action/dependency policy, current/proposed versions and runtime handoff. | Proposal assigned with A18; D04. |
| R16 | P | Required-check desired/observed distinction and exact-SHA CI/release gate map. | Assigned; settings change D08, release D09. |

| Decision | Accountable decision owner | Reviewable result required before decision |
| --- | --- | --- |
| D01 | Jamie / Architect | Representative local homepage/detail/navigation prototype, findings and rollout scope. |
| D02 | Jamie / Architect | Feed/date proposal with source rules, meaningful-update policy and verification requirements. |
| D03 | Jamie / Architect | Explicit-source sibling promotion contract and target-specific compatibility checklist. |
| D04 | Jamie / Architect | Proposed exact dependency/action/runtime changes with provenance, update ownership and required checks. |
| D05 | Jamie | Sanitized external GPT configuration/capability evidence; absence remains unknown. |
| D06 | Jamie / Architect | Host/header options, expected browser headers, costs/tradeoffs and rollback; no DNS/hosting action now. |
| D07 | Jamie | Provider settings evidence and optional separately approved field/research plan. |
| D08 | Jamie / Architect | Required review/check settings proposal compared with dated actual observations. |
| D09 | Jamie / Architect | Concrete local PR draft, exact commits, review results and release checklist; no external publication now. |

## Release and acceptance gates

| Gate | Accountable owner | Required evidence | Starting disposition |
| --- | --- | --- | --- |
| G01 Source and generated integrity | PM | Scoped diff, source review, preserved states/routes, generators in dependency order, check-only validation and whitespace. | Pending current continuation integration. |
| G02 Local regression and browser evidence | PM; X/P execute | Meaningful unit/static/browser checks and raw results; coverage, failures and exclusions stated. | Initial wave accepted; continuation pending. |
| G03 Exact-SHA Python/browser CI | P; PM release review | Actual GitHub CI on proposed source SHA, native Python browser tests and required contexts. | NOT RUN: external publication unauthorized; local fallback is not CI proof. |
| G04 Local artifact and final tar | PM | Explicit inventory, hidden public files, excluded development paths, exact provenance and final tar verification. | Initial wave accepted; repeat after integrated source. |
| G05 Actual artifact transfer | P; PM release review | Upload/download and Pages artifact inspection at exact source SHA. | NOT RUN: release authorization D09 required. |
| G06 Manual assistive technology | X coordinates; human reviewer | Real NVDA/VoiceOver journeys, focus announcements and usability record. | NOT RUN: browser automation does not substitute for AT. |
| G07 Deployment and live acceptance | P; PM / Architect review | Exact-SHA deployment provenance, public routes/assets/security.txt, excluded development URLs and response headers. | NOT RUN: deployment D09 and relevant hosting decision required. |
| G08 Final release review | Architect / Jamie | Reviewable local PR packet, unresolved decisions and all gate dispositions; do not imply deployed completion. | Pending deliverables; no push, external PR, merge or deploy in current scope. |

## Integration order and status updates

Workers deliver unique reports and source diffs. PM reviews them independently, requests corrections, then serializes search generation, portfolio statistics, search regeneration if statistics changed, CSP generation, and final CSS/SW fingerprints. PM then verifies the final tree and artifact, commits the bounded reviewed work, and updates this ledger with exact evidence and dispositions. A completed Worker report does not complete the entire program or release.

First checkpoint: all three Workers confirmed execution. Platform detected a possible WebKit modal focus-return defect and received exclusive scope for a focused reproduction/correction. Firefox fails during page setup in the installed runtime, before site navigation; this remains NOT RUN. Experience measurements encountered blocked Google Fonts requests, so font-loaded performance is not established. PM requested correction of search repeat-navigation comparability before accepting the performance evidence. Content received approval for `scripts/check-catalog-claims.py` and focused fixtures, with a future evidence-backed application-schema exception rather than a permanent universal prohibition.

## Reviewed local dispositions after integration

### Architect-requested CLS QA correction

The Architect's inspection required correcting A19/R11 measurement semantics. Experience Worker `/root/search_consent` (`01a07296-3a57-72f3-9cb1-c0a7b5a47652`) received exclusive ownership of the experience runner, `scripts/tests/test-cls-session-window.cjs`, its method note, and new dated evidence. PM independently reviewed the implementation and historical-data classification, owns this register, the integration record and PR draft, and commits the correction. Public source, generated outputs, the existing artifact, and accepted commits remain frozen.

Acceptance: six synthetic tests pass, covering separate bursts, strict one-/five-second boundaries, recent-input exclusion, and maximum-window selection. One constrained-home cold/repeat pair records zero shifts in both visits. PM independently verified all 152 reassessment rows across seven overlapping reports: 55 complete empty observations support zero; 97 lack sufficient timestamps/raw entries and remain legacy totals with unknown CLS. These are report rows, not independent observations. Historical files are unchanged, and all 23 previously fingerprinted public source files still match. See `experience-performance.md` and `assets/audit/remaining-program-2026-09-05/pm-cls-review-2026-09-05.json` (repository-relative) for evidence. No broad sweep or performance sampling was repeated. Local QA acceptance does not close the existing release gates.

The starting tables above preserve dispatch history. This table supersedes their in-progress labels. All public source changes are frozen, generated outputs are current, and the checks below use the integrated source. Exact implementation and artifact provenance are recorded in `pm-integration-record.md` after the local commit. Release, policy, and evidence decisions remain open as individually identified.

| Finding | Reviewed local disposition | Evidence / remaining dependency |
| --- | --- | --- |
| A01 | Accepted locally; protected through integration | PM search/consent 11 journeys; default sibling fixture retained. G03/G07 remain open. |
| A02 | Accepted locally; final generated search and history/keyboard behavior pass | 60 entries, deep search tests, browser journeys. R03 broader filtering remains a prototype decision. |
| A03 | Accepted locally; unavailable launch routes preserved | Whole-catalog and visitor tests: 42 entries, 1/24/17 states. External behavior D05 remains unknown. |
| A04 | Accepted locally; additional residual author instructions corrected | `content-and-dates.md`, eight claim tests and nine visitor tests; expanded scaffold patterns. |
| A05 | Accepted scoped contrast corrections | Existing four hero themes pass; 12 new search/footer theme combinations pass. Search dark text 14.73:1; affected dark footer text 15.22:1 and links 6.97:1. G06 remains open. |
| A06 | Accepted locally | Consent hydration/storage/enable-disable regressions and Chromium/WebKit reload checks pass. Provider settings D07 remain unknown. |
| A07 | Local staging mechanism accepted | Public artifact regression/stage/tar; actual GitHub transfer and live security.txt are G05/G07. |
| A08 | Local exclusion mechanism accepted | Public allowlist and negative fixtures; actual excluded live URLs remain G07. |
| A09 | Expanded local evidence accepted with explicit limits | Full Chromium 504/504; 26 Chromium/WebKit checks; 24 inclusive condition/route cases; delayed diagrams/assets. Python CI, Firefox runtime, true browser zoom and human AT remain unverified. |
| A10 | Accepted locally; preserved | Nine SW fault/cache regressions; packaged real-browser resilience recorded in PM evidence. G07 still applies. |
| A11 | Accepted locally; preserved | Query/cache bound, adapter bootstrap and offline shell checks. G07 still applies. |
| A12 | Local unsupported claims corrected | 42 details, seven hubs, Persona and relevant supporting copy; source review plus tests. D05 requires owner evidence before restoration of external claims. |
| A13 | Corrected CTA retained; representative design option delivered | Local homepage/task/status/navigation/detail prototype. Broad rollout remains D01. |
| A14 | Corrected locally | 42 canonical WebPage identities; unsupported offers/application screenshots removed; Showcase reconciled; CI claim regression added. |
| A15 | Source dates corrected; feed proposal delivered | 60 URLs, 57 supported dates, three optional omissions; Legal corrected; full date ledger/history. Historical feed unchanged pending D02. |
| A16 | Active factual corrections and reviewable runbook delivered | Platform report and current governance distinguish observed settings, policy, generated checks and release evidence. G03/G07/D08 remain open. |
| A17 | Concrete promotion contract delivered; execution pending | Full source/target/blob inventory and failure cases in platform report. No executor or sibling synchronization claimed; D03. |
| A18 | Concrete pin/runtime policy and evidence delivered; adoption pending | Installed runtime results, exact candidate provenance, host-aware setup proposal. No install or pin change; D04. |
| A19 | Measurement/prototype work delivered; CLS method corrected after Architect review | Search reserves loading space; homepage selects existing correct image size (100,926 bytes less at desktop DPR1). The historical 0.20863 homepage value is a legacy layout-shift total without timestamps, so session-window CLS cannot be recovered. Six isolated follow-up cases recorded no shifts; the new bounded two-visit smoke also records zero. No broad zero-CLS or field claim. |
| A20 | Accepted locally; preserved | All 43 SVGs parse and affected illustration decodes; final full sweep passes. |

| Broader recommendation | Delivered disposition and owner dependency |
| --- | --- |
| R01-R03 | Interactive local homepage, seven-branch/task/state filtering, status guide and concise detail pattern delivered and tested; final index snapshot used. D01 is broader rollout. |
| R04-R05 | External-evidence gaps and health boundaries recorded; specific unsupported claims removed without publication upgrades. D05 remains required for external capability certification. |
| R06-R08 | Showcase/architecture/proof/metadata/schema copy corrected; all 38 advisories individually disposed; actual `/#why` route repaired. |
| R09 | Meaningful date review delivered; historical feed explicitly retained pending concrete D02 policy proposal. |
| R10 | Local keyboard/reflow/motion/color-mode evidence delivered. Actual zoom and human AT remain NOT RUN, not conformance PASS. |
| R11 | Measured transfer/index/render costs, proposed regression budgets and focused image/search corrections delivered. Architect-requested CLS correction separates maximum session-window score from raw total; legacy data cannot validate the proposed CLS budget. Branded fonts and field evidence remain unverified. |
| R12 | Retain-Pages/proxy/alternate-host decision packet and acceptance/rollback delivered. D06 remains required before changes. |
| R13 | No-new-tracking task-study and provider-evidence/field-measurement proposal delivered; provider settings, field performance and user outcomes remain unknown. D07. |
| R14-R16 | Explicit-source promotion, immutable-version/runtime options and desired/observed release governance documented. D03/D04/D08/D09 remain open. |

G01/G02 pass for the scoped local checks recorded in the PM packet; G04 is finalized against the local implementation commit and exact tar. G03/G05/G06/G07/G08 remain NOT RUN or pending review/authorization. A Worker finishing or a local gate passing does not close the program, approve a policy, or publish the release.

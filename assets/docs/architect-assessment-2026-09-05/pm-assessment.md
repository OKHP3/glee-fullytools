# Project Manager assessment and reconciliation

Reviewed: 2026-09-05. Baseline: `5da805785d47f9bc29058b07d2a5467da32a1573`.

This report contributes source-backed governance and architecture findings to the Architect's comprehensive assessment. The worker reports provide the detailed content and infrastructure evidence; the Architect provides current GitHub and live-browser evidence. Production source and Git state were not changed by this assessment.

## Architectural judgment

**Proposal:** Keep the static HTML, shared CSS, vanilla JavaScript, and Python maintenance model. The product is a catalog and routing hub, and the accepted no-framework decision fits that purpose (`docs/adr/0001-static-html-no-framework.md:47`). Current problems concern truthful discovery, shared-runtime contracts, release evidence, and authoring drift. No measured evidence gathered by this PM justifies a framework migration.

**Confirmed:** `docs/suite-promise.md` is substantially stronger than a generic marketing promise. It separates authored catalog pages from external GPT behavior, defines 1 live / 24 beta / 17 unavailable entries, and records intentional deferrals. Preserve that distinction. A functioning external URL, internal link-check pass, or visually complete page is insufficient to upgrade a Tool-ette's publication state.

## Direct PM findings

| ID | Priority | Claim | Tier | Evidence | Consequence if false | Next check |
|---|---|---|---|---|---|---|
| PM-01 | P1 maintenance | Active operating guidance directs agents to missing or retired mutators and claims the post-merge hook rebuilds artifacts although the hook checks them only. | Confirmed | `.agents/agent-skills.md:49`, `:53`, `:129`; `replit.md:235`, `:259`, `:264`; `scripts/README.md:71`; `scripts/post-merge.sh:14`, `:17`, `:20`; `pm-governance-command-paths.json` | An editor may run archived one-shot tools, fail routine commands, or expect a release hook to repair stale generated data. | Replace current quick references with the active command contract; retain dated history unchanged. |
| PM-02 | P2 maintenance | ADR-0004 and the roadmap still describe an unsafe-inline script policy and future hardening that the current CSP implementation has already superseded. | Confirmed | `docs/adr/0004-enforced-csp-headers.md:43`, `:69`, `:74`; `docs/roadmap.md:24`; external GA setup `assets/js/glee-site-enhancements.js:18`; current CSP `scripts/csp.py:130` | A future worker could weaken current policy or duplicate already completed hardening. | Reconcile present-tense policy text with the generator and preserve genuine HTTP header limits. |
| PM-03 | P2 maintenance | Foundation sync chooses a winner by latest commit timestamp when copies form two content groups. That is not evidence of semantic compatibility or release readiness. | Confirmed mechanism; inferred risk | `scripts/sync-foundation-files.py:24`, `:318`, `:323`, `:339`, `:429`; `docs/companion-publishing-contract.md:53`, `:57`; `pm-foundation-hashes.json` | A clean but distinct sibling adaptation can be overwritten by newer content without a compatibility review. | Require a reviewed source commit and compatibility contract before write modes; test two-group, dirty, missing, and conflicting cases. |
| PM-04 | P2 governance | Release policy contains both a four-check desired table and wording requiring three checks. Current settings need their own live evidence. | Confirmed source inconsistency | `docs/release-governance.md:39`, `:89`, `:122` | A maintainer may configure the older three-check set while believing the new resilience gate is mandatory. | Reconcile desired and observed settings against the Architect's fresh GitHub snapshot. |
| PM-05 | P1 trust / P2 implementation | On reload with stored consent granted, analytics initializes but the status element retains its authored off text. | Confirmed source; independently reproduced by Architect in live browser with measurement requests aborted | `assets/js/glee-site-enhancements.js:33` updates status only on action; `:44` loads analytics on granted initialization without hydrating status; `legal/index.html:296` defaults to off. | The visible privacy control contradicts actual browser behavior after a visitor's prior choice. | Initialize status from the same consent value used for analytics loading; test enable/reload/disable/reload and blocked storage. |

Evidence JSON paths above are relative to `assets/audit/architect-assessment-2026-09-05/`.

The foundation hash snapshot found `app.js` and `mermaid-init.js` identical across all three local mirrors; Glee and AskJamie shared one CSS hash while OverKill had another. This proves content divergence, not a defect in either stylesheet and not authority to synchronize them. The sync script already defaults to dry-run, blocks dirty write inputs, and refuses three distinct groups. Preserve those safeguards while addressing the unsupported two-group inference.

## Proposed governance work packages

### GOV-1: Make the agent runbook executable

Owner: documentation/tooling Worker; PM reviews. Scope: `.agents/agent-skills.md`, current operational sections of `replit.md`, `scripts/README.md`, `docs/roadmap.md`, and ADR current-status wording. Do not rewrite historical audit sections or resurrect archived tools. Avoid structural edits to AGENTS sections 1–5 unless the cross-repository sync requirement is explicitly included in a later assignment.

Acceptance:

- Every command presented as active exists and uses the correct interpreter.
- Feed maintenance is described consistently with the contract's explicit owner-approved boundary.
- Post-merge is described as check-only and does not promise auto-repair.
- The CSP narrative matches the current hash-based page policies and separately states GitHub Pages HTTP delivery limits.
- Dated history remains visibly historical; no date-only freshness edits.

### GOV-2: Make shared-file promotion evidence-led

Owner: dedicated shared-platform PM with sibling-specific Workers. Scope: proposal and regression design first; implementation of `sync-foundation-files.py` only after selecting the intended shared-source model. Keep site-owned analytics modules, domains, branding, and route data protected.

Acceptance:

- Divergent clean content cannot become canonical merely because its Git timestamp is newer.
- A planned write identifies the chosen source commit, source hash, target baseline, intended shared changes, and required per-site checks.
- Dry-run, dirty-input protection, ambiguous-content stop behavior, and explicit target paths remain.
- Each affected site passes its own generated-output and browser checks before a cross-site promotion is accepted.

### GOV-3: Align required release controls with observed settings

Owner: release PM; Architect retains responsibility for any owner-level GitHub setting changes. Scope: check names, review policy, workflow coverage, and post-deploy proof. Use the Architect's current GitHub evidence instead of old observed-settings paragraphs.

Acceptance:

- Desired settings and observed settings are separately recorded with retrieval date.
- Required jobs run on every applicable PR and cannot remain pending due to path filtering.
- The site's final deployed provenance equals the validated main commit.
- Browser/static coverage and live verification retain FAIL/BLOCKED/NOT RUN distinctions.

## Integration and evidence review

The PM independently read the consequential source after workers reported findings: `app.js` hardcodes the OverKill search dialog name, placeholder, and suggestions; its index loader passes `pages` through without adapting section/branch into category. The category builder therefore exposes All/Page, not the intended useful taxonomy. The PM also confirmed Scheduling Wizard authoring placeholders and `sw.js` chaining successful network delivery to successful cache persistence. These are confirmed source defects, not simply recommendations based on visual taste.

The Architect independently observed the cross-brand search copy and the homepage Toolbox CTA routing to Ecosystem in the live browser. The Infrastructure Worker additionally reproduced the storage-failure service-worker branch in a Node VM. Independent source review corroborates the control-flow cause; it does not turn a VM probe into browser storage-quota testing.

Remaining live uncertainties belong to the Architect's final assessment; this PM does not infer user-testing outcomes, external GPT behavior, owner analytics settings, or current accessibility conformance from source alone.

## Implementation handoff proposed to the Architect

The following is a proposed execution decomposition for a separate implementation PM. It is not a record of completed repair. The current assessment workers remain read-only. Priorities reflect visitor harm and the ability to verify a focused change; cosmetic redesign and new capabilities remain later proposals.

| Package | Priority and owner | Exclusive source ownership | Concrete outcome | Acceptance and review gate |
|---|---|---|---|---|
| FIX-1: Truthful discovery and route repair | P1; content Worker | `index.html`, relevant `toolbox/**/index.html`, `showcase/index.html`, `docs/audit/tool-ette-verification-2026-09-04.md`, `scripts/audit-tool-ette-promises.py` and its focused test | Toolbox CTA reaches Toolbox; branch/cross-tool links cannot bypass withdrawn destinations; Scheduling Wizard uses an honest unavailable concept brief; branch descriptions match their actual detail pages; unsupported concierge/portfolio promises removed or qualified. | Preserve names, taxonomy, publication state and approved design. No invented GPT destinations, experience claims or testimonials. Prove known withdrawn destination links absent from every discovery entry point; check homepage destination and no scaffold strings; verify page promises against existing authored evidence. |
| FIX-2: Glee search adapter and catalog-aware results | P1; search Worker | `assets/js/app.js`, `assets/js/glee-site-enhancements.js`, `scripts/build-search-index.py`, focused search QA files | Glee name, prompt and examples appear in modal/full search; section/branch fields produce useful category labels; unavailable/beta state is visible before click; index body excludes repeated site chrome and authored placeholders; inline search synchronizes its URL and fulfills its stated keyboard behavior. | Preserve sibling behavior through explicit brand adapter logic; do not copy changed shared files to siblings. Tests cover Glee and the existing sibling branch paths, modal/inline empty and no-result states, keyboard/focus, index-load failure, useful category results, URL refresh/back/forward, and representative task queries. Regenerate the index only during serialized integration. |
| FIX-3: Best-effort navigation cache writes | P2; resilience Worker | `sw.js`, focused resilience/control-flow tests | Successful online navigation returns its fresh response even when cache storage fails; define bounded handling of query variations without breaking bookmarked search. | Add failure reproduction before repair. Test successful fetch plus rejected caches.open/cache.put, network failure with warm cache, true offline fallback, external request exclusion, and query behavior. Coordinate with PR #22 first because it also changes the service-worker precache URL; carry no duplicate offline URL fix. |
| FIX-4: Browser and release evidence | P1/P2; QA Worker after FIX-1/2 integration | Browser QA runners and selected workflow gates, governed by a PM-approved exact file list | Tests exercise actual search labels/schema, publication routing, late script errors and image decode/loading; delivered provenance and representative routes receive live confirmation. | Deliberately break a relevant behavior in an isolated fixture and show the test fails. Native/browser-unavailable paths report BLOCKED rather than success. Current viewport checks are not relabeled as full accessibility or asset proof. Do not mutate branch protection or approval counts. |
| FIX-5: Agent runbook and policy reconciliation | P2; governance Worker | Files in GOV-1, plus `docs/release-governance.md` if directed | Active instructions match implemented scripts, strict CSP, check-only generation, and actual versus desired release settings. | Verify every active command path; preserve historical audit dates and explicit deferrals; avoid AGENTS sync-circuit edits unless all affected repositories are included. |
| FIX-6: Deliberate public artifact contents | P1 security-contact reliability/P2 content hygiene; release Worker | `.github/workflows/pages.yml`, focused artifact manifest tests, `docs/deployment.md`; coordinate exact shared workflow ownership with FIX-4 | Preserve the intended `.well-known/security.txt` through artifact upload; prevent accidental template/brand-registry/internal-governance publishing. | Test the assembled and uploaded/downloaded artifact, not only the source folder. Assert required public files and security.txt; assert excluded internal development surfaces; preserve live routes and release-provenance SHA. After an authorized deployment, fetch security.txt and representative public pages. Do not describe public repository content as a secret exposure. |
| FIX-7: Visible text contrast in actual themes | P1 accessibility; focused CSS Worker | `.glee-main` rules within `assets/css/theme.css`, focused computed-style browser checks | Homepage light eyebrow and dark hero heading meet applicable contrast thresholds on their real composite backgrounds. | Architect live measurements found about 1.097:1 light eyebrow and 2.607:1 dark heading despite passing static guards. Verify foreground/background alpha composition in both forced and system light/dark modes after transitions settle; check ordinary text at 4.5:1 and large text at 3:1. Preserve brand and sibling scopes; inspect active PR #22 CSS diff before work; reserve stylesheet ownership so search badges cannot collide. |
| FIX-8: Repair the malformed Neighborly Bazaar illustration | P2; asset Worker or FIX-1 owner | `assets/img/tool-ettes/05f-neighborly-bazaar-illustration.svg`, focused SVG parse check | Escape the text's literal less-than sign so the existing illustration decodes. | Infrastructure Worker observed a completed broken image on this route at all eight widths; XML parsing isolates unescaped `<30 min` at line 67. All other 42 inspected SVGs parse. Require XML parse success plus real-browser `img.decode()`; preserve the drawing and text content. Add parse coverage so an existing but invalid SVG cannot pass the asset gate again. |

FIX-2's owner also owns the small PM-05 consent-status repair in `glee-site-enhancements.js`, so no parallel Worker should edit that file. Treat it as a separate acceptance case: the consent read, visible state, script-loading decision and disable flag must agree after reload, while analytics remains off by default. Browser tests should block or stub actual measurement requests rather than submitting test usage. This is an existing-choice display defect, not evidence that the fresh default sends analytics without consent.

### Sequencing and shared-output lock

1. Recheck main, PR #22 and all worktrees. Preserve the baseline evidence in this assessment. Rebase implementation plans on the actual chosen clean commit; do not claim the September 5 baseline is still current after another task merges.
2. FIX-1 and FIX-2 can run in parallel with exclusive file ownership. Their Workers must not regenerate shared artifacts independently. FIX-3 and FIX-7 can run only after checking the active PR #22 diff and choosing how to avoid overlapping `sw.js` or shared stylesheet edits. FIX-7 owns any stylesheet change requested by another Worker.
3. The implementation PM integrates source changes and then serially regenerates search index, portfolio stats if affected, search again if stats changed copy, and CSS/offline versions last. Generated files are integration-owned, including `assets/data/search-index.json`, derived HTML tokens, and cache version.
4. FIX-4 validates the integrated result; FIX-5 can run independently against stable observed behavior. FIX-6 and FIX-4 need one workflow owner or sequential integration because they may both edit the release workflow. Any test exposing a new issue returns to its source owner before the final rerun.
5. Run required local checks and relevant live preview journeys. Keep the final diff focused and reviewable. A PR, merge, GitHub setting change or deployment has its own explicit scope; these proposals do not claim any was performed.

### Explicitly retain as proposals

- Framework migration, CSS purge/minification pipeline, broad visual redesign, reordered taxonomy, global sibling-file synchronization, and public timestamp/FAQ rollout.
- New authored tool capabilities, restored withdrawn GPT links, launch-state upgrades, externally hosted GPT configuration audits, and analytics-property changes.
- New hosting/security-header platform. Current page-level CSP already provides meaningful enforced controls; residual HTTP delivery limits require a separately justified hosting decision.

## Artifact validation

- PASS: production tracked diff remained empty during the PM review; assessment output is isolated in the dated allowed directories.
- PASS: `git diff --check` returned no errors at the PM checkpoint.
- PASS: core worker claims above received direct source review; command-path and foundation-hash evidence are retained as machine-readable JSON.
- WARN: browser/runtime proof has a narrower scope than complete accessibility conformance or external GPT availability.
- PASS with findings: Infrastructure Worker completed all 63 routes at eight widths in real Chromium (504 combinations) with third parties blocked and service workers disabled. HTTP responses and CSS loaded, and there was no horizontal overflow or first-party page/request failure. Eight completed broken-image observations are the same malformed Neighborly Bazaar SVG across widths. Thirty-one pending lazy-image rows are timing uncertainty, not demonstrated broken images. An incorrectly targeted search-button probe and offscreen deferred Mermaid counts are excluded from conclusions.
- NOT RUN by this PM: external GPT execution, owner analytics configuration, deployment, dependency installs, or production mutation. The Architect and worker reports identify their own completed checks separately.

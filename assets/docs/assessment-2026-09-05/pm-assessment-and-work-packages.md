# Assessment management and implementation work packages

**Date:** 2026-09-05  
**Role:** Project Manager reporting to the Project Architect  
**Assessed commit:** `5da805785d47f9bc29058b07d2a5467da32a1573`  
**Scope:** Glee-fullyTools local website clone, coordinated with the Architect's live and GitHub checks  
**Execution state:** Assessment and delegated implementation designs only. No production changes, commits, pushes, issues, settings changes, or deployment performed by this assessment team.

## Decision

Keep the static architecture and invest first in behavioral correctness, truthful discovery, and executable maintenance guidance. The repository has useful release machinery, a coherent catalog contract, and passing structural checks. A framework migration would not solve the observed offline module, inconsistent search, crawler policy, or publication-copy problems.

The current site is usable online. The comprehensive assessment is **NOT READY for an unqualified resilience or end-to-end quality claim**: live browser reproduction shows contrast failures, offline search failure and a service-worker registration race despite passing deterministic gates. This is not a recommendation to take the public site down.

The first implementation wave should repair theme contrast, offline regressions, saved analytics preference display, search consistency, and crawler policy. Public-copy corrections and artifact hygiene follow in separately owned packages. Preserve the 42 authored Tool-ettes and the 1 Live / 24 Beta / 17 Unavailable publication register unless the owner supplies new destination evidence.

## Actual delegation performed

| Role | Agent | Assigned work | Deliverables |
|---|---|---|---|
| Project Architect | Root thread | Live HTTP, browser UX, GitHub state, recommendations and integration decision | Architect report and browser/GitHub evidence |
| Project Manager | `assessment_pm` | Review evidence, resolve overlap, preserve decisions, sequence improvements | This report and command-inventory evidence |
| Infrastructure Worker | `assessment_pm/infrastructure_worker` | Local infrastructure, security, CI, dependency and deterministic QA audit | `infrastructure-security-audit.md` and `infrastructure-patch-plan.md` |
| Content Worker | `assessment_pm/content_worker` | All-page source inventory, content, catalog, SEO and semantic accessibility | `content-catalog-seo-audit.md` and `content-patch-plan.md` |

The PM issued a second concrete assignment to each Worker to design the improvements after their audit, with exact files, conceptual diffs, regression checks, dependencies and rollback. Those delegated tasks produce execution-ready designs rather than silently changing production during an assessment. The Architect decides the accepted implementation set. External Copilot/Replit dispatch and publication have not occurred.

## Evidence and boundaries

| Consequential claim | Tier | Evidence | Consequence if false | Next check |
|---|---|---|---|---|
| The source contains 63 production HTML files, 60 indexed pages and 42 Tool-ettes with 1/24/17 states | Confirmed | `content-source-inventory.json`; independent source scan and current contract | Work packages could alter the wrong public inventory | Rerun inventory after the accepted patches |
| Eleven deterministic site checks pass, including structure, internal links, generated output and CSP | Confirmed | `infrastructure-local-checks.json`; 63 files, 2,690 internal links and no reported broken links | Assessment might confuse structural health with live behavior | Repeat affected gates after integration |
| Delayed enhancement import misses service-worker registration | Confirmed | Architect live `interaction-browser.json`, test `SW after 2.5s module delay`; module exists but registration false | Offline feature may be unavailable to first-time visitors | Delayed-response test must pass after R1 |
| Offline dedicated search needs a module omitted from the worker cache | Confirmed | `sw.js:4`; `assets/js/app.js:1097`; interaction evidence records uncached module and stuck loading | Offline contract overstates functionality | Cold-resource-cache controlled offline test after R1 |
| Search categories, accent matching and URL synchronization differ between surfaces | Confirmed | `interaction-browser.json`; global accent query gets 8 results, inline gets 1; categories All/Page; changed query leaves stale URL | Visitor cannot reproduce or accurately filter a result set | Shared behavioral cases after R2 |
| Passing static checks proves all external GPT destinations work | Unknown, and not a supported claim | `docs/suite-promise.md:35` and publication register distinguish configured links from external behavior | Misrepresents third-party tools and owner work | Separate destination verification if publication states change |
| Public protection settings match the older one-review requirement | Confirmed mismatch | Architect's current GitHub evidence reports zero required approvals, whereas `docs/release-governance.md:29` requires one | A written release gate may be assumed enforceable when it is not | Architect's explicit governance reconciliation package |
| A redesign or bundler would materially improve this site | Proposal without supporting comparative measurement | No measured need in this audit | Adds migration cost without resolving demonstrated faults | Defer; measure an accepted performance hypothesis first |

Evidence paths in this section are under `assets/audit/assessment-2026-09-05/` unless a repository path is shown. Browser results are representative behavior tests, not assistive-technology certification. The all-page static inventory is broader than manual rendered review. Refer to the Architect report for the exact live route/viewport matrix.

## PM findings: active operational guidance drift

### GOV-01: current quick references direct maintainers to missing or retired commands

- **Severity:** P2. **Tier:** Confirmed. **Domain:** Maintainability and change safety.
- **Evidence:** `.agents/agent-skills.md:49-53` directs feed and icon regeneration through historical paths and claims automatic post-merge rebuilding. Its quick reference at lines 129-137 includes retired mutators. `replit.md:235-259` repeats missing paths and invokes `python3 scripts/post-merge.sh`, despite that file being a Bash script. `scripts/README.md:70-80` explicitly retires multiple referenced mutators. The working hook at `scripts/post-merge.sh:13-29` runs check-only generation and validation.
- **Reproduction:** Compare the active quick-reference sections against filesystem existence and `scripts/README.md`. `pm-guidance-command-inventory.json` records 45 script references, 15 references to missing paths across 10 unique paths, and one shell script invoked with Python. `scripts/audit-assets.py` exists as a compatibility shim, so it is not counted as missing.
- **Impact:** A maintainer following the advertised sequence gets errors or may resurrect retired migration scripts to work around them. A misleading rebuild claim can leave generated content stale. This is distinct from historical audit paragraphs retaining their original commands.
- **Smallest remedy:** Replace active quick references with links to the canonical current deployment sequence, describe post-merge as check-only, use `bash scripts/post-merge.sh`, and label compatibility/archive tools precisely. Keep dated historical audit material unchanged. Do not revive or relocate retired mutators.

### GOV-02: roadmap and security decision text describe already completed hardening as future work

- **Severity:** P2. **Tier:** Confirmed. **Domain:** Architecture records and prioritization.
- **Evidence:** `docs/roadmap.md:23-28` still lists removal of script `unsafe-inline` and addition of Organization `sameAs` as next work. `scripts/csp.py:118-127` already emits hash-based scripts with `script-src-attr 'none'`; `index.html:111-118` already contains the social links. `docs/adr/0004-enforced-csp-headers.md:69-75` says script inline permission remains required and ties future hashes to server rendering, contradicting the working static hash approach. `docs/release-governance.md:44-49` lists four desired checks while line 89 still says three.
- **Reproduction:** Read those passages next to generated homepage CSP and Organization JSON-LD; no network inference is needed for the source mismatch.
- **Impact:** A future agent can propose unnecessary work or weaken the existing CSP to conform to stale instructions. Stale check counts obscure the difference between desired policy and current GitHub enforcement.
- **Smallest remedy:** Mark completed roadmap work as shipped with supporting evidence; add an explicit ADR amendment recording the current static hash policy and preserving the prior dated decision. Point policy examples to the generator rather than maintaining another copied CSP. Reconcile desired and observed release settings without claiming settings were changed.

## Prioritized implementation sequence

P1 means a demonstrated user-facing contract failure or high-impact discovery obstruction; P2 means material correctness, maintenance or performance improvement; P3 means optional optimization. No confirmed emergency P0 issue was identified by this PM's local/static work.

| Package | Priority | Outcome | Main owner | Dependencies |
|---|---|---|---|---|
| R0 | Prerequisite | Freeze the implementation base and resolve overlap with active PR #22 | Architect/PM | Read latest main and PR head; preserve active work |
| R10 | P1 | Restore readable theme combinations and CTA contrast | Theme Worker | R0; shared CSS integration with PR #22 |
| R11 | P1 | Saved analytics preference and displayed state agree | Runtime Worker | R0; serialize with R1/R2 module changes |
| R1 | P1 | Offline enhancement dependency and registration timing work reliably | Runtime Worker | R0; coordinate same module with R2 |
| R2 | P1 | One search contract across dialog and dedicated page | Search Worker | R0; serialize module integration with R1 |
| R3 | P1/P2 | Search crawlers can retrieve required rendering assets | Discovery Worker | Independent of runtime; review artifact exposure with R5 |
| R4 | P2 | Public routes, helper copy and metadata match the publication contract | Catalog Worker | R0 for HTML foundation; R2 if exposing states in search |
| R5 | P2 | Published artifact contains intended visitor assets and routes | Release Worker | Verify any deliberate downloads; retain repository source art |
| R6 | P2 | QA suite catches the demonstrated gaps and works on supported machines | QA Worker | R1/R2 tests land with fixes; standalone path fix independent |
| R7 | P2 | Current operating guidance describes executable commands and current policy | Documentation Worker | Final R1-R6 contracts and Architect governance decision |
| R8 | P2/P3 | Reduce favicon installation cost using existing approved art | Asset Worker | Measure baseline, inspect existing small icons; no new image pipeline |
| R9 | P3 | Improve visitor orientation through observed, measured refinements | UX Worker | Architect visual findings and owner design choices |

Effort is intentionally expressed as patch boundaries and acceptance criteria rather than unsupported calendar estimates. R1/R2 are medium-risk shared behavior changes; write failure reproductions first. R3 and localized R4 copy changes are low risk but can affect discovery, so verify exact resulting policy and routes. R5 is medium risk because exclusion mistakes can break public assets. R7 is a localized documentation reconciliation, not a governance redesign.

### Secondary queue and finding coverage

The first wave is intentionally bounded. The supporting plans also retain these distinct follow-ons:

| Follow-on | Evidence | Disposition and boundary |
|---|---|---|
| Report provenance/output controls | INF-05 | P2; separate from R6 path fix. Add optional report destinations/no-report and truthful capture identity without rewriting historical files |
| Immutable CI inputs and least privilege | INF-07 | P2 policy proposal; current major-tag policy is intentional. Change policy and its tests together only when accepted; do not upgrade dependencies implicitly |
| Fragment-aware links | INF-09 | P2 gate improvement, P3 observed holding-page footer fix; separate local fragment validity from external reachability |
| Optional Node QA engine alignment | INF-10 | P3 owner support decision; static site itself needs no Node runtime |
| Significant-change sitemap/Legal dates | C-07 / CD-4 | P2; derive dates from evidenced content changes, never a blanket audit-date refresh |
| Maintained 49-entry feed | C-07 / CD-4 | Separate reviewed feed preview; existing owner-approved maintenance boundary remains |
| Explicit state extraction and schema representation | C-04/C-08 / CD-3 | P2 design before code. Agree one authoritative state source and search interface; valid schema syntax alone does not prove available software or rich-result eligibility |
| Owner-supplied tool proof pilot | CD-5 | Optional advancement; cannot be manufactured from this public clone |

Shared `scripts/resilience-qa.py` work in R1 and R3 also needs one writer or sequential integration. A crawler-policy test can use an existing separate fixture module to keep the first runtime repair small. The PM should not combine every queue item into one large corrective commit.

### R0: integration contract

Root verified open PR #22 for the compact locale menu foundation, on `codex/regional-locale-menu-foundation`. Its head was changing during assessment. Before patching shared HTML, CSS, JavaScript or foundation sync, re-read the current PR diff and choose one explicit base. Do not cherry-pick, merge or overwrite that work merely because it overlaps this plan. Use one isolated task branch/worktree per independent package. The PM grants a single writer for each shared file at any moment.

The assessment scope is this repository. A shared-runtime repair may need equivalent sibling follow-up, but this does not authorize cross-repository edits. If a proposed change structurally edits AGENTS sections 1-5, stop that package at design review or separately obtain a scope covering the required sibling sync circuit. R7 can largely avoid this by correcting site-specific quick references and linking canonical documentation.

### R10: readable theme and CTA combinations

- **Owned files:** `assets/css/theme.css`, focused browser contrast regression coverage, and generated CSS/cache references owned by the integrator.
- **Confirmed evidence:** Architect `contrast-browser.json` spans OS light/dark crossed with stored auto/light/dark. Homepage eyebrow is 1.10:1 in light mode at 12.8px/400; dark hero H1 is 2.61:1 at 51.2px/700; primary CTA endpoints are 3.51/3.55:1 at 15.2px/600; light secondary CTA is 3.78:1. Normal text needs 4.5:1 and the large heading needs 3:1. `home-scrolled-dark.png`, inspected by this PM, shows mixed pale page surfaces/dark cards and nearly invisible Sparkle/section text in OS-dark auto. Static strict contrast PASS did not test these composited combinations.
- **Patch:** Repair actual foreground/background token assignments in Glee scope, including pseudo-element paper surfaces, inherited opacity, CTA gradient foreground and auto-mode Sparkle. Keep the approved palette and warm visual identity. Do not hardcode a blanket new theme or fix pinned dark while leaving OS-auto dark broken.
- **Acceptance:** All six OS/stored combinations render readable headings, eyebrow, prose, CTA normal/hover/focus states, Sparkle, nav/search, cards and footer on homepage plus representative branch/leaf/search pages. Measure composited colors, including alpha/pseudo-element backgrounds. Use the proper normal/large text thresholds, keyboard focus visibility and browser screenshots. Re-run existing static checks as supplementary coverage. Do not represent sampled measurements as complete WCAG certification.

### R11: saved analytics state

- **Owned files:** `assets/js/glee-site-enhancements.js` and focused consent-state reload tests; `legal/index.html` only if a supported status fallback change is needed.
- **Evidence:** Infrastructure INF-03 demonstrates that a persisted granted preference loads analytics at module line 44 while the legal status remains its default off text. The current consent interaction changes status, but boot does not.
- **Patch:** Separate preference reading, status rendering and side effects. Render the stored state on boot; update rendering after changes. Do not turn analytics on just to render a label. Coordinate one writer with R1/R2.
- **Acceptance:** Absent, denied, granted, invalid and inaccessible local storage all produce truthful labels and the intended request behavior. A granted preference survives reload with an on label; denied/default produce no analytics request; revocation disables future events. Attach live/browser evidence to confirm the VM reproduction.

### R1: offline module and registration lifecycle

- **Owned files:** `assets/js/glee-site-enhancements.js`, `sw.js`, focused resilience regression tests and `scripts/resilience-qa.py` as needed. Generated cache identity is produced by `scripts/sync-css-version.py`.
- **Patch:** Register immediately when `document.readyState` is complete, otherwise register once on load. Include the same-origin enhancement module in the intentional precache. Avoid broad runtime caching of all requests. Derive the updated cache identity through the existing synchronizer.
- **Acceptance:** Delay module response past load and observe registration; verify module membership in the active cache; disable ordinary HTTP cache, warm only documented routes, switch offline, reopen dedicated search and get results; verify uncached-route fallback and old-cache cleanup. Default analytics remains off and cross-origin responses remain uncached.
- **Detailed delegated design:** `infrastructure-patch-plan.md`.

### R2: consistent Glee-fully search

- **Owned files:** `assets/js/app.js`, `assets/js/glee-site-enhancements.js`, `search/index.html`, focused browser/client regressions. Modify the search-index schema only if the actual accepted design requires it.
- **Patch:** Preserve the current shared-runtime/brand-adapter architecture. Reuse one normalization and matching contract, consume the actual `section` field, synchronize the query URL as documented, and apply Glee labels to the global dialog. Retain no-JavaScript routing and error handling.
- **Acceptance:** `resume` and `résumé` agree between surfaces; query entry updates the share URL; reload and browser back/forward restore the intended state; category labels come from real sections; keyboard selection, Escape and focus restoration work; unavailable result pages are not presented as live launch offers. Empty/no-match/index-failure states are legible. Re-run R1 offline cases after integrating the shared module.
- **Rollback:** Revert the accepted runtime patch and regenerate shell identity; do not manually splice old generated cache tokens.

### R3: crawler access

- **Owned files:** `robots.txt` and a focused policy fixture/test if justified.
- **Patch:** Replace blanket `/assets/` crawl denial with specific protection for nonvisitor directories while allowing required CSS, JavaScript, images and search data. Preserve the owner's distinct training/search bot policy.
- **Acceptance:** Explicit user-agent/path cases prove Googlebot can fetch theme CSS, app module, icons and rendered content resources; private/editorial artifact routes remain disallowed as intended; GPTBot policy remains unchanged. Robots exclusion is never represented as access control. Live retrieval after a future release is separate from source checks.
- **Detailed delegated design:** `content-patch-plan.md`.

### R4: catalog truth and routing

- **Owned files:** Exact affected homepage/toolbox/Tool-ette HTML, `showcase/index.html`, authoritative publication documentation only where semantics change, the promise auditor and source tests where necessary.
- **Patch:** Correct the homepage full-Toolbox CTA route; align Identity Known's hub summary with its actual recognition tools; remove contradictory ChatGPT launch helper text from unavailable pages. Review SoftwareApplication/Offer claims against actual publication availability. Qualify unsupported rich-result claims rather than fabricating reviews or ratings. Retain authored names, taxonomy, branch order and beta status.
- **Acceptance:** All 63 pages remain structurally valid, 60 indexed routes and 42 authored leaves remain unless explicitly approved otherwise, 1/24/17 states remain, unavailable pages have no launch CTA or conflicting helper copy, route labels match destinations, generated index agrees with the resulting source. Do not silently revive the retired feed generator; feed maintenance remains a separately scoped owner decision.
- **Detailed delegated design:** `content-patch-plan.md`.

### R5: intentional public artifact

- **Owned files:** `.github/workflows/pages.yml`, possibly a focused artifact manifest/check script, `docs/deployment.md`.
- **Patch:** Inspect the existing artifact builder and exclude development templates, agent packages, internal governance and unused source-only material from deployment where they are not visitor dependencies. Prefer an explicit reviewed artifact policy. Preserve all source art in Git; this is packaging, not asset deletion. Preserve public downloads and all referenced resource paths.
- **Acceptance:** Build a candidate artifact without deploying; compare route and dependency inventory against all HTML/CSS/JS/manifest/service-worker references; all 63 intended HTML surfaces and required same-origin resources remain; token templates/agent instructions are absent; custom domain and release provenance remain. Run link and browser checks against the candidate artifact itself, not only the larger repository checkout.

### R6: trustworthy QA and portability

- **Owned files:** Focused audit path handling, corresponding test module, selected test steps in `.github/workflows/validate.yml`/`pages.yml`, behavioral runners touched by R1/R2.
- **Patch:** Normalize repository/report paths consistently around macOS temporary-directory symlinks. Keep the expected relative-path behavior rather than loosening the test to accept any path. Expand CI coverage to include the audit module or justified discovery set. Test actual user behavior and asset dependencies, not only source markers.
- **Acceptance:** Full unit discovery passes on macOS and the supported CI environment; output resolves within the expected report root; no reports overwrite unrelated historical evidence; existing selected tests remain green; intentionally broken offline module membership/search schema causes its new regression test to fail.
- **Detailed delegated design:** `infrastructure-patch-plan.md`.

### R7: documentation and governance reconciliation

- **Owned files:** `.agents/agent-skills.md`, current operational portions of `replit.md`, `scripts/README.md`, `docs/roadmap.md`, explicit amendment to ADR-0004 and release policy text as selected by Architect.
- **Patch:** Resolve GOV-01/GOV-02 using current source evidence; distinguish historical paragraphs from instructions to run now. Link `docs/deployment.md` as the release-command owner. Record observed approval/check settings separately from desired policy. Do not change GitHub settings as a side effect of a documentation task.
- **Acceptance:** Every command in active quick references resolves to an active tool or explicitly labeled compatibility entry point; shell tools use a shell; no current instruction presents retired mutators as routine; post-merge is described as check-only; roadmap completed items match source evidence; policy examples do not imply header delivery unavailable on GitHub Pages. `git diff --check` passes, and existing historical audit wording remains intact.

### R8/R9: measured improvements after correctness

The infrastructure inventory reports a 2,101,324-byte favicon SVG in the precache. Inspect existing approved icon alternatives and actual transfer/cache cost, then choose the smallest compatible existing asset or narrowly approved optimization. Do not add an image build pipeline or regenerate brand artwork merely to satisfy a byte target. Acceptance includes visual inspection of the icon, manifest/HTML reference checks and offline install regression coverage.

The Architect owns final UI recommendations from rendered evidence. Treat longer-term task-first browsing, status badges on discovery cards, diagram density and mobile reading rhythm as targeted design proposals. Use a before/after visitor task and a bounded sample to justify expansion. No blanket branch homogenization or brand rewrite is part of this plan.

## Shared-file ownership and generation order

1. Architect selects the implementation base and accepted scope after reviewing PR #22.
2. Runtime owner integrates R1, R2 and R11 sequentially in `glee-site-enhancements.js`; independent Workers may prepare patches, but only one writes that file.
3. Catalog owner performs source HTML changes. CSS changes remain in the required Glee or justified shared scope; no page-local style blocks.
4. Integration owner regenerates affected outputs with active tooling. Use the current deployment contract: search index, portfolio stats, rebuild search if stats changed page copy, CSP generation if inline policy inputs changed, then CSS/offline version synchronization last. Inspect actual tool contracts before invoking mutators.
5. Re-run check-only validation and targeted behavioral tests once on the final combined tree. Generated outputs are not independent worker-owned hand edits.
6. Build and test the candidate publication artifact. A future release then follows the reviewed protected-branch route and exact-commit Pages workflow, followed by live smoke evidence.

No Worker should claim a complete package because its isolated unit test passed while another package changed the same module. The PM checks the final integrated behavior and records which source SHA each result proves. The Architect intends to dispatch a persistent implementation PM task in an isolated worktree after reviewing this report; its thread identity and authorized scope belong in the Architect decision, not an invented dispatch claim here.

## Ready-to-dispatch management prompt

> Act as Project Manager for the accepted subset of R0-R11 in `assets/docs/assessment-2026-09-05/pm-assessment-and-work-packages.md`. Read the Architect decision and both Worker audit/patch-plan reports. Recheck main, worktree cleanliness and PR #22 before creating isolated implementation branches. Preserve unrelated work, taxonomy, owner publication states and deferred design decisions. Assign exactly one writer per file, put medium-risk regression reproductions before fixes, and have Workers use existing active generators. Implement only the accepted packages. Review diffs and integrated browser behavior against the acceptance criteria, then prepare a reviewable release summary with evidence and open questions. Do not infer authority to change sibling repositories, external GPTs, hosting, branch-protection settings, dependencies, or publish merely from this prompt.

Copilot can receive an isolated code/test package after the Architect selects that execution route. Replit is suitable for a scoped preview/design package with the same baseline, branch and ownership rules. Neither tool is needed simply to demonstrate delegation: the two Workers have already received and completed the assessment/design assignments in this team.

## Decisions deliberately preserved

`docs/suite-promise.md:206-221` retains the Active lifecycle, bespoke branch layouts, split portfolio copy, deferred visible update dates, deferred authored FAQ schema, no-build/minification posture, and source butterfly art. Existing Keep exploring trays and slim branch badges are resolved work. This plan does not turn those choices into defects. External GPT behavior, Google Analytics property retention, search-console acceptance and full assistive-technology validation remain separate checks with their own evidence requirements.

The historical OverKill-Hill thread is precedent for the requested management model, not evidence of this repository's implementation state. The Architect reports that the requested prior thread was unavailable on this host; this assessment therefore relies on the current clone, current public site and current accessible GitHub state.


## Translation-transition addendum and R12

**Checked:** 2026-09-05 after the owner's translation-cleanup steering. This addendum supersedes the earlier active-PR assumption for future implementation. GitHub API confirms PR #22 merged at `2026-09-05T17:27:53Z`, from head `4b400403700dafa61470a891390c070081c3a356` into merge commit `9b4ade05dbe6f8c755f20c2e7bc2e19b03da1b47`. The local assessment checkout and its remote-tracking ref still identify `5da8057`; this PM did not update them. The remote comparison contains 63 HTML cache-reference changes plus `assets/css/theme.css` and `sw.js`; `assets/js/app.js` is unchanged. Rebase or recreate future implementation work from the current selected main before testing, preserving this report's original evidence identity.

The Architect's completed cleanup and verification are recorded in [`translation-transition-review.md`](translation-transition-review.md): exactly five ignored Finder files and one old bytecode file removed, five empty obsolete roots removed, all active packages preserved, and 60 translation/page-sync tests passed. No runtime cleanup was justified or performed.

An implementation app task was not visible at this recheck. A prepared worktree alone is not evidence that a PM or Worker is executing. No new app task was created by this PM.

### R12 scope: clean the translation transition without deleting current support

**Priority:** P2 maintenance and future integration design. **Default disposition:** retain current support, clean only proven residue, and replace false site assumptions through the agreed shared-runtime interface. This is not a translation launch or a reason to alter public language inventory.

**Confirmed current distinctions:**

- Five exact-pair skills are active under `.agents/skills/language-mediation/okhp3-translation-en-us-{de-de,en-uk,es-es,es-mx,fr-fr}/`. Their dictionaries, voice profiles, examples, tests, evals and historical review records are useful authored assets. The `en-uk` package's actual target locale is `en-GB`; package names and locale identifiers must not be conflated.
- `.agents/skills/okhp3-i18n-page-sync/` and `.github/workflows/i18n-page-sync.yml` are current. The workflow runs Python read-only drift detection, then names the appropriate translation skill for human/agent handoff. It never translates, calls a drafting API, adopts a baseline, or publishes. It therefore fits the newer skills/Python/Actions approach.
- The exact check `python3 .agents/skills/okhp3-i18n-page-sync/scripts/i18n-page-sync.py --root . --mode check --format json` returns exit 0 with `configured: false`. No `i18n/sync.config.json` exists. This is an explicit supported no-op, not a failed rollout or proof of translated pages. Do not create a config merely to make that output look more complete.
- The current remote tree at `9b4ade05` is untruncated and contains no locale page roots, no i18n config/ledger, and no locale-specific search index. A production HTML search finds no language switcher markup or localized `lang`/hreflang surface in this clone. There is no evidence here of an abandoned published Glee translation to delete.
- PR #22 intentionally improves `.lang-switch-menu` width, wrapping, scrolling and compact-header placement in the shared stylesheet. The JavaScript disclosure is conditional on matching markup. These are current shared capabilities, dormant on this English-only Glee site, and must not be labeled dead code solely because Glee has no menu.
- A targeted search of current runtime, workflows, scripts, operational docs and active family content found no active references to the old top-level `.agents/skills/okhp3-translation-en-us-*` locations. Historical provenance/examples are not migration debris. The Architect separately owns any exact ignored-only ghost-directory cleanup and its evidence; this package does not repeat or broaden that deletion.

### Exact remaining assumptions to correct or isolate

| Location | Current assumption | Safe disposition |
|---|---|---|
| `assets/js/app.js:323-325` and `assets/css/theme.css:606-610` | Four pilot routes and `/fr/`, `/de/`, `/es/` describe the consuming site | Replace site-specific comments with conditional shared-capability documentation when that shared file is next edited; retain disclosure behavior and merged CSS |
| `assets/js/app.js:586-589` | French is reviewed/indexable and `/assets/data/search-index.fr.json` exists; German/Spanish are noindex drafts | This is a sibling pilot assumption, not current Glee truth. Move publication/index selection behind an explicit consuming-site configuration or adapter with English-only Glee defaults; do not delete other consumers' support |
| `assets/js/app.js:590-592` | Splitting `lang` to the first subtag is enough to choose catalog/search fallback | Preserve exact region tags when configuring future targets so `es-ES` and `es-MX`, or `en-US` and `en-GB`, cannot silently share the wrong catalog. Configure any English fallback explicitly and label it accurately |
| Dormant workflow/config state | A passing i18n job might be mistaken for translation coverage | Keep the explicit configured/no-config result in reporting and document the boundary. No green job may be described as reviewed multilingual content |

The current English page does not request the missing French index because its language is English. The hardcoded map is a latent integration hazard and stale shared assumption, not a demonstrated broken English visitor path. No broad shared-runtime removal is justified.

### Ownership and implementation shape

1. **Residue cleanup:** Architect owns the exact ignored-only ghost paths already inventoried. Retain the five active family packages and page-sync skill. Do not delete historical benchmark folders, dictionaries, or old source examples because their names refer to earlier approaches. Do not remove tracked files without a replacement/reference check.
2. **Current-state documentation:** R7 owner can add a short source-backed statement that Glee remains English-only, five pair skills are available, and page sync is unconfigured. Link the canonical skill contract rather than inventing a parallel translation engine.
3. **Search interface:** R2 owner coordinates any change to shared `assets/js/app.js` with the Glee adapter. A future explicit interface can map full BCP-47 locale tags to reviewed catalog URLs plus an explicit fallback, with no fetch for an undeclared locale index. Determine initialization order before coding because the Glee module is dynamically imported after shared runtime initialization; a configuration written too late merely moves the bug. Keep one source of locale publication truth.
4. **Shared foundation:** `scripts/sync-foundation-files.py:5-8` declares app.js/theme.css/Mermaid byte-identical across siblings. Its apply/commit modes write other repositories. This Glee-only package must not run those modes or silently fork shared constants. Design the adapter/configuration interface first, preserve current consumer compatibility, and queue any actual sibling migration in its separately authorized scope.
5. **Future pilot activation:** Only after the owner selects target pairs and routes, configure `i18n/sync.config.json` with a small explicit `in_scope_routes` set. Route detected missing/stale pages to the exact-pair skill, retain en-US source/owner voice, validate reviewable drafts, and adopt only a confirmed result using `--mode adopt --routes`. Language quality, publication approval, locale search generation and navigation promotion remain separate from hash-baseline adoption. Do not automatically create all 60 translated pages or invent destination availability.

### Acceptance and preservation tests

- Before/after tree inventory proves the five family packages and page-sync package are unchanged by residue cleanup; any removed entries match the Architect's exact ignored-file evidence. No authored translation or published route is deleted.
- The five pair test suites and page-sync tests pass using their actual filenames. A configured-false check still exits 0 without writes. The Architect recorded 50/50 pair tests and 10/10 detector tests passing in the cleanup addendum; this PM independently ran only the read-only current-state check.
- Page-sync fixtures retain missing/stale detection, out-of-scope exclusion, needs-baseline/orphan reporting and explicit adoption. Tests must not redefine its green result as translation quality or publication approval.
- If R2 changes locale routing, exercise `en-US` default with no locale config, `fr-FR` with a declared existing index, undeclared French with a truthful default/fallback, distinct `es-ES`/`es-MX`, and `en-US`/`en-GB`. Assert requested URLs, no silent region collapse and meaningful failed-index behavior. Do not create fake production index files to satisfy a test.
- Glee pages with no switcher remain unchanged; synthetic existing-consumer disclosure fixtures verify Enter/Escape/focus, 320px menu fit, long localized labels and scrollability while preserving PR #22 behavior. Sibling production behavior remains a separately tested integration boundary.
- Cleanup does not change the English 63/60/42 inventory. A future approved locale pilot updates inventory/search/sitemap/hreflang/canonical contracts deliberately and keeps unreviewed drafts outside published discovery.
- Run applicable generated-output and offline checks after runtime changes; R1 must cache any new required same-origin adapter/config asset. Do not hand-edit search JSON, CSP hashes or worker cache identity.

**Ready-to-dispatch R12 prompt:**

> Inspect the translation-transition addendum against current main after PR #22. Preserve the five active exact-pair skills, the current read-only page-sync detector/workflow, all authored dictionaries/reviews/examples, and the merged shared locale-menu foundation. Do not treat configured:false as failure or enable multilingual publishing. Review the Architect's completed ignored-only cleanup evidence without repeating broader deletion. Correct current Glee documentation and propose a consuming-site search-locale interface with exact BCP-47 tags, explicit catalog availability and truthful fallback. Coordinate with R2 and shared-foundation ownership before changing app.js. Test no-config behavior, regional separation, current disclosure behavior and missing-index failures. Do not run cross-repository sync write modes, adopt a translation baseline, publish locale pages, create tasks or change external GPTs without the separately accepted scope.

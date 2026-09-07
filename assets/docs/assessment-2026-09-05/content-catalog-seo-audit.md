# Content, catalog, discovery, and source accessibility assessment

Date: 2026-09-05. Assessed local commit: `5da805785d47f9bc29058b07d2a5467da32a1573`. Role: content Worker reporting to the assessment Project Manager. This is an assessment and implementation design, not an applied production change.

The catalog has a substantial authored foundation: 42 distinct Tool-ettes, seven meaningful branches, coherent internal routing, unique page descriptions, and a conservative publication register. The next useful advance is to make discovery, public claims, and machine-readable representations agree with that register. More pages or a framework migration would not solve the defects below.

## Coverage and evidence limits

- Automated source coverage: every one of the 63 validator-scoped production HTML files, excluding the same development/dependency directories as the validator. Captured metadata, canonical URLs, headings, main text, CTA labels/targets, JSON-LD, IDs, image-alt presence, and local fragment references.
- Manual review: all 42 Tool-ette descriptions and heading outlines; deeper reading of homepage, Toolbox, Search, Showcase, Legal, Treasured Finds, Healthy Bee-ing, Identity Known, bLinkIn Tuner, Self Fixer, and Moody Log. The audit did not read every paragraph of all 63 pages as a human visitor.
- Structural results are source evidence, not WCAG certification, screen-reader testing, external GPT behavior, or Google indexing evidence. Main-text word counts include some diagram source and hidden source text; do not treat them as rendered reading times.
- Shared browser findings are attributed to the Architect's live `interaction-browser.json`. This Worker did not operate an additional browser or probe external GPTs.
- Read governance: full `AGENTS.md`, `replit.md`, `.agents/agent-skills.md`, `docs/suite-promise.md`, historical required audit/TODO references, and `docs/audit/tool-ette-verification-2026-09-04.md`. Applied skill: `.agents/skills/okhp3-static-site-quality-gate/SKILL.md`.
- PR #22, `codex/regional-locale-menu-foundation`, is active parallel work reported by the Architect. Shared HTML/runtime patches must inspect its latest diff and integration state first.

Machine artifacts:

- `assets/audit/assessment-2026-09-05/content-source-inventory.json`: complete per-page extraction, with source lines.
- `assets/audit/assessment-2026-09-05/content-findings-evidence.json`: counts, exact 15-file unavailable-helper list, crawler examples, schema and freshness summaries, check outcomes.
- `assets/audit/assessment-2026-09-05/interaction-browser.json`: Architect's live interaction evidence.

## What currently holds up

| Check | Outcome | Meaning |
|---|---|---|
| Production HTML inventory | PASS: 63 | Includes 404, offline, and holding pages |
| Search generation | PASS: 60, current | `python3 scripts/build-search-index.py --check`, exit 0 |
| Leaf publication surface | PASS: 1 live, 24 beta, 17 unavailable | `python3 scripts/audit-tool-ette-promises.py`, exit 0; matches current contract |
| Titles and descriptions | PASS: 63 unique of each | Presence and uniqueness, not a judgment that every claim is accurate |
| JSON-LD parsing | PASS: 0 parse errors | Does not establish search feature eligibility |
| Images missing an alt attribute | PASS: 0 found | Alt accuracy and decorative treatment still need rendered/contextual review |
| Duplicate IDs | PASS: 0 found | Source IDs only |
| Same-site fragment references | FAIL: 1 missing target | `under-construction.html:233` uses `#why`; that page has no matching ID. Infrastructure INF-09 owns the repair. |
| Tool-ette navigation | PASS: all 42 carry authored leaf content and Keep exploring structure | Preserves parent/sibling/Toolbox/Search paths |
| Inventory reconciliation | PASS: 60 sitemap URLs, 49 feed entries | Feed is intentionally branches plus leaves, not the entire site |

The initial independent fragment scan incorrectly resolved relative links against the canonical URL. The holding page canonical points to the homepage, where `#why` exists, masking the broken fragment. A corrected complete scan resolves against the requested page route and confirms exactly one defect, `under-construction.html:233`. This correction is recorded in the machine evidence.

The 17 unavailable entries are deliberate public discovery pages, not automatically deletion or noindex candidates. Six branch beta badges and existing leaf construction overlays are intentional status treatments. External destination availability was not retested here; yesterday's HTTP results remain dated evidence only.

## Findings

Severity: P1 is a high-impact visitor/discovery problem to address in the next correction cycle; P2 is a material inconsistency or maintenance defect; P3 is focused editorial polish or an unmeasured opportunity. No P0 finding was established in this workstream.

### C-01 | P1 | Confirmed configuration, inferred search impact | Required assets blocked from general crawlers

**Evidence:** `robots.txt:3` declares `Disallow: /assets/`. All production styles, scripts, images, and the search data are beneath that path. The recorded standard-library robot-policy checks return false for Googlebot requesting `/assets/css/theme.css`, `/assets/js/app.js`, and the shared social card. The homepage itself is allowed.

**Reproduction:** inspect `robots.txt`; evaluate these URLs using `urllib.robotparser.RobotFileParser` with user agent `Googlebot`. No Search Console access is needed to establish the rule. Actual crawling/indexing loss remains unmeasured.

**Impact:** compliant general crawlers cannot fetch the CSS, JavaScript, and imagery needed to understand the rendered site. Google explicitly says blocked JavaScript cannot be rendered. [Google JavaScript SEO basics](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics).

**Smallest remedy:** replace the blanket asset restriction with named internal-artifact exclusions while retaining the separate GPTBot block and OAI-SearchBot/ChatGPT-User choices. Required assets stay crawlable. Test representative bots and URLs rather than assuming HTML `index, follow` overrides robots rules. Robots policy is not a privacy boundary; deployment exclusions remain the control for internal files.

### C-02 | P1 | Confirmed source and live behavior | Search surfaces disagree on identity, categories, and shareable state

**Evidence:** `assets/js/app.js:721` names the dialog Search OverKill Hill; `assets/js/app.js:730` prompts Search the Forge. `scripts/build-search-index.py:273` emits `section`, while `assets/js/glee-site-enhancements.js:98` and `:105` consume `category` with Page fallback. The adapter reads `q` at `:89` but its input listener at `:109` only renders results. It also implements a separate all-term substring matcher from the shared weighted engine.

**Live reproduction from the Architect:** open `/search/?q=resume`, type another query, inspect address bar and category buttons. `interaction-browser.json` records categories All/Page and an unchanged `?q=resume` after results change. Global search for accented resume text yielded 8 results; dedicated search yielded 1. The earlier completely stuck online Loading index issue is fixed by the present adapter and should not be reported as the current online defect.

**Impact:** visitors cannot rely on a copied search URL representing the results they see, meaningful branch/category filters disappear, and the same query produces materially different experiences. The dialog's accessible identity is another brand.

**Smallest remedy:** one Glee adapter over the shared search API, with explicit `section` mapping, consistent query normalization, Glee labels, URL update/back-forward support, and semantic lists/links retained. The PM owns the consolidated search work package to avoid conflicting runtime owners. Offline adapter failure is separately owned by infrastructure.

### C-03 | P2 | Confirmed | Unavailable pages retain launch-success wording

**Evidence:** 15 of the 17 unavailable Tool-ettes retain the sentence beginning Opens in ChatGPT in their primary helper copy even though the launch CTA was withdrawn. Example: `toolbox/01-discovered-careers/01e-blinkin-tuner/index.html:302`; its hero says ChatGPT destination pending immediately above. The exact 15 paths and lines are in `content-findings-evidence.json` under `unavailable_launch_helper`.

**Reproduction:** compare that list against the publication register; search those files for `Opens in ChatGPT`. Read the pending/unavailable hero and its next paragraph.

**Impact:** visitors are told both that no destination exists and that the tool opens. A correct disabled/pending CTA does not remove conflicting nearby instructions.

**Smallest remedy:** change only the 15 orphaned launch-helper paragraphs to state that the page describes intended use and the destination is unavailable or awaiting confirmation. Preserve specific pending-versus-misrouted wording, all authored descriptions, all 17 routes, and the 1/24/17 publication counts. Do not supply substitute GPT links.

### C-04 | P2 | Confirmed source mismatch, proposed representation | Search and schema omit publication truth

**Evidence:** `scripts/build-search-index.py:273` returns no publication-state field; dedicated results at `assets/js/glee-site-enhancements.js:101` show title and description only. All 42 Tool-ettes, including all 17 unavailable entries, contain `SoftwareApplication` plus `isAccessibleForFree: true` and a zero-price Offer. Example: `toolbox/07-identity-known/07g-self-fixer/index.html:94` and `:102`. Descriptions on unavailable pages still read as present-tense product capability claims.

**Reproduction:** inspect those source objects and query an unavailable tool in Search. The JSON evidence records 42 application nodes, 42 zero-price offers, and 17 unavailable applications still carrying offers.

**Impact:** visitors arriving through search and machine consumers receive a stronger availability/offer impression than the human publication register permits. Being able to read a free catalog page is not the same claim as a currently available free external application. Whether any destination requires payment or an account was not tested here.

**Smallest remedy:** carry explicit state into generated search data and result labels; keep all intended discovery URLs. For unavailable entries, consider describing the catalog page with WebPage/About or another accurately supported relationship and remove unsupported transactional offers. A SoftwareApplication type by itself is not invalid merely because the application is unavailable; the issue is the unsupported offer/availability representation. For available/beta entries, retain only owner-supported application claims. Schema change is a designed follow-on with validator alignment, not a request to fabricate review scores or new availability evidence.

### C-05 | P2 | Confirmed | Two high-level routes misdescribe their destinations

**Evidence:** `index.html:227` labels its link Explore the full toolbox but targets `ecosystem/`. `toolbox/index.html:404` describes Identity Known as stories, journaling, and meaning-making, while `toolbox/07-identity-known/index.html:225` onward presents a name-that-thing recognition hub with animal, architecture, scenery, screenshot, motif, craft, and object helpers.

**Reproduction:** follow the homepage primary CTA and compare the seventh Toolbox card with the actual branch H1/intro and its seven Tool-ettes.

**Impact:** the first catalog action takes a visitor to a large relationship map; the wrong branch description can route reflective-journaling visitors to recognition tools and hide the branch from people seeking identification.

**Smallest remedy:** point the existing toolbox-labeled homepage CTA to `/toolbox/`; use one concise recognition-oriented sentence for Identity Known. Keep route names, ordering, seven-branch taxonomy, and bespoke layouts. Clarify that the Toolbox hero's external Open the Toolbox button opens ChatGPT, distinct from browsing the website.

### C-06 | P2 | Confirmed | Showcase claims exceed current implementation and evidence

**Evidence:** `showcase/index.html:444` through `:462` claims application schema makes the 42 entries eligible for Google rich results, says no package.json exists, fixes app.js at 829 lines, and names a Ko-fi overlay dependency. The current repository has package metadata for optional QA, a longer shared runtime plus the Glee module, and outbound-only Ko-fi. The zero-review application nodes do not meet Google's required rating-or-review property. `:423` claims results under 50 ms without a benchmark linked to that measurement; source scoring weights also differ from the surrounding prose. The public hub does not establish a canonical always-current external ecosystem or verified behavior of every GPT.

**Reproduction:** read the architecture and structured-data cards; compare `package.json`, `assets/js/glee-site-enhancements.js`, search scoring at `assets/js/app.js:621`, and the 42 schema nodes. Google's software app documentation requires a rating or review in addition to other required properties. [Google SoftwareApplication documentation](https://developers.google.com/search/docs/appearance/structured-data/software-app).

**Impact:** a page presented as a portfolio proof undermines credibility with claims that are disproved by its own source or lack measurement. Rich-result eligibility and ordinary schema validity are different checks.

**Smallest remedy:** preserve the owner's static-site rationale and replace factual absolutes with current, bounded statements. Remove an unsupported speed number instead of manufacturing a benchmark. Say optional QA packages are separate from the no-build website runtime. Name current outbound/opt-in dependencies accurately. Describe structured data as machine-readable catalog context without asserting rich-result eligibility. No fabricated ratings.

### C-07 | P2 | Confirmed timestamps, inferred freshness impact | Sitemap, feed, and legal review date lag substantive work

**Evidence:** 58 sitemap entries retain 2026-05-12, Showcase retains 2026-05-27, Arcade retains 2026-07-15. `feed.xml:7` and all 49 entries use 2026-05-03. `legal/index.html:410` says Last updated: 2025 despite new analytics, fonts, iframe, and retention wording recorded in the current tree. The September 4 verification report documents substantive CTA withdrawal/status changes to public Tool-ettes; `sitemap.xml:77` still dates Self Fixer to May 12.

**Reproduction:** parse `sitemap.xml` lastmod and `feed.xml` updated values, then compare the dated September publication reconciliation and current Legal source. A recent Git timestamp alone is not proof of a significant public change; the CTA/privacy differences supply that evidence.

**Impact:** the public update stream and metadata do not communicate actual editorial updates, while the legal review date makes recent operational statements look unreviewed. Google says lastmod should reflect significant content/link/schema changes and be accurate. [Google sitemap guidance](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap).

**Smallest remedy:** update demonstrably changed sitemap entries from a maintained significant-change source or omit optional lastmod where reliable dating is unavailable. Give Legal a truthful editorial review date. Feed repair remains a separate owner-authorized maintenance action under `docs/suite-promise.md`; do not run the archived generator or bump every date merely to make the site look fresh. A future maintained feed can carry status-sensitive summaries without changing its intentional 49-entry scope.

### C-08 | P2 | Confirmed check gap | Publication audit infers state but does not assert a visible state contract

**Evidence:** `scripts/audit-tool-ette-promises.py:84` infers unavailable when no launch URL exists and beta from the construction-overlay substring. At `:125`, the beta assertion rechecks the exact condition that produced beta; at `:127`, the unavailable assertion cannot establish that pending/unavailable prose exists. The final PASS claims every entry has an explicit state signal but the code never compares the Markdown register to the per-page state or requires a visitor-visible unavailable signal.

**Reproduction:** inspect `publication_state` and the loop conditions. A page with a unique H1, description, no CTA, and no visible unavailable wording is still classified unavailable and does not fail those checks. This is a missing regression guard; current counts are correct.

**Impact:** later edits can erase status copy or change the register without this check noticing. The release signal promises more than it tests.

**Smallest remedy:** add focused positive/negative fixtures for visible state presence and register parity, then validate an explicit per-page state representation against the authoritative inventory. Keep external reachability out of deterministic CI and preserve unavailable-over-beta precedence. Coordinate with C-04 so there is one state extraction contract.

### C-09 | P3 | Confirmed | Small editorial residue weakens precision

**Evidence:** `toolbox/07-identity-known/index.html:761` addresses the writer with Give people a tiny playbook rather than the visitor. `index.html:286` hardcodes GPT-5 intelligence despite no evidence here that all externally hosted GPTs share a model. Source copy across the site also retains many em dashes and occasional prohibited filler despite the current AGENTS guardrail.

**Impact:** template instructions appear as final copy; model-specific marketing drifts independently of external configurations. A blanket typography rewrite would produce broad churn disproportionate to the core findings.

**Smallest remedy:** replace the one editorial instruction with visitor-directed copy and remove the unverified model number. Apply the current language/voice rules to touched copy. Treat any site-wide style cleanup as a separate reviewed editorial task; do not rewrite deliberate historical audit prose or proper nouns automatically.

## Product advancement proposals

These are proposals, not measured defects or new release prerequisites.

1. Put a small amount of proof near a small number of ready destinations. Start with Neighborly Bazaar plus one owner-selected beta with useful evidence. Show what the visitor brings, a source-authored example of the output, account/platform dependencies when verified, and honest boundaries. Do not invent external GPT transcripts. This yields more user value than expanding the 42-page catalog while 17 destinations remain unavailable.
2. Make status visible before commitment: search result labels, optional counts per existing branch, and plain local versus ChatGPT CTA labels. Do not flatten the trunk/branch/Tool-ette taxonomy or redesign deferred branch indices.
3. Keep public purpose concise at the top, with detailed functions below. Current leaf source text ranges from 497 to 1,383 main-text words. This is a review opportunity, not proof of low conversion. Preserve distinctive examples; validate a shorter pilot with visitor tasks before propagating it.
4. For health, career salary, nutrition, and DIY claims, complete the existing owner-evidence gate before promoting status. Existing disclaimers are useful context but do not prove behavior. This is an application of the repository's own publication contract, not a new clinical or legal certification program.
5. Treat discovery as a joined system: crawl permissions, accurate landing descriptions, state-aware search, bounded schema, and meaningful freshness metadata. Do not chase FAQ rich results or fabricate Q&A; the owner explicitly deferred per-tool FAQ authoring.

## Release assessment and delegation

**Content/discovery decision: READY WITH WARNINGS for the existing static catalog, with P1 correction work queued.** This is not a whole-site release approval; infrastructure/browser gates and current PR reconciliation belong to the Architect. The generated catalog is current and one broken holding-page fragment is assigned to infrastructure, but search and crawler behavior deserve prompt correction.

Detailed file ownership, dependencies, acceptance, rollback, and executable Worker assignments are in `content-patch-plan.md`. No production files, dependencies, external applications, commits, or publication settings were changed by this Worker.

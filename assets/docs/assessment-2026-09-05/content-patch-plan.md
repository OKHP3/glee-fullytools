# Content and discovery improvement packages

Date: 2026-09-05. Base evidence: `5da805785d47f9bc29058b07d2a5467da32a1573`. This is delegated implementation design. No patch below has been applied. Read `content-catalog-seo-audit.md` for reproduction and impact.

The Architect owns scheduling and integration; the assessment PM owns acceptance and cross-package conflict control. Workers must inspect active PR #22 (`codex/regional-locale-menu-foundation`) and the current checkout before editing shared HTML, JavaScript, or generated data. Do not resurrect work already present on an active branch. Use one writer per file set. No direct main push, deployment, or external GPT configuration change is part of these packages.

## Work order

1. CD-1 crawler policy can run independently of HTML/runtime work.
2. CD-2 narrow copy corrections can proceed in one content branch once PR #22 overlap is mapped. The search package belongs to the PM and takes exclusive ownership of shared JavaScript during its work.
3. CD-3 state/schema contract follows search interface agreement and owner/editor agreement on representation. Complete the existing publication register validation before generating result labels.
4. CD-4 freshness work uses the meaningful content changes from CD-2/CD-3; feed maintenance remains a distinct decision under the existing contract.
5. CD-5 proof pilot requires external owner evidence and should not block corrections to already-known defects.

## CD-1: Make required assets crawlable

**Findings:** C-01. **Priority:** first correction cycle. **Owner:** crawler-policy Worker. **Exclusive files:** `robots.txt`; focused policy cases within the existing `scripts/resilience-qa.py` static/crawler checks or the repository's established test directory after inspecting its convention. Do not create a second unrelated validation framework.

Conceptual diff for the wildcard group:

```text
User-agent: *
Allow: /
Disallow: /assets/audit/
Disallow: /assets/docs/
Disallow: /assets/templates/
```

Replace the existing `/assets/` blanket disallow with these specific internal-artifact paths. Before selecting any additional exclusion, inspect the Pages artifact manifest and current public asset inventory. CSS, JavaScript, images, manifest dependencies, and generated public search/sparkle JSON remain allowed. Keep current GPTBot, OAI-SearchBot, ChatGPT-User, and sitemap declarations exactly as policy choices unless the owner changes them. Search engines do not require a robots disallow to keep an asset out of the HTML page inventory. Do not represent this change as a privacy fix or as proof of search-engine indexing.

Acceptance matrix, evaluated with representative full URLs and actual policy parsing:

| User agent | `/` and a Tool-ette page | `/assets/css/theme.css` | `/assets/js/app.js` and Glee module | `/assets/img/...` | `/assets/data/search-index.json` | `/assets/audit/...`, `/assets/docs/...`, `/assets/templates/...` |
|---|---|---|---|---|---|---|
| Googlebot | Allow | Allow | Allow | Allow | Allow | Disallow |
| Bingbot | Allow | Allow | Allow | Allow | Allow | Disallow |
| Generic crawler | Allow | Allow | Allow | Allow | Allow | Disallow |
| GPTBot | Disallow | Disallow | Disallow | Disallow | Disallow | Disallow |
| OAI-SearchBot | Preserve existing explicit Allow policy | Allow | Allow | Allow | Allow | Preserve explicit group semantics |
| ChatGPT-User | Preserve existing explicit Allow policy | Allow | Allow | Allow | Allow | Preserve explicit group semantics |

The last two named groups currently explicitly allow the entire site and do not inherit wildcard exclusions. Record that deliberate retained behavior. Real internal-content exclusion is controlled by the deployed artifact. If the owner wants those agents to inherit internal path restrictions too, that is an explicit policy refinement separate from preserving existing policy.

Run the existing resilience static check and standard validator/link checks. Publish smoke confirmation later must retrieve live robots.txt and verify the exact deployed policy. Rollback is the targeted patch reversal; no asset or catalog files change.

Worker prompt:

> Implement CD-1 only from this plan. Inspect current robots policy, deployment artifact exclusions, existing crawler tests, and PR overlap. Replace the broad asset crawl block with the named internal-artifact exclusions, preserving named bot groups and sitemap. Add focused representative allow/deny cases in the existing validation location. Run checks, show exact diff and policy matrix, and report what remains unverified live. Do not deploy, push, install dependencies, or change content inventory.

## CD-2: Correct public routing and factual copy

**Findings:** C-03, C-05, C-06, C-09. **Owner:** public-content Worker. **Exclusive files:** `index.html`, `toolbox/index.html`, `toolbox/07-identity-known/index.html`, `showcase/index.html`, and the exact 15 files in `content-findings-evidence.json.unavailable_launch_helper`. Derived output: `assets/data/search-index.json` after all authored changes. No other Tool-ette is in this package's edit scope.

Concrete edits:

- Homepage: change the toolbox-labeled hero destination to `/toolbox/`; remove the unverified GPT-5 claim without replacing it with a newer model name.
- Toolbox: describe Identity Known as recognizing animals, places, images, patterns, and objects. Suggested owner-voice-preserving wording: “Name the things that catch your eye. Explore animals, places, screenshots, patterns, and mystery objects with a focused helper.” Label its external hero CTA “Open the Toolbox in ChatGPT.” Keep the website browse links intact.
- Identity Known: replace the writer instruction in the getting-results section with a visitor instruction, for example “Bring a photo or description, add a little context, and say what you want to learn.” Do not rename the branch or reorder its leaves.
- Fifteen unavailable leaf helper paragraphs: replace only stale launch-success language. Suggested common baseline: “This page describes the intended tool. Its ChatGPT destination is not available yet; explore this branch for another helper.” Keep stronger existing owner-confirmation/unavailable messages where appropriate. Do not overwrite all paragraphs with one sentence if they carry useful preserved context.
- Showcase: reconcile package metadata, runtime/module structure, Ko-fi outbound behavior, opt-in analytics, actual schema meaning, and unsupported speed/always-current claims. Preserve the static-site rationale and named project story. Remove unverified precision instead of turning code-line counts into more generated metrics. Do not promise rich results, external GPT quality, or guaranteed performance.

This is a localized content pass, not the deferred branch redesign. Use a bounded idempotent AUTOGEN-marked transformation for repeated HTML edits if required by local governance; keep it in the established script location and scope it explicitly to the 15-path list. A second invocation must make no additional diff. Do not run broad archived mutators merely to normalize touched pages.

Acceptance:

- Exact expected files only; all URLs except the one corrected homepage target remain stable.
- All 17 unavailable entries remain unavailable; exactly 1 live and 24 beta remain.
- No unavailable hero helper promises an available launch. No replacement ChatGPT URLs supplied.
- Toolbox Identity Known copy matches its actual seven leaf domains.
- Showcase contains no disproved no-package.json or Ko-fi-overlay claim and no unmeasured numeric speed guarantee.
- Regenerated search index is current at 60 entries. Existing validation, links, CSP, and applicable browser checks pass.
- Read the corrected homepage, Toolbox, one unavailable leaf, and Showcase at mobile and desktop widths; check CTA text/destination and ensure paragraph replacements do not damage layout.

Rollback: revert authored copy and its generated index together. Keep unrelated locale work and current publication register intact.

Worker prompt:

> Implement CD-2 only, after inspecting current PR #22 overlap. Read the audit, exact 15-file JSON list, and repository governance. Make the defined routing/copy corrections without changing publication counts, external GPT URLs, taxonomy, or page layouts. Preserve useful owner prose. Rebuild only documented generated outputs required by the edits, run the relevant checks, and show reviewable diff plus browser observations. Do not publish or touch the search runtime owned by the PM.

## CD-3: Carry publication state through discovery and validate it

**Findings:** C-04 and C-08. **Owner:** catalog-contract Worker; joint interface review with the PM's search Worker. **Exclusive files after design review:** `scripts/audit-tool-ette-promises.py`, `scripts/build-search-index.py`, `scripts/validate-site.py`, publication-state regression tests in the established test location, `docs/suite-promise.md`, the 42 leaf HTML files only where an explicit state/schema representation is required, and the generated search index. Search rendering changes remain exclusively with the PM's search Worker.

Representation decision to settle before implementation: maintain the existing authoritative register with a stable machine-readable extraction, or introduce a small reviewed JSON catalog whose generated Markdown register replaces duplicated manual truth. Do not create a third independent status source. The JSON route is a proposal, not an automatic architecture mandate. No new dependency or website build framework is needed.

Proposed interface for generated search entries:

```json
{
  "url": "/toolbox/07-identity-known/07g-self-fixer/",
  "section": "Identity Known",
  "publicationState": "unavailable"
}
```

Preserve existing index fields and agree with the search owner whether `section` remains the category field or is mapped at the adapter boundary. Adding `publicationState` should be backward-compatible. Supporting pages and branch hubs require their own explicit non-leaf meaning or an omitted state, not guessed leaf status. Do not infer leaf state from substring presence alone.

Testable behavior:

- The authoritative register and 42 page states agree; invalid/missing/duplicate entries fail.
- An unavailable page with no visible unavailable/pending signal fails.
- A beta page without its intended beta signal fails.
- A placeholder launch URL fails even if other valid-looking anchors exist.
- A page with unavailable precedence cannot become live merely because a new non-placeholder CTA appears elsewhere in a sibling tray.
- Schema for a catalog page does not assert an unsupported purchasable/available application. Remove free offers from unavailable entries. Keep schema IDs and breadcrumb references valid after changing node type/relationships.
- Google-rich-result eligibility is a separate optional assessment. Missing genuine ratings must never be solved with invented reviews.
- Search consumes the new field and labels unavailable/beta/live clearly before navigation, retaining 60 discoverable pages.

Dependencies: first reconcile active locale work; then settle shared search field mapping; then update authoritative state representation, validation fixtures, and builder; then change source schema/state blocks; finally integrate search rendering and regenerate output. Refresh the corresponding suite contract mirrors only when definitions/counts actually change. Publication counts are not planned to change.

Acceptance: `audit-tool-ette-promises.py`, targeted negative fixtures, `build-search-index.py --check`, site validation, links, JSON-LD references, and representative search results all pass. Run schema validation on one available beta, one unavailable, and the live page. Whole-site rerun confirms no lost routes or false availability claims.

Rollback: restore source schema, state extractor, validator expectations, and index in one coherent revert. The old register must remain interpretable during rollback. Do not roll back independent copy corrections or locale work.

Worker prompt:

> Design and implement CD-3 only after the PM agrees the single state source and search interface. Preserve 42 leaves and the 1/24/17 register. Add failing regression cases for lost visible state and register drift, then make state-aware extraction/schema changes. Keep external GPT probes and behavioral claims out of CI. Coordinate exclusive file ownership with the search Worker, generate the index, run acceptance, and report any owner evidence still missing. No fabricated ratings, schema claims, external URLs, or publication.

## CD-4: Accurate change signals, with feed separated

**Findings:** C-07. **Owner:** editorial-maintenance Worker. **Files:** `sitemap.xml`, `legal/index.html`, existing sitemap maintenance support if present; generated search index after legal copy change. Conditional later feed scope: `feed.xml`, `scripts/archive/generate-feed.py` only for inspection, and an owner-approved active replacement generator if the owner chooses maintained feed behavior.

First perform a meaningful-change ledger from source history for the pages actually changed during the September publication/privacy work and the current correction packages. Do not use checkout mtime. Set only supportable lastmod values; omit optional values where reliable attribution is not available. Correct Legal's review date only after reading the current statements. This does not reopen the deferred visible per-page timestamp design across all content pages.

Feed gate: `docs/suite-promise.md` explicitly limits regeneration to owner-approved feed maintenance. Prepare a concrete current-vs-proposed 49-entry preview with summaries, state language, and dated changes. Do not execute an archived generator before inspecting its constants and validating its paths. The Architect can resolve the feed-specific authorization at review time; this is not a reason to halt independent crawler/copy/search fixes.

Acceptance: 60 sitemap URLs unchanged, valid XML, accurate date provenance, no future dates, no blanket run-date refresh; Legal date matches the actual review. If feed maintenance is approved, 49 entries remain, stable IDs remain, only materially changed entries receive new updated dates, and rerunning generation without source change is byte-identical.

Rollback: restore the sitemap or feed from the targeted change only. Do not erase historical audit artifacts. Include exact generated files in any revert.

Worker prompt:

> Implement the approved sitemap/Legal portion of CD-4 using significant-change evidence, not filesystem dates. Prepare the 49-entry feed preview separately and state the existing feed-maintenance authorization boundary. Preserve sitemap/feed membership and stable IDs. Run XML, links, and generated-index checks; include date provenance. Do not run archived feed mutators or publish without the required scope decision.

## CD-5: Owner-evidenced proof pilot

**Finding:** advancement proposal. **Owner:** owner/editor with a delegated evidence Worker. **Files:** one owner-selected Tool-ette page and its existing dated verification record; generated index after approved public copy. This package has no permission to inspect private GPT configurations automatically.

Collect an owner-approved example input/output, current destination identity, meaningful limitations, and platform/dependency details for Neighborly Bazaar or a selected beta. Use the existing seven-part verification contract. Compare visitor completion with the current page using a small scripted task, such as finding the right helper and explaining what to bring. Publish no private prompts, uploaded knowledge, or personal test data. Keep unavailable tools discoverable until the owner changes publication policy.

Acceptance: every added public capability sentence traces to supplied evidence; sample input is safe and illustrative; no unverified status promotion; the page has a clear local and external action. Do not claim conversion improvement without observation.

## Shared validation and integration rules

For authorized HTML edits: run the current documented generation/check sequence, typically the search builder, any relevant stat/CSS synchronizers only if their inputs changed, then `build-search-index.py --check`, `validate-site.py`, `check-links.py`, and targeted catalog/browser checks. If a pre-cached resource changes, coordinate the service-worker cache version with the infrastructure owner. Inspect the Pages workflow for the current enforced sequence rather than invoking archived script lists from historical guidance.

Before closing each package: inspect `git diff --check`, confirm exact owned files, record command exit codes and source/browser/live scope, and provide a concise changed/why/validation/remaining-evidence report. A passing source validator is not proof of external GPT behavior, live publication, search-engine indexing, or screen-reader conformance.

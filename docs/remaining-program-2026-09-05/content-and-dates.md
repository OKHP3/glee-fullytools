# Content and dates worker report — September 5, 2026

Baseline: `f5f33986e6ee287fb165c75e82ef01e5d3ed1f99`. Accepted implementation `8dea009c` is preserved. This report covers A14, residual A12/A13, all 38 advisory findings, A15 source dates, and the PM-assigned homepage image correction.

## Catalog truth and residual content

The 42 Tool-ette detail pages now describe canonical `WebPage` nodes instead of unverified applications. Names, canonical routes, breadcrumbs, descriptive images, publication states, and taxonomy are preserved. Unsupported operating-system/category assumptions, free access, zero-price offers, and illustration-as-screenshot properties were removed. No ratings or reviews were invented. There are still 1 live, 24 beta, and 17 unavailable entries.

Google’s application rich-result requirements include evidence the catalog does not have, so adding ratings to seek eligibility would be inappropriate. The site describes pages without promising a search appearance. The decision follows the current [Google software-app documentation](https://developers.google.com/search/docs/appearance/structured-data/software-app), [WebPage definition](https://schema.org/WebPage), and [screenshot definition](https://schema.org/screenshot).

Visible boundaries on all seven branch hubs and 42 detail pages explain intended use, unverified external behavior, and user-owned notes. Specific affirmative claims were also corrected: preconfigured instructions, recurring memory, automatic routing/synchronization, live app data, safety checklists, and rapid-result guarantees. The homepage no longer asserts GPT-5. Personal Librarian, Giftlist Helper, Lifestyle Wallboard, and branch descriptions no longer promise shared records. Human memory and journaling metaphors remain where they do not claim platform storage.

Care Check retains its unavailable state. Its unverified diagnosis, urgency scoring, triage, treatment, and photo-assessment claims were removed in favor of organizing notes and questions for qualified care. The existing emergency limitation remains. This change does not certify clinical safety. Legal now distinguishes the owner’s retention target from an unverified provider setting. Persona does not certify external routing or safeguards.

The Showcase now matches the static architecture and current source: shared runtime plus site adapter, optional npm QA dependencies, locally served Mermaid, consent-controlled analytics, outbound Ko-fi, shared search engine, artifact checks, and separate live verification. Unsupported fixed search size/timing, zero-cost/performance guarantees, fabricated package absence, rich-result eligibility, universally safe generators, and always-current maps were removed. Existing STAT markers remain for PM-owned synchronization.

Residual visible author instructions were removed from 13 pages with “Connect this Tool…” text and from the Palatably Profiled/Lifestyle Wallboard explanatory sections and short-start prompts. The existing promise audit gained focused author-instruction patterns; its `launch_urls` and `publication_state` contracts are unchanged. Identity Known remains a recognition branch, including its Organized Life sibling summary.

The approved new `scripts/check-catalog-claims.py` is read-only and standard-library only. It checks the current unverified catalog scope, canonical page identity, unsupported application properties, conceptual screenshots, malformed JSON-LD, and a substantive visible provider boundary. Its API permits an explicitly reviewed future application scope; the tests do not claim that every future product must forever use WebPage.

## Individual advisory dispositions

The 165-character description and 70-character title thresholds are local heuristics, not Google hard limits. Each description was reviewed for subject, current state, clarity, and claim accuracy, rather than mechanically truncated. Unflagged descriptions were retained except where they made a material storage/integration claim. [Google’s snippet guidance](https://developers.google.com/search/docs/appearance/snippet) describes device-dependent truncation and accurate page-specific descriptions.

All 38 original findings are corrected. Exact before/current values are recorded in `assets/audit/remaining-program-2026-09-05/content-advisory-dispositions.json`.

| # | Page | Original finding | Disposition and reason |
|---|---|---|---|
| 1 | `about/index.html` | Description is 191 chars (>165) | Corrected: Preserves the Glee/Jamie origin story while describing a catalog rather than promising friendship from every GPT. |
| 2 | `arcade/index.html` | Title is 74 chars (>70) | Corrected: Retains Arcade, Chai Chasers, and brand identity without repeated branding. |
| 3 | `arcade/index.html` | Description is 178 chars (>165) | Corrected: Keeps the game, characters, and visitor action; avoids an unsupported free-access assertion in the snippet. |
| 4 | `legal/index.html` | Description is 177 chars (>165) | Corrected: Names the actual legal topics and provider boundaries instead of repeating three full trademarks. |
| 5 | `persona/index.html` | Description is 189 chars (>165) | Corrected: Describes authored persona intent instead of claiming that this voice powers every external GPT. |
| 6 | `search/index.html` | Description is 174 chars (>165) | Corrected: Describes catalog search and publication labels rather than implying every result is an available GPT. |
| 7 | `showcase/index.html` | Title is 88 chars (>70) | Corrected: Keeps Showcase and the suite identity without repeating a case-study subtitle. |
| 8 | `showcase/index.html` | Description is 184 chars (>165) | Corrected: Names the actual architectural subjects without overclaiming results. |
| 9 | `toolbox/01-discovered-careers/01b-resume-customizer/index.html` | Description is 211 chars (>165) | Corrected: Keeps job-post comparison and resume drafting scope and identifies the beta listing. |
| 10 | `toolbox/01-discovered-careers/01e-blinkin-tuner/index.html` | Description is 204 chars (>165) | Corrected: Replaces a LinkedIn-profile interpretation with energizing work moments and the unavailable destination state. |
| 11 | `toolbox/01-discovered-careers/01f-career-seeker/index.html` | Description is 220 chars (>165) | Corrected: Keeps job-search planning and tracking scope and states the unavailable destination. |
| 12 | `toolbox/01-discovered-careers/index.html` | Description is 200 chars (>165) | Corrected: Replaces LinkedIn routing with the actual career reflection catalog scope and state visibility. |
| 13 | `toolbox/02-treasured-finds/02a-personal-librarian/index.html` | Description is 229 chars (>165) | Corrected: Preserves print/ebook/audio inventory and reading-progress scope; identifies the beta listing. |
| 14 | `toolbox/02-treasured-finds/02b-decor-detective/index.html` | Description is 220 chars (>165) | Corrected: Preserves room/bin/holiday/condition organization and identifies its proposed beta workflow. |
| 15 | `toolbox/02-treasured-finds/02c-present-hoarder/index.html` | Description is 189 chars (>165) | Corrected: Preserves purchased-gift/recipient/storage scope and identifies the beta listing. |
| 16 | `toolbox/02-treasured-finds/02d-scentinal-journal/index.html` | Description is 186 chars (>165) | Corrected: Preserves fragrance-note purpose and states destination unavailable. |
| 17 | `toolbox/02-treasured-finds/02e-spirited-journal/index.html` | Description is 202 chars (>165) | Corrected: Preserves stories behind possessions rather than suggesting a verified external journal; states unavailable. |
| 18 | `toolbox/02-treasured-finds/02f-supply-haus/index.html` | Description is 198 chars (>165) | Corrected: Preserves craft supplies, storage, and material scope; identifies beta. |
| 19 | `toolbox/02-treasured-finds/index.html` | Description is 202 chars (>165) | Corrected: Describes the branch as a catalog across its actual collection topics with publication states. |
| 20 | `toolbox/03-tasty-tracker/03b-menu-conductor/index.html` | Description is 203 chars (>165) | Corrected: Preserves meal-planning inputs and states destination unavailable. |
| 21 | `toolbox/04-travelers-guide/04b-itinerary-hacker/index.html` | Description is 178 chars (>165) | Corrected: Preserves routes, activities, and daily planning while identifying beta. |
| 22 | `toolbox/04-travelers-guide/04d-dreamland-journeys/index.html` | Description is 223 chars (>165) | Corrected: Preserves future-trip inspiration and wishlists while identifying beta. |
| 23 | `toolbox/04-travelers-guide/04e-memento-log/index.html` | Description is 209 chars (>165) | Corrected: Preserves travel stories/captions and makes user-owned saving explicit; identifies beta. |
| 24 | `toolbox/05-organized-life/05b-thrifty-spender/index.html` | Description is 175 chars (>165) | Corrected: Preserves spending categories and budget questions; identifies beta and limitations. |
| 25 | `toolbox/05-organized-life/05c-giftlist-helper/index.html` | Description is 182 chars (>165) | Corrected: Preserves gift planning and requires the user to bring their own records; identifies beta. |
| 26 | `toolbox/06-healthy-bee-ing/06a-care-check/index.html` | Description is 186 chars (>165) | Corrected: Removes unsupported triage/diagnosis benefits; describes the unavailable symptom-note concept. |
| 27 | `toolbox/06-healthy-bee-ing/06c-snappy-count/index.html` | Description is 208 chars (>165) | Corrected: Preserves meal-note and estimate concepts with uncertainty and unavailable destination. |
| 28 | `toolbox/06-healthy-bee-ing/06e-moody-log/index.html` | Description is 190 chars (>165) | Corrected: Preserves mood-reflection purpose, beta state, and external data-handling boundaries. |
| 29 | `toolbox/06-healthy-bee-ing/06f-maven-wise/index.html` | Description is 173 chars (>165) | Corrected: Preserves midlife/hormonal note-taking purpose and clinician-conversation limits; identifies beta. |
| 30 | `toolbox/06-healthy-bee-ing/index.html` | Description is 174 chars (>165) | Corrected: Describes the health branch catalog and requires checking each entry’s availability and limitations. |
| 31 | `toolbox/07-identity-known/07a-critter-spotter/index.html` | Description is 166 chars (>165) | Corrected: Preserves animal-identification purpose while identifying beta and independent checking. |
| 32 | `toolbox/07-identity-known/07b-roost-wrangler/index.html` | Description is 209 chars (>165) | Corrected: Preserves architecture/furniture/design-recognition scope and identifies beta. |
| 33 | `toolbox/07-identity-known/07c-sight-seeker/index.html` | Description is 175 chars (>165) | Corrected: Preserves scenery/landmark/sky concepts and states the unavailable destination. |
| 34 | `toolbox/07-identity-known/07d-snap-decoder/index.html` | Description is 168 chars (>165) | Corrected: Preserves screenshot/quote/error interpretation scope and states unavailable. |
| 35 | `toolbox/07-identity-known/07e-motif-muse/index.html` | Description is 168 chars (>165) | Corrected: Preserves colors/patterns/style-recognition scope and states unavailable. |
| 36 | `toolbox/07-identity-known/07f-maker-matcher/index.html` | Description is 178 chars (>165) | Corrected: Preserves craft/material/tool recognition scope and states unavailable with identification limits. |
| 37 | `toolbox/07-identity-known/index.html` | Description is 189 chars (>165) | Corrected: Aligns the branch with recognition rather than identity journaling, and makes availability/limits visible. |
| 38 | `under-construction.html` | In-page anchor href="#why" has no matching id | Corrected: Changes the local nonexistent #why fragment to the existing homepage section /#why. |

## Homepage image correction

The Experience Worker measured a 900-pixel-high viewport at widths 320, 390, 820, 980, 1024, and 1440. The Chai image started at y=1733.88, 1620.28, 1268.94, 1312.38, 1452.84, and 1140.34 respectively: below the fold in every measured case. Source evidence is `assets/audit/remaining-program-2026-09-05/experience-search-layout-final.json`.

The hero picture’s `sizes` now mirrors the existing CSS clamp rules and awkward-width override. Its 768/1024/1536 WebP candidates, eager loading, high priority, dimensions, and artwork remain. The below-fold Chai image is lazy/auto. The desktop sizes estimate is deliberately conservative where the container further caps width. Browser lazy thresholds may still fetch the Chai image near the viewport; this report does not promise a fixed byte saving. Experience’s post-change `experience-home-images-after.json` covers the same six widths at DPR 1 and 2 in fresh contexts. DPR 1 selected the 768 WebP at every width; at desktop this source is 100,926 bytes smaller than the previous 1536 WebP. DPR 2 retained the 1536 source at 1024/1440 widths and selected 768 at the four narrower widths. Rendered dimensions were unchanged. This is image-source evidence, not a guaranteed whole-page transfer or timing improvement.

## Content date evidence

Date history review and final ledger are recorded separately in `assets/audit/remaining-program-2026-09-05/date-review.json` and `date-history-review.json`. The date ledger includes each route, original date, reviewed date or omission, substantive reason, and normalized source hashes before PM generation. The 60 sitemap URLs remain unchanged. Legal’s visible update date is September 5, 2026; commit `184c8ab9fa785a2911d2183a9f2f0aba2bfd4e85` proves a substantive September 4 privacy rewrite already made the old “2025” label stale, and this package makes another actual disclosure correction.

The final sitemap has **60 unchanged URLs, 57 evidence-backed lastmod values, and 3 omitted optional values**. No unverified historical value is retained by default. Of the 57 dates, 54 pages received substantial source changes in this package; Toolbox also has the independently inspected prior September 5 rewrite. Three other dates were recovered from substantive Git diffs:

| Page | Selected date | Evidence and decision |
|---|---|---|
| Search | 2026-09-05 | `8dea009c`: corrected visible keyboard instructions and instant-result claim. |
| About | 2026-09-04 | `c479fc31`: corrected the public count of external destinations; `b2cae9d3` also clarified catalog intent and unverified GPT behavior that day. |
| Arcade | 2026-09-04 | `184c8ab9`: added the preview failure path and changed the consent disclosure. The later punctuation-only change does not establish a new date. |
| Contact | omitted | Latest 60 path commits yielded cache/head maintenance and a `noreferrer` change, without a reliably established significant content date. |
| Ecosystem | omitted | Same bounded history limitation; no current map-edit date was established. |
| Universe | omitted | Same bounded history limitation; no current relationship-content date was established. |

Historical date-only values use the calendar date in the selected commit’s recorded timestamp. The history evidence stores the full timestamp and substantive main-HTML diff; the date is not silently converted to a different UTC day. Shared asset tokens and generated STAT-only value changes were normalized for candidate selection, then candidates were assessed manually. Omission is preferable to an unsupported optional date; later evidence can restore one.

A date represents significant source content, structured data, or links. It does not represent a crawl, audit run, filesystem mtime, token refresh, copyright bump, or automatically the newest touching commit. That distinction follows [Google’s sitemap lastmod guidance](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap). All 42 schema corrections qualify as actual structured-data updates, not mass timestamp maintenance.

## Feed and ongoing date policy proposal — owner decision

`feed.xml` is unchanged. Its 49 catalog entries and feed-level timestamp still use `2026-05-03T00:00:00Z`; its content includes historical summaries that differ from current corrected pages. The last source touch alone does not establish those entry dates. SHA-256 before and after is `523e6160a6ed14e73c7da8a2171f70261df7f4edb40b1c989e2bc4359e7b9053`. No archived generator was run. This public historical feed remains a known limitation pending an explicit publishing decision.

Recommended policy: retain the existing catalog-feed identity and stable entry IDs, and make the next feed change an explicit, reviewed correction of catalog summaries and publication states. Preserve entries for unavailable concepts with truthful status text; do not silently imply they are launches. Assign an entry update timestamp only when that entry actually receives a significant correction. Preserve a known first-publication timestamp where supported; omit optional publication dates when unknown. A subsequent feed-level update should correspond to the reviewed feed revision. Atom distinguishes first publication from significant modification; see [RFC 4287 sections 4.2.9 and 4.2.15](https://www.rfc-editor.org/rfc/rfc4287).

Proposed maintenance design, not implemented: an owner-reviewed content-date register keyed by canonical route, with separate `published_at` (optional), `modified_at`, source commit, and change reason. A new active feed builder would read that register and approved summaries/states, preserve stable IDs, escape XML, and support a check-only freshness mode. Test unchanged-input idempotence, unavailable states, missing date evidence, stable IDs, and future-date rejection before adoption. Do not resurrect the archived generator. Keep sitemap updates, visible page review dates, and feed revisions distinct: a stylesheet token should update none of them.

Concrete owner decisions: approve the catalog-correction feed policy or choose a separately authored announcement feed; approve the active builder/register ownership before implementation; verify the analytics property’s actual retention setting; supply independently reviewed GPT access, pricing, memory, storage, integration, and safeguard evidence before restoring any such application claim. No external GPT certification or legal-compliance guarantee is inferred from local tests.

## Validation and integration boundary

Before source correction, six new tests ran with one failure exposing unsupported schema on all 42 current detail pages. A later eight-test run reproduced an unrecognized “Connect this Tool…” author instruction before the existing audit patterns were extended. Final focused runs and details are in `content-tests.json`; the claim checker has its own `content-claim-check.json`.

The worker’s per-page validator evidence covers 63 production pages, zero issues, zero warnings, and zero advisory findings. The link check reports 2,719 internal links, zero broken links, zero style issues, and 60 sitemap URLs. Eight content tests and nine prior visitor tests pass. The promise audit preserves 42/1/24/17 and all launch-destination invariants. Source freeze was explicitly sent to the PM after the six-page history review. Global generator/governance drift, rebuilt JSON, serialized CSP/cache versions, browser release acceptance, and exact-head integration remain PM responsibilities. No first-party runtime/CSS changes were made by this worker.

## Exact source ownership

Production HTML modified by this worker:

- `about/index.html`
- `arcade/index.html`
- `index.html`
- `legal/index.html`
- `persona/index.html`
- `search/index.html`
- `showcase/index.html`
- `toolbox/01-discovered-careers/01a-resume-builder/index.html`
- `toolbox/01-discovered-careers/01b-resume-customizer/index.html`
- `toolbox/01-discovered-careers/01c-career-fitness/index.html`
- `toolbox/01-discovered-careers/01d-letter-composer/index.html`
- `toolbox/01-discovered-careers/01e-blinkin-tuner/index.html`
- `toolbox/01-discovered-careers/01f-career-seeker/index.html`
- `toolbox/01-discovered-careers/index.html`
- `toolbox/02-treasured-finds/02a-personal-librarian/index.html`
- `toolbox/02-treasured-finds/02b-decor-detective/index.html`
- `toolbox/02-treasured-finds/02c-present-hoarder/index.html`
- `toolbox/02-treasured-finds/02d-scentinal-journal/index.html`
- `toolbox/02-treasured-finds/02e-spirited-journal/index.html`
- `toolbox/02-treasured-finds/02f-supply-haus/index.html`
- `toolbox/02-treasured-finds/02g-bag-nabbit/index.html`
- `toolbox/02-treasured-finds/index.html`
- `toolbox/03-tasty-tracker/03a-flavor-meister/index.html`
- `toolbox/03-tasty-tracker/03b-menu-conductor/index.html`
- `toolbox/03-tasty-tracker/03c-wishful-tastes/index.html`
- `toolbox/03-tasty-tracker/03d-pantry-shopper/index.html`
- `toolbox/03-tasty-tracker/03e-palatably-profiled/index.html`
- `toolbox/03-tasty-tracker/index.html`
- `toolbox/04-travelers-guide/04a-journey-diary/index.html`
- `toolbox/04-travelers-guide/04b-itinerary-hacker/index.html`
- `toolbox/04-travelers-guide/04c-detour-discoverer/index.html`
- `toolbox/04-travelers-guide/04d-dreamland-journeys/index.html`
- `toolbox/04-travelers-guide/04e-memento-log/index.html`
- `toolbox/04-travelers-guide/index.html`
- `toolbox/05-organized-life/05a-task-maestro/index.html`
- `toolbox/05-organized-life/05b-thrifty-spender/index.html`
- `toolbox/05-organized-life/05c-giftlist-helper/index.html`
- `toolbox/05-organized-life/05d-scheduling-wizard/index.html`
- `toolbox/05-organized-life/05e-lifestyle-wallboard/index.html`
- `toolbox/05-organized-life/05f-neighborly-bazaar/index.html`
- `toolbox/05-organized-life/index.html`
- `toolbox/06-healthy-bee-ing/06a-care-check/index.html`
- `toolbox/06-healthy-bee-ing/06b-calm-keep/index.html`
- `toolbox/06-healthy-bee-ing/06c-snappy-count/index.html`
- `toolbox/06-healthy-bee-ing/06d-medi-minder/index.html`
- `toolbox/06-healthy-bee-ing/06e-moody-log/index.html`
- `toolbox/06-healthy-bee-ing/06f-maven-wise/index.html`
- `toolbox/06-healthy-bee-ing/index.html`
- `toolbox/07-identity-known/07a-critter-spotter/index.html`
- `toolbox/07-identity-known/07b-roost-wrangler/index.html`
- `toolbox/07-identity-known/07c-sight-seeker/index.html`
- `toolbox/07-identity-known/07d-snap-decoder/index.html`
- `toolbox/07-identity-known/07e-motif-muse/index.html`
- `toolbox/07-identity-known/07f-maker-matcher/index.html`
- `toolbox/07-identity-known/07g-self-fixer/index.html`
- `toolbox/07-identity-known/index.html`
- `toolbox/index.html`
- `under-construction.html`

Additional worker source files:

- `sitemap.xml`
- `scripts/check-catalog-claims.py`
- `scripts/tests/test_content_claims.py`
- `scripts/audit-tool-ette-promises.py`

Worker evidence: the `content-*.json` and `date-*.json` files under `assets/audit/remaining-program-2026-09-05/`, plus this report. Shared generated assets, feed, CSS, runtime, workflows, other governance, commits, staging, installation, sibling repositories, and external writes are outside this worker’s mutations.

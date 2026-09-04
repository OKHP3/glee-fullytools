# Glee-fully Tools — Suite Promise

**Status:** Current contract  
**Last reviewed:** 2026-09-04  
**Owner:** Project owner  
**Current phase:** Active growth and refinement

This document is the source of truth for what Glee-fully Tools promises, what
the public site actually owns, how the catalog is counted, and what complete
means for this project. Other documents may provide shorter summaries, but
their vision, phase, and inventory language must agree with this contract.

## The promise

**Glee-fully Tools is a warm, structured public catalog and routing hub for a
growing family of domain-focused Custom GPT experiences.** It helps visitors
find a fitting helper for life, work, or wonder through a playful
trunk-to-branch-to-tool-ette system, clear descriptions, honest publication
states, and a consistent human-centered design language.

The public site promises discoverability, orientation, and truthful context. It
does not promise that every catalog entry has a working external GPT, that a
third-party GPT will remain available, or that an external GPT will produce a
particular result.

## Suite boundary

### The static public hub owns

- The Glee-fully brand story, public descriptions, taxonomy, and visible
  publication states.
- The static HTML pages, navigation, breadcrumbs, branch routing, internal
  search, metadata, sitemap, and Atom feed.
- The public presentation of links to externally hosted GPT experiences.
- The shared design language, plain-language orientation, and the project's
  documented governance and release checks.

### Externally hosted GPTs own

- The Custom GPT configuration, conversation behavior, instructions,
  knowledge, actions, model availability, account requirements, and outputs
  after a visitor leaves this site.
- Whether a ChatGPT destination remains available or changes behavior.
- Any data handling, retention, or account experience controlled by the
  third-party platform.

The public catalog may describe intended use based on the authored page, but
this repository does not audit the internal configuration or behavior of every
external GPT. A non-placeholder URL is evidence of a configured destination,
not proof that the destination is currently reachable or that its behavior
matches the page.

### Related properties are adjacent, not silently included

The Arcade is a separate public site surface within this repository, not a
Tool-ette. OverKill Hill P³™ and AskJamie™ are sibling properties in the wider
universe, not additional Glee-fully Tool-ettes. Development templates,
generated reports, and agent files are not public catalog entries.

## Vision-to-capability matrix

The status terms below are deliberately conservative:

- **Met** — repository evidence demonstrates the public capability.
- **Partially met** — an important public layer exists, but a boundary,
  dependency, or verification gap remains.
- **Unverified** — the goal is claimed or designed, but this repository does
  not contain enough evidence to confirm it.
- **Intentionally deferred** — the owner has kept it out of the current phase
  and recorded why.
- **Out of scope** — this project does not claim responsibility for it.

| Goal | Status | Repository evidence and limit |
|---|---|---|
| Make AI feel warm, approachable, and human-centered | Partially met | Homepage, About, Persona, and Showcase establish the voice and visitor promise. The behavior of external GPTs is not audited here. |
| Offer practical help across life, work, and wonder | Partially met | Seven branches and 42 authored Tool-ette pages cover career, collecting, food, travel, organization, wellness, and identity. Actual external-tool quality remains unverified. |
| Personalize help around a visitor's story and rhythm | Unverified | Page copy describes personalizable workflows, but no internal Custom GPT configuration audit is part of this repository. |
| Make the suite legible through trunk → branch → tool-ette | Met | `/toolbox/` is the trunk, seven branch hubs organize the catalog, and 42 Tool-ette pages provide the leaf-level destinations. |
| Give every visitor a clear way forward | Met | Shared navigation, visible breadcrumbs, branch routing, Keep exploring trays, internal search, sitemap, and feed are present in the public HTML. |
| Keep one coherent Glee-fully visual and editorial language | Met for the public hub; unverified for GPT internals | Shared `theme.css`, Persona page, templates, and agent guidance cover the public surface. External GPT voice is outside this audit. |
| Make the public hub practically accessible and inclusive | Partially met | Static checks cover landmarks, labels, focus, alt text, reduced motion, and tap-target patterns. Manual assistive-technology and live-browser confirmation remain separate work. |
| Remain useful when network conditions are imperfect | Partially met | `sw.js` provides a same-origin offline shell and fallback page; `docs/resilience.md` and the CI `resilience-qa` reports define and exercise representative online, offline, reconnect, browser, crawler, and blocked-dependency behavior. External GPTs, fonts, analytics, Ko-fi, and other third-party services remain intentionally outside that cache boundary. |
| Explain privacy and third-party boundaries plainly | Partially met | The Legal page and cache policy describe limitations and third-party services. Production privacy behavior and trust evidence still require dedicated review. |
| Be discoverable and publishable as a static site | Partially met | 60 indexable URLs, structured metadata, sitemap, feed, robots policy, GitHub Pages workflows, and validators are present. Owner-side live smoke testing and search-engine submission are not proven by this repository alone. |
| Stay maintainable as the suite grows | Met | `AGENTS.md`, `replit.md`, idempotent maintenance scripts, generated-file rules, CI validation, and the template library provide operating guardrails. |
| Define “complete” without implying perfection | Met | The completion contract below separates a complete public catalog from finished external GPT behavior and future owner choices. |

## Public inventory vocabulary

Counts refer to the repository state reviewed on 2026-09-04. A count is only
meaningful with its inclusion rule and owning source.

| Term | Count | Inclusion rule | Source of truth |
|---|---:|---|---|
| Production HTML files | 63 | Validator-scoped HTML outside `assets/`, `.agents/`, `.local/`, dependencies, and other excluded directories. Includes the 404, offline, and holding pages. | `scripts/validate-site.py` |
| Indexable public pages | 60 | The 60 public content URLs indexed by the site's search builder and listed in the sitemap. Excludes 404, offline, and holding pages. | `assets/data/search-index.json` and `sitemap.xml` |
| Supporting public pages | 10 | Homepage, Search, About, Contact, Legal, Persona, Ecosystem, Universe, Showcase, and Arcade. | Search index section labels |
| Toolbox hub | 1 | The top-level `/toolbox/` trunk page. | `toolbox/index.html` |
| Branch hubs | 7 | One public category page for each numbered branch. | `toolbox/*/index.html` |
| Tool-ettes | 42 | One authored leaf page for each catalog Tool-ette under a branch. | `toolbox/*/*/index.html` |
| Catalog pages | 50 | Toolbox hub + seven branch hubs + 42 Tool-ettes. This is a subset of the 60 indexable public pages. | Toolbox filesystem and sitemap |
| Structural templates | 9 files | Non-crawlable development files in `assets/templates/`; they are not extra pages, tools, or URLs. | `assets/templates/INDEX.md` |
| Atom feed entries | 49 | The seven branch hubs plus the 42 Tool-ettes. The feed is an updates stream, not a complete mirror of the 60-page search index. | Checked-in `feed.xml`; historical generator is archived under `scripts/archive/` |
| Tool-ettes with non-placeholder ChatGPT destinations | 25 | A Tool-ette page contains a reviewed, non-placeholder primary ChatGPT CTA after unavailable or misrouted destinations have been withdrawn. This does not prove external behavior. | Tool-ette HTML and `docs/audit/tool-ette-verification-2026-09-04.md` |

Do not call the 60 indexable pages “60 Tool-ettes,” the 49 feed entries “the
whole site,” or the nine templates “published pages.” The 42 Tool-ette count is
the catalog count; the 60-page count is the public indexable-page count.

## Publication state semantics

Publication state describes the relationship between a public catalog page and
its launch destination. It does not certify the third-party GPT itself.

| State | Meaning | Current count |
|---|---|---:|
| **Live** | Public Tool-ette page has no construction overlay and carries a reviewed, non-placeholder ChatGPT destination. This is a publication label, not a behavior certification. | 1 |
| **Beta** | Public Tool-ette page carries a construction overlay and a reviewed, non-placeholder ChatGPT destination. Visitors may read the page and try the destination, but the page is not presented as finished or behavior-verified. | 24 |
| **Construction** | Reserved for a page that is not ready for a public catalog claim. A future construction page should be excluded from the index and sitemap or clearly marked as non-public. | 0 |
| **Unavailable** | Public page exists for discovery, but its ChatGPT launch destination is missing, placeholder, or observed unavailable. It must not be described as a live GPT and has no launch CTA. | 17 |
| **Retired** | No longer an active catalog offering; remove it from the public inventory and preserve a deliberate redirect or archival record. | 0 |

State precedence is **retired → unavailable → beta → live**. A construction
overlay always prevents a page from being called live; a non-placeholder link
does not override the overlay. A placeholder link does not become valid merely
because the surrounding page passes HTML or link validation.

### Tool-ette publication register

This is the complete current register. The page path is included so a future
editor can verify the state without guessing from a marketing count.

| Branch | Tool-ette | State |
|---|---|---|
| Discovered Careers | Resume Builder | Beta |
| Discovered Careers | Resume Customizer | Beta |
| Discovered Careers | Career Fitness | Beta |
| Discovered Careers | Letter Composer | Beta |
| Discovered Careers | bLinkIn Tuner | Unavailable |
| Discovered Careers | Career Seeker | Unavailable |
| Treasured Finds | Personal Librarian | Beta |
| Treasured Finds | Decor Detective | Beta |
| Treasured Finds | Present Hoarder | Beta |
| Treasured Finds | Scentinal Journal | Unavailable |
| Treasured Finds | Spirited Journal | Unavailable |
| Treasured Finds | Supply Haus | Beta |
| Treasured Finds | Bag Nabbit | Beta |
| Tasty Tracker | Flavor Meister | Beta |
| Tasty Tracker | Menu Conductor | Unavailable |
| Tasty Tracker | Wishful Tastes | Beta |
| Tasty Tracker | Pantry Shopper | Unavailable |
| Tasty Tracker | Palatably Profiled | Beta |
| Traveler’s Guide | Journey Diary | Beta |
| Traveler’s Guide | Itinerary Hacker | Beta |
| Traveler’s Guide | Detour Discoverer | Unavailable |
| Traveler’s Guide | Dreamland Journeys | Beta |
| Traveler’s Guide | Memento Log | Beta |
| Organized Life | Task Maestro | Beta |
| Organized Life | Thrifty Spender | Beta |
| Organized Life | Giftlist Helper | Beta |
| Organized Life | Scheduling Wizard | Unavailable |
| Organized Life | Lifestyle Wallboard | Beta |
| Organized Life | Neighborly Bazaar | Live |
| Healthy Bee-ing | Care Check | Unavailable |
| Healthy Bee-ing | Calm Keep | Unavailable |
| Healthy Bee-ing | Snappy Count | Unavailable |
| Healthy Bee-ing | Medi Minder | Unavailable |
| Healthy Bee-ing | Moody Log | Beta |
| Healthy Bee-ing | Maven Wise | Beta |
| Identity Known | Critter Spotter | Beta |
| Identity Known | Roost Wrangler | Beta |
| Identity Known | Sight Seeker | Unavailable |
| Identity Known | Snap Decoder | Unavailable |
| Identity Known | Motif Muse | Unavailable |
| Identity Known | Maker Matcher | Unavailable |
| Identity Known | Self Fixer | Unavailable |

Branch hubs follow the same public distinction: Organized Life is currently
live as a branch hub; the other six hubs are public beta routing
surfaces with slim construction badges. A branch badge is a truthful status
signal, not a claim that every child Tool-ette is available.

## What “complete” means in this phase

The project is complete for the current **active growth and refinement** phase
when:

1. The 60 indexable public pages, 50 catalog pages, seven branches, and 42
   Tool-ettes are represented consistently in the filesystem, sitemap, search
   index, and applicable feed entries.
2. Every Tool-ette has one state from the publication register, and public
   copy never calls an unavailable or beta entry live.
3. The public hub's navigation, metadata, status language, and generated
   outputs pass the repository's release checks.
4. The public site states its boundary: it is a catalog and routing layer,
   while external GPT configuration and third-party availability remain
   separate.
5. Deferred owner choices remain visible with an owner, rationale, and review
   condition.

This does **not** mean all 42 external GPTs are finished, every output is
correct, accessibility or privacy is fully proven, the offline shell can run
third-party tools, or search engines have accepted the sitemap. Those are
separate capabilities with the statuses shown in the matrix.

## Owner decisions and review conditions

These decisions are retained explicitly rather than silently treated as
release blockers or resolved facts.

| Decision | Current disposition | Owner, rationale, and review condition |
|---|---|---|
| Lifecycle state | **Retained: Active** | Project owner; the site is deployed, maintained, and still receiving suite growth and refinement. Review after 90 days with no new tool or content work, or immediately if hosting/repository changes. |
| B1 — stronger branch visual indices | **Intentionally deferred** | Project owner/editor; current branch hubs already route visitors and bespoke layouts should not be homogenized. Review during the next branch redesign or when a new branch is added. |
| B3 — placement of portfolio positioning copy | **Retained as a content split** | Project owner/editor; README stays a concise repository orientation while the homepage, About, and Showcase carry public story and portfolio detail. Revisit only if the owner wants one marketing surface to become canonical. |
| C2 — visible per-page “Last updated” timestamps | **Intentionally deferred** | Project owner/editor; a stable visible date source and a brand placement decision are still needed. Review during the next metadata/editorial pass. |
| C3 — per-Tool-ette FAQ JSON-LD | **Intentionally deferred** | Project owner/editor; each answer requires authored, current content and must not be fabricated from page scaffolding. Review when the editorial owner can supply and maintain the Q&A set. |
| PurgeCSS or CSS minification build step | **Intentionally deferred** | Project owner/maintainer; the no-build static philosophy is currently more valuable than an unmeasured byte reduction. Review only with a measured performance case and a reversible CI design. |
| Orphaned butterfly artwork | **Intentionally deferred** | Project owner/asset curator; source art may still be wanted and deleting it is irreversible. Review during an explicit asset-curation pass. |
| B2 — Keep exploring trays | **Resolved** | Existing implementation is present on all 42 Tool-ette pages; re-open only if visitor testing shows the route choices are confusing. |
| B5 — complete-branch construction overlays | **Resolved as status badges** | Complete branch surfaces use slim badges rather than blocking overlays; re-open when a branch's actual publication state changes. |

## Evidence maintenance

When content or status changes, update this contract and the concise mirrors in
`README.md`, `LIFECYCLE.md`, `AGENTS.md`, `replit.md`, `llms.txt`,
`CHANGELOG.md`, `docs/roadmap.md`, and `showcase/index.html` in the same
change. Then rebuild generated outputs and run:

```bash
python3 scripts/build-search-index.py
python3 scripts/validate-site.py
python3 scripts/check-links.py
```

`feed.xml` is checked in as a deterministic release artifact. Its historical
generator is archived under `scripts/archive/` and is not part of the active
pipeline; regenerate it only as an owner-approved feed maintenance action.

Historical audit reports remain useful evidence of what was true on their
stated dates; they do not override this current contract's counts.
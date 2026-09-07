# Tool-ette promise verification

**Review date:** 2026-09-04  
**Scope:** all 42 public Glee-fully Tool-ette pages across seven branches  
**Owner:** Project owner  
**Decision:** keep the catalog public, but do not present an external GPT as
behavior-verified without owner evidence.

## Executive result

The repository proves the public catalog layer for all 42 Tool-ettes: each has
an authored page, branch placement, description, internal routing, and a
visible publication signal. It does **not** prove the behavior of the GPT after
the visitor leaves the site.

The review found:

| Verification classification | Count | Meaning |
|---|---:|---|
| Verified | 0 | No Tool-ette has the required owner-supplied configuration or test evidence. |
| Partially verified | 25 | The page claim is represented in the public catalog and its named, non-placeholder destination returned HTTP 200 during this review. Behavior is still unverified. |
| Unavailable | 15 | The page has no usable destination, or its recorded destination returned HTTP 404 during this review. |
| Construction | 0 | Construction is represented by the existing page overlay and is not silently promoted to a verified state. |
| Blocked by missing owner evidence | 2 | The destination responded, but the recorded target name does not match the Tool-ette claim; the launch link is withheld pending owner confirmation. |

The public publication register therefore now contains **1 live page, 24 beta
pages, and 17 unavailable pages**. “Live” means that the public page has a
non-placeholder launch destination and no construction overlay; it is not a
claim that the external GPT is behavior-verified.

## Admissible evidence and limits

### Evidence used

1. **Catalog evidence:** the page path, H1, meta description, visible purpose
   copy, inputs/outputs copy, core-function headings or leaves, safety language
   where authored, and internal branch routing.
2. **Destination evidence:** a non-placeholder ChatGPT URL copied from the
   page, probed without scraping or storing response content on 2026-09-04.
   HTTP 200 means the endpoint responded; it does not prove login access,
   ownership, GPT identity, configuration, or output quality. HTTP 404 is
   treated as unavailable.
3. **Owner evidence:** none supplied in this repository for this review. No
   private instructions, knowledge files, action definitions, conversation
   starters, or test transcripts were copied or inferred.

### What remains unverified for every partially verified destination

- external GPT display name and ownership;
- conversation starters and representative prompt/output behavior;
- promised functions beyond the public authored description;
- knowledge files, actions, model, account, and platform dependencies;
- refusal behavior, privacy behavior, and safety boundaries;
- persistence, export quality, and hand-off behavior.

The public page may describe **intended use**. It must not imply that these
unverified external properties have been audited.

## Per-Tool-ette evidence register

The **catalog claim** column is the current page description in concise form;
the linked page remains the source for the full authored copy and function
lists. “Core-function surface” means the page includes an authored
`Core functions`/`Leaves` section or equivalent detailed use-case content.

### 01  -  Discovered Careers

| Tool-ette | Catalog claim | Public evidence | Destination probe | Classification |
|---|---|---|---|---|
| Resume Builder | Build/polish ATS-aware resumes, match job posts, export versions. | `toolbox/01-discovered-careers/01a-resume-builder/`; description + inputs/outputs + core functions; beta overlay. | 200; named non-placeholder URL. | Partially verified |
| Resume Customizer | Transform one resume into role-specific, keyword-aware versions. | `.../01b-resume-customizer/`; description + inputs/outputs + core functions; beta overlay. | 200; named non-placeholder URL. | Partially verified |
| Career Fitness | Benchmark skills, match job titles, check salaries, map growth paths. | `.../01c-career-fitness/`; description + inputs/outputs + core functions; beta overlay. | 200; named non-placeholder URL. | Partially verified |
| Letter Composer | Turn a resume and job post into a tailored cover letter with tone/export options. | `.../01d-letter-composer/`; description + inputs/outputs + core functions; beta overlay. | 200; named non-placeholder URL. | Partially verified |
| bLinkIn Tuner | Capture daily interest/dread signals and turn them into career patterns. | `.../01e-blinkin-tuner/`; detailed leaves + beta overlay; placeholder launch removed. | No usable destination recorded. | Unavailable |
| Career Seeker | Define targets, track roles, manage applications, and follow up. | `.../01f-career-seeker/`; detailed leaves + beta overlay; placeholder launch removed. | No usable destination recorded. | Unavailable |

### 02  -  Treasured Finds

| Tool-ette | Catalog claim | Public evidence | Destination probe | Classification |
|---|---|---|---|---|
| Personal Librarian | Track owned, read, and wanted books across formats. | `toolbox/02-treasured-finds/02a-personal-librarian/`; description + core functions; beta overlay. | 200; named non-placeholder URL. | Partially verified |
| Decor Detective | Catalog seasonal décor, storage bins, and swap reminders. | `.../02b-decor-detective/`; description + inputs/outputs + core functions; beta overlay. | 200; named non-placeholder URL. | Partially verified |
| Present Hoarder | Track gifts, recipients, occasions, locations, budgets, and wrapping status. | `.../02c-present-hoarder/`; description + inputs/outputs + core functions; beta overlay. | 200; named non-placeholder URL. | Partially verified |
| Scentinal Journal | Log candles, melts, diffusers, and oils by scent context. | `.../02d-scentinal-journal/`; description + core functions + beta overlay; launch withheld because it targets Personal Librarian. | 200, but target name does not match. | Blocked by missing owner evidence |
| Spirited Journal | Record memories and meaning behind books, décor, and keepsakes. | `.../02e-spirited-journal/`; description + core functions + beta overlay; placeholder launch removed. | Placeholder destination returned 404. | Unavailable |
| Supply Haus | Inventory craft and creative supplies and identify restock needs. | `.../02f-supply-haus/`; description + inputs/outputs + core functions; beta overlay. | 200; named non-placeholder URL. | Partially verified |
| Bag Nabbit | Track, tag, wishlist, and loan bags in a collection. | `.../02g-bag-nabbit/`; description + core functions; beta overlay. | 200; named non-placeholder URL. | Partially verified |

### 03  -  Tasty Tracker

| Tool-ette | Catalog claim | Public evidence | Destination probe | Classification |
|---|---|---|---|---|
| Flavor Meister | Store, rate, and tag recipes for repeatable home cooking. | `toolbox/03-tasty-tracker/03a-flavor-meister/`; description + core functions; beta overlay. | 200; named non-placeholder URL. | Partially verified |
| Menu Conductor | Turn recipes, pantry notes, and schedules into weekly menus and grocery outputs. | `.../03b-menu-conductor/`; description + core functions + beta overlay; generic launch removed. | No named destination recorded. | Unavailable |
| Wishful Tastes | Track dream dishes, restaurants, and food experiences. | `.../03c-wishful-tastes/`; description + inputs/outputs + core functions; beta overlay. | 200; named non-placeholder URL. | Partially verified |
| Pantry Shopper | Turn pantry, recipes, and meal plans into shopping runs. | `.../03d-pantry-shopper/`; description + core functions + beta overlay; generic launch removed. | No named destination recorded. | Unavailable |
| Palatably Profiled | Build a living household flavor profile from food ratings. | `.../03e-palatably-profiled/`; description + inputs/outputs + core functions; beta overlay. | 200; named non-placeholder URL. | Partially verified |

### 04  -  Traveler’s Guide

| Tool-ette | Catalog claim | Public evidence | Destination probe | Classification |
|---|---|---|---|---|
| Journey Diary | Log trips, memories, and export-ready travel stories. | `toolbox/04-travelers-guide/04a-journey-diary/`; description + core functions; beta overlay. | 200; named non-placeholder URL. | Partially verified |
| Itinerary Hacker | Turn trip notes into shareable, time-blocked plans. | `.../04b-itinerary-hacker/`; description + core functions; beta overlay. | 200; named non-placeholder URL. | Partially verified |
| Detour Discoverer | Find worthwhile side trips, scenic stops, and bonus adventures. | `.../04c-detour-discoverer/`; detailed use cases + beta overlay; placeholder launch removed. | Placeholder destination returned 404. | Unavailable |
| Dreamland Journeys | Capture dream destinations and turn inspiration into plans. | `.../04d-dreamland-journeys/`; detailed leaves + beta overlay. | 200; named non-placeholder URL. | Partially verified |
| Memento Log | Turn travel notes, souvenirs, and snapshots into searchable memories. | `.../04e-memento-log/`; description + core functions; beta overlay. | 200; named non-placeholder URL. | Partially verified |

### 05  -  Organized Life

| Tool-ette | Catalog claim | Public evidence | Destination probe | Classification |
|---|---|---|---|---|
| Task Maestro | Organize to-dos by category, urgency, due date, tags, and checklists. | `toolbox/05-organized-life/05a-task-maestro/`; description + core functions; beta overlay. | 200; named non-placeholder URL. | Partially verified |
| Thrifty Spender | Keep bills, budgets, and spending habits together. | `.../05b-thrifty-spender/`; description + core functions; beta overlay. | 200; named non-placeholder URL. | Partially verified |
| Giftlist Helper | Track wishlists, gift ideas, and gift history. | `.../05c-giftlist-helper/`; description + core functions; beta overlay. | 200; named non-placeholder URL. | Partially verified |
| Scheduling Wizard | Turn tasks, bills, and events into calendar-ready plans. | `.../05d-scheduling-wizard/`; description + core functions + beta overlay; placeholder launch removed. | No usable destination recorded. | Unavailable |
| Lifestyle Wallboard | Bring bills, goals, habits, and tasks into one dashboard. | `.../05e-lifestyle-wallboard/`; description + core functions; beta overlay. | 200; named non-placeholder URL. | Partially verified |
| Neighborly Bazaar | Evaluate, price, and list household items for resale or donation. | `.../05f-neighborly-bazaar/`; description + inputs/outputs + core functions; no overlay. | 200; named non-placeholder URL. | Partially verified |

### 06  -  Healthy Bee-ing

Healthy Bee-ing retains an intentional **public beta** treatment for its
authored pages and an **unavailable** treatment for destinations that do not
respond. The health-related descriptions remain bounded by the authored
“general information,” logistics-only, and “not medical advice” language where
present; no clinical behavior is verified by this review.

| Tool-ette | Catalog claim | Public evidence | Destination probe | Classification |
|---|---|---|---|---|
| Care Check | Provide plain-language symptom check-in and urgency-oriented next-step guidance. | `toolbox/06-healthy-bee-ing/06a-care-check/`; description + explicit limitations + core functions; beta overlay. | 404; launch withheld. | Unavailable |
| Calm Keep | Track stress, sleep, and movement patterns without guilt. | `.../06b-calm-keep/`; description + core functions + beta overlay. | 404; launch withheld. | Unavailable |
| Snappy Count | Offer photo-based nutrition awareness and gentle estimates. | `.../06c-snappy-count/`; description + core functions + beta overlay. | 404; launch withheld. | Unavailable |
| Medi Minder | Organize medication logistics, refills, and appointments, not medical advice. | `.../06d-medi-minder/`; description + limitations + core functions; beta overlay. | 404; launch withheld. | Unavailable |
| Moody Log | Combine self-photos, hydration, and mood check-ins into a wellness timeline. | `.../06e-moody-log/`; description + core functions + beta overlay. | 200; named non-placeholder URL. | Partially verified |
| Maven Wise | Track midlife/hormonal-change symptoms and prepare care-team conversations. | `.../06f-maven-wise/`; description + core functions + beta overlay. | 200; named non-placeholder URL. | Partially verified |

### 07  -  Identity Known

| Tool-ette | Catalog claim | Public evidence | Destination probe | Classification |
|---|---|---|---|---|
| Critter Spotter | Identify animals from photos and log them with traits and tags. | `toolbox/07-identity-known/07a-critter-spotter/`; description + core functions; beta overlay. | 200; destination name not exposed in URL, so identity remains unverified. | Partially verified |
| Roost Wrangler | Decode architecture and furniture style from photos. | `.../07b-roost-wrangler/`; description + core functions; beta overlay. | 200; named non-placeholder URL. | Partially verified |
| Sight Seeker | Identify landscapes, skylines, and skies and add context/lore. | `.../07c-sight-seeker/`; description + core functions + beta overlay; placeholder launch removed. | Placeholder destination returned 404. | Unavailable |
| Snap Decoder | Decode screenshots, quotes, errors, and UI oddities into context. | `.../07d-snap-decoder/`; description + core functions + beta overlay; launch withheld because it targets Lifestyle Wallboard. | 200, but target name does not match. | Blocked by missing owner evidence |
| Motif Muse | Pull palettes, motifs, and style tags from photos. | `.../07e-motif-muse/`; description + core functions + beta overlay; placeholder launch removed. | No usable destination recorded. | Unavailable |
| Maker Matcher | Identify crafts/hobbies from photos or works in progress and suggest next exploration. | `.../07f-maker-matcher/`; description + core functions + beta overlay; placeholder launch removed. | No usable destination recorded. | Unavailable |
| Self Fixer | Identify mystery objects and DIY parts and suggest next steps. | `.../07g-self-fixer/`; description + core functions + beta overlay; launch withheld. | Recorded destination returned 404. | Unavailable |

## Catalog reconciliation

- Removed generic or placeholder launch CTAs from the 15 unavailable pages.
- Withheld the two 200-response destinations whose URL names clearly point to a
  different Tool-ette: Scentinal Journal → Personal Librarian and Snap Decoder
  → Lifestyle Wallboard.
- Kept all 42 authored pages indexable for discovery, but their construction
  overlays and unavailable copy prevent them from being presented as finished
  GPTs.
- Updated the suite contract and its concise mirrors to 24 beta, 1 live, and
  17 unavailable. The 42-page Tool-ette catalog now has 25 non-placeholder
  primary launch CTAs after unsafe or unavailable CTAs were withdrawn; the
  site-wide portfolio stat is 26 because it also counts a branch-level GPT
  destination.
- Rebuilt the search index after copy changes. Sitemap and feed membership stay
  aligned with the intentional public discovery policy.

## Ongoing review contract

A new or materially changed Tool-ette must not be labeled live until a dated
review record contains all of the following:

1. **Catalog identity:** branch, page path, title, description, canonical URL,
   and intended audience match the owner-approved Tool-ette.
2. **Destination identity:** exact external URL supplied by the owner; the
   destination opens for a reviewer without bypassing access controls; its
   displayed name and owner match the catalog entry.
3. **Representative behavior:** owner-approved starter prompts or test
   transcripts cover the catalog's primary input, output, and hand-off claims.
4. **Dependencies:** knowledge files, actions/connectors, model/account
   requirements, persistence, export behavior, and third-party dependencies
   are recorded without copying private material into this repository.
5. **Safety and privacy:** limitations, refusal/escalation behavior, regulated
   advice boundaries, sensitive-input handling, and third-party data
   boundaries are reviewed for the actual experience.
6. **Reconciliation:** page copy, CTA, publication label, structured metadata,
   search index, sitemap, feed, and branch counts are updated together.
7. **Recheck trigger:** repeat the review after a destination change, owner
   configuration change, major platform/model change, or a reported behavior or
   safety regression.

### Classification rules

- **Verified:** all seven review requirements have admissible evidence.
- **Partially verified:** public page and destination are evidenced, but one or
  more behavior, dependency, or safety requirements remain open.
- **Unavailable:** no usable destination or the destination is observed as
  unavailable; no launch CTA is shown.
- **Construction:** public work is intentionally withheld from catalog claims
  and should be noindex/non-sitemap if used in a future release.
- **Blocked by missing owner evidence:** a destination exists but identity,
  ownership, or a key promise cannot be confirmed; withhold the CTA until
  evidence arrives.

## Reproducible checks

Run from the repository root:

```bash
python3 scripts/audit-tool-ette-promises.py
python3 scripts/build-search-index.py
python3 scripts/validate-site.py
python3 scripts/check-links.py
```

The first command is deterministic and checks the 42-page public evidence
surface. External probes must be repeated manually or by an approved reviewer;
they are deliberately not part of CI because third-party availability is
volatile and a network success is not proof of behavior.

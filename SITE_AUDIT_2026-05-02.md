# Glee-fully Personalizable Tools™ — Site Audit & Enhancement Plan
**Date:** 2026-05-02
**Scope:** Whole-repo audit of `OKHP3/Glee-fullyTools` (live: https://glee-fully.tools), plus orphaned GitHub-only assets that never reach the rendered site. Focus: metadata, SEO, bot search, plus look/functionality.

---

## 1 · Audit Findings

### 1.1 Page inventory — clean
| Metric | Count |
|---|---|
| HTML files in repo | 59 |
| Pages in `sitemap.xml` | 57 |
| Sitemap-vs-files match | ✓ All 57 sitemap URLs resolve to real files |
| Correctly excluded from sitemap | `404.html`, `under-construction.html` |

No orphaned page-level routes. Every linked URL has a backing file.

### 1.2 Asset orphans — large
| Asset class | Total in repo | Referenced in HTML | Orphaned |
|---|---|---|---|
| PNG images in `assets/img/` | 205 | 15 | **190** |
| GPT icons (per-tool, transparent) | 48 unique | 0 | **48** |
| GPT icons (per-tool, retro-stripe) | ~48 | 0 | **48** |
| Hero butterfly art (multiple sizes) | ~10 | partial | several unused |
| Favicon: `favicon.svg` | 1 | 0 | **1 (modern SVG favicon never linked)** |
| Favicon: `favicon-48x48.png` | 1 | 0 | 1 |

**Most significant gap:** every single one of the **48 per-tool GPT icons** exists in the repo but never appears on the corresponding tool page. Each twig page is currently using a generic butterfly hero image instead of its purpose-built icon.

### 1.3 Structured data coverage
| Signal | Coverage | Gap |
|---|---|---|
| JSON-LD `WebSite` schema | 1/59 (homepage only) | — (correct) |
| JSON-LD `Organization` schema | 1/59 (homepage only) | — (correct) |
| JSON-LD `WebPage` / `SoftwareApplication` per twig | 0/49 inner pages | **All 49 twigs/branches missing** |
| JSON-LD `BreadcrumbList` | 0/59 | **All inner pages missing** |
| HTML breadcrumb nav (visible) | 5/59 (5 of 7 branch pages only) | All 42 twigs + 2 branches + 6 supporting pages |
| `SearchAction` declared in JSON-LD | 1/1 (homepage) | Now backed by actual search ✓ |

### 1.4 PWA / manifest — broken
`site.webmanifest` is currently:
```json
{"name":"","short_name":"","icons":[{"src":"/android-chrome-192x192.png",...}],
 "theme_color":"#ffffff","background_color":"#ffffff","display":"standalone"}
```

Problems:
1. **Empty `name` and `short_name`** → "Add to Home Screen" shows nothing.
2. **Wrong icon paths** — `/android-chrome-192x192.png` does not exist; the actual files live at `/assets/img/favicons/android-chrome-192x192.png`.
3. **Wrong theme/background colors** (`#ffffff`) — should match the brand: `#d35b2d` rust theme, `#f6f2ee` paper background.
4. **No `start_url`, `scope`, `lang`, or `description`** — required by Lighthouse for installable-PWA.

### 1.5 Favicon coverage
Only the legacy 16/32 PNGs and `favicon.ico` are linked. Missing:
- `favicon.svg` (modern scalable favicon — should be primary)
- `apple-touch-icon` link (referenced but path is relative not absolute on some pages)
- `mask-icon` for Safari pinned tabs

### 1.6 README content not surfaced
`README.md` has marketing copy ("AI should *feel good to use*", "Smart design made human", Ko-fi support link) that is **not present anywhere on the site**. Visitors landing from GitHub get a different brand pitch than visitors landing on glee-fully.tools.

### 1.7 Bot / AI-crawler signals — already strong
`robots.txt` is well-tuned (GPTBot blocked from training, OAI-SearchBot + ChatGPT-User allowed for retrieval). Sitemap declared. Twitter card and OG complete on all 59. ✓ No changes needed here.

### 1.8 Page-level metadata defects found and fixed in this session
- `toolbox/02-treasured-finds/02e-spirited-journal/index.html` was missing `<!DOCTYPE html>` and the `<head>` opening tag entirely. **Fixed.** Discovered by the indexer skipping the page.
- **6 inner pages had their `<link rel="canonical">` pointing to the homepage** (`https://glee-fully.tools/`) instead of their own URL. This is a serious SEO defect — Google would treat these as duplicates of the homepage and de-list them.
  - `toolbox/03-tasty-tracker/03b-menu-conductor/`
  - `toolbox/03-tasty-tracker/03c-wishful-tastes/`
  - `toolbox/03-tasty-tracker/03d-pantry-shopper/`
  - `toolbox/06-healthy-bee-ing/06a-care-check/`
  - `toolbox/06-healthy-bee-ing/06b-calm-keep/`
  - `toolbox/06-healthy-bee-ing/06c-snappy-count/`

  **Fixed.** Each page's `og:url` was already correct, so the canonical was rewritten to match. (`404.html` and `under-construction.html` also point canonical to homepage — left as intentional fallbacks.)
- The search-index builder now contains a **defensive validator** that fails loud if any non-home page resolves to `/` or if duplicate URLs appear, so this regression class can't quietly recur.

---

## 2 · Enhancement Proposal — ordered by SEO/bot impact

### Tier A — High-impact SEO/discoverability
| # | Enhancement | Why | Effort |
|---|---|---|---|
| **A1** | **Per-twig JSON-LD `SoftwareApplication` + `BreadcrumbList`** on all 42 tool pages | Each tool becomes a first-class entity in Google's Knowledge Graph; rich-result eligibility for breadcrumbs and software cards | M (template + sweep across 49 pages) |
| **A2** | **Per-branch JSON-LD `CollectionPage` + `BreadcrumbList`** on the 7 branch hubs | Branch pages become indexable hubs that surface their child tools in SERPs | S |
| **A3** | **Surface the 48 per-tool GPT icons** on their corresponding twig pages (`og:image`, `twitter:image`, hero `<img>`, JSON-LD `image`) | Replaces generic butterfly art with brand-distinctive imagery in social shares + search; massive image-SEO win | M (mapping table + per-page swap) |
| **A4** | **Fix `site.webmanifest`** — populate name, fix icon paths, set brand theme color (`#d35b2d`), add `description`/`start_url`/`scope`/`lang` | PWA installability + correct browser chrome color on Android/Chrome | S |
| **A5** | **Add `<link rel="icon" type="image/svg+xml" href="/assets/img/favicons/favicon.svg">`** site-wide | Modern browsers prefer SVG; sharper at all DPIs | S |
| **A6** | **Add visible breadcrumb navigation** to all 49 inner pages (not just 5 branches) | UX + SEO simultaneously; matches the JSON-LD breadcrumb data | M |

### Tier B — Look & feel / functional polish
| # | Enhancement | Why | Effort |
|---|---|---|---|
| **B1** | **Surface the brand-distinct GPT icons in branch-page tool cards** (replace text-only links with icon + name + tagline cards) | Branch pages become visual indices; uses the orphaned art | M |
| **B2** | **"Recently visited" or "Suggested next" tray** at the bottom of twig pages | Reduces dead-ends; pulls from the same `search-index.json` we just generated | S |
| **B3** | **README content → on-site `/about/` or homepage `why-glee` section** | Brand consistency across GitHub and the site; stop maintaining two pitches | S |
| **B4** | **Add Ko-fi support link to footer** (currently only in `.github/FUNDING.yml` and `README.md`) | Monetization signal aligned with the GitHub funding page | XS |
| **B5** | **Consolidate the `<head>` boilerplate** into a `_head_partial.html` pattern (or document the exact canonical block in `replit.md`) so the spirited-journal class of bug never recurs | Maintainability | M |
| **B6** | **Image lazy-loading** (`loading="lazy" decoding="async"`) on all non-hero `<img>` tags | LCP / CLS improvements; Lighthouse score | S |
| **B7** | **Preconnect to Google Fonts** (`<link rel="preconnect" href="https://fonts.googleapis.com">`) on all pages | First-paint speed-up for the rounded display fonts | S |

### Tier C — Optional / forward-looking
| # | Enhancement | Why |
|---|---|---|
| **C1** | RSS/Atom feed at `/feed.xml` listing tools as items | Discoverability for feed readers + AI ingestion |
| **C2** | "Last updated" `<time datetime="…">` per page using JSON-LD `dateModified` | Freshness signal for Google + LLM crawlers |
| **C3** | Per-tool FAQ JSON-LD blocks (one Q/A: "What does X do?") | FAQ rich-results eligibility |
| **C4** | `humans.txt` and `security.txt` | Modern site polish; small SEO trust signal |
| **C5** | Open Graph article-style `og:type="website"` → consider `og:type="product"` for individual tool pages | More accurate type semantics for social cards |

---

## 3 · What was implemented in this session

### Internal site search engine — shipped
The user's primary request from this session is now live across all 59 pages.

| Piece | Location | Notes |
|---|---|---|
| Index builder | `tools/build-search-index.py` | Walks repo, extracts title/desc/canonical/h1–h3/body, outputs JSON |
| Static index | `assets/data/search-index.json` | 57 entries · ~130 KB raw (~30 KB gzipped) |
| Runtime | `assets/js/search.js` | Lazy fetch, weighted scoring, modal UI, keyboard nav |
| Styles | end of `assets/css/theme.css` | Brand-aligned, dark-mode aware |
| Page injection | `<script src="/assets/js/search.js" defer>` added after `app.js` on all 59 pages | Verified count: 59/59 |
| Nav button | Auto-injected by `search.js` into `.primary-nav ul` | No HTML edits required per page |
| Triggers | Click magnifier · press `/` · ⌘K / Ctrl+K · arrive with `?s=query` | The `?s=` URL hook matches the existing `SearchAction` JSON-LD on the homepage so it actually works now |
| Repair | `02e-spirited-journal/index.html` got its missing `<!DOCTYPE>` and `<head>` opening tag back | Was discovered by the indexer skipping the page |

### How to rebuild after content changes
```bash
python3 tools/build-search-index.py
```
That's it — no Node, no build step, no external service. Commit the updated `search-index.json` and the search reflects new content on next page load.

### Scoring weights (in `search.js`)
```
title             ×10    titleStart bonus  +6
exact phrase in title    +25
headings          ×5     description    ×4
keywords          ×4     branch         ×3
section           ×2     body           ×1
all-tokens-found bonus    +6
```

---

## 4 · Recommended next session

If you want to keep momentum on the SEO side, **A1 + A3** are the two biggest single moves:
1. **A3 (icon swap)** uses 48 already-paid-for assets and turns every social share + image search hit into branded imagery.
2. **A1 (per-twig JSON-LD)** makes Google understand each tool as a discrete software entity rather than a generic web page.

Both can be done as template-driven sweeps, similar to the SEO sweep already completed.

---
*Report generated by the post-search-engine audit pass — 2026-05-02.*

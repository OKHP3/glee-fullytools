# Glee‑fully Tools — GitHub Pages Showpiece Plan
**Date:** 2026‑05‑02
**Goal:** Take the site from "polished personal site" to "résumé‑grade portfolio piece" — something a hiring manager, partner, or client can land on and immediately recognize as the work of a careful, capable craftsperson.

---

## Q&A · Should the search results live in a modal or a dedicated page?

**Short answer: both — and we just did it.**

### What modern, well‑run sites do
Algolia DocSearch, GitHub, Linear, Stripe Docs, MDN, and Vercel all ship a **command‑palette modal** (⌘K) for fast in‑context look‑ups *and* a **dedicated `/search/` page** for shareable, bookmarkable, crawlable results. There is no "either/or" — the modal is the speed lane, the page is the share lane.

### Why a dedicated page matters specifically for a static GitHub Pages site
| Capability | Modal only | Dedicated `/search/` page |
|---|---|---|
| Bookmark a query (`/search/?q=resume`) | ❌ | ✅ |
| Share a query as a URL | ❌ | ✅ |
| Listed in `sitemap.xml` & crawled by Google | ❌ | ✅ |
| Wire up Schema.org `SearchAction` to a real page | ❌ | ✅ |
| Survives "no‑JS" visitors with a usable directory | ❌ | ✅ |
| Works as a "site‑wide index hub" linkable from footers | ❌ | ✅ |
| Indexable by AI search bots (Perplexity, OAI‑SearchBot) | partial | ✅ |

### What was just shipped
1. New page at `/search/` with full brand chrome (header, nav, footer), breadcrumb, search input, inline results, keyboard‑shortcut tips, and a `<noscript>` directory fallback.
2. `search.js` extended with an `attachInline()` API. On the dedicated page it skips the auto‑modal trigger and renders directly into the page.
3. Query is reflected back into the URL as `?q=…` via `history.replaceState` so visitors can copy/share/bookmark.
4. Page added to `sitemap.xml` (`priority 0.6, weekly`).
5. `Schema.org SearchAction` declared on the page itself, pointing to `/search/?q={search_term_string}` — Google's preferred pattern for declaring an internal search.
6. Brand tokens (rust `#d35b2d`, gold `#f3b932`, espresso `#2a2320`, paper `#f6f2ee`) honored, light + dark mode covered.

The modal still works exactly as before from every other page (⌘K / `/` / nav click).

---

## Showpiece Plan — closing the gap to a portfolio‑grade GitHub Pages site

GitHub Pages is just static hosting; "best practices" are really *modern web best practices applied to a build‑less static site*. Below is a tier‑ranked plan, ordered by impact‑per‑hour. Items already complete are checked.

### Tier 0 · Already in great shape
- ✅ Custom domain, HTTPS, CNAME, sitemap, robots.txt, OG, Twitter cards, JSON‑LD on the homepage, retro brand system, dark/light mode, accessible nav.
- ✅ Internal search engine (modal + dedicated page).
- ✅ Canonical URLs corrected on 6 inner pages (was a real SEO bug).
- ✅ `site.webmanifest` rewritten with proper name, brand colors, and full icon set.

### Tier A · Highest impact (immediate "polished pro" gains, low risk)

#### A1 · Per‑page JSON‑LD (`SoftwareApplication` for tools, `WebPage` for branches) [High SEO + LLM‑search impact]
- **Why:** Right now only the homepage carries rich structured data. Tool pages should declare `SoftwareApplication` (or `Product`), branch hubs should declare `CollectionPage` + `BreadcrumbList`. This is what unlocks rich result eligibility (sitelinks, tool cards, AI summaries).
- **What:** A small Python helper (`tools/inject-jsonld.py`) that reads each page's existing `<title>`/`<meta description>`/`og:image` and writes a JSON‑LD block immediately before `</head>`. Idempotent (skip if already present, or replace if stale via a generated‑at marker).
- **Effort:** 2–3 hrs. Affects 59 files but is automated.

#### A2 · `BreadcrumbList` on every inner page [High SEO impact]
- **Why:** Currently breadcrumbs exist on only 5 of 59 pages. Google uses them to render the URL trail in SERPs and to understand site hierarchy.
- **What:** Same generator as A1; emit `BreadcrumbList` derived from the file path (`/toolbox/03‑tasty‑tracker/03b‑menu‑conductor/` → Home › Toolbox › Tasty Tracker › Menu Conductor).
- **Effort:** Bundled with A1.

#### A3 · Site‑wide favicon, manifest, and theme‑color links [Quick win, polish]
- **Why:** Currently homepage references favicons + manifest, but inner pages may be inconsistent. Also the SVG favicon (better at any DPR) is referenced nowhere.
- **What:** Audit all 59 `<head>` blocks; ensure each contains:
  - `<link rel="icon" type="image/svg+xml" href="/assets/img/favicons/favicon.svg" />`
  - PNG fallback, `apple-touch-icon`, `manifest`, `theme-color` (`#d35b2d`).
- **Effort:** 30 min via Python script.

#### A4 · Lazy‑loading + intrinsic dimensions on every `<img>` [Performance + Lighthouse score]
- **Why:** Cumulative Layout Shift (CLS) and Largest Contentful Paint (LCP) are the two Lighthouse killers. `loading="lazy"`, `decoding="async"`, and `width`/`height` attributes fix both.
- **What:** Audit all `<img>` tags; add the three attributes wherever missing. Below‑the‑fold images get `loading="lazy"`; the hero/butterfly stays eager.
- **Effort:** 1 hr.

#### A5 · 48 orphaned per‑tool GPT icons → display them [Content win + reduces orphan asset count]
- **Why:** Each tool page already has a beautiful 1024×1024 GPT‑rendered icon in the repo, none are displayed. They're rich brand assets going to waste.
- **What:** Add an icon block to each tool page near the H1; resize/optimize to a 256×256 WebP for the visible variant (keep the 1024 PNG as the OG image).
- **Effort:** 2 hrs (template change + image conversion script).

### Tier B · Medium impact (professional polish, more effort)

#### B1 · WebP/AVIF conversion of large PNGs [Big perf gain]
- **Why:** 202 PNGs in repo, several over 500 KB. WebP usually cuts 60–80% off PNG sizes with no visible quality loss.
- **What:** A Pillow script that walks `assets/img/`, generates `.webp` siblings, and updates `<img>` tags to use `<picture><source type="image/webp">…</picture>`.
- **Effort:** 3–4 hrs (script + tag rewrite + spot‑check).

#### B2 · 404 page improvements [Brand impression on broken links]
- **Why:** A custom, on‑brand 404 with a search field and curated "popular destinations" list is a small touch hiring managers notice.
- **What:** Embed a search input on `404.html` (using the same inline API the new search page uses) and a directory of top 6 destinations.
- **Effort:** 45 min.

#### B3 · Reconcile README marketing copy with site copy [Content discipline]
- **Why:** Repo README has voice and claims that don't appear on the site itself. Either promote the strongest lines onto the homepage or pull them from the README so the public-facing voice is one consistent thing.
- **What:** Side‑by‑side review, choose one source of truth, update the other.
- **Effort:** 1 hr.

#### B4 · `Cache-Control` strategy via filename hashing [Perf for repeat visits]
- **Why:** GitHub Pages serves with default cache headers (10 min). For long‑lived assets like fonts and images, you can't add explicit headers, but you *can* fingerprint filenames so they cache forever after first hit. The search index already uses `cache: "no-cache"` so it revalidates.
- **What:** Rename `theme.css` → `theme.<hash>.css` and `app.js` → `app.<hash>.js`; auto‑rewrite all references via a small build helper. (Optional — a real "no build" purist would skip this.)
- **Effort:** 2 hrs. **Risk:** introduces a small build step. Skip if you want to stay 100% build‑less.

#### B5 · Open Graph image variants per branch [Better social shares]
- **Why:** Every page currently shares the same butterfly hero image. Branch pages should have their own OG images (e.g., the branch's signature icon on the brand gradient).
- **What:** 7 OG images at 1200×630 (one per branch), referenced from each branch hub and its tool children.
- **Effort:** 2 hrs (mostly designing the template once and batch‑rendering).

### Tier C · Differentiator polish (the things that make it stand out as a portfolio piece)

#### C1 · Lighthouse + Web Vitals dashboard committed to repo [Demonstrates engineering maturity]
- **What:** Run `npx unlighthouse` against production, export the report, drop a `lighthouse-report/` folder + a one‑page `PERFORMANCE.md` summary into the repo. Re‑run quarterly. This is the kind of artifact a hiring manager will spot in the repo and immediately upgrade their opinion of the candidate.
- **Effort:** 1 hr.

#### C2 · Accessibility statement page [Showcases empathy + standards literacy]
- **What:** A `/accessibility/` page declaring WCAG 2.1 AA conformance target, listing known limitations, and providing a contact route for a11y feedback. Required for many enterprise/government partnerships.
- **Effort:** 1 hr (mostly writing).

#### C3 · `humans.txt` and `security.txt` [Tasteful, professional touches]
- **Why:** Tiny files at the site root that signal "this person knows the standards."
  - `/humans.txt` — credits the makers (you, your AI collaborators, fonts, etc.)
  - `/.well-known/security.txt` — RFC 9116 standard for security disclosures (just an email + PGP optional).
- **Effort:** 20 min.

#### C4 · GitHub Actions workflow that auto‑rebuilds the search index on push [Demonstrates DevOps fluency]
- **What:** `.github/workflows/build-search-index.yml` — on push to main, run `python3 tools/build-search-index.py`, commit the result if it changed. Eliminates the manual rebuild step entirely.
- **Effort:** 45 min.

#### C5 · `og:image` PNG generated from page metadata at deploy time [Differentiator]
- **What:** A Python + Pillow script that reads each tool page's title/branch/icon and renders a branded 1200×630 OG image (gradient, butterfly, tool name). Wire into the same Actions workflow as C4. Some of the most polished personal sites do this; very few candidate portfolios do.
- **Effort:** 3–4 hrs.

#### C6 · Atom or JSON feed of "What's new" entries [Power‑user signal]
- **What:** `/feed.xml` or `/feed.json` listing the most recent additions/updates to the toolbox. Makes the site subscribable in any RSS reader, signals editorial discipline.
- **Effort:** 1 hr (manual entries) or 2 hrs (auto‑generated from a `CHANGELOG.md`).

#### C7 · `/sitemap-index.xml` + per‑section sitemaps [SEO at scale]
- **Why:** Once the site grows beyond ~100 URLs, splitting the sitemap into per‑section files (toolbox, ecosystem, etc.) helps crawlers prioritize. Premature today but worth noting in the roadmap.
- **Effort:** 1 hr when needed.

---

## What I just shipped in this session
1. ✅ Internal search engine (modal + ⌘K + `/` + `?s=` triggers).
2. ✅ Dedicated `/search/` page with shareable URLs, breadcrumbs, JSON‑LD, dark mode, no‑JS fallback.
3. ✅ Hardened `tools/build-search-index.py` (refuses to silently propagate bad canonicals; fails build if non‑home pages resolve to `/`).
4. ✅ Fixed canonical URLs on 6 inner pages (real SEO bug — homepage duplicates).
5. ✅ Repaired malformed `02e-spirited-journal/index.html` (missing `<!DOCTYPE>`/`<head>`).
6. ✅ Rewrote `site.webmanifest` (proper name, brand colors, full icon set).
7. ✅ Added `/search/` to `sitemap.xml`.

## Recommended next sprint (in order)
1. **A1 + A2 together** — biggest SEO leverage per hour. JSON‑LD generator that emits `SoftwareApplication` / `CollectionPage` / `BreadcrumbList` to all 59 pages.
2. **A4** — lazy‑load and intrinsic dimensions on every `<img>`. Lighthouse jumps 10–20 points.
3. **A5** — surface the 48 orphaned GPT icons on their tool pages. Already designed, just needs to be displayed.
4. **A3** — favicon/manifest/theme‑color audit across all 59 pages.
5. **C1 + C4** — commit a Lighthouse report + add the GitHub Actions workflow for the search index. These two together transform the repo from "personal site" to "portfolio artifact."

If you want me to keep going, say which tier (or which specific items) you'd like next and I'll execute them.

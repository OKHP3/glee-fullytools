# Glee-fully Personalizable Tools™

A joyful static website serving as a hub for custom GPTs organized in a "trunk-branch-twig" hierarchy. Part of the OKHP³™ (OverKill Hill P³) universe.

## Tech Stack

- **Frontend:** Pure HTML5, CSS3, and vanilla JavaScript (no build system)
- **Styling:** Custom CSS variables with a retro-bright palette (Teal, Olive, Ochre, Rust)
- **Fonts:** Google Fonts (Fredoka, Open Sans, Poppins, DM Sans, Alfa Slab One)
- **Dependencies:** Loaded via CDN (Mermaid.js v11, Ko-fi, Google Analytics G-89W66VMGPB)
- **Hosting:** Static site served with Python's built-in HTTP server in dev

## Project Structure

- `index.html` — Main landing page with JSON-LD WebSite+Organization schema
- `assets/css/theme.css` — Central stylesheet (4265 lines), reorganized 2026-05-02 into scope-grouped sections: GLOBAL (L 6) → OVERKILL (L 2215) → GLEE (L 2633) → ASKJAMIE (L 3659) → CROSS-BRAND (L 4116). Each scope has a `╔══╗` boxed banner. Within each scope, sections retain original relative order so cascade is unchanged.
- `assets/js/app.js` — Shared JS (918 lines): progress bar, theme toggle, mobile nav, sticky-TOC module, and the full search engine (search.js merged into app.js 2026-05-04). Exposes `window.GleeSearch` for debugging.
- `assets/js/mermaid-init.js` — External Mermaid v11 init (used by ecosystem + universe pages). Both pages also carry a single `.mermaid-referral` credit linking to the paid-referral URL `https://mermaidchart.cello.so/UhVlNtC2MlS` in Mermaid hot-pink `#FF3670`. `scripts/validate-site.py` enforces a one-instance-per-Mermaid-page invariant so this credit can never silently be dropped.
- `assets/img/` — Branded butterfly and GPT icons
- `toolbox/` — Central hub with 7 thematic branches and their tool-ettes (54 pages total)
- `about/`, `contact/`, `legal/`, `persona/`, `universe/`, `ecosystem/` — Supporting pages
- `robots.txt` — Bot policy (GPTBot blocked for training; OAI-SearchBot, ChatGPT-User allowed)
- `sitemap.xml` — 57 URLs

## Workflows

- **Start application:** `python3 -m http.server 5000 --bind 0.0.0.0` (port 5000, webview)

## Deployment

Configured as a **static** deployment with `publicDir: "."` — no build step needed.

## CSS Scope Map (post 2026-05-02 reorganization)

When editing `theme.css`, find the right scope first:

| Scope | Starts at | What lives here | Selector pattern |
|---|---:|---|---|
| GLOBAL | L 6 | Tokens, reset, layout, header/nav, footer, scroll-reveal, articles, Ko-fi, search engine, cross-site sync | unscoped or `:root` / `body` |
| OVERKILL | L 2215 | Default chrome (headings, blueprint-forge hero, brand stripes, default Mermaid skin) | `body:not(.glee-main):not(.askjamie-main) …` |
| GLEE | L 2633 | This site's brand chrome (paper hero, milestone, Glee Mermaid) | `.glee-main …` / `body.glee-main …` |
| ASKJAMIE | L 3659 | AskJamie chrome (mid-century paper + teal, system pages) | `.askjamie-main …` / `body.askjamie-main …` |
| CROSS-BRAND | L 4116 | Glee + AskJamie shared overrides of OverKill default | `.glee-main … , .askjamie-main …` |

When diffing against sibling repos: differences inside GLOBAL/CROSS-BRAND blocks should be reconciled; differences inside the OVERKILL/GLEE/ASKJAMIE blocks are intentional brand divergence. Pre-reorg backup at `assets/css/theme.css.bak-prereorg`.

## Inline-content audit (2026-05-02)

Site already at GitHub Pages best practices: 0 inline `<style>` blocks; only 2 trivial single-use `style="…"` attributes (toolbox/06-healthy-bee-ing); 13 inline JSON-LD blocks (must stay inline per Schema.org). All shared CSS/JS properly externalized.

## Site-wide enhancements (2026-05-02 polish pass)

Applied to every real HTML page (62 pages):

- **"Built with Replit" footer attribution** — `.footer-replit-credit` on the left edge of the 2-column `.footer-bottom`, links to `https://replit.com/refer/overkillhillp3/` (referral). Replit brand orange `#f26207`.
- **Google Analytics propagation** — `gtag.js` + inline `gtag('config','G-89W66VMGPB')` now in every page's `<head>` (was only on `index.html`).
- **Skip-to-content link** (a11y) — `<a class="skip-to-content" href="#main">` injected as first child of `<body>` on every page; visually hidden until keyboard-focused.
- **`theme-color` meta** — added on the 11 pages that were missing it (mobile browser chrome).
- **`og:locale` meta** — added on the 4 pages that were missing it (social-card completeness).
- **`loading="lazy" decoding="async"` on below-header images** — added to 54 images. Header logo intentionally preserved as eager-loaded to protect LCP.

The mutator script (`/tmp/enhance_pages.py`) is idempotent — each transformation has a "skip if already present" guard, so re-running is safe.

## SEO & Metadata Status (as of 2026-04-11)

All 59 HTML pages have been fully audited and updated:

| Signal | Status |
|---|---|
| Canonical URL / og:url | ✅ Fixed (was broken on 9 pages) |
| og:locale | ✅ Added to all 59 pages |
| og:site_name | ✅ Standardized to `Glee&#8209;fully Personalizable Tools™` |
| og:image:type | ✅ Added where og:image:height present (21 pages) |
| twitter:site + twitter:creator | ✅ `@OverKillHillP3` on all 59 pages |
| robots meta (full directives) | ✅ 58/59 pages (under-construction.html is noindex/nofollow by design) |
| googlebot | ✅ All indexable pages |
| bingbot | ✅ All 59 pages |
| revisit-after | ✅ All 59 pages |
| mobile-web-app-capable | ✅ All 59 pages |
| apple-mobile-web-app-capable | ✅ All 59 pages |
| apple-mobile-web-app-status-bar-style | ✅ All 59 pages |
| creator + publisher meta | ✅ 34 pages (pages with `name="author"` tag) |
| Mermaid v10 inline scripts | ✅ Removed from all pages (was 54 pages) |
| Mermaid v11 external ref | ✅ ecosystem + universe (only 2 pages with actual diagrams) |
| robots.txt | ✅ Created |
| sitemap.xml | ✅ Created (57 URLs) |
| JSON-LD schema | ✅ Homepage (WebSite + Organization) |
| Inline style= attributes | ✅ Extracted to utility classes (.mt-075, .mt-1–.mt-4) |

## Cross-site Sync Notes (overkillhill.com reference)

- CSS utility classes appended to `theme.css` (`.mermaid foreignObject` fix, `.text-amber`, `.link-amber`, `.diagram-*`, `.section-subtitle`, `.council-*`, `.mt-*` spacing helpers)
- Twitter handle: `@OverKillHillP3` used as site-wide `twitter:site` and `twitter:creator`
- Mermaid v11 ESM pattern now matches sibling sites
- 2 multi-property inline styles remain in `toolbox/06-healthy-bee-ing/index.html` (lines 290, 437) — they bundle font-size + max-width alongside margin-top and require page-specific class names

## Internal Site Search (added 2026-05-02)

A zero-dependency, fully client-side search engine indexes every published page so visitors can jump anywhere without clicking through the trunk-branch-twig hierarchy.

| Component | Path | Purpose |
|---|---|---|
| Index builder | `scripts/build-search-index.py` | Walks every `*.html`, extracts title/description/canonical/h1-h3/body, writes `assets/data/search-index.json` |
| Search index | `assets/data/search-index.json` | 57 pages, ~130 KB raw (~30 KB gzipped) — committed to repo, no backend needed |
| Runtime | `assets/js/app.js` (search section, line 263+) | Lazy-loads index, tokenizes query, weighted field scoring, renders modal results |
| Styles | `assets/css/theme.css` (search section at end) | Modal, nav button, result cards, dark-mode aware |
| Wired into | All 60 HTML pages | `<script src="/assets/js/app.js" defer>` — single script, no separate search.js |

**Triggers:** Click magnifier in nav · press `/` outside an input · press ⌘K / Ctrl+K · arrive at any page with `?s=query` (matches the JSON-LD `SearchAction` declared on the homepage)

**Rebuilding the index:** Run `python3 scripts/build-search-index.py` after content changes. The generator excludes `404.html` and `under-construction.html`.

**Why no Lunr.js or Algolia:** The site has 57 indexable pages and the raw text trims to ~130 KB. A homemade weighted scorer (title × 10, headings × 5, description × 4, body × 1) is plenty fast at this scale and adds zero external dependencies, matching the site's no-build philosophy.

**Two surfaces, one engine:** The search section of `app.js` powers (a) the global ⌘K/`/` modal injected into every page's nav, and (b) the dedicated `/search/` page. The dedicated page declares `data-glee-search-inline` on `<main>` plus three hooks: `[data-glee-search-inline-input]`, `[data-glee-search-inline-status]`, `[data-glee-search-inline-results]`. On boot it detects the inline marker and runs `attachInline()` instead of opening the modal — and writes the query back into the URL as `?q=` for shareability. The `?s=` param still auto-opens the modal everywhere else.

## Validation tooling (2026-05-03)

Seven standalone Python scripts under `scripts/` keep the site honest. **Run order
matters** — `inject-jsonld` reads `og:image` to set `primaryImageOfPage`, so it
must run *after* `activate-icons`; `inject-breadcrumb` reads the JSON-LD that
`inject-jsonld` writes, so it must run *after* both of those.

```bash
# 1. Mutators (idempotent, AUTOGEN-marker-driven)
python3 scripts/normalize-head.py     # canonical favicon chain + theme-color
python3 scripts/activate-icons.py     # hero <img> + og:image swap to per-tool icons
python3 scripts/inject-jsonld.py      # JSON-LD @graph + BreadcrumbList
python3 scripts/inject-breadcrumb.py  # visible <nav aria-label="Breadcrumb">

# 2. Index / asset / feed regenerators
python3 scripts/build-search-index.py # rebuilds assets/data/search-index.json
python3 scripts/audit-assets.py       # rebuilds assets/data/icon-map.json + audit/asset-inventory-*.json
python3 scripts/generate-feed.py      # rebuilds /feed.xml

# 3. Validators (exit non-zero on regressions; safe to wire into CI)
python3 scripts/validate-site.py      # every-page metadata + structure checks
python3 scripts/check-links.py        # every internal href + sitemap parity
```

Validators write machine-readable JSON to `audit/`. The Markdown audit covers
(`AUDIT_*_2026-05-03.md`) explain the JSON output for humans. Re-running the
mutators is byte-idempotent — they are safe to re-run on every content edit.

## Template library (`assets/templates/`)

Nine structural HTML templates covering all 67 pages of the site.
Templates live **flat** in `assets/templates/` as `template--[slug].html`.
Each carries a full comment block enumerating every `[[UPPERCASE-KEBAB-CASE]]`
token before `<!DOCTYPE html>`. The index and workflow for adding new pages
live in `assets/templates/INDEX.md`.

| Template file | Type | Pages |
|---|---|---|
| `template--homepage.html` | homepage | 1 |
| `template--hub-toolbox.html` | hub-toolbox | 1 |
| `template--hub-branch.html` | hub-branch | 7 |
| `template--tool-detail.html` | tool-detail | 49 |
| `template--interior-single.html` | interior-single | 4 |
| `template--utility.html` | utility | 1 |
| `template--mermaid-diagram.html` | mermaid-diagram | 2 |
| `template--error.html` | error | 1 |
| `template--holding.html` | holding | 1 |

Templates are **development artifacts**, not crawlable pages — every
HTML-walking tool in `scripts/` excludes the entire `assets/` tree, so
templates are invisible to validators, indexer, sitemap, and feed.

**Superseded:** `scripts/generate-templates.py` generated the old per-page
60-file `{{DOUBLE_BRACE}}` system (deleted). Do **not** re-run it.
`TEMPLATE_INDEX.md` replaced by `assets/templates/INDEX.md`.

## Audit artifacts (2026-05-03)

All audit documents live in `assets/docs/` (non-crawlable, skipped by all HTML-walking tools):

* `assets/docs/FINAL_AUDIT_2026-05-03.md` — comprehensive 26-row change log, canonical reference
* `assets/docs/OPEN_TODOS_2026-05-03.md` — 3 placeholder GPT URLs + deferred editorial items
* `assets/docs/AUDIT_PAGE_INVENTORY_2026-05-03.md` — Phase 0 page inventory
* `assets/docs/AUDIT_LINKS_2026-05-03.md` — Phase 3 link audit
* `assets/docs/AUDIT_ASSETS_2026-05-03.md` — Phase 7 asset inventory
* `assets/docs/AUDIT_ACCESSIBILITY_2026-05-03.md` — Phase 8 accessibility audit
* `assets/docs/AUDIT_PERFORMANCE_2026-05-03.md` — Phase 10 performance audit
* `assets/docs/gleefully-replit-theme-guide.md` — Replit app theme configuration guide

Machine-readable JSON outputs live in `assets/audit/` (written by tools on each run):
`assets/audit/validation-report-2026-05-03.json`, `assets/audit/links-report-2026-05-03.json`, `assets/audit/asset-inventory-2026-05-03.json`

## Recent Changes

- **2026-05-03 — Final audit pass.** Visible breadcrumb on 57 inner pages (mirrors the JSON-LD `BreadcrumbList`); restored missing `<!DOCTYPE html>` on `02b-decor-detective`; added `feed.xml` (Atom, 49 entries), `humans.txt`, `/.well-known/security.txt`; bumped sitemap dates from 2026-04-07 to 2026-05-03; new validators `scripts/validate-site.py`, `scripts/audit-assets.py`, `scripts/check-links.py`, `scripts/inject-breadcrumb.py`, `scripts/generate-feed.py`; 5 new `AUDIT_*_2026-05-03.md` reports + machine-readable JSON in `audit/`. 60/60 pages validate clean (0 issues, 0 warnings, 0 broken internal links).
- **2026-05-02 — Dedicated `/search/` page.** Shareable, bookmarkable search results page with breadcrumb, JSON-LD `SearchAction`, no-JS directory fallback, dark-mode support. URL syncs as `?q=` for share/bookmark. Added to `sitemap.xml`. `search.js` extended with `attachInline()` API; on the dedicated page it skips the auto-modal and renders inline.
- **2026-05-02 — `site.webmanifest` fixed.** Was empty (`name:""`, wrong icon paths, white theme color). Now declares full brand identity, brand colors (`theme:#d35b2d`, `bg:#f6f2ee`), correct paths to all favicon variants, plus maskable purpose for Android.
- **2026-05-02 — Internal search engine.** Index builder + runtime + nav UI + ⌘K/`/` keybinds shipped on all 59 pages.
- **2026-05-02 — Canonical-URL SEO bug fixed.** 6 inner tool pages (`03b-menu-conductor`, `03c-wishful-tastes`, `03d-pantry-shopper`, `06a-care-check`, `06b-calm-keep`, `06c-snappy-count`) had `<link rel="canonical">` pointing to the homepage instead of themselves — discovered by the search-index validator. All 6 corrected to match their `og:url`. Indexer now fails loud if this regression recurs.
- **2026-05-02 — Spirited Journal page repaired.** Was missing `<!DOCTYPE html>` and `<head>` opening tag (skipped during initial indexing).
- **2026-04-11 — Replit App Theme exports.** `gleefully-replit-theme.json` + `gleefully-replit-theme-guide.md` covering Foundation, Actions, Forms (focus border `#d35b2d`), Containers (paper-system surfaces), Charts (5 retro-stripe colors).


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
- `assets/css/theme.css` — Central stylesheet (~3620 lines incl. cross-site sync utility classes)
- `assets/js/app.js` — Shared JS (progress bar, theme toggle, mobile nav)
- `assets/js/mermaid-init.js` — External Mermaid v11 init (used by ecosystem + universe pages)
- `assets/img/` — Branded butterfly and GPT icons
- `toolbox/` — Central hub with 7 thematic branches and their tool-ettes (54 pages total)
- `about/`, `contact/`, `legal/`, `persona/`, `universe/`, `ecosystem/` — Supporting pages
- `robots.txt` — Bot policy (GPTBot blocked for training; OAI-SearchBot, ChatGPT-User allowed)
- `sitemap.xml` — 57 URLs

## Workflows

- **Start application:** `python3 -m http.server 5000 --bind 0.0.0.0` (port 5000, webview)

## Deployment

Configured as a **static** deployment with `publicDir: "."` — no build step needed.

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
| Index builder | `tools/build-search-index.py` | Walks every `*.html`, extracts title/description/canonical/h1-h3/body, writes `assets/data/search-index.json` |
| Search index | `assets/data/search-index.json` | 57 pages, ~130 KB raw (~30 KB gzipped) — committed to repo, no backend needed |
| Runtime | `assets/js/search.js` | Lazy-loads index, tokenizes query, weighted field scoring, renders modal results |
| Styles | `assets/css/theme.css` (search section at end) | Modal, nav button, result cards, dark-mode aware |
| Wired into | All 59 HTML pages | `<script src="/assets/js/search.js" defer>` after `app.js` |

**Triggers:** Click magnifier in nav · press `/` outside an input · press ⌘K / Ctrl+K · arrive at any page with `?s=query` (matches the JSON-LD `SearchAction` declared on the homepage)

**Rebuilding the index:** Run `python3 tools/build-search-index.py` after content changes. The generator excludes `404.html` and `under-construction.html`.

**Why no Lunr.js or Algolia:** The site has 57 indexable pages and the raw text trims to ~130 KB. A homemade weighted scorer (title × 10, headings × 5, description × 4, body × 1) is plenty fast at this scale and adds zero external dependencies, matching the site's no-build philosophy.

## Recent Changes

- **2026-05-02 — Internal search engine.** Index builder + runtime + nav UI + ⌘K/`/` keybinds shipped on all 59 pages.
- **2026-05-02 — Canonical-URL SEO bug fixed.** 6 inner tool pages (`03b-menu-conductor`, `03c-wishful-tastes`, `03d-pantry-shopper`, `06a-care-check`, `06b-calm-keep`, `06c-snappy-count`) had `<link rel="canonical">` pointing to the homepage instead of themselves — discovered by the search-index validator. All 6 corrected to match their `og:url`. Indexer now fails loud if this regression recurs.
- **2026-05-02 — Spirited Journal page repaired.** Was missing `<!DOCTYPE html>` and `<head>` opening tag (skipped during initial indexing).
- **2026-04-11 — Replit App Theme exports.** `gleefully-replit-theme.json` + `gleefully-replit-theme-guide.md` covering Foundation, Actions, Forms (focus border `#d35b2d`), Containers (paper-system surfaces), Charts (5 retro-stripe colors).


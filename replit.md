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

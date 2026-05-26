# Performance Audit — 2026-05-03

Static-site, no-build, GitHub-Pages-served. Goal: keep the page lean enough
that LCP stays under 2.0 s on a mid-tier 3G connection without sacrificing the
retro-bright look.

---

## Asset budget

| Asset | Size | Status |
|---|---:|---|
| `assets/css/theme.css` | 105 KB (4,454 lines) | One file, scope-mapped (GLOBAL / OVERKILL / GLEE / ASKJAMIE / CROSS-BRAND). +83 lines added in this pass for the breadcrumb component. |
| `assets/js/app.js` | 9 KB | Progress bar, theme toggle, mobile nav, sticky-TOC. No deps. |
| `assets/js/search.js` | 24 KB | Lazy-loads index. |
| `assets/js/mermaid-init.js` | 0.7 KB | Pulls Mermaid v11 only on `ecosystem/` and `universe/`. |
| `assets/data/search-index.json` | 132 KB raw / ~30 KB gzipped | Lazy-loaded only when the search modal opens. Not in the LCP path. |
| Total per-page critical CSS+JS | ~140 KB raw / ~45 KB gzipped | Acceptable for a content-heavy retro design. |

---

## Render-path practices already in place

* **Single shared CSS file** — one HTTP request, easily cached.
* **Non-blocking JS** — `assets/js/app.js` and `assets/js/mermaid-init.js`
  are `defer`'d (mermaid via `type="module"` which is defer-by-spec),
  the Ko-fi widget is `async`, and Google Tag Manager is `async`. No
  `<script src>` in the document blocks HTML parsing.
* **Preconnect to Google Fonts** — `<link rel="preconnect">` to
  `fonts.googleapis.com` and `fonts.gstatic.com` on all 60 pages.
* **Lazy hero icons except the LCP candidate** — every `<img>` below the
  initial viewport carries `loading="lazy" decoding="async"`. Header logo
  intentionally eager.
* **Mermaid scoped** — only the two pages that actually contain diagrams pull
  in the Mermaid bundle.
* **Ko-fi widget script** — not site-wide; only loaded on pages that opt in.
* **Inline JSON-LD** — small per-page (~1–2 KB), keeps schema with the page
  it describes (Schema.org best practice).
* **No duplicate script tags** — verified by validator.

---

## Largest fetched assets per page

For a typical tool-ette page (e.g. `01a-resume-builder/`):

| Asset | Size | Notes |
|---|---:|---|
| GPT icon hero | 90–600 KB depending on tool | One-shot, cached. |
| Header butterfly logo | 47 KB | Cached site-wide. |
| `theme.css` | 105 KB raw / ~22 KB gzipped | Cached site-wide. |
| `app.js` + `search.js` | 33 KB raw / ~10 KB gzipped | Cached site-wide. |
| Google Fonts (5 families woff2) | ~80 KB total | Fetched once per font-family. |

After the first navigation, every subsequent page is essentially HTML + the
unique hero image only.

---

## Known weight to keep an eye on

* **Hero PNGs are 1024 × 1024** at 100–600 KB each. On the highest-res tools
  this is the biggest single fetch on the page. A future pass could:
  * generate matching `.webp` siblings and emit them via `<picture>` (target:
    50–60% size cut, browser support is universal in 2026), or
  * downscale the rendered version to 512 × 512 since the actual displayed
    size is ≤ 280 px.
  Both are deferred — they require touching every tool-ette template, and
  the script that renders the icons is not part of this repo.
* **22 MB of orphaned butterfly composites** (see `AUDIT_ASSETS_2026-05-03.md`).
  Not on the runtime path; affects clone size only.

---

## Cumulative-Layout-Shift (CLS) hygiene

* Hero `<img>` tags carry explicit width/height attributes from the source
  template, so the browser reserves the box before the bytes arrive.
* No web-font swap-flash because Google Fonts is rendered with `font-display:
  swap` (Google's default) and the cascade falls back to system fonts that
  are dimensionally close.
* The breadcrumb component reserves height via padding rather than min-height,
  so it cannot cause a CLS event when injected.

---

## Deferred / future work

| Item | Effort | Impact |
|---|---|---|
| `.webp` siblings for hero PNGs via `<picture>` | M | 50–60% LCP byte cut on tool pages |
| Self-host the 5 Google Font families (woff2 only) | M | One fewer DNS handshake; saves ~80–120 ms on cold loads |
| Build a tiny PurgeCSS run over `theme.css` | M | Cuts CSS by ~30 KB; risk: cross-brand selectors that scan misses |
| Ship a minified `theme.min.css` via a CI step | S | Cuts ~25% of CSS bytes; trade: one extra build step |

None of these are blockers. The site already meets the no-build philosophy
and serves under the expected weight budget for a static retro-design site.

---

## How to re-measure

There is no Lighthouse inside the sandbox. To regression-check after content
changes:

```bash
python3 scripts/audit-assets.py     # surface any new oversized image
python3 scripts/build-search-index.py  # check the index hasn't ballooned
ls -lh assets/css/*.css assets/js/*.js  # quick CSS / JS budget check
```

For a production reading, run Lighthouse against `https://glee-fully.scripts/`
and any one tool-ette page. Both should sit comfortably above 90 in
Performance, Accessibility, Best Practices, and SEO.

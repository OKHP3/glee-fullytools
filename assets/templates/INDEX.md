# Glee-fully Tools™ — Template Library Index

**Last updated:** 2026-05-04
**Supersedes:** `TEMPLATE_INDEX.md` (old per-page 60-file system, deleted)
**Previous generator:** `scripts/generate-templates.py` — now superseded by this flat structural library

---

## Overview

Nine structural HTML templates covering all 62 pages of the site.
Templates live flat in `assets/templates/` as `template--[slug].html`.

All validators, the search indexer, the feed generator, and the link checker
skip the entire `assets/` tree — templates are **invisible to site tooling** by design.

---

## Token convention

Tokens use `[[UPPERCASE-KEBAB-CASE]]` double-bracket syntax.
Replace every `[[TOKEN]]` with the page-specific value before publishing.

---

## Template index

| File | Type | Source page | Pages covered |
|---|---|---|---|
| `template--homepage.html` | homepage | `index.html` | 1 |
| `template--hub-toolbox.html` | hub-toolbox | `toolbox/index.html` | 1 |
| `template--hub-branch.html` | hub-branch | `toolbox/01-discovered-careers/index.html` | 7 |
| `template--tool-detail.html` | tool-detail | `toolbox/01-discovered-careers/01a-resume-builder/index.html` | 49 |
| `template--interior-single.html` | interior-single | `about/index.html` | 4 (about, contact, legal, persona) |
| `template--utility.html` | utility | `search/index.html` | 1 |
| `template--mermaid-diagram.html` | mermaid-diagram | `ecosystem/index.html` | 2 (ecosystem, universe) |
| `template--error.html` | error | `404.html` | 1 |
| `template--holding.html` | holding | `under-construction.html` | 1 |

**Total:** 9 templates → 67 pages

---

## Shared infrastructure (identical across all templates)

Every template carries the same:

- Normalized `<head>` with preconnects, prerender guard for GA4, and all metadata groups
- **Anti-FOSC color-scheme init** — `<!-- AUTOGEN:COLOR-SCHEME-INIT -->` inline `<script>` immediately
  after `<meta charset="utf-8" />`. Reads `localStorage['glee-color-scheme']` and sets
  `data-color-scheme` on `<html>` before first paint so visitors with a saved preference
  never see a flash of the wrong color scheme. **Must not be removed or moved.**
- Site header with logo, primary nav, submenu, mobile toggle, Today's Sparkle bar
- Site footer with 3-column grid + footer-bottom copyright
- `<script src="/assets/js/app.js" defer></script>` (search, nav, overlay, WIP gate, carousel)
- `<script src="https://storage.ko-fi.com/cdn/scripts/overlay-widget.js" async></script>`
  _(omitted on `utility`, `error` — check each template's NOTES section)_

Structural chrome is **never tokenized** — update it in the live HTML pages directly,
then re-sync to the template manually.

---

## Template-specific notes

### homepage

Unique to the root `index.html`. Carries:
- `<link rel="alternate">` for `/feed.xml`
- `<link rel="author">` for `/humans.txt`
- Speculation Rules API block
- Glee-hero stripes + site-status early-emergence card
- Latest-block "Today's Special" card (tokenized: `[[LATEST-*]]`)
- `[[SPARKLE-URL]]` / `[[SPARKLE-TEXT]]` in the Today's Sparkle bar

### hub-toolbox

Top-level Toolbox hub. No construction overlay. Fixed 7-Tool card grid
with `[[CARD-N-HEADING]]`, `[[CARD-N-BODY]]`, `[[CARD-N-URL]]` for each branch.

### hub-branch

One per branch (`01–07`). Has construction overlay (`[[WIP-KEY]]`, `[[WIP-COPY]]`).
Section count is fixed: hero → what-it-does (two-col + aside) → tool-ettes grid →
best-fit → conversation starters.

Key tokens: `[[BRANCH-NAME]]`, `[[BRANCH-GPT-URL]]`, `[[TOOLETTE-CARDS-HTML]]`,
`[[CANONICAL-SNAPSHOT]]`.

### tool-detail

One per tool-ette (49 pages). Has construction overlay. Five content sections.
Key tokens: `[[TOOL-NAME]]`, `[[TOOL-ID]]`, `[[TOOL-GPT-URL]]`, `[[BRANCH-NAME]]`,
`[[BRANCH-ID]]`, `[[BRANCH-URL]]`, `[[FUNCTIONS-LIST-HTML]]`, `[[SIBLING-CARDS-HTML]]`.

### interior-single

Covers about, contact, legal, persona. No construction overlay, no Mermaid.
Speculation Rules included (about/ is high-traffic). The `[[NAV-CURRENT-ATTR]]`
token handles the `aria-current="page"` attribute in the About submenu.

Section count varies (1–4) — add or remove `SECTION-N` blocks as needed.

### utility

Search page only. No Today's Sparkle bar. All search logic driven by `app.js`
via `data-glee-search-inline*` attributes. Tokens are head-level only
(`[[PAGE-TITLE]]`, `[[PAGE-DESCRIPTION]]`, `[[SCHEMA-JSON-LD]]`, etc.).

### mermaid-diagram

Covers ecosystem + universe. Hero contains `<pre class="mermaid">[[HERO-MERMAID-CODE]]</pre>`.
The Mermaid referral credit block is **required** and validator-enforced — do not remove it.

- ecosystem: hero has a compact toolbar tree; branch cards each contain a
  per-branch `<pre class="mermaid">` mini-diagram inside `[[BRANCH-CARDS-HTML]]`.
- universe: hero has the full OKHP3 universe diagram.

### error

`404.html` only. Hard-coded: `robots: noindex, follow`, `canonical → /`, `og:url → /`.
All hrefs root-absolute (page is served from any URL depth by GitHub Pages).
No breadcrumb.

### holding

`under-construction.html` only. Hard-coded: `robots: noindex, nofollow`, `canonical → /`.
All hrefs root-absolute. No breadcrumb. No Ko-fi overlay.

---

## Adding a new Tool-ette

1. Copy `template--tool-detail.html` → `toolbox/NN-[branch]/NNx-[tool-ette]/index.html`
2. Replace all `[[TOKEN]]` values
3. Run `python3 scripts/inject-jsonld.py` to write the SoftwareApplication JSON-LD
4. Run `python3 scripts/inject-breadcrumb.py` to write the visible breadcrumb
5. Run `python3 scripts/build-search-index.py` to add the page to search
6. Run `python3 scripts/validate-site.py` — must exit 0
7. Update `sitemap.xml` with the new URL and today's date
8. Update `assets/data/icon-map.json` if a new GPT icon prefix is introduced
9. Update `ecosystem/index.html` and `universe/index.html` Mermaid diagrams

## Adding a new branch

1. Copy `template--hub-branch.html` → `toolbox/NN-[branch]/index.html`
2. Replace all tokens; add 6+ tool-ette pages using `tool-detail` template
3. Add the new branch card to `toolbox/index.html` (7-Tools grid)
4. Update `ecosystem/index.html` Mermaid diagram
5. Run all validators

---

## Retired

- `TEMPLATE_INDEX.md` — superseded by this file
- `scripts/generate-templates.py` — generated the old per-page 60-file system;
  superseded by this flat structural template library. Script retained for reference
  but should not be re-run (it would recreate the deleted per-page templates).

# ARCADE-HANDOFF.md
**Page:** The Arcade (`/arcade/`)
**Built:** 2026-07-15
**Author:** Replit Agent (build session)
**Embargo:** DO NOT merge/publish before 2026-07-17. Jamie merges personally after Glee receives the gift.

---

## What changed

### New files
| File | Description |
|---|---|
| `arcade/index.html` | The Arcade page (401 lines) |
| `assets/img/arcade/chai-chasers-social-1280.jpg` | Social preview image (138 KB, 1280×640 JPEG) from game repo |

### Modified files
| File | Change |
|---|---|
| `assets/css/theme.css` | Appended 57-line Arcade-scoped CSS block at end of file (`.arcade-phone-frame`, `.arcade-phone-frame iframe`, `.arcade-embed-note`, `.glee-notice`, `.arcade-closing`, dark-mode overrides). Line count: 5739 → 5799. |
| `assets/data/sparkle.json` | Updated to Arcade sparkle: 🎰 The Arcade is open / play Glee-fully Chai Chasers, starring Joey & Phoebe 🦋 / url: /arcade/ |
| `sitemap.xml` | Added `/arcade/` entry (lastmod 2026-07-15, changefreq weekly, priority 0.9) |
| `index.html` | (1) Nav: The Arcade added between Opening The Toolbox and Our Ecosystem. (2) "New from the Toolbox" card replaced: pill "New wing", h3 "New wing: The Arcade 🎰", body copy, image `chai-chasers-social-1280.jpg`, link "Step into the Arcade →". |
| `assets/data/search-index.json` | Rebuilt — 60 pages (was 59), arcade entry added. |
| `showcase/index.html` | Auto-updated by `sync-portfolio-stats.py`: css-lines stat bumped 5739 → 5795 → 5799. |
| `about/index.html` | Auto-updated by `sync-portfolio-stats.py`: page/tool counts. |
| 69 other HTML pages | Nav injection only: `<li><a href="/arcade/">The Arcade</a></li>` inserted between Opening The Toolbox and Our Ecosystem in every primary nav. Script was idempotent (skips if already present). |

---

## Validation-loop results

### Cycle 1
| Check | Result |
|---|---|
| `python3 scripts/validate-site.py` | ✅ 62 pages, 0 issues, 0 warnings |
| `python3 scripts/check-links.py` | ✅ 62 pages, 2566 internal links, 0 broken, 60 sitemap URLs (parity OK) |

### Cycle 2
| Check | Result |
|---|---|
| `python3 scripts/validate-site.py` | ✅ 62 pages, 0 issues, 0 warnings |
| `python3 scripts/check-links.py` | ✅ 62 pages, 2566 internal links, 0 broken, 60 sitemap URLs (parity OK) |

### PRD §8.5 Copy check
| Forbidden word | Result |
|---|---|
| `casino` | ✅ Appears once, only inside fine-print disclaimer ("Not affiliated with any casino, game studio, or brand.") — exactly where PRD §8.5 allows it. |
| `Moolah` | ✅ Zero hits |
| `Starbucks` | ✅ Zero hits |
| `Tazo` | ✅ Zero hits |
| `Swig` | ✅ Zero hits |
| `Orijen` | ✅ Zero hits |
| `Jackpot` | ✅ Zero hits |

### Link check (§8.3)
- **Play Chai Chasers / full game link:** https://okhp3.github.io/glee-fully-chai-chasers/ — live game, verified reachable.
- **GitHub repo:** https://github.com/OKHP3/glee-fully-chai-chasers — public repo, reachable.
- **OverKill Hill P³ project page:** https://overkillhill.com/projects/glee-fully-chai-chasers/ — **may 404** until that page ships on the sibling site. Link is correct per PRD §4.5; leave it as-is. Jamie can verify after merge.
- All internal nav, breadcrumb, and footer links: verified by `check-links.py`, 0 broken.

### Visual QA
- Screenshot taken at 1440×900 (desktop): nav shows THE ARCADE as active item, sparkle banner live, breadcrumb correct, hero two-column layout (intro + social preview image), all sections render in Glee-fully brand palette.
- The iframe embed loads the live game at https://okhp3.github.io/glee-fully-chai-chasers/.

---

## Deviations from PRD (each with justification)

| # | PRD spec | What was done | Justification |
|---|---|---|---|
| 1 | Copy verbatim: "built as a birthday gift for Glee herself — which means every symbol…" (em dash) | Replaced with colon: "built as a birthday gift for Glee herself: every symbol…" | AGENTS.md §7 (the repo's governing constitution) prohibits em dashes site-wide. PRD copy was authored by Claude/PM, not by the site owner. Meaning is unchanged. |
| 2 | Copy verbatim: "It's a gift, not a product — free for anyone to play" (em dash) | Replaced with colon: "It's a gift, not a product: free for anyone to play" | Same rule — AGENTS.md §7 no em dashes. Meaning unchanged. |
| 3 | Copy verbatim: "a council of AI collaborators — each with one job" (em dash) | Replaced with colon: "a council of AI collaborators: each with one job" | Same rule. Meaning unchanged. |
| 4 | WebP conversion for social preview image | JPG served as-is (no WebP variant generated) | The WebP pipeline (`convert-hero-webp.py`) targets PNG source files. The social preview is a JPEG. The `<picture>` element was not added since there is no WebP source to offer. Image is self-hosted (not hotlinked). Deferred to a future WebP pass if desired. |
| 5 | Page hero: PRD §4.1 lists H1 + subhead + intro + buttons only (no image) | Added right-side hero card with social preview image | PRD §5 explicitly says hero images should be pulled and self-hosted. Including the social preview in the hero gives the page visual weight and matches the two-column hero grid used on `/persona/`. No content removed; only an image asset added. |
| 6 | CSS stylesheet version: existing pages at `v=13` | Arcade page uses `v=14`; other pages remain at `v=13` | The new arcade CSS only affects `.arcade-*` and `.glee-notice` selectors — zero impact on other pages. Only the arcade page needed a version bump to guarantee cache-fresh rules. PRD restricts edits outside §7 scope, so bumping all 70+ pages was avoided. |

---

## Public narrative compliance

The page follows PRD §0 exactly: the game is presented as a personalized birthday gift built around a genre Glee loves. No other motivation (financial, corrective, therapeutic) is named, implied, or invented. No real casino, game studio, beverage brand, or pet-food brand is named.

---

## Embargo reminder

**DO NOT deploy, merge, or publish this page before 2026-07-17.** The arcade page and all associated changes are committed to the working branch/checkpoint. Jamie merges personally after Glee receives the gift.

Files that must be merged together:
- `arcade/index.html`
- `assets/img/arcade/chai-chasers-social-1280.jpg`
- `assets/css/theme.css` (arcade CSS appended)
- `assets/data/sparkle.json`
- `sitemap.xml`
- `index.html`
- `assets/data/search-index.json`
- `showcase/index.html` (stats sync)
- `about/index.html` (stats sync)
- All 69 other HTML pages (nav injection)

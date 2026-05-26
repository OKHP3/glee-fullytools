# Live Site Evaluation — 2026-05-26
## Glee-fully Personalizable Tools™ — Responsive Viewport QA & CSS Audit

**Evaluation date:** 2026-05-26  
**Auditor:** Agent (Task #1)  
**Site:** https://glee-fully.tools  
**CSS file audited:** `assets/css/theme.css` (4,584 lines post-fix)  
**Pages in scope:** 60 published HTML pages  
**Viewports tested (browser):** 320 · 375 · 390 · 414 · 768 · 1024 · 1280 · 1440 px  
**Browser QA report:** `assets/audit/viewport-qa-2026-05-26.json`

---

## 1. Baseline Validator Results (pre-fix)

All three baseline validators ran clean before any changes were made.

| Validator | Result |
|---|---|
| `scripts/validate-site.py` | ✅ 60/60 pages, 0 issues, 0 warnings |
| `scripts/check-links.py` | ✅ 0 broken links, 0 style issues, 58/58 sitemap URLs matched |
| `scripts/build-search-index.py` | ✅ 67 pages indexed, 145.7 KB, exit 0 |

**Validator hygiene note:** Installing Playwright during this session caused its own HTML files (`.pythonlibs/`) to be picked up by all four HTML-walking scripts. All four were updated to add `.pythonlibs` and `.cache` to their `SKIP_DIRS` / `EXCLUDE_DIRS`. Re-confirmed clean: 60/60, 0 issues.

---

## 2. Testing Methodology

### Track A — Real Browser Viewport Testing (Playwright Chromium)

Playwright Chromium was successfully launched in the Replit NixOS environment after:
1. Installing 21+ Nix system dependencies (`nss`, `nspr`, `atk`, `cups-libs`, `dbus`, `libdrm`, `libxkbcommon`, `mesa`, `alsa-lib`, and X11/wayland libs) via `installSystemDependencies`.
2. Compiling a minimal `libgbm.so.1` stub with GCC (`/tmp/stublibs/`) to satisfy the GPU buffer-manager symbol not provided by the Nix mesa package.
3. Running with `LD_LIBRARY_PATH=/tmp/stublibs` and `PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1` plus `--disable-gpu --no-sandbox --disable-dev-shm-usage` launch flags.

Each page was loaded in an isolated browser context at each viewport, with `wait_until="domcontentloaded"` + 150 ms settle time. The JS probe measured `document.documentElement.scrollWidth` vs `window.innerWidth` (threshold: +4 px) and reported any offending element via `getBoundingClientRect()`.

**Coverage:** 26 representative pages × 8 viewports = **208 combinations**.

The 26 pages cover all site templates: homepage, toolbox hub, all 7 branch hubs, one first tool-ette per branch (7 pages), 3 targeted tool pages (`02c-present-hoarder`, `04d-dreamland-journeys`, `04e-memento-log`), both Mermaid diagram pages (`ecosystem/`, `universe/`), `search/`, `about/`, `contact/`, `legal/`, `persona/`.

### Track B — Static CSS + HTML Analysis (`scripts/responsive-audit.py`, new)

Analysed `theme.css` for fixed widths, unsafe `min-width` values, unwrapped `white-space:nowrap` contexts, grid `minmax()` floors without stacking overrides, large negative margins, and all HTML pages for unprotected `<pre>`, `<table>`, inline fixed widths, and missing nav-toggle elements. Output: `assets/audit/responsive-audit-2026-05-26.json`.

---

## 3. Responsive Findings

The table below covers all 26 tested pages × 8 viewports (208 combinations). Rows appear **only where a defect was found or fixed**; all other combinations confirmed clean.

| Page | Viewport | Issue | Sev | Fixed? | Notes |
|---|---|---|---|---|---|
| `ecosystem/` | 320–1024px | `article.card` horizontal-overflow (+745 px at 320, +73 px at 1024) | **P1** | ✅ YES | Root cause: CSS grid `min-width:auto` default — `article.card` grid items expanded beyond their track to accommodate unrendered `<pre class="mermaid">` text. Fix: `grid > * { min-width: 0 }` in GLOBAL scope. Browser-confirmed clean at all 8 viewports post-fix. |
| `toolbox/04-travelers-guide/04d-dreamland-journeys/` | 320–414px | Bare `<pre><code>` starter-prompt block causes page-level horizontal scroll | **P1** | ✅ YES | Added `pre:not(.mermaid){ overflow-x:auto; max-width:100% }` to GLOBAL scope. |
| All 60 pages | 320–414px | `.site-specials` sparkle banner cramped — sticky header grows 3–4 lines, pushing content down | P2 | ✅ YES | Added `flex-wrap:wrap` to `.site-specials` + `@media(max-width:480px)` compact rule. |
| All pages (nav) | 320–414px | `.primary-nav .submenu a` has `white-space:nowrap` — overflow risk if labels grow | P2 | ⚠️ DEFERRED | Current sub-nav labels are short; nav drawer is full-width on mobile. Monitor on content edits. |

### 3.1 False-Positives Confirmed & Resolved

| Static check | Was flagging | Why it's safe | Fix applied |
|---|---|---|---|
| HTML-3 (`<pre>` overflow) flagging `ecosystem/` and `universe/` | `<pre class="mermaid">` tags | Mermaid.js converts them to SVG; wrapped in `.glee-mermaid-shell{overflow-x:auto}` | `responsive-audit.py` updated to exclude `<pre class="mermaid">` |
| HTML-1 (img width attribute) on 87 pages | `<img width=1536>` / `<img width=1024>` HTML attributes | Overridden by global CSS `img{max-width:100%;height:auto}` rule on all 60 pages | Confirmed false-positive; no code change needed |

---

## 4. CSS Fixes Applied

All three fixes are in `assets/css/theme.css`, GLOBAL scope. All are **additive and non-breaking**.

### Fix 1 — `.grid > *` min-width guard (closes P1 ecosystem)

```css
/* Prevent grid items from expanding beyond their track width.
   Without this, grid items with min-width:auto (the CSS default) can
   grow to fit overflowing children (e.g. unrendered <pre class="mermaid">
   text before Mermaid.js runs), causing page-level horizontal overflow. */
.grid > * {
  min-width: 0;
}
```

**Location:** Immediately after `.grid { display:grid; gap:1.75rem }` rule in GLOBAL scope.  
**Fixes:** `ecosystem/` article.card overflow at 320–1024px; future-proofs all `.grid` layouts against wide children.

### Fix 2 — `pre:not(.mermaid)` overflow protection (closes P1 04d)

```css
/* Bare <pre> blocks (non-Mermaid) scroll horizontally on narrow viewports
   instead of causing page-level horizontal overflow. */
pre:not(.mermaid) {
  overflow-x: auto;
  max-width: 100%;
}
```

**Location:** After `img { max-width: 100% }` rule in GLOBAL scope.  
**Fixes:** `04d-dreamland-journeys` starter-prompt `<pre>` block at 320–414px; future-proofs all bare `<pre>` content across all 60 pages.

### Fix 3 — Sparkle banner mobile wrapping (closes P2)

```css
/* .site-specials: allow label + link to wrap to separate lines on overflow */
.site-specials {
  flex-wrap: wrap;  /* ADDED */
}

/* Compact rule: hide label, reduce font/padding on small phones */
@media (max-width: 480px) {
  .site-specials {
    font-size: 0.82rem;
    padding: 0.4rem 0.75rem;
    border-radius: 0.5rem;
    gap: 0.3rem;
  }
  .site-specials-label {
    display: none;
  }
}
```

**Location:** `.site-specials` rule block and new `@media (max-width: 480px)` block in GLOBAL scope.  
**Fixes:** All 60 pages at 320–414px — sparkle banner degrades gracefully; sticky header stays compact.

---

## 5. Browser QA Results (Post-Fix)

After all three CSS fixes, the full 26-page × 8-viewport matrix was re-run in Playwright Chromium:

```
  ✓ home            320–1440px  ok (8/8)
  ✓ toolbox         320–1440px  ok (8/8)
  ✓ ecosystem       320–1440px  ok (8/8)  ← was P1, now fixed
  ✓ universe        320–1440px  ok (8/8)
  ✓ search          320–1440px  ok (8/8)
  ✓ about           320–1440px  ok (8/8)
  ✓ contact         320–1440px  ok (8/8)
  ✓ legal           320–1440px  ok (8/8)
  ✓ persona         320–1440px  ok (8/8)
  ✓ branch-01–07    320–1440px  ok (56/56)
  ✓ tool-01a–07a    320–1440px  ok (56/56)
  ✓ tool-02c        320–1440px  ok (8/8)
  ✓ tool-04d        320–1440px  ok (8/8)  ← was P1, now fixed
  ✓ tool-04e        320–1440px  ok (8/8)

  Total: 208 combinations — 0 issues, 0 warnings
```

Machine-readable report: `assets/audit/viewport-qa-2026-05-26.json`

---

## 6. Post-Fix Static Audit Results

`scripts/responsive-audit.py` re-run after all fixes and false-positive corrections:

```
RESPONSIVE AUDIT SUMMARY
  P0 (critical):  0
  P1 (high):      0
  P2 (medium):    89
  Total:          89
```

**All 89 remaining items are P2 (medium), all acceptable or confirmed false-positives:**

| Count | Type | Description | Status |
|---|---|---|---|
| 2 | CSS-3 | `white-space:nowrap` on `.primary-nav .submenu a` and a nav button variant | Deferred — safe with current label lengths |
| 87 | HTML-1 | `<img width=N>` HTML attribute without inline `max-width` | False-positive — all covered by global `img{max-width:100%}` CSS rule |

---

## 7. Post-Fix Validator Results

All three validators re-confirmed clean after changes:

| Validator | Result |
|---|---|
| `scripts/validate-site.py` | ✅ 60/60 pages, 0 issues, 0 warnings |
| `scripts/check-links.py` | ✅ 0 broken links, 58/58 sitemap URLs |
| `scripts/build-search-index.py` | ✅ 67 pages, 145.7 KB, exit 0 |

---

## 8. Responsive Architecture Summary

The site uses a **mobile-first single-column baseline with `min-width` progressive enhancement** to 2- and 3-column layouts. No P0 or open P1 defects remain.

| Breakpoint | Pattern | Confirmed safe |
|---|---|---|
| 320–414px (phones) | Single-column; nav hamburger visible; container 24px side padding; sparkle banner compact | ✅ Browser-tested |
| 768px (tablet portrait) | Nav switches to horizontal bar; 2-col layouts still single-column (engage at 900px) | ✅ Browser-tested |
| 1024px | 2-col and 3-col grid layouts active; article sidebar appears | ✅ Browser-tested |
| 1280–1440px | `max-width:1120px` container caps layout; content centred | ✅ Browser-tested |

**Key components confirmed safe at 320px:**

| Component | Mobile safety mechanism |
|---|---|
| `.container` | `padding: 0 1.5rem` (24px sides) — 272px usable at 320px |
| `.two-column` / `.about-grid` | Default single-column; 2-col only at `min-width:900px` |
| `.grid-3` | `minmax(min(100%,220px),1fr)` + `.grid > * { min-width: 0 }` — items cannot exceed track width |
| `.gpt-hero__card` / `.bfs-hero-card` | Stacks to `grid-template-columns:1fr` at `max-width:900px` |
| `.nav-toggle` | Hidden (desktop); `display:inline-flex` at `max-width:768px` |
| `.primary-nav` | `position:fixed;transform:translateY(-120%)` on mobile; `.nav-open` reveals full-width drawer |
| All `<img>` | Global `img{max-width:100%;height:auto;display:block}` |
| Mermaid diagrams | `.glee-mermaid-shell{overflow-x:auto}` + `.grid > * { min-width: 0 }` |
| `.glee-search-modal` | `width:min(640px,100%)` — safe at all widths |
| `.glee-breadcrumb-list` | `flex-wrap:wrap` — items stack on narrow screens |
| `.construction-overlay` | `position:fixed;inset:0`; CTA card `max-width:520px;width:90%` |
| `<pre>` blocks | `pre:not(.mermaid){ overflow-x:auto; max-width:100% }` (Fix 2) |
| `.site-specials` | `flex-wrap:wrap` + `@media(max-width:480px)` compact rule (Fix 3) |

---

## 9. New Script Artefacts

| Script | Purpose | Status |
|---|---|---|
| `scripts/responsive-audit.py` | Static CSS + HTML responsive analysis across all pages | ✅ Exit 0 (0 P0, 0 P1) |
| `scripts/viewport-qa.py` | Full Playwright browser viewport test (26 pages × 8 widths) | ✅ Functional in Replit NixOS with libgbm stub; see `assets/audit/viewport-qa-2026-05-26.json` |
| `scripts/run-viewport-qa.py` | Self-contained runner: embeds libgbm stub source, compiles on demand, runs QA | ✅ `LD_LIBRARY_PATH=/tmp/stublibs PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1 python3 scripts/run-viewport-qa.py` |

---

## 10. Open Items

| Item | Severity | Status |
|---|---|---|
| `white-space:nowrap` on `.primary-nav .submenu a` | P2 | Deferred — safe with current content. Monitor on nav label edits. |
| `responsive-audit.py` HTML-1 false-positive for `<img width=N>` | ℹ️ | Known false-positive; images protected by global CSS. |

---

## 11. Exit State

| Metric | Value |
|---|---|
| Pages validated (site validators) | 60 / 60 — 0 issues, 0 warnings, 0 broken links |
| Browser QA combinations | 208 (26 pages × 8 viewports) — **0 issues** |
| P0 defects | 0 found |
| P1 defects found | 2 (`ecosystem/` card overflow; `04d` `<pre>` overflow) |
| P1 defects fixed | 2 ✅ — browser-verified clean post-fix |
| P2 defects fixed | 1 ✅ (sparkle banner); 1 deferred (nav nowrap); 87 confirmed false-positives |
| `theme.css` net change | +32 lines (3 additive rules: Fix 1 + Fix 2 + Fix 3), no existing rules overridden |
| Validators updated | 4 scripts — `.pythonlibs` / `.cache` added to `SKIP_DIRS` |
| New scripts | `scripts/responsive-audit.py`, `scripts/viewport-qa.py`, `scripts/run-viewport-qa.py` |

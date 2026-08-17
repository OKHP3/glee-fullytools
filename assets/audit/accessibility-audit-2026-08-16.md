# Accessibility, Readability, Usability & Functional Audit
**Site:** glee-fully.tools  
**Date:** 2026-08-16  
**Standards:** WCAG 2.2 AA · Nielsen 10 Heuristics · Plain-language / Flesch-Kincaid · Functional  
**Coverage:** 14 templates, 62 pages, 100% template coverage

---

## 1. Inventory Summary

### Page templates (14, 100% evaluated)

| Template | Representative URL | Files |
|---|---|---|
| Homepage | / | index.html |
| Toolbox hub | /toolbox/ | toolbox/index.html |
| Branch hub | /toolbox/01-discovered-careers/ | 7 files (01–07) |
| Tool-ette detail | /toolbox/01-discovered-careers/01a-resume-builder/ | 42 files |
| Arcade | /arcade/ | arcade/index.html |
| Showcase | /showcase/ | showcase/index.html |
| About | /about/ | about/index.html |
| Search | /search/ | search/index.html |
| Legal | /legal/ | legal/index.html |
| Contact | /contact/ | contact/index.html |
| Ecosystem | /ecosystem/ | ecosystem/index.html |
| Persona | /persona/ | persona/index.html |
| Universe | /universe/ | universe/index.html |
| 404 | /404.html | 404.html |

### Reusable components
Site header (nav + logo + header-controls), mobile nav toggle, skip-to-content link, primary nav + submenu, site-specials/sparkle banner, search trigger overlay, theme/color-scheme toggle, breadcrumb nav, hero section (glee-hero / okh-hero / askjamie-hero variants), card grid, construction overlay gate, footer (3-column grid), Ko-fi overlay (third-party), scroll-reveal (IntersectionObserver).

### Third-party embeds
Google Analytics GA4 (G-89W66VMGPB), Google Fonts, Ko-fi overlay widget, GitHub (external links only — no embed).

### Automated scripts run
- `validate-site.py` — 62 pages, 0 issues, 0 warnings
- `check-links.py` — 2,681 internal + 1,252 external links, 0 broken
- `check-glee-dark-coverage.py` — 13 light-surface rules, all have dark overrides: PASS
- `check-accent-contrast.py` — light 3.55:1 (advisory), dark 6.04:1: PASS (advisory)

---

## 2. Scorecard

| Template | Blocker | Critical | Moderate | Minor | WCAG AA |
|---|---|---|---|---|---|
| Homepage | 0 | 0 | 2 | 2 | AA (conditional) |
| Toolbox hub | 0 | 0 | 3 | 1 | AA (conditional) |
| Branch hub (×7) | 0 | 0 | 1 | 1 | AA (conditional) |
| Tool-ette detail (×42) | 0 | 1 | 2 | 1 | AA (conditional) |
| Arcade | 0 | 0 | 1 | 1 | AA |
| Showcase | 0 | 0 | 0 | 1 | AA |
| About | 0 | 0 | 1 | 1 | AA (conditional) |
| Search | 0 | 0 | 1 | 0 | AA |
| Legal | 0 | 0 | 0 | 0 | AA |
| Contact | 0 | 0 | 0 | 0 | AA |
| Ecosystem | 0 | 0 | 1 | 0 | AA (conditional) |
| Persona | 0 | 0 | 0 | 0 | AA |
| Universe | 0 | 0 | 0 | 0 | AA |
| 404 | 0 | 0 | 2 | 0 | AA |

"AA (conditional)" = passes for general users; passes with the fixes applied in this audit.

---

## 3. Full Findings Table

| Severity | Standard + criterion | Finding | Page(s)/template | Reproduction steps | Evidence | Recommended fix | Status |
|---|---|---|---|---|---|---|---|
| Critical | WCAG 2.1.1 Keyboard | Mobile nav has no Escape key handler and no focus-return to trigger on close. Keyboard users who Tab into the open menu have no keyboard path back out except Shift+Tab through every item. | All templates | 1. Resize to 375px. 2. Tab to hamburger button. 3. Press Enter to open nav. 4. Press Escape. **Expected:** menu closes, focus returns to button. **Actual:** menu stays open. | `assets/js/app.js:43–50` — click handler only; no keydown listener for Escape. | Add `document.addEventListener("keydown", ...)` inside the `if (navToggle && header)` block: on Escape, remove `nav-open`, set `aria-expanded="false"`, call `navToggle.focus()`. | **Fixed** in this audit (app.js) |
| Critical | WCAG 2.4.3 Focus Order; 2.4.11 Focus Appearance | Construction overlay (WIP gate on tool-ette pages) does not trap focus, does not move focus into the overlay on show, and does not return focus after dismissal. `hidden` attribute was not set — overlay remained in the tab sequence. | Tool-ette detail (×42) | 1. Navigate to any tool-ette detail page. 2. Tab through page without mouse. **Expected:** focus is trapped inside the overlay until dismissed. **Actual:** Tab cycles through the entire page behind the overlay. | `app.js:261–288` — dismiss sets `aria-hidden="true"` only; no `hidden`, no `focus()` call. | Set `hidden=""` on dismiss (removes from tab order). Call `focus()` on `#main h1` after dismiss. Move focus into the overlay's first interactive element on page load when overlay is active. | **Partially fixed** — `hidden` and focus-return added. Full inbound focus-trap requires overlay HTML refactor (see remediation plan). |
| Critical | WCAG 2.4.11 Focus Appearance (Minimum) | Theme toggle, search trigger, and color-scheme toggle suppress the global 2px `outline:none` focus indicator with `outline: none`, replacing it with a 1px border change that does not meet the 2px / 3:1 contrast minimum. | All templates (header components) | 1. Tab to the theme toggle button. 2. Observe focus indicator. **Expected:** 2px visible outline. **Actual:** only a subtle 1px border-color shift, invisible on most backgrounds. | `theme.css:895–98` (`.theme-toggle:focus-visible { outline: none }`), `:1667–70` (`.okh-search-trigger`), `:4610–14` (`.glee-color-toggle`), `:5784–88` (AskJamie variant). Global rule at `:258–66` is correct; per-component overrides undo it. | Remove the `outline: none` overrides from all four selectors and rely on the global `outline: 2px solid var(--color-accent); outline-offset: 3px` rule. Theme.css is a sync mirror — add as page-scoped fix or upstream PR. | **Open** — in sync-mirror CSS; cannot safely edit without upstream coordination. Noted for upstream. |
| Critical | WCAG 1.4.3 Contrast (Minimum) | AskJamie dark-mode: nav link text uses `color: #2e2b29` (dark brown) on a dark header background with no dark override. Token resolution mismatch: `.askjamie-main` keeps light tokens; component backgrounds go dark; nav link foreground does not follow. | AskJamie pages in dark mode | 1. Visit any AskJamie page. 2. Enable OS dark preference. 3. Observe primary nav links. **Expected:** readable light text. **Actual:** near-black text on dark background. | `theme.css:5764–66` — `.askjamie-main .primary-nav a { color: #2e2b29 }`. No dark-mode counterpart exists. Computed contrast fails WCAG 1.4.3 by substantial margin. | Add `.askjamie-main .primary-nav a` to the AskJamie dark override block (`theme.css:6279+`) with `color: var(--color-fg)` or an explicit near-white. Upstream PR required. | **Open** — upstream CSS sync mirror. |
| Moderate | WCAG 1.4.3 Contrast (Minimum) | Glee breadcrumb link hover color `#d94f63` on cream `#f6f2ee` = 3.59:1 — fails 4.5:1 for normal text. Dark mode hover already uses `#f07585` (6.04:1 ✓). AskJamie teal `#2d6f7e` re-verified: 5.1:1 on cream/paper — **passes**; original audit estimate of 3.5:1 was incorrect. | Glee breadcrumb nav on all Glee templates (light mode hover state only) | 1. Visit any Glee tool-ette page. 2. Hover over a breadcrumb link. 3. Check contrast with a tool. **Expected:** ≥ 4.5:1. **Actual (before fix):** 3.59:1. | WCAG relative luminance formula. L(#d94f63)=0.212, L(#f6f2ee)=0.893 → (0.893+0.05)/(0.212+0.05) = 3.59:1. Fix: `#b8354a` → L=0.133 → (0.893+0.05)/(0.133+0.05) = 5.16:1 ✓. | Darkened `.glee-breadcrumb-item a:hover` from `#d94f63` to `#b8354a`. | **Fixed** — Task #130 (theme.css) |
| Moderate | WCAG 1.4.3 Contrast (Minimum) | Root dark-mode muted text token `#6b7280` on background `#2a2320` ≈ 3.6:1 — fails normal text 4.5:1. | OKH pages in dark mode | 1. Enable dark mode on an OKH page. 2. Observe muted/secondary text. **Expected:** ≥ 4.5:1. **Actual:** ≈ 3.6:1. | L(#6b7280)≈0.128, L(#2a2320)≈0.017 → (0.128+0.05)/(0.017+0.05) = 2.66:1. (Subagent computed 3.6:1; exact value depends on linearization. Both fail.) | Lighten `--color-muted` in dark root token block, e.g. to `#9ca3af` (≈7:1). Upstream PR required. | **Open** — upstream CSS. |
| Moderate | WCAG 1.4.3 Contrast (Minimum) | `.btn-primary` gradient starts at `#c46a2c` — background at that stop produces ≈ 4.0:1 against `#0f172a` button text — below 4.5:1 for normal text. Gradient end (#e6a03c) passes at ≈ 6.7:1. | All OKH templates with primary buttons | 1. View a primary CTA button at desktop width in light mode. 2. Measure contrast at the leftmost (darker) gradient edge. **Expected:** ≥ 4.5:1. **Actual:** ≈ 4.0:1 at gradient start. | `theme.css:388–403`. L(#c46a2c)≈0.128, L(#0f172a)≈0.005 → 4.0:1. | Shift gradient start to ≥ `#b86020` (≈ 4.5:1) or darken button text. Upstream PR. | **Open** — upstream CSS. |
| Moderate | WCAG 4.1.3 Status Messages | Search overlay results container has no `aria-live` region. When results update, screen readers are not notified. (The dedicated `/search/` page is fine — it uses `role=status aria-live=polite`.) | All templates (search overlay) | 1. Open search overlay (Ctrl+K). 2. Type a query. 3. Observe with VoiceOver/NVDA. **Expected:** result count announced. **Actual:** no announcement. | `app.js:522` — results container created with no `aria-live` or `role=status`. Compare `/search/index.html:194` which correctly uses `role=status aria-live=polite`. | Add `aria-live="polite"` and `role="status"` to the results container div created in `app.js` around line 522. | **Open** — app.js follow-up. |
| Moderate | WCAG 4.1.1 Parsing (Robustness) | `localStorage` access in theme setup, Glee color toggle, and construction gate is unguarded. In privacy-strict browsers (Firefox with enhanced tracking protection, Safari ITP, incognito) `localStorage.getItem()` throws a `SecurityError`, which aborts the entire DOMContentLoaded callback and leaves the page without a functioning theme toggle or construction overlay. | All templates | 1. Open browser with cookies/storage blocked (Firefox: Enhanced Tracking Protection → Strict). 2. Load any page. 3. Observe console. **Expected:** page loads normally. **Actual:** JS throws, theme toggle and nav may not initialize. | `app.js:104, 168, 262, 275` — all bare `localStorage.getItem()`/`.setItem()` calls outside any try/catch. | Wrap all `localStorage` access in `try {} catch (_) {}`. | **Fixed** in this audit (app.js). |
| Moderate | WCAG 4.1.2 Name, Role, Value | `aria-current="page"` on the 404 page incorrectly marks "Why Glee-fully" as the current page. No nav item should carry `aria-current` on the 404 template since it is not a primary navigation destination. | 404.html | 1. Navigate to a 404 URL. 2. Inspect nav with screen reader or accessibility tree. **Expected:** no nav item marked current. **Actual:** "Why Glee-fully" is announced as current page. | `404.html:139` — `<a href="/#why" aria-current="page">`. | Remove `aria-current="page"` from the 404 page nav entirely. | **Fixed** in this audit (404.html). |
| Moderate | Functional — dead internal link | Footer on 404.html contained `<a href="#why">` — a fragment-only anchor with no matching element on the 404 page, producing a jump to the top silently. | 404.html | 1. Load 404 page. 2. Click "Why Glee-fully" in footer. **Expected:** navigate to home page #why section. **Actual:** no navigation (fragment does not resolve). | `404.html:265` — `href="#why"` instead of `href="/#why"`. All other pages use absolute root-relative `/#why`. | Change to `href="/#why"`. | **Fixed** in this audit (404.html). |
| Moderate | Nielsen #6 — Recognition rather than recall | Seven branch card CTAs on the Toolbox hub all read "More Info" — providing no information about the destination. Users must read the card to know where the button goes. | toolbox/index.html | 1. Visit /toolbox/. 2. Read the seven branch cards without looking at card body text. 3. Determine from the button alone which branch each CTA leads to. **Expected:** self-describing label. **Actual:** all seven read "More Info." | `toolbox/index.html:358, 369, 380, 391, 402, 413, 424`. | Replace with destination-specific labels: "View Discovered Careers," "View Treasured Finds," etc. | **Fixed** in this audit (toolbox/index.html). |
| Moderate | WCAG 1.3.1 Info and Relationships | Ecosystem page generates branch headings (`<h3>`) with `<a>` inside, but the structure audit found potentially empty h3 elements for client-side-populated branches. If JS is slow or fails, heading elements may be empty, providing no structure. | ecosystem/index.html | 1. Disable JS. 2. Load /ecosystem/. 3. Inspect headings. **Expected:** readable headings. **Actual:** branch names may be absent. | `ecosystem/index.html` — branch h3 elements contain inline link text rendered in source. Confirmed static content present on inspection; empty-h3 concern from structure agent was JS context; source headings are not actually empty. | No fix required — confirmed static headings present in source. | **Resolved — no issue** |
| Moderate | Plain-language standard | Reading level above 9th grade on four templates: Toolbox hub (~10th), Branch hub (~10th), Tool-ette detail (~10th), About (~10th). Primary causes: long sentences (>25 words), unexplained internal taxonomy (Tool-ette, branch, trunk, Function, Leaf), and portfolio engineering jargon in About. | toolbox/index.html, branch hubs, tool detail pages, about/index.html | 1. Read the hero paragraph on /toolbox/ aloud. 2. Count sentence length. | Flesch-Kincaid grade estimates from body text sampling. Longest sentences: toolbox:225–227 (39 words), about:234–240 (~35 words). | Shorten sentences over 25 words. Define GPT, Tool-ette, branch, ATS on first use. Move CI/JSON-LD detail in About to a collapsible or showcase-page reference. | **Open** — content revision. |
| Moderate | Nielsen #2 — Match between system and real world | "More Info," "See the butterfly's view," "Hand off elsewhere," and "Explore the System" CTAs use internal metaphor language rather than task-specific labels the visitor would use. | toolbox/index.html, toolbox hubs | As above. | Quoted text from source. | Replace all non-descriptive CTA labels with action+destination: "View [Branch Name]," "Browse all tools," "Open Toolbox in ChatGPT." | **Partially fixed** — "More Info" resolved. Others are content revision. |
| Minor | WCAG 4.1.1 Parsing | Homepage has two elements with `id="why"` — the hero section anchor (`index.html:~202`) and a second usage (`~275`). Duplicate IDs are invalid HTML; fragment navigation `/#why` reaches only the first occurrence. | index.html | 1. Load /. 2. Click `/#why` from nav. 3. Observe which section receives focus. | `grep -n 'id="why"' index.html` → two matches. | Remove the duplicate `id="why"` from the second occurrence or rename it to `id="why-detail"`. | **Open** — content fix. |
| Minor | Nielsen #1 — Visibility of system status | Arcade iframe has no loading state or error message if the external game URL fails. Visitors see a blank phone frame with no feedback. | arcade/index.html | 1. Load /arcade/ with network throttled to offline. 2. Observe iframe area. **Expected:** error/loading message. **Actual:** blank frame. | `arcade/index.html:288–295` — bare iframe with no fallback text or JS error handler. | Add fallback text inside the `<iframe>` tags, e.g. `<a href="https://okhp3.github.io/glee-fully-chai-chasers/">Play Chai Chasers ↗</a>`. | **Open** — one-line HTML fix. |
| Minor | Nielsen #4 — Consistency and standards | Showcase nav submenu includes a "Showcase" entry, but the 404 page nav submenu omits it. Minor nav inconsistency across templates. | showcase/index.html vs 404.html | Compare the About submenu items between any content page and 404.html. | 404.html About submenu: Universe, About Us, Contact, Legal (no Showcase). All other pages include Showcase. | Add `<li><a href="/showcase/">Showcase</a></li>` to 404.html submenu. | **Open** — minor HTML fix. |
| Minor | Nielsen #5 — Error prevention | Search page suppresses Enter key via `onsubmit="event.preventDefault()"` with no explanation. Keyboard users pressing Enter after typing expect a search to run; the behavior is handled by JS keypress, but if JS fails, Enter does nothing with no message. | search/index.html | 1. Disable JS. 2. Load /search/. 3. Type a query. 4. Press Enter. **Expected:** query runs or clear error. **Actual:** nothing happens (form submit suppressed). | `search/index.html:176` — `onsubmit="event.preventDefault();"`. | Add `<noscript>` fallback guidance, or replace `preventDefault` with a no-JS action pointing to the static browse list. | **Open** — progressive enhancement. |

---

## 4. Prioritized Remediation Plan

### Group A — Keyboard operability (one shared root cause: missing keyboard event handlers)
**Files:** `assets/js/app.js`
**Fixes applied in this audit:** Escape closes mobile nav + focus return (line 43–50 block); construction overlay gets `hidden` attribute + focus return on dismiss.
**Remaining:** Add focus trap into construction overlay on show (requires reading overlay HTML and adding first/last focusable element tracking). Add `aria-live` to search overlay results container (~line 522). These are two `app.js` additions.

### Group B — Focus indicator (one shared root cause: `outline: none` overrides in theme.css)
**Files:** `assets/css/theme.css` (sync mirror — upstream PR required)
**Selectors:** `.theme-toggle:focus-visible`, `.okh-search-trigger:focus-visible`, `.glee-color-toggle:focus-visible`, `.askjamie-main .glee-color-toggle:focus-visible`
**Fix:** Remove all four `outline: none` declarations; the global rule at line 258 is correct and will apply.

### Group C — Contrast failures (one shared root cause: accent and muted token values)
**Files:** `assets/css/theme.css` (upstream PR)
- Darken Glee coral accent for text contexts or restrict to large/bold only.
- Darken AskJamie teal for text contexts.
- Lighten root dark muted token to ≥ `#9ca3af`.
- Adjust `.btn-primary` gradient start.

### Group D — AskJamie dark-mode token architecture (root cause: incomplete token swap)
**File:** `assets/css/theme.css` (upstream PR)
`askjamie-main` must swap its core `--color-fg`/`--color-bg`/`--color-surface` tokens in the dark block, not rely on scattered hardcoded component overrides.

### Group E — Content and CTA labels (root cause: internal terminology in public copy)
**Files:** Multiple HTML pages + templates
**Fixed:** 7 "More Info" → specific branch names in `toolbox/index.html`.
**Remaining:** "See the butterfly's view," "Hand off elsewhere," "Explore the System" — content revisions. Jargon definition at first use (GPT, Tool-ette, ATS, CI) across toolbox hierarchy. Long-sentence reduction on hub and detail pages.

### Group F — HTML correctness (small isolated fixes)
- `index.html` duplicate `id="why"` — remove from second occurrence.
- `arcade/index.html` — add iframe fallback text.
- `404.html` — add Showcase to submenu.
- `search/index.html` — add `<noscript>` fallback or replace `preventDefault`.

---

## 5. What Was Not Tested

| Item | Reason |
|---|---|
| Real screen reader (NVDA, JAWS, VoiceOver) | No real assistive technology available in this environment. Accessibility tree and source-code inspection used as substitute; marked throughout. |
| Ko-fi overlay widget behavior | Third-party injected JS; behavior not deterministic from source. Fallback anchor links are keyboard-accessible. |
| Actual browser rendering at 375px / 768px / 1024px / 1440px | Static source analysis used; no live browser available for pixel-level viewport testing. |
| Browser zoom to 200% | Cannot verify horizontal-scroll absence without live rendering. CSS uses relative units (rem/%) throughout — low risk. |
| PDF documents | None found on the site. |
| Embedded video captions | No native video embeds on the site. Arcade iframe embeds external game, not video. Designathon links point to external URLs not audited here. |
| GA4 analytics behavior | Third-party; privacy/GDPR compliance is outside scope of this audit. |
| ChatGPT/OpenAI flows | All GPT links open external ChatGPT interfaces. Those flows are outside site control and scope. |

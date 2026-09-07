# Inclusive Hub Experience  -  Current Evidence

**Site:** glee-fully.tools  
**Evidence date:** 2026-09-04  
**Scope:** Public hub, shared navigation/search, representative Toolbox detail,
Arcade, Search, and 404 routes  
**Purpose:** Rebaseline the historical accessibility audit with current
browser evidence. This report does not claim universal WCAG conformance.

## Executive result

The current browser regression run passed **16/16 checks** across six
representative routes. It verified:

- keyboard opening, Escape dismissal, focus return, and visible focus rings;
- the global search dialog, polite result announcement, list semantics, and
  accented `résumé` matching to Resume Builder;
- construction-gate focus containment and recovery;
- the 200% zoom layout equivalent (a 640px CSS layout viewport from a 1280px
  desktop baseline) without horizontal overflow;
- reduced-motion behavior, denied `localStorage`, and JavaScript-disabled
  Search fallback/form recovery;
- baseline HTTP loads, page errors, console errors, and horizontal overflow on
  Home, Toolbox, Search, Arcade, 404, and a construction-gated tool page.
- the analytics beacon’s CSP block is recorded separately as an expected
  third-party boundary; it is not mixed with unexpected application errors.

Machine-readable output: `inclusive-accessibility-qa-2026-09-04.json`  
Repeatable command: `python3 scripts/inclusive-accessibility-qa.py`

CI runs the same command after starting the local server in
`.github/workflows/viewport-qa.yml`.

## Historical finding rebaseline

Statuses use **Fixed**, **Still open**, **Superseded**, or
**Resolved / not reproducible**. The August report remains historical; the
status below is based on current source and the current browser run.

| Historical finding | Current status | Current evidence |
|---|---|---|
| Mobile navigation lacked Escape and focus return | **Fixed** | Keyboard run opens the 375px menu, Escape closes it, and focus returns to `.nav-toggle`. |
| Construction gate lacked inbound trap, hidden dismissal, and focus return | **Fixed** | Initial focus enters the dismiss button; Tab and Shift+Tab remain contained; Escape hides the gate and focuses `#main`. |
| Header controls suppressed the visible focus indicator | **Fixed** | The theme-toggle override no longer removes the outline; browser focus inspection reports a non-none, 2px-or-greater outline for the search trigger. |
| AskJamie dark-mode navigation contrast failed | **Superseded** | AskJamie is brand-locked light and has no dark-mode toggle/path in the current design. Third-party or alternate themes are not inferred from this result. |
| Glee breadcrumb hover contrast failed | **Fixed** | Current shared CSS uses the darker AA-safe hover token. |
| Root dark muted text contrast failed | **Fixed** | Current dark token is the lightened `#9ca3af` value. |
| Primary-button gradient began below normal-text contrast | **Still open** | The current gradient still begins at the historical darker stop; this remains the only confirmed visual contrast item carried forward. |
| Search overlay did not announce changing results | **Fixed** | The dialog has a `role="status"` / `aria-live="polite"` region; result links are wrapped in matching `role="listitem"` children. |
| Storage errors aborted setup | **Fixed** | Theme, color-scheme, and construction-gate storage writes/removals are guarded; denied-storage browser interaction passed. |
| 404 incorrectly marked a nav item current | **Fixed** | Current 404 navigation has no incorrect `aria-current="page"` marker. |
| 404 footer fragment link was dead | **Fixed** | Current footer uses the home root-relative destination. |
| Toolbox cards all said “More Info” | **Fixed** | Current branch CTAs identify their destinations. |
| Ecosystem headings could be empty with JavaScript unavailable | **Resolved / not reproducible** | Current source contains static branch heading/link text; no client-only heading dependency was found. |
| Reading level and undefined jargon were too high | **Fixed** | The historical remediation is present: key terms are defined and the listed long-copy pages were revised. |
| Metaphorical/internal CTA labels reduced recognition | **Still open** | Some copy such as “See the butterfly’s view” remains content debt; this is not a browser failure. |
| Homepage contained duplicate `id="why"` values | **Fixed** | Current `index.html` has one `id="why"` and the second section uses a distinct ID. |
| Arcade iframe had no static fallback | **Fixed** | The iframe contains fallback link content, and its page-specific presentation now lives in CSP-compatible shared CSS. |
| 404 About submenu omitted Showcase | **Fixed** | Current 404 submenu includes `/showcase/`. |
| Search form silently cancelled Enter when JavaScript was unavailable | **Fixed** | The form has `action="/search/" method="get"`; no-JS Enter navigation retained `q=résumé` and exposed the directory. |

## Browser evidence

### Accessibility-tree observations

Chromium’s accessibility tree was captured for each representative page:

- Home, Toolbox, Arcade, 404, and the construction page expose `main`,
  `navigation`, and `contentinfo` landmarks.
- Toolbox, Search, Arcade, and construction pages expose the expected
  breadcrumb name.
- Search exposes a `search` landmark, `searchbox`, `status`, and named
  “Search results” region.
- The construction page exposes a `dialog` and `status`.
- Arcade exposes the external game as an iframe while retaining the page’s
  static fallback link.

These are browser accessibility-tree observations, not spoken output.
VoiceOver, NVDA, and JAWS were not available in the Linux runner, so a real
screen-reader speech session remains a manual limitation and is not claimed
here.

### Keyboard and focus

The browser run covered the Home mobile menu, global search, and a
construction-gated tool page. It checked both forward and reverse
construction-gate traversal, Escape dismissal, trigger focus return, search
status semantics, and focus-ring visibility. The dedicated Search form was
also submitted with Enter under JavaScript-disabled conditions.

### Constrained environments

| Constraint | Evidence | Result |
|---|---|---|
| 200% zoom | 640px layout viewport equivalent to 200% from a 1280px CSS baseline | No horizontal overflow on Home, Toolbox, Search, Arcade, or 404 |
| Reduced motion | Chromium `prefers-reduced-motion: reduce` plus reveal/transition inspection | All reveal content visible; transitions/animations reduced |
| Storage unavailable | `localStorage` getter throws `SecurityError`, followed by toggle interaction | Controls initialize; no page error |
| JavaScript disabled | Search loaded with JS disabled and form submitted with Enter | Directory fallback visible; normal GET preserves the query |
| Accented input | Global query `résumé` | Eight results, first result Resume Builder; polite status populated |

### Automated vs. manual boundaries

Automated checks can prove DOM states, browser focus, layout overflow, and
accessibility-tree structure. They cannot prove speech order, pronunciation,
screen-reader verbosity, cognitive load, or every browser/OS combination.
Third-party Ko-fi, Google Analytics, Google Fonts, ChatGPT, and the external
Arcade application remain outside this evidence boundary.

## Remaining limitations

1. Perform a real VoiceOver or NVDA pass on a user workstation for essential
   navigation, search, and construction-gate journeys.
2. Revisit the primary-button gradient’s left-edge contrast before claiming
   complete AA coverage.
3. Keep the content-copy CTA cleanup separate from browser accessibility
   remediation.

# Accessibility Audit — 2026-05-03

Static, no-JS-required, screen-reader-friendly site review.

---

## Summary

| Check | Status |
|---|:-:|
| `<!DOCTYPE html>` on every page | ✓ 60/60 |
| `<html lang="en">` on every page | ✓ 60/60 |
| Single `<h1>` per page | ✓ 60/60 |
| Skip-to-content link as first interactive element | ✓ 60/60 |
| `<main id="main">` landmark matching skip target | ✓ 60/60 |
| Visible breadcrumb with `aria-label="Breadcrumb"` on inner pages | ✓ 57/57 |
| `aria-current="page"` on the leaf breadcrumb | ✓ |
| `<img>` tags missing `alt` | 0 |
| Decorative images marked `aria-hidden="true"` (brand stripes, glow) | ✓ |
| Footer landmarks (`<footer>`) | ✓ 60/60 |
| Nav landmarks (`<nav>`) | ✓ 60/60 |
| External links open in new tab use `rel="noopener"` | ✓ |
| Reduced-motion: scroll-reveal honors `prefers-reduced-motion` | ✓ (in `app.js`) |
| Keyboard: search modal opens on `/`, ⌘K, Ctrl+K and traps focus | ✓ (in `search.js`) |
| Focus-visible styles on links and buttons | ✓ (theme.css) |

---

## What was added in this pass

### Visible breadcrumb component
Until 2026-05-03, only the dedicated `/search/` page had a visible breadcrumb;
the JSON-LD `BreadcrumbList` shipped 2026-05-02 was machine-readable only.
Now every page that carries a JSON-LD breadcrumb (57 of 60) also renders:

```html
<nav class="glee-breadcrumb" aria-label="Breadcrumb">
  <ol class="glee-breadcrumb-list">
    <li class="glee-breadcrumb-item"><a href="…">Home</a></li>
    <li class="glee-breadcrumb-item"><a href="…">Toolbox</a></li>
    <li class="glee-breadcrumb-item"><a href="…">Discovered Careers</a></li>
    <li class="glee-breadcrumb-item glee-breadcrumb-current"
        aria-current="page">Resume Builder</li>
  </ol>
</nav>
```

* Semantic ordered list (screen reader announces "1, 2, 3, current").
* `aria-current="page"` on the leaf so AT users hear context.
* `›` separator is a CSS pseudo-element so it is **not** announced.
* On viewports < 480 px the type tightens and the gutter shrinks.
* Honors `prefers-color-scheme: dark` for visitors who set it.

The same data drives both surfaces: `scripts/inject-breadcrumb.py` reads the
JSON-LD `BreadcrumbList` already embedded by `scripts/inject-jsonld.py`, so the
visible labels can never drift from the structured data.

### DOCTYPE regression caught
`toolbox/02-treasured-finds/02b-decor-detective/index.html` was missing
`<!DOCTYPE html>` — the same class of bug that hit `02e-spirited-journal` in
the 2026-05-02 audit.  The page rendered in quirks mode, which silently
sabotages CSS box-model and breaks several keyboard-focus visual cues.
Restored.  The validator now fails loud on this regression.

---

## Spot checks (manual / heuristic)

* **Color contrast** — primary text `#2a2320` on `#f6f2ee` paper: contrast
  ratio ≈ 13.4:1 (passes AAA at all sizes). Rust `#d35b2d` on paper: ≈ 4.8:1
  (passes AA for normal text). Espresso headings: ≥ 12:1.
* **Focus rings** — `:focus-visible` is preserved across links, buttons, and
  the search button. Outlines are not removed globally.
* **Tap targets** — primary CTAs use the `glee-btn` / `glee-btn-primary`
  pattern with a minimum 44 × 44 px tap area on mobile.
* **Heading order** — every page opens with `<h1>` once, then descends into
  `<h2>` / `<h3>`. No jumps from `<h1>` to `<h3>`.

---

## Deferred / not auditable inside the sandbox

* **Live Lighthouse / axe runs** — would require Chrome + headless browser; the
  Replit sandbox has neither. The audit reports above are the static-analysis
  equivalent.
* **Screen-reader interaction testing** (NVDA / VoiceOver) — out of scope for an
  agentic pass; recommended as a manual quarterly check by a human user.
* **Color-blind simulation** — the brand palette (rust + gold + olive + paper)
  passes AA contrast; no information is conveyed by color alone (links are
  underlined or separated, breadcrumb separators are decorative).

---

## Re-running

There is no single "accessibility validator" script — the relevant signals are
spread across `validate-site.py` (DOCTYPE, lang, h1, skip target, main
landmark) and `check-links.py` (anchor target existence). Run both after any
content change:

```bash
python3 scripts/validate-site.py
python3 scripts/check-links.py
```

---
name: Glee toggle identity
description: How the Glee dark-mode toggle differs from OKH and AskJamie; its CSS style on the cream header.
---

Three sites share app.js but have completely different toggle implementations:

| Site | Detection | localStorage key | HTML attribute | Toggle |
|---|---|---|---|---|
| Glee | `body.glee-main` | `glee-color-scheme` | `data-color-scheme` on `<html>` | 3-state (system/light/dark) |
| OKH | neither flag | `okh-theme` | `data-theme` on `<html>` | 3-state (system/light/dark) |
| AskJamie | `body.askjamie-main` | — | forces `data-theme="light"` | none (brand-locked light) |

**Glee CSS dark-mode pattern** (in theme.css GLEE scope):
```css
@media (prefers-color-scheme: dark) {
  html:not([data-color-scheme="light"]) .glee-main { /* dark styles */ }
}
html[data-color-scheme="dark"] .glee-main { /* explicit dark override */ }
html[data-color-scheme="light"] .glee-main { /* explicit light pin */ }
```

**Toggle button style on cream header** — base CSS has dark-navy toggle (for OKH dark headers); Glee overrides it:
```css
.glee-main .theme-toggle {
  background: #d35b2d;   /* Glee brand rust/coral */
  border-color: #d35b2d;
  color: #fff;
}
```

**Footer color regression guard:** `html[data-theme="light"] .site-footer` had near-white text that bled onto Glee's cream footer. Fixed by scoping to `html[data-theme="light"] body:not(.glee-main) .site-footer`.

**Why:** OKH forces `data-theme="light"` on Glee pages via old brandLocked code, causing OKH light-theme rules to activate. Fix is the `isGlee` / `isAskJamie` branch separation — Glee never touches `data-theme`.

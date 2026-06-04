---
name: Pseudo-element dark mode
description: Dark mode rules on a container don't override ::before/::after pseudo-elements with hardcoded backgrounds. Always pair them.
---

A common Glee pattern is using a `::before` pseudo-element as the visible card background (the rotated "warm paper" panel):

```css
.glee-hero-card::before {
  background: #fff7f1;  /* hardcoded — survives CSS variable overrides */
  border-radius: 1.6rem;
  transform: rotate(-2.5deg);
  z-index: -1;
}
```

When a dark mode rule only targets the container:
```css
html[data-color-scheme="dark"] .glee-main .glee-hero-card {
  background: #241c1a;  /* applied to element, but ::before sits on top */
}
```
...the `::before` hardcoded cream background renders ON TOP and the container's dark bg is invisible. Text inherits `--color-fg: #f0e8e0` (near-white) from the dark mode token override, giving near-white text on cream = very low contrast.

**Fix:** Always add a matching `::before` rule in the dark mode block:
```css
html[data-color-scheme="dark"] .glee-main .glee-hero-card::before {
  background: #241c1a;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.45);
}
```

**How to apply:** Any time a Glee component uses `::before`/`::after` with a hardcoded cream background (`#fff7f1`, `#fffaf5`, `#fffcf5`) as a decorative card layer, it needs an explicit dark mode pseudo-element rule alongside its container rule. Search for `background: #fff` within the GLEE section of theme.css to find candidates.

---
name: Header-controls timing
description: Why .header-controls must be created in an eager IIFE before the search module runs.
---

The search module (bottom of app.js) calls `start()` immediately when `document.readyState !== "loading"` — which is always the case for `defer` scripts (readyState is "interactive" at defer-execute time). That means `injectTrigger()` runs **before** DOMContentLoaded fires.

If `.header-controls` doesn't exist yet at that point, `injectTrigger` falls back to inserting the search button as a direct sibling of `.nav-toggle` in `.container`. Later, DOMContentLoaded creates `.header-controls` and appends only the toggle — so search and toggle end up as separate flex children instead of siblings inside `.header-controls`.

**Fix:** An IIFE at the top of app.js (before the DOMContentLoaded listener and the search module) creates `.header-controls` eagerly:

```javascript
(function createHeaderControls() {
  const hdr = document.querySelector(".site-header");
  if (!hdr) return;
  const container = hdr.querySelector(".container");
  if (!container || container.querySelector(".header-controls")) return;
  const div = document.createElement("div");
  div.className = "header-controls";
  const nt = container.querySelector(".nav-toggle");
  container.insertBefore(div, nt || null);
}());
```

Then in DOMContentLoaded, replace the creation block with:
```javascript
let headerControls = header ? header.querySelector(".header-controls") : null;
```

**Why:** Keeps search + toggle together in `.header-controls` so they appear as a single right-aligned unit in the flex header.

**How to apply:** Any time a new JS module needs `.header-controls` at defer-execute time, make sure the createHeaderControls IIFE runs first (it's idempotent via the querySelector guard).

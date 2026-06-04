---
name: Screenshot cache behavior
description: The Replit screenshot browser caches aggressively; homepage is often stale.
---

The Replit screenshot tool uses a headless browser with a persistent cache. The homepage (`/`) is almost always served stale (old HTML → old JS/CSS). Effects:

- Console.log output from new JS won't appear in browser logs.
- Visual changes from new CSS won't appear in the screenshot.
- Adding `?v=N` query stamps to asset URLs in the HTML doesn't help if the HTML itself is cached.

**Workaround:** Screenshot a path the browser hasn't cached yet — any inner page like `/about/`, `/contact/`, `/legal/`. These load fresh HTML → fresh assets → new JS/CSS runs correctly.

**Server-side:** Switch from `python3 -m http.server` to a custom `serve.py` that adds `Cache-Control: no-store, no-cache` headers. This ensures future sessions always get fresh assets. The workflow command is `python3 serve.py`.

**Why:** The default Python http.server sends no Cache-Control header; browsers apply heuristic caching (often 10% of Last-Modified age), which can be hours for rarely-changed files.

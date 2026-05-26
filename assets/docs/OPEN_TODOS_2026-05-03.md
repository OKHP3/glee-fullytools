# Open TODOs — Editorial / Owner Action Required

Last updated: 2026-05-26

This file surfaces every `<!-- TODO -->` comment still embedded in the production
HTML so the human owner can resolve them in one pass. Each item is a placeholder
that the validator and link checker happily accept (the surrounding `<a href>`
points to a public landing page) but that the owner intends to swap once the
underlying GPT URL is finalized.

---

## 1. Three unfinished GPT links — ✅ RESOLVED 2026-05-26

All three placeholder links replaced with verified live ChatGPT URLs.
Source URLs confirmed from parent branch pages where they were already wired.

| # | File | Resolution |
|---|------|------------|
| 1 | `toolbox/02-treasured-finds/02c-present-hoarder/index.html` | ✅ Real URL: `g-685af65a822881919690d7410a122984-present-hoarder-by-glee-fully` |
| 2 | `toolbox/04-travelers-guide/04d-dreamland-journeys/index.html` | ✅ Real URL: `g-685b072fccec8191a595b10991348f30-dreamland-journeys-by-glee-fully` |
| 3 | `toolbox/04-travelers-guide/04e-memento-log/index.html` | ✅ Real URL: `g-685b072be58c8191ba386b00b33b93b8-memento-log-by-glee-fully` |

Fixed by `scripts/fix-placeholder-gpt-links.py` (idempotent, 2026-05-26).

---

## 2. Editorial / brand decisions tracked in `FINAL_AUDIT_2026-05-03.md` §6

These are **not** in the HTML as TODO comments — they live in the audit doc as
deferred items. Re-listed here for one-stop visibility:

- **B1** — Stronger branch-page visual indices (icon cards).
- **B2** — "Suggested next" / "Keep exploring" tray on tool-ettes.
- **B3** — Reconcile README copy onto `/about/` or homepage.
- **B5** — Construction overlays on complete branch pages. ✅ RESOLVED 2026-05-26 — branches 01–04, 07 converted to slim `.construction-badge--slim` strip via `scripts/reclassify-construction-banners.py`; branch 06 keeps full overlay (incomplete tool-ette links remain).
- **C2** — Visible "Last updated" `<time datetime>` blocks (placement is a brand call).
- **C3** — Per-tool FAQ JSON-LD (one Q/A per tool — editorial work).
- **WebP / PurgeCSS** — Requires a build step; currently violates "no-build" philosophy.
- **22 MB orphaned butterfly art** — Owner approval required before any `git rm`.

---

## 3. What is NOT a TODO

For the avoidance of doubt, these were considered and intentionally left as-is:

- **CSS brace count off-by-one** in `assets/css/theme.css` — cosmetic only;
  every browser parses it fine, every validator passes. Hunting it down is more
  effort than its impact warrants.
- **113 GPT-icon variant orphans** in `assets/img/` — kept as design slack so
  per-tool icon swaps remain a one-line change in the icon-map JSON.
- **`robots.txt` listing `feed.xml`** — non-standard; the feed is already
  discoverable via `<link rel="alternate" type="application/atom+xml">` in
  every page's `<head>`.

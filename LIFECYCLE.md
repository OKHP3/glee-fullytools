# Lifecycle — Glee-fully Tools

**Current state:** Active  
**Last reviewed:** 2026-08-23

---

## State definition

| State | Meaning |
|---|---|
| **Draft** | Work in progress; not published or publicly linked |
| **Active** | Deployed and maintained; receives regular updates |
| **Maintenance** | Deployed; receives security and critical fixes only |
| **Archived** | No longer maintained; preserved for reference |
| **Migrating** | Content or structure moving to a new home |

---

## Current state: Active

The Glee-fully Tools site is publicly deployed at `https://glee-fully.tools` and
actively maintained. The current phase is **growth and refinement** — new tool-ettes
are added as the GPT suite expands, and the toolbox structure is stable.

### Evidence

- 63 production HTML pages across seven branch directories (60 indexable pages, 42 tool-ettes)
- GitHub Actions CI validates HTML, links, and sitemap on every push
- `scripts/validate-site.py` and `scripts/check-links.py` pass with 0 issues
- `assets/data/search-index.json` indexes all 60 indexable pages

---

## Transition rules

### Active → Maintenance
Trigger when no new tools or content pages are expected for 90+ days.
Actions: Set state here, update `README.md` status badge, reduce CI to weekly.

### Active → Migrating
Trigger when the site URL, repo location, or static host is changing.
Actions: Create `MIGRATION.md`, add canonical redirects, notify AGENTS.md sync circuit.

### Any state → Archived
Requires explicit owner decision.
Actions: Set state here, add `noindex` meta to all pages, update `robots.txt`,
remove from the OKHP3 universe page, preserve the repo read-only.

---

## Owner decisions pending

- **B1** — Decide whether branch hubs should gain stronger icon-and-tagline visual indices.
- **B3** — Decide whether the README's portfolio positioning copy should be reconciled onto `/about/` or the homepage.
- **C2** — Decide where visible per-page “Last updated” timestamps belong.
- **C3** — Decide whether to author one FAQ JSON-LD entry for each tool-ette.
- **WebP / PurgeCSS** — Decide whether the performance benefit justifies a build-step exception to the no-build philosophy.
- **Orphaned butterfly art** — Decide whether to retain or remove the approximately 22 MB of unused source artwork.

These are documented owner decisions, not release blockers. B2 (Keep exploring
trays) and B5 (complete-branch construction overlays) are resolved and remain
in the historical TODO register for traceability.

---

## History

| Date | State | Notes |
|---|---|---|
| 2025 (launch) | Active | Site launched with initial toolbox structure |
| 2026-07-20 | Active | Footer nav, search index, and CSP enforcement updated (site-wide audit) |
| 2026-08-03 | Active | LIFECYCLE.md created; 14 skills compliance pass completed |
| 2026-08-23 | Active | Operational documentation reconciled; remaining owner decisions made explicit |

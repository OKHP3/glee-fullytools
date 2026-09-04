# Changelog — Glee-fully Tools

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

- Added `docs/suite-promise.md` as the authoritative contract for the current
  vision, public-vs-external boundary, inventory vocabulary, Tool-ette
  publication states, owner decisions, and phase completion criteria.
- Reconciled public and maintainer language around active growth and refinement:
  63 production HTML files, 60 indexable pages, 7 branches, 42 Tool-ettes, and
  49 branch/Tool-ette feed entries are now distinct terms.

---

## [1.0.0] — 2026-05-29

### Added
- Initial public release of Glee-fully Tools.
- Full static site: homepage, about, contact, legal, search, universe pages.
- Toolbox, showcase, ecosystem, and persona content sections.
- Shared design system via `theme.css` (scope `.glee-main`) synced from
  OverKill Hill P³ canonical stylesheet.
- Client-side search with static JSON index (`assets/data/search-index.json`).
- `scripts/audit-site.py` quality gate.
- `scripts/build-search-index.py` for index regeneration.
- Repository governance files: `AGENTS.md`, `CONTRIBUTING.md`,
  `CODE_OF_CONDUCT.md`, `SECURITY.md`, `CHANGELOG.md`, `ROADMAP.md`.
- `llms.txt` for LLM crawler guidance.
- `humans.txt` for team attribution.
- `robots.txt`, `sitemap.xml`, `site.webmanifest`.
- Full favicon set and Open Graph image set.
- Mermaid.js v11 ESM diagrams with affiliate referral convention.
- GA4 analytics with custom events.

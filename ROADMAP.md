# Roadmap

This roadmap outlines the near-term public direction for the **Glee-fully Tools** repository.

## Current
- Quality gates: `scripts/audit-site.py` — run on every meaningful HTML change
- Responsive QA: `node scripts/responsive-qa.mjs --static` — run after major edit rounds
- Portfolio stats sync: `python3 scripts/sync-portfolio-stats.py` — run after content updates

## Next
- **OG images** — commission 1200×630 landscape social-card images to replace
  current square assets.
- **Submit sitemap** to Google Search Console and Bing Webmaster Tools.
- **CSP hardening** — refactor inline script handlers into external JS files
  so `script-src 'unsafe-inline'` can be dropped from the CSP meta tag.
- **Self-hosted fonts** — move Google Fonts to `assets/fonts/` to eliminate
  the third-party privacy boundary and reduce DNS lookups.
- **Organization JSON-LD `sameAs`** — add social profile URLs.

## Later
- Expand toolette showcase with additional case entries
- Add progressive web app install flow (PWA manifest + service worker)
- GA disclosure in `legal/index.html` (GDPR/CCPA best practice)
- Cross-link more explicitly between Glee-fully Tools, OverKill Hill, and AskJamie™

## Shipped
- **v1.0 (2026-05-29)** — Scripts superset sync: all general-purpose tooling
  distributed across all three OKHP3 repos. AGENTS.md unified v2.0.
  Governance files (CHANGELOG, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY,
  llms.txt) created.

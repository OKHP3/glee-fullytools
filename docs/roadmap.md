# Roadmap

This roadmap outlines the near-term public direction for the **Glee-fully Tools**
repository. The authoritative current promise, inventory, publication states,
and completion criteria are in [`docs/suite-promise.md`](suite-promise.md).

## Current phase — Active growth and refinement

- Maintain the public catalog and routing hub while new Tool-ettes move through
  live, beta, construction, unavailable, or retired states.
- Keep the 63-file / 60-indexable-page / 7-branch / 42-Tool-ette / 49-feed-entry
  vocabulary synchronized with the contract.
- Treat passing static validation as proof of site structure, not proof of
  external GPT availability or behavior.

## Maintainer operations
- Quality gates: `scripts/audit-site.py` — run on every meaningful HTML change
- Responsive QA: `node scripts/responsive-qa.mjs --static` — run after major edit rounds
- Portfolio stats sync: `python3 scripts/sync-portfolio-stats.py` — run after content updates

## Next
- **Submit sitemap** to Google Search Console and Bing Webmaster Tools.
- **CSP hardening** — refactor inline script handlers into external JS files
  so `script-src 'unsafe-inline'` can eventually be removed from the configured
  CSP policy. Per-page CSP meta policies are enforced by browsers; the portable
  policy in `_headers` still requires a compatible host for HTTP response
  delivery.
- **Organization JSON-LD `sameAs`** — add social profile URLs.

## Later
- Expand toolette showcase with additional case entries
- Review the optional analytics property retention setting (the owner policy is
  14 months or less) and keep the public data-flow inventory current.
- Cross-link more explicitly between Glee-fully Tools, OverKill Hill, and AskJamie™

## Shipped
- **v1.0 (2026-05-29)** — Scripts superset sync: all general-purpose tooling
  distributed across all three OKHP3 repos. AGENTS.md unified v2.0.
  Governance files (CHANGELOG, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY,
  llms.txt) created.
- **Offline shell** — Versioned same-origin service-worker cache with an
  explicit offline fallback page; third-party resources remain outside the
  cache boundary.
- **Landscape social card (2026-08-22)** — Approved 1200×630 branded card is
  referenced by Open Graph and Twitter metadata across all published page
  families; source templates remain parameterized.

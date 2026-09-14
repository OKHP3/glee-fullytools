# Roadmap

This roadmap outlines the near-term public direction for the **Glee-fully Tools**
repository. The authoritative current promise, inventory, publication states,
and completion criteria are in [`docs/suite-promise.md`](suite-promise.md).

## Current phase - Active growth and refinement

- Maintain the public catalog and routing hub while new Tool-ettes move through
  live, beta, construction, unavailable, or retired states.
- Keep the 63-file / 60-indexable-page / 7-branch / 42-Tool-ette / 49-feed-entry
  vocabulary synchronized with the contract.
- Use [`config/public-inventory.json`](../config/public-inventory.json) as the
  shared scope contract for generated discovery outputs and release checks.
- Treat passing static validation as proof of site structure, not proof of
  external GPT availability or behavior.

## Maintainer operations
- Follow the active release sequence in `replit.md`: regenerate search, stats,
  search again if stats changed content, then CSS/offline versions. Review diffs.
- Run structural and link gates after meaningful changes; inspect the advisory
  audit separately. `bash scripts/post-merge.sh` checks committed outputs only.
- Run real browser QA after rendered changes. `node scripts/responsive-qa.mjs
  --static` is structural lint and does not establish browser behavior.
- Discovery artifacts: `python3 scripts/generate-sitemap.py` and
  `python3 scripts/generate-feed.py`

## Completed in this release-evidence pass
- **Discovery output scope** — search, sitemap, feed, portfolio statistics, and
  link checks now consume the shared public-inventory contract.
- **Current run evidence** — validator reports include the run date and UTC
  generation time; dated reports are historical records rather than current
  evidence by filename alone.
- **Pages artifact boundary** — the release workflow excludes maintainer and
  development content and fails on unexpected artifact paths.
- **Dependency reproducibility** — Python and npm QA dependencies are pinned,
  with GitHub Actions and monthly Dependabot update governance.

## Next
- **Reviewed release readiness (2026-09-05)**: finish the exact-commit browser,
  CI, artifact-transfer, and live gates in
  [`platform-release.md`](remaining-program-2026-09-05/platform-release.md).
  Dependency/action pins, host-header delivery, and explicit-source sibling
  promotion are concrete owner choices in that packet; none is applied by a
  successful local check.
- **Owner-controlled discovery setup** — verify the domain and submit
  `https://glee-fully.tools/sitemap.xml` in Google Search Console and Bing
  Webmaster Tools, then record non-secret result evidence in
  [`docs/discovery-evidence.md`](discovery-evidence.md).
- **HTTP security policy delivery**: review the residual GitHub Pages header
  limitations. Hash-based page CSP is already implemented in `scripts/csp.py`
  and checked by `scripts/check-csp.py`; executable inline scripts and event
  attributes are externalized, and script `unsafe-inline` is absent.
  JSON-LD/speculation-rules remain the documented declarative inline boundary.
  See the [September 9 CSP hardening evidence](../assets/audit/release-2026-09-09/csp-hardening.md);
  `_headers` still requires a compatible host for HTTP response delivery.
- **Organization identity approval** — confirm the seven already-published
  `sameAs` identities in the same evidence record; do not add new profiles
  without owner approval.

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
- **Resilient web behavior (2026-09-04)**  -  `scripts/resilience-qa.py` records
  static crawler/installability checks, Chromium/Firefox/WebKit journeys,
  offline/reconnect lifecycle evidence, and blocked-third-party fallback
  behavior. See [`docs/resilience.md`](resilience.md).
- **Landscape social card (2026-08-22)** — Approved 1200×630 branded card is
  referenced by Open Graph and Twitter metadata across all published page
  families; source templates remain parameterized.

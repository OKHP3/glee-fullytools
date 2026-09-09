# Glee-fullyTools maintenance scripts

This directory contains the scripts that are safe to use for the current
glee-fullytools repository. The active scripts are the only scripts kept at
this level. Historical and manual tools are preserved in `scripts/archive/`
so they cannot be mistaken for current pipeline commands. Classification
follows the same convention as `askjamie/scripts/README.md`.

## Classification

| Script | Classification | Use |
| --- | --- | --- |
| `audit-site.py` | active | Site audit |
| `audit-tool-ette-promises.py` | active | Check all 42 Tool-ette pages for a description, unique identity, publication signal, and primary CTA state |
| `build-search-index.py` | active | Rebuild the generated search index, then refresh the universe map |
| `sync-universe-map.py` | active | Generate the owned universe page block and public coverage/provenance JSON using the installed skill; `--check` is read-only |
| `check-accent-contrast.py` | active | Accent contrast check (has its own test coverage) |
| `check-catalog-claims.py` | active | Check all 42 Tool-ette pages for unsupported capability, availability, and platform-boundary claims; covered by `tests/test_content_claims.py` in CI |
| `check-csp.py` | active | CI guard against CSP drift |
| `check-glee-dark-coverage.py` | active | Dark-mode coverage check (invoked by `validate-site.py`) |
| `check-links.py` | active | Internal target and sitemap check; external links are counted, not fetched |
| `check-mtb-version.py` | active | MTB version consistency |
| `check-public-headers.py` | active | Public `_headers`/CSP header check |
| `check-workflow-actions.py` | active | Approved action-major-tag policy check; does not enforce immutable SHA pins |
| `csp.py` | active | Canonical CSP policy generation module |
| `generate-csp.py` | active | Apply CSP policies to every page |
| `inclusive-accessibility-qa.py` | active | Browser evidence for inclusive keyboard, search, fallback, and constrained-environment journeys |
| `post-merge.sh` | active | Post-merge integrity hook; checks generated outputs and idempotently repairs cache-version references and the offline shell; run with Bash, never Python |
| `public-artifact.py` | active | Stage and verify the reviewed public inventory, transferred bytes, and final Pages archive |
| `responsive-qa.mjs` | active | Responsive QA entry point |
| `run-viewport-qa.py` | active | Full browser viewport QA runner (`.github/workflows/pages.yml`, `viewport-qa.yml`) |
| `resilience-qa.py` | active | Installability, offline lifecycle, cross-browser, crawler, and third-party failure acceptance checks |
| `serve-site.py` | active | Local preview server |
| `sparkle-qa.py` | active | Sparkle-loader QA (`.github/workflows/sparkle-qa.yml`) |
| `sync-foundation-files.py` | active, review required | Dry-run foundation inventory; legacy write modes choose by Git touch time and require explicit per-file source/target review before use |
| `sync-css-version.py` | active | CSS and JavaScript cache-version sync, including the dynamic adapter import and offline shell; run after content generators (has its own test coverage) |
| `sync-image-alt.py` | active | Image alt-text sync (invoked by `validate-site.py`) |
| `sync-portfolio-stats.py` | active | Portfolio stats sync; the post-merge hook checks committed stats with `--check` |
| `sync-social-card.py` | active | Social-card sync (has its own test coverage) |
| `sync-sparkle-fallback.py` | active | Sparkle fallback sync (invoked by `validate-site.py`) |
| `validate-site.py` | active | Structural site validation |

Cross-site write authorization is separate from a dry-run suggestion. Follow
`docs/companion-publishing-contract.md`: record exact source and target commits,
review semantic compatibility, and preserve site adapters. Newest Git touch time
does not establish ownership or compatibility. This checkout has no replacement
manifest-driven promotion executor; do not describe the proposed model as implemented.

`tests/test-release-readiness.cjs` supplies focused Node Playwright cross-engine
journeys when that runtime and browsers already exist. Missing engines return
non-success and remain `NOT RUN`; a successful Node journey is not a successful
run of `tests/test_browser_acceptance.py` or `resilience-qa.py`.

The FoundRy accessibility evidence has an explicit Node runtime boundary:
`npm ci && npx playwright install chromium && npm run
qa:foundry-accessibility`. It checks both narrow viewports and keeps human
screen-reader testing outside the automated result.

The following scripts are **reference-only**. They may still be useful for a
deliberately scoped maintenance or migration task, but they are not part of
the current validation or release pipeline: `add-noreferrer.py`,
`apply-modern-baseline.py`, `audit-assets.py`, `audit-meta-versions.py`,
`cache-bust.py`, `cross-site-sync.py`, `enhance-pages.py`,
`extract-templates.py`, `fix-audit-2026-05-12.py`,
`fix-footer-nav-2026-07-20.py`, `fix-image-performance.py`,
`fix-placeholder-gpt-links.py`, `generate-illustrations.py`,
`generate-templates.py`, `inject-color-scheme-init.py`,
`inject-gpt-icon-picture.py`, `inject-keep-exploring.py`,
`inject-sparkle-loader.py`, `inject-toolette-hub.py`, `modernize-pages.py`,
`move-orphans-to-library.py`, `normalize-head.py`, `picture-upgrade.py`,
`png-to-webp.py`, `reclassify-construction-banners.py`,
`remove-deprecated-meta.py`, `rename-img-kebab.py`, `reorg-theme-css.py`,
`responsive-audit.py`, `update-card-srcsets.py`,
`update-placeholder-dimensions.py`, and `viewport-qa.py`.

`viewport-qa.py` is reference-only, not active, despite the similar name to
the active `run-viewport-qa.py`: nothing in CI or in any other script
invokes it directly (confirmed by exact-match search, not just a filename
substring check: `viewport-qa.py` is a literal substring of
`run-viewport-qa.py`, which produced a false positive on the first pass of
this audit). `run-viewport-qa.py` is the one both `pages.yml` and
`viewport-qa.yml` actually call.

`site-audit.py` is retired rather than reference-only: it is a different,
superseded tool from the active `audit-site.py` (confirmed zero references
anywhere in this repo, exact-match search), byte-identical to
overkill-hill's own retired copy of the same file.

The following scripts are **retired**. They are preserved for history only
and must not be run against glee-fullytools: `activate-icons.py`,
`add-toolbox-to-footer.py`, `convert-gpt-icons-webp.py`,
`convert-hero-webp.py`, `inject-breadcrumb.py`,
`inject-hero-picture.py`, `inject-jsonld.py`, `inject-nav-logo-webp.py`,
`inject-showcase-footer.py`, `inject-showcase-subnav.py`,
`push-to-github.py`, `release-mtb.py`, `site-audit.py`, and
`wire-illustrations.py`.

All reference-only and retired scripts live in `scripts/archive/`. Read
their headers and review their target paths before adapting any of them.

## Provenance

This classification and the `scripts/archive/` convention were ported from
`askjamie/scripts/README.md` as part of the 2026-08-30 scripts/ unification
pass (see `overkill-hill/docs/sxs-infrastructure-audit-2026-08-29.md`).
AskJamie triaged this same body of shared migration tooling first; this file
reclassifies glee-fullytools' copies against that precedent plus a live
repo-wide reference check (CI workflows, `post-merge.sh`, `AGENTS.md`, and
cross-script calls, verified for exact filename matches rather than
substrings).

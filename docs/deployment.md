# Glee-fully Tools deployment contract

This repository is the source of truth for the public site at
[glee-fully.tools](https://glee-fully.tools).

## Publishing source

- **Source branch:** `main`
- **Current Pages mode:** GitHub Actions deployment
- **Repository-owned workflow:** `.github/workflows/pages.yml`
- **Release flow:** the workflow validates the exact `main` commit, builds a static Pages artifact, and deploys that artifact to GitHub Pages.

GitHub Pages is the sole public publishing target. Replit’s local preview workflow is for development only and does not publish the site.

The required review, status-check, direct-push, ownership, and dependency-update
policy is maintained in [`docs/release-governance.md`](release-governance.md).
That document records which GitHub settings are observed versus still requiring
owner-side configuration.

## Artifact and paths

The published artifact is the repository root. It contains the root `index.html`, `offline.html`, `sw.js`, `assets/`, each public route directory, generated data files, and the committed `CNAME`. There is no bundler, framework build, or alternate output directory.

The site is served at the domain root. Existing root-relative links, asset references, and direct route directories (`/about/`, `/legal/`, and toolbox routes) are preserved exactly as authored. No base-path prefix or HTML rewrite is applied.

## Custom domain

`CNAME` is committed at the artifact root and must contain exactly:

`glee-fully.tools`

GitHub Pages custom-domain and HTTPS settings remain attached to `glee-fully.tools`. The CNAME must not be replaced with a preview or repository URL.

## Release guardrails

Run the repository-owned checks from a clean checkout before merging a release
change:

```bash
python3 scripts/check-workflow-actions.py
python3 scripts/build-search-index.py --check
python3 scripts/sync-portfolio-stats.py --check
python3 scripts/sync-css-version.py --check
python3 scripts/sync-social-card.py --check
python3 scripts/validate-site.py
python3 scripts/check-links.py
python3 scripts/audit-site.py --quiet
python3 scripts/check-accent-contrast.py --strict
python3 scripts/check-glee-dark-coverage.py --section all --require-both
```

The Pages workflow repeats the required checks and performs browser QA before
building the artifact. The previous reference to an external
`publishing-trigger-check` command is not an executable prerequisite in this
checkout and has been removed from the release contract. The repository
validation workflows continue to protect HTML, links, responsive layout, and
sparkle behavior.

## Release identity and header delivery

Before any Pages validation gate runs, the workflow compares `git rev-parse
HEAD` with `${{ github.sha }}` and fails on any mismatch. The deployed artifact
also contains `release-provenance.json`, whose commit field is the same event
SHA; the artifact name and validation-report artifact use that SHA as well.

`_headers` is a portable policy file and is not consumed by GitHub Pages. The
live Pages response currently supplies HSTS, but does not supply the repository
policy's CSP, framing, or MIME-protection headers. The post-deploy workflow
step runs `scripts/check-public-headers.py` against `https://glee-fully.tools/`.
It is non-blocking because these missing headers are a known host limitation;
an owner reviewing a release must treat any missing-header output as a finding,
not as a passing security control. A future hosting change must re-run the
smoke test before claiming those headers are deployed.

Each published HTML page also carries a generated page-level CSP `<meta>` tag.
That tag is enforced by the browser for the page itself and is separate from
HTTP response headers. It allows Google Fonts and the optional, visitor-enabled
Google Analytics path, while only Arcade page classes receive the
`okhp3.github.io` frame permission. The page-level policy does not turn
`_headers` into a GitHub Pages response-header configuration.

# Glee-fully Tools deployment contract

This repository is the source of truth for the public site at
[glee-fully.tools](https://glee-fully.tools).

## Publishing source

- **Source branch:** `main`
- **Current Pages mode:** GitHub Actions deployment
- **Repository-owned workflow:** `.github/workflows/pages.yml`
- **Release flow:** the workflow validates the exact `main` commit, builds a static Pages artifact, and deploys that artifact to GitHub Pages.

GitHub Pages is the sole public publishing target. Replit’s local preview workflow is for development only and does not publish the site.

## Artifact and paths

The published artifact is the repository root. It contains the root `index.html`, `assets/`, each public route directory, generated data files, and the committed `CNAME`. There is no bundler, framework build, or alternate output directory.

The site is served at the domain root. Existing root-relative links, asset references, and direct route directories (`/about/`, `/legal/`, and toolbox routes) are preserved exactly as authored. No base-path prefix or HTML rewrite is applied.

## Custom domain

`CNAME` is committed at the artifact root and must contain exactly:

`glee-fully.tools`

GitHub Pages custom-domain and HTTPS settings remain attached to `glee-fully.tools`. The CNAME must not be replaced with a preview or repository URL.

## Release guardrails

Run the repository-owned checks from a clean checkout before merging a release
change:

```bash
python3 scripts/build-search-index.py --check
python3 scripts/sync-portfolio-stats.py --check
python3 scripts/sync-css-version.py --check
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

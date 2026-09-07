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

The repository is the source; the published artifact is the reviewed inventory
staged by `scripts/public-artifact.py` into `$RUNNER_TEMP/glee-public-site`.
It contains the public pages and runtime assets, `CNAME`, `.nojekyll`, and
`.well-known/security.txt`. Development templates, documentation, agent/skill
packages, and tooling configuration are excluded. The workflow verifies the
complete inventory, bytes, and commit before upload, after download, and inside
the final Pages tar. There is no bundler or framework build.

The site is served at the domain root. Existing root-relative links, asset references, and direct route directories (`/about/`, `/legal/`, and toolbox routes) are preserved exactly as authored. No base-path prefix or HTML rewrite is applied.

## Custom domain

`CNAME` is committed at the artifact root and must contain exactly:

`glee-fully.tools`

GitHub Pages custom-domain and HTTPS settings remain attached to `glee-fully.tools`. The CNAME must not be replaced with a preview or repository URL.

## Release guardrails

Prepare changes on a temporary `codex/` branch. Generate the search index,
then portfolio stats, then rebuild the index if the stats changed page copy.
Run `scripts/sync-css-version.py` last: it updates CSS references and derives
the offline cache version from every precached file. Its `--check` mode blocks
releases with stale offline assets. Post-merge verification is read-only so
pulling a published commit cannot create another generated-content commit.

Replit's Sync button pushes the currently selected branch; it cannot supply
the approving review required by repository policy (the latest observed remote
rule requires zero approvals; see the governance record). Publish the temporary
branch through a pull request, finish its reviews and checks, then fast-forward
Replit's clean `main` from `origin/main`. Keep the origin URL set to
`https://github.com/OKHP3/Glee-fullyTools.git`. A stored PAT authenticates the
request but does not replace the review gate. Retire task branches only after
their work is merged or preserved with an explicit recovery reference.

The cross-browser test uses a local HTTP server. For those test documents only,
the runner removes CSP's HTTPS upgrade directive and disables service workers
in the navigation contexts so cached production HTML cannot override that
fixture. Production policies remain intact. A separate Chromium lifecycle
context tests real service-worker control, warm-page offline recovery, and
cache replacement.

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
python3 scripts/resilience-qa.py --static-only
```

The Pages workflow repeats the required checks and performs browser QA before
building the artifact. The previous reference to an external
`publishing-trigger-check` command is not an executable prerequisite in this
checkout and has been removed from the release contract. The repository
validation workflows continue to protect HTML, links, responsive layout, and
sparkle behavior. The resilience runner is the release proof for installability,
offline lifecycle, cross-browser behavior, crawler-visible metadata, and
third-party failure fallback; CI runs its full browser mode after installing
Chromium, Firefox, and WebKit.

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

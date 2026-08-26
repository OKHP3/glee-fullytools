# Main release governance

This is the authoritative repository-side release policy for
`OKHP3/Glee-fullyTools`. GitHub Pages publishes only from `main` through
`.github/workflows/pages.yml`; Replit preview is not a release path.

## Protected surfaces

Changes to these surfaces require repository-owner review through
`.github/CODEOWNERS`:

- `.github/workflows/` — validation, browser QA, and Pages deployment
- `.github/dependabot.yml` — automated dependency-update policy
- `_headers` — portable security-header policy
- `CNAME`, `site.webmanifest`, `robots.txt`, and `sitemap.xml` — public origin,
  installability, and crawler behavior
- `sw.js`, `offline.html`, `assets/js/`, and `assets/data/` — public runtime,
  offline behavior, and generated search/runtime data
- `docs/`, `CONTRIBUTING.md`, and `SECURITY.md` — release and security contracts

The catch-all `* @OKHP3` rule covers newly added files until a narrower rule is
needed. CODEOWNERS is review coverage, not branch protection; it does not by
itself prevent a direct push or prove that an owner approved a pull request.

## Supported release path

1. Open a pull request targeting `main`.
2. Run and pass the repository checks listed below.
3. Obtain at least one approving review from a code owner, with required
   conversations resolved.
4. Merge the pull request into `main`; do not use a direct push for normal
   release work.
5. Let the `push`-to-`main` Pages workflow validate that exact commit, build
   the SHA-named artifact, and deploy only that artifact.

Emergency direct pushes are an owner decision and must be followed by the same
validation and release review. They are not the normal or preferred path.

## Required checks

When branch protection is configured, require these PR checks by their job
names:

| Workflow | Required check |
|---|---|
| Site Validation | `Validate site HTML, links, and structure` |
| Viewport QA | `Responsive viewport QA (all pages × 8 viewports)` |
| Sparkle Banner QA | `Sparkle banner smoke test (5 pages)` |

The Pages workflow intentionally triggers on `push` to `main` and
`workflow_dispatch`, not on pull requests. Its
`Validate release commit and build Pages artifact` job is therefore a
post-merge release gate, not a PR required check. A failed Pages validation
must prevent deployment because the deploy job depends on it.

The repository’s current local release commands are listed in
`docs/deployment.md`. Generated-output checks must remain check-only in CI;
CI must not silently repair committed files.

## Desired branch-protection settings

The owner-side `main` rule should be configured with:

- Require a pull request before merging.
- Require at least one approving review from a code owner.
- Dismiss stale approvals when new commits are pushed.
- Require all conversations to be resolved.
- Require the three PR checks above before merging.
- Require branches to be up to date before merging when practical.
- Block force pushes and branch deletion.
- Apply the rule to administrators.
- Do not permit bypasses for routine releases; record any emergency bypass.

These settings are GitHub repository controls, not checked-in files. The
repository cannot truthfully claim they are active until the owner configures
and rechecks them in GitHub.

## Current observed GitHub settings

Read-only repository inspection on 2026-08-23 found:

- Default branch: `main`
- Visibility: public
- Pages source: GitHub Actions workflow, branch `main`, root path
- Custom domain: `glee-fully.tools`
- HTTPS enforcement: enabled
- Branch protection for `main`: **not configured** (`Branch not protected`)

Therefore the current release path has repository-owned workflow guardrails and
CODEOWNERS coverage, but it still permits direct pushes until the owner enables
the desired `main` branch rule. Pages deployment must not be described as
requiring PR approval until that owner-side setting is verified.

## Dependency update cadence

`.github/dependabot.yml` checks GitHub Actions and npm dependencies monthly.
Dependabot pull requests are covered by CODEOWNERS and must pass the same
required checks as any other change. The action-major-version policy remains
enforced by `scripts/check-workflow-actions.py`; Dependabot does not replace
that explicit repository policy.
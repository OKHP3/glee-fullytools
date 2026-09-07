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

## Required checks in the repository policy

When branch protection is configured, require these PR checks by their job
names:

| Workflow | Required check |
|---|---|
| Site Validation | `Validate site HTML, links, and structure` |
| Viewport QA | `Responsive viewport QA (all pages × 8 viewports)` |
| Sparkle Banner QA | `Sparkle banner smoke test (5 pages)` |
| Resilience QA | `Resilient web behavior (Chromium, Firefox, WebKit)` |

The Viewport QA, Sparkle Banner QA, and Resilience QA workflows intentionally have no
`paths` or `paths-ignore` filters. They run for every pull request targeting
`main`, so documentation- and governance-only pull requests still receive
completed successful statuses for the required browser checks. A pull request
that changes HTML, CSS, JavaScript, or `assets/data/sparkle.json` runs the same
full browser jobs; do not restore path filtering to optimize these required
checks.

The Pages workflow intentionally triggers on `push` to `main` and
`workflow_dispatch`, not on pull requests. Its
`Validate release commit and build Pages artifact` job is therefore a
post-merge release gate, not a PR required check. A failed Pages validation
must prevent deployment because the deploy job depends on it.

The repository’s current local release commands are listed in
`docs/deployment.md`. Generated-output checks must remain check-only in CI;
CI must not silently repair committed files.

GitHub verification on 2026-08-31 confirmed the workflow-only pull request
that introduced this policy completed all three required checks successfully.
The subsequent protected release pull request also completed the three checks
successfully, while the earlier governance-only pull request (before this
policy) had no browser-check statuses. This confirms both the repair and the
failure mode it prevents.

The landscape social-card check is a release gate: it verifies the approved
PNG is 1200×630 and that all published social-preview pages point to it with
the declared dimensions and alt metadata. `offline.html` is intentionally
noindex and excluded from this page-family check.

## Desired branch-protection settings

The owner-side `main` rule should be configured with:

- Require a pull request before merging.
- Require at least one approving review from a code owner.
- Dismiss stale approvals when new commits are pushed.
- Require all conversations to be resolved.
- Require all four PR checks listed above before merging.
- Require branches to be up to date before merging when practical.
- Block force pushes and branch deletion.
- Apply the rule to administrators.
- Do not permit bypasses for routine releases; record any emergency bypass.

These settings are GitHub repository controls, not checked-in files. The
repository cannot truthfully claim they are active until the owner configures
and rechecks them in GitHub.

## Historical observed GitHub settings (2026-08-31)

Repository inspection rechecked on 2026-08-31 found:

- Default branch: `main`
- Visibility: public
- Pages source: GitHub Actions workflow, branch `main`, root path
- Custom domain: `glee-fully.tools`
- HTTPS enforcement: enabled
- Branch protection for `main`: **configured and active**
- Pull requests: required before merging
- Required approving reviews: `1`, including a code-owner approval
- Stale approvals: dismissed when new commits are pushed
- Required conversations: all conversations must be resolved
- Required status checks:
  - `Validate site HTML, links, and structure`
  - `Responsive viewport QA (all pages × 8 viewports)`
  - `Sparkle banner smoke test (5 pages)`
- Branch freshness: required; the branch must be up to date before merging
- Force pushes: blocked
- Branch deletion: blocked
- Administrator enforcement: enabled

The resilience workflow is now present and runs on pull requests and releases,
but its job is not included in this previously observed branch rule yet. The
owner should add `Resilient web behavior (Chromium, Firefox, WebKit)` to the
required checks after the workflow has completed once on GitHub.

The historical observation above is retained for provenance and does not
override the newer observation below.

## Latest observed GitHub settings (2026-09-05)

A fresh read of `repos/OKHP3/Glee-fullyTools/branches/main/protection` found
**zero** required approving reviews and **code-owner review not required**.
Strict freshness and administrator enforcement are enabled; force pushes and
branch deletion are disabled. The required contexts are the three validation,
viewport, and Sparkle names listed above. Resilience is not in that remote rule.

The repository policy still calls for an approving owner review and all four
checks. These are owner review requirements, not a claim that GitHub currently
enforces them. The owner must explicitly choose whether to configure the remote
rule to match. No repository setting was changed during the September 5 program.
Recheck the rule at the actual release, because observed settings can change.

Local acceptance of `8dea009c7b1887b129a1c5540ec1a39f6c028841` is recorded in
the Architect packet and the implementation record. It does not establish
successful CI, GitHub artifact transfer, deployment, or live verification of the
final release commit. The executable handoff and separate pending categories
are in `remaining-program-2026-09-05/platform-release.md`.

## Dependency update cadence

`.github/dependabot.yml` checks GitHub Actions and npm dependencies monthly.
Dependabot pull requests are covered by CODEOWNERS and must pass the same
required checks as any other change. The action-major-version policy remains
enforced by `scripts/check-workflow-actions.py`; Dependabot does not replace
that explicit repository policy.

# Companion-Site Publishing Contract

**Status:** Documented release contract; live Pages health requires owner-side
confirmation.

This contract makes the publishing mechanics consistent across the three
companion repositories without making their sites visually or editorially
identical.

## Shared release stages

Each repository should implement these stages in order:

1. Check the exact checked-out commit and repository state.
2. Verify committed generated outputs and cache-buster tokens in check-only mode.
3. Run the site validator, link/sitemap checker, metadata/accessibility checks,
   and any site-specific contrast or dark-mode checks.
4. Run browser responsive QA when the dependency and browser are available.
   Missing browser coverage is `BLOCKED` or `NOT RUN`, never a silent pass.
5. Build a clean artifact from the validated checkout, including the repository's
   custom-domain file and public error page.
6. Upload that immutable artifact and deploy only after validation succeeds.
7. Perform a separate live smoke test against the real public domain. A green
   Actions run proves the workflow and artifact path, not DNS, Pages settings, or
   public asset delivery.

For GitHub Pages sites, repository `_headers` files are not treated as delivered
response headers. Each site's threat model must distinguish portable policy
configuration from observed production headers, and the live smoke result must
be retained or reviewed by the owner.

Each repository should also keep one authoritative release-governance document
covering CODEOWNERS, dependency-update cadence, required checks, approval rules,
and whether direct pushes are actually blocked by branch protection.

## Site adapters

| Repository | Domain | Required domain file | Site-specific checks |
|---|---|---|---|
| `OKHP3/OverKill-Hill` | `overkillhill.com` | `CNAME` | OverKill Hill contrast and fork-review checks; its page inventory |
| `OKHP3/Glee-fullyTools` | `glee-fully.tools` | `CNAME` | Glee accent contrast, both-form dark coverage, sparkle, template metadata, and its toolbox inventory |
| `OKHP3/AskJamie` | `askjamie.bot` | `CNAME` | AskJamie theme/contrast rules, responsive paths, and its page inventory |

The exact command names may differ where a repository genuinely has a
different script, but equivalent checks must retain the same failure semantics
and evidence labels.

## Safe shared mechanics

The repositories may share validation contracts, workflow permissions,
concurrency rules, artifact retention, report upload, check-only generated
output behavior, and release-report structure. Cross-site comparison should
compare these mechanics, not blindly synchronize files.

## Protected differences

Do not copy or normalize palettes, typography, logos, illustrations, copy,
analytics identifiers, canonical/Open Graph domains, page inventories, body
scopes, dark-mode policy, screenshots, or brand-specific CSS sections. A shared
workflow is correct when it produces equivalent safety guarantees while the
three sites continue to look and read like separate properties.

## Current repository comparison

The Glee-fully repository now has a checked-out-commit Pages workflow in
`.github/workflows/pages.yml`. Public repository definitions observed on
August 21, 2026 showed:

- AskJamie already had a validation job and a deploy job that transfers a
  prepared Pages artifact; its public definition still used a single combined
  workflow and had less explicit separation between check-only generation and
  artifact construction.
- OverKill Hill had stronger read-only permissions and browser/contrast checks,
  but no public Pages deploy workflow was present.
- Glee-fully had separate static, viewport, and sparkle workflows, but no
  Pages deploy workflow and its validation workflow previously repaired stale
  generated files silently.

Those remote definitions are comparison evidence only. Updating the sibling
repositories requires their own authorized changes and live validation; this
contract does not authorize remote writes.
# ADR-0007: Safe Stack Conformance for Glee-fully Tools

## Status

Accepted for the Glee-fully Tools baseline. Cross-site convergence remains proposed.

## Date

2026-09-12

## Context

A locally committed stack proposal could not be pushed directly to protected
`main`. Review found that its checker could report success after a check raised
an exception and that automatic repair would untrack retained audit records,
archived scripts, and skill references. The proposal also claimed CI enforcement
without a workflow invocation.

The owner delegated a nondestructive correction and delivery through the normal
review gates. The original proposal remains available in commit `77c82b39`.
Its cross-site audit claims and migration assumptions are historical proposal
material, not independently verified acceptance evidence for sibling sites.

## Decision

Enforce this repository's existing stack baseline through
`scripts/check-stack-conformance.py` in the Site Validation workflow. Run its
safety regressions before the checker. No dependency upgrade, downgrade, or
removal is part of this decision.

| Layer | Current baseline |
|---|---|
| Node QA tooling | 22.19.0 in `.node-version` and `package.json` engines |
| Browser QA | Playwright 1.60.0; retain optional Puppeteer tooling at 25.10.0 |
| Lighthouse | 13.4.1 |
| Python QA | beautifulsoup4 4.15.0; Playwright 1.60.0 where declared |
| Development server | `scripts/serve-site.py` |
| Pages deployment | `actions/deploy-pages@v5` |
| Agent guidance | `AGENTS.md` canonical, `CLAUDE.md` a pointer; retain `replit.md` |
| Skills and archives | Preserve existing references and archived scripts |
| Audit records | Preserve tracked evidence under `assets/audit/` |
| Disposable output | Ignore Python bytecode and `dist-pages/` where present |

Future dependency changes must update the existing dependency policy and checker
in the same reviewed change. These pins describe the current baseline, not a
recommendation to downgrade other repositories.

### Safety and failure behavior

- Unexpected check failures and invalid exemption configuration exit 2, including
  in `--warn-only` mode. JSON reports `pass: false` for incomplete verification.
- Policy violations exit 1; warning mode may allow those findings only.
- Exemptions must be an array of codes with a nonempty reason. Checker errors
  cannot be exempted.
- Automatic repairs never untrack or delete files and never modify the Git index.
  Tracked disposable output requires a separate manual review.
- Supported mechanical repairs update version metadata or ignore patterns;
  `--fix --dry-run` previews them. Dependency declarations remain manual.

### Delivery

Use a temporary branch and a PR into protected `main`. When local `main` already
contains unpublished commits, preserve their ancestry with a merge commit, then
fast-forward the local and Replit `main` checkouts after verifying their state.
Never bypass protection or force-push to resolve synchronization errors.

## Consequences

The baseline is now executable in CI without removing operating knowledge or
historical evidence. The checker adds a maintenance obligation: keep it aligned
with approved dependency and workflow changes. Consolidating sibling toolchains,
removing optional packages, and pruning archives remain separate proposals that
require evidence and review in their own repositories.

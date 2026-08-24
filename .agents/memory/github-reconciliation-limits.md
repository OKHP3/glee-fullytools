---
name: GitHub reconciliation limits
description: Replit connector and Git transport constraints encountered when reconciling a public GitHub repository.
---

For a public GitHub repository, fetch the live branch with credential helpers disabled into a temporary ref before comparing local history. Treat the live GitHub branch—not a stale local tracking ref—as authoritative.

**Why:** The Replit GitHub connector can read and create individual Git blobs, but its Git Database tree operation is unavailable and its Contents write path can be blocked by the connector proxy. The proxy can also truncate large request bodies while returning a misleading success response. Git transport with a valid PAT remains the reliable path for publishing a complete tree.

**How to apply:** Verify blob SHAs and never advance a branch after a size-mismatched API response. Use recovery refs before rebasing or pruning. After reconciliation, a clean local `main` that is ahead of verified `origin/main` is ready for a normal fast-forward push; force-push is unnecessary unless the remote moves independently.

Stale generated `subrepl-*` remote definitions can remain in `.git/config` after their branches are removed. Remove those remotes after archiving their branch tips, but preserve the managed backup remote and GitHub `origin`.

**Why:** Commands that enumerate all remotes can repeatedly contact obsolete Replit SSH endpoints, creating project-specific noise that is independent of GitHub authentication.

**How to apply:** A clean `git fetch --all --prune` after removing only the generated `subrepl-*` remotes confirms the remote fan-out is resolved; test `origin` authentication separately.

GitHub connector OAuth access with the general `repo` scope can still lack the separate `workflow` scope. In that state, normal Git Data writes succeed but a tree containing `.github/workflows/*` returns `404`.

**Why:** GitHub protects workflow-file updates with a distinct OAuth permission. Repository-level `push` capability alone does not prove that workflow changes can be published through the connector.

**How to apply:** Before publishing a history that changes workflow files, verify the connector grant includes `workflow`. If it does not, reauthorize the connector; if a workflow-scoped PAT is available, publish through Git Smart HTTP instead.

For Git Smart HTTP with a PAT, authenticate as `x-access-token` through `GIT_ASKPASS` (Basic authentication). Do not assume an `Authorization: Bearer` extra header is accepted for Git push.

**Why:** A valid workflow-scoped PAT can be rejected by Git Smart HTTP when supplied as a Bearer header, while the same token succeeds through the standard username/password exchange.

**How to apply:** Use an ephemeral askpass helper that returns `x-access-token` for the username prompt and the secret for the password prompt; clear credential helpers and never print or persist the token.
---
name: GitHub PAT credential helper
description: Workspace Git pushes can use the GITHUB_PAT secret through a local helper without embedding the token in the remote URL.
---

Use the workspace secret through a temporary or local Git credential helper when
the Replit GitHub OAuth helper rejects workflow-file pushes or a stale helper
reports an invalid token. The helper should read `GITHUB_PAT` at invocation
time; never put the token itself in `.git/config`, a remote URL, or chat.

**Why:** The GitHub API token can be valid with `repo` and `workflow` scopes
while the default Git OAuth helper still supplies an invalid or under-scoped
credential.

**How to apply:** Reset inherited credential helpers locally before adding a
helper that returns `x-access-token` and the environment variable value. Verify
with a normal no-op push and inspect only helper configuration, never the
credential.
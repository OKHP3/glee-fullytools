---
name: Local merge history normalization
description: Replit may replay a local merge linearly after a protected-branch synchronization
---

After a local merge of a divergent `main` into the checkout, verify the reflog and
final parentage rather than assuming the merge commit remains. The environment may
normalize the result into local commits replayed on top of `origin/main`.

**Why:** A successful merge command can be followed by host synchronization that
changes local-only commit SHAs without changing the remote or discarding the work.

**How to apply:** Preserve a recovery ref, inspect `git reflog` and `git log --graph`,
then report the final `HEAD`/remote relationship and any generated commits.
---
name: Local Git checkpoint safety
description: Replit may normalize merges or checkpoint file edits into branch refs
---

After local merges or file edits, inspect the reflog and decorated graph rather
than assuming branch refs moved only through explicit Git commands. The
environment may normalize local history or checkpoint edits into a commit on
the active branch, including generated validation outputs. A managed backup ref
may point to the same commit.

**Why:** Treating an automatically-created commit as a clean feature commit can
push generated reports or misstate the relationship to the verified base.

**How to apply:** Before staging or pushing, inspect `git status`, `git reflog`,
and `git log --graph --decorate`, then compare against the verified base. Keep
unexpected history and managed recovery refs intact. When generated outputs
entered an automatic commit, retain useful validation evidence and use an
additive cleanup commit rather than rewriting history when history must be
preserved.

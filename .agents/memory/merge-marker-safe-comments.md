---
name: Merge-marker-safe comments
description: Avoid decorative comment separators that merge validation can misidentify as unresolved conflicts.
---

Use hyphen-based HTML comment dividers instead of lines whose trimmed content
begins with repeated equals signs.

**Why:** The merge-resolution validator treats such decorative lines as conflict
markers even when they are ordinary HTML comments, blocking an otherwise clean
rebase.

**How to apply:** When adding or touching section-divider comments in HTML, use
hyphens or descriptive text rather than equals-sign bars.
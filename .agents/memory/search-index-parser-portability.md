---
name: Search index parser portability
description: Keeps generated search-index content deterministic when Python HTMLParser versions differ.
---

Treat embedded iframe contents, including fallback markup, as non-indexable page text.

**Why:** Python HTMLParser patch releases can interpret raw-text iframe fallback markup differently, making a committed search index look stale in CI even when source HTML is unchanged.

**How to apply:** When adding embedded content to public pages, exclude its raw fallback subtree from search extraction. Regenerate and commit the search index after changing extraction rules.
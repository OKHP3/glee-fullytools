---
name: Post-merge generated artifacts
description: Ordering and repair behavior for generated discovery outputs and offline-shell cache versions.
---

The post-merge hook should rebuild discovery outputs in dependency order before
validating them and running the idempotent CSS, JavaScript, and service-worker
cache-version synchronizer. Rebuild the search index both before and after
portfolio-stat synchronization because the stats patch changes indexable pages.

**Why:** A merged content/evidence change can update the service-worker
precache inputs without updating its generated cache name. Portfolio-stat
generation also changes page text consumed by search indexing, so checking the
index only before stats synchronization leaves it stale for the next merge.

**How to apply:** Generate search index, synchronize portfolio stats, then
regenerate the search index before checking both outputs. Regenerate sitemap and
feed from the refreshed index, check all discovery artifacts before cache
synchronization, and retain final validators so failures remain visible.
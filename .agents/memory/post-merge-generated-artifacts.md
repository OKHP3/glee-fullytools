---
name: Post-merge generated artifacts
description: Ordering and repair behavior for generated discovery outputs and offline-shell cache versions.
---

The post-merge hook must validate committed discovery outputs before running the
idempotent CSS, JavaScript, and service-worker cache-version synchronizer, then
verify the synchronized state.

**Why:** A merged content/evidence change can update the service-worker
precache inputs without updating its generated cache name. A check-only step
fails after the merge and gives no safe local repair path.

**How to apply:** Keep sitemap/feed validation ahead of cache synchronization;
allow the synchronization step to repair stale generated references, and retain
the final check plus site validators so failures remain visible.
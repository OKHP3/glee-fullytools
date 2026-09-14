---
name: Release evidence contracts
description: Discovery outputs and Pages publication must share explicit, testable scope contracts.
---

The public inventory contract should be the single scope authority for search,
sitemap, feed, catalog statistics, and release-artifact checks. Generated
reports should carry both a run date and UTC generation time, while historical
files remain identifiable as historical evidence. For tracked current-day
validation reports, an unchanged payload must preserve the existing bytes and
generation timestamp; that timestamp means when the evidence content last
changed, not when every check ran.

**Why:** Static sites accumulate easy-to-miss drift when each generator invents
its own exclusions or when dated reports are mistaken for current proof.
Timestamp-only rewrites add review noise without adding evidence.

**How to apply:** Extend the shared inventory and its tests before changing an
output generator or the Pages copy policy; validate a representative artifact,
including forbidden-path failures, before release. Keep idempotency behavior
covered by a regression test whenever a tracked report writer changes.

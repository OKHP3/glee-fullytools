---
name: Release evidence contracts
description: Discovery outputs and Pages publication must share explicit, testable scope contracts.
---

The public inventory contract should be the single scope authority for search,
sitemap, feed, catalog statistics, and release-artifact checks. Generated
reports should carry both a run date and UTC generation time, while historical
files remain identifiable as historical evidence.

**Why:** Static sites accumulate easy-to-miss drift when each generator invents
its own exclusions or when dated reports are mistaken for current proof.

**How to apply:** Extend the shared inventory and its tests before changing an
output generator or the Pages copy policy; validate a representative artifact,
including forbidden-path failures, before release.
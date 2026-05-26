# Asset Audit — 2026-05-03

**Generator:** `scripts/audit-assets.py`
**Outputs:** `audit/asset-inventory-2026-05-03.json` (full detail) +
`assets/data/icon-map.json` (best-icon mapping)

---

## Summary

| Class | Total in repo | Referenced | Orphaned |
|---|---:|---:|---:|
| GPT icons (`Glee-fullyTools-GPTIcon-*`) | 162 | 49 | 113 |
| Favicon variants (`assets/img/favicons/*`) | 8 | 4 | 4 |
| Butterfly hero composites (multiple sizes/poses) | 19 | 0 | 19 |
| Other (decorative, retired, holding) | 17 | 0 | 17 |
| **Total** | **206** | **53** | **153** |

The high orphan count is **mostly intentional design slack**:

* The GPT-icon family ships in 3 pose variants × 2 backgrounds × 2 styles —
  only 1 pose × 1 background is wired into each tool-ette page.  The other
  variants are kept for future hero/social/print needs.
* The butterfly composites are oversized (some > 3 MB each) source files that
  pre-date the per-tool icon rollout.  They are kept on disk but not loaded by
  any page.

---

## Per-tool icon mapping

`assets/data/icon-map.json` documents, for every tool-ette and branch hub
prefix (`00`, `01a`–`07g`), the four available variants:

```json
"01a": {
  "retro_stripe":     "assets/img/Glee-fullyTools-GPTIcon-01a-Resume-Builder-Background-RetroStripe-Square-1024.png",
  "retro_stripe_alt": null,
  "transparent":      "assets/img/Glee-fullyTools-GPTIcon-01a-Resume-Builder-Background-Transparent-Square-1024.png",
  "transparent_alt":  null,
  "primary":          "assets/img/Glee-fullyTools-GPTIcon-01a-Resume-Builder-Background-RetroStripe-Square-1024.png"
}
```

`primary` is what `scripts/activate-icons.py` uses for hero `<img>` and
`og:image` swap.  50 prefixes total are mapped (1 for the trunk + 7 branches
+ 42 tool-ettes).

---

## Orphan candidates for future cleanup

The 17 "other" orphans break down (top by size) as:

| Size | File | Notes |
|---:|---|---|
| 3.0 MB | `Glee-fully Neon Butterflies.png` | Source/marketing art; never used on site |
| 3.0 MB | `Glee-fullyTools TitleLowMidButterflyLeftBigToolboxRight Wide 1536.png` | Hero study; superseded by per-tool icons |
| 2.9 MB | `Glee-fullyTools TitleRotLowMidButterflyLeftToolboxRight Wide 1536.png` | Same |
| 2.9 MB | `Glee-fullyTools TitleLowMidButterflyLeftToolboxRight Wide 1536.png` | Same |
| 2.9 MB | `Glee-fullyTools TitleHighMidButterflyLeftToolboxRight Wide 1536.png` | Same |
| 2.3 MB | `Glee-fullyTools ButterflyPathLeft Wide 1536.png` | Same |
| 2.3 MB | `Glee-fullyTools ButterflyLoopRight Wide 1536.png` | Same |
| 2.3 MB | `Glee-fully Retro Butterfly Design.png` | Source art |

These are roughly **22 MB** of unused PNG.  Removing them would shave the
GitHub clone size meaningfully but offers no runtime benefit (they are not
fetched by any page).  Per the "do not delete content unless clearly safe"
rule, this is **deferred** for a future curation pass with the human owner.

---

## Best practices already in place

* All 49 referenced tool/branch pages now carry their purpose-built
  `Glee-fullyTools-GPTIcon-*` artwork as hero `<img>`, `og:image`,
  `twitter:image`, and JSON-LD `image` (Tier A3 from the 2026-05-02 backlog).
* All non-hero `<img>` tags have `loading="lazy" decoding="async"`.
* The header logo is intentionally eager-loaded to protect LCP.
* All images have meaningful `alt` attributes (validated by the prior pass —
  `Imgs missing alt: 0`).

---

## Re-running

```bash
python3 scripts/audit-assets.py
```

This will rebuild both the inventory JSON and the icon-map JSON. The icon-map
is what `scripts/activate-icons.py` reads when refreshing hero artwork — it is
safe to commit.

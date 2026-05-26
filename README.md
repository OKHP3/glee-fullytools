# Glee-fully Personalizable Tools™

Welcome to **Glee-fully Personalizable Tools™** — the joyful studio of custom GPTs that make everyday life feel lighter, smarter, and more personal.  
We believe creativity thrives when structure and delight work together, so we built a platform that does both.

### 🌟 Overview

At **Glee-fully™**, every Tool, Tool-ette, and Function adapts to *you*.  
Whether you’re exploring new career paths, planning meals, organizing projects, or simply rediscovering balance, our systems learn your rhythm — adding polish without pressure.  

We treat technology like a friend with good taste: it remembers what you love, keeps you organized, and always makes things feel a little more *you*.

### 🧰 Explore the Suite

Our growing ecosystem includes:

- **Discovered Careers** – find paths that match your spark and story.  
- **Organized Life** – design routines that work *with* you, not against you.  
- **Healthy Bee-ing** – track habits, moods, and motivation with kindness.  
- **Traveler’s Guide** – plan journeys with purpose and ease.  
- **Treasured Finds** – curate collections and memories worth keeping.  
- …and dozens more under our seven Tool branches and forty plus Tool-ettes.

Every element is crafted to be modular, charming, and useful — a mix of retro aesthetics and modern AI intelligence wrapped in authentic warmth.

### 💡 Why We Exist

Because AI should *feel good to use*.  
We believe productivity tools shouldn’t drain your energy or hide behind jargon. **Glee-fully™** reimagines personalization as joy — not data extraction.  
Our suite shows that structure can be playful, creativity can be systematic, and technology can be *deeply human*.

### 💬 Connect

- **Website:** [https://glee-fully.tools](https://glee-fully.tools)  
- **Email:** [contact@glee-fully.tools](mailto:contact@glee-fully.tools)  
- **Support:** [ko-fi.com/gleefullypersonalizabletools](https://ko-fi.com/gleefullypersonalizabletools)

---

> **Glee-fully Personalizable Tools™** — *Smart design made human.*  
> Build your world the Glee-fully way — where technology feels like joy.

---

### 🛠 Maintainers' notes

* **Live audit reports:** `FINAL_AUDIT_2026-05-03.md`, plus
  `AUDIT_PAGE_INVENTORY_*`, `AUDIT_LINKS_*`, `AUDIT_ASSETS_*`,
  `AUDIT_ACCESSIBILITY_*`, `AUDIT_PERFORMANCE_*` covering every phase of the
  2026-05-03 pass.
* **Run validators after content edits:**
  ```bash
  python3 scripts/validate-site.py  &&  python3 scripts/check-links.py
  ```
  Exit 0 = safe to publish.
* **Rebuild search/feed/icon map after content edits:**
  ```bash
  python3 scripts/build-search-index.py
  python3 scripts/audit-assets.py
  python3 scripts/generate-feed.py
  ```
* **Add a new tool-ette page:** drop the new `Glee-fullyTools-GPTIcon-…` PNG
  into `assets/img/`, add its URL to `sitemap.xml`, then run the four
  mutator scripts in order (`normalize-head` → `activate-icons` → `inject-jsonld`
  → `inject-breadcrumb`) and the three regenerators above. See `replit.md` for
  the detailed run order.
* **Template library:** `assets/templates/` mirrors the full site hierarchy
  with structural-only clones of every page. Every template preserves nav,
  footer, scripts, CSS, JSON-LD scaffold; every page-specific value is a
  `{{PLACEHOLDER}}` token. Documented in `assets/templates/TEMPLATE_INDEX.md`.
  Regenerate with `python3 scripts/generate-templates.py` (idempotent; pass
  `--force` to overwrite). Templates are dev artifacts and are excluded from
  the sitemap, search index, feed, and every validator.

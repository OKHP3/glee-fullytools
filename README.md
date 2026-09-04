# Glee-fully Personalizable Tools™

Welcome to **Glee-fully Personalizable Tools™** — the joyful studio of custom GPTs that make everyday life feel lighter, smarter, and more personal.  
We believe creativity thrives when structure and delight work together, so we built a platform that does both.

### 🌟 Overview

At **Glee-fully™**, every Tool, Tool-ette, and Function is designed to adapt to
*you*.
Whether you’re exploring new career paths, planning meals, organizing projects, or simply rediscovering balance, our systems learn your rhythm — adding polish without pressure.  

We treat technology like a friend with good taste: it remembers what you love, keeps you organized, and always makes things feel a little more *you*.

### 🧰 Explore the Suite

Our growing ecosystem includes:

- **Discovered Careers** – find paths that match your spark and story.  
- **Organized Life** – design routines that work *with* you, not against you.  
- **Healthy Bee-ing** – track habits, moods, and motivation with kindness.  
- **Traveler’s Guide** – plan journeys with purpose and ease.  
- **Treasured Finds** – curate collections and memories worth keeping.  
- …and more under our seven Tool branches and 42 catalog Tool-ettes.

Every element is crafted to be modular, charming, and useful — a mix of retro aesthetics and modern AI intelligence wrapped in authentic warmth.

### 🌱 Current phase

Glee-fully Tools is in **active growth and refinement**. The public site is a
catalog and routing hub, not a claim that every externally hosted GPT is
finished: 1 Tool-ette is live, 24 are beta, and 17 are unavailable while their
launch destinations are completed or owner-confirmed. The authoritative
inventory, state definitions, and completion contract live in
[`docs/suite-promise.md`](docs/suite-promise.md).

### 💡 Why We Exist

Because AI should *feel good to use*.  
We believe productivity tools shouldn’t drain your energy or hide behind jargon. **Glee-fully™** reimagines personalization as joy — not data extraction.  
Our suite shows that structure can be playful, creativity can be systematic, and technology can be *deeply human*.

### 📚 Public inventory

- **63** production HTML files, including utility and fallback pages
- **60** indexable public pages in the sitemap and search index
- **1** Toolbox hub, **7** branch hubs, and **42** Tool-ette pages
- **49** Atom feed entries for the branch and Tool-ette catalog

The feed is an update stream rather than a mirror of every public page, and the
9 structural templates under `assets/templates/` are development artifacts,
not additional public pages.

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
* **Mermaid runtime:** the `ecosystem/` and `universe/` diagrams run on
  Mermaid, vendored locally at `assets/vendor/mermaid/` (not loaded from a
  CDN). `assets/vendor/mermaid/VERSION` pins the exact release; a daily
  `mermaid-version-watch` GitHub Action compares it against the latest npm
  release and opens/updates a tracking issue when the vendored copy falls
  behind -- re-vendoring is a deliberate, reviewed step, never automatic.
  `scripts/validate-site.py` checks the VERSION pin against the vendored
  bundle and that every page with a live diagram carries a CSP class that
  allows Mermaid's runtime-generated inline styles (see `scripts/csp.py`).
  Every page's CSP is now enforced via a per-page <meta> tag
  (`scripts/generate-csp.py`) -- previously only defined, unenforced, in
  `_headers`, which GitHub Pages does not serve.
* **Rebuild the search index and asset map after content edits:**
  ```bash
  python3 scripts/build-search-index.py
  python3 scripts/audit-assets.py
  # feed.xml is a checked-in artifact; its historical generator is retired
  # under scripts/archive/ and is not part of the active pipeline.
  ```
* **Add a new tool-ette page:** drop the new `Glee-fullyTools-GPTIcon-…` PNG
  into `assets/img/`, add its URL to `sitemap.xml`, then run the four
  mutator scripts in order (`normalize-head` → `activate-icons` → `inject-jsonld`
  → `inject-breadcrumb`) and the active regenerators above. See `replit.md` for
  the detailed run order.
* **Template library:** `assets/templates/` mirrors the full site hierarchy
  with structural-only clones of every page. Every template preserves nav,
  footer, scripts, CSS, JSON-LD scaffold; every page-specific value is a
  `{{PLACEHOLDER}}` token. Documented in `assets/templates/INDEX.md`. The
  current templates are maintained directly as nine structural files; the
  superseded `scripts/generate-templates.py` generator should not be rerun.
  Templates are dev artifacts and are excluded from the sitemap, search index,
  feed, and every validator.

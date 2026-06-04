# agent-skills.md — Glee-fully Site Governance

This file is the operating constitution for any AI agent working on `OKHP3/Glee-fullyTools`.
Read it before touching any file. The site is both a working product and a portfolio artifact — every session must leave it at least as good as it found it.

---

## Read These First

1. `replit.md` — structure, CSS scope map, script run-order, recent changes
2. `assets/docs/FINAL_AUDIT_2026-05-03.md` — 26-item canonical change log
3. `assets/docs/OPEN_TODOS_2026-05-03.md` — deferred items and editorial decisions
4. `scripts/validate-site.py` — run before **and** after every change; must exit 0
5. `scripts/check-links.py` — run before **and** after every change; must exit 0

---

## Core Constraints (Never Violate)

1. **Static-only architecture.** No Node.js, no bundler, no framework without explicit owner approval.
2. **No build step without owner approval.** WebP, PurgeCSS, bundling — all require sign-off.
3. **Preserve brand voice.** Warm, human, retro-bright, approachable. Not corporate or generic SaaS.
4. **Preserve trunk → branch → tool-ette taxonomy.** Do not flatten, rename, or reorder without instruction.
5. **No fabricated content.** No invented GPT URLs, metrics, testimonials, or legal statements.
6. **Idempotent scripts with AUTOGEN markers only.** Site-wide changes must use scripts with "skip if present" guards. Scripts live in `scripts/`.

---

## CSS Scope Map

Edit `assets/css/theme.css` in the **correct scope only**. Each scope has a `╔══╗` banner.

| Scope | Starts at | Selector pattern |
|---|---:|---|
| GLOBAL | L 6 | unscoped / `:root` / `body` |
| OVERKILL | L 2215 | `body:not(.glee-main):not(.askjamie-main) …` |
| GLEE | L 2633 | `.glee-main …` |
| ASKJAMIE | L 3659 | `.askjamie-main …` |
| CROSS-BRAND | L 4116 | `.glee-main … , .askjamie-main …` |

Never add `<style>` blocks to HTML. Never use hardcoded hex — use `var(--color-*)` tokens.

---

## Auto-Generated Files (Do Not Hand-Edit)

| File | Regenerate with |
|---|---|
| `assets/data/search-index.json` | `python3 scripts/build-search-index.py` |
| `assets/data/icon-map.json` | `python3 scripts/audit-assets.py` |
| `feed.xml` | `python3 scripts/generate-feed.py` |

Rebuild the search index after any HTML content change. `scripts/post-merge.sh` does this automatically on task merges.

---

## Mermaid Referral Invariant

Every page with a `.mermaid` diagram must have exactly one `.mermaid-referral` credit linking to `https://mermaidchart.cello.so/UhVlNtC2MlS` in `#FF3670`. Currently only `ecosystem/` and `universe/`. `validate-site.py` enforces this and exits non-zero if violated.

---

## 10 Agent Skills

Each skill uses the same schema: **Purpose · Checks · Off-limits**.

### skill.static-site-auditor
**Purpose:** Verify GitHub Pages readiness and structural integrity.
**Checks:** `validate-site.py` exits 0; `check-links.py` exits 0; all internal hrefs are root-absolute; no render-blocking `<script>` tags; no new build-step dependencies introduced.
**Off-limits:** Do not introduce `node_modules`, `package.json`, or bundler config. Do not change `publicDir` without approval.

### skill.responsive-render-tester
**Purpose:** Confirm correct rendering across all device widths (320, 375, 390, 414, 768, 1024, 1280, 1440 px).
**Checks:** No horizontal overflow; nav usable and hamburger functional on mobile; skip link present; search modal opens/closes/doesn't trap focus; breadcrumbs wrap cleanly; CTA buttons ≥ 44×44 px; footer stacks; no console errors.
**Off-limits:** No page-specific CSS hacks. All responsive fixes go in `theme.css` GLOBAL scope.

### skill.portfolio-positioning-reviewer
**Purpose:** Ensure the site works as a credible portfolio artifact — not just a working site.
**Checks:** Homepage explains value within 5 seconds; every tool-ette has a plain-English utility sentence; branch pages act as visual routing hubs; About page makes the portfolio case; every page has at least one clear next action; no page is a dead end.
**Off-limits:** Do not rewrite brand voice to sound corporate. Do not invent capability claims not backed by visible outputs.

### skill.glee-brand-guardian
**Purpose:** Preserve Glee-fully voice and visual identity across all agent sessions.
**Checks:** No hardcoded hex values in new HTML or CSS; no `<style>` blocks or new inline `style="…"` attributes; no generic placeholder copy shipped to production; brand spelling uses `Glee‑fully` (non-breaking hyphen `&#8209;`) in display text and `glee-fully` in URLs.
**Off-limits:** Do not use Bootstrap, Tailwind, or generic component library aesthetics. Do not rename tool-ettes or branches.

### skill.accessibility-aa-reviewer
**Purpose:** Maintain WCAG 2.2 AA-oriented practical conformance.
**Checks:** All images have descriptive `alt`; all controls have accessible names; no keyboard traps; focus visible on all interactive elements; tap targets ≥ 44×44 px; color not sole conveyor of info; `prefers-reduced-motion` suppresses all animations; `<main id="main">` and `.skip-to-content` on every page.
**Off-limits:** Do not remove `aria-label` from nav toggle, search button, or breadcrumb. Do not remove `role` from search modal without equivalent semantics.

### skill.seo-schema-curator
**Purpose:** Maintain structured data and metadata quality across all 60 pages.
**Checks:** `<title>` matches the canonical format; `<meta name="description">` is non-empty; `<link rel="canonical">` points to the page's own URL; `og:url` matches canonical; `og:image` resolves to a real file; JSON-LD parses as valid JSON; `BreadcrumbList` JSON-LD matches the visible breadcrumb nav; sitemap includes every indexable page with accurate `lastmod`.
**Off-limits:** No fabricated FAQ entries. Do not change canonical URLs without also updating sitemap, breadcrumb, and `og:url`.

### skill.conversion-path-auditor
**Purpose:** Ensure every visitor type has a clear next action.
**Checks:** Every tool-ette has a "Keep exploring" tray (parent branch, siblings, Toolbox, Search); no page ends without ≥ 1 CTA; all GPT "Open Tool" links resolve to live ChatGPT URLs; Ko-fi link present in footer; contact and social links correct.
**Off-limits:** No more than 5 CTA links per page. Do not add Ko-fi inline widgets in the body — footer placement is intentional.

### skill.artifact-proof-checker
**Purpose:** Ensure portfolio claims are backed by visible evidence.
**Checks:** Audit reports exist and are dated correctly (`assets/docs/`); validation JSON outputs exist and are recent (`assets/audit/`); search index was rebuilt after the most recent content change; `sitemap.xml` and `feed.xml` are up to date; page/tool counts in docs match actual filesystem counts.
**Off-limits:** Do not delete audit reports without owner approval. Do not update "Recent Changes" in `replit.md` with unverified claims.

### skill.staleness-drift-detector
**Purpose:** Catch content that has become outdated or inconsistent.
**Checks:** No `<!-- TODO -->` comments remain in production HTML; audit report dates match when work was done; `sitemap.xml` `lastmod` is accurate; search index page count matches indexable pages; `replit.md` "Recent Changes" reflects current state; construction banners only on genuinely incomplete pages.
**Off-limits:** Do not silently update dates to make things look newer. Do not remove "under construction" language from pages that genuinely are incomplete.

### skill.agent-safety-governor
**Purpose:** Prevent destructive or out-of-scope changes.
**Checks:** `validate-site.py` and `check-links.py` both exit 0 before you start; planned change is within the assigned task's scope; no files outside the task's relevant file list are touched; a verification method exists before any large change begins.
**Off-limits:** No large framework rewrites; no deleting `assets/img/` files without documentation; no fabricated content; no CSS scope violations; no `<style>` blocks, inline styles, or `!important` hacks; no commits that break validators; no removing the Mermaid referral credit.

---

## Script Quick Reference

```bash
# Before AND after every change:
python3 scripts/validate-site.py
python3 scripts/check-links.py

# After any HTML content change:
python3 scripts/build-search-index.py

# Mutators (idempotent, safe to re-run):
python3 scripts/normalize-head.py
python3 scripts/activate-icons.py
python3 scripts/inject-jsonld.py
python3 scripts/inject-breadcrumb.py

# Regenerators:
python3 scripts/audit-assets.py
python3 scripts/generate-feed.py
```

*Maintained by OverKill Hill P³™ · Last updated 2026-05-27*

---

## Language Standard: en-US

This project is authored, owned, and maintained by a United States-based creator.
All user-facing content must use United States English (`en-US`).

Scope: UI copy, documentation, README content, release notes, comments intended for
human readers, prompts, tooltips, button text, error messages, validation messages,
QA/QC reports, and marketing language.

Examples of required US-EN spellings:
color, behavior, organization, optimize, customize, center, analyze, modeling,
artifact, visualization, standardization, initialize, finalize, prioritize, summarize,
license (noun), program, catalog, fulfill, gray, toward, among, while.

Do NOT change the following where spelling is externally defined or technically significant:
- Direct quotations from external sources
- Proper nouns, brand names, product names
- Dependency, package, or library names
- URLs, file names, route names
- API fields, schema keys, code identifiers
- Generated lockfiles or external standards

US English compliance is a required QA/QC gate. It is not a stylistic preference.
Any output that fails this standard is a defect.

# Page Inventory — 2026-05-03

**Generator:** `scripts/validate-site.py` → `audit/validation-report-2026-05-03.json`
**Pages scanned:** 60 HTML files (excludes `node_modules`, `.local`, `.git`, `attached_assets`)
**Validation status:** **0 issues, 0 warnings**

---

## Summary

| Metric | Value |
|---|---:|
| HTML files in repo | 60 |
| URLs in `sitemap.xml` | 58 |
| Sitemap-vs-files mismatch | 0 |
| Pages with valid `<!DOCTYPE html>` | 60 |
| Pages with `<html lang="en">` | 60 |
| Pages with non-empty `<title>` | 60 |
| Pages with meta description | 60 |
| Pages with self-pointing canonical | 57 |
| Pages with intentional homepage canonical (`index.html`, `404.html`, `under-construction.html`) | 3 |
| Pages with `og:url` matching canonical | 60 |
| Pages with `theme-color` = brand rust `#d35b2d` | 60 |
| Pages with SVG favicon link | 60 |
| Pages with manifest link | 60 |
| Pages with `search.js` wired in | 60 |
| Pages with `app.js` wired in | 60 |
| Pages with skip-to-content link | 60 |
| Pages with `<main id="main">` landmark | 60 |
| Pages with parseable JSON-LD | 60 |
| Pages with exactly one `<h1>` | 60 |
| Pages with JSON-LD `BreadcrumbList` | 57 |
| Pages with visible `<nav aria-label="Breadcrumb">` | 57 |
| Pages with JSON-LD `SoftwareApplication` (tool-ettes) | 42 |
| Pages with JSON-LD `CollectionPage` (branch hubs) | 8 |

---

## Page-by-page

| Path | Type | h1 / title key | Canon. OK | JSON-LD | Breadcrumb |
|---|---|---|:-:|:-:|:-:|
| `index.html` | Home | Glee-fully Personalizable Tools™ | self | WebSite + Org | n/a |
| `404.html` | Error | 404 | →home (intentional) | – | – |
| `under-construction.html` | Holding | Under construction | →home (intentional) | – | – |
| `search/index.html` | Search | Search | self | SearchResultsPage | own (pre-existing) |
| `about/index.html` | About | About | self | AboutPage | ✓ |
| `contact/index.html` | Contact | Contact | self | ContactPage | ✓ |
| `legal/index.html` | Legal | Legal | self | WebPage | ✓ |
| `persona/index.html` | Persona | The Voice & Muse | self | WebPage | ✓ |
| `ecosystem/index.html` | Hub | Our Ecosystem | self | CollectionPage | ✓ |
| `universe/index.html` | Hub | OKHP³ Universe | self | WebPage | ✓ |
| `toolbox/index.html` | Hub | Toolbox | self | CollectionPage | ✓ |
| `toolbox/01-discovered-careers/index.html` | Branch | Discovered Careers | self | CollectionPage | ✓ |
| `toolbox/01-discovered-careers/01a-resume-builder/…` | Tool | Resume Builder | self | SoftwareApplication | ✓ |
| `toolbox/01-discovered-careers/01b-resume-customizer/…` | Tool | Resume Customizer | self | SoftwareApplication | ✓ |
| `toolbox/01-discovered-careers/01c-career-fitness/…` | Tool | Career Fitness | self | SoftwareApplication | ✓ |
| `toolbox/01-discovered-careers/01d-letter-composer/…` | Tool | Letter Composer | self | SoftwareApplication | ✓ |
| `toolbox/01-discovered-careers/01e-blinkin-tuner/…` | Tool | bLinkIn Tuner | self | SoftwareApplication | ✓ |
| `toolbox/01-discovered-careers/01f-career-seeker/…` | Tool | Career Seeker | self | SoftwareApplication | ✓ |
| `toolbox/02-treasured-finds/…` (8 pages) | Branch + 7 tools | – | self | CollectionPage / SoftwareApplication | ✓ |
| `toolbox/03-tasty-tracker/…` (6 pages) | Branch + 5 tools | – | self | CollectionPage / SoftwareApplication | ✓ |
| `toolbox/04-travelers-guide/…` (6 pages) | Branch + 5 tools | – | self | CollectionPage / SoftwareApplication | ✓ |
| `toolbox/05-organized-life/…` (7 pages) | Branch + 6 tools | – | self | CollectionPage / SoftwareApplication | ✓ |
| `toolbox/06-healthy-bee-ing/…` (7 pages) | Branch + 6 tools | – | self | CollectionPage / SoftwareApplication | ✓ |
| `toolbox/07-identity-known/…` (8 pages) | Branch + 7 tools | – | self | CollectionPage / SoftwareApplication | ✓ |

> **Full per-page detail (titles, descriptions, links, images, scripts) is in the machine-readable
> `audit/validation-report-2026-05-03.json`.** That is the source of truth — this Markdown is its
> human-readable cover.

---

## Defects fixed in this pass

| Page | Defect | Fix |
|---|---|---|
| `toolbox/02-treasured-finds/02b-decor-detective/index.html` | Missing `<!DOCTYPE html>` and the file opened with `<html lang="en">` directly. Same regression class as `02e-spirited-journal` (caught in 2026-05-02 audit). | Prepended the missing DOCTYPE. Validator will now fail loud if any page regresses. |

---

## Re-running this audit

```bash
python3 scripts/validate-site.py
```

Exit code is `0` when the site is clean, `1` when any page has a critical issue
(missing DOCTYPE / title / canonical / theme-color / favicon / manifest, broken
JSON-LD, or canonical pointing to the homepage from a non-homepage file).

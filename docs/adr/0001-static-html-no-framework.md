# ADR-0001: Static HTML over a Frontend Framework

## Status

Accepted

## Date

2025-01-01

## Context

The Glee-fully Tools site is a public-facing content hub for a suite of Custom GPT tools.
It requires fast load times, excellent SEO, zero build complexity, and the ability to be
deployed directly from a Git repository as a static site (GitHub Pages / Cloudflare Pages).

The team evaluated using React, Vue, or Next.js.

## Decision Drivers

- **Must support direct static hosting** — no server-side rendering environment available
- **Must have excellent SEO** — pages are the primary discovery mechanism for GPTs
- **Should minimize build tooling** — reduce dependency surface and maintenance burden
- **Should be maintainable by scripts** — Python build scripts need to parse and modify pages

## Considered Options

### Option A: Static HTML (chosen)
- **Pros**: Zero build step, direct browser compatibility, trivially cacheable, Python-parseable
- **Cons**: No component reuse at build time, template duplication must be managed by scripts

### Option B: Next.js (static export)
- **Pros**: Component reuse, TypeScript, rich ecosystem
- **Cons**: Node.js build required, adds ~100+ MB of dependencies, complex Python interop

### Option C: Astro
- **Pros**: Component islands, Markdown support
- **Cons**: Node.js build required, relatively new, adds build complexity

## Decision

Use plain HTML pages with a single shared CSS file (`assets/css/theme.css`) and a single
shared JavaScript file (`assets/js/app.js`). Python scripts under `scripts/` handle
templating, injection, and index building at maintenance time.

## Consequences

### Positive
- Zero runtime dependencies — site works as a file tree
- Trivial deployment to any static host
- Python build scripts can parse, validate, and modify pages reliably
- Full browser caching potential with versioned asset URLs

### Negative
- HTML duplication across pages must be managed with scripts, not components
- Changes to shared layout (nav, footer) require running a script across all pages
- No TypeScript or JSX tooling benefits in `assets/js/app.js`

### Mitigations
- Idempotent injection scripts with `<!-- AUTOGEN:<MARKER> -->` guards prevent drift
- `scripts/validate-site.py` and `scripts/check-links.py` catch structural regressions

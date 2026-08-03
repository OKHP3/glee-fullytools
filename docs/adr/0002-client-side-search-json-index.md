# ADR-0002: Client-Side Search with Pre-Built JSON Index

## Status

Accepted

## Date

2025-01-01

## Context

The site has 60+ pages across a seven-branch toolbox structure. Visitors need a way
to find specific tools without navigating every branch. The static hosting constraint
(ADR-0001) rules out server-side search.

## Decision Drivers

- **Must work on static hosting** — no backend available
- **Must be fast** — search results should feel instant
- **Should cover all 60+ pages** — including tool-ette descriptions and headings
- **Should be maintainable** — search index rebuilt by a single script after content changes

## Considered Options

### Option A: Pre-built JSON index + client-side JS (chosen)
- `scripts/build-search-index.py` extracts title, headings, and body text per page
- `assets/data/search-index.json` (~134 KB) loaded once per session
- `assets/js/app.js` provides fuzzy token matching with `escapeHtml()` sanitization

### Option B: Algolia / Typesense hosted search
- **Pros**: Full-text search, typo tolerance, zero client JS
- **Cons**: External service dependency, API key management, ongoing cost, privacy concerns

### Option C: No search
- Not acceptable — 60+ pages require navigation support

## Decision

Pre-built JSON search index loaded client-side. Results are ranked by token frequency.
All user input is passed through `escapeHtml()` before DOM insertion; `highlight()` uses
only hardcoded `<mark>` tags, never raw user content.

## Consequences

### Positive
- Zero external dependencies — works fully offline
- Instant results (no network round-trip after initial load)
- Full control over ranking and snippet extraction

### Negative
- Index must be rebuilt (`python3 scripts/build-search-index.py`) after every content change
- JSON payload (~134 KB) increases initial page weight
- No typo tolerance or fuzzy matching beyond token prefix

### Constraints
- Rebuild search index after any HTML content change
- Do not hand-edit `assets/data/search-index.json`

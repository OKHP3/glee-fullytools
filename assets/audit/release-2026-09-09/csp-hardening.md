# CSP hardening evidence — September 9, 2026

## Scope

The site no longer depends on executable inline JavaScript or inline event
attributes for normal behavior.

- The repeated anti-flash color-scheme bootstrap was moved to the
  render-blocking same-origin asset
  `/assets/js/color-scheme-init.js?v=20260909`.
- The development search template no longer uses an inline `onsubmit`
  handler. Its form has a normal GET fallback, and the shared `app.js`
  runtime prevents submission and renders search results when JavaScript is
  available.
- The repository-wide inventory covers 75 tracked HTML files, including
  development templates. It found zero executable inline script blocks and
  zero inline event-handler attributes.
- JSON-LD and `speculationrules` blocks remain the documented declarative
  inline boundary. They are retained as data, not executable application
  JavaScript.

## Policy result

- Per-page meta CSP policies and the portable `_headers` policy use
  hash-locked `script-src` directives without `unsafe-inline`.
- Every policy retains `script-src-attr 'none'`.
- `style-src 'unsafe-inline'` remains scoped only to the Mermaid page classes,
  because Mermaid creates runtime styles that cannot be represented by
  build-time hashes. This is a style boundary, not a script allowance.
- `scripts/check-csp.py` now checks generated policy drift and rejects
  executable inline markup or event attributes in tracked HTML.

## Validation

The following checks passed after generated CSS/offline fingerprints were
resynchronized:

- `bash scripts/post-merge.sh`
- `python3 scripts/check-csp.py`
- `python3 scripts/validate-site.py` — 65 pages, 0 issues, 0 warnings
- `python3 scripts/check-links.py --no-report` — 0 broken links
- Full static validation workflow regressions, including publication,
  search, offline, service-worker, client behavior, contrast, and branded
  dark-mode checks

GitHub Pages does not consume `_headers`; its delivery remains a separate
hosting decision documented in
[`docs/adr/0004-enforced-csp-headers.md`](../../../docs/adr/0004-enforced-csp-headers.md).
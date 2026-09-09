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

## Live HTTP response evidence

The approved delivery host for this release is **GitHub Pages**, retaining the
current `glee-fully.tools` arrangement (owner choice A in the platform release
decision). No Cloudflare proxy, Cloudflare Pages project, Netlify site, DNS
cutover, or other header-capable delivery path has been approved.

- **Response URL:** `https://glee-fully.tools/`
- **Requests:** GET smoke test, with the existing checker now evaluating the
  actual response rather than reading `_headers`
- **Observed status:** `200 OK`
- **Observed server:** `GitHub.com`
- **Observed response date:** `Wed, 09 Sep 2026 12:10:53 GMT`
- **Observed `Strict-Transport-Security`:** `max-age=31556952`
- **Observed `Content-Security-Policy`:** **missing**
- **Observed `X-Frame-Options`:** **missing**
- **Observed `X-Content-Type-Options`:** **missing**

Because the CSP header is absent, the live `script-src` check cannot establish
that `unsafe-inline` is absent, and the expected `script-src-attr 'none'`,
`frame-src`, `object-src 'none'`, `base-uri`, `form-action`, `manifest-src`,
and `upgrade-insecure-requests` controls are **not delivered**. The smoke test
therefore exits nonzero. This is an honest host-delivery limitation, not a
protection PASS and not evidence that `_headers` was consumed.

**Host-specific exception:** GitHub Pages does not consume repository
`_headers` files or provide arbitrary response-header configuration. The
per-page meta CSP remains active, but HTTP-only controls such as response CSP
and framing headers remain unverified/unavailable until a separately approved
header-capable delivery path is selected.

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

The live response result above is the current delivery evidence. GitHub Pages
does not consume `_headers`; its delivery remains a separate hosting decision
documented in
[`docs/adr/0004-enforced-csp-headers.md`](../../../docs/adr/0004-enforced-csp-headers.md).

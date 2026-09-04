# ADR-0006: Privacy-first third-party boundaries

## Status

Accepted

## Date

2026-09-04

## Context

Glee-fully Tools is a static catalog and routing site with no accounts,
first-party database, or application server. Its previous page markup loaded
Google Analytics on most pages, and the public privacy text did not explain
fonts, embeds, offline caching, or visitor choices. GitHub Pages also does not
consume the repository’s `_headers` file.

## Decision

1. Keep the approved Google Fonts dependency for brand fidelity and the lack of
   a font build pipeline. Document it as a browser-visible third-party request.
2. Make Google Analytics 4 optional and off by default. Load it only after an
   explicit legal-page opt-in, store that choice locally, disable GA4 client
   storage, and turn off Google signals and ad-personalisation signals.
3. Keep the owner’s analytics property retention policy at 14 months or less.
   This is an owner-side configuration requirement, not something static code
   can enforce.
4. Treat Ko-fi as outbound navigation only; do not allow a future widget to
   inherit script or image permissions without a new review.
5. Keep the Arcade preview sandboxed with only scripts, same-origin behavior,
   pointer lock, and autoplay. Provide a direct-link fallback because
   cross-origin iframe failures are not reliably observable.
6. Keep the service worker limited to same-origin GET navigation and shell
   assets. It must not cache third-party responses.
7. Maintain both page-level CSP meta policies and the portable `_headers`
   policy, but describe GitHub Pages header delivery as unavailable until
   observed separately.

## Consequences

### Positive

- Visitors can use the catalog without an analytics request or analytics
  storage.
- The public notice matches the actual request, storage, embed, and caching
  boundaries.
- An unavailable Arcade origin does not strand the visitor without a play link.
- Unused Ko-fi script permissions are removed from CSP.

### Negative

- Aggregate reach reporting is incomplete unless visitors opt in.
- Google Fonts remains a documented third-party request.
- Static code cannot verify or enforce the retention configuration inside the
  Google Analytics property.
- GitHub Pages still does not deliver arbitrary HTTP response headers from
  `_headers`.

## Verification

The current inventory and release checks are maintained in
[`docs/privacy-data-flows.md`](../privacy-data-flows.md). The CSP generator and
page-level checks remain the source of truth for the static policy; the
post-deploy public-header smoke test remains the source of truth for delivered
HTTP headers.
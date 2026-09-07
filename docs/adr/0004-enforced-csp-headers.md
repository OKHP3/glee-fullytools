# ADR-0004: Portable CSP Policy and GitHub Pages Delivery Limits

## Status

Accepted. Hash-based meta CSP is implemented; portable HTTP policy delivery
remains a separate hosting decision. Current-status clarification: 2026-09-05.

## Date

2026-07-20

## Context

The repository needs a repeatable browser security policy for a host that supports
edge-header configuration. The `_headers` file provides that portable policy, but
GitHub Pages does not consume `_headers` files or expose a repository setting for
arbitrary response headers. Therefore, the file cannot by itself enforce CSP on
the current public host.

The public response must be checked separately. The live check on 2026-08-23
observed HSTS from GitHub Pages, but did not observe CSP, X-Frame-Options, or
X-Content-Type-Options.

## Decision Drivers

- **Security**: Report-only CSP provides no XSS protection
- **Feasibility**: The policy is compatible with a host that supports edge headers
- **Honesty**: Configured policy and deployed response headers must remain separate claims

## Decision

Retain an enforcing `Content-Security-Policy` in `_headers` as a portable policy
for a compatible edge host. Do not describe it as active on GitHub Pages.
Add `frame-src 'self' https://okhp3.github.io` to allow the arcade game iframe.
The optional analytics path remains allow-listed because it is dynamically
loaded only after visitor opt-in; Ko-fi is an outbound link and receives no
script or image permission.
Run `scripts/check-public-headers.py` after a Pages deployment and treat its
output as the delivery evidence for the public domain.

Historical portable policy snapshot (2026-07-20, superseded by the generator):
```
default-src 'self';
script-src 'self' 'unsafe-inline' https://www.googletagmanager.com
           https://www.google-analytics.com https://cdn.jsdelivr.net;
style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
font-src 'self' https://fonts.gstatic.com;
img-src 'self' data:;
connect-src 'self' https://www.google-analytics.com https://www.googletagmanager.com
            https://cdn.jsdelivr.net;
frame-src 'self' https://okhp3.github.io;
frame-ancestors 'self';
base-uri 'self';
form-action 'self';
object-src 'none';
manifest-src 'self';
upgrade-insecure-requests
```

## Consequences

### Positive
- A compatible edge host can enforce the reviewed policy
- `object-src 'none'` blocks Flash/plugin vectors entirely
- `upgrade-insecure-requests` forces HTTPS for all sub-resources

### Current implementation and remaining limits
- `scripts/csp.py` generates per-page meta policies and the portable `_headers`
  policy. `scripts/check-csp.py` verifies them. Current script policies use
  approved content hashes and do not require `unsafe-inline` or server rendering.
- Analytics initialization is external and remains opt-in. Vendored Mermaid
  runs from the same origin. Review the generator before adding external origins.
- GitHub Pages does not consume `_headers`. Meta CSP remains active, while
  `frame-ancestors` and other HTTP-only controls need separately verified delivery.

### Future hardening
- Consider HTTP policy delivery only through an owner-approved hosting decision.
- A violation-reporting endpoint remains a proposal; none is introduced here.
- The concrete retain-Pages, proxy, and alternate-static-host choices and their
  required owner decisions are recorded in
  [the September 5 platform handoff](../remaining-program-2026-09-05/platform-release.md#host-header-decision).
  Before applying `_headers` to a new host, review its immutable-cache rules,
  combined HTTP/meta CSP behavior, embedding policy, and HSTS subdomain coverage.

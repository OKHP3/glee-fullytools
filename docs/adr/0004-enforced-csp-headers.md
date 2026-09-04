# ADR-0004: Portable CSP Policy and GitHub Pages Delivery Limits

## Status

Accepted — policy retained; GitHub Pages delivery not demonstrated

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

Final enforced policy:
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

### Negative
- GitHub Pages currently does not deliver this policy, so its public site does not
  receive these controls from `_headers`
- `unsafe-inline` for scripts is required for gtag config blocks; a nonce-based approach
  would be more secure but requires server-side rendering to inject nonces dynamically
- Any new CDN origin requires a `_headers` update before it will load in production

### Future hardening
- Replace `unsafe-inline` with a nonce or hash-based approach if/when the site gains
  server-side rendering capability
- Add `report-uri` or `report-to` endpoint for violation telemetry

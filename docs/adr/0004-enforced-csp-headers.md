# ADR-0004: Enforced CSP via _headers File

## Status

Accepted

## Date

2026-07-20

## Context

The site previously had a `Content-Security-Policy-Report-Only` header — the policy was
declared but not enforced. Any XSS vulnerability would have been logged but not blocked.
As part of a security audit, all `innerHTML` usage in `assets/js/app.js` was verified to
pass through `escapeHtml()` before DOM insertion, making enforcement safe.

## Decision Drivers

- **Security**: Report-only CSP provides no XSS protection
- **Feasibility**: All `innerHTML` paths verified safe via audit on 2026-07-20
- **Completeness**: The `_headers` file supports Cloudflare Pages and Netlify edge headers

## Decision

Upgrade `Content-Security-Policy-Report-Only` to `Content-Security-Policy` in `_headers`.
Add `frame-src 'self' https://okhp3.github.io` to allow the arcade game iframe.

Final enforced policy:
```
default-src 'self';
script-src 'self' 'unsafe-inline' https://www.googletagmanager.com
           https://www.google-analytics.com https://cdn.jsdelivr.net;
style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
font-src 'self' https://fonts.gstatic.com;
img-src 'self' data: https://www.google-analytics.com https://storage.ko-fi.com;
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
- XSS attacks are blocked at the browser, not just logged
- `object-src 'none'` blocks Flash/plugin vectors entirely
- `upgrade-insecure-requests` forces HTTPS for all sub-resources

### Negative
- `unsafe-inline` for scripts is required for gtag config blocks; a nonce-based approach
  would be more secure but requires server-side rendering to inject nonces dynamically
- Any new CDN origin requires a `_headers` update before it will load in production

### Future hardening
- Replace `unsafe-inline` with a nonce or hash-based approach if/when the site gains
  server-side rendering capability
- Add `report-uri` or `report-to` endpoint for violation telemetry

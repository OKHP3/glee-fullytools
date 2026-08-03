# ADR-0003: CDN-Loaded Third-Party Resources

## Status

Accepted

## Date

2025-01-01

## Context

The site uses Google Fonts (Fredoka, Open Sans, Kalam, and others), Google Analytics 4
(GA4 via gtag), and Mermaid for two diagram pages. These could be self-hosted or CDN-loaded.

## Decision Drivers

- **Google Fonts**: Typography is critical to brand; self-hosting requires a font pipeline
- **GA4**: Measurement is required; the GA4 script must come from Google's CDN
- **Mermaid**: ESM-only v11; self-hosting adds build complexity for a rare feature (2 pages)
- **Performance**: `<link rel="preconnect">` hints reduce latency for CDN origins

## Considered Options

### Option A: CDN for all three (chosen)
- Google Fonts via `fonts.googleapis.com` + `fonts.gstatic.com`
- GA4 via `googletagmanager.com`
- Mermaid via `cdn.jsdelivr.net/npm/mermaid@<version>/dist/mermaid.esm.min.mjs`

### Option B: Self-host fonts
- **Pros**: No third-party DNS lookup, GDPR-cleaner
- **Cons**: Font pipeline to maintain, WOFF2 subset generation, cache headers to manage

### Option C: Remove Mermaid
- Not acceptable — ecosystem and universe pages use live diagrams

## Decision

Use CDN for all three. Add `<link rel="preconnect">` hints for all CDN origins.
Pin Mermaid to an exact version (`@11.16.0`) in `assets/js/mermaid-init.js` to prevent
silent upstream changes. Monitor the npm registry for new Mermaid releases.

## Consequences

### Positive
- Zero font pipeline to maintain
- GA4 always current from Google's CDN
- Mermaid ESM works natively without a bundler

### Negative
- Third-party DNS lookups add latency (mitigated by `preconnect`)
- Google Fonts sends a small cookie-like identifier (GDPR consideration; noted in privacy policy)
- If jsDelivr is unavailable, Mermaid diagrams on two pages will not render

### Security mitigations
- Mermaid: pinned to exact semver to prevent unexpected upstream changes
- GA4: allowed in CSP `script-src`; `unsafe-inline` is required for gtag config blocks
- CSP enforces `connect-src` to only the four necessary CDN origins

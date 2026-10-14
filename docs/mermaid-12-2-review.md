# Mermaid 12.2.0 runtime review

This intentional update resolves the older vendored runtime tracked in issue #66. The npm package is pinned to 12.2.0 and its SHA-512 integrity was verified before copying the minified ESM entry and matching chunks. The upstream MIT license is retained. Source maps are excluded from the public runtime.

Reviewed upstream release notes for 12.1.0 and 12.2.0 at https://github.com/mermaid-js/mermaid/releases. This update retains the existing initializer configuration, security-level choice, click-target filtering, YAML theme settings, and referral credits. Both entry imports now include its exact version so a previously cached entry cannot request removed older chunks. The initializer and universe-map references are regenerated with the repository cache-version script.

Validation: 65 HTML pages, zero issues or warnings; 3047 internal links with zero broken links and 62 sitemap URLs. Actual universe rendering passed in Chromium, Firefox, and WebKit at 390px/light and 1440px/dark, covering nine diagrams and all 62 indexed pages. Existing no-JavaScript and blocked-vendor fallbacks also passed. Ecosystem rendering passed the same six engine/viewport/theme combinations, with all eight diagrams rendered and no page errors. Loopback WebKit fixtures remove only upgrade-insecure-requests from the served response; committed production CSP is preserved.

These are automated rendering checks, not owner visual acceptance or external GPT certification. Windows runner work remains unverified; the change was prepared in an isolated checkout without editing the shared Mac or Replit checkout.

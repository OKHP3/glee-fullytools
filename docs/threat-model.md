# Threat Model

## Project Overview

This project is a static marketing and navigation website for Glee‑fully Personalizable Tools™, a catalog of custom GPT links arranged in a trunk → branch → tool hierarchy. Production consists of browser-rendered HTML, CSS, and vanilla JavaScript with no application server, database, authentication system, or user account layer in this repo. Public pages load local runtime code from `assets/js/app.js`, optionally load the vendored Mermaid bundle on diagram pages, retain Google Fonts for brand typography, and offer opt-in Google Analytics plus one externally hosted game iframe on `/arcade/`.

Per deployment assumptions, scans should focus on production-reachable browser code and ignore development-only tooling unless production reachability is demonstrated. Because this is a static site, the main security questions are client-side code injection, trust in third-party resources, framing/embed behavior, and accidental exposure of sensitive content in published assets.

## Assets

- **Site integrity and visitor trust** — the most important asset is the correctness of published pages and client-side behavior. If an attacker can inject script into the site, they can redirect visitors, alter outbound GPT links, or abuse the brand.
- **Outbound navigation targets** — the site’s value comes from sending users to intended ChatGPT tools, contact pages, and related properties. Tampering with links or embedded content would directly affect users.
- **Analytics and publisher integrations** — opt-in Google Analytics runs in the browser, while Ko-fi is outbound navigation only. Analytics configuration is not highly secret, but compromise of its script supply chain would execute in a trusted page context after consent.
- **Published content inventory** — `assets/data/search-index.json`, metadata, sitemap, and visible page copy represent the site’s public content corpus. They are not confidential, but integrity matters because they are consumed by runtime search and crawlers.
- **Security policy configuration** — `_headers` is a portable edge-host policy; it is not evidence of headers delivered by GitHub Pages.

## Trust Boundaries

- **Browser to static origin** — all visitors load untrusted content from the public internet into their browser. Every query parameter, URL fragment, and localStorage value must be treated as attacker-controlled input.
- **Local site code to third-party origins** — the site retains Google Fonts, can load Google Analytics only after opt-in, and embeds a game from `okhp3.github.io`. Ko-fi and external GPT links are navigations, not widgets. These resources are outside the repo’s direct control.
- **Published content to runtime search rendering** — `scripts/build-search-index.py` converts repo HTML into `assets/data/search-index.json`, and `assets/js/app.js` renders search results into the DOM. Any unsafe treatment of query strings or indexed text would create a client-side injection path.
- **Production vs development tooling** — `scripts/`, `.agents/`, `.local/`, `node_modules/`, `.pythonlibs/`, and `assets/templates/` are development artifacts and should normally be excluded from vulnerability reporting unless a production page or deployment process exposes them.

## Scan Anchors

- **Production entry points** — root HTML pages (`index.html`, `404.html`, `under-construction.html`) and directory pages such as `about/`, `contact/`, `legal/`, `persona/`, `search/`, `showcase/`, `ecosystem/`, `universe/`, `arcade/`, and `toolbox/**/index.html`.
- **Highest-risk production code** — `assets/js/app.js` for query handling and DOM sinks; `assets/js/mermaid-init.js` for third-party rendering configuration; `_headers` for a portable framing/CSP policy; `arcade/index.html` for the external iframe.
- **Public vs authenticated vs admin surfaces** — all production surfaces in this repo are public; there are no authenticated or admin-only routes in scope.
- **Usually dev-only areas to ignore** — `scripts/`, `.agents/`, `.local/`, `node_modules/`, `.pythonlibs/`, and `assets/templates/`.

## Threat Categories

## Privacy and storage boundaries

Analytics is off by default and is dynamically loaded only after a visitor
chooses the opt-in control on the legal page. The tag is configured without
Google signals, ad-personalisation signals, or GA4 client-side storage. The
owner policy is to keep the analytics property retention at 14 months or less;
static code cannot verify that Google-side setting.

The site’s local storage contains interface preferences, per-page
work-in-progress dismissals, and the analytics choice. The service worker
caches only same-origin GET shell resources and navigations. It does not cache
third-party responses. The Arcade child retains any game state in its own
origin and is sandboxed from the parent DOM.

## Deployed versus intended controls

The current public host is GitHub Pages. GitHub Pages serves the site over
HTTPS and currently supplies HSTS, but it does not consume the repository's
`_headers` file. As a result, CSP, X-Frame-Options, X-Content-Type-Options,
Permissions-Policy, COOP, CORP, and related policy lines in `_headers` are
**intended/configured controls**, not **observed/deployed controls**, until a
compatible edge layer is authorized and verified.

The Pages workflow runs `scripts/check-public-headers.py` after deployment.
That smoke test is deliberately non-blocking because the known host limitation
would otherwise turn a documented finding into a false release failure. A
missing-header result remains a release finding for the owner to review; the
workflow never converts it into a claim that the header is active.

### Tampering

The meaningful tampering risk in this project is client-side content or navigation tampering. Query parameters, localStorage values, and generated search-index content must never be allowed to inject executable HTML into page sinks. Runtime code must continue to use safe DOM APIs or robust escaping before assigning strings to `innerHTML`, and outbound links shown to users must resolve to intended destinations.

Because the site delegates some behavior to third-party scripts and an embedded external game, production must also assume those origins are separate trust domains. Embedded or imported content must not be given broader privileges than necessary.

### Information Disclosure

There is little private data in this repo, but the site must not accidentally publish secrets, tokens, internal-only documents, or sensitive deployment details in HTML, JSON, or static assets. Search indexing and metadata generation must only expose intended public content. Browser-visible errors and diagnostics must avoid leaking internal filesystem or tooling details if future runtime code expands.

### Spoofing

There is no user login flow here, so classic account spoofing does not apply. The relevant spoofing concern is origin and brand impersonation through compromised third-party resources, modified outbound links, or malicious framed/embedded content that appears to be first-party. The site must preserve clear first-party navigation and avoid granting external content unnecessary ability to mimic or replace trusted UI.

### Denial of Service

The static architecture substantially reduces backend DoS risk, but client-side features can still be abused if they perform expensive work on attacker-controlled input. Search tokenization, highlighting, and any dynamic regex use must remain bounded so a crafted query cannot freeze the browser tab or degrade the experience for normal visitors.

### Elevation of Privilege

Traditional privilege escalation is mostly not applicable because the repo exposes no authenticated roles or privileged server operations. The relevant equivalent is script execution in the site’s origin: any DOM XSS, unsafe third-party script execution, or overly permissive embed behavior would let an attacker act with the full privilege level of the published site in a visitor’s browser. Preventing arbitrary script execution is therefore the central security guarantee for this project.
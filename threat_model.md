# Threat Model

## Project Overview

This project is a static marketing and navigation website for Glee‑fully Personalizable Tools™, a catalog of custom GPT links arranged in a trunk → branch → tool hierarchy. Production consists of browser-rendered HTML, CSS, and vanilla JavaScript with no application server, database, authentication system, or user account layer in this repo. Public pages load local runtime code from `assets/js/app.js`, optionally load `assets/js/mermaid-init.js` on diagram pages, and trust several external services including Google Analytics, Google Fonts, Ko-fi, Mermaid CDN assets, and one externally hosted game iframe on `/arcade/`.

Per deployment assumptions, scans should focus on production-reachable browser code and ignore development-only tooling unless production reachability is demonstrated. Because this is a static site, the main security questions are client-side code injection, trust in third-party resources, framing/embed behavior, and accidental exposure of sensitive content in published assets.

## Assets

- **Site integrity and visitor trust** — the most important asset is the correctness of published pages and client-side behavior. If an attacker can inject script into the site, they can redirect visitors, alter outbound GPT links, or abuse the brand.
- **Outbound navigation targets** — the site’s value comes from sending users to intended ChatGPT tools, contact pages, and related properties. Tampering with links or embedded content would directly affect users.
- **Analytics and publisher integrations** — Google Analytics and Ko-fi are third-party integrations that run in the browser. Their configuration is not highly secret, but compromise of those script supply chains would execute in a trusted page context.
- **Published content inventory** — `assets/data/search-index.json`, metadata, sitemap, and visible page copy represent the site’s public content corpus. They are not confidential, but integrity matters because they are consumed by runtime search and crawlers.
- **Security policy configuration** — `_headers` governs framing and browser security behavior when honored by the deployment platform.

## Trust Boundaries

- **Browser to static origin** — all visitors load untrusted content from the public internet into their browser. Every query parameter, URL fragment, and localStorage value must be treated as attacker-controlled input.
- **Local site code to third-party origins** — the site loads scripts, fonts, and widgets from Google, Ko-fi, and jsDelivr, and embeds a game from `okhp3.github.io`. These resources are outside the repo’s direct control.
- **Published content to runtime search rendering** — `scripts/build-search-index.py` converts repo HTML into `assets/data/search-index.json`, and `assets/js/app.js` renders search results into the DOM. Any unsafe treatment of query strings or indexed text would create a client-side injection path.
- **Production vs development tooling** — `scripts/`, `.agents/`, `.local/`, `node_modules/`, `.pythonlibs/`, and `assets/templates/` are development artifacts and should normally be excluded from vulnerability reporting unless a production page or deployment process exposes them.

## Scan Anchors

- **Production entry points** — root HTML pages (`index.html`, `404.html`, `under-construction.html`) and directory pages such as `about/`, `contact/`, `legal/`, `persona/`, `search/`, `showcase/`, `ecosystem/`, `universe/`, `arcade/`, and `toolbox/**/index.html`.
- **Highest-risk production code** — `assets/js/app.js` for query handling and DOM sinks; `assets/js/mermaid-init.js` for third-party rendering configuration; `_headers` for framing/CSP behavior; `arcade/index.html` for the external iframe.
- **Public vs authenticated vs admin surfaces** — all production surfaces in this repo are public; there are no authenticated or admin-only routes in scope.
- **Usually dev-only areas to ignore** — `scripts/`, `.agents/`, `.local/`, `node_modules/`, `.pythonlibs/`, and `assets/templates/`.

## Threat Categories

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
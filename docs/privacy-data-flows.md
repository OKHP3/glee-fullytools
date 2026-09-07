# Privacy and third-party data-flow inventory

**Reviewed:** 2026-09-04  
**Scope:** browser-visible behavior in the GitHub Pages artifact for
`glee-fully.tools`

This is an engineering inventory, not legal advice or a certification of
compliance. It describes what this repository intentionally requests, stores,
and delegates. The privacy notice in [`/legal/`](../legal/) is the public
plain-language version.

## Owner policy

The owner has chosen the following operating posture:

1. **Analytics is optional, not necessary for the site to work.** Google
   Analytics 4 is off by default and is loaded only after a visitor selects
   “Turn analytics on” on the legal page. The choice can be withdrawn there.
2. **Measurement is limited.** The tag is configured without Google signals,
   ad-personalization signals, or GA4 client-side storage. The site does not
   send tool prompts, game state, account data, or form contents to analytics.
3. **Retention is bounded.** The owner’s policy is to keep any opted-in
   analytics property retention at 14 months or less and review that property
   setting at least annually. This repository cannot enforce a setting inside
   Google Analytics.
4. **Audience assumption.** The site is general-audience informational
   content and is not knowingly directed to children. Visitors and the owner
   must still consider the law and platform terms that apply to them.
5. **Third parties remain separate controllers or operators.** The owner
   controls the links and embed boundary described below, not the privacy
   practices of Google, GitHub, Ko-fi, email providers, ChatGPT, or the
   externally hosted game.

## Browser request inventory

| Flow | When it occurs | Data boundary and controls |
|---|---|---|
| **GitHub Pages / custom domain** | Every page and same-origin asset | The static origin serves HTML, CSS, JavaScript, images, JSON, and the offline shell. GitHub Pages may process operational request data under GitHub’s own policies; this site has no server-side application, account layer, or first-party database. |
| **Google Fonts** | Most public pages request the approved Fredoka, Open Sans, Poppins, and DM Sans stylesheet and font files | Retained for the approved brand typography because this static repository has no font build pipeline. The request is a Google boundary and may expose ordinary request metadata such as IP address and browser details. It is not used for personalization. |
| **Google Analytics 4** | Only after the visitor grants the browser-local opt-in | The tag is dynamically loaded from `googletagmanager.com` and sends aggregate page measurement to Google. It is not loaded by page markup and is disabled by default. GA4 is configured with `client_storage: "none"`, `allow_google_signals: false`, and `allow_ad_personalization_signals: false`. |
| **Ko-fi** | Only when a visitor clicks a support link | Ko-fi is an outbound navigation boundary. No Ko-fi iframe, image, or script is embedded in this site. Ko-fi receives the request after navigation under its own policies. |
| **External GPT platforms** | Only when a visitor follows a Tool or Tool-ette link | The destination platform receives and processes the visitor’s interaction. The site does not proxy prompts or responses and cannot control that platform’s retention, training, or account settings. |
| **Arcade iframe** | Only on `/arcade/`, when the preview is loaded | The iframe is `https://okhp3.github.io/glee-fully-chai-chasers/` with `sandbox="allow-scripts allow-same-origin allow-pointer-lock"`, `allow="autoplay"`, and a strict cross-origin referrer policy. The child can run its game and keep its own same-origin progress, but cannot access the parent DOM. A direct-link fallback is shown if loading fails or takes too long. |
| **Email contact** | Only when a visitor activates a `mailto:` link and sends mail | The visitor chooses the contents. The mail application, email provider, and studio receive it. The site has no contact form or automatic deletion workflow. Correspondence may be retained for responding, support, or studio records. |

## Browser storage and offline boundary

- The shared site stores only user-interface choices and dismissals in
  `localStorage`: theme/color-scheme preferences and per-page
  work-in-progress overlay dismissals. These values stay in the visitor’s
  browser and are not sent to this site.
- The analytics choice is stored as `glee-analytics-consent` with `granted` or
  `denied`. It is a first-party preference used to decide whether the optional
  tag may load.
- The Arcade application stores game progress in its own iframe origin. The
  parent site cannot read that storage. The game’s own documentation and
  platform boundary govern it.
- `sw.js` caches an intentional, same-origin list of public navigation pages
  and site assets. It ignores non-GET requests and cross-origin requests, so it
  does not cache Google, Ko-fi, GPT, or Arcade responses. A cached page can
  still contain the local opt-in control; analytics remains governed by the
  browser’s stored choice when the page is opened offline or online.

## Policy and deployment evidence

- Every published HTML page carries a page-level CSP `<meta>` policy generated
  from `config/csp-policies.json`. It allows only the optional analytics
  origins, Google Fonts, and the Arcade frame where the page class needs them.
- `_headers` is a portable policy for an edge host that supports it. GitHub
  Pages does **not** consume that file, so it is not evidence that the public
  response contains CSP, framing, MIME, or permissions headers.
- The Pages workflow’s public-header smoke test reports the distinction; a
  missing header is a known host finding, not a passed control.

## Open owner checks

Before enabling analytics for a release, confirm the Google Analytics property
retention setting is 14 months or less and that advertising features remain
disabled. If that cannot be confirmed, leave the site’s analytics property
unused; the static site remains fully functional with analytics off.

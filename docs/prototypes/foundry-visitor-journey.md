# FoundRy visitor journey prototype

Status: prototype only. Not a production page, not indexed, and not deployed.

## Purpose

This prototype explores a clearer visitor route for the existing FoundRy feature-page story:

1. Meet the locally run workbench.
2. Follow the public-source and local-setup path.
3. Understand the describe, try, and review rhythm.
4. Return explicitly to the public Toolbox.

The concept uses the existing Glee-fully site shell, shared stylesheet, typography, layout classes, buttons, card treatment, and brand tokens. It adds no production CSS, JavaScript, dependencies, generated output, or public route.

## Source-backed boundaries

- The existing `foundry/index.html` describes FoundRy as a locally run workbench with public source.
- The existing page links to `https://github.com/OKHP3/Glee-fullyTools-FoundRy` for the application and local setup guide.
- The existing page states that there is no hosted builder, account sign-up, or embedded application on the feature page.
- The existing page and `docs/suite-promise.md` keep the public Toolbox as the catalog and publication-state surface.

## Review notes

- The prototype is deliberately labeled in the visible banner and footer.
- The primary route is keyboard-linear: skip link, header navigation, hero actions, section content, return CTAs, and footer.
- Internal links are relative to the prototype location so the page can be served from the repository root without changing production URLs.
- The external source link opens in a new tab with `noopener noreferrer`.
- Desktop and narrow-viewport rendering should be checked through a local loopback server when an installed browser runner is available.

## Non-goals

- Do not add this page to the sitemap or search index.
- Do not alter `foundry/index.html`, `assets/css/theme.css`, generated files, or deployment configuration.
- Do not imply that the local workbench is hosted, certified, or ready for publication.

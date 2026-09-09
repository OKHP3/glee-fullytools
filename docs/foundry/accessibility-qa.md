# FoundRy accessibility QA

## Scope

Focused browser coverage for `foundry/index.html`: page landmarks and heading structure, visible CTA names, keyboard operation of the FAQ disclosures, focus visibility, and horizontal overflow at 320px and 390px widths. This is not a replacement for the site's full validation or viewport suites.

## Evidence

- Source SHA: generated at run time by the runner
- Runner: [`scripts/tests/foundry-accessibility-qa.mjs`](../../scripts/tests/foundry-accessibility-qa.mjs)
- Fixture: loopback HTTP server on an ephemeral port, with third-party requests and service workers blocked. The production HTML is not rewritten on disk.
- Supported command: `npm ci && npx playwright install chromium && npm run qa:foundry-accessibility`
- Optional report output: append `-- --output path/to/foundry-accessibility.json` to
  write the same JSON evidence that is printed to stdout. The Pages workflow uses
  the deterministic path `assets/audit/foundry-accessibility.json` and uploads it
  as a CI artifact after the focused gate completes, whether that gate passes or
  fails.
- Dependency boundary: this focused runner uses the exact-pinned Node
  `playwright` dev dependency and its Chromium driver. It is separate from the
  exact-pinned Python Playwright dependency used by the broader browser gates;
  neither runner weakens or replaces the other.
- CI command: GitHub Pages CI uses Node 22.19.0 from `.node-version`, runs
  `npm ci`, installs Node Chromium with `--with-deps`, and executes the same
  npm script. A missing Node package or browser is a failed setup, not a
  passing or skipped assertion.
- Human screen-reader testing: **NOT RUN**.

The JSON report includes both narrow viewport definitions, runtime status,
`summary` counts for PASS/FAIL/NOT RUN checks, and the explicit human
screen-reader limitation.

## Coverage implemented

The runner asserts:

1. The intended page title, one `h1`, and `header`, `main`, `nav`, and `footer` landmarks.
2. Heading levels do not skip forward by more than one level.
3. The four visible `.hero-actions` links have non-empty, expected accessible names.
4. A FAQ `summary` receives focus, opens with Enter, and closes with Space.
5. At both narrow viewports, the mobile navigation opens with Enter, clears its
   collapsed `inert` state, and each primary and submenu link is reached by
   keyboard Tab navigation with a visible focus indicator.
6. Every keyboard-reachable link, button, and FAQ summary exposes a non-zero
   visible focus indicator. Controls in unavailable regions—such as the
   intentionally collapsed, `inert` mobile navigation or a closed dialog—are
   reported as excluded rather than treated as reachable controls.
7. The document does not exceed the viewport width at 320px or 390px, and no page errors occur.

## Findings and limitations

The automated check does not prove screen-reader semantics, announcements,
real screen-reader navigation, or human zoom/usability behavior. Human
screen-reader testing therefore remains explicitly **NOT RUN** and is not
silently represented by the browser assertions.

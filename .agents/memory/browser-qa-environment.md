---
name: Browser QA environment
description: Non-obvious setup required for Playwright Chromium browser evidence in this Nix-based workspace
---

Playwright’s bundled Chromium may fail to start here because `libgbm.so.1` is
absent from the standard runtime path. The existing viewport-QA setup compiles
the harmless headless stub and sets the library path; browser-based scripts
should invoke that setup before importing Playwright.

**Why:** Importing Playwright before the environment setup can capture the
incomplete runtime environment, producing a misleading “browser closed” error
even though the shared setup succeeds.

**How to apply:** Reuse the viewport runner’s setup in browser QA scripts, and
keep the real screen-reader limitation separate from accessibility-tree
observations.

The Chromium helper only supplies the local `libgbm.so.1` workaround. Firefox
and WebKit also require their Playwright system dependencies; the full matrix
is expected to run in CI after `playwright install --with-deps chromium firefox
webkit`. In this Nix workspace those engines may be present but not launchable.

**Why:** A local full-matrix failure can be a missing host-library condition,
not a browser assertion or site regression.

**How to apply:** Keep the runner’s missing-engine error explicit, use
`--static-only` only for fast local checks, and rely on the CI job for the
three-engine release evidence.
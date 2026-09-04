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
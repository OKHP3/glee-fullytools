#!/usr/bin/env python3
"""
sparkle-qa.py — Sparkle banner smoke test
==========================================
Verifies that the sparkle loader in assets/js/app.js (section 6) correctly
fetches /assets/data/sparkle.json and rewrites every [data-sparkle-link]
element's href and visible text at runtime.

Checks ≥3 representative page types:
  • homepage        /
  • branch hub      /toolbox/01-discovered-careers/
  • tool-ette leaf  /toolbox/01-discovered-careers/01a-resume-builder/

Exit codes:
  0  all assertions passed
  1  one or more assertions failed (or Playwright error)

Usage:
    python3 scripts/sparkle-qa.py
    python3 scripts/sparkle-qa.py --base-url http://localhost:5000
"""
import os
import sys
import json
import argparse
import time
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent
STUB_DIR = "/tmp/stublibs"
STUB_LIB = os.path.join(STUB_DIR, "libgbm.so.1")

STUB_SRC = r"""
/* Minimal libgbm.so.1 stub — returns null/zero for all calls. */
#include <stddef.h>
#include <stdint.h>
typedef struct gbm_device  gbm_device;
typedef struct gbm_bo      gbm_bo;
typedef struct gbm_surface gbm_surface;
union gbm_bo_handle { void *ptr; int32_t s32; uint32_t u32; int64_t s64; uint64_t u64; };
gbm_device*  gbm_create_device(int fd)                          { return NULL; }
void         gbm_device_destroy(gbm_device *g)                  {}
int          gbm_device_get_fd(gbm_device *g)                   { return -1; }
const char*  gbm_device_get_backend_name(gbm_device *g)         { return "stub"; }
int          gbm_device_is_format_supported(gbm_device *g, uint32_t f, uint32_t u) { return 0; }
int          gbm_device_get_format_modifier_plane_count(gbm_device *g, uint32_t f, uint64_t m) { return 0; }
gbm_bo*      gbm_bo_create(gbm_device *g, uint32_t w, uint32_t h, uint32_t f, uint32_t fl) { return NULL; }
gbm_bo*      gbm_bo_create_with_modifiers(gbm_device *g, uint32_t w, uint32_t h, uint32_t f, const uint64_t *m, unsigned c) { return NULL; }
gbm_bo*      gbm_bo_create_with_modifiers2(gbm_device *g, uint32_t w, uint32_t h, uint32_t f, const uint64_t *m, unsigned c, uint32_t fl) { return NULL; }
gbm_bo*      gbm_bo_import(gbm_device *g, uint32_t t, void *b, uint32_t fl) { return NULL; }
void         gbm_bo_destroy(gbm_bo *b)                          {}
uint32_t     gbm_bo_get_width(gbm_bo *b)                        { return 0; }
uint32_t     gbm_bo_get_height(gbm_bo *b)                       { return 0; }
uint32_t     gbm_bo_get_stride(gbm_bo *b)                       { return 0; }
uint32_t     gbm_bo_get_stride_for_plane(gbm_bo *b, int p)      { return 0; }
uint32_t     gbm_bo_get_format(gbm_bo *b)                       { return 0; }
uint64_t     gbm_bo_get_modifier(gbm_bo *b)                     { return 0; }
int          gbm_bo_get_plane_count(gbm_bo *b)                  { return 0; }
union gbm_bo_handle gbm_bo_get_handle(gbm_bo *b)               { union gbm_bo_handle h; h.u64=0; return h; }
union gbm_bo_handle gbm_bo_get_handle_for_plane(gbm_bo *b, int p) { union gbm_bo_handle h; h.u64=0; return h; }
int          gbm_bo_get_fd(gbm_bo *b)                           { return -1; }
int          gbm_bo_get_fd_for_plane(gbm_bo *b, int p)          { return -1; }
int          gbm_bo_get_offset(gbm_bo *b, int p)                { return 0; }
gbm_device*  gbm_bo_get_device(gbm_bo *b)                       { return NULL; }
void*        gbm_bo_map(gbm_bo *b, uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint32_t fl, uint32_t *st, void **md) { return NULL; }
void         gbm_bo_unmap(gbm_bo *b, void *md)                  {}
int          gbm_bo_set_user_data(gbm_bo *b, void *d, void(*fn)(gbm_bo*,void*)) { return 0; }
void*        gbm_bo_get_user_data(gbm_bo *b)                    { return NULL; }
gbm_surface* gbm_surface_create(gbm_device *g, uint32_t w, uint32_t h, uint32_t f, uint32_t fl) { return NULL; }
gbm_surface* gbm_surface_create_with_modifiers(gbm_device *g, uint32_t w, uint32_t h, uint32_t f, const uint64_t *m, unsigned c) { return NULL; }
gbm_surface* gbm_surface_create_with_modifiers2(gbm_device *g, uint32_t w, uint32_t h, uint32_t f, const uint64_t *m, unsigned c, uint32_t fl) { return NULL; }
gbm_bo*      gbm_surface_lock_front_buffer(gbm_surface *s)      { return NULL; }
void         gbm_surface_release_buffer(gbm_surface *s, gbm_bo *b) {}
int          gbm_surface_has_free_buffers(gbm_surface *s)       { return 0; }
void         gbm_surface_destroy(gbm_surface *s)                {}
"""

LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-software-rasterizer",
    "--disable-dbus",
    "--disable-infobars",
    "--disable-extensions",
    "--disable-translate",
    "--disable-sync",
    "--disable-background-networking",
    "--metrics-recording-only",
    "--no-first-run",
    "--safebrowsing-disable-auto-update",
    "--mute-audio",
]

# Three representative page types required by the task spec.
TEST_PAGES = [
    ("homepage",    "/"),
    ("branch-hub",  "/toolbox/01-discovered-careers/"),
    ("tool-ette",   "/toolbox/01-discovered-careers/01a-resume-builder/"),
]


def ensure_stub():
    """Compile the libgbm stub if not already present (same approach as run-viewport-qa.py)."""
    Path(STUB_DIR).mkdir(parents=True, exist_ok=True)
    if not Path(STUB_LIB).exists():
        src = Path("/tmp/libgbm_sparkle_stub.c")
        src.write_text(STUB_SRC)
        ret = os.system(
            f"gcc -shared -fPIC -Wl,-soname,libgbm.so.1 -o {STUB_LIB} {src} 2>/dev/null"
        )
        if ret != 0:
            print("ERROR: failed to compile libgbm stub. Install gcc first.", file=sys.stderr)
            sys.exit(1)
        print(f"  compiled libgbm stub → {STUB_LIB}")
    existing = os.environ.get("LD_LIBRARY_PATH", "")
    if STUB_DIR not in existing:
        os.environ["LD_LIBRARY_PATH"] = f"{STUB_DIR}:{existing}" if existing else STUB_DIR
    os.environ["PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS"] = "1"


def load_sparkle_json():
    """Read the source-of-truth sparkle.json from disk."""
    path = ROOT / "assets" / "data" / "sparkle.json"
    if not path.exists():
        print(f"ERROR: sparkle.json not found at {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def run_sparkle_qa(base_url: str) -> int:
    """
    Open each TEST_PAGE in a real Chromium context (network-serving the local
    dev server) and assert:

      1. [data-sparkle-link] element is present in the DOM.
      2. After JS executes, its href matches sparkle.json → url.
      3. Its visible text includes sparkle.json → label.

    Returns 0 on full pass, 1 on any failure.
    """
    from playwright.sync_api import sync_playwright

    sparkle = load_sparkle_json()
    expected_url   = sparkle.get("url", "").rstrip("/")
    expected_label = sparkle.get("label", "")

    if not expected_url:
        print("ERROR: sparkle.json has no 'url' field.", file=sys.stderr)
        return 1
    if not expected_label:
        print("ERROR: sparkle.json has no 'label' field.", file=sys.stderr)
        return 1

    print(f"sparkle.json  url   : {expected_url}")
    print(f"sparkle.json  label : {expected_label}")
    print()

    failures  = 0
    passed    = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=LAUNCH_ARGS)

        for slug, path in TEST_PAGES:
            url = base_url.rstrip("/") + path
            ctx  = browser.new_context(
                viewport={"width": 1280, "height": 800},
                device_scale_factor=1,
            )
            page = ctx.new_page()

            try:
                resp = page.goto(url, wait_until="networkidle", timeout=20000)
                # Give the async sparkle fetch a moment to settle even if
                # networkidle already fired (race: fetch starts after DOMContentLoaded).
                time.sleep(0.3)

                http_status = resp.status if resp else 0
                if http_status >= 400:
                    print(f"  ✗  {slug:<16}  HTTP {http_status} — skipping sparkle checks")
                    failures += 1
                    continue

                # Read the element state from the browser
                result = page.evaluate("""() => {
                    var el = document.querySelector('[data-sparkle-link]');
                    if (!el) return { found: false };
                    return {
                        found: true,
                        href: el.getAttribute('href') || '',
                        text: el.textContent || ''
                    };
                }""")

                page_ok = True

                # ── Assertion 1: element must exist ─────────────────────────
                if not result.get("found"):
                    print(f"  ✗  {slug:<16}  [data-sparkle-link] element not found in DOM")
                    failures += 1
                    page_ok = False
                    continue

                # ── Assertion 2: href must match sparkle.json url ────────────
                actual_href = (result.get("href") or "").rstrip("/")
                if actual_href != expected_url:
                    print(
                        f"  ✗  {slug:<16}  href mismatch\n"
                        f"              expected : {expected_url!r}\n"
                        f"              actual   : {actual_href!r}"
                    )
                    failures += 1
                    page_ok = False
                else:
                    print(f"  ✓  {slug:<16}  href  {actual_href!r}")

                # ── Assertion 3: text must include sparkle.json label ────────
                actual_text = result.get("text", "")
                if expected_label not in actual_text:
                    print(
                        f"  ✗  {slug:<16}  label not found in link text\n"
                        f"              expected to contain : {expected_label!r}\n"
                        f"              actual text         : {actual_text!r}"
                    )
                    failures += 1
                    page_ok = False
                else:
                    print(f"  ✓  {slug:<16}  label found in text")

                if page_ok:
                    passed += 1

            except Exception as exc:
                print(f"  ✗  {slug:<16}  playwright-error: {str(exc)[:160]}")
                failures += 1

            finally:
                ctx.close()

        browser.close()

    print()
    print("=" * 50)
    print(f"Pages checked : {len(TEST_PAGES)}")
    print(f"Passed        : {passed}")
    print(f"Failed        : {failures}")

    if failures == 0:
        print("\n✓ All sparkle assertions passed.")
    else:
        print(f"\n✗ {failures} assertion(s) failed — sparkle banner may be broken.", file=sys.stderr)

    return 0 if failures == 0 else 1


def main():
    parser = argparse.ArgumentParser(description="Sparkle banner smoke test")
    parser.add_argument(
        "--base-url",
        default="http://localhost:5000",
        help="Base URL of the running dev server (default: http://localhost:5000)",
    )
    args = parser.parse_args()

    print("Setting up libgbm stub…")
    ensure_stub()
    print(f"Running sparkle QA against {args.base_url}\n")
    sys.exit(run_sparkle_qa(args.base_url))


if __name__ == "__main__":
    main()

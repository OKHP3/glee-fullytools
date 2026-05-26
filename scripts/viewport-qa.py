#!/usr/bin/env python3
"""
viewport-qa.py — Responsive viewport QA using Playwright
=========================================================
Tests key pages at 8 breakpoints, captures screenshots for failures,
checks for horizontal overflow, nav layout issues, and reports findings.

Usage:
    python3 scripts/viewport-qa.py [--base-url http://localhost:5000]
    python3 scripts/viewport-qa.py --all-screenshots

Output:
    assets/audit/screenshots/2026-05-26/<page>-<width>.png  (failures; all if --all-screenshots)
    assets/audit/viewport-qa-2026-05-26.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

BASE_URL = "http://localhost:5000"
if "--base-url" in sys.argv:
    idx = sys.argv.index("--base-url")
    BASE_URL = sys.argv[idx + 1]

SCREENSHOTS_ALL = "--all-screenshots" in sys.argv

VIEWPORTS = [
    {"name": "320",  "width": 320,  "height": 568},
    {"name": "375",  "width": 375,  "height": 812},
    {"name": "390",  "width": 390,  "height": 844},
    {"name": "414",  "width": 414,  "height": 896},
    {"name": "768",  "width": 768,  "height": 1024},
    {"name": "1024", "width": 1024, "height": 768},
    {"name": "1280", "width": 1280, "height": 800},
    {"name": "1440", "width": 1440, "height": 900},
]

# Pages: (slug_for_filename, path) — paths verified against real filesystem 2026-05-26
PAGES = [
    # Core pages
    ("home",               "/"),
    ("toolbox",            "/toolbox/"),
    ("ecosystem",          "/ecosystem/"),
    ("search",             "/search/"),
    ("about",              "/about/"),
    ("contact",            "/contact/"),
    ("legal",              "/legal/"),
    ("persona",            "/persona/"),
    ("universe",           "/universe/"),
    # 7 branch hub pages (actual folder names)
    ("branch-01",          "/toolbox/01-discovered-careers/"),
    ("branch-02",          "/toolbox/02-treasured-finds/"),
    ("branch-03",          "/toolbox/03-tasty-tracker/"),
    ("branch-04",          "/toolbox/04-travelers-guide/"),
    ("branch-05",          "/toolbox/05-organized-life/"),
    ("branch-06",          "/toolbox/06-healthy-bee-ing/"),
    ("branch-07",          "/toolbox/07-identity-known/"),
    # One tool-ette per branch (first tool in each)
    ("tool-01a",           "/toolbox/01-discovered-careers/01a-resume-builder/"),
    ("tool-02a",           "/toolbox/02-treasured-finds/02a-personal-librarian/"),
    ("tool-03a",           "/toolbox/03-tasty-tracker/03a-flavor-meister/"),
    ("tool-04a",           "/toolbox/04-travelers-guide/04a-journey-diary/"),
    ("tool-05a",           "/toolbox/05-organized-life/05a-task-maestro/"),
    ("tool-06a",           "/toolbox/06-healthy-bee-ing/06a-care-check/"),
    ("tool-07a",           "/toolbox/07-identity-known/07a-critter-spotter/"),
    # Specifically-called-out pages
    ("tool-02c",           "/toolbox/02-treasured-finds/02c-present-hoarder/"),
    ("tool-04d",           "/toolbox/04-travelers-guide/04d-dreamland-journeys/"),
    ("tool-04e",           "/toolbox/04-travelers-guide/04e-memento-log/"),
]

ROOT = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = ROOT / "assets" / "audit" / "screenshots" / "2026-05-26"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def run_qa():
    from playwright.sync_api import sync_playwright

    results = []
    total_issues = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )

        for page_slug, page_path in PAGES:
            page_results = {"page": page_path, "slug": page_slug, "viewports": []}
            url = BASE_URL + page_path

            for vp in VIEWPORTS:
                context = browser.new_context(
                    viewport={"width": vp["width"], "height": vp["height"]},
                    device_scale_factor=1,
                )
                page = context.new_page()
                vp_issues = []
                vp_warnings = []

                try:
                    resp = page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    time.sleep(0.5)  # let JS (sparkle-loader, construction overlay) settle

                    status = resp.status if resp else 0
                    if status >= 400:
                        vp_issues.append(f"HTTP {status}")

                    # ── Check 1: Horizontal overflow ──────────────────────────────
                    overflow_data = page.evaluate("""() => {
                        const vw = window.innerWidth;
                        const bodyW = document.body.scrollWidth;
                        const htmlW = document.documentElement.scrollWidth;
                        const maxW = Math.max(bodyW, htmlW);
                        const offenders = [];
                        for (const el of document.querySelectorAll('*')) {
                            const r = el.getBoundingClientRect();
                            if (r.right > vw + 4) {
                                const tag = el.tagName.toLowerCase();
                                const cls = el.className || '';
                                const id = el.id || '';
                                offenders.push({
                                    tag,
                                    cls: typeof cls === 'string' ? cls.slice(0, 60) : '',
                                    id: id.slice(0, 30),
                                    right: Math.round(r.right),
                                });
                                if (offenders.length >= 6) break;
                            }
                        }
                        return { bodyW, htmlW, maxW, vw, offenders };
                    }""")
                    if overflow_data["maxW"] > overflow_data["vw"] + 4:
                        overflow_px = overflow_data["maxW"] - overflow_data["vw"]
                        offenders = overflow_data["offenders"][:3]
                        offender_str = "; ".join(
                            f"{o['tag']}{'#'+o['id'] if o['id'] else ''}{'.' + o['cls'].split()[0] if o['cls'] else ''}"
                            for o in offenders
                        ) if offenders else "unknown"
                        vp_issues.append(
                            f"horizontal-overflow +{overflow_px}px (offenders: {offender_str})"
                        )

                    # ── Check 2: Nav toggle visible at mobile ─────────────────────
                    if vp["width"] < 768:
                        toggle = page.query_selector(".nav-toggle")
                        if toggle and not toggle.is_visible():
                            vp_issues.append("nav-toggle hidden at mobile width")
                        elif not toggle:
                            vp_warnings.append("nav-toggle element not found")

                    # ── Check 3: H1 not clipped ───────────────────────────────────
                    h1 = page.query_selector("h1")
                    if h1:
                        h1_box = h1.bounding_box()
                        if h1_box and h1_box["width"] > 0:
                            if h1_box["x"] + h1_box["width"] > vp["width"] + 4:
                                vp_issues.append("h1 overflows right edge")

                    # ── Check 4: Footer visible ───────────────────────────────────
                    footer = page.query_selector("footer, .site-footer")
                    if footer:
                        box = footer.bounding_box()
                        if box and box["height"] < 1:
                            vp_warnings.append("footer has zero height")

                    # ── Check 5: Images not overflowing ──────────────────────────
                    img_overflow = page.evaluate("""() => {
                        const issues = [];
                        for (const img of document.querySelectorAll('img')) {
                            const r = img.getBoundingClientRect();
                            const vw = window.innerWidth;
                            if (r.width > vw + 4 && r.width > 50) {
                                issues.push({ src: img.src.split('/').pop().slice(0, 30),
                                              w: Math.round(r.width), vw });
                                if (issues.length >= 3) break;
                            }
                        }
                        return issues;
                    }""")
                    for img_iss in img_overflow:
                        vp_issues.append(
                            f"img '{img_iss['src']}' wider than viewport "
                            f"({img_iss['w']}px > {img_iss['vw']}px)"
                        )

                    # ── Check 6: Text ≥ 14px ──────────────────────────────────────
                    small_text = page.evaluate("""() => {
                        const MIN_PX = 14;
                        const issues = [];
                        for (const el of document.querySelectorAll('p, li, td')) {
                            const fs = parseFloat(window.getComputedStyle(el).fontSize);
                            if (fs > 0 && fs < MIN_PX) {
                                const text = el.textContent.trim().slice(0, 40);
                                if (text) issues.push({ fs: Math.round(fs * 10) / 10, text });
                                if (issues.length >= 3) break;
                            }
                        }
                        return issues;
                    }""")
                    for st in small_text:
                        vp_warnings.append(f"text at {st['fs']}px (<14px): '{st['text'][:30]}'")

                    # Screenshot: on any issue, or --all-screenshots
                    if vp_issues or SCREENSHOTS_ALL:
                        shot_path = SCREENSHOTS_DIR / f"{page_slug}-{vp['name']}.png"
                        try:
                            page.screenshot(path=str(shot_path), full_page=False)
                        except Exception:
                            pass

                except Exception as exc:
                    vp_issues.append(f"playwright-error: {exc}")
                finally:
                    context.close()

                vp_entry = {
                    "viewport": vp["name"],
                    "width": vp["width"],
                    "issues": vp_issues,
                    "warnings": vp_warnings,
                }
                page_results["viewports"].append(vp_entry)
                total_issues += len(vp_issues)

                status_char = "✗" if vp_issues else ("△" if vp_warnings else "✓")
                issue_str = ("  ".join(vp_issues[:2]) if vp_issues
                             else ("  ".join(vp_warnings[:1]) if vp_warnings else "ok"))
                print(f"  {status_char} {page_slug:<22} {vp['name']:>5}px  {issue_str}")

            results.append(page_results)

        browser.close()

    # Write JSON report
    out_dir = ROOT / "assets" / "audit"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / "viewport-qa-2026-05-26.json"
    out.write_text(json.dumps({
        "date": "2026-05-26",
        "base_url": BASE_URL,
        "viewports_tested": [v["name"] for v in VIEWPORTS],
        "pages_tested": len(PAGES),
        "total_issues": total_issues,
        "results": results,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"Pages tested:   {len(PAGES)}")
    print(f"Viewports:      {len(VIEWPORTS)}")
    print(f"Total issues:   {total_issues}")
    print(f"Report:         {out.relative_to(ROOT)}")
    print(f"Screenshots:    {SCREENSHOTS_DIR.relative_to(ROOT)}/")

    return 0 if total_issues == 0 else 1


if __name__ == "__main__":
    sys.exit(run_qa())

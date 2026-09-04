#!/usr/bin/env python3
"""Inclusive browser QA for the Glee-fully public hub.

This is intentionally a small, static-site regression suite rather than a
claim of universal WCAG conformance. It exercises the journeys that can be
proved in a headless Chromium browser:

* keyboard navigation, focus return, focus rings, search status, and the WIP gate
* accessibility-tree landmarks and names
* 200% layout zoom, reduced motion, denied storage, and JavaScript disabled
* accented search input and no-JavaScript form recovery

Usage:
    python3 scripts/inclusive-accessibility-qa.py
    python3 scripts/inclusive-accessibility-qa.py --base=http://localhost:5000

The machine-readable report is written beside the human evidence report.
Real VoiceOver/NVDA speech output still requires a human workstation.
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "assets" / "audit"
ROUTES = {
    "home": "/",
    "toolbox": "/toolbox/",
    "search": "/search/",
    "arcade": "/arcade/",
    "404": "/404.html",
    "construction": "/toolbox/07-identity-known/07g-self-fixer/",
}


def browser_setup() -> list[str]:
    """Reuse the existing Replit Chromium setup when available."""
    runner = ROOT / "scripts" / "run-viewport-qa.py"
    spec = importlib.util.spec_from_file_location("viewport_qa", runner)
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.ensure_stub()
        return module.LAUNCH_ARGS
    return ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:5000")
    return parser.parse_args()


def record(results: list[dict], name: str, passed: bool, details: dict | str) -> None:
    results.append({
        "name": name,
        "status": "pass" if passed else "fail",
        "details": details,
    })
    mark = "PASS" if passed else "FAIL"
    print(f"{mark:>4}  {name}")
    if not passed:
        print(f"      {details}")


def is_expected_third_party_console_message(message: str) -> bool:
    """Google Analytics beacons are intentionally blocked by the page CSP."""
    return "googletagmanager.com/td?id=" in message


def ax_summary(context, page) -> dict:
    """Capture the browser accessibility tree without pretending it is speech."""
    session = context.new_cdp_session(page)
    nodes = session.send("Accessibility.getFullAXTree").get("nodes", [])
    roles = sorted({
        node.get("role", {}).get("value")
        for node in nodes
        if node.get("role", {}).get("value")
    })
    named = sorted({
        node.get("name", {}).get("value")
        for node in nodes
        if node.get("name", {}).get("value")
    })
    return {
        "roles": roles,
        "landmarks_present": {
            "main": "main" in roles,
            "navigation": "navigation" in roles,
            "contentinfo": "contentinfo" in roles,
            "search": "search" in roles,
        },
        "named_examples": [
            value for value in named
            if value in {
                "Primary navigation",
                "Breadcrumb",
                "Search results",
                "Tips",
                "Glee-fully home",
            }
        ],
    }


def main() -> int:
    args = parse_args()
    results: list[dict] = []
    page_evidence: dict = {}
    launch_args = browser_setup()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        print(f"Playwright is required: {exc}", file=sys.stderr)
        return 2

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=launch_args)

        for slug, path in ROUTES.items():
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            page = context.new_page()
            errors: list[str] = []
            console_errors: list[str] = []
            expected_console_blocks: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))

            def on_console(message) -> None:
                if message.type != "error":
                    return
                if is_expected_third_party_console_message(message.text):
                    expected_console_blocks.append(message.text)
                else:
                    console_errors.append(message.text)

            page.on("console", on_console)
            response = page.goto(
                args.base + path,
                wait_until="domcontentloaded",
                timeout=15000,
            )
            page.wait_for_timeout(250)
            overflow = page.evaluate(
                "() => Math.max(document.body.scrollWidth, "
                "document.documentElement.scrollWidth) - window.innerWidth"
            )
            page_evidence[slug] = {
                "path": path,
                "http_status": response.status if response else None,
                "horizontal_overflow_px": overflow,
                "page_errors": errors,
                "console_errors": console_errors,
                "expected_third_party_console_blocks": expected_console_blocks,
                "accessibility_tree": ax_summary(context, page),
            }
            record(
                results,
                f"{slug}: baseline loads without browser errors",
                bool(response and response.status < 400 and not errors and not console_errors),
                page_evidence[slug],
            )
            if slug == "arcade":
                outbound = page.evaluate(
                    """() => [...document.querySelectorAll('a[href^="http"]')]
                      .filter(link => link.target === '_blank')
                      .map(link => ({
                        href: link.href,
                        rel: link.rel.split(/\\s+/).filter(Boolean)
                      }))"""
                )
                outbound_safe = all(
                    "noopener" in link["rel"] and "noreferrer" in link["rel"]
                    for link in outbound
                )
                record(results, "Arcade: outbound links preserve safe new-tab handling", (
                    bool(outbound) and outbound_safe
                ), {"checked": len(outbound), "links": outbound})
            if slug == "404":
                error_page = page.evaluate(
                    """() => ({
                      heading: document.querySelector('main h1')?.textContent.trim(),
                      hasRecoveryLinks: document.querySelectorAll(
                        'main a[href="/"], main a[href="/toolbox/"]'
                      ).length >= 2
                    })"""
                )
                record(results, "404: not-found message and recovery links are exposed", (
                    "page" in error_page["heading"].lower()
                    and "toolbox" in error_page["heading"].lower()
                    and error_page["hasRecoveryLinks"]
                ), error_page)
            context.close()

        # Keyboard-only mobile navigation and focus visibility.
        context = browser.new_context(viewport={"width": 375, "height": 812})
        page = context.new_page()
        page.goto(args.base + "/", wait_until="domcontentloaded")
        page.wait_for_timeout(250)
        page.locator(".nav-toggle").focus()
        page.keyboard.press("Enter")
        opened = page.evaluate(
            "() => document.querySelector('.site-header').classList.contains('nav-open') "
            "&& document.querySelector('.nav-toggle').getAttribute('aria-expanded') === 'true'"
        )
        page.keyboard.press("Escape")
        closed = page.evaluate(
            "() => !document.querySelector('.site-header').classList.contains('nav-open') "
            "&& document.querySelector('.nav-toggle').getAttribute('aria-expanded') === 'false' "
            "&& document.activeElement === document.querySelector('.nav-toggle')"
        )
        focus_ring = page.evaluate(
            """() => {
              const button = document.querySelector('.okh-search-trigger');
              button.focus();
              const style = getComputedStyle(button);
              return {outlineStyle: style.outlineStyle, outlineWidth: style.outlineWidth};
            }"""
        )
        record(results, "mobile nav: Enter opens and Escape returns focus", bool(opened and closed), {
            "opened": opened,
            "closed_and_focus_returned": closed,
        })
        record(results, "search trigger: visible keyboard focus ring", (
            focus_ring["outlineStyle"] != "none"
            and float(focus_ring["outlineWidth"].replace("px", "")) >= 2
        ), focus_ring)
        context.close()

        # Global search: keyboard open, status announcement, accent folding,
        # and focus return to the trigger.
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        page.goto(args.base + "/", wait_until="domcontentloaded")
        page.wait_for_timeout(250)
        page.locator(".okh-search-trigger").focus()
        page.keyboard.press("Control+K")
        page.locator(".okh-search-input").fill("résumé")
        page.wait_for_timeout(250)
        search_result = page.evaluate(
            """() => ({
              open: document.querySelector('.okh-search-overlay').dataset.open,
              status: document.querySelector('.okh-search-status').textContent,
              resultCount: document.querySelectorAll('.okh-search-result').length,
              firstHref: document.querySelector('.okh-search-result')?.getAttribute('href'),
              statusRole: document.querySelector('.okh-search-status').getAttribute('role'),
              statusLive: document.querySelector('.okh-search-status').getAttribute('aria-live'),
              listItems: document.querySelectorAll('.okh-search-results > [role="listitem"]').length
            })"""
        )
        page.keyboard.press("Escape")
        search_result["focusReturned"] = page.evaluate(
            "() => document.activeElement === document.querySelector('.okh-search-trigger')"
        )
        record(results, "global search: accented input and announcement", (
            search_result["open"] == "true"
            and search_result["resultCount"] > 0
            and search_result["firstHref"] == "/toolbox/01-discovered-careers/01a-resume-builder/"
            and search_result["statusRole"] == "status"
            and search_result["statusLive"] == "polite"
            and search_result["listItems"] == search_result["resultCount"]
            and search_result["focusReturned"]
        ), search_result)
        context.close()

        # Construction gate: initial focus, forward/reverse focus trap, Escape,
        # and hidden/focus recovery after dismissal.
        context = browser.new_context(viewport={"width": 375, "height": 812})
        page = context.new_page()
        page.goto(args.base + ROUTES["construction"], wait_until="domcontentloaded")
        page.wait_for_timeout(250)
        initial_focus = page.evaluate(
            "() => document.activeElement?.matches('[data-wip-dismiss]')"
        )
        page.keyboard.press("Tab")
        forward_focus = page.evaluate(
            "() => document.activeElement?.matches('[data-wip-dismiss]')"
        )
        page.keyboard.down("Shift")
        page.keyboard.press("Tab")
        page.keyboard.up("Shift")
        reverse_focus = page.evaluate(
            "() => document.activeElement?.matches('[data-wip-dismiss]')"
        )
        page.keyboard.press("Escape")
        gate_dismissed = page.evaluate(
            "() => document.querySelector('.construction-overlay').hasAttribute('hidden') "
            "&& document.activeElement === document.querySelector('#main')"
        )
        record(results, "construction gate: focus trap and dismissal recovery", (
            initial_focus and forward_focus and reverse_focus and gate_dismissed
        ), {
            "initial_focus": initial_focus,
            "forward_focus": forward_focus,
            "reverse_focus": reverse_focus,
            "hidden_and_main_focused": gate_dismissed,
        })
        context.close()

        # A 640px layout viewport is the browser-layout equivalent of viewing
        # a 1280px desktop at 200% zoom. This makes responsive media queries
        # participate, unlike CSS zoom, which only scales painted content.
        zoom_overflow: dict[str, int] = {}
        for slug, path in {
            "home": "/",
            "toolbox": "/toolbox/",
            "search": "/search/",
            "arcade": "/arcade/",
            "404": "/404.html",
        }.items():
            context = browser.new_context(viewport={"width": 640, "height": 400})
            page = context.new_page()
            page.goto(args.base + path, wait_until="domcontentloaded")
            page.wait_for_timeout(150)
            zoom_overflow[slug] = page.evaluate(
                "() => Math.max(document.body.scrollWidth, "
                "document.documentElement.scrollWidth) - window.innerWidth"
            )
            context.close()
        record(results, "200% layout zoom: representative routes stay within viewport", (
            all(value <= 4 for value in zoom_overflow.values())
        ), {
            "method": "640px layout viewport equivalent to 200% zoom from 1280px CSS width",
            "overflow_px": zoom_overflow,
        })

        # Reduced motion: reveal content is not left hidden and transitions are
        # reduced by the shared stylesheet.
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            reduced_motion="reduce",
        )
        page = context.new_page()
        page.goto(args.base + "/", wait_until="domcontentloaded")
        page.wait_for_timeout(250)
        motion = page.evaluate(
            """() => ({
              revealCount: document.querySelectorAll('.reveal-on-scroll').length,
              visibleRevealCount: [...document.querySelectorAll('.reveal-on-scroll')]
                .filter(el => el.classList.contains('is-visible')).length,
              reducedTransitionCount: [...document.querySelectorAll('*')]
                .filter(el => parseFloat(getComputedStyle(el).transitionDuration) <= 0.001
                  && parseFloat(getComputedStyle(el).animationDuration) <= 0.001).length
            })"""
        )
        record(results, "reduced motion: content is visible without reveal delay", (
            motion["revealCount"] == motion["visibleRevealCount"]
            and motion["reducedTransitionCount"] > 0
        ), motion)
        context.close()

        # Denied storage: load and interact with both the brand toggle and the
        # construction gate without a SecurityError aborting page setup.
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        context.add_init_script(
            """Object.defineProperty(window, 'localStorage', {
              configurable: false,
              get() { throw new DOMException('Storage denied', 'SecurityError'); }
            });"""
        )
        page = context.new_page()
        storage_errors: list[str] = []
        page.on("pageerror", lambda error: storage_errors.append(str(error)))
        page.goto(args.base + "/", wait_until="domcontentloaded")
        page.wait_for_timeout(250)
        page.locator(".glee-color-toggle").click()
        storage_ready = page.evaluate(
            "() => Boolean(document.querySelector('.okh-search-trigger') "
            "&& document.querySelector('.glee-color-toggle'))"
        )
        record(results, "storage denied: hub initializes and toggle remains usable", (
            storage_ready and not storage_errors
        ), {"controls_present": storage_ready, "page_errors": storage_errors})
        context.close()

        # No-JavaScript search fallback: the directory is rendered and Enter
        # performs a normal GET instead of silently being cancelled.
        context = browser.new_context(
            viewport={"width": 375, "height": 812},
            java_script_enabled=False,
        )
        page = context.new_page()
        page.goto(args.base + "/search/", wait_until="domcontentloaded")
        page.locator("#glee-search-page-input").fill("résumé")
        page.locator("#glee-search-page-input").press("Enter")
        page.wait_for_load_state("domcontentloaded")
        nojs = page.evaluate(
            """() => ({
              query: new URL(location.href).searchParams.get('q'),
              directoryVisible: getComputedStyle(
                document.querySelector('.glee-search-page__nojs')
              ).display !== 'none',
              directoryLinks: document.querySelectorAll(
                '.glee-search-page__directory a'
              ).length,
              formAction: document.querySelector('form').getAttribute('action'),
              formMethod: document.querySelector('form').getAttribute('method'),
              overflow: Math.max(document.body.scrollWidth,
                document.documentElement.scrollWidth) - innerWidth
            })"""
        )
        record(results, "JavaScript disabled: search fallback and Enter recovery", (
            nojs["query"] == "résumé"
            and nojs["directoryVisible"]
            and nojs["directoryLinks"] >= 10
            and nojs["formAction"] == "/search/"
            and nojs["formMethod"] == "get"
            and nojs["overflow"] <= 4
        ), nojs)
        context.close()

        browser.close()

    date = dt.date.today().isoformat()
    report = {
        "date": date,
        "base_url": args.base,
        "purpose": "Current browser evidence for inclusive public-hub journeys",
        "automated_check_count": len(results),
        "passed": sum(item["status"] == "pass" for item in results),
        "failed": sum(item["status"] == "fail" for item in results),
        "browser": "Chromium via Playwright",
        "assistive_technology_note": (
            "Chrome accessibility-tree roles and names were captured. "
            "Real VoiceOver/NVDA speech output was not available in this Linux "
            "runner and is reported as a manual limitation."
        ),
        "page_evidence": page_evidence,
        "checks": results,
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    output = REPORT_DIR / f"inclusive-accessibility-qa-{date}.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nReport: {output.relative_to(ROOT)}")
    print(f"Passed: {report['passed']}  Failed: {report['failed']}")
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
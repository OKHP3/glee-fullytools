#!/usr/bin/env python3
"""Prove the blocking color-scheme bootstrap prevents a theme flash.

Run against the local site server:
    python3 scripts/tests/test-color-scheme-init.py \
        --base-url http://127.0.0.1:5000

The test deliberately waits only for DOMContentLoaded.  The color-scheme
script is a parser-blocking head script, so the initial DOM assertion at that
point proves the saved preference was applied before the page could render.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from urllib.parse import urljoin, urlsplit


ASSET_PATH = "/assets/js/color-scheme-init.js"


@dataclass
class AssetTiming:
    request_seen: bool
    request_finished_before_domcontentloaded: bool
    response_end: float | None
    first_paint: float | None


def first_party(url: str, base_url: str) -> bool:
    return urlsplit(url).netloc == urlsplit(base_url).netloc


def load_context(browser, base_url: str, init_script: str):
    context = browser.new_context(service_workers="block")
    context.add_init_script(init_script)
    context.route(
        "**/*",
        lambda route: (
            route.continue_()
            if first_party(route.request.url, base_url)
            else route.abort()
        ),
    )
    return context


def check_saved_preference(browser, base_url: str, preference: str) -> AssetTiming:
    context = load_context(
        browser,
        base_url,
        f"localStorage.setItem('glee-color-scheme', {preference!r});",
    )
    page = context.new_page()
    events: list[tuple[str, str | None]] = []
    page.on(
        "request",
        lambda request: (
            events.append(("request", request.url))
            if urlsplit(request.url).path == ASSET_PATH
            else None
        ),
    )
    page.on(
        "requestfinished",
        lambda request: (
            events.append(("finished", request.url))
            if urlsplit(request.url).path == ASSET_PATH
            else None
        ),
    )
    page.on("domcontentloaded", lambda: events.append(("domcontentloaded", None)))

    try:
        response = page.goto(urljoin(base_url, "/"), wait_until="domcontentloaded")
        assert response is not None and response.ok, (
            f"Representative Glee page did not load: "
            f"{response.status if response else 'no response'}"
        )

        initial = page.evaluate(
            """() => ({
              scheme: document.documentElement.getAttribute('data-color-scheme'),
              readyState: document.readyState,
              colorSchemeScript: Boolean(document.querySelector(
                'head > script[src*="color-scheme-init.js"]'
              ))
            })"""
        )
        assert initial["scheme"] == preference, (
            f"Saved {preference} preference was not present at initial DOM "
            f"assertion: {initial}"
        )
        assert initial["colorSchemeScript"], (
            "Representative page does not load the external color-scheme asset"
        )

        asset_events = [
            (kind, index)
            for index, (kind, _) in enumerate(events)
            if kind in {"request", "finished"}
        ]
        dcl_index = next(
            index
            for index, (kind, _) in enumerate(events)
            if kind == "domcontentloaded"
        )
        request_index = next(
            index for kind, index in asset_events if kind == "request"
        )
        finished_index = next(
            index for kind, index in asset_events if kind == "finished"
        )
        assert request_index < dcl_index, (
            "External color-scheme asset was not requested before "
            "DOMContentLoaded"
        )
        assert finished_index < dcl_index, (
            "External color-scheme asset did not finish before "
            "DOMContentLoaded"
        )

        timing = page.evaluate(
            """assetPath => {
              const asset = performance.getEntriesByType('resource')
                .find(entry => new URL(entry.name).pathname === assetPath);
              const paints = performance.getEntriesByType('paint');
              const firstPaint = paints.find(entry => entry.name === 'first-paint');
              return {
                responseEnd: asset ? asset.responseEnd : null,
                firstPaint: firstPaint ? firstPaint.startTime : null
              };
            }""",
            ASSET_PATH,
        )
        if timing["firstPaint"] is not None:
            assert timing["responseEnd"] is not None, (
                "Color-scheme asset has no resource timing entry despite "
                "first-paint being available"
            )
            assert timing["responseEnd"] <= timing["firstPaint"], (
                "Color-scheme asset finished after first-paint: "
                f"{timing}"
            )

        return AssetTiming(
            request_seen=True,
            request_finished_before_domcontentloaded=True,
            response_end=timing["responseEnd"],
            first_paint=timing["firstPaint"],
        )
    finally:
        context.close()


def check_disabled_storage(browser, base_url: str) -> dict[str, object]:
    context = load_context(
        browser,
        base_url,
        """Object.defineProperty(window, 'localStorage', {
          configurable: false,
          get() { throw new DOMException('Storage denied', 'SecurityError'); }
        });""",
    )
    page = context.new_page()
    page_errors: list[str] = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    try:
        response = page.goto(urljoin(base_url, "/"), wait_until="domcontentloaded")
        assert response is not None and response.ok, (
            f"Page failed when storage was disabled: "
            f"{response.status if response else 'no response'}"
        )
        assert page.locator("h1").is_visible(), (
            "Representative Glee page did not remain usable with disabled storage"
        )
        assert page.locator(".glee-color-toggle").is_visible(), (
            "Glee color control did not remain usable with disabled storage"
        )
        assert not page_errors, f"Page errors with disabled storage: {page_errors}"
        return {"h1_visible": True, "color_toggle_visible": True}
    finally:
        context.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    parser.add_argument(
        "--executable-path",
        default=os.environ.get("PLAYWRIGHT_EXECUTABLE_PATH"),
        help="Optional Chromium binary path for local runners.",
    )
    args = parser.parse_args()

    from playwright.sync_api import sync_playwright

    base_url = args.base_url.rstrip("/") + "/"
    with sync_playwright() as playwright:
        launch_options = {"headless": True}
        if args.executable_path:
            launch_options["executable_path"] = args.executable_path
        browser = playwright.chromium.launch(**launch_options)
        try:
            evidence = {
                preference: check_saved_preference(browser, base_url, preference).__dict__
                for preference in ("light", "dark")
            }
            evidence["disabled_storage"] = check_disabled_storage(browser, base_url)
        finally:
            browser.close()

    print("Color-scheme bootstrap browser regression passed.")
    for name, result in evidence.items():
        print(f"  {name}: {result}")


if __name__ == "__main__":
    main()
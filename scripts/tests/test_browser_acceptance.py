#!/usr/bin/env python3
"""Representative browser release gate against an already running static site.

Run explicitly after generators and static checks:
    python3 scripts/tests/test_browser_acceptance.py --base-url http://localhost:5000

Uses the served search JSON without rebuilding or substituting it. Playwright
and the selected browser must already be installed; missing support fails the
gate. Browser imports are deferred so ordinary unittest discovery stays usable.
All external browser requests, including measurement, are blocked. Service
workers are blocked here so a previous cached release cannot conceal defects;
the separate resilience suite owns worker lifecycle and offline coverage.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time
from urllib.parse import parse_qs, urljoin, urlsplit


def rgba(value: str) -> list[float]:
    if not value.startswith(("rgb(", "rgba(")):
        raise AssertionError(f"unsupported computed color: {value}")
    channels = [float(part) for part in re.findall(r"[\d.]+", value)]
    return channels + [1.0] if len(channels) == 3 else channels


def contrast(foreground: str, background: str) -> float:
    fg, bg = rgba(foreground), rgba(background)
    assert bg[3] == 1, "Contrast requires an opaque measured card background"

    def luminance(channels):
        linear = [(c / 255 / 12.92 if c / 255 <= .04045 else
                   ((c / 255 + .055) / 1.055) ** 2.4) for c in channels]
        return sum(c * weight for c, weight in zip(linear, (.2126, .7152, .0722)))

    front = luminance([fg[i] * fg[3] + bg[i] * (1 - fg[3]) for i in range(3)])
    back = luminance(bg[:3])
    return (max(front, back) + .05) / (min(front, back) + .05)


def measurement_url(url: str) -> bool:
    host = urlsplit(url).hostname or ""
    return any(host == domain or host.endswith("." + domain)
               for domain in ("googletagmanager.com", "google-analytics.com"))


def adapt_local_http_navigation(url: str, base_url: str, content_type: str,
                                body: str, *, is_navigation: bool) -> str | None:
    """Adapt only loopback HTTP HTML navigations for WebKit's local fixture.

    Production HTML and policy allowlists remain unchanged. The helper removes
    only the transport-upgrade directive that makes WebKit rewrite local HTTP
    subresources to HTTPS, where the test server has no TLS endpoint.
    """
    base = urlsplit(base_url)
    target = urlsplit(url)
    local_http = base.scheme == "http" and base.hostname in {"localhost", "127.0.0.1"}
    if not (local_http and is_navigation and target.scheme == base.scheme
            and target.netloc == base.netloc and "text/html" in content_type):
        return None
    return body.replace("; upgrade-insecure-requests", "")


def run_checks(browser, expect, args) -> list[dict]:
    base = args.base_url.rstrip("/")
    parsed_base = urlsplit(base)
    origin = parsed_base.netloc
    local_http = parsed_base.scheme == "http" and parsed_base.hostname in {"localhost", "127.0.0.1"}
    results = []

    def wait_for_page_condition(page, expression: str) -> None:
        """Poll a page expression without asking the page to compile eval code.

        The production CSP intentionally omits ``unsafe-eval``. Playwright's
        string form of ``wait_for_function`` compiles a predicate in the page
        realm and is therefore rejected by that policy. ``page.evaluate`` runs
        the same read-only probe through Playwright's evaluation channel, so a
        bounded Python poll preserves the assertion without asking the page
        to compile a new predicate under the real CSP.
        """
        deadline = time.monotonic() + args.timeout_ms / 1000
        while time.monotonic() < deadline:
            if page.evaluate(expression):
                return
            page.wait_for_timeout(50)
        raise AssertionError(f"Timed out waiting for page condition: {expression}")

    def first_party(url):
        parsed = urlsplit(url)
        return parsed.scheme == urlsplit(base).scheme and parsed.netloc == origin

    def visit(page, route="/"):
        response = page.goto(base + route, wait_until="load")
        assert response and response.ok, f"Navigation failed: {route}"
        expect(page.locator("h1")).to_be_visible()
        assert page.title().strip(), f"Blank page title: {route}"
        wait_for_page_condition(page, "Boolean(window.gleeAnalytics)")
        page.wait_for_load_state("networkidle")

    def check(name, action, **context_options):
        context = browser.new_context(service_workers="block", reduced_motion="reduce",
                                      viewport={"width": 1280, "height": 900}, **context_options)
        health = {"page_errors": [], "http_failures": [], "request_failures": [],
                  "first_party_console_errors": []}
        measurement_attempts = []
        blocked_external = []

        def route_request(route):
            url = route.request.url
            if local_http and route.request.is_navigation_request() and first_party(url):
                response = route.fetch()
                adapted = adapt_local_http_navigation(
                    url, base, response.headers.get("content-type", ""), response.text(),
                    is_navigation=True,
                )
                if adapted is not None:
                    route.fulfill(response=response, body=adapted)
                else:
                    route.fulfill(response=response)
                return
            if first_party(url):
                route.continue_()
            else:
                blocked_external.append(url)
                if measurement_url(url):
                    measurement_attempts.append(url)
                route.abort()

        context.route("**/*", route_request)
        page = context.new_page()
        page.set_default_timeout(args.timeout_ms)
        page.on("pageerror", lambda error: health["page_errors"].append(str(error)))
        page.on("response", lambda response: health["http_failures"].append(
            f"{response.status} {response.url}") if first_party(response.url) and response.status >= 400 else None)
        page.on("requestfailed", lambda request: health["request_failures"].append(
            f"{request.url}: {request.failure}") if first_party(request.url) else None)
        page.on("console", lambda message: health["first_party_console_errors"].append(message.text)
                if message.type == "error" and first_party(message.location.get("url", "")) else None)
        result = {"name": name}
        try:
            result["evidence"] = action(page, measurement_attempts)
            page.wait_for_load_state("networkidle")
            assert not any(health.values()), json.dumps(health)
            result["status"] = "PASS"
        except Exception as error:
            result.update(status="FAIL", error=str(error))
        finally:
            result["health"] = health
            result["local_http_fixture"] = {
                "enabled": local_http,
                "scope": "same-origin loopback HTTP navigation HTML only",
                "transformation": "remove ; upgrade-insecure-requests only",
            }
            result["blocked_external_requests"] = len(blocked_external)
            result["blocked_external_urls"] = blocked_external
            result["blocked_measurement_attempts"] = len(measurement_attempts)
            if args.screenshots:
                try:
                    args.screenshots.mkdir(parents=True, exist_ok=True)
                    image = args.screenshots / (re.sub(r"[^a-z0-9]+", "-", name.lower()) + ".png")
                    page.screenshot(path=str(image), full_page=False)
                    result["screenshot"] = str(image)
                except Exception as error:
                    result["screenshot_error"] = str(error)
            context.close()
            results.append(result)

    def generated_index(page, _):
        response = page.request.get(base + "/assets/data/search-index.json")
        assert response.ok, f"Search JSON returned {response.status}"
        data = response.json()
        entries = data["pages"]
        assert len(entries) == 61, f"Expected 61 public entries, got {len(entries)}"
        assert any(entry["url"] == "/foundry/" for entry in entries), "FoundRy is missing from search"
        assert len({entry["url"] for entry in entries}) == len(entries)
        assert all(entry.get("category") for entry in entries), "Missing useful categories"
        states = Counter(entry.get("publication_state") for entry in entries if entry.get("publication_state"))
        assert states == {"live": 1, "beta": 24, "unavailable": 17}, dict(states)
        scheduling = next(entry for entry in entries if "/05d-scheduling-wizard/" in entry["url"])
        assert scheduling["publication_state"] == "unavailable"
        assert "personality-rich tagline" not in scheduling.get("body", "").replace("‑", "-")
        visit(page, "/search/?q=seniority")
        expect(page.locator('[data-glee-search-inline-results] a[href="/toolbox/01-discovered-careers/01a-resume-builder/"]')).to_be_visible()
        return {"entries": len(entries), "publication_states": dict(states), "deep_function_query": "seniority"}

    check("served generated index and deep function discovery", generated_index)

    def modal(page, _):
        visit(page)
        trigger = page.locator(".okh-search-trigger")
        trigger.click()
        dialog = page.get_by_role("dialog", name="Search Glee‑fully Tools", exact=True)
        expect(dialog).to_be_visible()
        input_box = dialog.locator(".okh-search-input")
        expect(input_box).to_be_focused()
        expect(dialog.locator(".okh-search-hint-list button")).to_have_text(
            ["resume", "budget", "scheduling", "travel", "journal"])
        input_box.fill("scheduling")
        expect(dialog.locator(".okh-search-results")).to_contain_text("Scheduling Wizard")
        expect(dialog.locator(".okh-search-results")).to_contain_text("Unavailable")
        page.keyboard.press("Escape")
        expect(dialog).not_to_be_visible()
        expect(trigger).to_be_focused()
        trigger.click()
        input_box.fill("resume")
        links = dialog.locator(".okh-search-result")
        expect(links.nth(1)).to_be_visible()
        input_box.press("ArrowDown")
        expect(links.nth(1)).to_have_attribute("data-active", "true")
        selected = links.nth(1).get_attribute("href")
        input_box.press("ArrowUp")
        expect(links.first).to_have_attribute("data-active", "true")
        input_box.press("ArrowDown")
        input_box.press("Enter")
        page.wait_for_url(urljoin(base + "/", selected))
        page.wait_for_load_state("load")
        expect(page.locator("h1")).to_be_visible()
        return {"dialog": "Search Glee‑fully Tools", "keyboard_destination": selected,
                "escape_restores_trigger_focus": True}

    check("Glee modal identity keyboard and focus return", modal)

    def inline(page, _):
        visit(page, "/search/?q=resume")
        input_box = page.locator("[data-glee-search-inline-input]")
        links = page.locator("[data-glee-search-inline-results] a")
        expect(links.first).to_be_visible()
        input_box.fill("budget")
        wait_for_page_condition(page, "new URL(location.href).searchParams.get('q') === 'budget'")
        expect(links.first).to_be_visible()
        first_budget = links.first.get_attribute("href")
        chip = page.locator('[data-glee-search-inline-categories] button[data-cat="Tool-ette"]')
        chip.click()
        expect(chip).to_have_attribute("aria-pressed", "true")
        assert parse_qs(urlsplit(page.url).query).get("cat") == ["Tool-ette"]
        page.go_back()
        expect(input_box).to_have_value("budget")
        assert "cat" not in parse_qs(urlsplit(page.url).query)
        page.go_back()
        expect(input_box).to_have_value("resume")
        page.go_forward()
        expect(input_box).to_have_value("budget")
        page.reload(wait_until="load")
        expect(input_box).to_have_value("budget")
        expect(links.first).to_have_attribute("href", first_budget)
        for width in (1280, 375):
            page.set_viewport_size({"width": width, "height": 900})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"Search overflows at {width}px"
        input_box.press("ArrowDown")
        selected = page.locator('[data-glee-search-inline-results] a[data-active="true"]').get_attribute("href")
        input_box.press("Enter")
        page.wait_for_url(urljoin(base + "/", selected))
        page.wait_for_load_state("load")
        expect(page.locator("h1")).to_be_visible()
        return {"query": "budget", "category": "Tool-ette", "history_and_reload": True,
                "viewports": [1280, 375], "keyboard_destination": selected}

    check("inline query category history reload and keyboard", inline)

    def consent(page, attempts):
        visit(page, "/legal/")
        status = page.locator("[data-analytics-status]")
        expect(status).to_contain_text("is off for this browser")
        assert not attempts, "Measurement attempted before consent"
        with page.expect_request(lambda request: measurement_url(request.url)):
            page.locator('[data-analytics-action="granted"]').click()
        expect(status).to_contain_text("is on for this browser")
        assert page.evaluate("localStorage.getItem('glee-analytics-consent')") == "granted"
        assert page.evaluate("window['ga-disable-G-89W66VMGPB']") is False
        with page.expect_request(lambda request: measurement_url(request.url)):
            page.reload(wait_until="load")
        expect(status).to_contain_text("is on for this browser")
        page.locator('[data-analytics-action="denied"]').click()
        expect(status).to_contain_text("is off for this browser")
        assert page.evaluate("window['ga-disable-G-89W66VMGPB']") is True
        assert page.evaluate("localStorage.getItem('glee-analytics-consent')") == "denied"
        before = len(attempts)
        page.reload(wait_until="load")
        wait_for_page_condition(page, "Boolean(window.gleeAnalytics)")
        expect(status).to_contain_text("is off for this browser")
        expect(page.locator("script[data-glee-analytics]")).to_have_count(0)
        assert len(attempts) == before, "Measurement attempted after saved denial"
        return {"saved_grant_reload": True, "saved_denial_reload": True,
                "measurement_requests_sent": 0, "attempts_blocked": len(attempts)}

    check("consent default grant reload and denied reload", consent)

    for mode in ("light", "dark", "auto-light", "auto-dark"):
        def measured_colors(page, _, mode=mode):
            visit(page)
            colors = page.evaluate("""async mode => {
                if (mode.startsWith('auto')) document.documentElement.removeAttribute('data-color-scheme');
                else document.documentElement.setAttribute('data-color-scheme', mode);
                await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                return {
                    eyebrow: getComputedStyle(document.querySelector('.hero-eyebrow')).color,
                    heading: getComputedStyle(document.querySelector('h1')).color,
                    background: getComputedStyle(document.querySelector('.glee-hero-card'), '::before').backgroundColor,
                    headingSize: getComputedStyle(document.querySelector('h1')).fontSize
                };
            }""", mode)
            eyebrow = contrast(colors["eyebrow"], colors["background"])
            heading = contrast(colors["heading"], colors["background"])
            assert float(colors["headingSize"].removesuffix("px")) >= 24, "Heading threshold requires large text"
            assert eyebrow >= 4.5, f"{mode} eyebrow contrast {eyebrow:.2f}:1 is below 4.5:1"
            assert heading >= 3, f"{mode} heading contrast {heading:.2f}:1 is below 3:1"
            return {**colors, "eyebrow_ratio": eyebrow, "heading_ratio": heading}

        check("computed hero contrast " + mode, measured_colors,
              color_scheme="dark" if mode.endswith("dark") else "light")

    def svg(page, _):
        visit(page, "/toolbox/05-organized-life/05f-neighborly-bazaar/")
        dimensions = page.evaluate("""async () => {
            const image = new Image();
            image.src = '/assets/img/tool-ettes/05f-neighborly-bazaar-illustration.svg';
            await image.decode();
            return [image.naturalWidth, image.naturalHeight];
        }""")
        assert all(size > 0 for size in dimensions), dimensions
        return {"decoded_dimensions": dimensions}

    check("Neighborly Bazaar SVG decodes", svg)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:5000")
    parser.add_argument("--browser", choices=("chromium", "firefox", "webkit"), default="chromium")
    parser.add_argument("--timeout-ms", type=int, default=15000)
    parser.add_argument("--output", type=Path, help="Optional JSON evidence report")
    parser.add_argument("--screenshots", type=Path, help="Optional directory for per-journey screenshots")
    args = parser.parse_args()
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "base_url": args.base_url,
              "browser": args.browser, "service_workers": "blocked (separate resilience gate)", "results": []}
    try:
        from playwright.sync_api import expect, sync_playwright
        with sync_playwright() as playwright:
            browser = getattr(playwright, args.browser).launch(headless=True)
            try:
                report["results"] = run_checks(browser, expect, args)
            finally:
                browser.close()
    except Exception as error:
        report["results"].append({"name": "browser gate setup or execution", "status": "FAIL", "error": str(error)})
    report["failures"] = sum(item["status"] != "PASS" for item in report["results"])
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

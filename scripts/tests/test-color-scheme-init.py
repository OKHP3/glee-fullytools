#!/usr/bin/env python3
"""Prove the blocking color-scheme bootstrap prevents a theme flash.

Run against the local site server:
    python3 scripts/tests/test-color-scheme-init.py \
        --base-url http://127.0.0.1:5000 --browser chromium

The test deliberately waits only for DOMContentLoaded.  The color-scheme
script is a parser-blocking head script, so the initial DOM assertion at that
point proves the saved preference was applied before the page could render.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Callable, Literal
from urllib.parse import urljoin, urlsplit


ASSET_PATH = "/assets/js/color-scheme-init.js"
THEME_CASES = ("light", "dark", "disabled_storage")
UTILITY_ROUTES = ("/404.html", "/under-construction.html", "/offline.html")
UTILITY_RECOVERY = {
    "/404.html": ("main .btn-primary", "Return home", "/"),
    "/under-construction.html": ("main .btn-primary", "Browse live Tools", "/toolbox/"),
    "/offline.html": ("main .button-primary", "Return home", "/"),
}
UTILITY_ALTERNATE_RECOVERY = {
    "/404.html": ("main .btn-quiet", "Open the Toolbox", "/toolbox/"),
    "/under-construction.html": ("main .btn-quiet", "Return home", "/"),
    "/offline.html": (
        "main a[data-sparkle-link]",
        "🎰 The Arcade is open — play Glee-fully Chai Chasers, starring Joey & Phoebe 🦋",
        "/arcade/",
    ),
}
FirstPaintStatus = Literal["observed", "unsupported", "unavailable_after_load"]
SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from public_inventory import iter_indexable_urls, page_type  # noqa: E402


def first_party(url: str, base_url: str) -> bool:
    return urlsplit(url).netloc == urlsplit(base_url).netloc


def adapt_local_http_navigation(
    route,
    base_url: str,
) -> bool:
    """Remove only loopback CSP transport upgrades for WebKit's local fixture."""
    base = urlsplit(base_url)
    request = route.request
    target = urlsplit(request.url)
    local_http = base.scheme == "http" and base.hostname in {"localhost", "127.0.0.1"}
    if not (
        local_http
        and request.is_navigation_request()
        and target.scheme == base.scheme
        and target.netloc == base.netloc
    ):
        return False

    response = route.fetch()
    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type:
        route.fulfill(response=response)
        return True
    route.fulfill(
        response=response,
        body=response.text().replace("; upgrade-insecure-requests", ""),
    )
    return True


def load_context(browser, base_url: str, init_script: str = "", *, preference=None):
    options = {"service_workers": "block"}
    if preference is not None:
        base = urlsplit(base_url)
        # Seed storage before creating a page, independently of document scripts.
        options["storage_state"] = {"cookies": [], "origins": [{
            "origin": f"{base.scheme}://{base.netloc}",
            "localStorage": [{"name": "glee-color-scheme", "value": preference}],
        }]}
    context = browser.new_context(**options)
    if init_script:
        context.add_init_script(init_script)

    def route_request(route):
        if adapt_local_http_navigation(route, base_url):
            return
        if first_party(route.request.url, base_url):
            route.continue_()
        else:
            route.abort()

    context.route("**/*", route_request)
    return context


def bootstrap_events(
    events: list[tuple[str, str | None]],
    route: str,
    timing: dict[str, object],
) -> dict[str, object]:
    """Prove completion on the browser clock; retain protocol events as evidence."""
    request_index = next(
        (
            index
            for index, (kind, url) in enumerate(events)
            if kind == "request" and urlsplit(url or "").path == ASSET_PATH
        ),
        None,
    )
    finished_index = next(
        (
            index
            for index, (kind, url) in enumerate(events)
            if kind == "finished" and urlsplit(url or "").path == ASSET_PATH
        ),
        None,
    )
    dcl_index = next(
        (
            index
            for index, (kind, url) in enumerate(events)
            if kind == "domcontentloaded" and urlsplit(url or "").path == route
        ),
        None,
    )
    checks: list[tuple[str, Callable[[], None]]] = [
        (
            "complete bootstrap event trace",
            lambda: require_condition(
                request_index is not None
                and finished_index is not None
                and dcl_index is not None,
                f"incomplete color-scheme bootstrap event trace: {events}",
            ),
        )
    ]
    if request_index is not None and dcl_index is not None:
        checks.append(
            (
                "asset request before DOMContentLoaded",
                lambda: require_condition(
                    request_index < dcl_index,
                    "external color-scheme asset was not requested before "
                    "DOMContentLoaded",
                ),
            )
        )

    # WebKit can deliver requestfinished after its DOMContentLoaded callback.
    # Resource and navigation timing share the document's time origin, so they
    # prove actual completion independently of protocol callback delivery order.
    response_end = timing.get("asset_response_end")
    dcl_start = timing.get("domcontentloaded_start")
    checks.append(
        (
            "bootstrap timing available",
            lambda: require_condition(
                response_end is not None and dcl_start is not None,
                f"missing browser timing for color-scheme bootstrap: {timing}",
            ),
        )
    )
    if response_end is not None and dcl_start is not None:
        checks.extend(
            [
                (
                    "positive bootstrap timing",
                    lambda: require_condition(
                        response_end > 0 and dcl_start > 0,
                        f"missing browser timing for color-scheme bootstrap: {timing}",
                    ),
                ),
                (
                    "asset completion before DOMContentLoaded",
                    lambda: require_condition(
                        response_end <= dcl_start,
                        "external color-scheme asset did not finish before "
                        f"DOMContentLoaded: timing={timing}; events={events}",
                    ),
                ),
            ]
        )
    assert_independent_checks(route, checks)
    return {
        "event_order": [kind for kind, _ in events],
        "asset_request_index": request_index,
        "asset_finished_index": finished_index,
        "domcontentloaded_index": dcl_index,
        "asset_response_end": response_end,
        "domcontentloaded_start": dcl_start,
    }


def paint_timing(page) -> dict[str, float | FirstPaintStatus | None]:
    """Capture the browser's resource and first-paint timing evidence."""
    return page.evaluate(
        """assetPath => {
          const assets = performance.getEntriesByType('resource')
            .filter(entry => new URL(entry.name).pathname === assetPath);
          const asset = assets[assets.length - 1];
          const navigation = performance.getEntriesByType('navigation')[0];
          const canReadPaintEntries =
            typeof performance.getEntriesByType === 'function';
          const supportedEntryTypes =
            typeof PerformanceObserver !== 'undefined' &&
            Array.isArray(PerformanceObserver.supportedEntryTypes)
              ? PerformanceObserver.supportedEntryTypes
              : [];
          const paintTimingSupported =
            canReadPaintEntries && supportedEntryTypes.includes('paint');
          const paints = canReadPaintEntries
            ? performance.getEntriesByType('paint')
            : [];
          const firstPaint = paints.find(entry => entry.name === 'first-paint');
          return {
            asset_response_end: asset ? asset.responseEnd : null,
            domcontentloaded_start: navigation
              ? navigation.domContentLoadedEventStart : null,
            first_paint: firstPaint ? firstPaint.startTime : null,
            first_paint_status: firstPaint
              ? 'observed'
              : paintTimingSupported
                ? 'unavailable_after_load'
                : 'unsupported'
          };
        }""",
        ASSET_PATH,
    )


def assert_paint_order(
    route: str,
    timing: dict[str, float | FirstPaintStatus | None],
) -> None:
    """Require the bootstrap resource to finish before first paint when exposed."""
    status = timing["first_paint_status"]
    checks: list[tuple[str, Callable[[], None]]] = [
        (
            "recognized first-paint status",
            lambda: require_condition(
                status in {"observed", "unsupported", "unavailable_after_load"},
                f"unknown first-paint timing status: {timing}",
            ),
        )
    ]
    if status == "observed":
        first_paint = timing["first_paint"]
        response_end = timing["asset_response_end"]
        checks.extend(
            [
                (
                    "first-paint timing present",
                    lambda: require_condition(
                        first_paint is not None,
                        f"first-paint status was observed without a timing value: {timing}",
                    ),
                ),
                (
                    "asset response timing present",
                    lambda: require_condition(
                        response_end is not None,
                        "color-scheme asset has no resource timing entry despite "
                        f"first-paint being available: {timing}",
                    ),
                ),
            ]
        )
        if first_paint is not None and response_end is not None:
            checks.append(
                (
                    "asset completed before first paint",
                    lambda: require_condition(
                        response_end <= first_paint,
                        f"color-scheme asset finished after first-paint: {timing}",
                    ),
                )
            )
    elif status in {"unsupported", "unavailable_after_load"}:
        checks.append(
            (
                "first-paint value matches availability",
                lambda: require_condition(
                    timing["first_paint"] is None,
                    f"first-paint timing was present with status {status}: {timing}",
                ),
            )
        )
    assert_independent_checks(route, checks)


def public_routes() -> list[str]:
    """Return the current browser route set from the public page inventory."""
    routes = list(iter_indexable_urls())
    assert routes, "Public page inventory did not provide any browser routes"
    required_types = {"home", "toolbox_hub", "branch", "tool-ette", "supporting"}
    present_types = {page_type(route) for route in routes}
    assert required_types <= present_types, (
        "Public page inventory is missing a required route type: "
        f"expected {sorted(required_types)}, got {sorted(present_types)}"
    )
    return routes


def browser_routes() -> list[str]:
    """Return indexable routes plus approved non-indexable utility pages."""
    routes = public_routes()
    utility_routes_in_inventory = sorted(set(routes) & set(UTILITY_ROUTES))
    assert not utility_routes_in_inventory, (
        "Fallback/offline routes must remain outside the public inventory: "
        f"{utility_routes_in_inventory}"
    )
    return [*routes, *UTILITY_ROUTES]


def route_type(route: str) -> str:
    return "utility" if route in UTILITY_ROUTES else page_type(route)


class RouteCheckFailure(AssertionError):
    """Keep every failed route available to failure-only diagnostics."""

    def __init__(self, failures: list[dict[str, str]]):
        self.failed_routes = failures
        details = "; ".join(
            f"{failure['route']}: {failure['error']}" for failure in failures
        )
        super().__init__(f"Theme checks failed on {len(failures)} route(s): {details}")


def assert_independent_checks(
    route: str,
    checks: list[tuple[str, Callable[[], None]]],
) -> None:
    """Run independent assertions and report every failed check for a route."""
    failures: list[str] = []
    for name, check in checks:
        try:
            check()
        except AssertionError as error:
            failures.append(f"{name}: {error}")
    if failures:
        details = "; ".join(failures)
        raise AssertionError(
            f"{route}: {len(failures)} independent theme check(s) failed: "
            f"{details}"
        )


def require_condition(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def collect_route_evidence(routes: list[str], check) -> list[dict[str, object]]:
    """Run every route check and raise once with all route-specific failures."""
    results: list[dict[str, object]] = []
    failures: list[dict[str, str]] = []
    for route in routes:
        try:
            evidence = check(route)
            results.extend(evidence["route_evidence"])
        except Exception as error:
            failures.append({"route": route, "error": str(error)})
    if failures:
        raise RouteCheckFailure(failures)
    return results


def _check_saved_preference_context(
    browser,
    base_url: str,
    preference: str,
    routes: list[str],
) -> dict[str, object]:
    context = load_context(
        browser,
        base_url,
        preference=preference,
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
    page.on("domcontentloaded", lambda: events.append(("domcontentloaded", page.url)))

    try:
        results: list[dict[str, object]] = []
        for route in routes:
            events.clear()
            try:
                response = page.goto(
                    urljoin(base_url, route),
                    wait_until="domcontentloaded",
                )
            except Exception as error:
                raise RuntimeError(
                    f"{route}: navigation failed before theme assertions: {error}"
                ) from error
            assert response is not None and response.ok, (
                f"{route} did not load with saved {preference} preference: "
                f"{response.status if response else 'no response'}"
            )

            try:
                initial = page.evaluate(
                    """() => ({
                      scheme: document.documentElement.getAttribute('data-color-scheme'),
                      savedPreference: localStorage.getItem('glee-color-scheme'),
                      readyState: document.readyState,
                      colorSchemeScript: Boolean(document.querySelector(
                        'head > script[src*="color-scheme-init.js"]'
                      ))
                    })"""
                )
                page.wait_for_load_state("load")
                timing = paint_timing(page)
            except Exception as error:
                raise RuntimeError(
                    f"{route}: could not collect theme evidence before "
                    f"assertions: {error}"
                ) from error

            event_evidence: dict[str, object] = {}

            def check_bootstrap_events():
                event_evidence.update(bootstrap_events(events, route, timing))

            assert_independent_checks(
                route,
                [
                    (
                        "initial DOM scheme",
                        lambda: require_condition(
                            initial["scheme"] == preference,
                            f"expected saved {preference!r} preference, got {initial}",
                        ),
                    ),
                    (
                        "external color-scheme asset",
                        lambda: require_condition(
                            initial["colorSchemeScript"],
                            "page does not load the external color-scheme asset",
                        ),
                    ),
                    ("bootstrap events and timing", check_bootstrap_events),
                    ("first-paint order", lambda: assert_paint_order(route, timing)),
                ],
            )

            results.append({
                "route": route,
                "page_type": route_type(route),
                "initial_dom": initial,
                "bootstrap_events": event_evidence,
                "timing": timing,
            })

        return {
            "routes": len(results),
            "page_types": dict(Counter(result["page_type"] for result in results)),
            "route_evidence": results,
        }
    finally:
        context.close()


def storage_error_name(page) -> str:
    """Confirm the denied-storage fixture remains active across navigation."""
    return page.evaluate(
        """() => {
          try { void window.localStorage; return 'accessible'; }
          catch (error) { return error.name; }
        }"""
    )


def link_traversal_key(context) -> str:
    """Verify link traversal on a separate page, independent of recovery targets.

    Mac WebKit follows the host's keyboard-navigation preference: plain Tab
    can skip links while Option+Tab includes them. Never retry a failed target
    with another key; doing so could conceal an actual focus regression.
    """
    probe = context.new_page()
    try:
        probe.set_content(
            '<button id="before">Before</button>'
            '<a id="link" href="#destination">Link</a><button>After</button>'
        )
        for key in ("Tab", "Alt+Tab"):
            # Focus only the synthetic starting button, never a recovery action.
            probe.locator("#before").focus()
            probe.keyboard.press(key)
            if probe.evaluate("() => document.activeElement.id === 'link'"):
                return key
        raise AssertionError("browser has no verified link traversal key")
    finally:
        probe.close()


def _run_recovery_check(failures: list[str], name: str, check) -> None:
    try:
        check()
    except AssertionError as error:
        failures.append(f"{name}: {error}")


def _raise_recovery_failures(route: str, failures: list[str]) -> None:
    if failures:
        details = "; ".join(failures)
        raise AssertionError(
            f"{route}: {len(failures)} independent keyboard recovery "
            f"check(s) failed: {details}"
        )


def check_utility_recovery(
    page, base_url: str, route: str, page_errors, *, alternate: bool = False,
) -> dict:
    """Tab to a recovery action and activate it without mouse or focus()."""
    actions = UTILITY_ALTERNATE_RECOVERY if alternate else UTILITY_RECOVERY
    selector, label, destination = actions[route]
    action_kind = "alternate" if alternate else "primary"
    action = page.locator(selector)
    if action.count() != 1 or not action.is_visible():
        raise AssertionError(
            f"{route}: expected one visible {action_kind} recovery action"
        )
    if storage_error_name(page) != "SecurityError":
        raise AssertionError(
            f"{route}: storage was not blocked before keyboard recovery"
        )
    try:
        tab_key = link_traversal_key(page.context)
    except Exception as error:
        raise AssertionError(
            f"{route}: could not set up keyboard recovery: {error}"
        ) from error

    failures: list[str] = []
    _run_recovery_check(
        failures,
        f"{action_kind} recovery label",
        lambda: require_condition(
            action.inner_text().strip() == label,
            f"{route}: {action_kind} recovery action no longer says {label!r}",
        ),
    )
    expected_url = urljoin(base_url, destination)
    _run_recovery_check(
        failures,
        f"{action_kind} recovery destination",
        lambda: require_condition(
            action.evaluate("element => element.href") == expected_url,
            f"{route}: recovery action must point to {destination}",
        ),
    )

    # Bounded real keyboard traversal catches tabindex=-1, inert, and focus traps.
    for tab_count in range(1, 101):
        page.keyboard.press(tab_key)
        if action.evaluate("element => element === document.activeElement"):
            break
    else:
        failures.append(
            f"keyboard reachability: {route}: recovery action was not reachable "
            f"with {tab_key}"
        )
        _raise_recovery_failures(route, failures)

    try:
        with page.expect_navigation(wait_until="load") as navigation:
            page.keyboard.press("Enter")
        response = navigation.value
    except Exception as error:
        failures.append(f"keyboard navigation: {route}: keyboard recovery failed: {error}")
        _raise_recovery_failures(route, failures)

    navigation_failed = False
    if response is None or not response.ok:
        failures.append(
            f"keyboard navigation: {route}: keyboard recovery failed: "
            f"{response.status if response else 'no response'}"
        )
        navigation_failed = True
    if page.url != expected_url:
        failures.append(
            f"keyboard destination: {route}: recovery reached {page.url}, "
            f"expected {expected_url}"
        )
        navigation_failed = True
    if navigation_failed:
        _raise_recovery_failures(route, failures)

    _run_recovery_check(
        failures,
        "destination primary content",
        lambda: require_condition(
            page.locator("h1").is_visible(),
            f"{route}: recovery destination has no visible primary content",
        ),
    )
    _run_recovery_check(
        failures,
        "destination storage denial",
        lambda: require_condition(
            storage_error_name(page) == "SecurityError",
            f"{route}: storage denial did not persist on the recovery destination",
        ),
    )
    _run_recovery_check(
        failures,
        "page errors",
        lambda: require_condition(
            not page_errors,
            f"{route}: page errors during keyboard recovery: {page_errors}",
        ),
    )
    _raise_recovery_failures(route, failures)
    return {
        "action": label,
        "destination": destination,
        "keyboard_reachable": True,
        "tab_presses": tab_count,
        "traversal_key": tab_key,
        "activation_key": "Enter",
        "destination_status": response.status,
        "destination_h1_visible": True,
        "storage_error": "SecurityError",
        "page_errors": [],
    }


def _check_disabled_storage_context(
    browser,
    base_url: str,
    routes: list[str],
) -> dict[str, object]:
    context = load_context(
        browser,
        base_url,
        """Object.defineProperty(window, 'localStorage', {
          configurable: false,
          get() { throw new DOMException('Storage denied', 'SecurityError'); }
        });""",
    )
    page = context.new_page()
    events: list[tuple[str, str | None]] = []
    page_errors: list[str] = []
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
    page.on("domcontentloaded", lambda: events.append(("domcontentloaded", page.url)))
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    try:
        results: list[dict[str, object]] = []
        for route in routes:
            events.clear()
            page_errors.clear()
            try:
                response = page.goto(
                    urljoin(base_url, route),
                    wait_until="domcontentloaded",
                )
            except Exception as error:
                raise RuntimeError(
                    f"{route}: navigation failed before theme assertions: {error}"
                ) from error
            assert response is not None and response.ok, (
                f"{route} failed when storage was disabled: "
                f"{response.status if response else 'no response'}"
            )
            try:
                h1_visible = page.locator("h1").is_visible()
                color_toggle_visible = (
                    page.locator(".glee-color-toggle").is_visible()
                    if route == "/" else None
                )
                page_errors_before_load = list(page_errors)
                initial = page.evaluate(
                    """() => ({
                      scheme: document.documentElement.getAttribute('data-color-scheme'),
                      readyState: document.readyState,
                      colorSchemeScript: Boolean(document.querySelector(
                        'head > script[src*="color-scheme-init.js"]'
                      ))
                    })"""
                )
                page.wait_for_load_state("load")
                timing = paint_timing(page)
            except Exception as error:
                raise RuntimeError(
                    f"{route}: could not collect disabled-storage theme "
                    f"evidence before assertions: {error}"
                ) from error

            event_evidence: dict[str, object] = {}

            def check_bootstrap_events():
                event_evidence.update(bootstrap_events(events, route, timing))

            checks: list[tuple[str, Callable[[], None]]] = [
                (
                    "visible primary content",
                    lambda: require_condition(
                        h1_visible,
                        "page did not retain visible primary content with disabled storage",
                    ),
                ),
                (
                    "page errors before load",
                    lambda: require_condition(
                        not page_errors_before_load,
                        "page raised errors with disabled storage before load: "
                        f"{page_errors_before_load}",
                    ),
                ),
                (
                    "page errors after load",
                    lambda: require_condition(
                        not page_errors,
                        f"page raised errors after load with disabled storage: "
                        f"{page_errors}",
                    ),
                ),
                (
                    "DOMContentLoaded readiness",
                    lambda: require_condition(
                        initial["readyState"] in {"interactive", "complete"},
                        f"page did not reach DOMContentLoaded: {initial}",
                    ),
                ),
                ("bootstrap events and timing", check_bootstrap_events),
                ("first-paint order", lambda: assert_paint_order(route, timing)),
            ]
            if route == "/":
                checks.append(
                    (
                        "usable Glee color control",
                        lambda: require_condition(
                            color_toggle_visible,
                            "Glee color control did not remain usable with disabled storage",
                        ),
                    )
                )
            assert_independent_checks(route, checks)
            recovery = (
                check_utility_recovery(page, base_url, route, page_errors)
                if route in UTILITY_ROUTES else None
            )
            alternate_recovery = None
            if route in UTILITY_ROUTES:
                # Return to the source with fresh document focus; the primary
                # action already navigated away. Keep the same denied-storage
                # context and error listener active for the entire recovery flow.
                response = page.goto(urljoin(base_url, route), wait_until="load")
                assert response is not None and response.ok, (
                    f"{route}: could not reload for alternate keyboard recovery"
                )
                alternate_recovery = check_utility_recovery(
                    page, base_url, route, page_errors, alternate=True,
                )
            results.append({
                "route": route,
                "page_type": route_type(route),
                "h1_visible": True,
                "page_errors": [],
                "initial_dom": initial,
                "bootstrap_events": event_evidence,
                "timing": timing,
                **({"recovery": recovery} if recovery is not None else {}),
                **({"alternate_recovery": alternate_recovery}
                   if alternate_recovery is not None else {}),
            })
        return {
            "routes": len(results),
            "page_types": dict(Counter(result["page_type"] for result in results)),
            "color_toggle_visible": True,
            "route_evidence": results,
        }
    finally:
        context.close()


def check_saved_preference(browser, base_url, preference, routes):
    # WebKit intermittently lost the seeded storage during consecutive
    # navigations in one context. Each URL needs its own saved-state fixture
    # and navigation events; cross-page behavior has a separate acceptance suite.
    results = collect_route_evidence(
        routes,
        lambda route: _check_saved_preference_context(
            browser, base_url, preference, [route]
        ),
    )
    return {
        "routes": len(results),
        "page_types": dict(Counter(result["page_type"] for result in results)),
        "route_evidence": results,
    }


def check_disabled_storage(browser, base_url, routes):
    results = collect_route_evidence(
        routes,
        lambda route: _check_disabled_storage_context(browser, base_url, [route]),
    )
    return {
        "routes": len(results),
        "page_types": dict(Counter(result["page_type"] for result in results)),
        "color_toggle_visible": True,
        "route_evidence": results,
    }


def capture_case(report: dict[str, object], name: str, check) -> None:
    """Keep completed cases and mark a failing case for diagnostic summaries."""
    try:
        result = check()
    except Exception as error:
        report["diagnostic_only"] = True
        report["failure_stage"] = "theme_check"
        report["failed_case"] = name
        if name in THEME_CASES:
            report["not_run_cases"] = list(
                THEME_CASES[THEME_CASES.index(name) + 1:]
            )
        failed_routes = getattr(error, "failed_routes", None)
        if isinstance(failed_routes, list):
            report["failed_routes"] = failed_routes
        report["error"] = str(error)
        raise

    cases = report.setdefault("cases", {})
    if not isinstance(cases, dict):
        raise TypeError("Browser report cases must be an object")
    cases[name] = result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    parser.add_argument(
        "--browser",
        choices=("chromium", "firefox", "webkit"),
        default="chromium",
        help="Playwright engine to exercise.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON evidence report path.",
    )
    parser.add_argument(
        "--executable-path",
        default=os.environ.get("PLAYWRIGHT_EXECUTABLE_PATH"),
        help="Optional browser binary path for local runners.",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/") + "/"
    report: dict[str, object] = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "browser": args.browser,
        "cases": {},
        "failure_stage": "browser_startup",
        "setup_step": "loading_playwright",
    }
    try:
        from playwright.sync_api import sync_playwright

        report["setup_step"] = "preparing_routes"
        routes = browser_routes()
        report["route_count"] = len(routes)
        report["setup_step"] = "entering_browser_manager"
        with sync_playwright() as playwright:
            report["setup_step"] = "launching_browser"
            launch_options = {"headless": True}
            if args.executable_path:
                launch_options["executable_path"] = args.executable_path
            browser = getattr(playwright, args.browser).launch(**launch_options)
            report["browser_version"] = browser.version
            report.pop("setup_step", None)
            report["failure_stage"] = "theme_checks"
            try:
                for preference in THEME_CASES[:2]:
                    capture_case(
                        report,
                        preference,
                        lambda preference=preference: check_saved_preference(
                            browser, base_url, preference, routes
                        ),
                    )
                capture_case(
                    report,
                    THEME_CASES[2],
                    lambda: check_disabled_storage(
                        browser, base_url, ["/", *UTILITY_ROUTES]
                    ),
                )
            finally:
                try:
                    browser.close()
                except Exception as cleanup_error:
                    if report.get("failure_stage") == "theme_check":
                        report["cleanup_error"] = str(cleanup_error)
                    else:
                        report["failure_stage"] = "browser_cleanup"
                        report["error"] = str(cleanup_error)
                    raise
        report["status"] = "PASS"
    except Exception as error:
        report["status"] = "FAIL"
        report["diagnostic_only"] = True
        report.setdefault("failure_stage", "browser_startup")
        report.setdefault("error", str(error))
        report.setdefault(
            "not_run_cases",
            [
                name
                for name in THEME_CASES
                if name not in report.get("cases", {})
                and name != report.get("failed_case")
            ],
        )

    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    if report["status"] == "PASS":
        print("Color-scheme bootstrap browser regression passed.")
        return
    raise SystemExit(1)


if __name__ == "__main__":
    main()

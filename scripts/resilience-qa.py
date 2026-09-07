#!/usr/bin/env python3
"""
resilience-qa.py  -  installability, offline, browser, crawler, and dependency QA
===============================================================================

This is the executable acceptance check for docs/resilience.md.  It deliberately
keeps the product boundary visible:

* static checks use Python's HTML parser and never execute page JavaScript;
* browser checks cover Chromium, Firefox, and WebKit;
* only same-origin resources are expected to survive an offline navigation;
* third-party requests are blocked in a separate browser journey and must not
  hide first-party navigation or content.

Usage:
    python3 scripts/resilience-qa.py
    python3 scripts/resilience-qa.py --static-only
    python3 scripts/resilience-qa.py --base-url http://localhost:5000

The report is written to assets/audit/resilience-qa-YYYY-MM-DD.json.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import socket
import subprocess
import sys
import time
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
REPORT_DATE = date.today().isoformat()
REPORT_PATH = ROOT / "assets" / "audit" / f"resilience-qa-{REPORT_DATE}.json"
SITE_ORIGIN = "https://glee-fully.tools"

# These routes intentionally span the public surface, not just the precache.
ROUTES = [
    ("core", "/"),
    ("branch", "/toolbox/01-discovered-careers/"),
    ("tool-ette", "/toolbox/01-discovered-careers/01a-resume-builder/"),
    ("search", "/search/"),
    ("utility", "/offline.html"),
]
ONLINE_NAVIGATION_ROUTES = [path for _, path in ROUTES if path != "/offline.html"]
CRAWLER_ROUTES = [
    (kind, path) for kind, path in ROUTES if path != "/offline.html"
] + [("utility", "/404.html"), ("utility", "/offline.html")]

REQUIRED_MANIFEST = {
    "name": "Glee-fully Personalizable Tools™",
    "short_name": "Glee-fully",
    "start_url": "/",
    "scope": "/",
    "display": "standalone",
}
REQUIRED_PRECACHE_ROUTES = {"/", "/search/", "/toolbox/", "/about/", "/offline.html"}
THIRD_PARTY_MARKERS = (
    "googletagmanager.com",
    "google-analytics.com",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "ko-fi.com",
    "okhp3.github.io",
    "chatgpt.com",
)
CHROMIUM_ARGS = [
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


def ensure_browser_runtime() -> None:
    """Reuse the verified libgbm/Playwright setup used by viewport QA."""
    if not os.environ.get("REPL_ID"):
        return
    helper_path = ROOT / "scripts" / "run-viewport-qa.py"
    spec = importlib.util.spec_from_file_location("_viewport_qa_runtime", helper_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load scripts/run-viewport-qa.py runtime setup")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.ensure_stub()


class StaticPageParser(HTMLParser):
    """Collect only crawler-visible HTML; no scripts or browser APIs involved."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.h1 = ""
        self.meta: dict[tuple[str, str], str] = {}
        self._in_title = False
        self._in_h1 = False
        self._title_parts: list[str] = []
        self._h1_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs_list) -> None:
        attrs = {key.lower(): (value or "") for key, value in attrs_list}
        tag = tag.lower()
        if tag == "title":
            self._in_title = True
        elif tag == "h1":
            self._in_h1 = True
        elif tag == "meta":
            key = attrs.get("name") or attrs.get("property")
            if key:
                self.meta[(("name" if attrs.get("name") else "property"), key)] = attrs.get(
                    "content", ""
                )

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
            self.title = "".join(self._title_parts).strip()
        elif tag == "h1":
            self._in_h1 = False
            self.h1 = "".join(self._h1_parts).strip()

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)
        if self._in_h1:
            self._h1_parts.append(data)


def route_file(route: str) -> Path:
    clean = route.split("?", 1)[0].split("#", 1)[0]
    if clean == "/":
        return ROOT / "index.html"
    if clean.endswith("/"):
        return ROOT / clean.lstrip("/") / "index.html"
    return ROOT / clean.lstrip("/")


def get_meta(parser: StaticPageParser, attr: str, value: str) -> str:
    return parser.meta.get((attr, value), "")


def static_checks() -> tuple[list[dict], list[str]]:
    """Check installability and crawler-visible metadata without executing JS."""
    results: list[dict] = []
    failures: list[str] = []

    manifest_path = ROOT / "site.webmanifest"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        failures.append(f"manifest cannot be parsed: {exc}")
        manifest = {}

    for key, expected in REQUIRED_MANIFEST.items():
        if manifest.get(key) != expected:
            failures.append(
                f"manifest {key!r} is {manifest.get(key)!r}; expected {expected!r}"
            )
    if not isinstance(manifest.get("icons"), list) or not manifest["icons"]:
        failures.append("manifest has no icons")
    else:
        for icon in manifest["icons"]:
            src = icon.get("src", "")
            if not src or not (ROOT / src.lstrip("/")).is_file():
                failures.append(f"manifest icon is missing: {src!r}")

    worker_text = (ROOT / "sw.js").read_text(encoding="utf-8", errors="replace")
    cache_match = re.search(
        r'CACHE_NAME\s*=\s*["\'](glee-fully-shell-v\d+)["\']', worker_text
    )
    if not cache_match:
        failures.append("service worker cache name is not versioned")
    precache_match = re.search(
        r"const\s+PRECACHE_URLS\s*=\s*\[(.*?)\];", worker_text, re.DOTALL
    )
    precache = (
        re.findall(r'["\']([^"\']+)["\']', precache_match.group(1))
        if precache_match
        else []
    )
    if not precache_match:
        failures.append("service worker has no PRECACHE_URLS list")
    for route in sorted(REQUIRED_PRECACHE_ROUTES - set(precache)):
        failures.append(f"service worker precache is missing {route}")
    external_precache = [
        url for url in precache if url.startswith(("http://", "https://", "//"))
    ]
    if external_precache:
        failures.append(f"service worker precaches third-party URLs: {external_precache}")
    registration_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in (
            ROOT / "assets/js/app.js",
            ROOT / "assets/js/glee-site-enhancements.js",
        )
        if path.is_file()
    )
    if 'scope: "/"' not in registration_text:
        failures.append("service-worker registration is not root scoped")

    for kind, route in CRAWLER_ROUTES:
        path = route_file(route)
        item = {"kind": kind, "route": route, "file": path.relative_to(ROOT).as_posix()}
        if not path.is_file():
            failures.append(f"{route}: source file is missing")
            results.append({**item, "ok": False, "issues": ["source file is missing"]})
            continue

        parser = StaticPageParser()
        parser.feed(path.read_text(encoding="utf-8", errors="replace"))
        issues = []
        if not parser.title:
            issues.append("missing crawler-visible title")
        if not parser.h1:
            issues.append("missing crawler-visible h1")
        if not get_meta(parser, "name", "description"):
            issues.append("missing crawler-visible description")
        canonical = re.search(
            r'<link\s+rel=["\']canonical["\']\s+href=["\']([^"\']+)',
            path.read_text(encoding="utf-8", errors="replace"),
            re.IGNORECASE,
        )
        if not canonical:
            issues.append("missing canonical URL")
        if route not in ("/404.html", "/offline.html"):
            if not get_meta(parser, "property", "og:url"):
                issues.append("missing og:url")
            if not get_meta(parser, "property", "og:image"):
                issues.append("missing og:image")
            if get_meta(parser, "name", "twitter:card") != "summary_large_image":
                issues.append("missing summary_large_image Twitter card")
        if issues:
            failures.extend(f"{route}: {issue}" for issue in issues)
        results.append({**item, "ok": not issues, "title": parser.title, "h1": parser.h1, "issues": issues})

    results.append(
        {
            "kind": "installability",
            "route": "/site.webmanifest",
            "ok": not failures,
            "manifest": {
                key: manifest.get(key) for key in REQUIRED_MANIFEST
            },
            "icon_count": len(manifest.get("icons", [])),
            "service_worker_cache": cache_match.group(1) if cache_match else None,
            "precache_count": len(precache),
        }
    )
    return results, failures


def wait_for_control(page) -> None:
    """A first navigation registers the worker; reload establishes control."""
    try:
        page.wait_for_function(
            "() => navigator.serviceWorker && navigator.serviceWorker.ready",
            timeout=5000,
        )
        page.reload(wait_until="domcontentloaded", timeout=15000)
        page.wait_for_function(
            "() => !!navigator.serviceWorker.controller",
            timeout=8000,
        )
    except Exception:
        # Browser journeys remain useful even where a browser declines SW on
        # localhost; the dedicated Chromium lifecycle check reports that gap.
        pass


def start_lifecycle_server(port: int | None = None) -> tuple[subprocess.Popen, str]:
    """Start an isolated copy of the no-cache server for offline testing."""
    if port is None:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
    env = os.environ.copy()
    env["PORT"] = str(port)
    process = subprocess.Popen(
        [sys.executable, str(ROOT / "scripts" / "serve-site.py")],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    import urllib.request

    for _ in range(30):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=0.5):
                return process, f"http://127.0.0.1:{port}"
        except Exception:
            time.sleep(0.1)
    process.terminate()
    process.wait(timeout=3)
    detail = process.stderr.read() if process.stderr else ""
    raise RuntimeError(f"isolated lifecycle server did not start: {detail[:160]}")


def stop_lifecycle_server(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)


def goto_assert_first_party(page, base_url: str, route: str, label: str) -> dict:
    response = page.goto(
        base_url.rstrip("/") + route, wait_until="domcontentloaded", timeout=15000
    )
    status = response.status if response else 0
    page.wait_for_function("""() => [...document.styleSheets].some(sheet => {
      try { return sheet.href && sheet.href.includes('/assets/css/theme.css') && sheet.cssRules.length > 0; }
      catch (_) { return false; }
    })""", timeout=15000)
    page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
    heading = page.locator("h1").first.text_content(timeout=5000).strip()
    viewport = page.evaluate(
        """() => ({
          width: window.innerWidth,
          scrollWidth: Math.max(document.body.scrollWidth, document.documentElement.scrollWidth),
          headingVisible: !!document.querySelector('h1')
        })"""
    )
    issues = []
    if status >= 400 or status == 0:
        issues.append(f"HTTP {status}")
    if not heading:
        issues.append("no visible h1")
    if viewport["scrollWidth"] > viewport["width"] + 4:
        issues.append(f"horizontal overflow +{viewport['scrollWidth'] - viewport['width']}px")
    return {
        "label": label,
        "route": route,
        "status": status,
        "heading": heading,
        "viewport": viewport,
        "issues": issues,
    }


def browser_journeys(base_url: str, browser_names: list[str]) -> tuple[list[dict], list[str]]:
    """Run essential navigation, manifest, zoom, and failed-dependency journeys."""
    from playwright.sync_api import sync_playwright

    results: list[dict] = []
    failures: list[str] = []
    base_origin = urlparse(base_url).netloc
    local_http = urlparse(base_url).scheme == "http" and urlparse(base_url).hostname in {"localhost", "127.0.0.1"}

    def serve_test_route(route) -> None:
        # WebKit upgrades even loopback HTTP under the production CSP. Remove
        # only that transport directive from local test documents; keep all
        # resource allowlists and the shipped HTML unchanged.
        if local_http and route.request.is_navigation_request() and urlparse(route.request.url).netloc == base_origin:
            response = route.fetch()
            if "text/html" in response.headers.get("content-type", ""):
                route.fulfill(response=response, body=response.text().replace("; upgrade-insecure-requests", ""))
            else:
                route.fulfill(response=response)
        else:
            route.continue_()

    with sync_playwright() as pw:
        for browser_name in browser_names:
            browser_type = getattr(pw, browser_name)
            try:
                browser = browser_type.launch(
                    headless=True, args=CHROMIUM_ARGS if browser_name == "chromium" else None
                )
            except Exception as exc:
                failures.append(f"{browser_name}: browser unavailable: {str(exc)[:160]}")
                results.append({"browser": browser_name, "ok": False, "error": str(exc)[:240]})
                continue

            browser_result = {"browser": browser_name, "ok": True, "journeys": []}
            context = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
            context.route("**/*", serve_test_route)
            page = context.new_page()
            page_errors: list[str] = []
            page.on("pageerror", lambda exc: page_errors.append(str(exc)[:160]))
            try:
                for kind, route in ROUTES[:4]:
                    item = goto_assert_first_party(page, base_url, route, f"{kind} navigation")
                    browser_result["journeys"].append(item)
                    if item["issues"]:
                        failures.extend(f"{browser_name} {route}: {issue}" for issue in item["issues"])

                manifest = page.evaluate(
                    """async () => {
                      const response = await fetch('/site.webmanifest');
                      return {status: response.status, data: await response.json()};
                    }"""
                )
                if manifest["status"] != 200:
                    failures.append(f"{browser_name}: manifest HTTP {manifest['status']}")
                for key, expected in REQUIRED_MANIFEST.items():
                    if manifest["data"].get(key) != expected:
                        failures.append(f"{browser_name}: manifest {key} mismatch")

                # 200% style zoom is a deterministic proxy for a user zooming
                # the page; essential first-party content must remain present.
                zoom = page.evaluate(
                    """() => {
                      document.documentElement.style.zoom = '2';
                      const h1 = document.querySelector('h1');
                      return {heading: h1 && h1.textContent.trim(), visible: !!(h1 && h1.getBoundingClientRect().height)};
                    }"""
                )
                browser_result["journeys"].append({"label": "200% zoom", **zoom})
                if not zoom["visible"] or not zoom["heading"]:
                    failures.append(f"{browser_name}: essential heading missing at 200% zoom")
                page.evaluate("document.documentElement.style.zoom = ''")

                # Block every cross-origin request. The first-party shell must
                # still render, while the Arcade's direct-link fallback appears
                # after its documented timeout.
                blocked: list[str] = []
                blocked_context = browser.new_context(viewport={"width": 1280, "height": 800}, service_workers="block")
                blocked_context.add_init_script(
                    "localStorage.setItem('glee-analytics-consent', 'granted')"
                )

                def block_external(route) -> None:
                    target = urlparse(route.request.url)
                    if target.netloc and target.netloc != base_origin:
                        blocked.append(target.netloc)
                        route.abort()
                    else:
                        serve_test_route(route)

                blocked_context.route("**/*", block_external)
                blocked_page = blocked_context.new_page()
                failure_item = goto_assert_first_party(
                    blocked_page, base_url, "/arcade/", "third-party failure"
                )
                time.sleep(8.4)
                fallback = blocked_page.locator("#arcade-preview-fallback:not([hidden])").count()
                failure_item["blocked_origins"] = sorted(set(blocked))
                failure_item["fallback_visible"] = fallback > 0
                failure_item["ko_fi_link_present"] = (
                    blocked_page.locator('a[href*="ko-fi.com"]').count() > 0
                )
                failure_item["first_party_nav_present"] = (
                    blocked_page.locator("nav").count() > 0
                    and blocked_page.locator("nav").first.is_visible()
                )
                browser_result["journeys"].append(failure_item)
                if failure_item["issues"]:
                    failures.extend(
                        f"{browser_name} third-party failure: {issue}"
                        for issue in failure_item["issues"]
                    )
                if not failure_item["fallback_visible"]:
                    failures.append(
                        f"{browser_name}: Arcade direct-link fallback did not appear after blocked embed"
                    )
                if not failure_item["ko_fi_link_present"]:
                    failures.append(f"{browser_name}: Ko-fi outbound link disappeared under dependency failure")
                if not failure_item["first_party_nav_present"]:
                    failures.append(f"{browser_name}: first-party navigation disappeared under dependency failure")
                if not any("googletagmanager.com" in origin for origin in blocked):
                    failures.append(
                        f"{browser_name}: opted-in analytics request was not observed and blocked"
                    )
                blocked_context.close()
            except Exception as exc:
                browser_result["ok"] = False
                failures.append(f"{browser_name}: browser journey error: {str(exc)[:180]}")
            finally:
                if page_errors:
                    browser_result["page_errors"] = page_errors
                    failures.extend(f"{browser_name}: page error: {error}" for error in page_errors)
                context.close()
                browser.close()

            browser_result["ok"] = not any(
                failure.startswith(f"{browser_name}:") or failure.startswith(f"{browser_name} ")
                for failure in failures
            )
            results.append(browser_result)
    return results, failures


def chromium_lifecycle(base_url: str) -> tuple[dict, list[str]]:
    """Prove warm/offline/reconnect behavior and stale-cache cleanup in Chromium."""
    from playwright.sync_api import sync_playwright

    result: dict = {"browser": "chromium", "journeys": []}
    failures: list[str] = []
    isolated_server = None
    lifecycle_url = base_url
    parsed_base = urlparse(base_url)
    if parsed_base.hostname in {"localhost", "127.0.0.1"}:
        isolated_server, lifecycle_url = start_lifecycle_server()
    lifecycle_port = urlparse(lifecycle_url).port
    result["lifecycle_base_url"] = lifecycle_url

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=True, args=CHROMIUM_ARGS)
        except Exception as exc:
            stop_lifecycle_server(isolated_server)
            return {"browser": "chromium", "ok": False, "error": str(exc)}, [
                f"chromium lifecycle: browser unavailable: {str(exc)[:160]}"
            ]
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        try:
            # Seed a prior shell before the page's load event registers the
            # current worker. Activation must remove this cache.
            page.goto(
                lifecycle_url + "/offline.html",
                wait_until="commit",
                timeout=15000,
            )
            seeded = page.evaluate(
                """async () => {
                  const cache = await caches.open('glee-fully-shell-v0');
                  await cache.put('/resilience-stale-cache-seed', new Response('stale'));
                  return true;
                }"""
                )
            result["stale_cache_seeded"] = seeded
            if not seeded:
                failures.append("chromium lifecycle: could not seed stale shell cache")

            # Online first visit + repeat visit warms navigation caches.
            for route in ONLINE_NAVIGATION_ROUTES:
                result["journeys"].append(
                    goto_assert_first_party(page, lifecycle_url, route, f"online warm {route}")
                )
            result["journeys"].append(
                goto_assert_first_party(page, lifecycle_url, "/", "online repeat /")
            )
            wait_for_control(page)
            warmed_headings = {}
            for route in ONLINE_NAVIGATION_ROUTES:
                item = goto_assert_first_party(page, lifecycle_url, route, "controlled warm")
                warmed_headings[route] = item["heading"]
            cache_state = page.evaluate(
                """async () => ({
                  controller: !!navigator.serviceWorker.controller,
                  keys: await caches.keys(),
                  entries: (await caches.keys()).length
                })"""
            )
            result["cache_after_warm"] = cache_state
            if not cache_state["controller"]:
                failures.append("chromium lifecycle: page is not controlled by service worker")
            if not any(key.startswith("glee-fully-shell-v") for key in cache_state["keys"]):
                failures.append("chromium lifecycle: versioned shell cache was not created")
            if "glee-fully-shell-v0" in cache_state["keys"]:
                failures.append("chromium lifecycle: stale shell cache was not deleted on activation")
            result["stale_cache_removed"] = "glee-fully-shell-v0" not in cache_state["keys"]

            context.set_offline(True)
            # Playwright's offline emulation can leave an already-open
            # localhost server reachable to service-worker fetches. Stopping
            # this isolated server makes the network failure unambiguous.
            stop_lifecycle_server(isolated_server)
            isolated_server = None
            for route in ONLINE_NAVIGATION_ROUTES:
                try:
                    item = goto_assert_first_party(page, lifecycle_url, route, f"offline {route}")
                    if item["heading"] != warmed_headings[route]:
                        item["issues"].append("visited page was replaced by the generic offline fallback")
                except Exception as exc:
                    item = {"route": route, "issues": [f"navigation error: {str(exc)[:120]}"]}
                result["journeys"].append(item)
                failures.extend(f"offline {route}: {issue}" for issue in item["issues"])
            try:
                item = goto_assert_first_party(
                    page, lifecycle_url, "/not-cached-by-resilience-qa/", "offline fallback"
                )
            except Exception as exc:
                item = {"route": "/not-cached-by-resilience-qa/", "issues": [str(exc)[:120]]}
            result["journeys"].append(item)
            if "offline" not in (item.get("heading") or "").lower():
                failures.append("chromium lifecycle: unknown offline route did not show offline fallback")

            isolated_server, lifecycle_url = start_lifecycle_server(lifecycle_port)
            context.set_offline(False)
            reconnect = goto_assert_first_party(page, lifecycle_url, "/", "reconnect")
            result["journeys"].append(reconnect)
            failures.extend(f"reconnect: {issue}" for issue in reconnect["issues"])
            cache_update = page.evaluate(
                """async () => {
                  const names = await caches.keys();
                  const shell = names.find((key) => key.startsWith('glee-fully-shell-v'));
                  const cached = shell ? await caches.open(shell).then((cache) => cache.match('/')) : null;
                  return {shell, cachedStatus: cached ? cached.status : 0, cached: !!cached};
                }"""
            )
            result["cache_after_reconnect"] = cache_update
            if not cache_update["cached"] or cache_update["cachedStatus"] != 200:
                failures.append("chromium lifecycle: reconnect did not leave an updated home cache entry")

            # Keep a source-level check alongside the runtime seed so a future
            # refactor cannot remove activation cleanup while a warm cache masks it.
            worker_source = (ROOT / "sw.js").read_text(encoding="utf-8", errors="replace")
            if (
                "caches.delete(key)" not in worker_source
                or "self.clients.claim()" not in worker_source
                or "cache.put(request, copy)" not in worker_source
            ):
                failures.append("chromium lifecycle: stale-cache activation cleanup is incomplete")
            result["cache_update_source_check"] = True
        finally:
            context.close()
            browser.close()
            stop_lifecycle_server(isolated_server)
    result["ok"] = not failures
    return result, failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Prove resilient web behavior")
    parser.add_argument("--base-url", default="http://localhost:5000")
    parser.add_argument("--static-only", action="store_true")
    parser.add_argument(
        "--browsers",
        default="chromium,firefox,webkit",
        help="comma-separated Playwright engines (default: chromium,firefox,webkit)",
    )
    args = parser.parse_args()

    static_results, failures = static_checks()
    report: dict = {
        "date": REPORT_DATE,
        "base_url": args.base_url,
        "contract": "docs/resilience.md",
        "static_checks": static_results,
        "browser_checks": [],
        "lifecycle_check": None,
        "failures": failures[:],
    }
    print(f"Static resilience checks: {'PASS' if not failures else 'FAIL'}")
    for failure in failures:
        print(f"  ! {failure}")

    if not args.static_only:
        ensure_browser_runtime()
        names = [name.strip() for name in args.browsers.split(",") if name.strip()]
        browser_results, browser_failures = browser_journeys(args.base_url, names)
        lifecycle_result, lifecycle_failures = chromium_lifecycle(args.base_url)
        report["browser_checks"] = browser_results
        report["lifecycle_check"] = lifecycle_result
        report["failures"].extend(browser_failures)
        report["failures"].extend(lifecycle_failures)
        print(f"Browser resilience checks: {'PASS' if not browser_failures else 'FAIL'}")
        print(f"Chromium lifecycle checks: {'PASS' if not lifecycle_failures else 'FAIL'}")

    report["ok"] = not report["failures"]
    report["mode"] = "static-only" if args.static_only else "full"
    report["failure_count"] = len(report["failures"])
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Report: {REPORT_PATH.relative_to(ROOT)}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

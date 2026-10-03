"""Cross-consumer regressions for discovery routes versus HTML links."""
import importlib.util
import json
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from public_inventory import derive_url
from public_paths import discovery_path, link_target


def load_script(name):
    spec = importlib.util.spec_from_file_location(
        name.replace("-", "_"), SCRIPTS / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AUDIT = load_script("audit-site")
COVERAGE = load_script("check-search-coverage")
RESILIENCE = load_script("resilience-qa")
LINKS = load_script("check-links")
ORIGIN = "https://glee-fully.tools"


class PublicPathTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name) / "site"
        self.root.mkdir()
        self.files = [
            "index.html", "about/index.html", "about/child/index.html",
            "café/index.html", "standalone.html", "about/standalone.html",
            "assets/style.css", "extensionless",
        ]
        for relative in self.files:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('<h1 id="section">Test</h1>', encoding="utf-8")
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for module in (AUDIT, RESILIENCE, LINKS):
            self.stack.enter_context(patch.object(module, "ROOT", self.root))

    def assert_consumers(self, route, relative):
        """Same-origin canonical routes are the overlap of all four contracts."""
        url = ORIGIN + route
        expected = Path(relative)
        self.assertEqual(AUDIT.url_to_relpath(url), relative)
        self.assertEqual(COVERAGE._path_for_url(url, ORIGIN, self.root), expected)
        self.assertEqual(RESILIENCE.route_file(url), self.root / expected)
        self.assertEqual(LINKS.resolve_target(url, self.root / "about"), self.root / expected)
        self.assertEqual(AUDIT.url_to_relpath(route), relative)
        self.assertEqual(RESILIENCE.route_file(route), self.root / expected)
        self.assertEqual(LINKS.resolve_target(route, self.root / "about"), self.root / expected)

    def test_overlapping_routes_and_forward_round_trip(self):
        for route, relative in [
            ("/", "index.html"),
            ("/about/", "about/index.html"),
            ("/about", "about/index.html"),
            ("/standalone.html", "standalone.html"),
            ("/caf%C3%A9/", "café/index.html"),
            ("/about%2Fchild/", "about/child/index.html"),
        ]:
            with self.subTest(route=route):
                self.assert_consumers(route, relative)
        for relative in self.files:
            if relative.endswith(".html"):
                route = derive_url(self.root / relative, self.root)
                self.assert_consumers(route, relative)

    def test_query_fragment_policy_is_explicit(self):
        for route in ("/about/?view=1#section", "/standalone.html#section"):
            relative = "about/index.html" if route.startswith("/about/") else "standalone.html"
            url = ORIGIN + route
            self.assertEqual(AUDIT.url_to_relpath(url), relative)
            self.assertEqual(RESILIENCE.route_file(route), self.root / relative)
            self.assertEqual(LINKS.resolve_target(route, self.root), self.root / relative)
            self.assertIsNone(COVERAGE._path_for_url(url, ORIGIN, self.root))
        self.assertIsNone(COVERAGE._path_for_url("/about/", ORIGIN, self.root))
        self.assertTrue(LINKS.resolves(
            "?view=1#section", self.root / "standalone.html", {"section"}
        ))

    def test_source_relative_links_are_not_discovery_routes(self):
        source = self.root / "about"
        for href, relative in [
            ("child/", "about/child/index.html"),
            ("standalone.html?x=1#section", "about/standalone.html"),
            ("../standalone.html", "standalone.html"),
            ("../assets/style.css?v=1", "assets/style.css"),
            ("", "about/index.html"),
            ("#section", "about/index.html"),
        ]:
            with self.subTest(href=href):
                self.assertEqual(LINKS.resolve_target(href, source), self.root / relative)
                self.assertIsNone(AUDIT.url_to_relpath(href))
                self.assertIsNone(COVERAGE._path_for_url(href, ORIGIN, self.root))
                with self.assertRaises(ValueError):
                    RESILIENCE.route_file(href)
        self.assertEqual(
            LINKS.resolve_target("extensionless", self.root),
            self.root / "extensionless",
        )
        # Discovery maps extensionless page routes without filesystem guessing.
        self.assertEqual(AUDIT.url_to_relpath("/extensionless"), "extensionless/index.html")

    def test_invalid_origin_and_escaping_paths_are_rejected(self):
        outside = self.root.parent / "outside.html"
        outside.write_text("<h1>Outside</h1>", encoding="utf-8")
        for route in [
            "https://other.test/about/",
            "https://glee-fully.tools.evil.test/about/",
            "http://glee-fully.tools/about/",
            "//other.test/about/",
            "mailto:owner@example.test",
            "/../outside.html", "/%2e%2e/outside.html",
            "/%2E%2E%2Foutside.html", "/about/../../outside.html",
            "/bad%00.html", "/..%5coutside.html",
        ]:
            with self.subTest(route=route):
                self.assertIsNone(AUDIT.url_to_relpath(route))
                self.assertIsNone(COVERAGE._path_for_url(route, ORIGIN, self.root))
                self.assertIsNone(LINKS.resolve_target(route, self.root))
                with self.assertRaises(ValueError):
                    RESILIENCE.route_file(route)
        self.assertIsNone(LINKS.resolve_target("../../outside.html", self.root / "about"))

    def test_symlink_escape_is_rejected_including_directory_indexes(self):
        outside = self.root.parent / "outside"
        outside.mkdir()
        (outside / "index.html").write_text("<h1>Outside</h1>", encoding="utf-8")
        try:
            (self.root / "escape").symlink_to(outside, target_is_directory=True)
            (self.root / "about/index.html").unlink()
            (self.root / "about/index.html").symlink_to(outside / "index.html")
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"Symlinks unavailable: {exc}")
        for route in ("/escape/", "/about/"):
            self.assertIsNone(discovery_path(route, self.root, ORIGIN))
            self.assertIsNone(link_target(route, self.root, self.root, ORIGIN))
        self.assertIsNone(link_target("index.html", outside, self.root, ORIGIN))

    def test_missing_files_remain_reportable_without_link_success(self):
        self.assertEqual(AUDIT.url_to_relpath("/missing/"), "missing/index.html")
        self.assertEqual(
            COVERAGE._path_for_url(ORIGIN + "/missing/", ORIGIN, self.root),
            Path("missing/index.html"),
        )
        self.assertEqual(RESILIENCE.route_file("/missing.html"), self.root / "missing.html")
        self.assertIsNone(LINKS.resolve_target("/missing/", self.root))

    def test_coverage_scope_uses_decoding_and_rejects_escapes(self):
        inventory = COVERAGE.load_inventory(SCRIPTS.parent)
        sitemap = self.root / "sitemap.xml"
        for route, valid in [
            ("/caf%C3%A9/", True),
            ("/standalone.html", True),
            ("/about", True),
            ("/%2e%2e/outside.html", False),
            ("/about/?view=1", False),
            ("/standalone.html#section", False),
            ("about/", False),
        ]:
            url = ORIGIN + route if route.startswith("/") else route
            sitemap.write_text(
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                f"<url><loc>{url}</loc></url></urlset>", encoding="utf-8",
            )
            with self.subTest(url=url), patch.object(
                COVERAGE, "load_inventory", return_value=inventory
            ):
                _, issues = COVERAGE.derive_scope(self.root)
                self.assertEqual(not issues, valid, issues)

    def test_audit_reconciliation_reports_invalid_urls_and_maps_root(self):
        (self.root / "sitemap.xml").write_text(
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f"<url><loc>{ORIGIN}/</loc></url>"
            "<url><loc>https://other.test/</loc></url></urlset>",
            encoding="utf-8",
        )
        missing, extra, issues = AUDIT.reconcile_sitemap([self.root / "index.html"])
        self.assertEqual((missing, extra), ([], []))
        self.assertTrue(any("Invalid sitemap" in issue for issue in issues))
        index = self.root / "assets/data/search-index.json"
        index.parent.mkdir(parents=True)
        index.write_text(json.dumps({"pages": [
            {"url": "/"}, {"url": "standalone.html"},
            {"url": "https://other.test/"},
        ]}), encoding="utf-8")
        issues = AUDIT.reconcile_search_index([self.root / "index.html"])
        self.assertEqual(len(issues), 2)
        self.assertTrue(all("Invalid search-index" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
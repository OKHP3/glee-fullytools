import unittest
import importlib.util
from pathlib import Path

from scripts.tests.test_browser_acceptance import adapt_local_http_navigation

spec = importlib.util.spec_from_file_location(
    "color_scheme_test", Path(__file__).with_name("test-color-scheme-init.py")
)
color_scheme_test = importlib.util.module_from_spec(spec)
spec.loader.exec_module(color_scheme_test)


class BootstrapEventIsolationTests(unittest.TestCase):
    def test_initial_blank_document_is_not_the_navigation_boundary(self):
        events = [
            ("domcontentloaded", "about:blank"),
            ("request", "http://localhost:5000/assets/js/color-scheme-init.js"),
            ("finished", "http://localhost:5000/assets/js/color-scheme-init.js"),
            ("domcontentloaded", "http://localhost:5000/about/"),
        ]
        result = color_scheme_test.bootstrap_events(events, "/about/")
        self.assertEqual(result["domcontentloaded_index"], 3)

    def test_actual_late_bootstrap_still_fails(self):
        events = [
            ("request", "http://localhost:5000/assets/js/color-scheme-init.js"),
            ("domcontentloaded", "http://localhost:5000/about/"),
            ("finished", "http://localhost:5000/assets/js/color-scheme-init.js"),
        ]
        with self.assertRaisesRegex(AssertionError, "did not finish"):
            color_scheme_test.bootstrap_events(events, "/about/")

    def test_missing_target_navigation_still_fails(self):
        events = [
            ("request", "http://localhost:5000/assets/js/color-scheme-init.js"),
            ("finished", "http://localhost:5000/assets/js/color-scheme-init.js"),
            ("domcontentloaded", "about:blank"),
        ]
        with self.assertRaisesRegex(AssertionError, "incomplete"):
            color_scheme_test.bootstrap_events(events, "/about/")


class LocalHttpNavigationFixtureTests(unittest.TestCase):
    base = "http://127.0.0.1:5000"
    html = '<meta http-equiv="Content-Security-Policy" content="default-src \'self\'; upgrade-insecure-requests">'

    def test_adapts_same_origin_loopback_html_navigation(self):
        adapted = adapt_local_http_navigation(
            self.base + "/", self.base, "text/html; charset=utf-8", self.html,
            is_navigation=True,
        )
        self.assertEqual(adapted, self.html.replace("; upgrade-insecure-requests", ""))

    def test_leaves_remote_origin_untouched(self):
        self.assertIsNone(adapt_local_http_navigation(
            "http://example.test/", self.base, "text/html", self.html,
            is_navigation=True,
        ))

    def test_leaves_same_origin_non_loopback_http_untouched(self):
        base = "http://example.test:5000"
        self.assertIsNone(adapt_local_http_navigation(
            base + "/", base, "text/html", self.html,
            is_navigation=True,
        ))

    def test_leaves_https_navigation_untouched(self):
        self.assertIsNone(adapt_local_http_navigation(
            "https://127.0.0.1:5000/", self.base, "text/html", self.html,
            is_navigation=True,
        ))
        base = "https://127.0.0.1:5000"
        self.assertIsNone(adapt_local_http_navigation(
            base + "/", base, "text/html", self.html,
            is_navigation=True,
        ))

    def test_leaves_non_html_and_non_navigation_untouched(self):
        self.assertIsNone(adapt_local_http_navigation(
            self.base + "/app.js", self.base, "text/javascript", self.html,
            is_navigation=True,
        ))
        self.assertIsNone(adapt_local_http_navigation(
            self.base + "/", self.base, "text/html", self.html,
            is_navigation=False,
        ))


if __name__ == "__main__":
    unittest.main()

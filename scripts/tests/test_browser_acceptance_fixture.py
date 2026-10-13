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
    timing = {"asset_response_end": 12, "domcontentloaded_start": 20}

    def test_initial_blank_document_is_not_the_navigation_boundary(self):
        events = [
            ("domcontentloaded", "about:blank"),
            ("request", "http://localhost:5000/assets/js/color-scheme-init.js"),
            ("finished", "http://localhost:5000/assets/js/color-scheme-init.js"),
            ("domcontentloaded", "http://localhost:5000/about/"),
        ]
        result = color_scheme_test.bootstrap_events(events, "/about/", self.timing)
        self.assertEqual(result["domcontentloaded_index"], 3)

    def test_actual_late_bootstrap_still_fails(self):
        events = [
            ("request", "http://localhost:5000/assets/js/color-scheme-init.js"),
            ("domcontentloaded", "http://localhost:5000/about/"),
            ("finished", "http://localhost:5000/assets/js/color-scheme-init.js"),
        ]
        with self.assertRaisesRegex(AssertionError, "did not finish"):
            color_scheme_test.bootstrap_events(events, "/about/", {
                "asset_response_end": 25, "domcontentloaded_start": 20,
            })

    def test_delayed_protocol_callback_uses_browser_timing(self):
        events = [
            ("request", "http://localhost:5000/assets/js/color-scheme-init.js"),
            ("domcontentloaded", "http://localhost:5000/about/"),
            ("finished", "http://localhost:5000/assets/js/color-scheme-init.js"),
        ]
        result = color_scheme_test.bootstrap_events(events, "/about/", self.timing)
        self.assertEqual(result["asset_finished_index"], 2)
        self.assertEqual(result["asset_response_end"], 12)

    def test_early_callback_does_not_override_late_browser_timing(self):
        events = [
            ("request", "http://localhost:5000/assets/js/color-scheme-init.js"),
            ("finished", "http://localhost:5000/assets/js/color-scheme-init.js"),
            ("domcontentloaded", "http://localhost:5000/about/"),
        ]
        with self.assertRaisesRegex(AssertionError, "did not finish"):
            color_scheme_test.bootstrap_events(events, "/about/", {
                "asset_response_end": 25, "domcontentloaded_start": 20,
            })

    def test_missing_browser_timing_cannot_pass(self):
        events = [
            ("request", "http://localhost:5000/assets/js/color-scheme-init.js"),
            ("finished", "http://localhost:5000/assets/js/color-scheme-init.js"),
            ("domcontentloaded", "http://localhost:5000/about/"),
        ]
        for end, start in ((None, 20), (12, None), (0, 20), (12, 0)):
            with self.subTest(end=end, start=start):
                with self.assertRaisesRegex(AssertionError, "missing browser timing"):
                    color_scheme_test.bootstrap_events(events, "/about/", {
                        "asset_response_end": end, "domcontentloaded_start": start,
                    })

    def test_missing_target_navigation_still_fails(self):
        events = [
            ("request", "http://localhost:5000/assets/js/color-scheme-init.js"),
            ("finished", "http://localhost:5000/assets/js/color-scheme-init.js"),
            ("domcontentloaded", "about:blank"),
        ]
        with self.assertRaisesRegex(AssertionError, "incomplete"):
            color_scheme_test.bootstrap_events(events, "/about/", self.timing)


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

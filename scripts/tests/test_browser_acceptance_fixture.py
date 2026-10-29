import unittest
import importlib.util
import json
import contextlib
import io
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.tests import test_browser_acceptance as visitor
from scripts.tests.test_browser_acceptance import (
    adapt_local_http_navigation,
    write_report,
)

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


class BrowserAcceptanceReportTests(unittest.TestCase):
    def test_failed_report_is_written_in_full_for_diagnostics(self):
        report = {
            "browser": "chromium",
            "results": [
                {"name": "visitor journey", "status": "FAIL", "error": "assertion"}
            ],
            "failures": 1,
        }
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "nested" / "browser-acceptance.json"
            serialized = write_report(report, output)

            self.assertEqual(output.read_text(encoding="utf-8"), serialized + "\n")
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), report)

    def test_sanitized_diagnostic_excludes_arbitrary_browser_detail(self):
        raw = {"browser": "chromium", "results": [{
            "name": visitor.JOURNEYS[0], "status": "FAIL",
            "error": "SYNTHETIC_SECRET", "blocked_external_urls": ["https://secret.invalid/token"],
        }]}
        result = visitor.failure_diagnostic(raw, "execution_failed")
        encoded = json.dumps(result)
        self.assertNotIn("SYNTHETIC_SECRET", encoded)
        self.assertNotIn("secret.invalid", encoded)
        self.assertEqual(result["results"], [{"name": visitor.JOURNEYS[0], "status": "FAIL"}])
        self.assertEqual(result["not_completed"], list(visitor.JOURNEYS[1:]))

    def test_validation_rejects_duplicate_unknown_and_inconsistent_reports(self):
        valid = visitor.failure_diagnostic({"browser": "chromium", "results": [
            {"name": name, "status": "FAIL" if index == 0 else "PASS"}
            for index, name in enumerate(visitor.JOURNEYS)
        ]}, "journey_failed")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            path.write_text(json.dumps(valid), encoding="utf-8")
            visitor.validate_failure_diagnostic(path, "chromium")
            cases = [
                json.dumps(valid).replace('"version": 1', '"version": "SYNTHETIC_SECRET", "version": 1', 1),
                json.dumps(valid).replace('"status": "FAIL"}', '"status": "SYNTHETIC_SECRET", "status": "FAIL"}', 1),
                json.dumps({**valid, "browser": "firefox"}),
                json.dumps({**valid, "not_completed": [visitor.JOURNEYS[-1]]}),
                json.dumps({**valid, "results": [{"name": "private-route", "status": "FAIL"}]}),
            ]
            for raw in cases:
                with self.subTest(raw=raw[:80]):
                    path.write_text(raw, encoding="utf-8")
                    with self.assertRaises(ValueError):
                        visitor.validate_failure_diagnostic(path, "chromium")

    def test_validator_cli_fails_closed_without_echoing_malformed_bytes(self):
        valid = visitor.failure_diagnostic({"browser": "chromium", "results": []}, "execution_failed")
        raw = json.dumps(valid).replace('"version": 1', '"version": "SYNTHETIC_SECRET", "version": 1', 1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "failure.json"
            path.write_text(raw, encoding="utf-8")
            result = subprocess.run([sys.executable, visitor.__file__, "--validate-failure", str(path)],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("SYNTHETIC_SECRET", result.stdout + result.stderr)

    def test_isolated_main_preserves_partial_results_and_hides_errors(self):
        class Browser:
            def close(self):
                raise RuntimeError("CLEANUP_SECRET")
        browser = Browser()
        class Manager:
            def __enter__(self):
                return SimpleNamespace(chromium=SimpleNamespace(launch=lambda **kwargs: browser))
            def __exit__(self, *args):
                return False
        def interrupted(browser, expect, args, results):
            results.append({"name": visitor.JOURNEYS[0], "status": "FAIL", "error": "PRIMARY_SECRET"})
            raise RuntimeError("EXECUTION_SECRET")
        with tempfile.TemporaryDirectory() as directory:
            failure = Path(directory) / "failure.json"
            success = Path(directory) / "success.json"
            fake = SimpleNamespace(expect=object(), sync_playwright=lambda: Manager())
            argv = ["visitor", "--diagnostic-output", str(failure), "--success-output", str(success)]
            stdout, stderr = io.StringIO(), io.StringIO()
            with patch.dict(sys.modules, {"playwright": SimpleNamespace(sync_api=fake), "playwright.sync_api": fake}), \
                 patch.object(visitor, "run_checks", side_effect=interrupted), patch.object(sys, "argv", argv), \
                 contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                self.assertEqual(visitor.main(), 1)
            visitor.validate_failure_diagnostic(failure, "chromium")
            text = failure.read_text(encoding="utf-8") + stdout.getvalue() + stderr.getvalue()
            self.assertNotIn("SECRET", text)
            self.assertFalse(success.exists())
            self.assertEqual(json.loads(failure.read_text())["results"][0]["status"], "FAIL")

    def test_actual_first_journey_failure_survives_context_cleanup_failure(self):
        class Request:
            def get(self, *args):
                raise RuntimeError("ACTION_SECRET")
        class Page:
            request = Request()
            def set_default_timeout(self, value): pass
            def on(self, *args): pass
        class Context:
            def route(self, *args): pass
            def new_page(self): return Page()
            def close(self): raise RuntimeError("CONTEXT_SECRET")
        class Browser:
            def new_context(self, **kwargs): return Context()
            def close(self): raise RuntimeError("BROWSER_SECRET")
        class Manager:
            def __enter__(self):
                return SimpleNamespace(chromium=SimpleNamespace(launch=lambda **kwargs: Browser()))
            def __exit__(self, *args): return False
        with tempfile.TemporaryDirectory() as directory:
            failure = Path(directory) / "failure.json"
            success = Path(directory) / "success.json"
            fake = SimpleNamespace(expect=object(), sync_playwright=lambda: Manager())
            argv = ["visitor", "--diagnostic-output", str(failure), "--success-output", str(success)]
            stdout, stderr = io.StringIO(), io.StringIO()
            with patch.dict(sys.modules, {"playwright": SimpleNamespace(sync_api=fake), "playwright.sync_api": fake}), \
                 patch.object(sys, "argv", argv), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                self.assertEqual(visitor.main(), 1)
            report = json.loads(failure.read_text(encoding="utf-8"))
            visitor.validate_failure_diagnostic(failure, "chromium")
            self.assertEqual(report["phase"], "execution_failed")
            self.assertEqual(report["results"], [{"name": visitor.JOURNEYS[0], "status": "FAIL"}])
            self.assertNotIn("SECRET", failure.read_text(encoding="utf-8") + stdout.getvalue() + stderr.getvalue())

    def test_browser_startup_failure_is_incomplete_and_safe(self):
        def launch_error(**kwargs): raise RuntimeError("STARTUP_SECRET")
        class Manager:
            def __enter__(self): return SimpleNamespace(chromium=SimpleNamespace(launch=launch_error))
            def __exit__(self, *args): return False
        with tempfile.TemporaryDirectory() as directory:
            failure = Path(directory) / "failure.json"
            success = Path(directory) / "success.json"
            fake = SimpleNamespace(expect=object(), sync_playwright=lambda: Manager())
            argv = ["visitor", "--diagnostic-output", str(failure), "--success-output", str(success)]
            output = io.StringIO()
            with patch.dict(sys.modules, {"playwright": SimpleNamespace(sync_api=fake), "playwright.sync_api": fake}), \
                 patch.object(sys, "argv", argv), contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                self.assertEqual(visitor.main(), 1)
            report = json.loads(failure.read_text(encoding="utf-8"))
            visitor.validate_failure_diagnostic(failure, "chromium")
            self.assertEqual(report["results"], [])
            self.assertEqual(report["not_completed"], list(visitor.JOURNEYS))
            self.assertNotIn("STARTUP_SECRET", failure.read_text(encoding="utf-8") + output.getvalue())

    def test_isolated_main_propagates_cancellation_and_preserves_existing_report(self):
        class Browser:
            def close(self):
                raise RuntimeError("cleanup")
        class Manager:
            def __enter__(self):
                return SimpleNamespace(chromium=SimpleNamespace(launch=lambda **kwargs: Browser()))
            def __exit__(self, *args):
                return False
        with tempfile.TemporaryDirectory() as directory:
            failure = Path(directory) / "failure.json"
            success = Path(directory) / "success.json"
            failure.write_text("retained", encoding="utf-8")
            fake = SimpleNamespace(expect=object(), sync_playwright=lambda: Manager())
            argv = ["visitor", "--diagnostic-output", str(failure), "--success-output", str(success)]
            with patch.dict(sys.modules, {"playwright": SimpleNamespace(sync_api=fake), "playwright.sync_api": fake}), \
                 patch.object(visitor, "run_checks", side_effect=KeyboardInterrupt()), patch.object(sys, "argv", argv):
                with self.assertRaises(KeyboardInterrupt):
                    visitor.main()
            self.assertEqual(failure.read_text(encoding="utf-8"), "retained")
            self.assertFalse(success.exists())

    def test_isolated_success_is_current_and_exclusive(self):
        class Manager:
            def __enter__(self):
                return SimpleNamespace(chromium=SimpleNamespace(launch=lambda **kwargs: SimpleNamespace(close=lambda: None)))
            def __exit__(self, *args):
                return False
        def passing(browser, expect, args, results):
            results.extend({"name": name, "status": "PASS"} for name in visitor.JOURNEYS)
        with tempfile.TemporaryDirectory() as directory:
            failure, success = Path(directory) / "failure.json", Path(directory) / "success.json"
            fake = SimpleNamespace(expect=object(), sync_playwright=lambda: Manager())
            argv = ["visitor", "--diagnostic-output", str(failure), "--success-output", str(success)]
            with patch.dict(sys.modules, {"playwright": SimpleNamespace(sync_api=fake), "playwright.sync_api": fake}), \
                 patch.object(visitor, "run_checks", side_effect=passing), patch.object(sys, "argv", argv):
                self.assertEqual(visitor.main(), 0)
                self.assertEqual(visitor.main(), 1)
            self.assertEqual(json.loads(success.read_text())["failures"], 0)
            self.assertFalse(failure.exists())


if __name__ == "__main__":
    unittest.main()

"""Regression checks for browser link traversal and honest recovery failures."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location(
    "utility_keyboard_checker", Path(__file__).with_name("test-color-scheme-init.py")
)
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


class UtilityKeyboardTests(unittest.TestCase):
    def probe(self, results):
        page = Mock()
        page.evaluate.side_effect = results
        context = Mock()
        context.new_page.return_value = page
        return context, page

    def test_tab_is_preferred_when_it_reaches_a_link(self):
        context, page = self.probe([True])
        self.assertEqual(checker.link_traversal_key(context), "Tab")
        page.keyboard.press.assert_called_once_with("Tab")
        page.close.assert_called_once()

    def test_alt_tab_requires_separate_probe_evidence(self):
        context, page = self.probe([False, True])
        self.assertEqual(checker.link_traversal_key(context), "Alt+Tab")
        self.assertEqual(
            [call.args[0] for call in page.keyboard.press.call_args_list],
            ["Tab", "Alt+Tab"],
        )
        self.assertEqual(page.locator.return_value.focus.call_count, 2)
        page.close.assert_called_once()

    def test_no_verified_link_key_fails_closed(self):
        context, page = self.probe([False, False])
        with self.assertRaisesRegex(AssertionError, "no verified link traversal key"):
            checker.link_traversal_key(context)
        page.close.assert_called_once()

    def test_probe_is_closed_on_browser_error(self):
        context, page = self.probe([RuntimeError("browser unavailable")])
        with self.assertRaisesRegex(RuntimeError, "browser unavailable"):
            checker.link_traversal_key(context)
        page.close.assert_called_once()

    def test_unreachable_target_still_fails_without_focus_or_activation(self):
        for key in ("Tab", "Alt+Tab"):
            with self.subTest(key=key):
                page = Mock()
                action = page.locator.return_value
                action.count.return_value = 1
                action.is_visible.return_value = True
                action.inner_text.return_value = "Return home"
                action.evaluate.side_effect = ["https://example.test/"] + [False] * 100
                with (
                    patch.object(checker, "link_traversal_key", return_value=key),
                    patch.object(checker, "storage_error_name", return_value="SecurityError"),
                    self.assertRaisesRegex(AssertionError, "recovery action was not reachable"),
                ):
                    checker.check_utility_recovery(page, "https://example.test/", "/404.html", [])
                self.assertEqual(page.keyboard.press.call_count, 100)
                self.assertTrue(all(call.args == (key,) for call in page.keyboard.press.call_args_list))
                action.focus.assert_not_called()
                page.expect_navigation.assert_not_called()

    def test_reachable_target_uses_enter_and_records_verified_key(self):
        page = Mock(url="https://example.test/")
        action = page.locator.return_value
        action.count.return_value = 1
        action.is_visible.return_value = True
        action.inner_text.return_value = "Return home"
        action.evaluate.side_effect = ["https://example.test/", False, True]
        page.expect_navigation.return_value.__enter__ = Mock(
            return_value=SimpleNamespace(value=SimpleNamespace(ok=True, status=200))
        )
        page.expect_navigation.return_value.__exit__ = Mock(return_value=False)
        with (
            patch.object(checker, "link_traversal_key", return_value="Alt+Tab"),
            patch.object(checker, "storage_error_name", return_value="SecurityError"),
        ):
            result = checker.check_utility_recovery(page, "https://example.test/", "/404.html", [])
        self.assertEqual(result["traversal_key"], "Alt+Tab")
        self.assertEqual(result["tab_presses"], 2)
        self.assertEqual([call.args[0] for call in page.keyboard.press.call_args_list],
                         ["Alt+Tab", "Alt+Tab", "Enter"])
        action.focus.assert_not_called()


if __name__ == "__main__":
    unittest.main()

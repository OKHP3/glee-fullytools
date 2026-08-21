#!/usr/bin/env python3
"""Regression tests for fixed branded hover contrast checks."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


_SCRIPT = Path(__file__).resolve().parent.parent / "check-accent-contrast.py"
_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "accent-contrast"
_SPEC = importlib.util.spec_from_file_location("_check_accent_contrast", _SCRIPT)
assert _SPEC.loader is not None
mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mod)


def _scan_fixture(fixture_name: str, foreground: str = "#ffffff") -> list[dict]:
    """Scan one CSS fixture with a single isolated hover-state definition."""
    original_checks = mod.HOVER_CONTRAST_CHECKS
    fixture = _FIXTURES / fixture_name
    check = {
        "name": "Fixture CTA hover",
        "selector": ".fixture-cta:hover",
        "mode": "light",
        "foreground": foreground,
        "background": "#ffac3d",
        "required": True,
    }
    try:
        mod.HOVER_CONTRAST_CHECKS = (check,)
        return mod.scan_hover_contrast(fixture)
    finally:
        mod.HOVER_CONTRAST_CHECKS = original_checks


class AccentContrastHoverTests(unittest.TestCase):
    def test_fixed_foreground_and_background_pair_passes(self) -> None:
        self.assertEqual(
            _scan_fixture("fixed-foreground-pass.css.fixture", "#111111"), []
        )

    def test_missing_hover_rule_is_reported(self) -> None:
        findings = _scan_fixture("missing-hover-rule.css.fixture")

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule"], "known-hover-state-missing")

    def test_failing_fixed_pair_is_reported(self) -> None:
        findings = _scan_fixture("failing-contrast.css.fixture")

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule"], "known-hover-state-contrast")
        self.assertFalse(findings[0]["passes_aa_normal"])


if __name__ == "__main__":
    unittest.main()
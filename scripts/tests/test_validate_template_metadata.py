#!/usr/bin/env python3
"""Regression tests for template social-image metadata pairs."""
from __future__ import annotations

import importlib.util
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import shutil
import tempfile
import unittest


_SCRIPT = Path(__file__).resolve().parent.parent / "validate-site.py"
_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "template-metadata"
_spec = importlib.util.spec_from_file_location("_validate_site", _SCRIPT)
validate_site = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(validate_site)


def _run_validator_with_fixture(fixture_name: str) -> tuple[int, str]:
    """Run the validator against one isolated template fixture."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        templates = root / "assets" / "templates"
        templates.mkdir(parents=True)
        output_name = fixture_name.removesuffix(".fixture")
        shutil.copy(_FIXTURES / fixture_name, templates / output_name)

        original_root = validate_site.ROOT
        validate_site.ROOT = root
        try:
            output = StringIO()
            with redirect_stdout(output):
                result = validate_site.main()
            return result, output.getvalue()
        finally:
            validate_site.ROOT = original_root


class TemplateMetadataTests(unittest.TestCase):
    def test_valid_twitter_and_open_graph_pairs_pass(self):
        result, output = _run_validator_with_fixture("valid-pairs.html.fixture")

        self.assertEqual(result, 0)
        self.assertNotIn("Template metadata:", output)

    def test_missing_twitter_alt_fails_and_identifies_template(self):
        result, output = _run_validator_with_fixture(
            "missing-twitter-image-alt.html.fixture"
        )

        self.assertNotEqual(result, 0)
        self.assertIn("missing-twitter-image-alt.html", output)
        self.assertIn('name="twitter:image:alt"', output)

    def test_missing_open_graph_alt_fails_and_identifies_template(self):
        result, output = _run_validator_with_fixture(
            "missing-og-image-alt.html.fixture"
        )

        self.assertNotEqual(result, 0)
        self.assertIn("missing-og-image-alt.html", output)
        self.assertIn('property="og:image:alt"', output)


if __name__ == "__main__":
    unittest.main()
#!/usr/bin/env python3
"""Regression tests for scripts/sync-css-version.py."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path


_SCRIPT = Path(__file__).resolve().parent.parent / "sync-css-version.py"
_SPEC = importlib.util.spec_from_file_location("_sync_css_version", _SCRIPT)
_MODULE = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_MODULE)


class SyncCssVersionTests(unittest.TestCase):
    def run_main(self, *args: str) -> tuple[int, str]:
        """Run the synchronizer against the current temporary fixture."""
        old_argv = sys.argv
        output = io.StringIO()
        try:
            sys.argv = [str(_SCRIPT), *args]
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                status = _MODULE.main()
        finally:
            sys.argv = old_argv
        return status, output.getvalue()

    def test_check_detects_stale_tokens_and_never_writes(self) -> None:
        """Check mode fails and stays read-only until synchronization is run."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            theme = root / "assets" / "css" / "theme.css"
            page = root / "about" / "index.html"
            theme.parent.mkdir(parents=True)
            page.parent.mkdir(parents=True)
            theme.write_text("body { color: #222; }\n", encoding="utf-8")
            page.write_text(
                '<link rel="stylesheet" href="/assets/css/theme.css?v=deadbeef">\n',
                encoding="utf-8",
            )

            old_repo = _MODULE.REPO
            old_theme = _MODULE.THEME_CSS
            try:
                _MODULE.REPO = root
                _MODULE.THEME_CSS = theme
                before_check = page.read_bytes()

                status, output = self.run_main("--check")
                self.assertEqual(status, 1)
                self.assertIn("STALE: about/index.html", output)
                self.assertIn("1 HTML file(s) have stale", output)
                self.assertEqual(page.read_bytes(), before_check)

                status, output = self.run_main()
                self.assertEqual(status, 0)
                current_token = _MODULE.css_hash(theme)
                self.assertIn(f"CSS token → {current_token}", output)
                self.assertIn(f"theme.css?v={current_token}", page.read_text(encoding="utf-8"))

                before_clean_check = page.read_bytes()
                status, output = self.run_main("--check")
                self.assertEqual(status, 0)
                self.assertIn("all 1 file(s) already current", output)
                self.assertEqual(page.read_bytes(), before_clean_check)
            finally:
                _MODULE.REPO = old_repo
                _MODULE.THEME_CSS = old_theme


if __name__ == "__main__":
    unittest.main()
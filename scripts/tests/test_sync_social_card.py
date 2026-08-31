#!/usr/bin/env python3
"""Regression tests for scripts/sync-social-card.py."""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


_SCRIPT = Path(__file__).resolve().parent.parent / "sync-social-card.py"
_SPEC = importlib.util.spec_from_file_location("_sync_social_card", _SCRIPT)
_MODULE = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_MODULE)


class SyncSocialCardTests(unittest.TestCase):
    def test_offline_fallback_is_not_a_social_preview_page(self) -> None:
        """The noindex offline shell must not be required to carry OG metadata."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "about").mkdir()
            (root / "about" / "index.html").write_text("<html></html>", encoding="utf-8")
            (root / "offline.html").write_text("<html></html>", encoding="utf-8")

            old_root = _MODULE.ROOT
            try:
                _MODULE.ROOT = root
                self.assertEqual(
                    [path.relative_to(root).as_posix() for path in _MODULE.iter_html_files()],
                    ["about/index.html"],
                )
            finally:
                _MODULE.ROOT = old_root

    def test_card_dimensions_read_from_png_header(self) -> None:
        """The approved card must remain an actual 1200×630 PNG."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            card = root / "assets" / "img" / "glee-fully-tools-social-card-1200x630.png"
            card.parent.mkdir(parents=True)
            card.write_bytes(
                b"\x89PNG\r\n\x1a\n"
                + b"\x00\x00\x00\rIHDR"
                + (1200).to_bytes(4, "big")
                + (630).to_bytes(4, "big")
            )

            old_root = _MODULE.ROOT
            try:
                _MODULE.ROOT = root
                self.assertEqual(_MODULE.card_dimensions(), (1200, 630))
            finally:
                _MODULE.ROOT = old_root


if __name__ == "__main__":
    unittest.main()
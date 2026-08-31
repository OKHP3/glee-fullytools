#!/usr/bin/env python3
"""Regression tests for archived scripts/cache-bust.py."""
from __future__ import annotations

import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path


_SCRIPT = Path(__file__).resolve().parent.parent / "archive" / "cache-bust.py"
_SPEC = importlib.util.spec_from_file_location("_cache_bust", _SCRIPT)
_MODULE = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_MODULE)


class CacheBustTests(unittest.TestCase):
    def test_hash_normalizes_line_endings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            asset = Path(directory) / "theme.css"
            asset.write_bytes(b"body {\r\n  color: red;\r\n}\r\n")
            expected = hashlib.sha256(b"body {\n  color: red;\n}\n").hexdigest()[:8]
            self.assertEqual(_MODULE.file_hash(asset), expected)

    def test_only_owned_content_hashed_assets_are_rewritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset = root / "assets" / "css" / "theme.css"
            asset.parent.mkdir(parents=True)
            asset.write_bytes(b"body {\r\n  color: red;\r\n}\r\n")
            source = (
                '<link rel="stylesheet" href="/assets/css/theme.css?v=deadbeef">\n'
                '<script src="/assets/js/app.js?v=3"></script>\n'
            )

            rewritten, changes = _MODULE.rewrite_one(source, root)

            self.assertEqual(changes, 1)
            self.assertIn(
                f'theme.css?v={_MODULE.file_hash(asset)}', rewritten
            )
            self.assertIn('app.js?v=3', rewritten)


if __name__ == "__main__":
    unittest.main()

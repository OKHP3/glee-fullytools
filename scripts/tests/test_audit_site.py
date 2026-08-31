#!/usr/bin/env python3
"""Regression tests for scripts/audit-site.py discovery checks."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


_SCRIPT = Path(__file__).resolve().parent.parent / "audit-site.py"
_SPEC = importlib.util.spec_from_file_location("_audit_site", _SCRIPT)
_MODULE = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_MODULE)


class AuditSiteTests(unittest.TestCase):
    def test_utf8_index_and_offline_fallback_share_discovery_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            about = root / "about" / "index.html"
            offline = root / "offline.html"
            about.parent.mkdir(parents=True)
            about.write_text("<title>About</title>", encoding="utf-8")
            offline.write_text("<title>Offline</title>", encoding="utf-8")
            (root / "assets" / "data").mkdir(parents=True)
            (root / "assets" / "data" / "search-index.json").write_text(
                json.dumps(
                    {"pages": [{"url": "https://glee-fully.tools/about/", "title": "Café"}]},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (root / "sitemap.xml").write_text(
                "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"
                "<url><loc>https://glee-fully.tools/about/</loc></url></urlset>",
                encoding="utf-8",
            )

            old_root = _MODULE.ROOT
            try:
                _MODULE.ROOT = root
                files = [about, offline]
                self.assertEqual(_MODULE.reconcile_search_index(files), [])
                self.assertEqual(_MODULE.reconcile_sitemap(files), ([], [], []))
            finally:
                _MODULE.ROOT = old_root

    def test_freshness_uses_generator_check_instead_of_mtime(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index = root / "assets" / "data" / "search-index.json"
            builder = root / "scripts" / "build-search-index.py"
            index.parent.mkdir(parents=True)
            builder.parent.mkdir(parents=True)
            index.write_text('{"pages": []}', encoding="utf-8")
            builder.write_text("", encoding="utf-8")
            old_root = _MODULE.ROOT
            try:
                _MODULE.ROOT = root
                with patch.object(
                    _MODULE.subprocess,
                    "run",
                    return_value=type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
                ) as run:
                    self.assertEqual(_MODULE.check_search_index_freshness([]), [])
                self.assertEqual(run.call_args.args[0][-1], "--check")
            finally:
                _MODULE.ROOT = old_root


if __name__ == "__main__":
    unittest.main()

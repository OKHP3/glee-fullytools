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
                self.assertRegex(output, rf"CSS token (?:→|->) {current_token}")
                self.assertIn(f"theme.css?v={current_token}", page.read_text(encoding="utf-8"))

                before_clean_check = page.read_bytes()
                status, output = self.run_main("--check")
                self.assertEqual(status, 0)
                self.assertIn("all 1 file(s) already current", output)
                self.assertEqual(page.read_bytes(), before_clean_check)
            finally:
                _MODULE.REPO = old_repo
                _MODULE.THEME_CSS = old_theme

    def test_javascript_tokens_cover_html_and_worker_with_crlf_normalization(self) -> None:
        """Version both shared JS URLs consistently and keep check mode read-only."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            css = root / "assets" / "css" / "theme.css"
            app = root / "assets" / "js" / "app.js"
            enhancements = root / "assets" / "js" / "glee-site-enhancements.js"
            bootstrap = root / "assets" / "js" / "color-scheme-init.js"
            page = root / "about" / "index.html"
            worker = root / "sw.js"
            css.parent.mkdir(parents=True)
            app.parent.mkdir(parents=True)
            page.parent.mkdir(parents=True)
            (root / "index.html").write_text("shell\n", encoding="utf-8")
            css.write_text("body {}\n", encoding="utf-8")
            app.write_bytes(b"console.log('app');\r\n")
            enhancements.write_bytes(b"console.log('enhance');\r\n")
            bootstrap.write_bytes(b"console.log('theme');\r\n")
            app.write_bytes(b'const moduleUrl = "/assets/js/glee-site-enhancements.js";\r\n')
            page.write_text(
                '<script src="/assets/js/color-scheme-init.js?v=old"></script>\n'
                '<script src="/assets/js/app.js?v=stale&mode=test#keep"></script>\n'
                '<script src="https://cdn.example/assets/js/app.js?v=foreign"></script>\n'
                '<script src="/assets/js/glee-site-enhancements.js#keep"></script>\n',
                encoding="utf-8",
            )
            worker.write_text(
                'const CACHE_NAME = "glee-fully-shell-v1";\n'
                'const PRECACHE_URLS = ["/", "/assets/js/app.js?v=3", '
                '"/assets/js/glee-site-enhancements.js", "/assets/js/color-scheme-init.js?v=old"];\n',
                encoding="utf-8",
            )

            old_repo = _MODULE.REPO
            old_theme = _MODULE.THEME_CSS
            try:
                _MODULE.REPO = root
                _MODULE.THEME_CSS = css
                before_page = page.read_bytes()
                before_worker = worker.read_bytes()
                before_app = app.read_bytes()
                status, output = self.run_main("--check")
                self.assertEqual(status, 1)
                self.assertIn("STALE: assets/js/app.js adapter import", output)
                self.assertIn("offline shell is stale", output)
                self.assertEqual(page.read_bytes(), before_page)
                self.assertEqual(worker.read_bytes(), before_worker)
                self.assertEqual(app.read_bytes(), before_app)

                status, output = self.run_main()
                self.assertEqual(status, 0)
                tokens = _MODULE.javascript_tokens(root)
                app_source = app.read_text(encoding="utf-8")
                self.assertIn(
                    f'glee-site-enhancements.js?v={tokens["glee-site-enhancements"]}',
                    app_source,
                )
                rewritten = page.read_text(encoding="utf-8")
                self.assertIn(f'app.js?v={tokens["app"]}&mode=test#keep', rewritten)
                self.assertIn('https://cdn.example/assets/js/app.js?v=foreign', rewritten)
                self.assertIn(
                    f'glee-site-enhancements.js?v={tokens["glee-site-enhancements"]}#keep',
                    rewritten,
                )
                worker_text = worker.read_text(encoding="utf-8")
                self.assertIn(f'/assets/js/app.js?v={tokens["app"]}', worker_text)
                self.assertIn(
                    f'/assets/js/glee-site-enhancements.js?v={tokens["glee-site-enhancements"]}',
                    worker_text,
                )
                self.assertIn(f'color-scheme-init.js?v={tokens["color-scheme-init"]}', rewritten)
                self.assertIn(f'color-scheme-init.js?v={tokens["color-scheme-init"]}', worker_text)
                stable_worker = worker.read_bytes()
                stable_page = page.read_bytes()
                stable_app = app.read_bytes()
                self.assertEqual(self.run_main()[0], 0)
                self.assertEqual(worker.read_bytes(), stable_worker)
                self.assertEqual(page.read_bytes(), stable_page)
                self.assertEqual(app.read_bytes(), stable_app)
            finally:
                _MODULE.REPO = old_repo
                _MODULE.THEME_CSS = old_theme


    def test_search_index_url_changes_when_an_old_worker_has_unversioned_index(self) -> None:
        """A new index must use a new cache key for returning visitors."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            css = root / "assets" / "css" / "theme.css"
            app = root / "assets" / "js" / "app.js"
            page = root / "index.html"
            worker = root / "sw.js"
            index = root / "assets" / "data" / "search-index.json"
            css.parent.mkdir(parents=True)
            app.parent.mkdir(parents=True)
            index.parent.mkdir(parents=True)
            css.write_text("body {}\n", encoding="utf-8")
            app.write_text('const INDEX_URL = "/assets/data/search-index.json?mode=test#keep";\n', encoding="utf-8")
            page.write_text("<script src=\"/assets/js/app.js?v=old&mode=test#keep\"></script>\n", encoding="utf-8")
            index.write_text('{"pages":[{"url":"/foundry/"}]}\n', encoding="utf-8")
            worker.write_text(
                'const CACHE_NAME = "glee-fully-shell-v1";\n'
                'const PRECACHE_URLS = ["/assets/data/search-index.json"];\n',
                encoding="utf-8",
            )

            old_repo = _MODULE.REPO
            old_theme = _MODULE.THEME_CSS
            try:
                _MODULE.REPO = root
                _MODULE.THEME_CSS = css
                self.assertEqual(self.run_main()[0], 0)
                token = _MODULE.normalized_hash(index)
                app_text = app.read_text(encoding="utf-8")
                page_text = page.read_text(encoding="utf-8")
                worker_text = worker.read_text(encoding="utf-8")
                self.assertIn(f"search-index.json?mode=test&v={token}#keep", app_text)
                self.assertIn(f"app.js?v={_MODULE.normalized_hash(app)}&mode=test#keep", page_text)
                self.assertIn(f"search-index.json?v={token}", worker_text)

                stable = (app.read_bytes(), page.read_bytes(), worker.read_bytes())
                self.assertEqual(self.run_main("--check")[0], 0)
                self.assertEqual((app.read_bytes(), page.read_bytes(), worker.read_bytes()), stable)

                index.write_text('{"pages":[{"url":"/foundry/"},{"url":"/new-page/"}]}\n', encoding="utf-8")
                self.assertEqual(self.run_main()[0], 0)
                new_token = _MODULE.normalized_hash(index)
                self.assertNotEqual(token, new_token)
                self.assertIn(f"search-index.json?mode=test&v={new_token}#keep", app.read_text(encoding="utf-8"))
                self.assertIn(f"app.js?v={_MODULE.normalized_hash(app)}&mode=test#keep", page.read_text(encoding="utf-8"))
                self.assertIn(f"search-index.json?v={new_token}", worker.read_text(encoding="utf-8"))
                self.assertEqual(self.run_main("--check")[0], 0)
            finally:
                _MODULE.REPO = old_repo
                _MODULE.THEME_CSS = old_theme


if __name__ == "__main__":
    unittest.main()

"""Check direct-entry coverage, graceful fallback and unchanged launch destinations."""
import importlib.util
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from public_inventory import collect_indexable_html_files, derive_url

spec = importlib.util.spec_from_file_location("transition_sync", ROOT / "scripts/sync-transition-notices.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class TransitionNoticeTests(unittest.TestCase):
    def test_all_catalog_entries_have_static_and_modal_disclosures(self):
        catalog = [p for p in collect_indexable_html_files(ROOT) if derive_url(p, ROOT).startswith("/toolbox/")]
        self.assertEqual(len(catalog), 50)
        for page in catalog:
            with self.subTest(page=page):
                source = page.read_text(encoding="utf-8")
                self.assertEqual(source.count('class="glee-transition-notice container"'), 1)
                self.assertEqual(source.count('class="glee-transition-dialog"'), 1)
                self.assertIn('data-transition-auto="true"', source)
                self.assertIn("December 11, 2026", source)
                self.assertIn("does not mean a replacement is ready", source)
                self.assertIn('data-transition-open hidden', source)
                self.assertEqual(sync.synchronize(source, derive_url(page, ROOT)), source)

    def test_unrelated_web_experience_and_search_do_not_auto_open(self):
        for route in ("arcade", "search", "next-chapter"):
            source = (ROOT / route / "index.html").read_text(encoding="utf-8")
            self.assertNotIn('class="glee-transition-dialog"', source)
            self.assertIn('href="/next-chapter/"', source)

    def test_landing_page_is_a_transition_page_with_its_own_identity(self):
        source = (ROOT / "next-chapter/index.html").read_text(encoding="utf-8")
        self.assertIn('<title>Our Next Chapter | Glee-fully Personalizable Tools', source)
        self.assertIn("December 11, 2026", source)
        self.assertIn("Your past conversations do not automatically move", source)
        self.assertNotIn('id="how-it-works"', source)
        self.assertIn('https://glee-fully.tools/next-chapter/', source)

    def test_sync_preserves_external_destinations_and_publication_labels(self):
        fixture = '''<main id="main" class="stripe-bg"><h1>Example Tool</h1>
        <a class="btn btn-primary" href="https://chatgpt.com/g/g-123-example">Launch</a>
        <span data-status="beta">Beta</span></main>
        <footer><ul><li><a href="/search/">Search</a></li></ul></footer>'''
        result = sync.synchronize(fixture, "/toolbox/01-careers/01a-example/")
        self.assertIn('<a class="btn btn-primary" href="https://chatgpt.com/g/g-123-example">Launch</a>', result)
        self.assertIn('<span data-status="beta">Beta</span>', result)
        self.assertIn("Example Tool is part of our original Custom GPT catalog", result)
        self.assertEqual(sync.synchronize(result, "/toolbox/01-careers/01a-example/"), result)

    def test_dialog_has_native_focus_and_keyboard_close_semantics(self):
        source = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertRegex(source, r'<dialog[^>]*aria-labelledby="transition-dialog-title"[^>]*aria-describedby="transition-dialog-body"')
        self.assertIn("data-transition-close autofocus", source)
        runtime = (ROOT / "assets/js/glee-site-enhancements.js").read_text(encoding="utf-8")
        self.assertIn("transitionDialog.showModal()", runtime)
        self.assertIn('transitionDialog.addEventListener("close", rememberTransition)', runtime)
        self.assertIn("sessionStorage", runtime)
        self.assertIn("document.prerendering", runtime)


if __name__ == "__main__":
    unittest.main()

import importlib.util
import sys
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "check-links.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("check_links", SCRIPT)
check_links = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_links)


class FragmentLinkTests(unittest.TestCase):
    def test_parser_ignores_comments_and_data_ids(self):
        parser = check_links.PageLinks()
        parser.feed('<!-- <a href="missing.html#nope"> --> <div data-id="fake"></div>')
        self.assertEqual(parser.hrefs, [])
        self.assertEqual(parser.fragments, set())

    def test_same_document_and_cross_page_fragments_are_exact(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.html"
            target = root / "target.html"
            source.write_text('<h1 id="R&#233;sum&#233;">x</h1><a name="legacy">x</a>', encoding="utf-8")
            target.write_text('<h1 id="CaseSensitive">x</h1><h2 id="Café">x</h2>', encoding="utf-8")
            parser = check_links.PageLinks()
            parser.feed(source.read_text(encoding="utf-8"))
            self.assertTrue(check_links.resolves("#R%C3%A9sum%C3%A9", source, parser.fragments))
            self.assertTrue(check_links.resolves("#legacy", source, parser.fragments))
            self.assertFalse(check_links.resolves("#résumé", source, parser.fragments))
            self.assertTrue(check_links.resolves("target.html#CaseSensitive", source, parser.fragments))
            self.assertFalse(check_links.resolves("target.html#casesensitive", source, parser.fragments))
            self.assertTrue(check_links.resolves("target.html#Caf%C3%A9", source, parser.fragments))

            encoded_dir = root / "encoded dir"
            encoded_dir.mkdir()
            (encoded_dir / "index.html").write_text('<h1 id="section">x</h1>', encoding="utf-8")
            self.assertTrue(check_links.resolves("encoded%20dir/?mode=full#section", source, parser.fragments))

    def test_empty_top_and_text_fragments_are_browser_directives(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source.html"
            source.write_text('<p id="section">source</p>', encoding="utf-8")
            parser = check_links.PageLinks()
            parser.feed(source.read_text(encoding="utf-8"))
            for href in ("#", "#top", "#:~:text=source"):
                self.assertTrue(check_links.resolves(href, source, parser.fragments))
            self.assertTrue(check_links.resolves("#section:~:text=source", source, parser.fragments))
            self.assertFalse(check_links.resolves("#missing:~:text=source", source, parser.fragments))

    def test_protocol_relative_and_non_html_fragments(self):
        self.assertTrue(check_links.is_external("//cdn.example/site.css"))
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source.html"
            pdf = Path(temp) / "guide.pdf"
            source.write_text("<p>source</p>", encoding="utf-8")
            pdf.write_bytes(b"%PDF")
            parser = check_links.PageLinks()
            parser.feed(source.read_text(encoding="utf-8"))
            self.assertTrue(check_links.resolves("guide.pdf#page=2", source, parser.fragments))

    def test_main_reports_missing_fragments_and_resources(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "index.html").write_text(
                '<link href="missing.css"><a href="index.html#missing">bad</a>'
            )
            output = StringIO()
            (root / "sitemap.xml").write_text(
                "<urlset><url><loc>https://glee-fully.tools/</loc></url></urlset>", encoding="utf-8"
            )
            with patch.object(check_links, "ROOT", root), redirect_stdout(output):
                self.assertEqual(check_links.main(["--no-report"]), 1)
            self.assertIn("missing.css", output.getvalue())
            self.assertIn("index.html#missing", output.getvalue())


if __name__ == "__main__":
    unittest.main()

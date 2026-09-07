"""Search producer regressions. These tests never write the generated index."""
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BUILDER = runpy.run_path(str(Path(__file__).resolve().parents[1] / "build-search-index.py"))


class SearchIndexTests(unittest.TestCase):
    def test_main_text_excludes_chrome_and_nested_hidden_content(self):
        parser = BUILDER["PageParser"]()
        parser.feed('<html><head><title>Test</title></head><body><header>sparkle chai</header>'
                    '<main><h1>Resume</h1><div aria-hidden="true"><b>decoration</b> still hidden</div>'
                    '<p>Meaningful content</p><nav>Keep exploring</nav></main><footer>arcade</footer></body></html>')
        self.assertEqual(" ".join(parser.body_chunks), "Resume Meaningful content")

    def test_category_state_and_deep_content_are_indexed(self):
        root = BUILDER["REPO_ROOT"]
        entries = [BUILDER["build_entry"](p) for p in root.glob("toolbox/*/*/index.html")]
        states = {state: sum(e.get("publication_state") == state for e in entries)
                  for state in ("live", "beta", "unavailable")}
        self.assertEqual(states, {"live": 1, "beta": 24, "unavailable": 17})
        self.assertTrue(all(e.get("category") == "Tool-ette" for e in entries))
        self.assertTrue(all(e.get("branch_label") for e in entries))
        self.assertFalse(all("chai" in e["body"].lower() for e in entries))
        self.assertTrue(any(len(e["body"].split()) > 220 for e in entries))

    def test_nonpublic_and_cross_origin_canonical_are_not_propagated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / "about" / "index.html"
            page.parent.mkdir()
            page.write_text('<html><head><title>About</title><meta name="robots" content="noindex">'
                            '<link rel="canonical" href="https://other.example/wrong/"></head>'
                            '<body><main><h1>About</h1></main></body></html>', encoding="utf-8")
            globals_ = BUILDER["build_entry"].__globals__
            with patch.dict(globals_, REPO_ROOT=root):
                self.assertIsNone(BUILDER["build_entry"](page))
                page.write_text(page.read_text().replace('content="noindex"', 'content="index"'))
                self.assertEqual(BUILDER["build_entry"](page)["url"], "/about/")


if __name__ == "__main__":
    unittest.main()

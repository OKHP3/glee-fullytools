"""Catalog regressions: secondary routes must respect withdrawn destinations."""
from pathlib import Path
import contextlib
import io
import re
import runpy
import unittest

ROOT = Path(__file__).resolve().parents[2]
AUDIT = runpy.run_path(str(ROOT / "scripts/audit-tool-ette-promises.py"))


class VisitorTruthTests(unittest.TestCase):
    def test_secondary_link_to_unavailable_entry_is_rejected(self):
        html = '<a href="https://chatgpt.com/g/g-deadbeef-withdrawn">Withdrawn Helper</a>'
        errors = AUDIT["destination_errors"](html, {"abc123": "Working Helper"}, {"withdrawnhelper": None})
        self.assertTrue(errors, "A plain sibling link must not bypass an unavailable entry")

    def test_wrong_identity_cannot_reuse_an_available_destination(self):
        html = '<a href="https://chatgpt.com/g/g-abc123-working">Withdrawn Helper</a>'
        errors = AUDIT["destination_errors"](html, {"abc123": "Working Helper"}, {"withdrawnhelper": None})
        self.assertTrue(errors, "A reviewed URL does not authorize a different tool identity")

    def test_reviewed_secondary_and_internal_routes_are_allowed(self):
        html = '<a href="https://chatgpt.com/g/g-abc123-working">Working Helper</a><a href="/toolbox/withdrawn/">Withdrawn Helper</a>'
        self.assertEqual(AUDIT["destination_errors"](html, {"abc123": "Working Helper"}, {"workinghelper": "abc123", "withdrawnhelper": None}), [])

    def test_generic_and_placeholder_destinations_are_rejected(self):
        for url in ("https://chatgpt.com/", "https://chatgpt.com/g/g-YOUR-GPT-ID-HERE"):
            self.assertTrue(AUDIT["destination_errors"](f'<a href="{url}">Open helper</a>', {}, {}))

    def test_authoring_scaffold_is_rejected_but_comments_are_ignored(self):
        self.assertTrue(AUDIT["scaffold_errors"]('<p>Short, personality‑rich tagline for this GPT.</p>'))
        self.assertTrue(AUDIT["scaffold_errors"]('<p>Explain what users bring in (text, lists, uploads, prompts).</p>'))
        self.assertEqual(AUDIT["scaffold_errors"]('<!-- Short, personality‑rich tagline for this GPT. --><p>Calendar planning concept.</p>'), [])

    def test_homepage_toolbox_cta_reaches_catalog(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertRegex(html, r'href="/toolbox/"[^>]*>\s*Explore the full toolbox')

    def test_scheduling_has_no_public_authoring_scaffold(self):
        html = (ROOT / "toolbox/05-organized-life/05d-scheduling-wizard/index.html").read_text(encoding="utf-8")
        self.assertNotIn("Short, personality‑rich tagline", html)
        self.assertNotIn("One sentence about what this function does", html)

    def test_whole_catalog_passes_all_entry_point_audit(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = AUDIT["main"]()
        self.assertEqual(result, 0, output.getvalue())
        self.assertIn("42 pages; 1 live, 24 beta, 17 unavailable", output.getvalue())

    def test_unavailable_branch_cards_keep_a_truthful_detail_route(self):
        for path in (ROOT / "toolbox").glob("*/*/index.html"):
            html = path.read_text(encoding="utf-8")
            if AUDIT["launch_urls"](html):
                continue
            branch = (path.parent.parent / "index.html").read_text(encoding="utf-8")
            route = "/" + path.parent.relative_to(ROOT).as_posix() + "/"
            cards = re.findall(r'<article class="card card--tool-ette">.*?</article>', branch, re.S)
            self.assertTrue(any(route in card and "ChatGPT destination unavailable" in card for card in cards), route)


if __name__ == "__main__":
    unittest.main()

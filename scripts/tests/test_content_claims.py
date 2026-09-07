"""Regression coverage for unsupported catalog schema and identity claims."""
import json
from pathlib import Path
import runpy
import unittest

ROOT = Path(__file__).resolve().parents[2]
check = runpy.run_path(str(ROOT / "scripts/check-catalog-claims.py"))["check_claims"]
URL = "https://glee-fully.tools/toolbox/example/detail/"


def page(node):
    return (f'<link rel="canonical" href="{URL}">'
            '<p id="catalog-evidence">Intended use; behavior is not verified. Keep your own notes.</p>'
            f'<script type="application/ld+json">{json.dumps(node)}</script>')


class CatalogClaimTests(unittest.TestCase):
    def test_canonical_page_with_concept_image_is_valid(self):
        self.assertEqual([], check(page({"@type": "WebPage", "url": URL,
            "image": {"url": "/concept-illustration.svg"}})))

    def test_free_offer_and_illustration_screenshot_reproduce_old_claims(self):
        errors = check(page({"@type": "SoftwareApplication", "url": URL,
            "isAccessibleForFree": True, "offers": {"price": "0"},
            "screenshot": {"url": "/concept-illustration.svg"}}))
        for text in ("canonical WebPage", "offers", "isAccessibleForFree", "not an application screenshot"):
            self.assertTrue(any(text in error for error in errors), errors)

    def test_wrong_canonical_identity_is_rejected(self):
        self.assertTrue(check(page({"@type": "WebPage", "url": URL + "wrong/"})))

    def test_empty_hidden_or_commented_boundary_is_rejected(self):
        valid = page({"@type": "WebPage", "url": URL})
        for invalid in (valid.replace('<p id=', '<p hidden id='),
                        valid.replace('<p id=', '<!-- <p id=').replace('</p>', '</p> -->'),
                        valid.replace('Intended use; behavior is not verified. Keep your own notes.', '')):
            self.assertTrue(any('boundary' in error for error in check(invalid)))

    def test_verified_future_application_is_not_universally_forbidden(self):
        self.assertEqual([], check(page({"@type": "SoftwareApplication", "url": URL,
            "offers": {"price": "0"}, "screenshot": "/verified-screen.png"}),
            unverified_application=False))

    def test_nested_claims_and_malformed_json_fail(self):
        self.assertTrue(check(page({"@graph": [{"@type": "WebPage", "url": URL},
            {"offers": {"price": "0"}}]})))
        self.assertTrue(check('<script type="application/ld+json">{</script>'))

    def test_residual_author_instructions_are_rejected(self):
        scaffold_errors = runpy.run_path(str(ROOT / "scripts/audit-tool-ette-promises.py"))["scaffold_errors"]
        for instruction in ("Connect this Tool-ette to its parent Tool.",
                            "Show users how this GPT is already wired.",
                            "Help users take their first step in under a minute.",
                            "Spell out why this pre-tuned wallboard brain beats a blank prompt."):
            self.assertTrue(scaffold_errors('<p>' + instruction + '</p>'), instruction)

    def test_current_unverified_catalog_has_no_unsupported_claims(self):
        pages = sorted((ROOT / "toolbox").glob("*/*/index.html"))
        self.assertTrue(pages)
        errors = {str(path.relative_to(ROOT)): check(path.read_text(encoding="utf-8"))
                  for path in pages}
        self.assertFalse({path: issues for path, issues in errors.items() if issues})


if __name__ == "__main__":
    unittest.main()

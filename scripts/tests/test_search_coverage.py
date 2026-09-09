"""Regression tests for the credential-free search coverage scope check."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check-search-coverage.py"
SPEC = importlib.util.spec_from_file_location("check_search_coverage", SCRIPT)
CHECKER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(CHECKER)


class SearchCoverageTests(unittest.TestCase):
    def write_fixture(self, *, count=1, digest=None, bing_date=None):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        (root / "config").mkdir()
        (root / "docs").mkdir()
        (root / "about").mkdir()
        (root / "index.html").write_text("<!doctype html>", encoding="utf-8")
        (root / "about/index.html").write_text("<!doctype html>", encoding="utf-8")
        inventory = {
            "version": 1,
            "site": "https://example.test",
            "html_scope": {
                "excluded_files": ["404.html"],
                "excluded_directories": ["docs"],
            },
            "catalog": {
                "toolbox_hub": "^/toolbox/$",
                "branch": "^/toolbox/[0-9]+-[^/]+/$",
                "tool_ette": "^/toolbox/[0-9]+-[^/]+/[0-9]+[a-z]-[^/]+/$",
            },
            "discovery": {"sitemap": True},
        }
        (root / "config/public-inventory.json").write_text(
            json.dumps(inventory), encoding="utf-8"
        )
        (root / "sitemap.xml").write_text(
            """<?xml version="1.0"?>
            <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
              <url><loc>https://example.test/</loc></url>
              <url><loc>https://example.test/about/</loc></url>
            </urlset>
            """,
            encoding="utf-8",
        )
        current, issues = CHECKER.derive_scope(root)
        self.assertEqual(issues, [])
        scope = {
            "url_count": count,
            "url_sha256": digest or current["url_sha256"],
        }
        record = {
            "schema": 1,
            "review_date": "2026-09-09",
            "scope": {
                **scope,
                "source": "config/public-inventory.json + sitemap.xml",
            },
            "records": {
                "google-search-console": {
                    "review_date": "2026-09-09",
                    "scope": scope,
                    "status": "blocked",
                },
                "bing-webmaster-tools": {
                    "review_date": bing_date or "2026-09-09",
                    "scope": scope,
                    "status": "blocked",
                },
            },
        }
        block = (
            "# Evidence\n\n"
            "## Sanitized coverage record\n\n"
            "```json\n"
            + json.dumps(record)
            + "\n```\n"
        )
        (root / "docs/discovery-evidence.md").write_text(block, encoding="utf-8")
        return root, current

    def test_current_repository_record_matches_sitemap_scope(self):
        current, issues = CHECKER.check(ROOT)
        self.assertEqual(issues, [])
        self.assertEqual(current["url_count"], 61)
        self.assertEqual(
            current["breakdown"],
            {
                "home": 1,
                "toolbox_hub": 1,
                "branch": 7,
                "tool-ette": 42,
                "supporting": 10,
            },
        )

    def test_stale_count_and_digest_are_reported_for_both_consoles(self):
        root, _ = self.write_fixture(count=1, digest="0" * 64)
        _, issues = CHECKER.check(root)
        self.assertTrue(any("overall scope is stale" in issue for issue in issues))
        self.assertEqual(
            sum("URL scope digest does not match" in issue for issue in issues),
            3,
        )

    def test_mismatched_review_date_is_reported(self):
        root, _ = self.write_fixture(bing_date="2026-09-08")
        _, issues = CHECKER.check(root)
        self.assertTrue(
            any("Bing Webmaster Tools review date" in issue for issue in issues)
        )

    def test_sitemap_outside_inventory_origin_fails_without_credentials(self):
        root, _ = self.write_fixture()
        sitemap = (root / "sitemap.xml").read_text(encoding="utf-8")
        (root / "sitemap.xml").write_text(
            sitemap.replace("https://example.test/about/", "https://other.test/about/"),
            encoding="utf-8",
        )
        _, issues = CHECKER.check(root)
        self.assertTrue(any("outside the configured site origin" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
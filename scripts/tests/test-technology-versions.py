"""Offline release-selection and failure tests; no network or installs."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import gzip
import io

SPEC = importlib.util.spec_from_file_location("versions", Path(__file__).resolve().parents[1] / "technology-versions.py")
versions = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(versions)


class TechnologyVersionsTests(unittest.TestCase):
    def test_numeric_comparison_and_no_downgrade(self):
        self.assertEqual(versions.comparison("1.9.0", "1.10.0"), "update")
        self.assertEqual(versions.comparison("2.0.0", "1.10.0"), "ahead-review")
        self.assertEqual(versions.comparison("v7", "7.2.0"), "floating-selector")
        self.assertEqual(versions.comparison("3.11", "3.14.7"), "newer-line")
        self.assertEqual(versions.comparison("not locked", "1.0.0"), "unresolved-current")

    def test_prerelease_latest_tag_is_unknown(self):
        item = versions.row("example", "npm", "1.0.0", "fixture", "test:npm")
        versions.check([item], "22.19.0", lambda _: {"version": "2.0.0-rc.1"})
        self.assertEqual(item["status"], "unknown")

    def test_registry_failure_does_not_look_current(self):
        def offline(_):
            raise OSError("offline")
        item = versions.row("example", "npm", "1.0.0", "fixture", "test:npm")
        versions.check([item], "22.19.0", offline)
        self.assertEqual(item["status"], "unknown")
        self.assertIn("offline", item["error"])

    def test_yanked_and_prerelease_python_packages_excluded(self):
        item = versions.row("example", "pypi", "1.0.0", "fixture", "test:pypi")
        versions.resolve(item, {"test:pypi": {"releases": {
            "1.0.0": [{"yanked": False}], "1.2.0": [{"yanked": False}],
            "2.0.0": [{"yanked": True}], "3.0.0rc1": [{"yanked": False}],
        }}}, "22.19.0")
        self.assertEqual(item["latest_stable"], "1.2.0")

    def test_python_prerelease_does_not_match_download_page(self):
        item = versions.row("Python", "python", "3.11", "fixture", versions.PYTHON_FEED)
        versions.resolve(item, {versions.PYTHON_FEED: "Python 3.15.0rc2< Python 3.14.7< Python 3.13.15 "}, "22.19.0")
        self.assertEqual(item["latest_stable"], "3.14.7")

    def test_latest_node_current_does_not_force_migration_from_current_lts(self):
        item = versions.row("Node.js", "node", "24.21.0", "fixture", versions.NODE_FEED)
        versions.resolve(item, {versions.NODE_FEED: [
            {"version": "v26.9.0", "lts": False},
            {"version": "v24.21.0", "lts": "Krypton"},
        ]}, "24.21.0")
        self.assertEqual(item["latest_stable"], "26.9.0")
        self.assertEqual(item["update_target"], "24.21.0")
        self.assertEqual(item["status"], "current")

    def test_gzip_download_feed_is_decoded(self):
        response = io.BytesIO(gzip.compress(b"Python 3.14.7<"))
        response.headers = {"Content-Encoding": "gzip"}
        with patch.object(versions.urllib.request, "urlopen", return_value=response):
            self.assertEqual(versions.fetch(versions.PYTHON_FEED), "Python 3.14.7<")

    def test_inventory_includes_every_locked_npm_package_and_no_framework_claim(self):
        rows = versions.inventory(versions.ROOT)
        import json
        lock = json.loads((versions.ROOT / "package-lock.json").read_text())
        self.assertEqual(sum(x["kind"] == "npm" and x["scope"] != "vendored" for x in rows), len(lock["packages"]) - 1)
        self.assertFalse({"vite", "tailwindcss", "typescript"} & {x["name"] for x in rows if x["scope"] == "direct"})


if __name__ == "__main__":
    unittest.main()

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

    def test_prerelease_latest_tag_uses_highest_stable_and_preserves_channel(self):
        source = "https://registry.npmjs.org/example/latest"
        item = versions.row("example", "npm", "1.0.0", "fixture", source)
        responses = {
            source: {"version": "2.0.0-rc.1"},
            "https://registry.npmjs.org/example": {
                "dist-tags": {"latest": "2.0.0-rc.1"},
                "versions": {"1.0.0": {}, "1.9.2": {}, "2.0.0-rc.1": {}},
            },
        }
        versions.check([item], "22.19.0", lambda url: responses[url])
        self.assertEqual(item["latest_stable"], "1.9.2")
        self.assertEqual(item["latest_channel"], "2.0.0-rc.1")
        self.assertEqual(item["latest_channel_source"], source)
        self.assertEqual(item["latest_stable_source"], "https://registry.npmjs.org/example")
        self.assertEqual(item["status"], "update")

    def test_prerelease_fallback_failure_is_local_to_that_package(self):
        prerelease = versions.row("example", "npm", "1.0.0", "fixture",
                                  "https://registry.npmjs.org/example/latest")
        stable = versions.row("other", "npm", "1.0.0", "fixture",
                              "https://registry.npmjs.org/other/latest")

        def fixture(url):
            if url.endswith("/example/latest"):
                return {"version": "2.0.0-rc.1"}
            if url.endswith("/other/latest"):
                return {"version": "1.1.0"}
            if url == "https://registry.npmjs.org/example":
                raise OSError("fallback metadata unavailable")
            return {"version": "22.19.0"}

        versions.check([prerelease, stable], "22.19.0", fixture)
        self.assertEqual(prerelease["status"], "unknown")
        self.assertIn("fallback metadata unavailable", prerelease["error"])
        self.assertEqual(stable["latest_stable"], "1.1.0")
        self.assertEqual(stable["status"], "update")

    def test_invalid_prerelease_metadata_fails_closed(self):
        for package_metadata in (
            {"dist-tags": {"latest": "2.0.0-rc.2"},
             "versions": {"1.0.0": {}, "2.0.0-rc.1": {}}},
            {"dist-tags": {"latest": "2.0.0-rc.1"},
             "versions": {"2.0.0-rc.1": {}}},
        ):
            with self.subTest(package_metadata=package_metadata):
                item = versions.row("example", "npm", "1.0.0", "fixture",
                                    "https://registry.npmjs.org/example/latest")
                responses = {
                    item["source"]: {"version": "2.0.0-rc.1"},
                    "https://registry.npmjs.org/example": package_metadata,
                }
                versions.check([item], "22.19.0", lambda url: responses[url])
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

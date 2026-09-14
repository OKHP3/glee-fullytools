import json
import importlib.util
import re
import tempfile
import unittest
from pathlib import Path

import sys

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from public_inventory import (  # noqa: E402
    collect_html_files,
    collect_indexable_html_files,
    is_counted_destination,
    is_discoverable,
    page_type,
)

ARTIFACT_SPEC = importlib.util.spec_from_file_location(
    "check_pages_artifact", SCRIPTS / "check-pages-artifact.py"
)
ARTIFACT = importlib.util.module_from_spec(ARTIFACT_SPEC)
ARTIFACT_SPEC.loader.exec_module(ARTIFACT)


class PublicInventoryTests(unittest.TestCase):
    def test_current_scope_matches_contract(self):
        config = json.loads(
            (SCRIPTS.parent / "config" / "public-inventory.json").read_text(
                encoding="utf-8"
            )
        )
        all_pages = collect_html_files()
        pages = collect_indexable_html_files()
        urls = [ARTIFACT_PATH(p) for p in pages]
        page_types = {url: page_type(url) for url in urls}

        excluded_files = set(config["html_scope"]["excluded_files"])
        self.assertEqual(
            {path.name for path in all_pages if path not in pages},
            excluded_files,
        )
        self.assertEqual(len(urls), len(set(urls)))
        self.assertEqual(
            set(page_types.values()),
            {"home", "toolbox_hub", "branch", "tool-ette", "supporting"},
        )
        self.assertEqual(
            [url for url, kind in page_types.items() if kind == "toolbox_hub"],
            ["/toolbox/"],
        )

        feed_types = set(config["discovery"]["feed_types"])
        self.assertEqual(
            {url for url in urls if is_discoverable(url, "feed")},
            {url for url, kind in page_types.items() if kind in feed_types},
        )

        tool_ette_urls = {
            url for url, kind in page_types.items() if kind == "tool-ette"
        }
        destination_exclusions = set(config["catalog"]["destination_exclusions"])
        self.assertLessEqual(destination_exclusions, tool_ette_urls)
        self.assertEqual(
            {url for url in tool_ette_urls if is_counted_destination(url)},
            tool_ette_urls - destination_exclusions,
        )

        destination_pattern = re.compile(
            config["catalog"]["destination_pattern"], re.IGNORECASE
        )
        counted_destinations = set()
        for path, url in zip(pages, urls):
            if page_type(url) == "tool-ette" and is_counted_destination(url):
                if destination_pattern.search(path.read_text(encoding="utf-8")):
                    counted_destinations.add(url)
        self.assertTrue(counted_destinations)
        self.assertLessEqual(counted_destinations, tool_ette_urls)

    def test_artifact_policy_rejects_internal_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "release-provenance.json").write_text("{}", encoding="utf-8")
            (root / "index.html").write_text("<!doctype html>", encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs" / "private.md").write_text("no", encoding="utf-8")
            issues = ARTIFACT.check_artifact(root)
            self.assertTrue(any("forbidden artifact path" in issue for issue in issues))

    def test_artifact_policy_accepts_minimal_public_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "release-provenance.json").write_text("{}", encoding="utf-8")
            (root / "index.html").write_text("<!doctype html>", encoding="utf-8")
            self.assertEqual(ARTIFACT.check_artifact(root), [])

    def test_artifact_policy_accepts_foundry_section(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.html").write_text("<!doctype html>", encoding="utf-8")
            (root / "release-provenance.json").write_text("{}", encoding="utf-8")
            (root / "foundry").mkdir()
            (root / "foundry" / "index.html").write_text(
                "<!doctype html>", encoding="utf-8"
            )
            self.assertEqual(ARTIFACT.check_artifact(root), [])


def ARTIFACT_PATH(path: Path) -> str:
    rel = path.relative_to(SCRIPTS.parent)
    if rel.as_posix() == "index.html":
        return "/"
    return "/" + rel.parent.as_posix() + "/"

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
        self.assertEqual(len(collect_html_files()), 64)
        pages = collect_indexable_html_files()
        self.assertEqual(len(pages), 61)

        urls = [ARTIFACT_PATH(p) for p in pages]
        self.assertEqual(sum(page_type(url) == "toolbox_hub" for url in urls), 1)
        self.assertEqual(sum(page_type(url) == "branch" for url in urls), 7)
        self.assertEqual(sum(page_type(url) == "tool-ette" for url in urls), 42)
        self.assertEqual(
            sum(is_discoverable(url, "feed") for url in urls),
            49,
        )
        config = json.loads(
            (SCRIPTS.parent / "config" / "public-inventory.json").read_text(
                encoding="utf-8"
            )
        )
        destination_pattern = re.compile(
            config["catalog"]["destination_pattern"], re.IGNORECASE
        )
        destination_count = 0
        for path, url in zip(pages, urls):
            if page_type(url) == "tool-ette" and is_counted_destination(url):
                if destination_pattern.search(path.read_text(encoding="utf-8")):
                    destination_count += 1
        self.assertEqual(destination_count, 25)

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

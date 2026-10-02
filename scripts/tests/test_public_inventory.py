import json
import importlib.util
import re
import tempfile
import unittest
from pathlib import Path

import sys
from unittest.mock import patch

from scripts.tests.public_url_guard import duplicate_url_rules, scan_scripts

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from public_inventory import (  # noqa: E402
    collect_html_files,
    collect_indexable_html_files,
    derive_url,
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
    def test_active_scripts_share_public_url_derivation(self):
        self.assertEqual(scan_scripts(SCRIPTS), [])

    def test_guard_rejects_independent_conversions_despite_shared_import(self):
        rules = [
            'return "/" + path.relative_to(root).as_posix().replace("index.html", "")',
            'rel = path.relative_to(root)\nreturn f"/{rel.parent.as_posix()}/"',
            'renamed = path.relative_to(root).as_posix()\nreturn "/" + renamed',
            'rel = path.relative_to(root)\nreturn f"/{str(rel)[:-10]}"',
            'rel = path.relative_to(root)\nreturn f"/{chr(47).join(rel.parts[:-1])}/"',
            'branch = path.parent.name\nreturn f"/toolbox/{branch}/"',
        ]
        for rule in rules:
            with self.subTest(rule=rule):
                source = (
                    "from public_inventory import derive_url\n"
                    "def new_converter(path, root):\n    "
                    + rule.replace("\n", "\n    ") + "\n"
                )
                self.assertTrue(duplicate_url_rules(source))

    def test_guard_accepts_shared_aliases_reporting_and_inverse_lookups(self):
        source = '''
from public_inventory import derive_url as shared
import public_inventory as inventory
def delegated(path, root):
    return shared(path, root)
def qualified(path, root):
    return inventory.derive_url(path, root)
def report(path, root):
    return path.relative_to(root).as_posix()
def diagnostic(path, root):
    rel = path.relative_to(root).as_posix()
    return f"{rel}: missing {'/'.join(('og', 'url'))}"
def screenshot_report(path, root):
    return f"Screenshots: {path.relative_to(root)}/"
def inverse(url, root):
    return root / url.strip("/") / "index.html"
'''
        self.assertEqual(duplicate_url_rules(source), [])

    def test_guard_discovers_new_nested_tool_without_allowing_unused_import(self):
        with tempfile.TemporaryDirectory() as directory:
            scripts = Path(directory)
            nested = scripts / "release"
            nested.mkdir()
            tool = nested / "new-tool.py"
            tool.write_text(
                'from public_inventory import derive_url\n'
                'rel = path.relative_to(root)\nurl = "/" + rel.as_posix()\n',
                encoding="utf-8",
            )
            self.assertEqual(
                scan_scripts(scripts),
                ["release/new-tool.py:3: use public_inventory.derive_url"],
            )

    def test_release_wrappers_delegate_for_all_public_html_shapes(self):
        for filename, function, absolute in (
            ("build-search-index.py", "derive_url", True),
            ("check-links.py", "route_for_index", True),
            ("validate-site.py", "expected_canonical", False),
        ):
            spec = importlib.util.spec_from_file_location(filename[:-3], SCRIPTS / filename)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            root = getattr(module, "ROOT", getattr(module, "REPO_ROOT", None))
            for relative in ("index.html", "toolbox/branch/tool/index.html", "offline.html"):
                with self.subTest(script=filename, path=relative):
                    value = root / relative if absolute else Path(relative)
                    expected = derive_url(root / relative, root)
                    if filename == "validate-site.py":
                        expected = module.SITE + expected
                    self.assertEqual(getattr(module, function)(value), expected)
            # Verify actual delegation, not just today's matching output.
            with patch("public_inventory.derive_url", return_value="/delegated/"):
                # Top-level imports are bound at load time.
                spec.loader.exec_module(module)
                expected = "/delegated/"
                if filename == "validate-site.py":
                    expected = module.SITE + expected
                value = root / "index.html" if absolute else Path("index.html")
                self.assertEqual(getattr(module, function)(value), expected)

    def test_current_scope_matches_contract(self):
        config = json.loads(
            (SCRIPTS.parent / "config" / "public-inventory.json").read_text(
                encoding="utf-8"
            )
        )
        all_pages = collect_html_files()
        pages = collect_indexable_html_files()
        urls = [derive_url(path) for path in pages]
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

    def test_derive_url_covers_public_html_shapes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(derive_url(root / "index.html", root), "/")
            self.assertEqual(
                derive_url(root / "toolbox" / "index.html", root),
                "/toolbox/",
            )
            self.assertEqual(
                derive_url(root / "under-construction.html", root),
                "/under-construction.html",
            )

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

    def test_artifact_policy_accepts_transition_section(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "release-provenance.json").write_text("{}", encoding="utf-8")
            (root / "next-chapter").mkdir()
            (root / "next-chapter" / "index.html").write_text("<!doctype html>", encoding="utf-8")
            self.assertEqual(ARTIFACT.check_artifact(root), [])

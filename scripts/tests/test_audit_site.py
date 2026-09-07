#!/usr/bin/env python3
"""Regression tests for scripts/audit-site.py discovery checks."""
from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch


_SCRIPT = Path(__file__).resolve().parent.parent / "audit-site.py"
_SPEC = importlib.util.spec_from_file_location("_audit_site", _SCRIPT)
_MODULE = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_MODULE)


class AuditSiteTests(unittest.TestCase):
    def run_cli_fixture(self, root: Path, report: str, stdout) -> int:
        page = root / "caf\u00e9-\u2603" / "index.html"
        with ExitStack() as stack:
            for name, value in {
                "iter_html_files": [page],
                "audit_page": ["Missing description"],
                "reconcile_sitemap": ([], [], []),
                "reconcile_search_index": [],
                "check_search_index_freshness": [],
                "scan_repo_cruft": [],
            }.items():
                stack.enter_context(patch.object(_MODULE, name, return_value=value))
            stack.enter_context(patch.object(_MODULE, "ROOT", root))
            stack.enter_context(patch.object(_MODULE.sys, "argv", [str(_SCRIPT), "--report", report]))
            stack.enter_context(patch.object(_MODULE.sys, "stdout", stdout))
            stack.enter_context(patch.object(_MODULE.sys, "stderr", io.StringIO()))
            return _MODULE.main()

    def test_external_report_and_legacy_console_preserve_advisory_findings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            report = Path(directory) / "reports-\u2603" / "audit.md"
            with io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict") as console:
                result = self.run_cli_fixture(root, str(report), console)
                console.flush()
                output = console.buffer.getvalue().decode("utf-8")
            self.assertEqual(result, 0, "Findings remain advisory")
            self.assertIn(str(report.resolve()), output)
            self.assertIn("caf\u00e9-\u2603/index.html", output)
            self.assertIn("Total issues found: 1", output)
            self.assertIn("Missing description", report.read_text(encoding="utf-8"))

    def test_relative_report_is_rooted_in_repo_with_nonreconfigurable_console(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            console = io.StringIO()
            self.assertEqual(self.run_cli_fixture(root, "reports/audit.md", console), 0)
            self.assertTrue((root / "reports/audit.md").is_file())
            self.assertIn("Report written to reports/audit.md", console.getvalue())
            self.assertIn("Total issues found: 1", console.getvalue())

    def test_external_report_prints_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            report = Path(directory) / "external" / "audit.md"
            console = io.StringIO()
            self.assertEqual(self.run_cli_fixture(root, str(report), console), 0)
            self.assertIn(str(report.resolve()), console.getvalue())
            self.assertIn("Missing description", report.read_text(encoding="utf-8"))

    def test_symlinked_root_keeps_report_display_relative(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            actual = Path(directory) / "actual"
            actual.mkdir()
            alias = Path(directory) / "alias"
            try:
                alias.symlink_to(actual, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"Directory symlinks unavailable: {exc}")
            console = io.StringIO()
            self.assertEqual(self.run_cli_fixture(alias, "reports/audit.md", console), 0)
            self.assertTrue((actual / "reports/audit.md").is_file())
            self.assertIn("Report written to reports/audit.md", console.getvalue())
            self.assertIn("Total issues found: 1", console.getvalue())

    def test_post_merge_hook_has_durable_lf_checkout_policy(self) -> None:
        repo = _SCRIPT.parent.parent
        attributes = subprocess.check_output(
            ["git", "check-attr", "eol", "--", "scripts/post-merge.sh"],
            cwd=repo, text=True,
        )
        self.assertEqual(attributes.strip(), "scripts/post-merge.sh: eol: lf")
        self.assertNotIn(b"\r\n", (repo / "scripts/post-merge.sh").read_bytes())

    def test_utf8_index_and_offline_fallback_share_discovery_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            about = root / "about" / "index.html"
            offline = root / "offline.html"
            about.parent.mkdir(parents=True)
            about.write_text("<title>About</title>", encoding="utf-8")
            offline.write_text("<title>Offline</title>", encoding="utf-8")
            (root / "assets" / "data").mkdir(parents=True)
            (root / "assets" / "data" / "search-index.json").write_text(
                json.dumps(
                    {"pages": [{"url": "https://glee-fully.tools/about/", "title": "Café"}]},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (root / "sitemap.xml").write_text(
                "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"
                "<url><loc>https://glee-fully.tools/about/</loc></url></urlset>",
                encoding="utf-8",
            )

            old_root = _MODULE.ROOT
            try:
                _MODULE.ROOT = root
                files = [about, offline]
                self.assertEqual(_MODULE.reconcile_search_index(files), [])
                self.assertEqual(_MODULE.reconcile_sitemap(files), ([], [], []))
            finally:
                _MODULE.ROOT = old_root

    def test_freshness_uses_generator_check_instead_of_mtime(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index = root / "assets" / "data" / "search-index.json"
            builder = root / "scripts" / "build-search-index.py"
            index.parent.mkdir(parents=True)
            builder.parent.mkdir(parents=True)
            index.write_text('{"pages": []}', encoding="utf-8")
            builder.write_text("", encoding="utf-8")
            old_root = _MODULE.ROOT
            try:
                _MODULE.ROOT = root
                with patch.object(
                    _MODULE.subprocess,
                    "run",
                    return_value=type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
                ) as run:
                    self.assertEqual(_MODULE.check_search_index_freshness([]), [])
                self.assertEqual(run.call_args.args[0][-1], "--check")
            finally:
                _MODULE.ROOT = old_root


if __name__ == "__main__":
    unittest.main()

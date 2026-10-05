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

    def test_invalid_utf8_index_is_reported_without_aborting_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index = root / "assets" / "data" / "search-index.json"
            index.parent.mkdir(parents=True)
            index.write_bytes(b'{"pages": [{"title": "\xff"}]}')
            page = root / "about" / "index.html"
            console = io.StringIO()
            with ExitStack() as stack:
                stack.enter_context(patch.object(_MODULE, "ROOT", root))
                findings = _MODULE.reconcile_search_index([page])
                self.assertEqual(len(findings), 1)
                self.assertIn("search-index.json is unreadable:", findings[0])
                self.assertIn("utf-8", findings[0])
                stack.enter_context(patch.object(_MODULE, "iter_html_files", return_value=[page]))
                stack.enter_context(patch.object(_MODULE, "audit_page", return_value=["Missing description"]))
                stack.enter_context(patch.object(_MODULE, "reconcile_sitemap", return_value=([], [], [])))
                freshness = stack.enter_context(patch.object(
                    _MODULE, "check_search_index_freshness", return_value=[],
                ))
                cruft = stack.enter_context(patch.object(
                    _MODULE, "scan_repo_cruft", return_value=["Unexpected fixture file"],
                ))
                stack.enter_context(patch.object(
                    _MODULE.sys, "argv", [str(_SCRIPT), "--report", "reports/audit.md"],
                ))
                stack.enter_context(patch.object(_MODULE.sys, "stdout", console))
                stack.enter_context(patch.object(_MODULE.sys, "stderr", io.StringIO()))
                self.assertEqual(_MODULE.main(), 0, "Unreadable-index findings remain advisory")
                freshness.assert_called_once_with([page])
                cruft.assert_called_once_with()
            report = (root / "reports" / "audit.md").read_text(encoding="utf-8")
            self.assertIn(findings[0], report)
            self.assertIn("Missing description", report)
            self.assertIn("Unexpected fixture file", report)
            self.assertIn("Total issues found: 3", console.getvalue())
            self.assertEqual(index.read_bytes(), b'{"pages": [{"title": "\xff"}]}')

    def assert_unreadable_index_report(self, root: Path, detail: str) -> None:
        page = root / "about" / "index.html"
        console = io.StringIO()
        with ExitStack() as stack:
            stack.enter_context(patch.object(_MODULE, "ROOT", root))
            findings = _MODULE.reconcile_search_index([page])
            self.assertEqual(len(findings), 1)
            self.assertTrue(findings[0].startswith("search-index.json is unreadable:"))
            self.assertIn(detail, findings[0])
            stack.enter_context(patch.object(_MODULE, "iter_html_files", return_value=[page]))
            stack.enter_context(patch.object(_MODULE, "audit_page", return_value=["Missing description"]))
            stack.enter_context(patch.object(_MODULE, "reconcile_sitemap", return_value=([], [], [])))
            freshness = stack.enter_context(patch.object(
                _MODULE, "check_search_index_freshness", return_value=[],
            ))
            cruft = stack.enter_context(patch.object(
                _MODULE, "scan_repo_cruft", return_value=["Unexpected fixture file"],
            ))
            stack.enter_context(patch.object(
                _MODULE.sys, "argv", [str(_SCRIPT), "--report", "reports/audit.md"],
            ))
            stack.enter_context(patch.object(_MODULE.sys, "stdout", console))
            stack.enter_context(patch.object(_MODULE.sys, "stderr", io.StringIO()))
            self.assertEqual(_MODULE.main(), 0, "Unreadable-index findings remain advisory")
            freshness.assert_called_once_with([page])
            cruft.assert_called_once_with()
        report = (root / "reports" / "audit.md").read_text(encoding="utf-8")
        self.assertIn(findings[0], report)
        self.assertIn("Missing description", report)
        self.assertIn("Unexpected fixture file", report)
        self.assertIn("Report written to reports/audit.md", console.getvalue())
        self.assertIn("Total issues found: 3", console.getvalue())

    def test_malformed_json_index_is_reported_without_aborting_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index = root / "assets" / "data" / "search-index.json"
            index.parent.mkdir(parents=True)
            content = '{"pages": [}'
            index.write_text(content, encoding="utf-8")
            self.assert_unreadable_index_report(root, "Expecting value")
            self.assertEqual(index.read_text(encoding="utf-8"), content)

    def test_unexpected_pages_shape_is_reported_without_aborting_audit(self) -> None:
        for pages, shape in [({"url": "/about/"}, "dict"), (None, "NoneType")]:
            with self.subTest(shape=shape), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                index = root / "assets" / "data" / "search-index.json"
                index.parent.mkdir(parents=True)
                content = json.dumps({"pages": pages})
                index.write_text(content, encoding="utf-8")
                page = root / "about" / "index.html"
                console = io.StringIO()
                finding = f"search-index.json has unexpected shape: {shape}"
                with ExitStack() as stack:
                    stack.enter_context(patch.object(_MODULE, "ROOT", root))
                    self.assertEqual(_MODULE.reconcile_search_index([page]), [finding])
                    stack.enter_context(patch.object(
                        _MODULE, "iter_html_files", return_value=[page],
                    ))
                    stack.enter_context(patch.object(
                        _MODULE, "audit_page", return_value=["Missing description"],
                    ))
                    stack.enter_context(patch.object(
                        _MODULE, "reconcile_sitemap", return_value=([], [], []),
                    ))
                    freshness = stack.enter_context(patch.object(
                        _MODULE, "check_search_index_freshness",
                        return_value=["Fixture search-index freshness finding"],
                    ))
                    cruft = stack.enter_context(patch.object(
                        _MODULE, "scan_repo_cruft", return_value=["Unexpected fixture file"],
                    ))
                    stack.enter_context(patch.object(
                        _MODULE.sys, "argv", [str(_SCRIPT), "--report", "reports/audit.md"],
                    ))
                    stack.enter_context(patch.object(_MODULE.sys, "stdout", console))
                    stack.enter_context(patch.object(_MODULE.sys, "stderr", io.StringIO()))
                    self.assertEqual(_MODULE.main(), 0, "Unexpected-shape findings remain advisory")
                    freshness.assert_called_once_with([page])
                    cruft.assert_called_once_with()
                report = (root / "reports" / "audit.md").read_text(encoding="utf-8")
                self.assertIn(finding, report)
                self.assertIn("Missing description", report)
                self.assertIn("Fixture search-index freshness finding", report)
                self.assertIn("Unexpected fixture file", report)
                self.assertIn("**Total issues:** 4", report)
                self.assertIn("Report written to reports/audit.md", console.getvalue())
                self.assertIn("Total issues found: 4", console.getvalue())
                self.assertEqual(index.read_text(encoding="utf-8"), content)

    def test_index_read_oserror_is_reported_without_aborting_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index = root / "assets" / "data" / "search-index.json"
            index.parent.mkdir(parents=True)
            content = '{"pages": []}'
            index.write_text(content, encoding="utf-8")
            original_read_text = Path.read_text

            def read_text(path, *args, **kwargs):
                if path == index:
                    raise OSError("simulated index read failure")
                return original_read_text(path, *args, **kwargs)

            with patch.object(Path, "read_text", autospec=True, side_effect=read_text) as read:
                self.assert_unreadable_index_report(root, "simulated index read failure")
                index_reads = [call for call in read.call_args_list if call.args[0] == index]
                self.assertEqual(len(index_reads), 2)
                for call in index_reads:
                    self.assertEqual(call.kwargs, {"encoding": "utf-8"})
            self.assertEqual(index.read_text(encoding="utf-8"), content)

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

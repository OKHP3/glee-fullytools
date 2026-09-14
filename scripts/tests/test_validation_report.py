#!/usr/bin/env python3
"""Regression tests for idempotent site-validation evidence."""
from __future__ import annotations

import importlib.util
import json
from contextlib import ExitStack
from pathlib import Path
import tempfile
import unittest
from unittest import mock


_SCRIPT = Path(__file__).resolve().parent.parent / "validate-site.py"
_SPEC = importlib.util.spec_from_file_location("_validate_site", _SCRIPT)
validate_site = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(validate_site)


class ValidationReportTests(unittest.TestCase):
    def test_global_failure_is_saved_in_final_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "assets").mkdir()
            clean_checks = {
                "_check_organization_identity_approval": [],
                "_check_stat_markers_drift": [],
                "_check_adr_index_sync": None,
                "_check_scripts_py_drift": None,
                "_check_scripts_non_py_drift": None,
                "_check_og_image_alt_drift": [],
                "_check_sparkle_drift": [],
                "_check_glee_dark_coverage": [],
                "_check_css_token_drift": [],
                "_check_template_metadata": [],
                "_check_offline_shell": [],
                "_check_mermaid_version_pin": [],
                "_check_mermaid_csp_alignment": [],
            }
            patches = [
                mock.patch.object(validate_site, "ROOT", root),
                mock.patch.object(validate_site, "collect_html_files", return_value=[]),
                mock.patch.object(
                    validate_site,
                    "_check_css_lines_drift",
                    return_value="fixture global failure",
                ),
            ]
            patches.extend(
                mock.patch.object(validate_site, name, return_value=value)
                for name, value in clean_checks.items()
            )

            with ExitStack() as stack:
                for patch in patches:
                    stack.enter_context(patch)
                self.assertEqual(validate_site.main(), 1)

            report_path = next((root / "assets" / "audit").glob("validation-report-*.json"))
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["total_issues"], 1)
            self.assertEqual(report["total_warnings"], 0)
            self.assertEqual(
                report["global_issues"],
                ["CSS-lines drift: fixture global failure"],
            )
            self.assertEqual(report["global_warnings"], [])

    def test_unchanged_payload_preserves_report_bytes_and_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "validation-report-2026-09-10.json"
            report = {
                "generated_at": "2026-09-10T17:00:00Z",
                "run_date": "2026-09-10",
                "report_type": "site-validation",
                "scanned": 1,
                "total_issues": 0,
                "total_warnings": 0,
                "pages": [{"issues": [], "warnings": [], "path": "index.html"}],
            }

            self.assertTrue(validate_site._write_validation_report(report_path, report))
            original_bytes = report_path.read_bytes()

            rerun_report = {**report, "generated_at": "2026-09-10T17:05:00Z"}
            self.assertFalse(
                validate_site._write_validation_report(report_path, rerun_report)
            )
            self.assertEqual(report_path.read_bytes(), original_bytes)
            self.assertEqual(
                json.loads(report_path.read_text(encoding="utf-8"))["generated_at"],
                "2026-09-10T17:00:00Z",
            )

    def test_changed_payload_refreshes_report_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "validation-report-2026-09-10.json"
            original = {
                "generated_at": "2026-09-10T17:00:00Z",
                "run_date": "2026-09-10",
                "report_type": "site-validation",
                "scanned": 1,
                "total_issues": 0,
                "total_warnings": 0,
                "pages": [{"issues": [], "warnings": [], "path": "index.html"}],
            }
            changed = {
                **original,
                "generated_at": "2026-09-10T17:05:00Z",
                "total_warnings": 1,
            }

            validate_site._write_validation_report(report_path, original)
            self.assertTrue(
                validate_site._write_validation_report(report_path, changed)
            )
            self.assertEqual(
                json.loads(report_path.read_text(encoding="utf-8")),
                changed,
            )


if __name__ == "__main__":
    unittest.main()
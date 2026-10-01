#!/usr/bin/env python3
"""Regression tests for idempotent site-validation evidence."""
from __future__ import annotations

import importlib.util
import json
import argparse
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
    def test_commit_sha_is_normalized_and_rejects_ambiguous_values(self):
        commit = "ABCDEF0123456789ABCDEF0123456789ABCDEF01"
        self.assertEqual(
            validate_site._validated_commit(commit),
            commit.lower(),
        )
        with self.assertRaises(argparse.ArgumentTypeError):
            validate_site._validated_commit("abcdef0")

    def test_final_totals_match_serialized_page_and_global_details(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "assets").mkdir()
            page_path = root / "index.html"
            page_path.write_text("<!doctype html>", encoding="utf-8")
            clean_checks = {
                "_check_organization_identity_approval": [],
                "_check_stat_markers_drift": [],
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
                mock.patch.object(
                    validate_site, "collect_html_files", return_value=[page_path]
                ),
                mock.patch.object(
                    validate_site,
                    "check_page",
                    return_value={
                        "issues": ["fixture page issue"],
                        "warnings": ["fixture page warning"],
                    },
                ),
                mock.patch.object(
                    validate_site,
                    "_check_css_lines_drift",
                    return_value="fixture global failure",
                ),
                mock.patch.object(
                    validate_site,
                    "_check_adr_index_sync",
                    return_value="fixture global warning",
                ),
            ]
            patches.extend(
                mock.patch.object(validate_site, name, return_value=value)
                for name, value in clean_checks.items()
            )

            with ExitStack() as stack:
                for patch in patches:
                    stack.enter_context(patch)
                self.assertEqual(
                    validate_site.main(
                        validated_commit="abcdef0123456789abcdef0123456789abcdef01"
                    ),
                    1,
                )

            report_path = next((root / "assets" / "audit").glob("validation-report-*.json"))
            report = json.loads(report_path.read_text(encoding="utf-8"))
            serialized_issue_count = sum(
                len(page["issues"]) for page in report["pages"]
            ) + len(report["global_issues"])
            serialized_warning_count = sum(
                len(page["warnings"]) for page in report["pages"]
            ) + len(report["global_warnings"])
            self.assertEqual(report["total_issues"], serialized_issue_count)
            self.assertEqual(report["total_warnings"], serialized_warning_count)
            self.assertEqual(report["total_issues"], 2)
            self.assertEqual(report["total_warnings"], 2)
            self.assertEqual(
                report["global_issues"],
                ["CSS-lines drift: fixture global failure"],
            )
            self.assertEqual(
                report["global_warnings"],
                ["ADR index drift: fixture global warning"],
            )
            self.assertEqual(
                report["provenance"]["validated_commit"],
                "abcdef0123456789abcdef0123456789abcdef01",
            )

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
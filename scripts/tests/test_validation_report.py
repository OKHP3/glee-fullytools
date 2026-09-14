#!/usr/bin/env python3
"""Regression tests for idempotent site-validation evidence."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


_SCRIPT = Path(__file__).resolve().parent.parent / "validate-site.py"
_SPEC = importlib.util.spec_from_file_location("_validate_site", _SCRIPT)
validate_site = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(validate_site)


class ValidationReportTests(unittest.TestCase):
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
#!/usr/bin/env python3
"""Contract tests for FoundRy accessibility evidence and its Pages gate."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"
sys.path.insert(0, str(ROOT / "scripts"))

from check_foundry_accessibility_report import (  # noqa: E402
    EXPECTED_VIEWPORTS,
    SCREEN_READER_LIMITATION,
    STATUSES,
    validate_file,
    validate_report,
)


def valid_report() -> dict:
    checks = [
        {
            "name": "narrow-320: page identity and landmarks",
            "status": "PASS",
            "evidence": {"h1": "FoundRy"},
        },
        {
            "name": "narrow-390: narrow viewport overflow and console health",
            "status": "FAIL",
            "error": "document width exceeded viewport",
        },
        {
            "name": "narrow-390: optional check",
            "status": "NOT RUN",
        },
    ]
    return {
        "generatedAt": "2026-10-01T18:00:00.000Z",
        "sourceSha": "a" * 40,
        "route": "/foundry/",
        "viewports": deepcopy(EXPECTED_VIEWPORTS),
        "baseUrl": "http://127.0.0.1:38471",
        "runtime": {"status": "RUN", "driver": "Playwright Chromium"},
        "checks": checks,
        "summary": {
            status: sum(check["status"] == status for check in checks)
            for status in STATUSES
        },
        "limitations": [SCREEN_READER_LIMITATION],
    }


def step_block(workflow: str, name: str) -> str:
    marker = f"      - name: {name}\n"
    start = workflow.find(marker)
    if start < 0:
        raise AssertionError(f"Pages workflow is missing step {name!r}")
    next_step = workflow.find("\n      - name: ", start + len(marker))
    return workflow[start:] if next_step < 0 else workflow[start:next_step]


class FoundryAccessibilityReportTests(unittest.TestCase):
    def test_complete_report_contract_is_accepted(self):
        self.assertEqual(validate_report(valid_report()), [])

    def test_not_run_report_is_valid_with_reason_and_zero_counts(self):
        report = valid_report()
        report.pop("baseUrl")
        report["runtime"] = {
            "status": "NOT RUN",
            "reason": "Installed Chromium driver unavailable",
        }
        report["checks"] = []
        report["summary"] = {status: 0 for status in STATUSES}
        self.assertEqual(validate_report(report), [])

    def test_both_narrow_viewport_records_are_required(self):
        report = valid_report()
        report["viewports"] = report["viewports"][:1]
        self.assertTrue(
            any("viewports must contain narrow-320" in error for error in validate_report(report))
        )

    def test_runtime_run_requires_checks_for_both_viewports(self):
        report = valid_report()
        report["checks"] = [report["checks"][0]]
        report["summary"] = {status: 0 for status in STATUSES}
        report["summary"]["PASS"] = 1
        errors = validate_report(report)
        self.assertTrue(
            any("no checks for: narrow-390" in error for error in errors),
            errors,
        )

    def test_runtime_status_and_not_run_reason_are_required(self):
        for runtime in (
            {"status": "SKIPPED"},
            {"status": "NOT RUN", "reason": " "},
        ):
            with self.subTest(runtime=runtime):
                report = valid_report()
                report["runtime"] = runtime
                errors = validate_report(report)
                self.assertTrue(
                    any("runtime status must be RUN or NOT RUN" in error
                        or "runtime NOT RUN status requires a reason" in error
                        for error in errors),
                    errors,
                )

    def test_summary_counts_must_match_check_statuses(self):
        report = valid_report()
        report["summary"]["PASS"] += 1
        errors = validate_report(report)
        self.assertTrue(any("summary PASS count" in error for error in errors))

    def test_summary_counts_must_be_integer_values(self):
        report = valid_report()
        report["summary"]["FAIL"] = True
        errors = validate_report(report)
        self.assertTrue(
            any("summary FAIL count must be a non-negative integer" in error for error in errors)
        )

    def test_malformed_check_status_and_missing_failure_error_are_rejected(self):
        report = valid_report()
        report["checks"][1]["status"] = "BROKEN"
        report["checks"][1].pop("error")
        errors = validate_report(report)
        self.assertTrue(
            any("status must be PASS, FAIL, or NOT RUN" in error for error in errors)
        )

        report = valid_report()
        report["checks"][1].pop("error")
        errors = validate_report(report)
        self.assertTrue(any("must include an error" in error for error in errors))

    def test_explicit_human_screen_reader_limitation_is_required(self):
        report = valid_report()
        report["limitations"] = ["Automated browser checks only."]
        errors = validate_report(report)
        self.assertTrue(
            any("human screen-reader testing was not run" in error for error in errors)
        )

    def test_invalid_json_report_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            path.write_text("{", encoding="utf-8")
            errors = validate_file(path)
        self.assertTrue(any("report is invalid JSON" in error for error in errors))

    def test_pages_runs_contract_after_existing_gate_without_weakening_it(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        browser = step_block(workflow, "Run FoundRy accessibility evidence")
        contract = step_block(workflow, "Verify FoundRy accessibility report contract")
        upload = step_block(workflow, "Upload FoundRy accessibility evidence")

        browser_position = workflow.index(browser)
        contract_position = workflow.index(contract)
        upload_position = workflow.index(upload)
        self.assertLess(browser_position, contract_position)
        self.assertLess(contract_position, upload_position)

        self.assertIn("id: foundry_accessibility", browser)
        self.assertIn(
            "run: npm run qa:foundry-accessibility -- --output "
            "assets/audit/foundry-accessibility.json",
            browser,
        )
        self.assertNotIn("continue-on-error", browser)
        self.assertIn("always()", contract)
        self.assertIn("steps.foundry_accessibility.outcome == 'success'", contract)
        self.assertIn("steps.foundry_accessibility.outcome == 'failure'", contract)
        self.assertIn(
            "python3 scripts/tests/test_foundry_accessibility_report.py",
            contract,
        )
        self.assertIn(
            "python3 scripts/check_foundry_accessibility_report.py "
            "assets/audit/foundry-accessibility.json",
            contract,
        )
        self.assertIn("always()", upload)
        self.assertIn("if-no-files-found: error", upload)


if __name__ == "__main__":
    unittest.main()
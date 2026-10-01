#!/usr/bin/env python3
"""Contract tests for FoundRy accessibility evidence and its Pages gate."""
import importlib.util
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"
CHECKER_PATH = ROOT / "scripts" / "check-foundry-accessibility-report.py"
CHECKER_SPEC = importlib.util.spec_from_file_location(
    "foundry_accessibility_report_checker", CHECKER_PATH
)
if CHECKER_SPEC is None or CHECKER_SPEC.loader is None:
    raise ImportError(f"Could not load report checker at {CHECKER_PATH}")
CHECKER = importlib.util.module_from_spec(CHECKER_SPEC)
CHECKER_SPEC.loader.exec_module(CHECKER)

EXPECTED_VIEWPORTS = CHECKER.EXPECTED_VIEWPORTS
SCREEN_READER_LIMITATION = CHECKER.SCREEN_READER_LIMITATION
STATUSES = CHECKER.STATUSES
validate_file = CHECKER.validate_file
validate_report = CHECKER.validate_report


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

    def test_runtime_run_requires_driver_and_loopback_url(self):
        report = valid_report()
        report["runtime"] = {"status": "RUN"}
        report["baseUrl"] = "https://example.com"
        errors = validate_report(report)
        self.assertTrue(any("runtime RUN status requires a driver" in error for error in errors))
        self.assertTrue(any("runtime RUN status requires the loopback baseUrl" in error for error in errors))

    def test_summary_counts_must_match_check_statuses(self):
        for status in STATUSES:
            with self.subTest(status=status):
                report = valid_report()
                report["summary"][status] += 1
                errors = validate_report(report)
                self.assertTrue(
                    any(f"summary {status} count" in error for error in errors)
                )

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

    def test_check_names_require_a_nonempty_viewport_label(self):
        report = valid_report()
        report["checks"][0]["name"] = "narrow-320: "
        errors = validate_report(report)
        self.assertTrue(
            any("check name has no recognized narrow viewport" in error for error in errors)
        )

    def test_invalid_json_report_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            path.write_text("{", encoding="utf-8")
            errors = validate_file(path)
        self.assertTrue(any("report is invalid JSON" in error for error in errors))

    def test_pages_runs_contract_after_existing_gate_without_weakening_it(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        dependencies = step_block(workflow, "Install Node QA dependencies")
        browser_install = step_block(workflow, "Install Node Playwright Chromium")
        browser = step_block(workflow, "Run FoundRy accessibility evidence")
        contract = step_block(workflow, "Verify FoundRy accessibility report contract")
        upload = step_block(workflow, "Upload FoundRy accessibility evidence")

        browser_position = workflow.index(browser)
        contract_position = workflow.index(contract)
        upload_position = workflow.index(upload)
        self.assertLess(workflow.index(dependencies), browser_position)
        self.assertLess(workflow.index(browser_install), browser_position)
        self.assertLess(browser_position, contract_position)
        self.assertLess(contract_position, upload_position)

        self.assertIn("run: npm ci", dependencies)
        self.assertIn("run: npx playwright install --with-deps chromium", browser_install)
        self.assertIn("id: foundry_accessibility", browser)
        self.assertIn(
            'run: npm run qa:foundry-accessibility -- --output "$RUNNER_TEMP/foundry-accessibility.json"',
            browser,
        )
        self.assertNotIn("continue-on-error", browser)
        self.assertIn("always()", contract)
        self.assertIn("steps.foundry_accessibility.outcome == 'success'", contract)
        self.assertIn("steps.foundry_accessibility.outcome == 'failure'", contract)
        self.assertIn(
            "python3 scripts/tests/test-foundry-accessibility-report.py",
            contract,
        )
        self.assertIn(
            'python3 scripts/check-foundry-accessibility-report.py "$RUNNER_TEMP/foundry-accessibility.json"',
            contract,
        )
        self.assertIn("always()", upload)
        self.assertIn("steps.foundry_accessibility.outcome == 'success'", upload)
        self.assertIn("steps.foundry_accessibility.outcome == 'failure'", upload)
        self.assertIn(
            "path: ${{ runner.temp }}/foundry-accessibility.json",
            upload,
        )
        self.assertIn("if-no-files-found: error", upload)
        self.assertNotIn("assets/audit/foundry-accessibility.json", workflow)


if __name__ == "__main__":
    unittest.main()
#!/usr/bin/env python3
"""Contract tests for complete, commit-linked Pages validation evidence."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"
PROVENANCE_STEP = "- name: Verify validation report provenance"
STAGING_STEP = "- name: Stage complete validation evidence"
UPLOAD_STEP = "- name: Upload validation reports"
THEME_VERIFY_STEP = "- name: Verify browser-specific theme evidence"
LATE_EVIDENCE_STEPS = (
    "- name: Run browser responsive and asset QA",
    "- name: Run visitor, privacy, and rendered contrast acceptance",
    "- name: Run resilient web behavior QA",
    "- name: Run color-scheme bootstrap regression in all installed engines",
    "- name: Verify browser-specific theme evidence",
)
PROVENANCE_GATE = "steps.validation_provenance.outcome == 'success'"
STAGING_GATE = "steps.validation_staging.outcome == 'success'"
THEME_GATE = "steps.theme_evidence.outcome == 'success'"
HISTORICAL_FILTER = 'audit_dir.glob("validation-report-*.json")'
COMPLETE_AUDIT_COPY = 'shutil.copytree("assets/audit", audit_dir)'
THEME_BROWSER_LOOP = "for browser in chromium firefox webkit; do"
THEME_REPORT_PATTERN = "color-scheme-init-$browser.json"


def assert_validation_evidence_contract(workflow: str) -> None:
    """Raise a focused failure when release-evidence staging becomes unsafe."""
    positions = {
        label: workflow.find(label)
        for label in (PROVENANCE_STEP, STAGING_STEP, UPLOAD_STEP, *LATE_EVIDENCE_STEPS)
    }
    missing = [label for label, position in positions.items() if position < 0]
    if missing:
        raise AssertionError(
            "Pages validation evidence contract is missing: " + ", ".join(missing)
        )

    staging_position = positions[STAGING_STEP]
    upload_position = positions[UPLOAD_STEP]
    if any(positions[step] > staging_position for step in LATE_EVIDENCE_STEPS):
        raise AssertionError(
            "Validation evidence must be staged after all evidence-producing "
            "browser and resilience gates"
        )
    if staging_position > upload_position:
        raise AssertionError(
            "Validation evidence must be staged before the artifact upload"
        )

    staging_block = workflow[staging_position:upload_position]
    if "if: ${{ success() &&" not in staging_block:
        raise AssertionError("Complete evidence requires successful preceding gates")
    if COMPLETE_AUDIT_COPY not in staging_block:
        raise AssertionError(
            "Validation evidence staging must copy the complete final audit directory"
        )
    if HISTORICAL_FILTER not in staging_block or "report.unlink()" not in staging_block:
        raise AssertionError(
            "Validation evidence staging must filter historical dated reports"
        )

    upload_block = workflow[upload_position:].split("\n      - name:", 1)[0]
    if PROVENANCE_GATE not in upload_block or STAGING_GATE not in upload_block:
        raise AssertionError(
            "Validation evidence upload must require successful commit provenance "
            "and complete evidence staging"
        )

    theme_position = positions[THEME_VERIFY_STEP]
    theme_block = workflow[theme_position:staging_position]
    if "Browser-specific color-scheme evidence is incomplete" not in theme_block:
        raise AssertionError(
            "Release evidence must fail clearly when browser-specific theme evidence is incomplete"
        )
    if THEME_BROWSER_LOOP not in workflow or THEME_REPORT_PATTERN not in workflow:
        raise AssertionError(
            "Release workflow must retain color-scheme reports for chromium, firefox, and webkit"
        )
    if "light" not in theme_block or "dark" not in theme_block or "disabled_storage" not in theme_block:
        raise AssertionError(
            "Browser-specific theme evidence must include light, dark, and disabled-storage cases"
        )
    if THEME_GATE not in staging_block:
        raise AssertionError(
            "Complete evidence staging must require successful browser-specific theme verification"
        )


class PagesValidationEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_complete_commit_linked_evidence_is_staged_before_upload(self):
        assert_validation_evidence_contract(self.workflow)

    def test_early_staging_has_clear_failure(self):
        changed = self.workflow.replace(
            STAGING_STEP,
            f"{STAGING_STEP}\n        # moved before browser evidence",
            1,
        )
        staging_start = changed.find(STAGING_STEP)
        staging_end = changed.find(UPLOAD_STEP)
        staging_block = changed[staging_start:staging_end]
        changed = changed[:staging_start] + changed[staging_end:]
        insert_at = changed.find(LATE_EVIDENCE_STEPS[0])
        changed = changed[:insert_at] + staging_block + changed[insert_at:]
        with self.assertRaisesRegex(AssertionError, "staged after all"):
            assert_validation_evidence_contract(changed)

    def test_upload_without_provenance_gate_has_clear_failure(self):
        changed = self.workflow.replace(PROVENANCE_GATE, "always()", 2)
        with self.assertRaisesRegex(AssertionError, "successful commit provenance"):
            assert_validation_evidence_contract(changed)

    def test_failed_gate_cannot_stage_complete_evidence(self):
        changed = self.workflow.replace("if: ${{ success() &&", "if: ${{ always() &&")
        with self.assertRaisesRegex(AssertionError, "successful preceding gates"):
            assert_validation_evidence_contract(changed)

    def test_missing_browser_theme_report_has_clear_failure(self):
        block = self.workflow.split(THEME_VERIFY_STEP, 1)[1].split(
            "\n      - name:", 1
        )[0]
        code = textwrap.dedent(
            block.split("python3 - <<'PY'\n", 1)[1].rsplit("          PY", 1)[0]
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = root / "assets" / "audit"
            audit.mkdir(parents=True)
            for browser in ("chromium", "firefox"):
                (audit / f"color-scheme-init-{browser}.json").write_text(
                    json.dumps(
                        {
                            "browser": browser,
                            "status": "PASS",
                            "cases": {
                                "light": {},
                                "dark": {},
                                "disabled_storage": {},
                            },
                        }
                    ),
                    encoding="utf-8",
                )
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=root,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "missing: color-scheme-init-webkit.json",
                result.stderr,
            )

    def test_provenance_uses_commit_not_the_current_calendar_date(self):
        block = self.workflow.split(PROVENANCE_STEP, 1)[1].split("\n      - name:", 1)[0]
        code = textwrap.dedent(block.split("python3 - <<'PY'\n", 1)[1].rsplit("          PY", 1)[0])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = root / "assets" / "audit"
            audit.mkdir(parents=True)
            sha = "abcdef0123456789abcdef0123456789abcdef01"
            report_name = "validation-report-2000-01-01.json"
            payload = json.dumps({"provenance": {"validated_commit": sha}})
            (audit / report_name).write_text(payload, encoding="utf-8")
            output = root / "output.txt"
            env = {**os.environ, "EXPECTED_COMMIT": sha, "GITHUB_OUTPUT": str(output)}
            result = subprocess.run([sys.executable, "-c", code], cwd=root, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_text(encoding="utf-8").strip(), f"report_name={report_name}")
            (audit / "validation-report-2000-01-02.json").write_text(payload, encoding="utf-8")
            duplicate = subprocess.run([sys.executable, "-c", code], cwd=root, env=env, capture_output=True, text=True)
            self.assertNotEqual(duplicate.returncode, 0)
            self.assertIn("got 2", duplicate.stderr)


if __name__ == "__main__":
    unittest.main()

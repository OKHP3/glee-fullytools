#!/usr/bin/env python3
"""Contract tests for complete, commit-linked Pages validation evidence."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"
PROVENANCE_STEP = "- name: Verify validation report provenance"
STAGING_STEP = "- name: Stage complete validation evidence"
UPLOAD_STEP = "- name: Upload validation reports"
LATE_EVIDENCE_STEPS = (
    "- name: Run browser responsive and asset QA",
    "- name: Run visitor, privacy, and rendered contrast acceptance",
    "- name: Run resilient web behavior QA",
)
PROVENANCE_GATE = "steps.validation_provenance.outcome == 'success'"
STAGING_GATE = "steps.validation_staging.outcome == 'success'"
HISTORICAL_FILTER = 'audit_dir.glob("validation-report-*.json")'
COMPLETE_AUDIT_COPY = 'shutil.copytree("assets/audit", audit_dir)'


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


if __name__ == "__main__":
    unittest.main()
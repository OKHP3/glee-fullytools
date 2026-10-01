"""Contract tests for the search-coverage gate in the validation workflow."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "validate.yml"
SEARCH_GATE = "python3 scripts/check-search-coverage.py"
DISCOVERY_CHECKS = (
    "python3 scripts/build-search-index.py --check",
    "python3 scripts/generate-sitemap.py --check",
    "python3 scripts/generate-feed.py --check",
    "python3 scripts/sync-portfolio-stats.py --check",
)


def assert_search_coverage_validation_gate(workflow: str) -> None:
    """Raise a focused failure when the validation search gate contract drifts."""
    if SEARCH_GATE not in workflow:
        raise AssertionError(
            "Validation search coverage gate removed: validate.yml must invoke "
            "scripts/check-search-coverage.py"
        )

    validate_start = workflow.find("  validate:")
    next_job = re.search(r"\n  [\w-]+:\s*\n", workflow[validate_start + 1:])
    if validate_start < 0 or next_job is None:
        raise AssertionError(
            "Validation workflow job boundaries changed; search coverage contract "
            "must inspect the contributor-facing validate job"
        )

    next_job_start = validate_start + 1 + next_job.start()
    validate_job = workflow[validate_start:next_job_start]
    gate_position = validate_job.find(SEARCH_GATE)
    if gate_position < 0:
        raise AssertionError(
            "Validation search coverage gate moved outside the validate job; "
            "contributors must receive this feedback on pushes and pull requests"
        )

    for check in DISCOVERY_CHECKS:
        check_position = validate_job.find(check)
        if check_position < 0:
            raise AssertionError(
                f"Generated discovery check missing before validation search "
                f"coverage gate: {check}"
            )
        if check_position > gate_position:
            raise AssertionError(
                f"Validation search coverage gate moved before generated discovery "
                f"check: {check}"
            )


class ValidateSearchCoverageGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_search_coverage_gate_follows_generated_discovery_checks(self):
        assert_search_coverage_validation_gate(self.workflow)

    def test_removed_gate_has_clear_failure(self):
        changed = self.workflow.replace(SEARCH_GATE, "echo gate removed")
        with self.assertRaisesRegex(AssertionError, "coverage gate removed"):
            assert_search_coverage_validation_gate(changed)

    def test_gate_before_discovery_checks_has_clear_failure(self):
        changed = self.workflow.replace(SEARCH_GATE, "echo gate moved", 1)
        first_check = DISCOVERY_CHECKS[0]
        changed = changed.replace(first_check, f"{SEARCH_GATE}\n          {first_check}", 1)
        with self.assertRaisesRegex(AssertionError, "moved before generated discovery"):
            assert_search_coverage_validation_gate(changed)

    def test_gate_in_another_job_has_clear_failure(self):
        changed = self.workflow.replace(SEARCH_GATE, "echo gate moved", 1)
        changed = changed.replace(
            "python3 scripts/check-workflow-actions.py --check-updates",
            SEARCH_GATE,
            1,
        )
        with self.assertRaisesRegex(AssertionError, "moved outside the validate job"):
            assert_search_coverage_validation_gate(changed)

    def test_gate_in_new_adjacent_job_has_clear_failure(self):
        changed = self.workflow.replace(SEARCH_GATE, "echo gate moved", 1)
        changed = changed.replace(
            "  node-qa:\n",
            f"  injected-job:\n    steps:\n      - run: {SEARCH_GATE}\n\n  node-qa:\n",
            1,
        )
        with self.assertRaisesRegex(AssertionError, "moved outside the validate job"):
            assert_search_coverage_validation_gate(changed)


if __name__ == "__main__":
    unittest.main()

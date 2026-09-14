"""Contract tests for the search-coverage gate in the Pages workflow."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"
SEARCH_GATE = "python3 scripts/check-search-coverage.py"
DISCOVERY_CHECKS = (
    "python3 scripts/build-search-index.py --check",
    "python3 scripts/sync-portfolio-stats.py --check",
    "python3 scripts/generate-sitemap.py --check",
    "python3 scripts/generate-feed.py --check",
)
DEPLOY_ACTION = "uses: actions/deploy-pages@"


def assert_search_coverage_release_gate(workflow: str) -> None:
    """Raise a focused failure when the Pages search gate contract drifts."""
    if SEARCH_GATE not in workflow:
        raise AssertionError(
            "Pages release gate removed: pages.yml must invoke "
            "scripts/check-search-coverage.py"
        )

    validate_start = workflow.find("  validate:")
    deploy_start = workflow.find("  deploy:")
    if validate_start < 0 or deploy_start < 0 or validate_start >= deploy_start:
        raise AssertionError(
            "Pages workflow must define validate before deploy so release gates "
            "run before publication"
        )

    validate_job = workflow[validate_start:deploy_start]
    gate_position = validate_job.find(SEARCH_GATE)
    if gate_position < 0:
        raise AssertionError(
            "Search coverage release gate moved outside the validate job; it "
            "must block publication"
        )

    for check in DISCOVERY_CHECKS:
        check_position = validate_job.find(check)
        if check_position < 0:
            raise AssertionError(
                f"Generated discovery check missing before search coverage gate: {check}"
            )
        if check_position > gate_position:
            raise AssertionError(
                f"Search coverage release gate moved before generated discovery "
                f"check: {check}"
            )

    deploy_job = workflow[deploy_start:]
    if "needs: validate" not in deploy_job:
        raise AssertionError(
            "Deploy job must need validate so search coverage can block publication"
        )
    deploy_position = workflow.find(DEPLOY_ACTION, deploy_start)
    if deploy_position < 0:
        raise AssertionError("Pages deployment action is missing")
    if workflow.find(SEARCH_GATE) > deploy_position:
        raise AssertionError(
            "Search coverage release gate moved after deployment; it must run "
            "before publication"
        )


class PagesSearchCoverageGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_search_coverage_gate_blocks_pages_publication(self):
        assert_search_coverage_release_gate(self.workflow)

    def test_removed_gate_has_clear_failure(self):
        changed = self.workflow.replace(SEARCH_GATE, "echo gate removed")
        with self.assertRaisesRegex(AssertionError, "release gate removed"):
            assert_search_coverage_release_gate(changed)

    def test_gate_before_discovery_checks_has_clear_failure(self):
        changed = self.workflow.replace(SEARCH_GATE, "echo gate moved", 1)
        first_check = DISCOVERY_CHECKS[0]
        changed = changed.replace(first_check, f"{SEARCH_GATE}\n          {first_check}", 1)
        with self.assertRaisesRegex(AssertionError, "moved before generated discovery"):
            assert_search_coverage_release_gate(changed)

    def test_deploy_bypass_has_clear_failure(self):
        changed = self.workflow.replace("needs: validate", "needs: []", 1)
        with self.assertRaisesRegex(AssertionError, "must need validate"):
            assert_search_coverage_release_gate(changed)


if __name__ == "__main__":
    unittest.main()
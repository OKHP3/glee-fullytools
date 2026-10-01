"""Contract tests for the search-coverage gate in the Pages workflow."""

from pathlib import Path
import re
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
JOB_HEADER = re.compile(r"(?m)^  (?P<name>[A-Za-z0-9_-]+):[ \t]*(?:#.*)?$")
NEEDS_LINE = re.compile(r"(?m)^    needs:[ \t]*(?P<value>.*)$")
DEPENDENCY_NAME = re.compile(r"^[A-Za-z0-9_-]+$")


def _job_bounds(workflow: str, job_name: str) -> tuple[int, int]:
    """Find one top-level job block without parsing unrelated workflow YAML."""
    jobs_header = re.search(r"(?m)^jobs:[ \t]*$", workflow)
    if jobs_header is None:
        raise AssertionError("Pages workflow has no top-level jobs section")

    job_headers = list(JOB_HEADER.finditer(workflow, jobs_header.end()))
    for index, header in enumerate(job_headers):
        if header.group("name") == job_name:
            end = (
                job_headers[index + 1].start()
                if index + 1 < len(job_headers)
                else len(workflow)
            )
            return header.start(), end
    raise AssertionError(f"Pages workflow is missing the {job_name!r} job")


def _job_block(workflow: str, job_name: str) -> str:
    start, end = _job_bounds(workflow, job_name)
    return workflow[start:end]


def _dependency_name(value: str) -> str:
    """Parse one simple YAML job identifier, optionally quoted."""
    value = value.strip()
    if (
        len(value) >= 2
        and value[0] in {"'", '"'}
        and value[-1] == value[0]
    ):
        value = value[1:-1]
    if not DEPENDENCY_NAME.fullmatch(value):
        raise AssertionError(
            f"Deploy job has unsupported needs dependency syntax: {value!r}"
        )
    return value


def _parse_dependency_list(value: str) -> list[str]:
    """Parse a scalar or an inline YAML list of job identifiers."""
    value = value.split("#", 1)[0].strip()
    if value.startswith("["):
        if not value.endswith("]"):
            raise AssertionError("Deploy job has an incomplete needs list")
        body = value[1:-1].strip()
        if not body:
            return []
        return [_dependency_name(item) for item in body.split(",")]
    if not value:
        raise AssertionError("Deploy job has an empty needs dependency")
    return [_dependency_name(value)]


def _job_needs(workflow: str, job_name: str) -> list[str]:
    """Read only scalar, flow-list, and block-list job dependency syntax."""
    block = _job_block(workflow, job_name)
    match = NEEDS_LINE.search(block)
    if match is None:
        raise AssertionError(f"The {job_name} job must declare needs dependencies")

    value = match.group("value").split("#", 1)[0].strip()
    if value:
        return _parse_dependency_list(value)

    dependencies = []
    for line in block[match.end():].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = re.fullmatch(r" {6}-[ \t]*(.*?)[ \t]*(?:#.*)?", line)
        if item:
            dependencies.append(_dependency_name(item.group(1)))
        elif re.match(r"^ {4}\S", line):
            break
        elif not line.startswith("      "):
            break
        else:
            raise AssertionError("Deploy job has unsupported block-list needs syntax")
    return dependencies


def _replace_deploy_needs(workflow: str, replacement: str) -> str:
    """Mutate only the deploy job's direct needs line for contract tests."""
    start, end = _job_bounds(workflow, "deploy")
    block = workflow[start:end]
    match = NEEDS_LINE.search(block)
    if match is None:
        raise AssertionError("Deploy job has no needs line to mutate")
    changed_block = (
        block[:match.start()]
        + f"    needs: {replacement}"
        + block[match.end():]
    )
    return workflow[:start] + changed_block + workflow[end:]


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

    validate_job = _job_block(workflow, "validate")
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

    deploy_needs = _job_needs(workflow, "deploy")
    if "validate" not in deploy_needs:
        raise AssertionError(
            "Deploy job must directly need validate so search coverage can block publication"
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

    def test_gate_moved_to_evidence_job_is_rejected(self):
        changed = self.workflow.replace(SEARCH_GATE, "echo gate moved", 1)
        evidence_start, evidence_end = _job_bounds(
            changed,
            "verify-validation-evidence",
        )
        evidence_job = changed[evidence_start:evidence_end]
        steps_marker = "    steps:\n"
        self.assertIn(steps_marker, evidence_job)
        evidence_job = evidence_job.replace(
            steps_marker,
            steps_marker
            + f"      - name: Check search coverage scope\n"
            + f"        run: {SEARCH_GATE}\n",
            1,
        )
        changed = changed[:evidence_start] + evidence_job + changed[evidence_end:]
        with self.assertRaisesRegex(
            AssertionError,
            "moved outside the validate job",
        ):
            assert_search_coverage_release_gate(changed)

    def test_deploy_accepts_scalar_dependency(self):
        changed = _replace_deploy_needs(self.workflow, "validate")
        assert_search_coverage_release_gate(changed)

    def test_deploy_accepts_flow_list_dependencies(self):
        changed = _replace_deploy_needs(
            self.workflow,
            "[validate, verify-validation-evidence]",
        )
        assert_search_coverage_release_gate(changed)

    def test_deploy_accepts_block_list_dependencies(self):
        changed = _replace_deploy_needs(
            self.workflow,
            "\n      - validate\n      - verify-validation-evidence",
        )
        assert_search_coverage_release_gate(changed)

    def test_deploy_bypass_has_clear_failure(self):
        changed = _replace_deploy_needs(
            self.workflow,
            "[verify-validation-evidence]",
        )
        self.assertIn("needs: validate", _job_block(changed, "verify-validation-evidence"))
        with self.assertRaisesRegex(AssertionError, "must directly need validate"):
            assert_search_coverage_release_gate(changed)

    def test_deploy_rejects_lookalike_validate_dependencies(self):
        for lookalike in ("validate-job", "not-validate"):
            with self.subTest(dependency=lookalike):
                changed = _replace_deploy_needs(
                    self.workflow,
                    f"[{lookalike}, verify-validation-evidence]",
                )
                with self.assertRaisesRegex(
                    AssertionError,
                    "must directly need validate",
                ):
                    assert_search_coverage_release_gate(changed)


if __name__ == "__main__":
    unittest.main()

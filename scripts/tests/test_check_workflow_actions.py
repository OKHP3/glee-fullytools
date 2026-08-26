import importlib.util
import tempfile
import unittest
from pathlib import Path


_SCRIPT = Path(__file__).resolve().parent.parent / "check-workflow-actions.py"
_SPEC = importlib.util.spec_from_file_location("_check_workflow_actions", _SCRIPT)
check_workflow_actions = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(check_workflow_actions)


class WorkflowActionVersionTests(unittest.TestCase):
    def check(self, content: str) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            workflow = Path(directory) / "test.yml"
            workflow.write_text(content, encoding="utf-8")
            return check_workflow_actions.check_workflows(Path(directory))

    def test_approved_actions_pass(self) -> None:
        errors = self.check(
            """
            steps:
              - uses: actions/checkout@v4
              - uses: actions/setup-python@v5
              - uses: actions/upload-artifact@v4
            """
        )
        self.assertEqual(errors, [])

    def test_wrong_major_is_reported_with_location(self) -> None:
        errors = self.check("      uses: actions/checkout@v3\n")
        self.assertEqual(len(errors), 1)
        self.assertIn("test.yml:1", errors[0])
        self.assertIn("use v4", errors[0])

    def test_commit_refs_and_unknown_actions_are_rejected(self) -> None:
        errors = self.check(
            "      uses: actions/checkout@main\n"
            "      uses: example/custom-action@v1\n"
        )
        self.assertEqual(len(errors), 2)
        self.assertIn("must use an approved major tag", errors[0])
        self.assertIn("unsupported action", errors[1])

    def test_yaml_and_shell_lines_are_not_mistaken_for_action_references(self) -> None:
        errors = self.check(
            """
            run: echo "uses: actions/checkout@v1"
            # uses: actions/checkout@v1
            """
        )
        self.assertEqual(errors, [])

    def test_update_review_reports_newer_stable_major(self) -> None:
        def fetcher(action: str) -> dict[str, object]:
            if action == "actions/checkout":
                return {"tag_name": "v5.0.0"}
            approved = check_workflow_actions.ACTION_MAJOR_VERSIONS[action]
            return {"tag_name": f"v{approved}.0.0"}

        findings = check_workflow_actions.check_for_updates(fetcher)

        self.assertEqual(len(findings), 1)
        self.assertIn("actions/checkout", findings[0])
        self.assertIn("newer stable major v5", findings[0])

    def test_update_review_reports_fetch_failures(self) -> None:
        def fetcher(action: str) -> dict[str, object]:
            raise RuntimeError("network unavailable")

        findings = check_workflow_actions.check_for_updates(fetcher)

        self.assertEqual(len(findings), len(check_workflow_actions.ACTION_MAJOR_VERSIONS))
        self.assertTrue(all("update review failed" in finding for finding in findings))


if __name__ == "__main__":
    unittest.main()
"""Safety regressions for the stack checker; fixtures never touch this checkout."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "stack_checker", Path(__file__).resolve().parents[1] / "check-stack-conformance.py"
)
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


class StackSafetyTests(unittest.TestCase):
    def invoke(self, root, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = checker.main(["--root", str(root), "--json", *args])
        return code, json.loads(output.getvalue())

    def test_broken_check_cannot_pass_even_in_warning_mode(self):
        def broken(root, report):
            raise RuntimeError("verification unavailable")
        with tempfile.TemporaryDirectory() as root, patch.object(checker, "CHECKS", (broken,)):
            for args in ((), ("--warn-only",), ("--fix",)):
                code, result = self.invoke(root, *args)
                self.assertEqual(code, 2)
                self.assertFalse(result["pass"])

    def test_invalid_exemptions_cannot_disable_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for raw in ('{', '[]', '{"exempt":"NODE_ENGINES"}', '{"exempt":["NODE_ENGINES"]}'):
                (root / ".stack-conformance.json").write_text(raw)
                code, result = self.invoke(root)
                self.assertEqual(code, 2)
                self.assertFalse(result["pass"])

    def test_fix_preserves_tracked_evidence_and_index(self):
        paths = ["assets/audit/evidence.json", "scripts/archive/history.py", "skills/reference/SKILL.md"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in paths + ["replit.md"]:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("preserve me")
            checks = (checker.check_tracked_paths, checker.check_forbidden_files)
            with patch.object(checker, "CHECKS", checks), patch.object(checker, "git_tracked_files", return_value=paths), patch.object(checker, "git") as git:
                code, result = self.invoke(root, "--fix")
                self.assertEqual(code, 0)
                git.assert_not_called()
                self.assertTrue(result["pass"])
            for name in paths + ["replit.md"]:
                self.assertEqual((root / name).read_text(), "preserve me")

    def test_unavailable_git_is_a_checker_error(self):
        with tempfile.TemporaryDirectory() as root, patch.object(checker, "CHECKS", (checker.check_tracked_paths,)), patch.object(checker, "git_tracked_files", return_value=None):
            code, result = self.invoke(root)
            self.assertEqual(code, 2)
            self.assertFalse(result["pass"])

    def test_failed_repair_cannot_report_success_after_recheck(self):
        def partial_failure():
            raise RuntimeError("repair incomplete")
        report = checker.Report([])
        report.fail("REPAIR", "repair required", partial_failure)
        with tempfile.TemporaryDirectory() as root, patch.object(checker, "run_checks", side_effect=[report, checker.Report([])]):
            code, result = self.invoke(root, "--fix")
            self.assertEqual(code, 2)
            self.assertFalse(result["pass"])

    def test_missing_deployment_action_is_a_policy_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".github/workflows").mkdir(parents=True)
            with patch.object(checker, "CHECKS", (checker.check_deploy_action,)):
                code, result = self.invoke(root)
                self.assertEqual(code, 1)
                self.assertFalse(result["pass"])
                code, result = self.invoke(root, "--warn-only")
                self.assertEqual(code, 0)
                self.assertFalse(result["pass"])

    def test_retained_operating_guidance_is_required(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in checker.REQUIRED_FILES:
                if name != "replit.md":
                    (root / name).write_text("AGENTS.md")
            report = checker.Report([])
            checker.check_required_files(root, report)
            self.assertTrue(any(f["message"] == "replit.md is missing" for f in report.failures))

    def test_retained_puppeteer_must_keep_approved_pin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for version in (None, "0.0.0", "25.10.0"):
                deps = dict(checker.NPM_REQUIRED)
                if version is None:
                    del deps["puppeteer"]
                else:
                    deps["puppeteer"] = version
                (root / "package.json").write_text(json.dumps({"devDependencies": deps}))
                report = checker.Report([])
                checker.check_npm_deps(root, report)
                self.assertEqual(bool(report.failures), version != "25.10.0")


if __name__ == "__main__":
    unittest.main()

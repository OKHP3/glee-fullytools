"""Run the real post-merge shell hook with mocked validation commands."""
import os
import importlib.util
import io
from contextlib import redirect_stdout
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


HOOK = Path(__file__).resolve().parents[1] / "post-merge.sh"
GIT_BASH = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe"
BASH = str(GIT_BASH) if os.name == "nt" and GIT_BASH.is_file() else shutil.which("bash")
CALLS = [
    "scripts/build-search-index.py --check",
    "scripts/sync-portfolio-stats.py --check",
    "scripts/sync-css-version.py --check",
    "scripts/check-csp.py",
    "scripts/validate-site.py",
    "scripts/check-links.py --no-report",
]
REQUIRED = ("index.html", "assets/css/theme.css", "assets/js/app.js")
SUCCESS = "Post-merge: all checks passed."
SHELL = """
python3() {
  printf 'CALL|%s\\n' "$*"
  if [ "$*" = "$FAIL_CALL" ]; then return 23; fi
  return 0
}
tree() { echo 'Unexpected tree command' >&2; return 97; }
export -f python3 tree
source ./post-merge.sh
"""


class PostMergeTests(unittest.TestCase):
    def run_hook(self, fail_call="", missing=None):
        self.assertIsNotNone(BASH, "Bash is required to exercise the shell hook")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "post-merge.sh").write_bytes(HOOK.read_bytes())
            for name in REQUIRED:
                if name != missing:
                    path = root / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.touch()
            result = subprocess.run(
                [BASH, "-c", SHELL], cwd=root,
                env={**os.environ, "FAIL_CALL": fail_call},
                capture_output=True, text=True, timeout=15,
            )
        calls = [line.removeprefix("CALL|") for line in result.stdout.splitlines()
                 if line.startswith("CALL|")]
        return result, calls

    def test_success_runs_all_checks_in_order_without_generation(self):
        result, calls = self.run_hook()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(calls, CALLS)
        self.assertEqual(result.stdout.splitlines()[-1], SUCCESS)
        self.assertEqual(result.stderr, "")

    def test_each_failed_check_stops_later_checks_and_success(self):
        for index, call in enumerate(CALLS):
            with self.subTest(call=call):
                result, calls = self.run_hook(fail_call=call)
                self.assertEqual(result.returncode, 23, result.stdout + result.stderr)
                self.assertEqual(calls, CALLS[:index + 1])
                self.assertNotIn(SUCCESS, result.stdout)

    def test_missing_required_file_stops_before_checks(self):
        for name in REQUIRED:
            with self.subTest(file=name):
                result, calls = self.run_hook(missing=name)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(calls, [])
                self.assertIn(f"ERROR: required file missing: {name}", result.stderr)
                self.assertNotIn(SUCCESS, result.stdout)

    def test_hook_retains_lf_line_endings(self):
        self.assertNotIn(b"\r", HOOK.read_bytes())

    def test_link_check_no_report_preserves_findings_and_disk(self):
        spec = importlib.util.spec_from_file_location("links", HOOK.parent / "check-links.py")
        links = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(links)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            links.ROOT = root
            (root / "index.html").write_text('<a href="/missing/">Broken</a>', encoding="utf-8")
            (root / "sitemap.xml").write_text(f"<loc>{links.SITE}/</loc>", encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(links.main(["--no-report"]), 1)
            self.assertFalse((root / "assets").exists())
            audit = root / "assets/audit"
            audit.mkdir(parents=True)
            report = audit / f"links-report-{links.REPORT_DATE}.json"
            report.write_bytes(b"existing audit evidence")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(links.main(["--no-report"]), 1)
            self.assertEqual(report.read_bytes(), b"existing audit evidence")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(links.main([]), 1)
            self.assertIn('"broken_links"', report.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

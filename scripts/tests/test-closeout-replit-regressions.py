"""Isolated regressions for Replit's owner-transferred closeout batch.

Task map: #244 merge approval history; #245 shallow history and Pages checkout;
#251 legacy search-index lists; #258 simultaneous save/cleanup failure;
#285 local reporting dates independent of UTC. All mutations use temp fixtures.
"""
from contextlib import contextmanager, ExitStack, redirect_stdout
from copy import deepcopy
from datetime import date, datetime, timezone
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


identity = load("closeout_identity_fixtures", Path(__file__).with_name("test_organization_identity_approval.py"))
validator = identity.validate_site
auditor = load("closeout_auditor", ROOT / "scripts/audit-site.py")


@contextmanager
def main_fixture(root, *, local_day=date(2026, 9, 11), instant=None, real_identity=False):
    """Isolate unrelated page/global policies while retaining real main/writer."""
    instant = instant or datetime(2026, 9, 11, 17, tzinfo=timezone.utc)
    (root / "assets").mkdir(exist_ok=True)
    page = root / "index.html"
    if not page.exists():
        page.write_text("<!doctype html>", encoding="utf-8")
    with ExitStack() as stack:
        stack.enter_context(mock.patch.object(validator, "ROOT", root))
        stack.enter_context(mock.patch.object(validator, "collect_html_files", return_value=[page]))
        stack.enter_context(mock.patch.object(validator, "check_page", side_effect=lambda *_: {"issues": [], "warnings": []}))
        for name in (
            "_check_css_lines_drift", "_check_stat_markers_drift", "_check_adr_index_sync",
            "_check_scripts_py_drift", "_check_scripts_non_py_drift", "_check_og_image_alt_drift",
            "_check_sparkle_drift", "_check_glee_dark_coverage", "_check_css_token_drift",
            "_check_template_metadata", "_check_offline_shell", "_check_mermaid_version_pin",
            "_check_mermaid_csp_alignment",
        ):
            stack.enter_context(mock.patch.object(validator, name, return_value=[]))
        if not real_identity:
            stack.enter_context(mock.patch.object(validator, "_last_owner_confirmed_identity_snapshot", return_value=(None, None)))
            stack.enter_context(mock.patch.object(validator, "_check_organization_identity_approval", return_value=[]))
        calendar = stack.enter_context(mock.patch.object(validator, "date", wraps=date))
        calendar.today.return_value = local_day
        clock = stack.enter_context(mock.patch.object(validator, "datetime", wraps=datetime))
        clock.now.return_value = instant
        output = stack.enter_context(redirect_stdout(io.StringIO()))
        yield output, clock


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True, stderr=subprocess.PIPE).strip()


def identity_repository(root):
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.name", "Identity Fixture")
    git(root, "config", "user.email", "identity@example.invalid")
    (root / "docs").mkdir()
    (root / "docs/discovery-evidence.md").write_text(identity.EVIDENCE_TEMPLATE, encoding="utf-8")
    record = deepcopy(identity.APPROVAL_TEMPLATE)
    record["approved_urls"] = ["https://example.com/one"]
    write_identity(root, record)
    commit_identity(root, "initial owner approval")
    return record


def write_identity(root, record):
    (root / "docs/organization-identity-approval.json").write_text(json.dumps(record), encoding="utf-8")
    (root / "index.html").write_text(identity.ORGANIZATION_TEMPLATE.format(same_as=json.dumps(record["approved_urls"])), encoding="utf-8")


def commit_identity(root, message):
    git(root, "add", "index.html", "docs")
    git(root, "commit", "-q", "-m", message)


class CloseoutReplitRegressions(unittest.TestCase):
    def test_244_release_merges_reject_stale_identity_and_accept_renewed_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = identity_repository(root)
            original_urls = list(record["approved_urls"])
            git(root, "switch", "-q", "-c", "changed-identities")
            record["approved_urls"].append("https://example.com/new")
            write_identity(root, record)
            commit_identity(root, "changed URLs without renewed approval")
            git(root, "switch", "-q", "main")
            git(root, "merge", "-q", "--no-ff", "changed-identities", "-m", "merge stale identity change")
            stale_release = git(root, "rev-parse", "HEAD")
            self.assertEqual(len(git(root, "rev-list", "--parents", "-n", "1", stale_release).split()), 3)
            with main_fixture(root, real_identity=True):
                self.assertEqual(validator.main(validated_commit=stale_release), 1)
                snapshot, error = validator._last_owner_confirmed_identity_snapshot(stale_release)
                self.assertIsNone(error)
                self.assertEqual(snapshot["approved_urls"], original_urls)
            report_path = root / "assets/audit/validation-report-2026-09-11.json"
            stale_report = json.loads(report_path.read_text())
            self.assertEqual(stale_report["provenance"]["validated_commit"], stale_release)
            self.assertTrue(any("last owner-confirmed set" in issue for issue in stale_report["global_issues"]))

            git(root, "switch", "-q", "-c", "renew-approval")
            record["approval_date"] = "2026-09-10"
            record["reviewer_confirmation"]["statement"] = "Owner renewed approval of this updated fixture set."
            write_identity(root, record)
            commit_identity(root, "renew both approval fields")
            git(root, "switch", "-q", "main")
            git(root, "merge", "-q", "--no-ff", "renew-approval", "-m", "merge renewed approval")
            approved_release = git(root, "rev-parse", "HEAD")
            self.assertEqual(len(git(root, "rev-list", "--parents", "-n", "1", approved_release).split()), 3)
            with main_fixture(root, real_identity=True):
                self.assertEqual(validator.main(validated_commit=approved_release), 0)
                snapshot, error = validator._last_owner_confirmed_identity_snapshot(approved_release)
                self.assertIsNone(error)
                self.assertEqual(snapshot["approved_urls"], record["approved_urls"])
                # A later HEAD must not silently substitute its approval for an old release.
                old_snapshot, error = validator._last_owner_confirmed_identity_snapshot(stale_release)
                self.assertIsNone(error)
                self.assertEqual(old_snapshot["approved_urls"], original_urls)
            approved_report = json.loads(report_path.read_text())
            self.assertEqual(approved_report["provenance"]["validated_commit"], approved_release)
            self.assertEqual(approved_report["total_issues"], 0)

    def test_245_pages_validation_checkout_requires_full_history(self):
        workflow = (ROOT / ".github/workflows/pages.yml").read_text()
        def require_full_history(text):
            start = text.index("      - name: Checkout exact release commit\n")
            end = text.index("\n      - name:", start + 1)
            checkout = text[start:end]
            self.assertIn("uses: actions/checkout@", checkout)
            self.assertRegex(checkout, r"(?m)^\s+fetch-depth:\s*0\s*$")
        require_full_history(workflow)
        for broken in (workflow.replace("fetch-depth: 0", "fetch-depth: 1", 1), workflow.replace("          fetch-depth: 0\n", "", 1)):
            with self.assertRaises(AssertionError):
                require_full_history(broken)

    def test_245_real_shallow_history_blocks_console_and_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            source.mkdir()
            identity_repository(source)
            (source / "unrelated.txt").write_text("later release", encoding="utf-8")
            git(source, "add", "unrelated.txt")
            git(source, "commit", "-q", "-m", "later release")
            shallow = Path(directory) / "shallow"
            git(source, "clone", "-q", "--depth=1", source.as_uri(), str(shallow))
            self.assertEqual(git(shallow, "rev-parse", "--is-shallow-repository"), "true")
            release = git(shallow, "rev-parse", "HEAD")
            with main_fixture(shallow, real_identity=True) as (output, _):
                self.assertEqual(validator.main(validated_commit=release), 1)
            self.assertIn("Git history is shallow", output.getvalue())
            report = json.loads((shallow / "assets/audit/validation-report-2026-09-11.json").read_text())
            self.assertTrue(any("Git history is shallow" in issue for issue in report["global_issues"]))
            self.assertGreater(report["total_issues"], 0)
            self.assertEqual(report["provenance"]["validated_commit"], release)

    def test_251_legacy_list_covers_public_pages_and_detects_omission(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index = root / "assets/data/search-index.json"
            index.parent.mkdir(parents=True)
            files = [root / "index.html", root / "about/index.html"]
            for page in files:
                page.parent.mkdir(parents=True, exist_ok=True)
                page.write_text("<title>Fixture</title>", encoding="utf-8")
            entries = [{"url": "https://glee-fully.tools/"}, {"url": "https://glee-fully.tools/about/"}]
            with mock.patch.object(auditor, "ROOT", root):
                index.write_text(json.dumps(entries), encoding="utf-8")
                original = index.read_bytes()
                self.assertEqual(auditor.reconcile_search_index(files), [])
                self.assertEqual(index.read_bytes(), original)
                index.write_text(json.dumps(entries[:1]), encoding="utf-8")
                omitted = index.read_bytes()
                self.assertEqual(auditor.reconcile_search_index(files), ["Page on disk not in search index: about/index.html"])
                self.assertEqual(index.read_bytes(), omitted)

    def test_258_main_preserves_primary_save_error_when_cleanup_also_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with main_fixture(root) as (output, _):
                self.assertEqual(validator.main(validated_commit="a" * 40), 0)
                report = root / "assets/audit/validation-report-2026-09-11.json"
                historical = report.with_name("validation-report-2026-09-10.json")
                historical.write_bytes(b'{"historical":true}\n')
                originals = {path: path.read_bytes() for path in (report, historical)}
                staged = []
                save_error = OSError("fixture report replacement failed")
                cleanup_error = OSError("fixture subsequent cleanup failed")
                def fail_replace(path, destination):
                    self.assertEqual(destination, report)
                    self.assertTrue(path.exists())
                    staged.append(path)
                    raise save_error
                def fail_unlink(path, *, missing_ok=False):
                    self.assertEqual(path, staged[0])
                    self.assertTrue(missing_ok)
                    raise cleanup_error
                output.seek(0)
                output.truncate(0)
                with mock.patch.object(Path, "replace", autospec=True, side_effect=fail_replace), mock.patch.object(Path, "unlink", autospec=True, side_effect=fail_unlink):
                    with self.assertRaises(OSError) as raised:
                        validator.main(validated_commit="b" * 40)
                self.assertIs(raised.exception, save_error)
                self.assertIs(raised.exception.__cause__, cleanup_error)
                self.assertEqual(output.getvalue(), "")
                self.assertEqual(len(staged), 1)
                self.assertTrue(staged[0].exists())
                for path, content in originals.items():
                    self.assertEqual(path.read_bytes(), content)

    def test_285_local_reporting_day_is_independent_of_utc_calendar(self):
        local_day = date(2026, 9, 11)
        for instant in (datetime(2026, 9, 12, 1, tzinfo=timezone.utc), datetime(2026, 9, 10, 23, tzinfo=timezone.utc)):
            with self.subTest(utc=instant), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                with main_fixture(root, local_day=local_day, instant=instant) as (_, clock):
                    self.assertEqual(validator.main(validated_commit="a" * 40), 0)
                    clock.now.assert_called_once_with(timezone.utc)
                reports = list((root / "assets/audit").glob("validation-report-*.json"))
                self.assertEqual([path.name for path in reports], ["validation-report-2026-09-11.json"])
                report = json.loads(reports[0].read_text())
                self.assertEqual(report["run_date"], local_day.isoformat())
                self.assertEqual(report["generated_at"], instant.isoformat().replace("+00:00", "Z"))
                self.assertNotEqual(instant.date(), local_day)


if __name__ == "__main__":
    unittest.main()

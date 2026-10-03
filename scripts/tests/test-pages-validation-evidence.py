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
POST_UPLOAD_JOB = "  verify-validation-evidence:"
RETENTION_VERIFY_STEP = "- name: Verify validation artifact retention"
POST_UPLOAD_VERIFY_STEP = "- name: Verify downloaded browser theme reports"
THEME_SUMMARY_STEP = "- name: Add verified browser theme results to run summary"
DEPLOY_JOB = "  deploy:"
RETENTION_CHECKER = ROOT / "scripts" / "check-pages-validation-retention.py"
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
THEME_INDEX_NAME = "color-scheme-evidence-index.md"
THEME_CASE_LABELS = ("`light`", "`dark`", "`disabled_storage`")


def browser_theme_index() -> str:
    """Return a valid minimal index for exercising the uploaded-artifact gate."""
    rows = [
        "| Browser engine | Browser version | Covered cases | Report |",
        "| --- | --- | --- | --- |",
    ]
    for browser, label, version in browser_versions():
        rows.append(
            f"| {label} | {version} | `light` (saved light preference); "
            f"`dark` (saved dark preference); "
            f"`disabled_storage` (local storage blocked) | "
            f"[`color-scheme-init-{browser}.json`]"
            f"(color-scheme-init-{browser}.json) |"
        )
    return "\n".join(["# Browser color-scheme evidence", "", *rows, ""])


def browser_versions():
    return (
        ("chromium", "Chromium", "136.0.7103.25"),
        ("firefox", "Firefox", "138.0"),
        ("webkit", "WebKit", "18.4"),
    )


def write_browser_theme_reports(audit: Path) -> None:
    for browser, _, version in browser_versions():
        (audit / f"color-scheme-init-{browser}.json").write_text(
            json.dumps({"browser": browser, "browser_version": version}),
            encoding="utf-8",
        )


def audit_report_index_link() -> str:
    return (
        "[browser color-scheme evidence index]"
        "(../audit/color-scheme-evidence-index.md)"
    )


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
    if THEME_INDEX_NAME not in theme_block:
        raise AssertionError(
            "Successful browser theme verification must generate its release index"
        )
    if "browser_version" not in theme_block or "Browser version" not in theme_block:
        raise AssertionError(
            "Browser theme reports and the release index must retain exact browser versions"
        )
    if (
        THEME_INDEX_NAME not in staging_block
        or "../audit/color-scheme-evidence-index.md" not in staging_block
    ):
        raise AssertionError(
            "Validation staging must retain and link the browser theme index"
        )


def assert_uploaded_theme_evidence_contract(workflow: str) -> None:
    """Require a release-level check of the uploaded validation artifact."""
    post_upload_position = workflow.find(POST_UPLOAD_JOB)
    verify_step_position = workflow.find(POST_UPLOAD_VERIFY_STEP)
    summary_step_position = workflow.find(THEME_SUMMARY_STEP)
    deploy_position = workflow.find(DEPLOY_JOB)
    if min(
        post_upload_position,
        verify_step_position,
        summary_step_position,
        deploy_position,
    ) < 0:
        raise AssertionError(
            "Pages workflow must download, verify, and summarize the validation artifact in a separate job"
        )
    if not (
        post_upload_position
        < verify_step_position
        < summary_step_position
        < deploy_position
    ):
        raise AssertionError(
            "Downloaded validation evidence must be checked and summarized before the deploy job"
        )

    job_block = workflow[post_upload_position:deploy_position]
    if "    needs: validate" not in job_block:
        raise AssertionError(
            "Uploaded validation evidence check must run after the release validation job"
        )
    if "      actions: read" not in job_block:
        raise AssertionError(
            "Uploaded validation evidence check needs read access to artifact metadata"
        )
    if RETENTION_VERIFY_STEP not in job_block:
        raise AssertionError(
            "Uploaded validation evidence must have its effective retention checked"
        )
    checkout_position = job_block.find("uses: actions/checkout@v7")
    retention_position = job_block.find(RETENTION_VERIFY_STEP)
    if checkout_position < 0 or checkout_position > retention_position:
        raise AssertionError("Retention checker requires checkout before execution")
    download_position = job_block.find("uses: actions/download-artifact@v8")
    if (
        retention_position < 0
        or download_position < retention_position
        or download_position > job_block.find(POST_UPLOAD_VERIFY_STEP)
    ):
        raise AssertionError(
            "Artifact retention and report accessibility must be checked before deployment"
        )
    if (
        "needs.validate.outputs.validation_artifact_id" not in job_block
        or "scripts/check-pages-validation-retention.py" not in job_block
    ):
        raise AssertionError(
            "Release check must inspect the uploaded artifact's GitHub retention metadata"
        )
    download_block = job_block[download_position:].split("\n      - name:", 1)[0]
    if "name: pages-validation-${{ github.sha }}" not in download_block:
        raise AssertionError(
            "Uploaded validation evidence check must download this commit's artifact"
        )

    validate_block = workflow[
        workflow.find("  validate:"):post_upload_position
    ]
    upload_position = validate_block.find(UPLOAD_STEP)
    if upload_position < 0:
        raise AssertionError("Pages validation artifact upload step is missing")
    upload_block = validate_block[upload_position:].split("\n      - name:", 1)[0]
    if (
        "id: upload_validation_reports" not in upload_block
        or "retention-days: 90" not in upload_block
    ):
        raise AssertionError(
            "Pages validation evidence upload must request the approved 90-day period"
        )
    if (
        "validation_artifact_id: ${{ steps.upload_validation_reports.outputs.artifact-id }}"
        not in validate_block
    ):
        raise AssertionError(
            "The uploaded validation artifact id must be passed to the retention check"
        )

    verify_block = job_block[job_block.find(POST_UPLOAD_VERIFY_STEP):]
    expected_reports = (
        "color-scheme-init-chromium.json",
        "color-scheme-init-firefox.json",
        "color-scheme-init-webkit.json",
    )
    missing_names = [name for name in expected_reports if name not in verify_block]
    if (
        missing_names
        or THEME_INDEX_NAME not in verify_block
        or "audit-report.md" not in verify_block
        or "missing" not in verify_block
    ):
        raise AssertionError(
            "Downloaded validation artifact check must require the reports and their index"
        )
    for case in THEME_CASE_LABELS:
        if case not in verify_block:
            raise AssertionError(
                "Downloaded browser theme index must identify light, dark, "
                "and disabled-storage cases"
            )
    if "browser_version" not in verify_block or "version.strip()" not in verify_block:
        raise AssertionError(
            "Downloaded theme evidence must verify browser versions in both reports and index"
        )

    summary_block = workflow[summary_step_position:deploy_position]
    if (
        "steps.downloaded_theme_evidence.outcome == 'success'" not in summary_block
        or "success()" not in summary_block
        or "VALIDATION_ARTIFACT_DIR: ${{ runner.temp }}/pages-validation"
        not in summary_block
        or "GITHUB_STEP_SUMMARY" not in summary_block
    ):
        raise AssertionError(
            "Run summary must use the downloaded artifact and run only after its verification succeeds"
        )
    for browser in ("Chromium", "Firefox", "WebKit"):
        if browser not in summary_block:
            raise AssertionError(
                f"Run summary must include the {browser} browser engine"
            )
    for case in ("Light preference", "Dark preference", "Disabled storage"):
        if case not in summary_block:
            raise AssertionError(
                f"Run summary must include the {case} browser theme case"
            )

    deploy_block = workflow[deploy_position:]
    deploy_needs = deploy_block.split("\n    runs-on:", 1)[0]
    if (
        "needs: [validate, verify-validation-evidence]" not in deploy_needs
        or "needs: validate" in deploy_needs
    ):
        raise AssertionError(
            "Pages deployment must wait for the separate uploaded-evidence check"
        )


class PagesValidationEvidenceTests(unittest.TestCase):
    def test_retention_checker_requires_repository_checkout(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        before, job = workflow.split(POST_UPLOAD_JOB, 1)
        job, after = job.split(DEPLOY_JOB, 1)
        broken = before + POST_UPLOAD_JOB + job.replace("uses: actions/checkout@v7", "uses: actions/download-artifact@v8", 1) + DEPLOY_JOB + after
        with self.assertRaisesRegex(AssertionError, "requires checkout"):
            assert_uploaded_theme_evidence_contract(broken)

    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_complete_commit_linked_evidence_is_staged_before_upload(self):
        assert_validation_evidence_contract(self.workflow)

    def test_uploaded_validation_artifact_is_checked_before_deployment(self):
        assert_uploaded_theme_evidence_contract(self.workflow)

    def test_run_summary_lists_verified_engines_and_theme_cases(self):
        block = self.workflow.split(THEME_SUMMARY_STEP, 1)[1].split(
            "\n      - name:", 1
        )[0]
        code = textwrap.dedent(
            block.split("python3 - <<'PY'\n", 1)[1].rsplit("          PY", 1)[0]
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = root / "pages-validation" / "assets" / "audit"
            audit.mkdir(parents=True)
            summary_path = root / "step-summary.md"
            for browser, _, version in browser_versions():
                (audit / f"color-scheme-init-{browser}.json").write_text(
                    json.dumps(
                        {
                            "browser": browser,
                            "browser_version": version,
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
            env = {
                **os.environ,
                "VALIDATION_ARTIFACT_DIR": str(root / "pages-validation"),
                "GITHUB_STEP_SUMMARY": str(summary_path),
            }
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = summary_path.read_text(encoding="utf-8")
            for browser, label, version in browser_versions():
                self.assertIn(f"| {label} | {version} | Pass | Pass | Pass |", summary)
                self.assertIn(f"color-scheme-init-{browser}.json", summary)
            for case in (
                "Light preference",
                "Dark preference",
                "Disabled storage",
            ):
                self.assertIn(case, summary)

            (audit / "color-scheme-init-webkit.json").unlink()
            summary_path.unlink()
            failed = subprocess.run(
                [sys.executable, "-c", code],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn(
                "color-scheme-init-webkit.json: cannot read verified browser report",
                failed.stderr,
            )
            self.assertFalse(summary_path.exists())

    def test_artifact_retention_checker_accepts_the_approved_period(self):
        artifact = {
            "id": 123,
            "name": "pages-validation-abc123",
            "expired": False,
            "created_at": "2026-01-01T00:00:00Z",
            "expires_at": "2026-04-01T00:00:00Z",
        }
        result = subprocess.run(
            [
                sys.executable,
                str(RETENTION_CHECKER),
                "--artifact-id",
                "123",
                "--artifact-name",
                "pages-validation-abc123",
            ],
            input=json.dumps(artifact),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("at least 90 days", result.stdout)

    def test_artifact_retention_checker_rejects_short_or_wrong_artifacts(self):
        cases = (
            (
                {
                    "id": 123,
                    "name": "pages-validation-abc123",
                    "expired": False,
                    "created_at": "2026-01-01T00:00:00Z",
                    "expires_at": "2026-03-31T00:00:00Z",
                },
                "shorter than the approved 90 days",
            ),
            (
                {
                    "id": 123,
                    "name": "pages-validation-abc123",
                    "expired": True,
                    "created_at": "2026-01-01T00:00:00Z",
                    "expires_at": "2026-04-01T00:00:00Z",
                },
                "artifact is expired",
            ),
            (
                {
                    "id": 456,
                    "name": "pages-validation-abc123",
                    "expired": False,
                    "created_at": "2026-01-01T00:00:00Z",
                    "expires_at": "2026-04-01T00:00:00Z",
                },
                "expected 123",
            ),
            (
                {
                    "id": 123,
                    "name": "pages-validation-other",
                    "expired": False,
                    "created_at": "2026-01-01T00:00:00Z",
                    "expires_at": "2026-04-01T00:00:00Z",
                },
                "expected 'pages-validation-abc123'",
            ),
        )
        for artifact, expected_error in cases:
            with self.subTest(expected_error=expected_error):
                result = subprocess.run(
                    [
                        sys.executable,
                        str(RETENTION_CHECKER),
                        "--artifact-id",
                        "123",
                        "--artifact-name",
                        "pages-validation-abc123",
                    ],
                    input=json.dumps(artifact),
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_error, result.stderr)

    def test_downloaded_artifact_check_fails_for_each_missing_browser_report(self):
        job_block = self.workflow.split(POST_UPLOAD_JOB, 1)[1].split(DEPLOY_JOB, 1)[0]
        block = job_block.split(POST_UPLOAD_VERIFY_STEP, 1)[1].split(
            THEME_SUMMARY_STEP, 1
        )[0]
        code = textwrap.dedent(
            block.split("python3 - <<'PY'\n", 1)[1].rsplit("          PY", 1)[0]
        )
        expected_reports = (
            "color-scheme-init-chromium.json",
            "color-scheme-init-firefox.json",
            "color-scheme-init-webkit.json",
        )
        for missing_name in expected_reports:
            with self.subTest(missing=missing_name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                audit = root / "assets" / "audit"
                audit.mkdir(parents=True)
                for report_name in expected_reports:
                    if report_name != missing_name:
                        (audit / report_name).write_text("{}", encoding="utf-8")
                (audit / THEME_INDEX_NAME).write_text(
                    browser_theme_index(), encoding="utf-8"
                )
                docs = root / "assets" / "docs"
                docs.mkdir(parents=True)
                (docs / "audit-report.md").write_text(
                    audit_report_index_link(), encoding="utf-8"
                )
                env = {**os.environ, "VALIDATION_ARTIFACT_DIR": str(root)}
                result = subprocess.run(
                    [sys.executable, "-c", code],
                    cwd=root,
                    env=env,
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(missing_name, result.stderr)

    def test_downloaded_artifact_check_fails_when_theme_index_is_missing(self):
        job_block = self.workflow.split(POST_UPLOAD_JOB, 1)[1].split(DEPLOY_JOB, 1)[0]
        block = job_block.split(POST_UPLOAD_VERIFY_STEP, 1)[1].split(
            THEME_SUMMARY_STEP, 1
        )[0]
        code = textwrap.dedent(
            block.split("python3 - <<'PY'\n", 1)[1].rsplit("          PY", 1)[0]
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = root / "assets" / "audit"
            audit.mkdir(parents=True)
            write_browser_theme_reports(audit)
            docs = root / "assets" / "docs"
            docs.mkdir(parents=True)
            (docs / "audit-report.md").write_text(
                audit_report_index_link(), encoding="utf-8"
            )
            env = {**os.environ, "VALIDATION_ARTIFACT_DIR": str(root)}
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(THEME_INDEX_NAME, result.stderr)

    def test_downloaded_artifact_check_accepts_all_browser_reports(self):
        job_block = self.workflow.split(POST_UPLOAD_JOB, 1)[1].split(DEPLOY_JOB, 1)[0]
        block = job_block.split(POST_UPLOAD_VERIFY_STEP, 1)[1].split(
            THEME_SUMMARY_STEP, 1
        )[0]
        code = textwrap.dedent(
            block.split("python3 - <<'PY'\n", 1)[1].rsplit("          PY", 1)[0]
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = root / "assets" / "audit"
            audit.mkdir(parents=True)
            write_browser_theme_reports(audit)
            (audit / THEME_INDEX_NAME).write_text(
                browser_theme_index(), encoding="utf-8"
            )
            docs = root / "assets" / "docs"
            docs.mkdir(parents=True)
            (docs / "audit-report.md").write_text(
                audit_report_index_link(), encoding="utf-8"
            )
            env = {**os.environ, "VALIDATION_ARTIFACT_DIR": str(root)}
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("indexed cases", result.stdout)

    def test_downloaded_artifact_check_rejects_a_version_mismatch(self):
        job_block = self.workflow.split(POST_UPLOAD_JOB, 1)[1].split(DEPLOY_JOB, 1)[0]
        block = job_block.split(POST_UPLOAD_VERIFY_STEP, 1)[1].split(
            THEME_SUMMARY_STEP, 1
        )[0]
        code = textwrap.dedent(
            block.split("python3 - <<'PY'\n", 1)[1].rsplit("          PY", 1)[0]
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = root / "assets" / "audit"
            audit.mkdir(parents=True)
            write_browser_theme_reports(audit)
            mismatched_index = browser_theme_index().replace(
                "136.0.7103.25", "136.0.7103.26"
            )
            (audit / THEME_INDEX_NAME).write_text(
                mismatched_index, encoding="utf-8"
            )
            docs = root / "assets" / "docs"
            docs.mkdir(parents=True)
            (docs / "audit-report.md").write_text(
                audit_report_index_link(), encoding="utf-8"
            )
            env = {**os.environ, "VALIDATION_ARTIFACT_DIR": str(root)}
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("incomplete browser theme index", result.stderr)

    def test_theme_verification_generates_index_for_all_engines_and_cases(self):
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
            versions = dict((browser, version) for browser, _, version in browser_versions())
            for browser, _, version in browser_versions():
                (audit / f"color-scheme-init-{browser}.json").write_text(
                    json.dumps(
                        {
                            "browser": browser,
                            "browser_version": version,
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
            self.assertEqual(result.returncode, 0, result.stderr)
            index = (audit / THEME_INDEX_NAME).read_text(encoding="utf-8")
            for browser, label in (
                ("chromium", "Chromium"),
                ("firefox", "Firefox"),
                ("webkit", "WebKit"),
            ):
                self.assertIn(label, index)
                self.assertIn(f"color-scheme-init-{browser}.json", index)
                self.assertIn(versions[browser], index)
            self.assertIn("Browser version", index)
            for case in THEME_CASE_LABELS:
                self.assertIn(case, index)

    def test_theme_verification_rejects_missing_browser_version(self):
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
            for browser, _, version in browser_versions():
                report = {
                    "browser": browser,
                    "status": "PASS",
                    "cases": {
                        "light": {},
                        "dark": {},
                        "disabled_storage": {},
                    },
                }
                if browser != "webkit":
                    report["browser_version"] = version
                (audit / f"color-scheme-init-{browser}.json").write_text(
                    json.dumps(report), encoding="utf-8"
                )
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=root,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "color-scheme-init-webkit.json: browser_version must be a non-empty string",
                result.stderr,
            )

    def test_staging_links_the_generated_index_from_the_copied_audit_report(self):
        block = self.workflow.split(STAGING_STEP, 1)[1].split(UPLOAD_STEP, 1)[0]
        code = textwrap.dedent(
            block.split("python3 - <<'PY'\n", 1)[1].rsplit("          PY", 1)[0]
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = root / "assets" / "audit"
            audit.mkdir(parents=True)
            for browser, _, version in browser_versions():
                (audit / f"color-scheme-init-{browser}.json").write_text(
                    json.dumps(
                        {"browser": browser, "browser_version": version}
                    ),
                    encoding="utf-8",
                )
            (audit / THEME_INDEX_NAME).write_text(browser_theme_index(), encoding="utf-8")
            (audit / "validation-report-2026-10-02.json").write_text(
                '{"current": true}', encoding="utf-8"
            )
            (audit / "validation-report-2026-10-01.json").write_text(
                '{"historical": true}', encoding="utf-8"
            )
            (audit / "links-report-2026-10-02.json").write_text(
                '{"audit": true}', encoding="utf-8"
            )
            docs = root / "assets" / "docs"
            docs.mkdir(parents=True)
            (docs / "audit-report.md").write_text(
                "# Audit report\n", encoding="utf-8"
            )
            artifact = root / "validation-artifact"
            env = {
                **os.environ,
                "VALIDATION_ARTIFACT_DIR": str(artifact),
                "VALIDATION_REPORT_NAME": "validation-report-2026-10-02.json",
            }
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            staged_audit = artifact / "assets" / "audit"
            self.assertTrue((staged_audit / THEME_INDEX_NAME).is_file())
            staged_index = (staged_audit / THEME_INDEX_NAME).read_text(
                encoding="utf-8"
            )
            for browser, _, version in browser_versions():
                staged_report = json.loads(
                    (staged_audit / f"color-scheme-init-{browser}.json").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(staged_report["browser_version"], version)
                self.assertIn(version, staged_index)
            self.assertTrue(
                (staged_audit / "validation-report-2026-10-02.json").is_file()
            )
            self.assertFalse(
                (staged_audit / "validation-report-2026-10-01.json").exists()
            )
            self.assertTrue((staged_audit / "links-report-2026-10-02.json").is_file())
            staged_summary = (
                artifact / "assets" / "docs" / "audit-report.md"
            ).read_text(encoding="utf-8")
            self.assertIn(audit_report_index_link(), staged_summary)

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

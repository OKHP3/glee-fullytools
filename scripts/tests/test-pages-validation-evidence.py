#!/usr/bin/env python3
"""Contract tests for complete, commit-linked Pages validation evidence."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
import hashlib
from io import BytesIO, StringIO
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import traceback
import unittest
from types import ModuleType, SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler
import zipfile
import zlib
from contextlib import redirect_stderr, redirect_stdout


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"
PROVENANCE_STEP = "- name: Verify validation report provenance"
STAGING_STEP = "- name: Stage complete validation evidence"
UPLOAD_STEP = "- name: Upload validation reports"
THEME_VERIFY_STEP = "- name: Verify browser-specific theme evidence"
THEME_BROWSER_STEP = "- name: Run color-scheme bootstrap regression in all installed engines"
THEME_FAILURE_DIAGNOSTIC_STEP = "- name: Summarize browser theme failures (diagnostic only)"
THEME_FAILURE_UPLOAD_STEP = "- name: Upload failed browser theme reports (diagnostic only)"
THEME_FAILURE_LINK_STEP = "- name: Link browser theme failure diagnostics"
RESPONSIVE_QA_STEP = "- name: Run browser responsive and asset QA"
RESPONSIVE_FAILURE_UPLOAD_STEP = (
    "- name: Upload failed responsive QA report (diagnostic only)"
)
RESPONSIVE_FAILURE_LINK_STEP = "- name: Link responsive QA failure diagnostics"
VISITOR_ACCEPTANCE_STEP = "- name: Run visitor, privacy, and rendered contrast acceptance"
VISITOR_FAILURE_UPLOAD_STEP = (
    "- name: Upload failed visitor acceptance report (diagnostic only)"
)
VISITOR_FAILURE_LINK_STEP = "- name: Link visitor acceptance failure diagnostics"
POST_UPLOAD_JOB = "  verify-validation-evidence:"
RETENTION_VERIFY_STEP = "- name: Verify validation artifact retention"
POST_UPLOAD_VERIFY_STEP = "- name: Verify downloaded browser theme reports"
THEME_SUMMARY_STEP = "- name: Add verified browser theme results to run summary"
DEPLOY_JOB = "  deploy:"
RETENTION_CHECKER = ROOT / "scripts" / "check-pages-validation-retention.py"
RETENTION_WORKFLOW = ROOT / ".github" / "workflows" / "pages-validation-retention.yml"
RETENTION_SPEC = importlib.util.spec_from_file_location(
    "check_pages_validation_retention", RETENTION_CHECKER
)
retention_checker = importlib.util.module_from_spec(RETENTION_SPEC)
RETENTION_SPEC.loader.exec_module(retention_checker)
COLOR_SCHEME_SCRIPT = ROOT / "scripts" / "tests" / "test-color-scheme-init.py"
COLOR_SCHEME_SPEC = importlib.util.spec_from_file_location(
    "color_scheme_init_browser_check", COLOR_SCHEME_SCRIPT
)
color_scheme_checker = importlib.util.module_from_spec(COLOR_SCHEME_SPEC)
COLOR_SCHEME_SPEC.loader.exec_module(color_scheme_checker)
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
COMPLETE_AUDIT_COPY = 'shutil.copytree("assets/audit", audit_dir,'
THEME_BROWSER_LOOP = "for browser in chromium firefox webkit; do"
THEME_REPORT_PATTERN = "color-scheme-init-$browser.json"
THEME_INDEX_NAME = "color-scheme-evidence-index.md"
THEME_CASE_LABELS = ("`light`", "`dark`", "`disabled_storage`")


class FakeDownloadResponse:
    def __init__(self, status, body=b"", headers=None):
        self.status = status
        self._body = BytesIO(body)
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self, size=-1):
        return self._body.read(size)


def valid_artifact_archive(
    missing_file=None, additional_files=None, duplicate_files=None
):
    contents = {
        "assets/audit/color-scheme-init-chromium.json": b'{"browser":"chromium"}',
        "assets/audit/color-scheme-init-firefox.json": b'{"browser":"firefox"}',
        "assets/audit/color-scheme-init-webkit.json": b'{"browser":"webkit"}',
        "assets/audit/color-scheme-evidence-index.md": b"# Browser theme evidence",
        "assets/docs/audit-report.md": b"# Audit report",
    }
    contents.update(additional_files or {})
    if missing_file is not None:
        contents.pop(missing_file)
    archive = BytesIO()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
        for name, content in contents.items():
            zipped.writestr(name, content)
        for name, content in duplicate_files or []:
            zipped.writestr(name, content)
    return archive.getvalue()


def artifact_archive_with_special_required_entry(report_path, entry_attributes, creator=3):
    """Build a complete artifact with controlled required-entry metadata."""
    contents = {
        "assets/audit/color-scheme-init-chromium.json": b'{"browser":"chromium"}',
        "assets/audit/color-scheme-init-firefox.json": b'{"browser":"firefox"}',
        "assets/audit/color-scheme-init-webkit.json": b'{"browser":"webkit"}',
        "assets/audit/color-scheme-evidence-index.md": b"# Browser theme evidence",
        "assets/docs/audit-report.md": b"# Audit report",
    }
    archive = BytesIO()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
        for name, content in contents.items():
            if name == report_path:
                entry = zipfile.ZipInfo(name)
                entry.create_system = creator
                entry.external_attr = entry_attributes
                zipped.writestr(entry, content)
            else:
                zipped.writestr(name, content)
    return archive.getvalue()


def zip_fixture_header_offsets(archive, report_path):
    """Locate the exact local and central records in a controlled ZIP fixture."""
    with zipfile.ZipFile(BytesIO(archive)) as zipped:
        local_offset = zipped.getinfo(report_path).header_offset
        central_offset = zipped.start_dir
        for entry in zipped.infolist():
            if bytes(archive[central_offset:central_offset + 4]) != b"PK\x01\x02":
                raise AssertionError("invalid fixture central directory")
            name_length = int.from_bytes(archive[central_offset + 28:central_offset + 30], "little")
            extra_length = int.from_bytes(archive[central_offset + 30:central_offset + 32], "little")
            comment_length = int.from_bytes(archive[central_offset + 32:central_offset + 34], "little")
            name = bytes(archive[central_offset + 46:central_offset + 46 + name_length])
            if entry.filename == report_path:
                if name != report_path.encode("utf-8"):
                    raise AssertionError("fixture central name mismatch")
                return local_offset, central_offset
            central_offset += 46 + name_length + extra_length + comment_length
    raise AssertionError("fixture member not found")


def artifact_archive_with_invalid_utf8_optional_name(report_path, header):
    archive = bytearray(valid_artifact_archive(additional_files={report_path: b"data"}))
    local, central = zip_fixture_header_offsets(archive, report_path)
    flags_offset, name_offset = ((local + 6, local + 30) if header == "local"
                                 else (central + 8, central + 46))
    flags = int.from_bytes(archive[flags_offset:flags_offset + 2], "little") | 0x800
    archive[flags_offset:flags_offset + 2] = flags.to_bytes(2, "little")
    archive[name_offset] = 0xFF
    return bytes(archive)


def artifact_archive_with_required_entry_flags(report_path, *, local_flags=1, central_flags=1, source=None):
    """Set flags in the named records, never by searching arbitrary payload bytes."""
    archive = bytearray(valid_artifact_archive() if source is None else source)
    local, central = zip_fixture_header_offsets(archive, report_path)
    for offset, bits in ((local + 6, local_flags), (central + 8, central_flags)):
        flags = int.from_bytes(archive[offset:offset + 2], "little") | bits
        archive[offset:offset + 2] = flags.to_bytes(2, "little")
    return bytes(archive)


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


def theme_failure_diagnostic_code(workflow: str) -> str:
    block = workflow.split(THEME_FAILURE_DIAGNOSTIC_STEP, 1)[1].split(
        "\n      - name:", 1
    )[0]
    return textwrap.dedent(
        block.split("python3 - <<'PY'\n", 1)[1].rsplit("          PY", 1)[0]
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
        for label in (
            PROVENANCE_STEP,
            STAGING_STEP,
            UPLOAD_STEP,
            THEME_BROWSER_STEP,
            THEME_FAILURE_DIAGNOSTIC_STEP,
            THEME_FAILURE_UPLOAD_STEP,
            THEME_FAILURE_LINK_STEP,
            RESPONSIVE_QA_STEP,
            RESPONSIVE_FAILURE_UPLOAD_STEP,
            RESPONSIVE_FAILURE_LINK_STEP,
            VISITOR_ACCEPTANCE_STEP,
            VISITOR_FAILURE_UPLOAD_STEP,
            VISITOR_FAILURE_LINK_STEP,
            *LATE_EVIDENCE_STEPS,
        )
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
    if COMPLETE_AUDIT_COPY not in staging_block or 'shutil.ignore_patterns("browser-acceptance.json")' not in staging_block:
        raise AssertionError(
            "Validation evidence staging must copy the audit directory while excluding stale visitor output"
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
    browser_gate_position = positions[THEME_BROWSER_STEP]
    diagnostic_position = positions[THEME_FAILURE_DIAGNOSTIC_STEP]
    if not browser_gate_position < diagnostic_position < theme_position:
        raise AssertionError(
            "Browser failure diagnostics must run after the browser gate and "
            "before verified theme evidence"
        )
    diagnostic_block = workflow[diagnostic_position:theme_position]
    if (
        "always() && steps.theme_browser_checks.outcome == 'failure'"
        not in diagnostic_block
        or "GITHUB_STEP_SUMMARY" not in diagnostic_block
        or "not validated release evidence" not in diagnostic_block
    ):
        raise AssertionError(
            "Browser failure summaries must be failure-only, diagnostic, and "
            "separate from validated release evidence"
        )
    diagnostic_upload_position = positions[THEME_FAILURE_UPLOAD_STEP]
    diagnostic_link_position = positions[THEME_FAILURE_LINK_STEP]
    if not (
        diagnostic_position < diagnostic_upload_position
        < diagnostic_link_position < theme_position
    ):
        raise AssertionError(
            "Failed browser JSON must be uploaded and linked before verified theme evidence"
        )
    diagnostic_upload_block = workflow[diagnostic_upload_position:diagnostic_link_position]
    if (
        "always() && steps.theme_browser_checks.outcome == 'failure'"
        not in diagnostic_upload_block
        or "uses: actions/upload-artifact@v7" not in diagnostic_upload_block
        or "name: pages-theme-failure-diagnostics-${{ github.sha }}"
        not in diagnostic_upload_block
        or "path: assets/audit/color-scheme-init-*.json"
        not in diagnostic_upload_block
        or "if-no-files-found: warn" not in diagnostic_upload_block
        or "retention-days: 14" not in diagnostic_upload_block
        or "pages-validation" in diagnostic_upload_block
        or "glee-public-site" in diagnostic_upload_block
    ):
        raise AssertionError(
            "Failed browser JSON must be available in a separate diagnostic-only artifact"
        )
    diagnostic_link_block = workflow[diagnostic_link_position:theme_position]
    if (
        "always() && steps.theme_browser_checks.outcome == 'failure'"
        not in diagnostic_link_block
        or "GITHUB_STEP_SUMMARY" not in diagnostic_link_block
        or "Diagnostic only" not in diagnostic_link_block
        or "not validated release evidence" not in diagnostic_link_block
        or "actions/runs/${{ github.run_id }}#artifacts" not in diagnostic_link_block
    ):
        raise AssertionError(
            "Failed browser run summary must link the downloadable diagnostic artifact "
            "without presenting it as validated evidence"
        )
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

    responsive_position = positions[RESPONSIVE_QA_STEP]
    responsive_upload_position = positions[RESPONSIVE_FAILURE_UPLOAD_STEP]
    responsive_link_position = positions[RESPONSIVE_FAILURE_LINK_STEP]
    visitor_acceptance_position = workflow.find(
        "- name: Run visitor, privacy, and rendered contrast acceptance"
    )
    if not (
        responsive_position
        < responsive_upload_position
        < responsive_link_position
        < visitor_acceptance_position
        < staging_position
    ):
        raise AssertionError(
            "Failed responsive QA reports must be uploaded and linked immediately "
            "after the QA gate, before validation evidence staging"
        )
    visitor_acceptance_position = positions[VISITOR_ACCEPTANCE_STEP]
    visitor_upload_position = positions[VISITOR_FAILURE_UPLOAD_STEP]
    visitor_link_position = positions[VISITOR_FAILURE_LINK_STEP]
    resilient_qa_position = workflow.find("- name: Run resilient web behavior QA")
    if not (
        visitor_acceptance_position
        < visitor_upload_position
        < visitor_link_position
        < resilient_qa_position
        < staging_position
    ):
        raise AssertionError(
            "Failed visitor acceptance reports must be uploaded and linked "
            "immediately after the acceptance gate, before validation staging"
        )
    visitor_gate_block = workflow[
        visitor_acceptance_position:visitor_upload_position
    ]
    if (
        "id: visitor_acceptance" not in visitor_gate_block
        or 'mktemp -d "$RUNNER_TEMP/glee-visitor-qa.XXXXXXXX"' not in visitor_gate_block
        or 'rm -f' in visitor_gate_block
        or 'continue-on-error' in visitor_gate_block
        or '--diagnostic-output "$report_path" --success-output "$success_path"' not in visitor_gate_block
        or '--validate-failure "$VISITOR_FAILURE_REPORT"' not in visitor_gate_block
        or "report_path=%s\\n" not in visitor_gate_block
        or "scripts/tests/test_browser_acceptance.py" not in visitor_gate_block
    ):
        raise AssertionError(
            "Visitor acceptance must isolate and validate its current-run reports"
        )
    visitor_upload_block = workflow[visitor_upload_position:visitor_link_position]
    if (
        "always() && steps.visitor_acceptance.outcome == 'failure'"
        not in visitor_upload_block
        or "steps.visitor_diagnostic_validation.outcome == 'success'" not in visitor_upload_block
        or "uses: actions/upload-artifact@v7" not in visitor_upload_block
        or "name: pages-visitor-acceptance-failure-diagnostics-${{ github.sha }}"
        not in visitor_upload_block
        or "path: ${{ steps.visitor_acceptance.outputs.report_path }}"
        not in visitor_upload_block
        or "if-no-files-found: warn" not in visitor_upload_block
        or "retention-days: 14" not in visitor_upload_block
        or "pages-validation" in visitor_upload_block
        or "glee-public-site" in visitor_upload_block
    ):
        raise AssertionError(
            "Failed visitor acceptance JSON must be available in a separate "
            "failure-only diagnostic artifact"
        )
    visitor_link_block = workflow[visitor_link_position:resilient_qa_position]
    if (
        "always() && steps.visitor_acceptance.outcome == 'failure'"
        not in visitor_link_block
        or "GITHUB_STEP_SUMMARY" not in visitor_link_block
        or "Diagnostic only" not in visitor_link_block
        or "not validated release evidence" not in visitor_link_block
        or "steps.upload_visitor_failure_diagnostics.outcome" not in visitor_link_block
        or "steps.upload_visitor_failure_diagnostics.outputs.artifact-id" not in visitor_link_block
        or "steps.upload_visitor_failure_diagnostics.outputs.artifact-url" not in visitor_link_block
        or '[ "$UPLOAD_OUTCOME" = success ] && [ -n "$ARTIFACT_ID" ] && [ -n "$ARTIFACT_URL" ]' not in visitor_link_block
        or "report unavailable" not in visitor_link_block
    ):
        raise AssertionError(
            "Failed visitor acceptance summary must link the diagnostic artifact "
            "without presenting it as validated evidence"
        )
    responsive_block = workflow[responsive_position:responsive_upload_position]
    if (
        "id: responsive_asset_qa" not in responsive_block
        or 'mktemp -d "$RUNNER_TEMP/glee-responsive-qa.XXXXXXXX"' not in responsive_block
        or '--diagnostic-output "$report_path" --success-output "$success_path"' not in responsive_block
        or "rm -f" in responsive_block
        or "continue-on-error" in responsive_block
    ):
        raise AssertionError("Responsive QA must use a fresh isolated report path and remain a gate")
    responsive_upload_block = workflow[responsive_upload_position:responsive_link_position]
    if (
        "always() && steps.responsive_asset_qa.outcome == 'failure'" not in responsive_upload_block
        or "steps.responsive_diagnostic_validation.outcome == 'success'" not in responsive_upload_block
        or "uses: actions/upload-artifact@v7" not in responsive_upload_block
        or "path: ${{ steps.responsive_asset_qa.outputs.report_path }}" not in responsive_upload_block
        or "if-no-files-found: warn" not in responsive_upload_block
        or "retention-days: 14" not in responsive_upload_block
        or "pages-validation" in responsive_upload_block
        or "glee-public-site" in responsive_upload_block
    ):
        raise AssertionError("Responsive failure upload must be isolated and failure-only")
    responsive_link_block = workflow[responsive_link_position:visitor_acceptance_position]
    if (
        "always() && steps.responsive_asset_qa.outcome == 'failure'" not in responsive_link_block
        or "steps.upload_responsive_qa_failure_diagnostics.outcome" not in responsive_link_block
        or "steps.upload_responsive_qa_failure_diagnostics.outputs.artifact-id" not in responsive_link_block
        or "steps.upload_responsive_qa_failure_diagnostics.outputs.artifact-url" not in responsive_link_block
        or '[ "$UPLOAD_OUTCOME" = success ] && [ -n "$ARTIFACT_ID" ] && [ -n "$ARTIFACT_URL" ]' not in responsive_link_block
        or "report unavailable" not in responsive_link_block
        or "not validated release evidence" not in responsive_link_block
    ):
        raise AssertionError("Responsive summary must distinguish uploaded and unavailable evidence")
    if "if: ${{ success() &&" not in staging_block:
        raise AssertionError(
            "Failed responsive QA must remain excluded from complete validation evidence"
        )
    if 'browser-acceptance-current-run.json' not in staging_block:
        raise AssertionError(
            "Visitor acceptance success evidence must be staged from the current run"
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
    retention_block = job_block[retention_position:download_position]
    required_run_binding = (
        "EXPECTED_RUN_ID: ${{ github.run_id }}",
        "EXPECTED_COMMIT: ${{ github.sha }}",
        "actions/runs/$EXPECTED_RUN_ID",
        '--output "$RUNNER_TEMP/pages-workflow-run.json"',
        '--run-metadata "$RUNNER_TEMP/pages-workflow-run.json"',
        '--run-id "$EXPECTED_RUN_ID"',
        '--commit "$EXPECTED_COMMIT"',
    )
    if any(binding not in retention_block for binding in required_run_binding):
        raise AssertionError("Retention check must fetch and bind the current workflow run and commit")
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

    def test_retention_checker_requires_authenticated_run_metadata_and_release_identity(self):
        before, retention = self.workflow.split(RETENTION_VERIFY_STEP, 1)
        for binding in (
            "EXPECTED_RUN_ID: ${{ github.run_id }}",
            "EXPECTED_COMMIT: ${{ github.sha }}",
            "actions/runs/$EXPECTED_RUN_ID",
            '--output "$RUNNER_TEMP/pages-workflow-run.json"',
            '--run-metadata "$RUNNER_TEMP/pages-workflow-run.json"',
            '--run-id "$EXPECTED_RUN_ID"',
            '--commit "$EXPECTED_COMMIT"',
        ):
            with self.subTest(binding=binding):
                with self.assertRaisesRegex(AssertionError, "fetch and bind"):
                    assert_uploaded_theme_evidence_contract(
                        before + RETENTION_VERIFY_STEP + retention.replace(binding, "missing", 1)
                    )

    def test_scheduled_retention_workflow_is_read_only_and_daily(self):
        workflow = RETENTION_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('cron: "17 12 * * *"', workflow)
        self.assertIn("timeout-minutes: 10", workflow)
        self.assertIn("actions: read", workflow)
        self.assertIn("--monitor-window", workflow)
        self.assertIn("GITHUB_TOKEN: ${{ github.token }}", workflow)
        self.assertIn("Check Pages validation evidence remains downloadable", workflow)
        self.assertNotIn("actions/deploy-pages", workflow)
        self.assertEqual(retention_checker.MONITOR_RUNTIME_BUDGET_SECONDS, 7 * 60)
        self.assertGreaterEqual(
            10 * 60 - retention_checker.MONITOR_RUNTIME_BUDGET_SECONDS, 3 * 60
        )

    def test_shared_monitor_budget_identifies_runs_left_unchecked(self):
        now = datetime(2026, 10, 13, tzinfo=timezone.utc)
        runs = [
            {
                "id": 44,
                "head_sha": "a" * 40,
                "created_at": "2026-10-01T12:00:00Z",
                "conclusion": "success",
            },
            {
                "id": 45,
                "head_sha": "b" * 40,
                "created_at": "2026-10-02T12:00:00Z",
                "conclusion": "success",
            },
        ]
        elapsed = [0.0]
        sleeps = []
        budget = retention_checker._RuntimeBudget(
            3,
            clock=lambda: elapsed[0],
            sleeper=lambda seconds: (
                sleeps.append(seconds),
                elapsed.__setitem__(0, elapsed[0] + seconds),
            ),
        )

        def fetch(url, token):
            if "/workflows/pages.yml/runs?" in url:
                return {"workflow_runs": runs}, None
            if "/compare/" in url:
                return {"status": "ahead"}, None
            if "/runs/44/artifacts?" in url:
                return {
                    "artifacts": [{
                        "id": 440,
                        "name": f"pages-validation-{'a' * 40}",
                        "expired": False,
                        "created_at": "2026-10-01T12:01:00Z",
                        "expires_at": "2026-12-30T12:00:00Z",
                        "workflow_run": {"id": 44, "head_sha": "a" * 40},
                    }]
                }, None
            if "/runs/45/artifacts?" in url:
                return {
                    "artifacts": [{
                        "id": 450,
                        "name": f"pages-validation-{'b' * 40}",
                        "expired": False,
                        "created_at": "2026-10-02T12:01:00Z",
                        "expires_at": "2026-12-31T12:00:00Z",
                        "workflow_run": {"id": 45, "head_sha": "b" * 40},
                    }]
                }, None
            self.fail(f"Unexpected GitHub API request: {url}")

        download_ids = []
        download_timeouts = []

        def open_url(request, timeout):
            download_ids.append(int(request.full_url.rsplit("/", 2)[-2]))
            download_timeouts.append(timeout)
            raise URLError("temporary connection reset")

        with self.assertRaises(ValueError) as raised:
            retention_checker.monitor_repository(
                "owner/repo",
                "https://api.github.com",
                "test-token",
                now=now,
                fetch_page=fetch,
                open_url=open_url,
                budget=budget,
            )

        message = str(raised.exception)
        self.assertIn(
            f"run 44 | commit {'a' * 40} | review deadline "
            "2026-12-30T12:00:00+00:00: evidence not checked; "
            "shared monitor time budget exhausted after 3 seconds",
            message,
        )
        self.assertIn(
            f"run 45 | commit {'b' * 40} | review deadline "
            "2026-12-31T12:00:00+00:00: evidence not checked; "
            "shared monitor time budget exhausted after 3 seconds",
            message,
        )
        self.assertEqual(download_ids, [440, 440])
        self.assertEqual(download_timeouts, [3, 2])
        self.assertEqual(sleeps, [1, 2])

    def test_archive_failure_at_runtime_deadline_cannot_count_as_verified(self):
        elapsed = [0.0]
        commit = "a" * 40
        run = {"id": 44, "head_sha": commit, "created_at": "2026-10-01T12:00:00Z", "conclusion": "success"}
        artifact = {"id": 440, "name": f"pages-validation-{commit}", "expired": False,
                    "created_at": "2026-10-01T12:01:00Z", "expires_at": "2026-12-30T12:00:00Z",
                    "workflow_run": {"id": 44, "head_sha": commit}}

        def fetch(url, token):
            if "/workflows/" in url:
                return {"workflow_runs": [run]}, None
            if "/compare/" in url:
                return {"status": "ahead"}, None
            return {"artifacts": [artifact]}, None

        def invalid_archive(*args, **kwargs):
            elapsed[0] = 3
            raise ValueError("corrupt archive")

        budget = retention_checker._RuntimeBudget(3, clock=lambda: elapsed[0])
        with patch.object(retention_checker, "verify_artifact_download", side_effect=invalid_archive):
            with self.assertRaisesRegex(ValueError, "run 44.*evidence not checked.*budget exhausted"):
                retention_checker.monitor_repository(
                    "owner/repo", "https://api.github.com", "token",
                    now=datetime(2026, 10, 13, tzinfo=timezone.utc), fetch_page=fetch, budget=budget,
                )

    def test_retention_monitor_does_not_require_evidence_from_pre_policy_release(self):
        legacy_run = {
            "id": 32620098281,
            "head_sha": "874297729317108f804d0e1bf65c9c792bb09b37",
            "created_at": "2026-08-23T05:20:14Z",
            "conclusion": "success",
        }
        artifact_requests = []

        def fetch(url, token):
            if "/workflows/pages.yml/runs?" in url:
                return {"workflow_runs": [legacy_run]}, None
            if "/compare/" in url:
                return {"status": "behind"}, None
            artifact_requests.append(url)
            return {"artifacts": []}, None

        checked = retention_checker.monitor_repository(
            "owner/repo", "https://api.github.com", "test-token",
            now=datetime(2026, 10, 13, tzinfo=timezone.utc), fetch_page=fetch,
        )
        self.assertEqual(checked, 0)
        self.assertEqual(artifact_requests, [])

    def test_retention_monitor_rejects_unknown_or_divergent_policy_ancestry(self):
        run = {
            "id": 44, "head_sha": "a" * 40,
            "created_at": "2026-10-12T10:00:00Z", "conclusion": "success",
        }
        for status in ("diverged", None):
            with self.subTest(status=status):
                def fetch(url, token):
                    if "/workflows/pages.yml/runs?" in url:
                        return {"workflow_runs": [run]}, None
                    if "/compare/" in url:
                        return {"status": status}, None
                    self.fail("Uncertain ancestry must not reach artifact lookup")

                with self.assertRaisesRegex(ValueError, "retention-policy ancestry"):
                    retention_checker.monitor_repository(
                        "owner/repo", "https://api.github.com", "test-token",
                        now=datetime(2026, 10, 13, tzinfo=timezone.utc), fetch_page=fetch,
                    )

    def test_retention_monitor_reports_missing_active_artifact_with_commit(self):
        now = datetime(2026, 10, 13, tzinfo=timezone.utc)
        commit = "a" * 40
        run = {
            "id": 44,
            "head_sha": commit,
            "created_at": "2026-10-01T12:00:00Z",
            "conclusion": "success",
        }

        def fetch(url, token):
            if "/workflows/pages.yml/runs?" in url:
                return {"workflow_runs": [run]}, None
            if "/compare/" in url:
                return {"status": "ahead"}, None
            if "/runs/44/artifacts?" in url:
                self.assertIn("include_expired=true", url)
                return {"artifacts": []}, None
            self.fail(f"Unexpected GitHub API request: {url}")

        with self.assertRaisesRegex(
            ValueError,
            rf"run 44 \| commit {commit} \| review deadline "
            r"2026-12-30T12:00:00\+00:00: validation artifact is missing",
        ):
            retention_checker.monitor_repository(
                "owner/repo",
                "https://api.github.com",
                "test-token",
                now=now,
                fetch_page=fetch,
            )

    def test_retention_monitor_retries_temporary_metadata_failures(self):
        now = datetime(2026, 10, 13, tzinfo=timezone.utc)
        commit = "a" * 40
        run = {
            "id": 44,
            "head_sha": commit,
            "created_at": "2026-10-01T12:00:00Z",
            "conclusion": "success",
        }
        artifact = {
            "id": 440,
            "name": f"pages-validation-{commit}",
            "expired": False,
            "created_at": "2026-10-01T12:01:00Z",
            "expires_at": "2026-12-30T12:00:00Z",
            "workflow_run": {"id": 44, "head_sha": commit},
        }
        attempts = {"runs": 0, "compare": 0, "artifacts": 0}

        def fetch(url, token):
            if "/workflows/pages.yml/runs?" in url:
                attempts["runs"] += 1
                if attempts["runs"] == 1:
                    raise URLError("temporary connection reset")
                return {"workflow_runs": [run]}, None
            if "/compare/" in url:
                attempts["compare"] += 1
                if attempts["compare"] == 1:
                    raise HTTPError(url, 503, "Service Unavailable", {}, None)
                return {"status": "ahead"}, None
            if "/runs/44/artifacts?" in url:
                attempts["artifacts"] += 1
                if attempts["artifacts"] == 1:
                    raise URLError("temporary connection reset")
                return {"artifacts": [artifact]}, None
            self.fail(f"Unexpected GitHub API request: {url}")

        def open_url(request, timeout):
            body = valid_artifact_archive()
            return FakeDownloadResponse(
                200, body, {"Content-Length": str(len(body))}
            )

        with patch.object(retention_checker.time, "sleep") as sleep:
            checked = retention_checker.monitor_repository(
                "owner/repo",
                "https://api.github.com",
                "test-token",
                now=now,
                fetch_page=fetch,
                open_url=open_url,
            )

        self.assertEqual(checked, 1)
        self.assertEqual(attempts, {"runs": 2, "compare": 2, "artifacts": 2})
        self.assertEqual(sleep.call_count, 3)

    def test_metadata_retries_honor_server_wait_and_close_error(self):
        for status, headers, delay in (
            (429, {"Retry-After": "7"}, 7),
            (403, {"Retry-After": "8"}, 8),
            (503, {"Retry-After": "9"}, 9),
        ):
            with self.subTest(status=status):
                body = BytesIO(b"temporary failure")
                error = HTTPError("https://api.github.com/test", status, "Retry", headers, body)
                attempts = []

                def fetch(url, token):
                    attempts.append(url)
                    if len(attempts) == 1:
                        raise error
                    self.assertTrue(body.closed)
                    return {"ok": True}, None

                with patch.object(retention_checker.time, "sleep") as sleep:
                    self.assertEqual(
                        retention_checker._fetch_metadata_page("https://api.github.com/test", "token", fetch),
                        ({"ok": True}, None),
                    )
                sleep.assert_called_once_with(delay)
                self.assertTrue(body.closed)

    def test_metadata_server_wait_beyond_budget_defers_without_retry(self):
        body = BytesIO(b"throttled")
        error = HTTPError("https://api.github.com/test", 429, "Retry", {"Retry-After": "120"}, body)
        with patch.object(retention_checker.time, "sleep") as sleep:
            with patch.object(retention_checker, "api_page", side_effect=error) as fetch:
                with self.assertRaisesRegex(ValueError, "metadata.*retry deferred"):
                    retention_checker._fetch_metadata_page("https://api.github.com/test", "token")
        self.assertEqual(fetch.call_count, 1)
        sleep.assert_not_called()
        self.assertTrue(body.closed)

    def test_metadata_http_date_wait_and_budget_deferral(self):
        for header, expected_delay in (
            ("Thu, 01 Jan 1970 00:00:07 GMT", 7),
            ("  Thu, 01 Jan 1970 00:00:07 GMT  ", 7),
            ("Thu, 01 Jan 1970 00:02:00 GMT", None),
            ("Wed, 31 Dec 1969 23:59:59 GMT", 0),
        ):
            with self.subTest(header=header):
                body = BytesIO(b"throttled")
                error = HTTPError("https://api.github.com/test", 429, "Retry", {"Retry-After": header}, body)
                with patch.object(retention_checker.time, "time", return_value=0):
                    with patch.object(retention_checker.time, "sleep") as sleep:
                        with patch.object(retention_checker, "api_page", side_effect=[error, ({"ok": True}, None)]) as fetch:
                            if expected_delay is None:
                                with self.assertRaisesRegex(ValueError, "metadata.*retry deferred"):
                                    retention_checker._fetch_metadata_page("https://api.github.com/test", "token")
                                self.assertEqual(fetch.call_count, 1)
                                sleep.assert_not_called()
                            else:
                                self.assertEqual(retention_checker._fetch_metadata_page("https://api.github.com/test", "token"), ({"ok": True}, None))
                                self.assertEqual(fetch.call_count, 2)
                                sleep.assert_called_once_with(expected_delay)
                self.assertTrue(body.closed)

    def test_metadata_http_date_respects_shared_runtime_budget(self):
        clock = [0.0]
        budget = retention_checker._RuntimeBudget(
            5, clock=lambda: clock[0], sleeper=lambda seconds: clock.__setitem__(0, clock[0] + seconds)
        )
        body = BytesIO(b"throttled")
        error = HTTPError("https://api.github.com/test", 429, "Retry", {"Retry-After": "Thu, 01 Jan 1970 00:00:07 GMT"}, body)
        with patch.object(retention_checker.time, "time", return_value=0):
            with patch.object(retention_checker, "api_page", side_effect=error) as fetch:
                with self.assertRaises(retention_checker._RetryBudgetExceeded):
                    retention_checker._fetch_metadata_page("https://api.github.com/test", "token", budget=budget)
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(clock[0], 5)
        self.assertTrue(body.closed)

    def test_metadata_http_date_respects_remaining_retry_budget(self):
        first = HTTPError("https://api.github.com/test", 429, "Retry", {"Retry-After": "40"}, BytesIO())
        second = HTTPError("https://api.github.com/test", 429, "Retry", {"Retry-After": "Thu, 01 Jan 1970 00:00:30 GMT"}, BytesIO())
        with patch.object(retention_checker.time, "time", return_value=0):
            with patch.object(retention_checker.time, "sleep") as sleep:
                with patch.object(retention_checker, "api_page", side_effect=[first, second]) as fetch:
                    with self.assertRaisesRegex(ValueError, "metadata.*retry deferred"):
                        retention_checker._fetch_metadata_page("https://api.github.com/test", "token")
        self.assertEqual(fetch.call_count, 2)
        sleep.assert_called_once_with(40)
        self.assertTrue(first.closed)
        self.assertTrue(second.closed)

    def test_retry_after_invalid_dates_defer_and_fractional_numbers_remain_valid(self):
        for header in (
            "not-a-date", "Thu, 01 Jan 1970 00:00:07", "nan", "-1",
            "Sat, 31 Dec 2016 23:59:60 GMT",
        ):
            with self.subTest(header=header):
                error = HTTPError("https://api.github.com/test", 429, "Retry", {"Retry-After": header}, BytesIO())
                with self.assertRaisesRegex(ValueError, "invalid Retry-After"):
                    retention_checker._http_download_retry_delay(error, 1)
                error.close()
        error = HTTPError("https://api.github.com/test", 429, "Retry", {"Retry-After": "0.5"}, BytesIO())
        self.assertEqual(retention_checker._http_download_retry_delay(error, 1), 0.5)
        error.close()

    def test_metadata_malformed_retry_after_fails_without_retry(self):
        body = BytesIO(b"throttled")
        error = HTTPError("https://api.github.com/test", 429, "Retry", {"Retry-After": "later"}, body)
        with patch.object(retention_checker, "api_page", side_effect=error) as fetch:
            with patch.object(retention_checker.time, "sleep") as sleep:
                with self.assertRaisesRegex(ValueError, "invalid Retry-After"):
                    retention_checker._fetch_metadata_page("https://api.github.com/test", "token")
        self.assertEqual(fetch.call_count, 1)
        sleep.assert_not_called()
        self.assertTrue(body.closed)

    def test_retry_after_accepts_obsolete_http_dates_without_early_retry(self):
        now = datetime(2026, 10, 27, tzinfo=timezone.utc)
        target = datetime(2069, 11, 6, 8, 49, 37, tzinfo=timezone.utc)
        cases = (
            ("Wednesday, 06-Nov-69 08:49:37 GMT", (target - now).total_seconds()),
            ("Wed Nov  6 08:49:37 2069", (target - now).total_seconds()),
            ("Sunday, 06-Nov-94 08:49:37 GMT", 0),
            ("Tuesday, 27-Oct-76 00:00:00 GMT", (datetime(2076, 10, 27, tzinfo=timezone.utc) - now).total_seconds()),
            ("Tuesday, 27-Oct-76 00:00:01 GMT", 0),
        )
        for header, expected in cases:
            with self.subTest(header=header):
                error = HTTPError("https://api.github.com/test", 429, "Retry", {"Retry-After": header}, BytesIO())
                self.addCleanup(error.close)
                with patch.object(retention_checker.time, "time", return_value=now.timestamp()):
                    self.assertEqual(retention_checker._http_download_retry_delay(error, 1), expected)

        late_century = datetime(2090, 10, 27, tzinfo=timezone.utc)
        exactly_fifty = datetime(2140, 10, 27, tzinfo=timezone.utc)
        error = HTTPError("https://api.github.com/test", 429, "Retry", {"Retry-After": "Thursday, 27-Oct-40 00:00:00 GMT"}, BytesIO())
        self.addCleanup(error.close)
        with patch.object(retention_checker.time, "time", return_value=late_century.timestamp()):
            self.assertEqual(retention_checker._http_download_retry_delay(error, 1), (exactly_fifty - late_century).total_seconds())

    def test_metadata_retry_cannot_outlive_shared_runtime_budget(self):
        clock = [0.0]

        def wait(seconds):
            clock[0] += seconds

        budget = retention_checker._RuntimeBudget(5, clock=lambda: clock[0], sleeper=wait)
        body = BytesIO(b"throttled")
        error = HTTPError("https://api.github.com/test", 429, "Retry", {"Retry-After": "7"}, body)
        with patch.object(retention_checker, "api_page", side_effect=error) as fetch:
            with self.assertRaises(retention_checker._RetryBudgetExceeded):
                retention_checker._fetch_metadata_page("https://api.github.com/test", "token", budget=budget)
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(clock[0], 5)
        self.assertTrue(body.closed)

    def test_retention_monitor_reports_permanent_metadata_failure_for_run(self):
        now = datetime(2026, 10, 13, tzinfo=timezone.utc)
        commit = "b" * 40
        run = {
            "id": 45,
            "head_sha": commit,
            "created_at": "2026-10-01T12:00:00Z",
            "conclusion": "success",
        }
        artifact_requests = []

        def fetch(url, token):
            if "/workflows/pages.yml/runs?" in url:
                return {"workflow_runs": [run]}, None
            if "/compare/" in url:
                return {"status": "ahead"}, None
            if "/runs/45/artifacts?" in url:
                artifact_requests.append(url)
                raise HTTPError(url, 403, "Forbidden", {}, None)
            self.fail(f"Unexpected GitHub API request: {url}")

        with patch.object(retention_checker.time, "sleep") as sleep:
            with self.assertRaises(ValueError) as raised:
                retention_checker.monitor_repository(
                    "owner/repo",
                    "https://api.github.com",
                    "test-token",
                    now=now,
                    fetch_page=fetch,
                )

        message = str(raised.exception)
        self.assertIn(f"run 45 | commit {commit} | review deadline ", message)
        self.assertIn("GitHub metadata request failed with HTTP 403", message)
        self.assertEqual(len(artifact_requests), 1)
        sleep.assert_not_called()

    def test_retention_monitor_stops_retrying_temporary_metadata_failure(self):
        now = datetime(2026, 10, 13, tzinfo=timezone.utc)
        commit = "c" * 40
        run = {
            "id": 46,
            "head_sha": commit,
            "created_at": "2026-10-01T12:00:00Z",
            "conclusion": "success",
        }
        artifact_requests = []

        def fetch(url, token):
            if "/workflows/pages.yml/runs?" in url:
                return {"workflow_runs": [run]}, None
            if "/compare/" in url:
                return {"status": "ahead"}, None
            if "/runs/46/artifacts?" in url:
                artifact_requests.append(url)
                raise HTTPError(url, 503, "Service Unavailable", {}, None)
            self.fail(f"Unexpected GitHub API request: {url}")

        with patch.object(retention_checker.time, "sleep") as sleep:
            with self.assertRaises(ValueError) as raised:
                retention_checker.monitor_repository(
                    "owner/repo",
                    "https://api.github.com",
                    "test-token",
                    now=now,
                    fetch_page=fetch,
                )

        message = str(raised.exception)
        self.assertIn(f"run 46 | commit {commit} | review deadline ", message)
        self.assertIn(
            "GitHub metadata request failed after 3 attempts (HTTP 503)", message
        )
        self.assertEqual(len(artifact_requests), 3)
        self.assertEqual(sleep.call_count, 2)

    def test_retention_monitor_reports_every_active_run_with_invalid_or_missing_evidence(self):
        now = datetime(2026, 10, 13, tzinfo=timezone.utc)
        first_commit = "a" * 40
        second_commit = "b" * 40
        runs = [
            {
                "id": 44,
                "head_sha": first_commit,
                "created_at": "2026-10-01T12:00:00Z",
                "conclusion": "success",
            },
            {
                "id": 45,
                "head_sha": second_commit,
                "created_at": "2026-10-02T12:00:00Z",
                "conclusion": "success",
            },
        ]
        requests = []
        invalid_artifact = {
            "id": 450,
            "name": f"pages-validation-{second_commit}",
            "expired": True,
            "created_at": "2026-10-02T12:01:00Z",
            "expires_at": "2026-12-31T12:00:00Z",
            "workflow_run": {"id": 45, "head_sha": second_commit},
        }

        def fetch(url, token):
            if "/workflows/pages.yml/runs?" in url:
                return {"workflow_runs": runs}, None
            if "/compare/" in url:
                return {"status": "ahead"}, None
            if "/runs/" in url and "/artifacts?" in url:
                run_id = int(url.split("/runs/", 1)[1].split("/", 1)[0])
                requests.append(run_id)
                if run_id == 44:
                    return {"artifacts": []}, None
                return {"artifacts": [invalid_artifact]}, None
            self.fail(f"Unexpected GitHub API request: {url}")

        with self.assertRaises(ValueError) as raised:
            retention_checker.monitor_repository(
                "owner/repo",
                "https://api.github.com",
                "test-token",
                now=now,
                fetch_page=fetch,
            )

        message = str(raised.exception)
        self.assertIn("problems in active review windows (2)", message)
        self.assertIn(
            f"run 44 | commit {first_commit} | review deadline "
            "2026-12-30T12:00:00+00:00: validation artifact is missing",
            message,
        )
        self.assertIn(
            f"run 45 | commit {second_commit} | review deadline "
            "2026-12-31T12:00:00+00:00: validation artifact is invalid or unavailable: "
            "GitHub reports that the validation artifact is expired",
            message,
        )
        self.assertEqual(requests, [44, 45])

    def test_retention_monitor_checks_successful_runs_only_inside_window(self):
        now = datetime(2026, 10, 13, tzinfo=timezone.utc)
        commit = "b" * 40
        active_run = {
            "id": 51,
            "head_sha": commit,
            "created_at": "2026-10-01T12:00:00Z",
            "conclusion": "success",
        }
        old_run = {
            "id": 52,
            "head_sha": "c" * 40,
            "created_at": "2026-07-01T12:00:00Z",
            "conclusion": "success",
        }
        failed_run = {
            "id": 53,
            "head_sha": "d" * 40,
            "created_at": "2026-10-05T12:00:00Z",
            "conclusion": "failure",
        }
        artifact = {
            "id": 501,
            "name": f"pages-validation-{commit}",
            "expired": False,
            "digest": "sha256:" + hashlib.sha256(valid_artifact_archive()).hexdigest(),
            "created_at": "2026-10-01T12:01:00Z",
            "expires_at": "2026-12-30T12:00:00Z",
            "workflow_run": {"id": 51, "head_sha": commit},
        }
        requested_runs = []
        requested_downloads = []

        def fetch(url, token):
            if "/workflows/pages.yml/runs?" in url:
                return {
                    "workflow_runs": [active_run, old_run, failed_run]
                }, None
            if "/compare/" in url:
                return {"status": "ahead"}, None
            if "/runs/" in url and "/artifacts?" in url:
                run_id = int(url.split("/runs/", 1)[1].split("/", 1)[0])
                requested_runs.append(run_id)
                return {"artifacts": [artifact]}, None
            self.fail(f"Unexpected GitHub API request: {url}")

        def open_url(request, timeout):
            requested_downloads.append((request.full_url, request.get_method(), timeout))
            body = valid_artifact_archive()
            return FakeDownloadResponse(
                200,
                body,
                {"Content-Length": str(len(body))},
            )

        output = StringIO()
        with redirect_stdout(output):
            checked = retention_checker.monitor_repository(
                "owner/repo",
                "https://api.github.com",
                "test-token",
                now=now,
                fetch_page=fetch,
                open_url=open_url,
            )
        self.assertEqual(checked, 1)
        self.assertEqual(output.getvalue(), "")
        self.assertEqual(requested_runs, [51])
        self.assertEqual(
            requested_downloads,
            [(
                "https://api.github.com/repos/owner/repo/actions/artifacts/501/zip",
                "GET",
                30,
            )],
        )

    def test_artifact_authorization_is_not_forwarded_to_download_storage(self):
        def open_url(request, timeout):
            self.assertEqual(request.get_header("Authorization"), "Bearer test-token")
            redirected = HTTPRedirectHandler().redirect_request(
                request, None, 302, "Found", {},
                "https://artifact-storage.example/download.zip",
            )
            self.assertIsNone(redirected.get_header("Authorization"))
            return FakeDownloadResponse(200, valid_artifact_archive())

        retention_checker.verify_artifact_download(
            "owner/repo", 701, "https://api.github.com", "test-token",
            open_url=open_url,
        )

    def test_artifact_download_recovers_after_temporary_transport_failure(self):
        attempts = []

        def open_url(request, timeout):
            attempts.append(request.full_url)
            if len(attempts) == 1:
                raise URLError("temporary connection reset")
            body = valid_artifact_archive()
            return FakeDownloadResponse(
                200, body, {"Content-Length": str(len(body))}
            )

        with patch.object(retention_checker.time, "sleep") as sleep:
            retries = retention_checker.verify_artifact_download(
                "owner/repo",
                701,
                "https://api.github.com",
                "test-token",
                open_url=open_url,
            )

        self.assertEqual(len(attempts), 2)
        self.assertEqual(retries, 1)
        sleep.assert_called_once_with(1)

    def test_retention_monitor_reports_recovered_artifact_download_without_secrets(self):
        now = datetime(2026, 10, 13, tzinfo=timezone.utc)
        commit = "c" * 40
        run = {
            "id": 52,
            "head_sha": commit,
            "created_at": "2026-10-01T12:00:00Z",
            "conclusion": "success",
        }
        artifact = {
            "id": 702,
            "name": f"pages-validation-{commit}",
            "expired": False,
            "created_at": "2026-10-01T12:01:00Z",
            "expires_at": "2026-12-30T12:00:00Z",
            "workflow_run": {"id": 52, "head_sha": commit},
        }
        attempts = []

        def fetch(url, token):
            if "/workflows/pages.yml/runs?" in url:
                return {"workflow_runs": [run]}, None
            if "/compare/" in url:
                return {"status": "ahead"}, None
            if "/runs/52/artifacts?" in url:
                return {"artifacts": [artifact]}, None
            self.fail(f"Unexpected GitHub API request: {url}")

        def open_url(request, timeout):
            attempts.append(request)
            if len(attempts) == 1:
                raise URLError("temporary connection reset")
            body = valid_artifact_archive()
            return FakeDownloadResponse(
                200, body, {"Content-Length": str(len(body))}
            )

        output = StringIO()
        with patch.object(retention_checker.time, "sleep"), redirect_stdout(output):
            checked = retention_checker.monitor_repository(
                "owner/repo",
                "https://api.github.com",
                "test-token",
                now=now,
                fetch_page=fetch,
                open_url=open_url,
            )

        self.assertEqual(checked, 1)
        self.assertEqual(len(attempts), 2)
        message = output.getvalue()
        self.assertIn("after 1 retry (run 52", message)
        self.assertIn(f"run 52, artifact pages-validation-{commit}, ID 702", message)
        self.assertNotIn("test-token", message)
        self.assertNotIn("https://", message)
        self.assertNotIn("artifact-storage", message)

    def test_artifact_download_recovers_after_temporary_server_error(self):
        attempts = []

        def open_url(request, timeout):
            attempts.append(request.full_url)
            if len(attempts) == 1:
                raise HTTPError(request.full_url, 503, "Service Unavailable", {}, None)
            body = valid_artifact_archive()
            return FakeDownloadResponse(
                200, body, {"Content-Length": str(len(body))}
            )

        with patch.object(retention_checker.time, "sleep") as sleep:
            retention_checker.verify_artifact_download(
                "owner/repo",
                701,
                "https://api.github.com",
                "test-token",
                open_url=open_url,
            )

        self.assertEqual(len(attempts), 2)
        sleep.assert_called_once_with(1)

    def test_artifact_download_retries_interrupted_response_body(self):
        attempts = []
        body = valid_artifact_archive()

        class InterruptedResponse(FakeDownloadResponse):
            def read(self, size=-1):
                raise ConnectionResetError("connection reset during transfer")

        def open_url(request, timeout):
            attempts.append(request.full_url)
            if len(attempts) == 1:
                return InterruptedResponse(200, body)
            return FakeDownloadResponse(
                200, body, {"Content-Length": str(len(body))}
            )

        with patch.object(retention_checker.time, "sleep") as sleep:
            retention_checker.verify_artifact_download(
                "owner/repo",
                701,
                "https://api.github.com",
                "test-token",
                open_url=open_url,
            )

        self.assertEqual(len(attempts), 2)
        sleep.assert_called_once_with(1)

    def test_artifact_download_honors_rate_limit_headers(self):
        body = valid_artifact_archive()
        cases = (
            (403, {"retry-after": "4"}, 4),
            (403, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1005"}, 6),
            (429, {"Retry-After": "7"}, 7),
            (429, {}, 60),
            (403, {}, 60),
        )
        for status, headers, delay in cases:
            with self.subTest(status=status, headers=headers):
                calls = []
                errors = []

                def open_url(request, timeout):
                    calls.append(1)
                    if len(calls) == 1:
                        error = HTTPError(request.full_url, status, "Throttled", headers,
                                          BytesIO(b'{"message":"API rate limit exceeded"}'))
                        errors.append(error)
                        raise error
                    self.assertTrue(errors[0].closed)
                    return FakeDownloadResponse(200, body)

                with patch.object(retention_checker.time, "sleep") as sleep:
                    with patch.object(retention_checker.time, "time", return_value=1000):
                        retention_checker.verify_artifact_download(
                            "owner/repo", 701, "https://api.github.com",
                            "test-token", open_url=open_url,
                        )
                self.assertEqual(len(calls), 2)
                sleep.assert_called_once_with(delay)

    def test_artifact_download_defers_rate_limits_beyond_wait_budget(self):
        for headers in ({"Retry-After": "120"}, {}):
            calls = []
            errors = []

            def open_url(request, timeout):
                calls.append(1)
                error = HTTPError(request.full_url, 429, "Throttled", headers, BytesIO())
                errors.append(error)
                raise error

            with patch.object(retention_checker.time, "sleep") as sleep:
                with self.assertRaisesRegex(ValueError, "retry deferred"):
                    retention_checker.verify_artifact_download(
                        "owner/repo", 701, "https://api.github.com",
                        "test-token", open_url=open_url,
                    )
            self.assertEqual(len(calls), 1 if headers else 2)
            self.assertTrue(all(error.closed for error in errors))
            self.assertEqual(sleep.call_count, 0 if headers else 1)

    def test_artifact_download_http_date_honors_or_defers_server_wait(self):
        for header, expected_delay in (
            ("Thu, 01 Jan 1970 00:00:07 GMT", 7),
            ("Thu, 01 Jan 1970 00:02:00 GMT", None),
        ):
            with self.subTest(header=header):
                body = BytesIO(b"throttled")
                error = HTTPError("https://api.github.com/test", 429, "Retry", {"Retry-After": header}, body)
                response = FakeDownloadResponse(200, valid_artifact_archive())
                with patch.object(retention_checker.time, "time", return_value=0):
                    with patch.object(retention_checker.time, "sleep") as sleep:
                        with patch.object(retention_checker, "_verify_artifact_download_once", side_effect=[error, response]) as download:
                            if expected_delay is None:
                                with self.assertRaisesRegex(ValueError, "retry deferred"):
                                    retention_checker.verify_artifact_download("owner/repo", 701, "https://api.github.com", "token")
                                self.assertEqual(download.call_count, 1)
                                sleep.assert_not_called()
                            else:
                                self.assertEqual(retention_checker.verify_artifact_download("owner/repo", 701, "https://api.github.com", "token"), 1)
                                self.assertEqual(download.call_count, 2)
                                sleep.assert_called_once_with(expected_delay)
                self.assertTrue(body.closed)

    def test_artifact_download_http_date_respects_shared_runtime_budget(self):
        clock = [0.0]
        budget = retention_checker._RuntimeBudget(
            5, clock=lambda: clock[0], sleeper=lambda seconds: clock.__setitem__(0, clock[0] + seconds)
        )
        body = BytesIO(b"throttled")
        error = HTTPError("https://api.github.com/test", 429, "Retry", {"Retry-After": "Thu, 01 Jan 1970 00:00:07 GMT"}, body)
        with patch.object(retention_checker.time, "time", return_value=0):
            with patch.object(retention_checker, "_verify_artifact_download_once", side_effect=error) as download:
                with self.assertRaises(retention_checker._RetryBudgetExceeded):
                    retention_checker.verify_artifact_download("owner/repo", 701, "https://api.github.com", "token", budget=budget)
        self.assertEqual(download.call_count, 1)
        self.assertEqual(clock[0], 5)
        self.assertTrue(body.closed)

    def test_artifact_download_closes_http_error_responses(self):
        for status in (503, 403):
            with self.subTest(status=status):
                error_body = BytesIO(b"temporary or permanent API error")
                errors = []
                attempts = []

                def open_url(request, timeout):
                    attempts.append(request.full_url)
                    if len(attempts) == 1:
                        error = HTTPError(request.full_url, status, "API error", {}, error_body)
                        errors.append(error)
                        raise error
                    self.assertTrue(error_body.closed)
                    return FakeDownloadResponse(200, valid_artifact_archive())

                with patch.object(retention_checker.time, "sleep"):
                    if status == 403:
                        with self.assertRaises(ValueError):
                            retention_checker.verify_artifact_download(
                                "owner/repo", 701, "https://api.github.com",
                                "test-token", open_url=open_url,
                            )
                    else:
                        retention_checker.verify_artifact_download(
                            "owner/repo", 701, "https://api.github.com",
                            "test-token", open_url=open_url,
                        )
                self.assertTrue(error_body.closed)

    def test_artifact_download_does_not_retry_permanent_http_access_errors(self):
        attempts = []

        def open_url(request, timeout):
            attempts.append(request.full_url)
            raise HTTPError(request.full_url, 403, "Forbidden", {}, None)

        with patch.object(retention_checker.time, "sleep") as sleep:
            with self.assertRaisesRegex(
                ValueError, "artifact download failed: HTTP Error 403: Forbidden"
            ):
                retention_checker.verify_artifact_download(
                    "owner/repo",
                    701,
                    "https://api.github.com",
                    "test-token",
                    open_url=open_url,
                )

        self.assertEqual(len(attempts), 1)
        sleep.assert_not_called()

    def test_retention_monitor_reports_artifact_download_failure_with_review_details(self):
        now = datetime(2026, 10, 13, tzinfo=timezone.utc)
        commit = "f" * 40
        run = {
            "id": 71,
            "head_sha": commit,
            "created_at": "2026-10-01T12:00:00Z",
            "conclusion": "success",
        }
        artifact = {
            "id": 701,
            "name": f"pages-validation-{commit}",
            "expired": False,
            "created_at": "2026-10-01T12:01:00Z",
            "expires_at": "2026-12-30T12:00:00Z",
            "workflow_run": {"id": 71, "head_sha": commit},
        }

        def fetch(url, token):
            if "/workflows/pages.yml/runs?" in url:
                return {"workflow_runs": [run]}, None
            if "/compare/" in url:
                return {"status": "ahead"}, None
            if "/runs/71/artifacts?" in url:
                return {"artifacts": [artifact]}, None
            self.fail(f"Unexpected GitHub API request: {url}")

        attempts = []

        def open_url(request, timeout):
            self.assertEqual(
                request.full_url,
                "https://api.github.com/repos/owner/repo/actions/artifacts/701/zip",
            )
            attempts.append(request.full_url)
            raise URLError("temporary connection reset")

        with patch.object(retention_checker.time, "sleep") as sleep:
            with self.assertRaisesRegex(
                ValueError,
                rf"run 71 \| commit {commit} \| review deadline "
                r"2026-12-30T12:00:00\+00:00: validation artifact is invalid or "
                r"unavailable: artifact download failed after 3 attempts: "
                r"temporary transport error: <urlopen error temporary connection reset>",
            ):
                retention_checker.monitor_repository(
                    "owner/repo",
                    "https://api.github.com",
                    "test-token",
                    now=now,
                    fetch_page=fetch,
                    open_url=open_url,
                )

        self.assertEqual(len(attempts), 3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [1, 2])

    def test_retention_monitor_links_each_affected_run(self):
        now = datetime(2026, 10, 13, tzinfo=timezone.utc)
        runs = [
            {
                "id": 71,
                "head_sha": "a" * 40,
                "created_at": "2026-10-01T12:00:00Z",
                "conclusion": "success",
            },
            {
                "id": 72,
                "head_sha": "b" * 40,
                "created_at": "2026-10-02T12:00:00Z",
                "conclusion": "success",
            },
        ]

        def fetch(url, token):
            if "/workflows/pages.yml/runs?" in url:
                return {"workflow_runs": runs}, None
            if "/compare/" in url:
                return {"status": "ahead"}, None
            if "/runs/71/artifacts?" in url or "/runs/72/artifacts?" in url:
                return {"artifacts": []}, None
            self.fail(f"Unexpected GitHub API request: {url}")

        with self.assertRaises(ValueError) as error:
            retention_checker.monitor_repository(
                "configured-owner/configured-repo",
                "https://api.github.com",
                "test-token",
                now=now,
                fetch_page=fetch,
            )

        report = str(error.exception)
        self.assertIn(
            "run 71 | commit " + "a" * 40 + " | review deadline "
            "2026-12-30T12:00:00+00:00: validation artifact is missing | "
            "GitHub Actions: "
            "https://github.com/configured-owner/configured-repo/actions/runs/71",
            report,
        )
        self.assertIn(
            "run 72 | commit " + "b" * 40 + " | review deadline "
            "2026-12-31T12:00:00+00:00: validation artifact is missing | "
            "GitHub Actions: "
            "https://github.com/configured-owner/configured-repo/actions/runs/72",
            report,
        )

    def test_retention_monitor_uses_enterprise_host_for_run_links(self):
        now = datetime(2026, 10, 13, tzinfo=timezone.utc)
        run = {
            "id": 71,
            "head_sha": "a" * 40,
            "created_at": "2026-10-01T12:00:00Z",
            "conclusion": "success",
        }

        def fetch(url, token):
            if "/workflows/pages.yml/runs?" in url:
                return {"workflow_runs": [run]}, None
            if "/compare/" in url:
                return {"status": "ahead"}, None
            if "/runs/71/artifacts?" in url:
                return {"artifacts": []}, None
            self.fail(f"Unexpected GitHub API request: {url}")

        with self.assertRaises(ValueError) as error:
            retention_checker.monitor_repository(
                "configured-owner/configured-repo",
                "https://github.enterprise.example/api/v3",
                "test-token",
                now=now,
                fetch_page=fetch,
            )

        self.assertIn(
            "GitHub Actions: "
            "https://github.enterprise.example/configured-owner/"
            "configured-repo/actions/runs/71",
            str(error.exception),
        )

    def test_retention_monitor_links_invalid_metadata_only_when_run_id_is_numeric(self):
        now = datetime(2026, 10, 13, tzinfo=timezone.utc)
        runs = [
            {
                "id": 81,
                "head_sha": None,
                "created_at": "2026-10-01T12:00:00Z",
                "conclusion": "success",
            },
            {
                "id": 82,
                "head_sha": "b" * 40,
                "created_at": "not-a-timestamp",
                "conclusion": "success",
            },
            {
                "id": True,
                "head_sha": "c" * 40,
                "created_at": "2026-10-03T12:00:00Z",
                "conclusion": "success",
            },
            {
                "head_sha": "d" * 40,
                "created_at": "2026-10-04T12:00:00Z",
                "conclusion": "success",
            },
        ]

        def fetch(url, token):
            if "/workflows/pages.yml/runs?" in url:
                return {"workflow_runs": runs}, None
            self.fail(f"Invalid run metadata must not trigger more API requests: {url}")

        with self.assertRaises(ValueError) as error:
            retention_checker.monitor_repository(
                "owner/repo",
                "https://api.github.com",
                "test-token",
                now=now,
                fetch_page=fetch,
            )

        report = str(error.exception)
        self.assertIn(
            "review deadline 2026-12-30T12:00:00+00:00: "
            "successful Pages run is missing a numeric id or commit SHA | "
            "GitHub Actions: https://github.com/owner/repo/actions/runs/81",
            report,
        )
        self.assertIn(
            "run 82 | commit " + "b" * 40
            + " | review deadline unknown: artifact metadata has invalid "
            "workflow run created_at: 'not-a-timestamp' | GitHub Actions: "
            "https://github.com/owner/repo/actions/runs/82",
            report,
        )
        self.assertIn(
            "run unknown | commit " + "c" * 40
            + " | review deadline 2027-01-01T12:00:00+00:00: "
            "successful Pages run is missing a numeric id or commit SHA",
            report,
        )
        self.assertIn(
            "run unknown | commit " + "d" * 40
            + " | review deadline 2027-01-02T12:00:00+00:00: "
            "successful Pages run is missing a numeric id or commit SHA",
            report,
        )
        self.assertNotIn("actions/runs/True", report)
        self.assertNotIn("actions/runs/unknown", report)
        self.assertNotIn("actions/runs/None", report)

    def test_downloaded_archive_must_contain_all_review_evidence(self):
        incomplete_archive = valid_artifact_archive(
            "assets/audit/color-scheme-init-firefox.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            "missing required evidence files: "
            "assets/audit/color-scheme-init-firefox.json",
        ):
            retention_checker.verify_artifact_download(
                "owner/repo",
                701,
                "https://api.github.com",
                "test-token",
                open_url=lambda request, timeout: FakeDownloadResponse(
                    200, incomplete_archive
                ),
            )

    def test_encrypted_required_evidence_entry_is_rejected_as_invalid_archive(self):
        report_path = "assets/audit/color-scheme-init-chromium.json"
        encrypted_archive = artifact_archive_with_required_entry_flags(report_path)

        with self.assertRaisesRegex(
            ValueError,
            f"artifact archive contains an encrypted required evidence file: "
            f"{report_path}",
        ):
            retention_checker.validate_artifact_archive(BytesIO(encrypted_archive))

    def test_required_entry_rejects_local_or_central_encryption_flags(self):
        for name in sorted(retention_checker.REQUIRED_EVIDENCE_FILES):
            for local, central in ((1, 0), (0, 1), (1, 1), (0x40, 0), (0, 0x40), (0x40, 0x40)):
                with self.subTest(name=name, local=local, central=central):
                    data = artifact_archive_with_required_entry_flags(
                        name, local_flags=local, central_flags=central
                    )
                    with self.assertRaisesRegex(ValueError, "encrypted required evidence file"):
                        retention_checker.validate_artifact_archive(BytesIO(data))

    def test_required_entry_rejects_invalid_or_truncated_local_headers(self):
        name = "assets/audit/color-scheme-init-chromium.json"
        for corruption in ("signature", "offset", "length"):
            with self.subTest(corruption=corruption):
                data = bytearray(valid_artifact_archive())
                local, central = zip_fixture_header_offsets(data, name)
                if corruption == "signature":
                    data[local:local + 4] = b"FAIL"
                elif corruption == "offset":
                    data[central + 42:central + 46] = (len(data) - 5).to_bytes(4, "little")
                else:
                    data[local + 26:local + 30] = b"\xff\xff\xff\xff"
                with self.assertRaisesRegex(ValueError, "invalid local header|truncated local header|corrupt or incomplete"):
                    retention_checker.validate_artifact_archive(BytesIO(data))

    def test_required_entry_allows_utf8_data_descriptor_and_adjusted_prefix_offsets(self):
        name = "assets/audit/color-scheme-init-chromium.json"
        utf8 = artifact_archive_with_required_entry_flags(name, local_flags=0x800, central_flags=0x800)
        retention_checker.validate_artifact_archive(BytesIO(utf8))

        class NonSeekable(BytesIO):
            def seekable(self): return False
            def seek(self, *args): raise OSError("fixture stream is not seekable")
        output = NonSeekable()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
            for member in sorted(retention_checker.REQUIRED_EVIDENCE_FILES):
                zipped.writestr(member, b"{}")
        descriptor = output.getvalue()
        with zipfile.ZipFile(BytesIO(descriptor)) as zipped:
            self.assertTrue(all(entry.flag_bits & 0x8 for entry in zipped.infolist()))
        retention_checker.validate_artifact_archive(BytesIO(descriptor))
        prefixed = b"synthetic-self-extracting-stub" + valid_artifact_archive()
        with zipfile.ZipFile(BytesIO(prefixed)) as zipped:
            self.assertGreater(zipped.getinfo(name).header_offset, 0)
        retention_checker.validate_artifact_archive(BytesIO(prefixed))
        flagged = artifact_archive_with_required_entry_flags(name, local_flags=1, central_flags=0, source=prefixed)
        with self.assertRaisesRegex(ValueError, "encrypted required evidence file"):
            retention_checker.validate_artifact_archive(BytesIO(flagged))

    def test_required_entry_allows_zip64_local_extra_fields(self):
        output = BytesIO()
        with zipfile.ZipFile(output, "w", allowZip64=True) as zipped:
            for member in sorted(retention_checker.REQUIRED_EVIDENCE_FILES):
                with zipped.open(member, "w", force_zip64=True) as entry:
                    entry.write(b"{}")
        retention_checker.validate_artifact_archive(BytesIO(output.getvalue()))

    def test_required_evidence_entry_rejects_explicit_non_file_types(self):
        report_path = "assets/audit/color-scheme-init-chromium.json"
        for creator, entry_attributes, label in (
            (3, (stat.S_IFDIR | 0o755) << 16, "Unix directory"),
            (3, (stat.S_IFLNK | 0o777) << 16, "symbolic link"),
            (0, 0x10, "DOS directory attribute without slash"),
            (3, (stat.S_IFIFO | 0o600) << 16, "FIFO"),
            (3, (stat.S_IFCHR | 0o600) << 16, "character device"),
            (3, (stat.S_IFBLK | 0o600) << 16, "block device"),
            (3, (stat.S_IFSOCK | 0o600) << 16, "socket"),
        ):
            with self.subTest(entry_type=label):
                archive = artifact_archive_with_special_required_entry(
                    report_path, entry_attributes, creator=creator
                )
                with self.assertRaisesRegex(
                    ValueError,
                    f"required evidence entry is not a regular file: {report_path}",
                ):
                    retention_checker.validate_artifact_archive(BytesIO(archive))

    def test_required_evidence_entry_accepts_regular_or_unspecified_cross_platform_metadata(self):
        report_path = "assets/audit/color-scheme-init-chromium.json"
        for creator, attrs, label in (
            (3, ((stat.S_IFREG | 0o644) << 16) | 0x20, "Unix regular with DOS archive bit"),
            (3, 0o644 << 16, "Unix permissions without type"),
            (0, 0x20, "DOS archive attribute"),
            (0, ((stat.S_IFLNK | 0o777) << 16) | 0x20, "DOS creator with unrelated upper bits"),
        ):
            with self.subTest(creator=creator, entry_type=label):
                archive = artifact_archive_with_special_required_entry(report_path, attrs, creator=creator)
                retention_checker.validate_artifact_archive(BytesIO(archive))

    def test_non_required_directory_entries_remain_compatible(self):
        archive = valid_artifact_archive(additional_files={"assets/audit/optional/": b""})
        retention_checker.validate_artifact_archive(BytesIO(archive))

    def test_all_required_paths_reject_explicit_symlinks(self):
        for name in sorted(retention_checker.REQUIRED_EVIDENCE_FILES):
            with self.subTest(name=name):
                archive = artifact_archive_with_special_required_entry(
                    name, (stat.S_IFLNK | 0o777) << 16, creator=3
                )
                with self.assertRaisesRegex(ValueError, "not a regular file"):
                    retention_checker.validate_artifact_archive(BytesIO(archive))

    def test_released_pages_artifact_shaped_unix_metadata_is_accepted(self):
        # One previously released Pages artifact had Unix regular-file type
        # and the DOS archive bit for each required member. Permissions below
        # are synthetic; they were not observed in that artifact sample.
        archive = BytesIO()
        with zipfile.ZipFile(archive, "w") as zipped:
            for name in sorted(retention_checker.REQUIRED_EVIDENCE_FILES):
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = ((stat.S_IFREG | 0o644) << 16) | 0x20
                zipped.writestr(info, b"{}")
        with patch.object(zipfile.ZipFile, "extract", side_effect=AssertionError("unexpected extraction")), \
             patch.object(zipfile.ZipFile, "extractall", side_effect=AssertionError("unexpected extraction")):
            retention_checker.validate_artifact_archive(archive)

    def test_downloaded_archive_with_duplicate_required_report_is_rejected(self):
        report_path = "assets/audit/color-scheme-init-chromium.json"
        with self.assertWarns(UserWarning):
            ambiguous_archive = valid_artifact_archive(
                duplicate_files=[(report_path, b'{"browser":"different"}')]
            )

        with self.assertRaisesRegex(
            ValueError,
            "artifact archive has duplicate paths: "
            "assets/audit/color-scheme-init-chromium.json",
        ):
            retention_checker.verify_artifact_download(
                "owner/repo",
                701,
                "https://api.github.com",
                "test-token",
                open_url=lambda request, timeout: FakeDownloadResponse(
                    200, ambiguous_archive
                ),
            )

    def test_downloaded_archive_with_duplicate_optional_files_is_rejected(self):
        duplicate_paths = (
            "assets/audit/SYNTHETIC_PRIVATE_SECRET\nforged-log.json",
            "assets/docs/" + "long-marker-" * 400,
        )
        with self.assertWarns(UserWarning):
            ambiguous_archive = valid_artifact_archive(
                duplicate_files=[
                    (path, b"first copy")
                    for path in duplicate_paths
                ]
                + [
                    (path, b"second copy")
                    for path in duplicate_paths
                ]
            )

        with self.assertRaisesRegex(ValueError, "duplicate paths outside required evidence") as raised:
            retention_checker.verify_artifact_download(
                "owner/repo",
                701,
                "https://api.github.com",
                "test-token",
                open_url=lambda request, timeout: FakeDownloadResponse(
                    200, ambiguous_archive
                ),
            )
        trace = "".join(traceback.format_exception(raised.exception))
        for name in duplicate_paths:
            self.assertNotIn(name, trace)
        self.assertNotIn("SYNTHETIC_PRIVATE_SECRET", trace)
        self.assertNotIn("long-marker-", trace)

    def test_duplicate_required_and_optional_paths_only_name_allowlisted_path(self):
        required = "assets/audit/color-scheme-init-chromium.json"
        optional = "assets/audit/SYNTHETIC_PRIVATE_SECRET\nforged.json"
        with self.assertWarns(UserWarning):
            archive = valid_artifact_archive(
                additional_files={optional: b"one"},
                duplicate_files=[(required, b"different"), (optional, b"two")],
            )
        with self.assertRaises(ValueError) as raised:
            retention_checker.validate_artifact_archive(BytesIO(archive))
        trace = "".join(traceback.format_exception(raised.exception))
        self.assertIn(required, trace)
        self.assertIn("additional duplicate paths omitted", trace)
        self.assertNotIn("SYNTHETIC_PRIVATE_SECRET", trace)

    def test_normalized_required_collision_keeps_existing_guard(self):
        required = "assets/audit/color-scheme-init-chromium.json"
        optional = required + "-SYNTHETIC_PRIVATE_SECRET"
        archive = bytearray(valid_artifact_archive(additional_files={optional: b"data"}))
        local, central = zip_fixture_header_offsets(archive, optional)
        archive[local + 30 + len(required)] = 0
        archive[central + 46 + len(required)] = 0
        with self.assertRaisesRegex(ValueError, "duplicate paths: " + required) as raised:
            retention_checker.validate_artifact_archive(BytesIO(archive))
        self.assertNotIn("SYNTHETIC_PRIVATE_SECRET", "".join(traceback.format_exception(raised.exception)))

    def test_duplicate_optional_directory_is_rejected_without_name(self):
        directory = "assets/audit/SYNTHETIC_PRIVATE_SECRET/"
        with self.assertWarns(UserWarning):
            archive = valid_artifact_archive(
                additional_files={directory: b""}, duplicate_files=[(directory, b"")]
            )
        with self.assertRaisesRegex(ValueError, "duplicate paths outside required evidence") as raised:
            retention_checker.validate_artifact_archive(BytesIO(archive))
        self.assertNotIn("SYNTHETIC_PRIVATE_SECRET", str(raised.exception))

    def test_optional_effective_name_collision_blocks_corrupt_first_entry(self):
        prefix = "assets/audit/SYNTHETIC_PRIVATE_SECRET"
        first, second = prefix + "-first.json", prefix + "-second.json"
        archive = bytearray(valid_artifact_archive(additional_files={first: b"first data", second: b"second data"}))
        offsets = [zip_fixture_header_offsets(archive, name) for name in (first, second)]
        first_local = offsets[0][0]
        name_length = int.from_bytes(archive[first_local + 26:first_local + 28], "little")
        extra_length = int.from_bytes(archive[first_local + 28:first_local + 30], "little")
        archive[first_local + 30 + name_length + extra_length] ^= 0xFF
        for local, central in offsets:
            archive[local + 30 + len(prefix)] = 0
            archive[central + 46 + len(prefix)] = 0
        with zipfile.ZipFile(BytesIO(archive)) as zipped:
            entries = zipped.infolist()[-2:]
            self.assertNotEqual(entries[0].orig_filename, entries[1].orig_filename)
            self.assertEqual(entries[0].filename, entries[1].filename)
            # Name-based testzip would read the second entry twice.
            self.assertIsNone(zipped.testzip())
            with self.assertRaises((zipfile.BadZipFile, zlib.error)):
                with zipped.open(entries[0]) as member:
                    member.read()
        with self.assertRaisesRegex(ValueError, "duplicate paths outside required evidence") as raised:
            retention_checker.validate_artifact_archive(BytesIO(archive))
        self.assertNotIn("SYNTHETIC_PRIVATE_SECRET", "".join(traceback.format_exception(raised.exception)))

    def test_synthetic_207_entry_unique_archive_is_accepted(self):
        # Shape only: one sampled released artifact had 207 entries and no
        # exact duplicate names; its optional names and bytes were not copied.
        optional = {f"synthetic/entry-{index:03d}.json": b"{}" for index in range(201)}
        optional["synthetic/unique-directory/"] = b""
        archive = valid_artifact_archive(additional_files=optional)
        with zipfile.ZipFile(BytesIO(archive)) as zipped:
            self.assertEqual(len(zipped.infolist()), 207)
        with patch.object(zipfile.ZipFile, "extract", side_effect=AssertionError("unexpected extraction")), \
             patch.object(zipfile.ZipFile, "extractall", side_effect=AssertionError("unexpected extraction")):
            retention_checker.validate_artifact_archive(BytesIO(archive))

    def test_corrupt_optional_filename_does_not_leak_in_exception_trace(self):
        optional = "assets/audit/SYNTHETIC_PRIVATE_SECRET\nforged.json"
        archive = bytearray(valid_artifact_archive(additional_files={optional: b"data"}))
        local, _ = zip_fixture_header_offsets(archive, optional)
        archive[local + 30] ^= 1  # Central and local names no longer agree.
        with self.assertRaisesRegex(ValueError, "artifact archive is corrupt or incomplete|damaged optional entry") as raised:
            retention_checker.validate_artifact_archive(BytesIO(archive))
        self.assertNotIn("SYNTHETIC_PRIVATE_SECRET", "".join(traceback.format_exception(raised.exception)))

        with patch.object(zipfile.ZipFile, "testzip", side_effect=zipfile.BadZipFile(optional)):
            with self.assertRaisesRegex(ValueError, "artifact archive is corrupt or incomplete") as raised:
                retention_checker.validate_artifact_archive(BytesIO(valid_artifact_archive()))
        self.assertNotIn("SYNTHETIC_PRIVATE_SECRET", "".join(traceback.format_exception(raised.exception)))

    def test_invalid_utf8_optional_names_fail_safely_in_both_zip_headers(self):
        optional = "assets/audit/SYNTHETIC_PRIVATE_SECRET\nforged.json"
        for header in ("central", "local"):
            with self.subTest(header=header):
                archive = artifact_archive_with_invalid_utf8_optional_name(optional, header)
                with self.assertRaises(UnicodeDecodeError):
                    with zipfile.ZipFile(BytesIO(archive)) as zipped:
                        with zipped.open(optional):
                            pass
                with self.assertRaisesRegex(ValueError, "artifact archive is corrupt or incomplete") as raised:
                    retention_checker.validate_artifact_archive(BytesIO(archive))
                trace = "".join(traceback.format_exception(raised.exception))
                self.assertNotIn("SYNTHETIC_PRIVATE_SECRET", trace)
                self.assertNotIn("forged.json", trace)

    def test_historical_archive_with_dated_audit_reports_is_accepted(self):
        # Successful October 6 evidence archives include release-specific audit
        # reports beyond the stable set required by the retention checker.
        historical_archive = valid_artifact_archive(
            additional_files={
                "assets/audit/links-report-2026-10-05.json": b"{}",
                "assets/audit/links-report-2026-10-06.json": b"{}",
                "assets/audit/resilience-qa-2026-10-06.json": b"{}",
                "assets/audit/validation-report-2026-10-06.json": b"{}",
                "assets/audit/viewport-qa-full-2026-10-06.json": b"{}",
            }
        )

        retention_checker.validate_artifact_archive(BytesIO(historical_archive))

    def test_archive_with_damaged_file_contents_is_rejected(self):
        damaged_archive = bytearray(valid_artifact_archive())
        with zipfile.ZipFile(BytesIO(damaged_archive)) as zipped:
            entry = zipped.getinfo("assets/audit/color-scheme-init-chromium.json")
            name_length = int.from_bytes(
                damaged_archive[entry.header_offset + 26:entry.header_offset + 28],
                "little",
            )
            extra_length = int.from_bytes(
                damaged_archive[entry.header_offset + 28:entry.header_offset + 30],
                "little",
            )
            data_offset = entry.header_offset + 30 + name_length + extra_length
        damaged_archive[data_offset] ^= 0xFF

        with self.assertRaisesRegex(ValueError, "corrupt or incomplete|damaged file"):
            retention_checker.validate_artifact_archive(BytesIO(damaged_archive))

    def test_downloaded_archive_size_is_capped_before_temporary_write(self):
        with patch.object(retention_checker, "MAX_ARTIFACT_BYTES", 8):
            with self.assertRaisesRegex(ValueError, "exceeds the 512 MiB size limit"):
                retention_checker.verify_artifact_download(
                    "owner/repo",
                    701,
                    "https://api.github.com",
                    "test-token",
                    open_url=lambda request, timeout: FakeDownloadResponse(
                        200, b"x" * 9
                    ),
                )

    def test_retention_monitor_reports_a_damaged_archive_with_review_details(self):
        now = datetime(2026, 10, 13, tzinfo=timezone.utc)
        commit = "9" * 40
        run = {
            "id": 79,
            "head_sha": commit,
            "created_at": "2026-10-01T12:00:00Z",
            "conclusion": "success",
        }
        artifact = {
            "id": 709,
            "name": f"pages-validation-{commit}",
            "expired": False,
            "created_at": "2026-10-01T12:01:00Z",
            "expires_at": "2026-12-30T12:00:00Z",
            "workflow_run": {"id": 79, "head_sha": commit},
        }

        def fetch(url, token):
            if "/workflows/pages.yml/runs?" in url:
                return {"workflow_runs": [run]}, None
            if "/compare/" in url:
                return {"status": "ahead"}, None
            if "/runs/79/artifacts?" in url:
                return {"artifacts": [artifact]}, None
            self.fail(f"Unexpected GitHub API request: {url}")

        def open_url(request, timeout):
            return FakeDownloadResponse(200, b"PK\x03\x04 truncated archive")

        with self.assertRaisesRegex(
            ValueError,
            rf"run 79 \| commit {commit} \| review deadline "
            r"2026-12-30T12:00:00\+00:00: validation artifact is invalid or "
            r"unavailable: artifact download failed: artifact archive is corrupt or incomplete",
        ):
            retention_checker.monitor_repository(
                "owner/repo",
                "https://api.github.com",
                "test-token",
                now=now,
                fetch_page=fetch,
                open_url=open_url,
            )

    def test_monitor_hides_duplicate_optional_names_in_report_and_logs(self):
        marker = "SYNTHETIC_PRIVATE_SECRET"
        optional = f"assets/audit/{marker}\nforged-log.json"
        with self.assertWarns(UserWarning):
            archive = valid_artifact_archive(
                additional_files={optional: b"one"}, duplicate_files=[(optional, b"two")]
            )
        commit = "9" * 40
        run = {"id": 79, "head_sha": commit, "created_at": "2026-10-01T12:00:00Z", "conclusion": "success"}
        artifact = {
            "id": 709, "name": f"pages-validation-{commit}", "expired": False,
            "created_at": "2026-10-01T12:01:00Z", "expires_at": "2026-12-30T12:00:00Z",
            "workflow_run": {"id": 79, "head_sha": commit},
        }

        def fetch(url, token):
            if "/workflows/pages.yml/runs?" in url:
                return {"workflow_runs": [run]}, None
            if "/compare/" in url:
                return {"status": "ahead"}, None
            if "/runs/79/artifacts?" in url:
                return {"artifacts": [artifact]}, None
            self.fail(f"Unexpected GitHub API request: {url}")

        corrupt = bytearray(valid_artifact_archive(additional_files={optional: b"data"}))
        local, _ = zip_fixture_header_offsets(corrupt, optional)
        corrupt[local + 30] ^= 1
        for body, expected in ((archive, "duplicate paths outside required evidence"),
                               (corrupt, "damaged optional entry"),
                               (artifact_archive_with_invalid_utf8_optional_name(optional, "central"),
                                "artifact archive is corrupt or incomplete"),
                               (artifact_archive_with_invalid_utf8_optional_name(optional, "local"),
                                "artifact archive is corrupt or incomplete")):
            with self.subTest(expected=expected):
                output, errors = StringIO(), StringIO()
                with redirect_stdout(output), redirect_stderr(errors), self.assertRaises(ValueError) as raised:
                    retention_checker.monitor_repository(
                        "owner/repo", "https://api.github.com", "test-token",
                        now=datetime(2026, 10, 13, tzinfo=timezone.utc), fetch_page=fetch,
                        open_url=lambda request, timeout: FakeDownloadResponse(200, body),
                    )
                result = output.getvalue() + errors.getvalue() + "".join(traceback.format_exception(raised.exception))
                self.assertIn(expected, result)
                self.assertNotIn(marker, result)
                self.assertNotIn("forged-log", result)

    def test_retention_monitor_stops_checking_at_the_90_day_deadline(self):
        now = datetime(2026, 10, 13, tzinfo=timezone.utc)
        exact_deadline_run = {
            "id": 61,
            "head_sha": "e" * 40,
            "created_at": (now - timedelta(days=90)).isoformat(),
            "conclusion": "success",
        }
        artifact_requests = []

        def fetch(url, token):
            if "/workflows/pages.yml/runs?" in url:
                return {"workflow_runs": [exact_deadline_run]}, None
            artifact_requests.append(url)
            return {"artifacts": []}, None

        checked = retention_checker.monitor_repository(
            "owner/repo",
            "https://api.github.com",
            "test-token",
            now=now,
            fetch_page=fetch,
        )
        self.assertEqual(checked, 0)
        self.assertEqual(artifact_requests, [])

    def test_retention_monitor_follows_github_pagination(self):
        first = "https://api.github.com/first"
        second = "https://api.github.com/second"
        calls = []

        def fetch(url, token):
            calls.append(url)
            if url == first:
                return {"workflow_runs": [{"id": 1}]}, second
            return {"workflow_runs": [{"id": 2}]}, None

        self.assertEqual(
            retention_checker._list_all(first, "workflow_runs", "test-token", fetch),
            [{"id": 1}, {"id": 2}],
        )
        self.assertEqual(calls, [first, second])

    def test_retention_monitor_retries_a_later_workflow_runs_page_once(self):
        now = datetime(2026, 10, 13, tzinfo=timezone.utc)
        second_runs_page = "https://api.github.com/second-runs-page"
        runs = [
            {
                "id": run_id,
                "head_sha": commit,
                "created_at": "2026-10-01T12:00:00Z",
                "conclusion": "success",
            }
            for run_id, commit in ((71, "a" * 40), (72, "b" * 40))
        ]
        runs_page_attempts = 0
        compare_calls = []
        artifact_calls = []
        download_calls = []

        def artifact_for(run):
            return {
                "id": run["id"] * 10,
                "name": f"pages-validation-{run['head_sha']}",
                "expired": False,
                "created_at": "2026-10-01T12:01:00Z",
                "expires_at": "2026-12-30T12:00:00Z",
                "workflow_run": {
                    "id": run["id"],
                    "head_sha": run["head_sha"],
                },
            }

        def fetch(url, token):
            nonlocal runs_page_attempts
            if url == second_runs_page:
                runs_page_attempts += 1
                if runs_page_attempts == 1:
                    raise URLError("temporary connection reset")
                return {"workflow_runs": [runs[1]]}, None
            if "/workflows/pages.yml/runs?" in url:
                return {"workflow_runs": [runs[0]]}, second_runs_page
            if "/compare/" in url:
                run = runs[0] if runs[0]["head_sha"] in url else runs[1]
                compare_calls.append(run["id"])
                return {"status": "ahead"}, None
            if "/artifacts?" in url:
                run = runs[0] if "/runs/71/" in url else runs[1]
                artifact_calls.append(run["id"])
                return {"artifacts": [artifact_for(run)]}, None
            self.fail(f"Unexpected GitHub API request: {url}")

        def open_url(request, timeout):
            download_calls.append(request.full_url.rsplit("/", 2)[-2])
            body = valid_artifact_archive()
            return FakeDownloadResponse(
                200, body, {"Content-Length": str(len(body))}
            )

        with patch.object(retention_checker.time, "sleep"):
            checked = retention_checker.monitor_repository(
                "owner/repo",
                "https://api.github.com",
                "test-token",
                now=now,
                fetch_page=fetch,
                open_url=open_url,
            )

        self.assertEqual(checked, 2)
        self.assertEqual(runs_page_attempts, 2)
        self.assertEqual(compare_calls, [71, 72])
        self.assertEqual(artifact_calls, [71, 72])
        self.assertEqual(download_calls, ["710", "720"])

    def test_list_all_retries_later_artifact_page_without_duplicate_items(self):
        first = "https://api.github.com/first-artifact-page"
        second = "https://api.github.com/second-artifact-page"
        calls = []
        second_page_attempts = 0
        pages = {
            first: [{"id": 730}],
            second: [{"id": 731}, {"id": 732}],
        }

        def fetch(url, token):
            nonlocal second_page_attempts
            calls.append(url)
            if url == second:
                second_page_attempts += 1
                if second_page_attempts == 1:
                    raise HTTPError(url, 503, "Service Unavailable", {}, None)
            return {"artifacts": pages[url]}, second if url == first else None

        with patch.object(retention_checker.time, "sleep"):
            artifacts = retention_checker._list_all(
                first, "artifacts", "test-token", fetch
            )

        self.assertEqual([artifact["id"] for artifact in artifacts], [730, 731, 732])
        self.assertEqual(calls, [first, second, second])
        self.assertEqual(second_page_attempts, 2)

    def test_retention_monitor_reports_permanent_later_artifact_page_failure(self):
        now = datetime(2026, 10, 13, tzinfo=timezone.utc)
        run = {
            "id": 74,
            "head_sha": "d" * 40,
            "created_at": "2026-10-01T12:00:00Z",
            "conclusion": "success",
        }
        second_artifacts_page = "https://api.github.com/second-artifacts-page"
        artifact_page_attempts = 0

        def fetch(url, token):
            nonlocal artifact_page_attempts
            if "/workflows/pages.yml/runs?" in url:
                return {"workflow_runs": [run]}, None
            if "/compare/" in url:
                return {"status": "ahead"}, None
            if "/runs/74/artifacts?" in url:
                return {"artifacts": []}, second_artifacts_page
            if url == second_artifacts_page:
                artifact_page_attempts += 1
                raise HTTPError(url, 403, "Forbidden", {}, None)
            self.fail(f"Unexpected GitHub API request: {url}")

        with patch.object(retention_checker.time, "sleep") as sleep:
            with self.assertRaises(ValueError) as raised:
                retention_checker.monitor_repository(
                    "owner/repo",
                    "https://api.github.com",
                    "test-token",
                    now=now,
                    fetch_page=fetch,
                )

        message = str(raised.exception)
        self.assertIn(f"run 74 | commit {run['head_sha']} | review deadline ", message)
        self.assertIn("GitHub metadata request failed with HTTP 403", message)
        self.assertEqual(artifact_page_attempts, 1)
        sleep.assert_not_called()

    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_complete_commit_linked_evidence_is_staged_before_upload(self):
        assert_validation_evidence_contract(self.workflow)

    def test_uploaded_validation_artifact_is_checked_before_deployment(self):
        assert_uploaded_theme_evidence_contract(self.workflow)

    def test_browser_check_records_failed_case_without_discarding_completed_cases(self):
        report = {"cases": {}}
        color_scheme_checker.capture_case(
            report, "light", lambda: {"preference_applied": True}
        )

        def fail_dark_case():
            raise AssertionError("dark preference was not applied")

        color_scheme_checker.capture_case(report, "dark", fail_dark_case)
        color_scheme_checker.capture_case(
            report, "disabled_storage", lambda: {"storage_blocked": True}
        )

        self.assertEqual(
            report["cases"],
            {
                "light": {"preference_applied": True},
                "disabled_storage": {"storage_blocked": True},
            },
        )
        self.assertEqual(report["failure_stage"], "theme_check")
        self.assertEqual(report["failed_case"], "dark")
        self.assertEqual(report["error"], "One or more theme cases failed.")
        self.assertEqual(
            report["case_failures"],
            {"dark": {"error": "Theme case failed."}},
        )
        self.assertEqual(report["attempted_cases"], ["light", "dark", "disabled_storage"])
        self.assertEqual(report["not_run_cases"], [])
        self.assertTrue(report["diagnostic_only"])

    def test_multiple_theme_failures_keep_later_results_and_hide_exception_details(self):
        report = {"cases": {}}
        marker = "synthetic-private-token"
        for name in ("light", "dark", "disabled_storage"):
            def check(name=name):
                if name != "dark":
                    raise RuntimeError(f"{marker} https://private.invalid/?token={marker}")
                return {"routes": 1}
            color_scheme_checker.capture_case(report, name, check)
        self.assertEqual(report["attempted_cases"], ["light", "dark", "disabled_storage"])
        self.assertEqual(report["not_run_cases"], [])
        self.assertEqual(report["cases"], {"dark": {"routes": 1}})
        self.assertEqual(set(report["case_failures"]), {"light", "disabled_storage"})
        self.assertEqual(report["failed_case"], "light")
        self.assertNotIn(marker, json.dumps(report))

    def test_multi_case_route_diagnostics_are_allowlisted_and_do_not_expose_secrets(self):
        marker = "synthetic-private-token"
        report = {"cases": {}}

        def check(route):
            if route == "/about/":
                color_scheme_checker.assert_independent_checks(
                    route, [("visible primary content", lambda: color_scheme_checker.require_condition(False, marker))]
                )
            if route == "/toolbox/":
                raise color_scheme_checker.TypedThemeRuntimeFailure(marker, "navigation_failed")
            raise RuntimeError(marker)

        first_routes = ["/about/", f"/private-{marker}/"]
        second_routes = ["/toolbox/", "/404.html"]
        color_scheme_checker.capture_case(
            report, "light", lambda: color_scheme_checker.collect_route_evidence(first_routes, check),
            allowed_routes=first_routes,
        )
        color_scheme_checker.capture_case(
            report, "dark", lambda: color_scheme_checker.collect_route_evidence(second_routes, check),
            allowed_routes=second_routes,
        )
        color_scheme_checker.capture_case(report, "disabled_storage", lambda: {"routes": 1})
        self.assertEqual(report["case_failures"]["light"], {
            "error": "Theme case failed.",
            "affected_routes": [{"route": "/about/", "reasons": ["theme_assertion_failed"]}],
            "route_details_incomplete": True,
        })
        self.assertEqual(report["case_failures"]["dark"]["affected_routes"], [
            {"route": "/toolbox/", "reasons": ["navigation_failed"]},
            {"route": "/404.html", "reasons": ["route_check_failed"]},
        ])
        self.assertNotIn(marker, json.dumps(report))

        playwright_api = ModuleType("playwright.sync_api")
        class FakeBrowser:
            version = "test-browser"
            def close(self): pass
        class PlaywrightManager:
            def __enter__(self):
                return SimpleNamespace(chromium=SimpleNamespace(launch=lambda **_: FakeBrowser()))
            def __exit__(self, *_args): return False
        playwright_api.sync_playwright = PlaywrightManager
        playwright_module = ModuleType("playwright")
        playwright_module.sync_api = playwright_api
        def fail_preference(_browser, _base, _preference, routes):
            return color_scheme_checker.collect_route_evidence(routes, check)
        stdout = StringIO()
        with (
            patch.dict(sys.modules, {"playwright": playwright_module, "playwright.sync_api": playwright_api}),
            patch.object(sys, "argv", [str(COLOR_SCHEME_SCRIPT)]),
            patch.object(color_scheme_checker, "browser_routes", return_value=["/about/", "/toolbox/"]),
            patch.object(color_scheme_checker, "check_saved_preference", side_effect=fail_preference),
            patch.object(color_scheme_checker, "check_disabled_storage", return_value={"routes": 1}),
            redirect_stdout(stdout),
            self.assertRaises(SystemExit),
        ):
            color_scheme_checker.main()
        main_report = json.loads(stdout.getvalue())
        self.assertEqual(main_report["status"], "FAIL")
        self.assertEqual(main_report["case_failures"]["light"]["affected_routes"], [
            {"route": "/about/", "reasons": ["theme_assertion_failed"]},
            {"route": "/toolbox/", "reasons": ["navigation_failed"]},
        ])
        self.assertNotIn(marker, stdout.getvalue())

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = root / "assets" / "audit"
            audit.mkdir(parents=True)
            path = audit / "color-scheme-init-firefox.json"
            report.update(browser="firefox", status="FAIL")
            code = theme_failure_diagnostic_code(self.workflow)
            path.write_text(json.dumps(report), encoding="utf-8")
            summary_path = root / "summary.md"
            env = {**os.environ, "GITHUB_STEP_SUMMARY": str(summary_path), "GITHUB_WORKSPACE": str(ROOT)}
            result = subprocess.run([sys.executable, "-c", code], cwd=root, env=env,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = summary_path.read_text(encoding="utf-8")
            self.assertIn("`light`, route `/about/`: `theme_assertion_failed`", summary)
            self.assertIn("`dark`, route `/toolbox/`: `navigation_failed`", summary)
            self.assertIn("`dark`, route `/404.html`: `route_check_failed`", summary)
            self.assertIn("omitted or unavailable route details", summary)
            self.assertNotIn(marker, summary)

            invalid_routes = (
                {"route": f"/private-{marker}/", "reasons": ["route_check_failed"]},
                {"route": "/about/", "reasons": [marker]},
                {"route": "/about/", "reasons": []},
                {"route": "/about/", "reasons": ["route_check_failed", "route_check_failed"]},
                {"route": "/about/", "reasons": ["route_check_failed"], "extra": marker},
                {"route": "https://example.test/about/", "reasons": ["route_check_failed"]},
            )
            for index, item in enumerate(invalid_routes):
                with self.subTest(item=item):
                    broken = {**report, "case_failures": {
                        **report["case_failures"],
                        "light": {"error": "Theme case failed.", "affected_routes": [item]},
                    }}
                    path.write_text(json.dumps(broken), encoding="utf-8")
                    result_path = root / f"bad-{index}.md"
                    result = subprocess.run(
                        [sys.executable, "-c", code], cwd=root,
                        env={**env, "GITHUB_STEP_SUMMARY": str(result_path)},
                        capture_output=True, text=True,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    summary = result_path.read_text(encoding="utf-8")
                    self.assertIn("case sequence and results remain unverified", summary)
                    self.assertNotIn(marker, summary)
                    self.assertNotIn("Completed theme cases", summary)

            bad_case_route = {
                **report, "cases": {},
                "case_failures": {
                    **report["case_failures"],
                    "disabled_storage": {
                        "error": "Theme case failed.",
                        "affected_routes": [{"route": "/about/", "reasons": ["route_check_failed"]}],
                    },
                },
            }
            path.write_text(json.dumps(bad_case_route), encoding="utf-8")
            bad_summary = root / "bad-case-route.md"
            result = subprocess.run([sys.executable, "-c", code], cwd=root,
                                    env={**env, "GITHUB_STEP_SUMMARY": str(bad_summary)},
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("case sequence and results remain unverified", bad_summary.read_text(encoding="utf-8"))

            path.write_text(json.dumps(report), encoding="utf-8")
            unavailable_summary = root / "unavailable-inventory.md"
            result = subprocess.run([sys.executable, "-c", code], cwd=root,
                                    env={**env, "GITHUB_WORKSPACE": str(root),
                                         "GITHUB_STEP_SUMMARY": str(unavailable_summary)},
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("case sequence and results remain unverified", unavailable_summary.read_text(encoding="utf-8"))

    def test_shared_route_reason_contract_is_accepted_by_capture_and_summary(self):
        reasons = sorted(color_scheme_checker.ROUTE_REASON_CODES)
        route_failure = color_scheme_checker.RouteCheckFailure(
            [{"route": "/about/", "error": "synthetic-private-token"}],
            [{"route": "/about/", "reasons": reasons}],
        )
        report = {"cases": {}}
        color_scheme_checker.capture_case(
            report, "light", lambda: (_ for _ in ()).throw(route_failure),
            allowed_routes=["/about/"],
        )
        color_scheme_checker.capture_case(report, "dark", lambda: {"routes": 1})
        color_scheme_checker.capture_case(report, "disabled_storage", lambda: {"routes": 1})
        self.assertEqual(report["case_failures"]["light"]["affected_routes"][0]["reasons"], reasons)
        self.assertNotIn("synthetic-private-token", json.dumps(report))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = root / "assets" / "audit"
            audit.mkdir(parents=True)
            (audit / "color-scheme-init-firefox.json").write_text(
                json.dumps({**report, "browser": "firefox", "status": "FAIL"}), encoding="utf-8"
            )
            summary_path = root / "summary.md"
            result = subprocess.run(
                [sys.executable, "-c", theme_failure_diagnostic_code(self.workflow)], cwd=root,
                env={**os.environ, "GITHUB_WORKSPACE": str(ROOT),
                     "GITHUB_STEP_SUMMARY": str(summary_path)}, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = summary_path.read_text(encoding="utf-8")
            for reason in reasons:
                self.assertIn(f"`{reason}`", summary)
            self.assertNotIn("synthetic-private-token", summary)

    def test_responsive_diagnostic_executes_failure_without_raw_details(self):
        spec = importlib.util.spec_from_file_location("viewport_runner", ROOT / "scripts" / "run-viewport-qa.py")
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        secret = "SYNTHETIC_SECRET_in_exception_and_page"

        class Page:
            def goto(self, *args, **kwargs):
                raise RuntimeError(secret)
            def screenshot(self, **kwargs):
                raise AssertionError("Diagnostic mode must not capture screenshots")
        class Context:
            def new_page(self): return Page()
            def close(self): pass
        class Browser:
            def new_context(self, **kwargs): return Context()
            def close(self): pass
        class Manager:
            def __enter__(self): return SimpleNamespace(chromium=SimpleNamespace(launch=lambda **kw: Browser()))
            def __exit__(self, *args): return False
        fake_playwright = ModuleType("playwright")
        fake_api = ModuleType("playwright.sync_api")
        fake_api.sync_playwright = lambda: Manager()
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.json"
            with patch.dict(sys.modules, {"playwright": fake_playwright, "playwright.sync_api": fake_api}), \
                 patch.object(runner, "PAGES", [("about", "/about/")]), \
                 patch.object(runner, "VIEWPORTS", [{"name": "320", "width": 320, "height": 568}]), \
                 redirect_stdout(StringIO()) as output:
                self.assertEqual(runner.run_qa(diagnostic_output=report_path), 1)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["affected"], [{"page_index": 0, "viewport": "320", "issue_count": 1, "reason_codes": ["browser_error"]}])
            self.assertEqual(report["combinations_completed"], 1)
            self.assertNotIn(secret, report_path.read_text(encoding="utf-8"))
            self.assertNotIn(secret, output.getvalue())
            self.assertNotIn("base_url", report)
            original = report_path.read_bytes()
            with patch.dict(sys.modules, {"playwright": fake_playwright, "playwright.sync_api": fake_api}), \
                 patch.object(runner, "PAGES", [("about", "/about/")]), \
                 patch.object(runner, "VIEWPORTS", [{"name": "320", "width": 320, "height": 568}]), \
                 redirect_stdout(StringIO()):
                with self.assertRaises(FileExistsError):
                    runner.run_qa(diagnostic_output=report_path)
            self.assertEqual(original, report_path.read_bytes())

    def test_responsive_failure_does_not_publish_page_content(self):
        spec = importlib.util.spec_from_file_location("viewport_runner", ROOT / "scripts" / "run-viewport-qa.py")
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        secret = "SYNTHETIC_PRIVATE_PAGE_CONTENT"
        class Page:
            def goto(self, *args, **kwargs): return SimpleNamespace(status=200)
            def evaluate(self, code):
                if "maxW" in code:
                    return {"maxW": 400, "vw": 320, "offenders": [{"tag": "div", "id": secret, "cls": secret}]}
                if "const problems" in code: return [{"src": secret, "w": 500}]
                return [{"fs": 10, "txt": secret}]
            def query_selector(self, name):
                return SimpleNamespace(is_visible=lambda: True) if name == ".nav-toggle" else None
        class Context:
            def new_page(self): return Page()
            def close(self): pass
        class Browser:
            def new_context(self, **kwargs): return Context()
            def close(self): pass
        class Manager:
            def __enter__(self): return SimpleNamespace(chromium=SimpleNamespace(launch=lambda **kw: Browser()))
            def __exit__(self, *args): return False
        fake_api = ModuleType("playwright.sync_api")
        fake_api.sync_playwright = lambda: Manager()
        with tempfile.TemporaryDirectory() as directory:
            failure = Path(directory) / "failure.json"
            with patch.dict(sys.modules, {"playwright": ModuleType("playwright"), "playwright.sync_api": fake_api}), \
                 patch.object(runner, "PAGES", [("home", "/")]), \
                 patch.object(runner, "VIEWPORTS", [{"name": "320", "width": 320, "height": 568}]), \
                 patch.object(runner.time, "sleep"), redirect_stdout(StringIO()) as output:
                self.assertEqual(runner.run_qa(diagnostic_output=failure), 1)
            self.assertNotIn(secret, failure.read_text(encoding="utf-8"))
            self.assertNotIn(secret, output.getvalue())
            report = json.loads(failure.read_text(encoding="utf-8"))
            self.assertEqual(report["total_issues"], 2)
            self.assertEqual(report["total_warnings"], 1)
            self.assertEqual(report["affected"][0]["reason_codes"], ["horizontal_overflow", "image_overflow"])

    def test_site_ci_responsive_smoke_checks_the_actual_report(self):
        workflow = (ROOT / ".github" / "workflows" / "validate.yml").read_text(encoding="utf-8")
        block = workflow.split("- name: Smoke-test isolated responsive QA in Chromium", 1)[1].split("\n      - name:", 1)[0]
        code = textwrap.dedent(block.split("python3 - <<'PY'\n", 1)[1].rsplit("          PY", 1)[0])
        names = ["320", "375", "390", "414", "768", "1024", "1280", "1440"]
        report = {"pages_tested": 1, "total_combinations": 8, "total_issues": 0,
                  "screenshots_dir": None, "viewports_tested": names,
                  "results": [{"page": "/", "viewports": [{"viewport": name, "issues": []} for name in names]}]}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "success.json"
            env = {**os.environ, "SMOKE_DIR": str(root)}
            def check():
                return subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
            self.assertNotEqual(check().returncode, 0)
            path.write_text(json.dumps(report), encoding="utf-8")
            self.assertEqual(check().returncode, 0)
            (root / "failure.json").write_text("{}", encoding="utf-8")
            self.assertNotEqual(check().returncode, 0)
            (root / "failure.json").unlink()
            path.write_text(json.dumps({**report, "total_combinations": 7}), encoding="utf-8")
            self.assertNotEqual(check().returncode, 0)

    def test_responsive_success_report_is_current_and_failure_report_absent(self):
        spec = importlib.util.spec_from_file_location("viewport_runner", ROOT / "scripts" / "run-viewport-qa.py")
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        class Page:
            def goto(self, *args, **kwargs): return SimpleNamespace(status=200)
            def evaluate(self, code):
                if "maxW" in code: return {"maxW": 320, "vw": 320, "offenders": []}
                return []
            def query_selector(self, name):
                return SimpleNamespace(is_visible=lambda: True) if name == ".nav-toggle" else None
        class Context:
            def new_page(self): return Page()
            def close(self): pass
        class Browser:
            def new_context(self, **kwargs): return Context()
            def close(self): pass
        class Manager:
            def __enter__(self): return SimpleNamespace(chromium=SimpleNamespace(launch=lambda **kw: Browser()))
            def __exit__(self, *args): return False
        fake_api = ModuleType("playwright.sync_api")
        fake_api.sync_playwright = lambda: Manager()
        with tempfile.TemporaryDirectory() as directory:
            failure = Path(directory) / "failure.json"
            success = Path(directory) / "success.json"
            with patch.dict(sys.modules, {"playwright": ModuleType("playwright"), "playwright.sync_api": fake_api}), \
                 patch.object(runner, "PAGES", [("home", "/")]), \
                 patch.object(runner, "VIEWPORTS", [{"name": "320", "width": 320, "height": 568}]), \
                 patch.object(runner.time, "sleep"), redirect_stdout(StringIO()):
                self.assertEqual(runner.run_qa(diagnostic_output=failure, success_output=success), 0)
            self.assertFalse(failure.exists())
            report = json.loads(success.read_text(encoding="utf-8"))
            self.assertEqual(report["total_issues"], 0)
            self.assertEqual(report["total_combinations"], 1)
            self.assertEqual(report["results"][0]["page"], "/")
            self.assertIsNone(report["screenshots_dir"])

    def test_responsive_report_validation_rejects_untrusted_or_partial_content(self):
        block = self.workflow.split("- name: Validate responsive failure report (diagnostic only)", 1)[1].split("\n      - name:", 1)[0]
        code = textwrap.dedent(block.split("python3 - <<'PY'\n", 1)[1].rsplit("          PY", 1)[0])
        spec = importlib.util.spec_from_file_location("viewport_runner_contract_test", ROOT / "scripts" / "run-viewport-qa.py")
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        good = {"version": 1, "status": "FAIL", "diagnostic_only": True,
                "pages_completed": len(runner.PAGES),
                "combinations_completed": len(runner.PAGES) * len(runner.VIEWPORTS),
                "total_issues": 1, "total_warnings": 0,
                "affected": [{"page_index": 0, "viewport": "320", "issue_count": 1, "reason_codes": ["browser_error"]}]}
        bad = ["{", json.dumps({**good, "error": "synthetic-secret"}),
               json.dumps({**good, "affected": [{**good["affected"][0], "reason_codes": ["synthetic-secret"]}]}),
               json.dumps({**good, "total_issues": 2}),
               json.dumps({**good, "pages_completed": 5, "combinations_completed": 1}),
               json.dumps({**good, "affected": [{**good["affected"][0], "viewport": "9999"}]}),
               json.dumps(good).replace('"status": "FAIL"', '"status": "synthetic-secret", "status": "FAIL"'),
               json.dumps(good).replace('"viewport": "320"', '"viewport": "synthetic-secret", "viewport": "320"')]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            env = {**os.environ, "RESPONSIVE_FAILURE_REPORT": str(path), "GITHUB_WORKSPACE": str(ROOT)}
            for payload, accepted in [(json.dumps(good), True), *[(v, False) for v in bad]]:
                path.write_text(payload, encoding="utf-8")
                result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode == 0, accepted)
                self.assertNotIn("synthetic-secret", result.stdout + result.stderr)
            path.write_text(json.dumps(good), encoding="utf-8")
            missing_workspace = {**env, "GITHUB_WORKSPACE": str(Path(directory) / "missing")}
            self.assertNotEqual(subprocess.run([sys.executable, "-c", code], env=missing_workspace, capture_output=True).returncode, 0)
            path.unlink()
            self.assertNotEqual(subprocess.run([sys.executable, "-c", code], env=env, capture_output=True).returncode, 0)

    def test_responsive_main_hides_setup_error_only_in_isolated_mode(self):
        spec = importlib.util.spec_from_file_location("viewport_runner", ROOT / "scripts" / "run-viewport-qa.py")
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        args = SimpleNamespace(diagnostic_output=Path("unused"), success_output=Path("unused-success"),
                               start=0, end=1, batch=None)
        with patch.object(runner, "_parse_args", return_value=args), \
             patch.object(runner, "ensure_stub", side_effect=RuntimeError("synthetic setup secret")), \
             redirect_stdout(StringIO()), redirect_stderr(StringIO()) as error:
            self.assertEqual(runner.main(), 1)
        self.assertNotIn("synthetic setup secret", error.getvalue())
        self.assertIn("diagnostic report unavailable", error.getvalue())

    def test_responsive_summary_reports_actual_upload_outcome(self):
        block = self.workflow.split(RESPONSIVE_FAILURE_LINK_STEP, 1)[1].split("\n      - name:", 1)[0]
        script = textwrap.dedent(block.split("        run: |\n", 1)[1])
        bash = shutil.which("bash")
        if os.name == "nt":
            git = shutil.which("git")
            candidate = Path(git).resolve().parent.parent / "bin" / "bash.exe" if git else None
            bash = str(candidate) if candidate and candidate.is_file() else None
        if not bash:
            self.skipTest("Bash is unavailable")
        scenarios = [("success", "42", "https://example.invalid/artifact", True),
                     ("success", "", "", False), ("failure", "42", "https://example.invalid/artifact", False),
                     ("skipped", "", "", False)]
        with tempfile.TemporaryDirectory() as directory:
            for index, (outcome, artifact_id, url, linked) in enumerate(scenarios):
                path = Path(directory) / f"summary-{index}.md"
                shell_path = path.as_posix()
                if os.name == "nt": shell_path = "/" + shell_path[0].lower() + shell_path[2:]
                env = {**os.environ, "UPLOAD_OUTCOME": outcome, "ARTIFACT_ID": artifact_id,
                       "ARTIFACT_URL": url, "GITHUB_STEP_SUMMARY": shell_path}
                result = subprocess.run([bash, "-c", script], env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                summary = path.read_text(encoding="utf-8")
                self.assertEqual("Download the sanitized" in summary, linked)
                self.assertEqual("report unavailable" in summary, not linked)
                self.assertIn("not validated release evidence", summary)
                self.assertNotIn(chr(0x2014), summary)

    def test_visitor_summary_reports_actual_upload_outcome(self):
        block = self.workflow.split(VISITOR_FAILURE_LINK_STEP, 1)[1].split("\n      - name:", 1)[0]
        script = textwrap.dedent(block.split("        run: |\n", 1)[1])
        bash = shutil.which("bash")
        if os.name == "nt":
            git = shutil.which("git")
            candidate = Path(git).resolve().parent.parent / "bin" / "bash.exe" if git else None
            bash = str(candidate) if candidate and candidate.is_file() else None
        if not bash:
            self.skipTest("Bash is unavailable")
        scenarios = [("success", "42", "https://example.invalid/artifact", True),
                     ("success", "", "", False), ("failure", "42", "https://example.invalid/artifact", False),
                     ("skipped", "", "", False)]
        with tempfile.TemporaryDirectory() as directory:
            for index, (outcome, artifact_id, url, linked) in enumerate(scenarios):
                path = Path(directory) / f"summary-{index}.md"
                shell_path = path.as_posix()
                if os.name == "nt": shell_path = "/" + shell_path[0].lower() + shell_path[2:]
                env = {**os.environ, "UPLOAD_OUTCOME": outcome, "ARTIFACT_ID": artifact_id,
                       "ARTIFACT_URL": url, "GITHUB_STEP_SUMMARY": shell_path}
                result = subprocess.run([bash, "-c", script], env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                summary = path.read_text(encoding="utf-8")
                self.assertEqual("Download the sanitized" in summary, linked)
                self.assertEqual("report unavailable" in summary, not linked)
                self.assertIn("not validated release evidence", summary)
                self.assertNotIn(chr(0x2014), summary)

    def test_responsive_interruption_survives_cleanup_failure_without_report(self):
        spec = importlib.util.spec_from_file_location("viewport_runner", ROOT / "scripts" / "run-viewport-qa.py")
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        class Page:
            def goto(self, *args, **kwargs): raise KeyboardInterrupt()
        class Context:
            def new_page(self): return Page()
            def close(self): raise RuntimeError("synthetic cleanup secret")
        class Browser:
            def new_context(self, **kwargs): return Context()
        class Manager:
            def __enter__(self): return SimpleNamespace(chromium=SimpleNamespace(launch=lambda **kw: Browser()))
            def __exit__(self, *args): return False
        fake_api = ModuleType("playwright.sync_api")
        fake_api.sync_playwright = lambda: Manager()
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "failure.json"
            with patch.dict(sys.modules, {"playwright": ModuleType("playwright"), "playwright.sync_api": fake_api}), \
                 patch.object(runner, "PAGES", [("home", "/")]), \
                 patch.object(runner, "VIEWPORTS", [{"name": "320", "width": 320, "height": 568}]), \
                 redirect_stdout(StringIO()):
                with self.assertRaises(KeyboardInterrupt):
                    runner.run_qa(diagnostic_output=report)
            self.assertFalse(report.exists())

    def test_responsive_diagnostic_startup_and_cancellation_leave_no_report(self):
        spec = importlib.util.spec_from_file_location("viewport_runner", ROOT / "scripts" / "run-viewport-qa.py")
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        for error in (RuntimeError("synthetic secret"), KeyboardInterrupt(), SystemExit(7)):
            with self.subTest(error=type(error).__name__), tempfile.TemporaryDirectory() as directory:
                report_path = Path(directory) / "report.json"
                fake_playwright = ModuleType("playwright")
                fake_api = ModuleType("playwright.sync_api")
                def start(): raise error
                fake_api.sync_playwright = start
                with patch.dict(sys.modules, {"playwright": fake_playwright, "playwright.sync_api": fake_api}), \
                     redirect_stdout(StringIO()):
                    with self.assertRaises(type(error)):
                        runner.run_qa(diagnostic_output=report_path)
                self.assertFalse(report_path.exists())

    def test_release_gates_reject_pass_reports_with_failure_indicators(self):
        verify_block = self.workflow.split(THEME_VERIFY_STEP, 1)[1].split("\n      - name:", 1)[0]
        job_block = self.workflow.split(POST_UPLOAD_JOB, 1)[1].split(DEPLOY_JOB, 1)[0]
        downloaded_block = job_block.split(POST_UPLOAD_VERIFY_STEP, 1)[1].split(THEME_SUMMARY_STEP, 1)[0]
        summary_block = job_block.split(THEME_SUMMARY_STEP, 1)[1].split("\n      - name:", 1)[0]
        def python_code(block):
            return textwrap.dedent(block.split("python3 - <<'PY'\n", 1)[1].rsplit("          PY", 1)[0])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = root / "assets" / "audit"
            audit.mkdir(parents=True)
            (audit / THEME_INDEX_NAME).write_text(browser_theme_index(), encoding="utf-8")
            docs = root / "assets" / "docs"
            docs.mkdir(parents=True)
            (docs / "audit-report.md").write_text(audit_report_index_link(), encoding="utf-8")
            flags = (
                {"case_results_version": 1},
                {"case_failures": {"light": {"error": "Theme case failed."}}},
                {"not_run_cases": ["dark"]},
                {"failed_case": "dark"},
                {"cleanup_failed": True},
            )
            for flag in flags:
                with self.subTest(flag=flag):
                    for browser, _, version in browser_versions():
                        report = {
                            "browser": browser, "browser_version": version, "status": "PASS",
                            "cases": {"light": {}, "dark": {}, "disabled_storage": {}},
                            **(flag if browser == "firefox" else {}),
                        }
                        (audit / f"color-scheme-init-{browser}.json").write_text(
                            json.dumps(report), encoding="utf-8"
                        )
                    env = {**os.environ, "VALIDATION_ARTIFACT_DIR": str(root),
                           "GITHUB_STEP_SUMMARY": str(root / "summary.md")}
                    for block in (verify_block, downloaded_block, summary_block):
                        result = subprocess.run([sys.executable, "-c", python_code(block)],
                                                cwd=root, env=env, capture_output=True, text=True)
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn("diagnostic case failures are not release evidence", result.stderr)

    def test_multi_case_diagnostics_validate_sequence_and_hide_untrusted_fields(self):
        code = theme_failure_diagnostic_code(self.workflow)
        good = {
            "browser": "firefox", "status": "FAIL", "diagnostic_only": True,
            "failure_stage": "theme_check", "case_results_version": 1,
            "attempted_cases": ["light", "dark", "disabled_storage"],
            "cases": {"dark": {"routes": 1}},
            "case_failures": {"light": {"error": "Theme case failed."},
                              "disabled_storage": {"error": "Theme case failed."}},
            "failed_case": "light", "not_run_cases": [], "cleanup_failed": True,
            "error": "synthetic-private-token",
        }
        conflicts = (
            {"case_results_version": True},
            {"case_results_version": 2},
            {"browser": "chromium"},
            {"browser": None},
            {"attempted_cases": ["light", "dark", "dark"]},
            {"attempted_cases": ["dark", "light", "disabled_storage"]},
            {"attempted_cases": ["light", "dark", "unknown"]},
            {"not_run_cases": ["dark"]},
            {"not_run_cases": "disabled_storage"},
            {"cases": {"light": {}, "dark": {}}},
            {"cases": {"dark": None}},
            {"case_failures": {"light": {"error": "synthetic-private-token"}}},
            {"case_failures": {"unknown": {"error": "Theme case failed."}}},
            {"failed_case": "disabled_storage"},
            {"failed_routes": [{"route": "/synthetic-private-token"}]},
            {"failure_stage": "browser_startup"},
            {"failure_stage": "browser_cleanup"},
            {"status": "PASS"},
            {"cleanup_failed": 1},
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = root / "assets" / "audit"
            audit.mkdir(parents=True)
            path = audit / "color-scheme-init-firefox.json"
            for index, update in enumerate(({}, *conflicts, {"missing_browser": True})):
                with self.subTest(update=update):
                    candidate = {**good, **update}
                    if candidate.pop("missing_browser", False):
                        candidate.pop("browser")
                    path.write_text(json.dumps(candidate), encoding="utf-8")
                    summary_path = root / f"summary-{index}.md"
                    result = subprocess.run(
                        [sys.executable, "-c", code], cwd=root,
                        env={**os.environ, "GITHUB_WORKSPACE": str(ROOT),
                             "GITHUB_STEP_SUMMARY": str(summary_path)},
                        capture_output=True, text=True,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    summary = summary_path.read_text(encoding="utf-8")
                    self.assertNotIn("synthetic-private-token", summary)
                    if update:
                        self.assertIn("case sequence and results remain unverified", summary)
                        self.assertNotIn("Completed theme cases", summary)
                        self.assertNotIn("Not run:", summary)
                        self.assertNotIn("theme checks failed in", summary)
                    else:
                        self.assertIn("theme checks failed in `light`, `disabled_storage`", summary)
                        self.assertIn("Completed theme cases (diagnostic only; not validated evidence): `dark`", summary)
                        self.assertIn("Not run: none reported", summary)
                        self.assertIn("Browser cleanup also failed", summary)
            partial = {
                **good, "attempted_cases": ["light", "dark"],
                "case_failures": {"light": {"error": "Theme case failed."}},
                "not_run_cases": ["disabled_storage"],
            }
            path.write_text(json.dumps(partial), encoding="utf-8")
            partial_summary = root / "summary-partial.md"
            result = subprocess.run(
                [sys.executable, "-c", code], cwd=root,
                env={**os.environ, "GITHUB_WORKSPACE": str(ROOT),
                     "GITHUB_STEP_SUMMARY": str(partial_summary)},
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = partial_summary.read_text(encoding="utf-8")
            self.assertIn("theme checks failed in `light`", summary)
            self.assertIn("Not run: `disabled_storage`", summary)
            self.assertNotIn("case sequence and results remain unverified", summary)

            path.write_text(json.dumps(good), encoding="utf-8")
            missing_contract_summary = root / "summary-missing-contract.md"
            result = subprocess.run(
                [sys.executable, "-c", code], cwd=root,
                env={**os.environ, "GITHUB_WORKSPACE": str(root),
                     "PYTHONPATH": str(ROOT / "scripts"),
                     "GITHUB_STEP_SUMMARY": str(missing_contract_summary)},
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = missing_contract_summary.read_text(encoding="utf-8")
            self.assertIn("case sequence and results remain unverified", summary)
            self.assertNotIn("theme checks failed in", summary)

    def test_multi_case_cancellation_is_not_caught_or_followed_by_other_cases(self):
        for interrupt in (KeyboardInterrupt, SystemExit):
            with self.subTest(interrupt=interrupt.__name__):
                report = {"cases": {}}
                color_scheme_checker.capture_case(
                    report, "light", lambda: (_ for _ in ()).throw(ValueError("first failure"))
                )
                with self.assertRaises(interrupt):
                    color_scheme_checker.capture_case(
                        report, "dark", lambda: (_ for _ in ()).throw(interrupt())
                    )
                self.assertEqual(report["attempted_cases"], ["light", "dark"])
                self.assertEqual(report["not_run_cases"], ["disabled_storage"])
                self.assertEqual(set(report["case_failures"]), {"light"})

    def test_main_cancellation_after_case_failure_closes_without_running_later_cases(self):
        playwright_api = ModuleType("playwright.sync_api")
        closed = []
        attempted = []

        class FakeBrowser:
            version = "test-browser"
            def close(self):
                closed.append(True)

        class PlaywrightManager:
            def __enter__(self):
                return SimpleNamespace(chromium=SimpleNamespace(launch=lambda **_: FakeBrowser()))
            def __exit__(self, *_args):
                return False

        playwright_api.sync_playwright = PlaywrightManager
        playwright_module = ModuleType("playwright")
        playwright_module.sync_api = playwright_api
        def check_preference(_browser, _base, preference, _routes):
            attempted.append(preference)
            if preference == "light":
                raise ValueError("first failure")
            raise KeyboardInterrupt()
        with (
            patch.dict(sys.modules, {"playwright": playwright_module, "playwright.sync_api": playwright_api}),
            patch.object(sys, "argv", [str(COLOR_SCHEME_SCRIPT)]),
            patch.object(color_scheme_checker, "browser_routes", return_value=[]),
            patch.object(color_scheme_checker, "check_saved_preference", side_effect=check_preference),
            patch.object(color_scheme_checker, "check_disabled_storage") as disabled,
            redirect_stdout(StringIO()),
            self.assertRaises(KeyboardInterrupt),
        ):
            color_scheme_checker.main()
        self.assertEqual(attempted, ["light", "dark"])
        disabled.assert_not_called()
        self.assertEqual(closed, [True])

    def test_multi_case_main_failure_and_cleanup_preserve_safe_diagnostics(self):
        marker = "synthetic-private-token"
        playwright_api = ModuleType("playwright.sync_api")

        class FakeBrowser:
            version = "test-browser"

            def close(self):
                raise RuntimeError(marker)

        class PlaywrightManager:
            def __enter__(self):
                return SimpleNamespace(chromium=SimpleNamespace(launch=lambda **_: FakeBrowser()))

            def __exit__(self, *_args):
                return False

        playwright_api.sync_playwright = PlaywrightManager
        playwright_module = ModuleType("playwright")
        playwright_module.sync_api = playwright_api
        def check_preference(_browser, _base, preference, _routes):
            if preference == "light":
                raise RuntimeError(marker)
            return {"routes": 1}
        stdout = StringIO()
        with (
            patch.dict(sys.modules, {"playwright": playwright_module, "playwright.sync_api": playwright_api}),
            patch.object(sys, "argv", [str(COLOR_SCHEME_SCRIPT)]),
            patch.object(color_scheme_checker, "browser_routes", return_value=[]),
            patch.object(color_scheme_checker, "check_saved_preference", side_effect=check_preference),
            patch.object(color_scheme_checker, "check_disabled_storage", side_effect=RuntimeError(marker)),
            redirect_stdout(stdout),
            self.assertRaises(SystemExit) as result,
        ):
            color_scheme_checker.main()
        report = json.loads(stdout.getvalue())
        self.assertEqual(result.exception.code, 1)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["failure_stage"], "theme_check")
        self.assertEqual(report["attempted_cases"], ["light", "dark", "disabled_storage"])
        self.assertEqual(report["not_run_cases"], [])
        self.assertEqual(set(report["case_failures"]), {"light", "disabled_storage"})
        self.assertEqual(set(report["cases"]), {"dark"})
        self.assertIs(report["cleanup_failed"], True)
        self.assertNotIn(marker, stdout.getvalue())

    def test_all_successful_cases_remain_pass_release_evidence(self):
        playwright_api = ModuleType("playwright.sync_api")

        class FakeBrowser:
            version = "test-browser"
            def close(self):
                pass

        class PlaywrightManager:
            def __enter__(self):
                return SimpleNamespace(chromium=SimpleNamespace(launch=lambda **_: FakeBrowser()))
            def __exit__(self, *_args):
                return False

        playwright_api.sync_playwright = PlaywrightManager
        playwright_module = ModuleType("playwright")
        playwright_module.sync_api = playwright_api
        stdout = StringIO()
        with (
            patch.dict(sys.modules, {"playwright": playwright_module, "playwright.sync_api": playwright_api}),
            patch.object(sys, "argv", [str(COLOR_SCHEME_SCRIPT)]),
            patch.object(color_scheme_checker, "browser_routes", return_value=[]),
            patch.object(color_scheme_checker, "check_saved_preference", return_value={"routes": 1}),
            patch.object(color_scheme_checker, "check_disabled_storage", return_value={"routes": 1}),
            redirect_stdout(stdout),
        ):
            color_scheme_checker.main()
        report, _ = json.JSONDecoder().raw_decode(stdout.getvalue())
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["attempted_cases"], ["light", "dark", "disabled_storage"])
        self.assertEqual(report["not_run_cases"], [])
        self.assertEqual(report["case_failures"], {})
        self.assertNotIn("case_results_version", report)
        block = self.workflow.split(THEME_VERIFY_STEP, 1)[1].split("\n      - name:", 1)[0]
        code = textwrap.dedent(block.split("python3 - <<'PY'\n", 1)[1].rsplit("          PY", 1)[0])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = root / "assets" / "audit"
            audit.mkdir(parents=True)
            for browser, _, version in browser_versions():
                (audit / f"color-scheme-init-{browser}.json").write_text(
                    json.dumps({**report, "browser": browser, "browser_version": version}),
                    encoding="utf-8",
                )
            result = subprocess.run([sys.executable, "-c", code], cwd=root,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_browser_launch_failure_is_reported_before_theme_checks_begin(self):
        playwright_api = ModuleType("playwright.sync_api")

        def fail_launch(**_kwargs):
            raise RuntimeError("browser could not be launched")

        class PlaywrightManager:
            def __enter__(self):
                return SimpleNamespace(
                    chromium=SimpleNamespace(launch=fail_launch)
                )

            def __exit__(self, *_args):
                return False

        playwright_api.sync_playwright = PlaywrightManager
        playwright_module = ModuleType("playwright")
        playwright_module.sync_api = playwright_api

        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "browser-report.json"
            stdout = tempfile.TemporaryFile(mode="w+t", encoding="utf-8")
            with (
                patch.dict(
                    sys.modules,
                    {
                        "playwright": playwright_module,
                        "playwright.sync_api": playwright_api,
                    },
                ),
                patch.object(
                    sys,
                    "argv",
                    [
                        str(COLOR_SCHEME_SCRIPT),
                        "--browser",
                        "chromium",
                        "--output",
                        str(report_path),
                    ],
                ),
                patch.object(color_scheme_checker, "browser_routes", return_value=[]),
                patch.object(sys, "stdout", stdout),
                self.assertRaises(SystemExit),
            ):
                color_scheme_checker.main()

            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["failure_stage"], "browser_startup")
            self.assertEqual(report["setup_step"], "launching_browser")
            self.assertNotIn("failed_case", report)
            self.assertEqual(
                report["not_run_cases"],
                ["light", "dark", "disabled_storage"],
            )
            self.assertEqual(report["error"], "browser could not be launched")
            stdout.close()

    def test_browser_setup_failures_name_the_last_step_reached(self):
        cases = (
            ("route preparation", "preparing_routes", "route scan failed"),
            ("browser manager entry", "entering_browser_manager", "manager failed"),
        )
        for label, setup_step, message in cases:
            with self.subTest(step=label):
                playwright_api = ModuleType("playwright.sync_api")

                def unexpected_launch(**_kwargs):
                    raise AssertionError("launch must not run")

                class PlaywrightManager:
                    def __enter__(self):
                        if setup_step == "entering_browser_manager":
                            raise RuntimeError(message)
                        return SimpleNamespace(
                            chromium=SimpleNamespace(
                                launch=unexpected_launch
                            )
                        )

                    def __exit__(self, *_args):
                        return False

                playwright_api.sync_playwright = PlaywrightManager
                playwright_module = ModuleType("playwright")
                playwright_module.sync_api = playwright_api
                with tempfile.TemporaryDirectory() as directory:
                    report_path = Path(directory) / "browser-report.json"
                    stdout = tempfile.TemporaryFile(mode="w+t", encoding="utf-8")
                    with (
                        patch.dict(
                            sys.modules,
                            {
                                "playwright": playwright_module,
                                "playwright.sync_api": playwright_api,
                            },
                        ),
                        patch.object(
                            sys,
                            "argv",
                            [
                                str(COLOR_SCHEME_SCRIPT),
                                "--browser",
                                "chromium",
                                "--output",
                                str(report_path),
                            ],
                        ),
                        patch.object(
                            color_scheme_checker,
                            "browser_routes",
                            side_effect=RuntimeError(message)
                            if setup_step == "preparing_routes"
                            else lambda: [],
                        ),
                        patch.object(sys, "stdout", stdout),
                        self.assertRaises(SystemExit),
                    ):
                        color_scheme_checker.main()

                    report = json.loads(report_path.read_text(encoding="utf-8"))
                    self.assertEqual(report["failure_stage"], "browser_startup")
                    self.assertEqual(report["setup_step"], setup_step)
                    self.assertEqual(report["error"], message)
                    stdout.close()

    def test_playwright_import_failure_is_identified_as_setup_failure(self):
        original_import = __import__

        def fail_playwright_import(name, *args, **kwargs):
            if name == "playwright.sync_api":
                raise ImportError("Playwright is unavailable")
            return original_import(name, *args, **kwargs)

        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "browser-report.json"
            stdout = tempfile.TemporaryFile(mode="w+t", encoding="utf-8")
            with (
                patch("builtins.__import__", side_effect=fail_playwright_import),
                patch.object(
                    sys,
                    "argv",
                    [
                        str(COLOR_SCHEME_SCRIPT),
                        "--browser",
                        "chromium",
                        "--output",
                        str(report_path),
                    ],
                ),
                patch.object(sys, "stdout", stdout),
                self.assertRaises(SystemExit),
            ):
                color_scheme_checker.main()

            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["failure_stage"], "browser_startup")
            self.assertEqual(report["setup_step"], "loading_playwright")
            self.assertEqual(report["error"], "Playwright is unavailable")
            stdout.close()

    def test_browser_route_checks_collect_all_failures(self):
        checked = []

        def check(route):
            checked.append(route)
            if route != "/healthy/":
                raise AssertionError(f"{route} has the wrong theme")
            return {"route_evidence": [{"route": route}]}

        with self.assertRaises(color_scheme_checker.RouteCheckFailure) as failure:
            color_scheme_checker.collect_route_evidence(
                ["/healthy/", "/first/", "/second/"], check
            )

        self.assertEqual(checked, ["/healthy/", "/first/", "/second/"])
        self.assertEqual(
            failure.exception.failed_routes,
            [
                {"route": "/first/", "error": "/first/ has the wrong theme"},
                {"route": "/second/", "error": "/second/ has the wrong theme"},
            ],
        )

        report = {"cases": {}}
        color_scheme_checker.capture_case(
            report,
            "dark",
            lambda: color_scheme_checker.collect_route_evidence(
                ["/first/", "/second/"], check
            )
        )
        self.assertTrue(report["diagnostic_only"])
        self.assertEqual(report["failed_case"], "dark")
        self.assertEqual(report["case_failures"]["dark"], {
            "error": "Theme case failed.", "route_details_incomplete": True,
        })
        self.assertNotIn("failed_routes", report)

    def test_browser_route_reports_every_independent_theme_assertion_failure(self):
        class FakePage:
            url = "https://example.test/theme-regression/"

            def on(self, *_args):
                pass

            def goto(self, *_args, **_kwargs):
                return SimpleNamespace(ok=True, status=200)

            def evaluate(self, *_args):
                return {
                    "scheme": "light",
                    "savedPreference": "dark",
                    "readyState": "interactive",
                    "colorSchemeScript": False,
                }

            def wait_for_load_state(self, *_args):
                pass

        class FakeContext:
            def new_page(self):
                return FakePage()

            def close(self):
                pass

        def check_route(route):
            return {
                "route_evidence": [
                    color_scheme_checker._check_saved_preference_context(
                        object(),
                        "https://example.test/",
                        "dark",
                        [route],
                    )
                ]
            }

        with (
            patch.object(
                color_scheme_checker, "load_context", return_value=FakeContext()
            ),
            patch.object(
                color_scheme_checker,
                "paint_timing",
                return_value={
                    "asset_response_end": None,
                    "domcontentloaded_start": None,
                    "first_paint": 3.0,
                    "first_paint_status": "observed",
                },
            ),
            self.assertRaises(color_scheme_checker.RouteCheckFailure) as failure,
        ):
            color_scheme_checker.collect_route_evidence(
                ["/theme-regression/"], check_route
            )

        route_failure = failure.exception.failed_routes[0]
        self.assertEqual(route_failure["route"], "/theme-regression/")
        self.assertIn("4 independent theme check(s) failed", route_failure["error"])
        for detail in (
            "initial DOM scheme: expected saved 'dark' preference",
            "external color-scheme asset: page does not load",
            "incomplete color-scheme bootstrap event trace",
            "missing browser timing for color-scheme bootstrap",
            "color-scheme asset has no resource timing entry",
        ):
            self.assertIn(detail, route_failure["error"])

    def test_utility_recovery_reports_independent_failures_together(self):
        expected_url = "https://example.test/"

        class FakeAction:
            def count(self):
                return 1

            def is_visible(self):
                return True

            def inner_text(self):
                return "Wrong label"

            def evaluate(self, expression):
                if expression == "element => element.href":
                    return expected_url
                if "href: element.href" in expression:
                    return {"href": expected_url, "focused": True, "visible": True}
                return True

        class FakeHeading:
            def is_visible(self):
                return False

        class FakeNavigation:
            value = SimpleNamespace(ok=True, status=200)

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

        class FakeKeyboard:
            def press(self, key):
                if key == "Enter":
                    page.url = expected_url

        class FakePage:
            context = object()
            url = "https://example.test/404.html"
            keyboard = FakeKeyboard()

            def locator(self, selector):
                return FakeHeading() if selector == "h1" else FakeAction()

            def expect_navigation(self, **_kwargs):
                return FakeNavigation()

        page = FakePage()
        with (
            patch.object(color_scheme_checker, "link_traversal_key", return_value="Tab"),
            patch.object(
                color_scheme_checker,
                "storage_error_name",
                side_effect=["SecurityError", "NotAllowedError"],
            ),
            self.assertRaises(AssertionError) as failure,
        ):
            color_scheme_checker.check_utility_recovery(
                page,
                "https://example.test/",
                "/404.html",
                ["synthetic-private-page-error-token"],
            )

        report = str(failure.exception)
        self.assertIn("4 independent keyboard recovery check(s) failed", report)
        for detail in (
            "primary recovery label",
            "primary recovery action no longer says 'Return home'",
            "destination primary content",
            "destination storage denial",
            "page errors occurred during keyboard recovery",
        ):
            self.assertIn(detail, report)
        self.assertNotIn("synthetic-private-page-error-token", report)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = root / "assets" / "audit"
            audit.mkdir(parents=True)
            serialized = json.dumps({
                "browser": "firefox", "status": "FAIL", "diagnostic_only": True,
                "failure_stage": "theme_check", "failed_case": "disabled_storage",
                "cases": {"light": {}, "dark": {}}, "not_run_cases": [],
                "error": report[report.index("page errors:"):],
                "failed_routes": [{"route": "/404.html", "error": report}],
            })
            self.assertNotIn("synthetic-private-page-error-token", serialized)
            (audit / "color-scheme-init-firefox.json").write_text(serialized, encoding="utf-8")
            summary_path = root / "summary.md"
            result = subprocess.run(
                [sys.executable, "-c", theme_failure_diagnostic_code(self.workflow)],
                cwd=root, env={**os.environ, "GITHUB_STEP_SUMMARY": str(summary_path)},
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = summary_path.read_text(encoding="utf-8")
            self.assertIn("primary recovery label", summary)
            self.assertIn("page errors occurred during keyboard recovery", summary)
            self.assertNotIn("synthetic-private-page-error-token", summary)

    def test_utility_recovery_setup_failure_stops_follow_on_checks(self):
        class FakeAction:
            def count(self):
                return 0

        class FakePage:
            context = object()

            def locator(self, _selector):
                return FakeAction()

        with (
            patch.object(
                color_scheme_checker,
                "storage_error_name",
                side_effect=AssertionError("storage check must not run"),
            ),
            patch.object(
                color_scheme_checker,
                "link_traversal_key",
                side_effect=AssertionError("keyboard setup must not run"),
            ),
            self.assertRaisesRegex(
                AssertionError,
                "/404.html: expected one visible primary recovery action",
            ),
        ):
            color_scheme_checker.check_utility_recovery(
                FakePage(), "https://example.test/", "/404.html", []
            )

    def test_utility_recovery_navigation_failure_skips_destination_checks(self):
        class FakeAction:
            def count(self):
                return 1

            def is_visible(self):
                return True

            def inner_text(self):
                return "Return home"

            def evaluate(self, expression):
                if expression == "element => element.href":
                    return "https://example.test/"
                if "href: element.href" in expression:
                    return {"href": "https://example.test/", "focused": True, "visible": True}
                return True

        class FakeNavigation:
            value = SimpleNamespace(ok=False, status=503)

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

        class FakeKeyboard:
            def press(self, _key):
                pass

        class FakePage:
            context = object()
            url = "https://example.test/404.html"
            keyboard = FakeKeyboard()

            def locator(self, selector):
                if selector == "h1":
                    raise AssertionError("destination checks must not run")
                return FakeAction()

            def expect_navigation(self, **_kwargs):
                return FakeNavigation()

        with (
            patch.object(color_scheme_checker, "link_traversal_key", return_value="Tab"),
            patch.object(
                color_scheme_checker,
                "storage_error_name",
                side_effect=["SecurityError"],
            ),
            self.assertRaisesRegex(
                AssertionError,
                "keyboard recovery failed: 503",
            ),
        ):
            color_scheme_checker.check_utility_recovery(
                FakePage(), "https://example.test/", "/404.html", []
            )

    def test_utility_recovery_blocks_unverified_targets_and_preserves_failures(self):
        expected_url = "https://example.test/"
        secret = "synthetic-secret-token"

        class FakeAction:
            def __init__(self, scenario):
                self.scenario = scenario

            def count(self):
                if self.scenario == "action_exception":
                    raise RuntimeError(secret)
                return 1

            def is_visible(self):
                return True

            def inner_text(self):
                if self.scenario == "label_exception":
                    raise RuntimeError(secret)
                return "Wrong label" if self.scenario in ("setup_exception", "tab_exception", "navigation_exception") else "Return home"

            def evaluate(self, expression):
                if expression == "element => element.href":
                    if self.scenario == "href_exception":
                        raise RuntimeError(secret)
                    if self.scenario == "wrong_href":
                        return "https://outside.invalid/?token=" + secret
                    return expected_url
                if "href: element.href" in expression:
                    if self.scenario == "recheck_exception":
                        raise RuntimeError(secret)
                    return {
                        "href": "https://outside.invalid/?token=" + secret if self.scenario == "mutated_href" else expected_url,
                        "focused": self.scenario != "lost_focus",
                        "visible": True,
                    }
                return self.scenario != "unreachable"

        class FakeNavigation:
            value = SimpleNamespace(ok=True, status=200)

            def __init__(self, scenario):
                self.scenario = scenario

            def __enter__(self):
                if self.scenario == "navigation_exception":
                    raise RuntimeError(secret)
                return self

            def __exit__(self, *_args):
                return False

        class FakeKeyboard:
            def __init__(self, page):
                self.page = page
                self.keys = []

            def press(self, key):
                self.keys.append(key)
                if key == "Tab" and self.page.scenario == "tab_exception":
                    raise RuntimeError(secret)
                if key == "Enter":
                    self.page.url = (
                        "https://outside.invalid/?token=" + secret
                        if self.page.scenario == "wrong_final_url" else expected_url
                    )

        class FakePage:
            context = object()

            def __init__(self, scenario):
                self.scenario = scenario
                self.url = "https://example.test/404.html"
                self.action = FakeAction(scenario)
                self.keyboard = FakeKeyboard(self)
                self.heading_calls = 0

            def locator(self, selector):
                if selector == "h1":
                    self.heading_calls += 1
                    raise RuntimeError(secret)
                return self.action

            def expect_navigation(self, **_kwargs):
                return FakeNavigation(self.scenario)

        scenarios = (
            "wrong_href", "mutated_href", "lost_focus", "unreachable",
            "tab_exception", "setup_exception", "navigation_exception",
            "wrong_final_url", "href_exception", "recheck_exception", "label_exception",
            "action_exception", "storage_exception",
        )
        for scenario in scenarios:
            with self.subTest(scenario=scenario):
                page = FakePage(scenario)
                setup = RuntimeError(secret) if scenario == "setup_exception" else None
                storage = RuntimeError(secret) if scenario == "storage_exception" else None
                with (
                    patch.object(color_scheme_checker, "storage_error_name", side_effect=storage, return_value="SecurityError"),
                    patch.object(color_scheme_checker, "link_traversal_key", side_effect=setup, return_value="Tab"),
                    self.assertRaises(AssertionError) as result,
                ):
                    color_scheme_checker.check_utility_recovery(
                        page, "https://example.test/", "/404.html", []
                    )
                message = str(result.exception)
                trace = "".join(traceback.format_exception(result.exception))
                self.assertNotIn(secret, message)
                self.assertNotIn(secret, trace)
                if scenario in ("setup_exception", "tab_exception", "navigation_exception"):
                    self.assertIn("primary recovery label", message)
                if scenario in ("wrong_href", "mutated_href", "lost_focus", "unreachable", "tab_exception", "setup_exception", "href_exception", "recheck_exception", "action_exception", "storage_exception"):
                    self.assertNotIn("Enter", page.keyboard.keys)
                    self.assertIn("were not run", message)
                if scenario == "unreachable":
                    self.assertEqual(len(page.keyboard.keys), 100)
                if scenario in ("navigation_exception", "wrong_final_url"):
                    self.assertEqual(page.heading_calls, 0)
                    self.assertIn("destination checks were not run", message)

    def test_utility_recovery_does_not_swallow_keyboard_cancellation(self):
        class FakeAction:
            def count(self): return 1
            def is_visible(self): return True
            def inner_text(self): return "Return home"
            def evaluate(self, expression):
                return "https://example.test/" if expression == "element => element.href" else True

        class FakePage:
            context = object()
            def locator(self, _selector): return FakeAction()

        for interrupt in (KeyboardInterrupt, SystemExit):
            with self.subTest(interrupt=interrupt.__name__):
                page = FakePage()
                page.keyboard = SimpleNamespace(press=lambda _key: (_ for _ in ()).throw(interrupt()))
                with (
                    patch.object(color_scheme_checker, "storage_error_name", return_value="SecurityError"),
                    patch.object(color_scheme_checker, "link_traversal_key", return_value="Tab"),
                    self.assertRaises(interrupt),
                ):
                    color_scheme_checker.check_utility_recovery(
                        page, "https://example.test/", "/404.html", []
                    )

    def test_navigation_failure_does_not_run_theme_assertions(self):
        calls = {"evaluate": 0, "wait_for_load": 0}

        class FakePage:
            url = "https://example.test/broken/"

            def on(self, *_args):
                pass

            def goto(self, *_args, **_kwargs):
                return SimpleNamespace(ok=False, status=503)

            def evaluate(self, *_args):
                calls["evaluate"] += 1
                raise AssertionError("theme assertions must not run")

            def wait_for_load_state(self, *_args):
                calls["wait_for_load"] += 1

        class FakeContext:
            def new_page(self):
                return FakePage()

            def close(self):
                pass

        with patch.object(
            color_scheme_checker, "load_context", return_value=FakeContext()
        ):
            with self.assertRaisesRegex(
                AssertionError, "did not load with saved dark preference"
            ):
                color_scheme_checker._check_saved_preference_context(
                    object(), "https://example.test/", "dark", ["/broken/"]
                )

        self.assertEqual(calls, {"evaluate": 0, "wait_for_load": 0})

    def test_theme_setup_failure_does_not_run_follow_on_assertions(self):
        calls = {"wait_for_load": 0}

        class FakePage:
            url = "https://example.test/setup-error/"

            def on(self, *_args):
                pass

            def goto(self, *_args, **_kwargs):
                return SimpleNamespace(ok=True, status=200)

            def evaluate(self, *_args):
                raise RuntimeError("DOM inspection unavailable")

            def wait_for_load_state(self, *_args):
                calls["wait_for_load"] += 1

        class FakeContext:
            def new_page(self):
                return FakePage()

            def close(self):
                pass

        with patch.object(
            color_scheme_checker, "load_context", return_value=FakeContext()
        ):
            with self.assertRaisesRegex(
                RuntimeError, "could not collect theme evidence before assertions"
            ) as failure:
                color_scheme_checker._check_saved_preference_context(
                    object(), "https://example.test/", "dark", ["/setup-error/"]
                )

        self.assertIn("DOM inspection unavailable", str(failure.exception))
        self.assertEqual(calls["wait_for_load"], 0)

    def test_browser_gate_fails_when_aggregated_theme_assertions_fail(self):
        playwright_api = ModuleType("playwright.sync_api")

        class FakeBrowser:
            version = "test-browser"

            def close(self):
                pass

        class PlaywrightManager:
            def __enter__(self):
                return SimpleNamespace(
                    chromium=SimpleNamespace(launch=lambda **_kwargs: FakeBrowser())
                )

            def __exit__(self, *_args):
                return False

        playwright_api.sync_playwright = PlaywrightManager
        playwright_module = ModuleType("playwright")
        playwright_module.sync_api = playwright_api
        combined_failure = color_scheme_checker.RouteCheckFailure(
            [
                {
                    "route": "/theme-regression/",
                    "error": (
                        "/theme-regression/: 2 independent theme check(s) failed: "
                        "initial DOM scheme: expected dark, got light; "
                        "external asset: bootstrap script is missing"
                    ),
                }
            ]
        )

        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "browser-report.json"
            stdout = tempfile.TemporaryFile(mode="w+t", encoding="utf-8")
            with (
                patch.dict(
                    sys.modules,
                    {
                        "playwright": playwright_module,
                        "playwright.sync_api": playwright_api,
                    },
                ),
                patch.object(
                    sys,
                    "argv",
                    [
                        str(COLOR_SCHEME_SCRIPT),
                        "--browser",
                        "chromium",
                        "--output",
                        str(report_path),
                    ],
                ),
                patch.object(
                    color_scheme_checker,
                    "browser_routes",
                    return_value=["/theme-regression/"],
                ),
                patch.object(
                    color_scheme_checker,
                    "check_saved_preference",
                    side_effect=combined_failure,
                ),
                patch.object(sys, "stdout", stdout),
                self.assertRaises(SystemExit) as exit_result,
            ):
                color_scheme_checker.main()

            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(exit_result.exception.code, 1)
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["failure_stage"], "theme_check")
            self.assertEqual(report["error"], "One or more theme cases failed.")
            self.assertEqual(report["case_failures"]["dark"], {
                "error": "Theme case failed.", "route_details_incomplete": True,
            })
            self.assertNotIn("failed_routes", report)
            stdout.close()

    def test_first_theme_failure_keeps_running_and_reports_later_case_results(self):
        playwright_api = ModuleType("playwright.sync_api")

        class FakeBrowser:
            version = "test-browser"

            def close(self):
                pass

        class PlaywrightManager:
            def __enter__(self):
                return SimpleNamespace(
                    chromium=SimpleNamespace(launch=lambda **_kwargs: FakeBrowser())
                )

            def __exit__(self, *_args):
                return False

        playwright_api.sync_playwright = PlaywrightManager
        playwright_module = ModuleType("playwright")
        playwright_module.sync_api = playwright_api
        attempted = []

        def check_saved(_browser, _base_url, preference, _routes):
            attempted.append(preference)
            if preference == "light":
                raise AssertionError("light preference regressed")
            return {"routes": 1, "preference": preference}

        def check_blocked(_browser, _base_url, _routes):
            attempted.append("disabled_storage")
            return {"routes": 1, "storage_blocked": True}

        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "browser-report.json"
            stdout = tempfile.TemporaryFile(mode="w+t", encoding="utf-8")
            with (
                patch.dict(
                    sys.modules,
                    {
                        "playwright": playwright_module,
                        "playwright.sync_api": playwright_api,
                    },
                ),
                patch.object(
                    sys,
                    "argv",
                    [
                        str(COLOR_SCHEME_SCRIPT),
                        "--browser",
                        "chromium",
                        "--output",
                        str(report_path),
                    ],
                ),
                patch.object(
                    color_scheme_checker, "browser_routes", return_value=["/"]
                ),
                patch.object(
                    color_scheme_checker,
                    "check_saved_preference",
                    side_effect=check_saved,
                ),
                patch.object(
                    color_scheme_checker,
                    "check_disabled_storage",
                    side_effect=check_blocked,
                ),
                patch.object(sys, "stdout", stdout),
                self.assertRaises(SystemExit) as exit_result,
            ):
                color_scheme_checker.main()

            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(exit_result.exception.code, 1)
            self.assertEqual(attempted, ["light", "dark", "disabled_storage"])
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["failure_stage"], "theme_check")
            self.assertEqual(
                report["case_failures"],
                {"light": {"error": "Theme case failed."}},
            )
            self.assertEqual(
                report["cases"],
                {
                    "dark": {"routes": 1, "preference": "dark"},
                    "disabled_storage": {"routes": 1, "storage_blocked": True},
                },
            )
            self.assertEqual(report["not_run_cases"], [])
            stdout.close()

    def test_browser_close_failure_preserves_completed_theme_cases(self):
        playwright_api = ModuleType("playwright.sync_api")

        class FakeBrowser:
            version = "test-browser"

            def close(self):
                raise RuntimeError("secret-marker https://example.invalid/?token=private /private/path")

        class PlaywrightManager:
            def __enter__(self):
                return SimpleNamespace(
                    chromium=SimpleNamespace(launch=lambda **_kwargs: FakeBrowser())
                )

            def __exit__(self, *_args):
                return False

        playwright_api.sync_playwright = PlaywrightManager
        playwright_module = ModuleType("playwright")
        playwright_module.sync_api = playwright_api

        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "browser-report.json"
            stdout = tempfile.TemporaryFile(mode="w+t", encoding="utf-8")
            with (
                patch.dict(
                    sys.modules,
                    {
                        "playwright": playwright_module,
                        "playwright.sync_api": playwright_api,
                    },
                ),
                patch.object(
                    sys,
                    "argv",
                    [
                        str(COLOR_SCHEME_SCRIPT),
                        "--browser",
                        "chromium",
                        "--output",
                        str(report_path),
                    ],
                ),
                patch.object(
                    color_scheme_checker, "browser_routes", return_value=["/"]
                ),
                patch.object(
                    color_scheme_checker,
                    "check_saved_preference",
                    return_value={"routes": 1},
                ),
                patch.object(
                    color_scheme_checker,
                    "check_disabled_storage",
                    return_value={"routes": 1},
                ),
                patch.object(sys, "stdout", stdout),
                self.assertRaises(SystemExit) as exit_result,
            ):
                color_scheme_checker.main()

            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(exit_result.exception.code, 1)
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["failure_stage"], "browser_cleanup")
            self.assertNotIn("failed_case", report)
            self.assertEqual(
                tuple(report["cases"]),
                ("light", "dark", "disabled_storage"),
            )
            self.assertEqual(report["not_run_cases"], [])
            self.assertEqual(report["error"], "Browser cleanup failed.")
            self.assertNotIn("secret-marker", json.dumps(report))
            stdout.close()

    def test_cleanup_failure_diagnostic_lists_completed_cases(self):
        code = theme_failure_diagnostic_code(self.workflow)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = root / "assets" / "audit"
            audit.mkdir(parents=True)
            (audit / "color-scheme-init-firefox.json").write_text(
                json.dumps(
                    {
                        "browser": "firefox",
                        "status": "FAIL",
                        "diagnostic_only": True,
                        "failure_stage": "browser_cleanup",
                        "cases": {"light": {}, "dark": {}, "disabled_storage": {}},
                        "not_run_cases": [],
                        "error": "secret-marker https://example.invalid/?token=private",
                    }
                ),
                encoding="utf-8",
            )
            summary_path = root / "summary.md"
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=root,
                env={**os.environ, "GITHUB_STEP_SUMMARY": str(summary_path)},
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = summary_path.read_text(encoding="utf-8")
            self.assertIn("browser cleanup failed while closing the browser", summary)
            self.assertIn(
                "Completed before failure (diagnostic only; not validated "
                "evidence): `light`, `dark`, `disabled_storage`.",
                summary,
            )
            self.assertIn("Not run: none reported", summary)
            self.assertNotIn("theme check failed in", summary)
            self.assertNotIn("secret-marker", summary)

    def test_cleanup_failure_does_not_stringify_exception(self):
        playwright_api = ModuleType("playwright.sync_api")

        class CleanupError(RuntimeError):
            def __str__(self):
                raise AssertionError("cleanup exception was stringified")

        class FakeBrowser:
            version = "test-browser"

            def close(self):
                raise CleanupError()

        class PlaywrightManager:
            def __enter__(self):
                return SimpleNamespace(
                    chromium=SimpleNamespace(launch=lambda **_kwargs: FakeBrowser())
                )

            def __exit__(self, *_args):
                return False

        playwright_api.sync_playwright = PlaywrightManager
        playwright_module = ModuleType("playwright")
        playwright_module.sync_api = playwright_api
        stdout = StringIO()
        with (
            patch.dict(sys.modules, {
                "playwright": playwright_module,
                "playwright.sync_api": playwright_api,
            }),
            patch.object(sys, "argv", [str(COLOR_SCHEME_SCRIPT)]),
            patch.object(color_scheme_checker, "browser_routes", return_value=[]),
            patch.object(color_scheme_checker, "check_saved_preference", return_value={}),
            patch.object(color_scheme_checker, "check_disabled_storage", return_value={}),
            redirect_stdout(stdout),
            self.assertRaises(SystemExit) as exit_result,
        ):
            color_scheme_checker.main()
        self.assertEqual(exit_result.exception.code, 1)
        report = json.loads(stdout.getvalue())
        self.assertEqual(report["failure_stage"], "browser_cleanup")
        self.assertEqual(report["error"], "Browser cleanup failed.")

    def test_theme_failure_remains_primary_when_browser_cleanup_also_fails(self):
        playwright_api = ModuleType("playwright.sync_api")

        class FakeBrowser:
            version = "test-browser"

            def close(self):
                raise RuntimeError("browser close failed")

        class PlaywrightManager:
            def __enter__(self):
                return SimpleNamespace(
                    chromium=SimpleNamespace(launch=lambda **_kwargs: FakeBrowser())
                )

            def __exit__(self, *_args):
                return False

        playwright_api.sync_playwright = PlaywrightManager
        playwright_module = ModuleType("playwright")
        playwright_module.sync_api = playwright_api
        theme_failure = AssertionError("dark preference failed")

        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "browser-report.json"
            stdout = tempfile.TemporaryFile(mode="w+t", encoding="utf-8")
            with (
                patch.dict(
                    sys.modules,
                    {
                        "playwright": playwright_module,
                        "playwright.sync_api": playwright_api,
                    },
                ),
                patch.object(
                    sys,
                    "argv",
                    [
                        str(COLOR_SCHEME_SCRIPT),
                        "--browser",
                        "chromium",
                        "--output",
                        str(report_path),
                    ],
                ),
                patch.object(color_scheme_checker, "browser_routes", return_value=[]),
                patch.object(
                    color_scheme_checker,
                    "check_saved_preference",
                    side_effect=[{"routes": 1}, theme_failure],
                ),
                patch.object(
                    color_scheme_checker,
                    "check_disabled_storage",
                    return_value={"routes": 1},
                ),
                patch.object(sys, "stdout", stdout),
                self.assertRaises(SystemExit),
            ):
                color_scheme_checker.main()

            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["failure_stage"], "theme_check")
            self.assertEqual(report["failed_case"], "dark")
            self.assertEqual(report["error"], "One or more theme cases failed.")
            self.assertIs(report["cleanup_failed"], True)
            self.assertNotIn("browser close failed", json.dumps(report))
            self.assertEqual(report["not_run_cases"], [])
            self.assertIn("disabled_storage", report["cases"])
            stdout.close()

    def test_unclassified_execution_failure_remains_primary_when_close_fails(self):
        playwright_api = ModuleType("playwright.sync_api")

        class FakeBrowser:
            version = "test-browser"

            def close(self):
                raise RuntimeError("cleanup-secret-marker")

        class PlaywrightManager:
            def __enter__(self):
                return SimpleNamespace(
                    chromium=SimpleNamespace(launch=lambda **_kwargs: FakeBrowser())
                )

            def __exit__(self, *_args):
                return False

        playwright_api.sync_playwright = PlaywrightManager
        playwright_module = ModuleType("playwright")
        playwright_module.sync_api = playwright_api
        real_capture_case = color_scheme_checker.capture_case

        for malformed_cases in (False, True):
            with self.subTest(malformed_cases=malformed_cases):
                def fail_outside_case_handler(report, *_args, **_kwargs):
                    if malformed_cases:
                        report["cases"] = None
                        return real_capture_case(report, "light", lambda: {"routes": 1})
                    raise ValueError("primary execution failure")

                stdout = StringIO()
                with (
                    patch.dict(sys.modules, {
                        "playwright": playwright_module,
                        "playwright.sync_api": playwright_api,
                    }),
                    patch.object(sys, "argv", [str(COLOR_SCHEME_SCRIPT)]),
                    patch.object(color_scheme_checker, "browser_routes", return_value=[]),
                    patch.object(color_scheme_checker, "capture_case", side_effect=fail_outside_case_handler),
                    redirect_stdout(stdout),
                    self.assertRaises(SystemExit) as exit_result,
                ):
                    color_scheme_checker.main()
                report = json.loads(stdout.getvalue())
                self.assertEqual(exit_result.exception.code, 1)
                self.assertEqual(report["failure_stage"], "theme_checks")
                self.assertEqual(report["error"], "Theme case execution could not be completed.")
                self.assertIs(report["cleanup_failed"], True)
                self.assertNotIn("cleanup-secret-marker", stdout.getvalue())
                if malformed_cases:
                    self.assertIsNone(report["cases"])
                    self.assertNotIn("not_run_cases", report)

    def test_cleanup_interrupt_during_execution_failure_is_not_suppressed(self):
        playwright_api = ModuleType("playwright.sync_api")

        class FakeBrowser:
            version = "test-browser"

            def close(self):
                pass

        class PlaywrightManager:
            def __enter__(self):
                return SimpleNamespace(
                    chromium=SimpleNamespace(launch=lambda **_kwargs: FakeBrowser())
                )

            def __exit__(self, *_args):
                return False

        playwright_api.sync_playwright = PlaywrightManager
        playwright_module = ModuleType("playwright")
        playwright_module.sync_api = playwright_api
        for interrupt in (KeyboardInterrupt, SystemExit):
            with (
                self.subTest(interrupt=interrupt.__name__),
                patch.dict(sys.modules, {
                    "playwright": playwright_module,
                    "playwright.sync_api": playwright_api,
                }),
                patch.object(sys, "argv", [str(COLOR_SCHEME_SCRIPT)]),
                patch.object(color_scheme_checker, "browser_routes", return_value=[]),
                patch.object(color_scheme_checker, "capture_case", side_effect=ValueError("primary")),
                patch.object(FakeBrowser, "close", side_effect=interrupt),
                redirect_stdout(StringIO()),
                self.assertRaises(interrupt),
            ):
                color_scheme_checker.main()

    def test_cleanup_conflicting_reports_do_not_claim_case_sequence(self):
        code = theme_failure_diagnostic_code(self.workflow)
        valid_cases = {"light": {}, "dark": {}, "disabled_storage": {}}
        conflicts = (
            {"failed_case": "dark"},
            {"failed_case": ["dark"]},
            {"cases": {"light": {}, "dark": {}}},
            {"cases": None},
            {"cases": {**valid_cases, "other": {}}},
            {"not_run_cases": ["disabled_storage"]},
            {"not_run_cases": "dark"},
            {"failed_routes": [{"route": "/private-route"}]},
            {"failed_routes": "malformed"},
        )
        for conflict in conflicts:
            with self.subTest(conflict=conflict), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                audit = root / "assets" / "audit"
                audit.mkdir(parents=True)
                report = {
                    "browser": "firefox", "status": "FAIL",
                    "diagnostic_only": True, "failure_stage": "browser_cleanup",
                    "cases": valid_cases, "not_run_cases": [],
                    "error": "cleanup-secret-marker",
                    "cleanup_error": "secondary-secret-marker",
                    **conflict,
                }
                (audit / "color-scheme-init-firefox.json").write_text(
                    json.dumps(report), encoding="utf-8"
                )
                summary_path = root / "summary.md"
                result = subprocess.run(
                    [sys.executable, "-c", code], cwd=root,
                    env={**os.environ, "GITHUB_STEP_SUMMARY": str(summary_path)},
                    capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                summary = summary_path.read_text(encoding="utf-8")
                self.assertIn("Case sequence cannot be established", summary)
                self.assertNotIn("Completed before failure", summary)
                self.assertNotIn("Not run:", summary)
                self.assertNotIn("Affected pages", summary)
                self.assertNotIn("theme check failed in", summary)
                self.assertNotIn("secret-marker", summary)

    def test_secondary_cleanup_preserves_theme_failure_and_hides_raw_detail(self):
        code = theme_failure_diagnostic_code(self.workflow)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = root / "assets" / "audit"
            audit.mkdir(parents=True)
            report_path = audit / "color-scheme-init-firefox.json"
            for index, cases in enumerate(({"light": {}}, None)):
                summary_path = root / f"summary-{index}.md"
                report_path.write_text(json.dumps({
                    "browser": "firefox", "status": "FAIL", "diagnostic_only": True,
                    "failure_stage": "theme_check", "failed_case": "dark",
                    "cases": cases, "not_run_cases": ["disabled_storage"],
                    "error": "dark preference failed", "cleanup_failed": True,
                    "cleanup_error": "secondary-secret-marker",
                }), encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, "-c", code], cwd=root,
                    env={**os.environ, "GITHUB_STEP_SUMMARY": str(summary_path)},
                    capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                summary = summary_path.read_text(encoding="utf-8")
                self.assertIn("theme check failed in `dark`", summary)
                self.assertIn("dark preference failed", summary)
                self.assertIn("Browser cleanup also failed", summary)
                self.assertNotIn("secondary-secret-marker", summary)
                if cases is None:
                    self.assertIn("Case sequence cannot be established", summary)
                    self.assertNotIn("Completed before failure", summary)
                    self.assertNotIn("Not run:", summary)
                else:
                    self.assertIn("Completed before failure", summary)
                    self.assertIn("Not run: `disabled_storage`", summary)

    def test_failure_diagnostic_names_engine_case_and_is_not_release_evidence(self):
        code = theme_failure_diagnostic_code(self.workflow)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = root / "assets" / "audit"
            audit.mkdir(parents=True)
            (audit / "color-scheme-init-chromium.json").write_text(
                json.dumps(
                    {
                        "browser": "chromium",
                        "status": "FAIL",
                        "diagnostic_only": True,
                        "failure_stage": "browser_startup",
                        "setup_step": "launching_browser",
                        "not_run_cases": [
                            "light",
                            "dark",
                            "disabled_storage",
                        ],
                        "error": "browser could not be launched",
                    }
                ),
                encoding="utf-8",
            )
            (audit / "color-scheme-init-firefox.json").write_text(
                json.dumps(
                    {
                        "browser": "firefox",
                        "browser_version": "138.0",
                        "status": "FAIL",
                        "diagnostic_only": True,
                        "failure_stage": "theme_check",
                        "failed_case": "dark",
                        "cases": {"light": {"routes": 1}},
                        "failed_routes": [
                            {
                                "route": "/toolbox/example/",
                                "error": "saved dark preference was not applied",
                            },
                            {
                                "route": "/branch/another/",
                                "error": "wrong initial scheme",
                            },
                        ],
                        "not_run_cases": ["disabled_storage"],
                        "error": "saved dark preference was not applied",
                    }
                ),
                encoding="utf-8",
            )
            summary_path = root / "step-summary.md"
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=root,
                env={**os.environ, "GITHUB_STEP_SUMMARY": str(summary_path)},
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = summary_path.read_text(encoding="utf-8")
            self.assertIn(
                "browser startup/setup failed before theme checks began",
                summary,
            )
            self.assertIn(
                "Setup phase attempted (diagnostic only; not validated evidence): "
                "`launching the browser engine`.",
                summary,
            )
            self.assertIn(
                "Not run: `light`, `dark`, `disabled_storage`",
                summary,
            )
            self.assertIn("Firefox (138.0)", summary)
            self.assertIn("theme check failed in `dark`", summary)
            setup_step_lines = [
                line for line in summary.splitlines()
                if "Setup phase attempted" in line
            ]
            self.assertEqual(len(setup_step_lines), 1)
            self.assertIn(
                "Completed before failure (diagnostic only; not validated "
                "evidence): `light`.",
                summary,
            )
            self.assertNotIn("Report is inconsistent", summary)
            self.assertIn("Not run: `disabled_storage`", summary)
            self.assertIn("saved dark preference was not applied", summary)
            self.assertIn(
                "Affected pages (diagnostic only; not validated release evidence)",
                summary,
            )
            self.assertIn("`/toolbox/example/`", summary)
            self.assertIn("`/branch/another/`", summary)
            self.assertIn("Diagnostic only", summary)
            self.assertIn("not validated release evidence", summary)
            not_run_line = next(
                line for line in summary.splitlines() if "Not run:" in line
            )
            self.assertIn(
                "must not be treated as passing or validated evidence",
                not_run_line,
            )
            self.assertNotIn("Generated from the successful browser theme checks", summary)

    def test_failure_diagnostic_omits_unrecognized_or_irrelevant_setup_phase(self):
        code = theme_failure_diagnostic_code(self.workflow)
        reports = (
            {"failure_stage": "browser_startup"},
            {"failure_stage": "browser_startup", "setup_step": "unknown"},
            {"failure_stage": "browser_startup", "setup_step": ["launching_browser"]},
            {"failure_stage": "theme_checks", "setup_step": "launching_browser"},
        )
        for extra in reports:
            with self.subTest(report=extra), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                audit = root / "assets" / "audit"
                audit.mkdir(parents=True)
                report = {"browser": "firefox", "status": "FAIL", "cases": {}, **extra}
                (audit / "color-scheme-init-firefox.json").write_text(
                    json.dumps(report), encoding="utf-8",
                )
                summary_path = root / "summary.md"
                result = subprocess.run(
                    [sys.executable, "-c", code], cwd=root,
                    env={**os.environ, "GITHUB_STEP_SUMMARY": str(summary_path)},
                    capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                summary = summary_path.read_text(encoding="utf-8")
                self.assertNotIn("Setup phase attempted", summary)
                self.assertNotIn("unknown", summary)

    def test_failure_diagnostic_keeps_conflicting_startup_case_unverified(self):
        code = theme_failure_diagnostic_code(self.workflow)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = root / "assets" / "audit"
            audit.mkdir(parents=True)
            report = {
                "browser": "firefox", "status": "FAIL", "diagnostic_only": True,
                "failure_stage": "browser_startup", "setup_step": "launching_browser",
                "failed_case": "dark", "cases": {"light": {}, "disabled_storage": {}},
                "not_run_cases": ["dark", "disabled_storage"],
            }
            (audit / "color-scheme-init-firefox.json").write_text(
                json.dumps(report), encoding="utf-8",
            )
            summary_path = root / "summary.md"
            result = subprocess.run(
                [sys.executable, "-c", code], cwd=root,
                env={**os.environ, "GITHUB_STEP_SUMMARY": str(summary_path)},
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = summary_path.read_text(encoding="utf-8")
            self.assertIn("browser startup failure and a named theme case are both reported; neither is verified", summary)
            self.assertIn("Setup phase attempted (diagnostic only; not validated evidence)", summary)
            self.assertIn("actual failed case remains unverified", summary)
            self.assertIn("Case sequence cannot be established from the conflicting report", summary)
            self.assertNotIn("theme check failed in `dark`", summary)
            self.assertNotIn("It is treated as failed", summary)
            self.assertNotIn("Completed before failure", summary)
            self.assertNotIn("after failed case", summary)
            self.assertNotIn("Not run:", summary)

    def test_failure_diagnostic_flags_cases_listed_after_failure(self):
        code = theme_failure_diagnostic_code(self.workflow)
        reports = (
            (
                "consistent partial report",
                {
                    "browser": "firefox", "status": "FAIL",
                    "diagnostic_only": True, "failed_case": "dark",
                    "cases": {"light": {}},
                    "not_run_cases": ["disabled_storage"],
                },
                False,
            ),
            (
                "later case listed after failure",
                {
                    "browser": "firefox", "status": "FAIL",
                    "diagnostic_only": True, "failed_case": "dark",
                    "cases": {"light": {}, "disabled_storage": {}},
                    "not_run_cases": ["disabled_storage"],
                },
                True,
            ),
            (
                "failed case also listed as not run",
                {
                    "browser": "firefox", "status": "FAIL",
                    "diagnostic_only": True, "failed_case": "dark",
                    "cases": {"light": {}},
                    "not_run_cases": ["dark", "disabled_storage"],
                },
                True,
            ),
        )
        for label, report, inconsistent in reports:
            with self.subTest(report=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                audit = root / "assets" / "audit"
                audit.mkdir(parents=True)
                (audit / "color-scheme-init-firefox.json").write_text(
                    json.dumps(report), encoding="utf-8",
                )
                summary_path = root / "summary.md"
                result = subprocess.run(
                    [sys.executable, "-c", code], cwd=root,
                    env={**os.environ, "GITHUB_STEP_SUMMARY": str(summary_path)},
                    capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                summary = summary_path.read_text(encoding="utf-8")
                completed = next(line for line in summary.splitlines()
                                 if "Completed before failure" in line)
                self.assertTrue(completed.endswith(": `light`."), completed)
                self.assertNotIn("disabled_storage", completed)
                self.assertIn("Not run: `disabled_storage`", summary)
                self.assertEqual("Report is inconsistent" in summary, inconsistent)
                if label == "later case listed after failure":
                    self.assertIn(
                        "lists `disabled_storage` after failed case `dark`",
                        summary,
                    )
                    self.assertIn(
                        "must not be treated as completed, passed, or validated evidence",
                        summary,
                    )
                if label == "failed case also listed as not run":
                    self.assertIn(
                        "the failed case `dark` is also listed in `not_run_cases`",
                        summary,
                    )
                    self.assertIn(
                        "It is treated as failed, not completed, passed, or "
                        "validated evidence.",
                        summary,
                    )
                    completed = next(
                        line for line in summary.splitlines()
                        if "Completed before failure" in line
                    )
                    self.assertNotIn("`dark`", completed)

    def test_failure_diagnostic_does_not_name_an_unknown_case(self):
        code = theme_failure_diagnostic_code(self.workflow)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = root / "assets" / "audit"
            audit.mkdir(parents=True)
            report = {
                "browser": "firefox", "status": "FAIL", "diagnostic_only": True,
                "failed_case": "unknown-case", "cases": {"light": {}},
                "not_run_cases": ["unknown-case", "dark"],
            }
            (audit / "color-scheme-init-firefox.json").write_text(
                json.dumps(report), encoding="utf-8",
            )
            summary_path = root / "summary.md"
            result = subprocess.run(
                [sys.executable, "-c", code], cwd=root,
                env={**os.environ, "GITHUB_STEP_SUMMARY": str(summary_path)},
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = summary_path.read_text(encoding="utf-8")
            self.assertIn("an unrecognized failure label also appears in `not_run_cases`", summary)
            self.assertIn("the actual failed case remains unverified", summary)
            self.assertNotIn("the failed case `not identified`", summary)
            self.assertNotIn("unknown-case", summary)

    def test_failure_diagnostic_marks_unsupported_case_results_as_malformed(self):
        code = theme_failure_diagnostic_code(self.workflow)
        reports = (
            (
                "valid case object",
                "FAIL",
                {"light": {}},
                "`light`.",
            ),
            ("null cases", "FAIL", None, "none."),
            ("list cases", "FAIL", ["light"], "none."),
            ("string cases", "FAIL", "light", "none."),
            ("numeric cases", "FAIL", 3, "none."),
            ("boolean cases", "FAIL", False, "none."),
            ("absent cases", "FAIL", None, "none."),
            ("malformed cases with PASS status", "PASS", ["light"], None),
            ("boolean cases with PASS status", "PASS", True, None),
        )
        for label, status, case_results, expected_completed in reports:
            with self.subTest(report=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                audit = root / "assets" / "audit"
                audit.mkdir(parents=True)
                report = {
                    "browser": "firefox",
                    "status": status,
                    "diagnostic_only": True,
                    "failed_case": "dark",
                    "cases": case_results,
                }
                if label == "absent cases":
                    del report["cases"]
                (audit / "color-scheme-init-firefox.json").write_text(
                    json.dumps(report), encoding="utf-8",
                )
                summary_path = root / "summary.md"
                result = subprocess.run(
                    [sys.executable, "-c", code], cwd=root,
                    env={**os.environ, "GITHUB_STEP_SUMMARY": str(summary_path)},
                    capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                summary = summary_path.read_text(encoding="utf-8")
                if label == "valid case object":
                    completed = next(
                        line for line in summary.splitlines()
                        if "Completed before failure" in line
                    )
                    self.assertTrue(completed.endswith(expected_completed), completed)
                    self.assertNotIn("case results are malformed", summary)
                else:
                    self.assertIn("case results are malformed", summary)
                    self.assertIn(
                        "no cases are treated as completed, passed, or validated evidence",
                        summary,
                    )
                    if status == "FAIL":
                        completed = next(
                            line for line in summary.splitlines()
                            if "Completed before failure" in line
                        )
                        self.assertTrue(completed.endswith(expected_completed), completed)
                    else:
                        self.assertNotIn("completed cases (diagnostic only", summary)
                        self.assertIn(
                            "PASS status cannot establish completed cases",
                            summary,
                        )

    def test_failed_route_details_cannot_become_validated_theme_evidence(self):
        diagnostic_code = theme_failure_diagnostic_code(self.workflow)
        verify_block = self.workflow.split(THEME_VERIFY_STEP, 1)[1].split(
            "\n      - name:", 1
        )[0]
        verify_code = textwrap.dedent(
            verify_block.split("python3 - <<'PY'\n", 1)[1].rsplit(
                "          PY", 1
            )[0]
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = root / "assets" / "audit"
            audit.mkdir(parents=True)
            for browser, _, version in browser_versions():
                report = {
                    "browser": browser,
                    "browser_version": version,
                    "status": "FAIL" if browser == "firefox" else "PASS",
                    "cases": {
                        "light": {},
                        "dark": {},
                        "disabled_storage": {},
                    },
                }
                if browser == "firefox":
                    report.update(
                        {
                            "diagnostic_only": True,
                            "failed_case": "dark",
                            "failed_routes": [
                                {
                                    "route": "/private-detail/",
                                    "error": "wrong scheme",
                                }
                            ],
                        }
                    )
                (audit / f"color-scheme-init-{browser}.json").write_text(
                    json.dumps(report), encoding="utf-8"
                )

            summary_path = root / "step-summary.md"
            diagnostic = subprocess.run(
                [sys.executable, "-c", diagnostic_code],
                cwd=root,
                env={**os.environ, "GITHUB_STEP_SUMMARY": str(summary_path)},
                capture_output=True,
                text=True,
            )
            self.assertEqual(diagnostic.returncode, 0, diagnostic.stderr)
            summary = summary_path.read_text(encoding="utf-8")
            self.assertIn("`/private-detail/`", summary)
            self.assertIn("diagnostic only; not validated release evidence", summary)

            verification = subprocess.run(
                [sys.executable, "-c", verify_code],
                cwd=root,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(verification.returncode, 0)
            self.assertIn("status='FAIL', expected 'PASS'", verification.stderr)
            self.assertFalse((audit / THEME_INDEX_NAME).exists())

    def test_failure_diagnostic_handles_unavailable_and_malformed_reports(self):
        code = theme_failure_diagnostic_code(self.workflow)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = root / "assets" / "audit"
            audit.mkdir(parents=True)
            (audit / "color-scheme-init-firefox.json").write_text(
                "{broken JSON", encoding="utf-8"
            )
            (audit / "color-scheme-init-webkit.json").write_text(
                "[]", encoding="utf-8"
            )
            summary_path = root / "step-summary.md"
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=root,
                env={**os.environ, "GITHUB_STEP_SUMMARY": str(summary_path)},
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = summary_path.read_text(encoding="utf-8")
            self.assertIn("Chromium", summary)
            self.assertIn("failure report unavailable", summary)
            self.assertIn("Firefox", summary)
            self.assertIn("malformed or unreadable", summary)
            self.assertIn("WebKit", summary)
            self.assertIn("JSON root must be an object", summary)
            self.assertIn("not validated release evidence", summary)

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

    def run_retention_check(self, artifact, workflow_run=None):
        workflow_run = workflow_run if workflow_run is not None else {
            "id": 987,
            "head_sha": "a" * 40,
            "created_at": "2026-01-01T00:00:00Z",
        }
        artifact = dict(artifact)
        artifact.setdefault("workflow_run", {"id": 987, "head_sha": "a" * 40})
        with tempfile.TemporaryDirectory() as directory:
            run_path = Path(directory) / "workflow-run.json"
            run_path.write_text(json.dumps(workflow_run), encoding="utf-8")
            return subprocess.run(
                [
                    sys.executable,
                    str(RETENTION_CHECKER),
                    "--artifact-id", "123",
                    "--artifact-name", "pages-validation-abc123",
                    "--run-metadata", str(run_path),
                    "--run-id", "987",
                    "--commit", "a" * 40,
                ],
                input=json.dumps(artifact),
                capture_output=True,
                text=True,
            )

    def test_artifact_retention_checker_accepts_the_approved_period(self):
        artifact = {
            "id": 123,
            "name": "pages-validation-abc123",
            "expired": False,
            "created_at": "2026-01-01T00:00:00Z",
            "expires_at": "2026-04-01T00:00:00Z",
        }
        result = self.run_retention_check(artifact)
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
                result = self.run_retention_check(artifact)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_error, result.stderr)

    def test_delayed_upload_and_rerun_use_the_original_run_retention_clock(self):
        # GitHub caps expiry at run creation + retention, not artifact upload time.
        for created_at in ("2026-01-01T00:10:55Z", "2026-01-11T00:00:00Z"):
            with self.subTest(created_at=created_at):
                artifact = {
                    "id": 123, "name": "pages-validation-abc123", "expired": False,
                    "created_at": created_at, "expires_at": "2026-04-01T00:00:00Z",
                }
                run = {
                    "id": 987, "head_sha": "a" * 40,
                    "created_at": "2026-01-01T00:00:00Z",
                    "run_started_at": created_at,
                }
                result = self.run_retention_check(artifact, run)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_retention_clock_rejects_short_period_and_unbound_or_invalid_metadata(self):
        artifact = {
            "id": 123, "name": "pages-validation-abc123", "expired": False,
            "created_at": "2026-01-01T00:10:55Z",
            "expires_at": "2026-04-01T00:00:00Z",
            "workflow_run": {"id": 987, "head_sha": "a" * 40},
        }
        run = {"id": 987, "head_sha": "a" * 40, "created_at": "2026-01-01T00:00:00Z"}
        cases = (
            ({"expires_at": "2026-03-31T23:59:59Z"}, {}, "shorter than the approved 90 days"),
            ({"workflow_run": None}, {}, "workflow_run"),
            ({"workflow_run": {"id": 986, "head_sha": "a" * 40}}, {}, "run id"),
            ({"workflow_run": {"id": 987, "head_sha": "b" * 40}}, {}, "commit"),
            ({}, {"id": 986}, "run id"),
            ({}, {"head_sha": "b" * 40}, "commit"),
            ({}, {"created_at": None}, "created_at"),
            ({}, {"created_at": "2026-01-01T00:00:00"}, "timezone"),
            ({"created_at": "2025-12-31T23:59:59Z"}, {}, "before its workflow run"),
            ({"created_at": "2026-04-01T00:00:00Z"}, {}, "before its expiration"),
        )
        for artifact_patch, run_patch, expected_error in cases:
            with self.subTest(expected_error=expected_error):
                result = self.run_retention_check(
                    {**artifact, **artifact_patch}, {**run, **run_patch}
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_error, result.stderr)

    def test_retention_checker_rejects_non_object_run_metadata(self):
        artifact = {
            "id": 123, "name": "pages-validation-abc123", "expired": False,
            "created_at": "2026-01-01T00:10:55Z",
            "expires_at": "2026-04-01T00:00:00Z",
        }
        for run in ([], "not a workflow run"):
            with self.subTest(run=run):
                result = self.run_retention_check(artifact, run)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("workflow run response must be a JSON object", result.stderr)

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
            (audit / "browser-acceptance.json").write_text(
                '{"failures": 1}', encoding="utf-8"
            )
            docs = root / "assets" / "docs"
            docs.mkdir(parents=True)
            (docs / "audit-report.md").write_text(
                "# Audit report\n", encoding="utf-8"
            )
            artifact = root / "validation-artifact"
            responsive = root / "current-responsive.json"
            responsive.write_text('{"current": true}', encoding="utf-8")
            visitor = root / "current-visitor.json"
            visitor.write_text('{"failures": 0}', encoding="utf-8")
            env = {
                **os.environ,
                "VALIDATION_ARTIFACT_DIR": str(artifact),
                "VALIDATION_REPORT_NAME": "validation-report-2026-10-02.json",
                "RESPONSIVE_SUCCESS_REPORT": str(responsive),
                "VISITOR_SUCCESS_REPORT": str(visitor),
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
            self.assertEqual((staged_audit / "viewport-qa-full-current-run.json").read_text(encoding="utf-8"), '{"current": true}')
            self.assertEqual(responsive.read_text(encoding="utf-8"), '{"current": true}')
            self.assertFalse((staged_audit / "browser-acceptance.json").exists())
            self.assertEqual((staged_audit / "browser-acceptance-current-run.json").read_text(encoding="utf-8"), '{"failures": 0}')
            self.assertEqual((audit / "browser-acceptance.json").read_text(encoding="utf-8"), '{"failures": 1}')
            staged_summary = (
                artifact / "assets" / "docs" / "audit-report.md"
            ).read_text(encoding="utf-8")
            self.assertIn(audit_report_index_link(), staged_summary)

    def test_staging_rejects_missing_or_colliding_current_responsive_report(self):
        block = self.workflow.split(STAGING_STEP, 1)[1].split(UPLOAD_STEP, 1)[0]
        code = textwrap.dedent(block.split("python3 - <<'PY'\n", 1)[1].rsplit("          PY", 1)[0])
        for collision in (False, True):
            with self.subTest(collision=collision), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                audit = root / "assets" / "audit"
                audit.mkdir(parents=True)
                source = root / "success.json"
                if collision:
                    source.write_text("{}", encoding="utf-8")
                    (audit / "viewport-qa-full-current-run.json").write_text("historical", encoding="utf-8")
                env = {**os.environ, "VALIDATION_ARTIFACT_DIR": str(root / "artifact"),
                       "VALIDATION_REPORT_NAME": "report.json", "RESPONSIVE_SUCCESS_REPORT": str(source)}
                result = subprocess.run([sys.executable, "-c", code], cwd=root, env=env,
                                        capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Current responsive QA report unavailable", result.stderr)
                if collision:
                    self.assertEqual((audit / "viewport-qa-full-current-run.json").read_text(), "historical")

    def test_staging_rejects_missing_or_colliding_current_visitor_report(self):
        block = self.workflow.split(STAGING_STEP, 1)[1].split(UPLOAD_STEP, 1)[0]
        code = textwrap.dedent(block.split("python3 - <<'PY'\n", 1)[1].rsplit("          PY", 1)[0])
        for collision in (False, True):
            with self.subTest(collision=collision), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                audit = root / "assets" / "audit"
                audit.mkdir(parents=True)
                responsive = root / "responsive.json"
                responsive.write_text("{}", encoding="utf-8")
                source = root / "visitor.json"
                if collision:
                    source.write_text("{}", encoding="utf-8")
                    (audit / "browser-acceptance-current-run.json").write_text("historical", encoding="utf-8")
                env = {**os.environ, "VALIDATION_ARTIFACT_DIR": str(root / "artifact"),
                       "VALIDATION_REPORT_NAME": "report.json", "RESPONSIVE_SUCCESS_REPORT": str(responsive),
                       "VISITOR_SUCCESS_REPORT": str(source)}
                result = subprocess.run([sys.executable, "-c", code], cwd=root, env=env,
                                        capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Current visitor acceptance report unavailable", result.stderr)
                if collision:
                    self.assertEqual((audit / "browser-acceptance-current-run.json").read_text(), "historical")

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

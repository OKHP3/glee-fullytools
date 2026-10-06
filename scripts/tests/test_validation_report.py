#!/usr/bin/env python3
"""Regression tests for idempotent site-validation evidence."""
from __future__ import annotations

import importlib.util
import json
import argparse
from contextlib import ExitStack
from datetime import date, datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest import mock


_SCRIPT = Path(__file__).resolve().parent.parent / "validate-site.py"
_SPEC = importlib.util.spec_from_file_location("_validate_site", _SCRIPT)
validate_site = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(validate_site)


class ValidationReportTests(unittest.TestCase):
    def test_all_global_checks_preserve_details_counts_and_exit_status(self):
        # Scalar checks report one finding; list checks must retain every item.
        checks = {
            "_check_organization_identity_approval": ("Organization identity approval", False, []),
            "_check_css_lines_drift": ("CSS-lines drift", False, None),
            "_check_stat_markers_drift": ("STAT marker drift", False, []),
            "_check_adr_index_sync": ("ADR index drift", True, None),
            "_check_scripts_py_drift": ("scripts/ count drift", False, None),
            "_check_scripts_non_py_drift": ("scripts/ non-Python count drift", False, None),
            "_check_og_image_alt_drift": ("og:image:alt drift", False, []),
            "_check_sparkle_drift": ("Sparkle drift", False, []),
            "_check_glee_dark_coverage": ("Glee dark-mode coverage", False, []),
            "_check_css_token_drift": ("CSS token drift", False, []),
            "_check_template_metadata": ("Template metadata", False, []),
            "_check_offline_shell": ("Offline shell", False, []),
            "_check_mermaid_version_pin": ("Mermaid VERSION pin", False, []),
            "_check_mermaid_csp_alignment": ("Mermaid/CSP alignment", True, []),
        }
        for scenario in ("clean", "warnings", "all"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "assets").mkdir()
                expected_issues = []
                expected_warnings = []
                identity_issues = []
                with ExitStack() as stack:
                    stack.enter_context(mock.patch.object(validate_site, "ROOT", root))
                    stack.enter_context(
                        mock.patch.object(validate_site, "collect_html_files", return_value=[])
                    )
                    stack.enter_context(mock.patch("builtins.print"))
                    for name, (prefix, warning, clean) in checks.items():
                        value = clean
                        if scenario == "all" or (scenario == "warnings" and warning):
                            messages = ["first finding", "second finding"] if clean == [] else ["finding"]
                            value = messages if clean == [] else messages[0]
                            expected = expected_warnings if warning else expected_issues
                            expected.extend(f"{prefix}: {msg}" for msg in messages)
                        if name == "_check_organization_identity_approval":
                            identity_issues = value
                        stack.enter_context(
                            mock.patch.object(validate_site, name, return_value=value)
                        )
                    self.assertEqual(validate_site.main(), int(bool(expected_issues)))

                report_path = next((root / "assets" / "audit").glob("validation-report-*.json"))
                report = json.loads(report_path.read_text(encoding="utf-8"))
                self.assertEqual(report["global_issues"], expected_issues)
                self.assertEqual(report["global_warnings"], expected_warnings)
                self.assertEqual(report["total_issues"], len(expected_issues))
                self.assertEqual(report["total_warnings"], len(expected_warnings))
                # This compatibility field mirrors issues, not additional findings.
                self.assertEqual(report["organization_identity_issues"], identity_issues)
                self.assertEqual(report["pages"], [])

    def test_commit_sha_is_normalized_and_rejects_ambiguous_values(self):
        commit = "ABCDEF0123456789ABCDEF0123456789ABCDEF01"
        self.assertEqual(
            validate_site._validated_commit(commit),
            commit.lower(),
        )
        with self.assertRaises(argparse.ArgumentTypeError):
            validate_site._validated_commit("abcdef0")

    def test_final_totals_match_serialized_page_and_global_details(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "assets").mkdir()
            page_path = root / "index.html"
            page_path.write_text("<!doctype html>", encoding="utf-8")
            clean_checks = {
                "_check_organization_identity_approval": [],
                "_check_stat_markers_drift": [],
                "_check_scripts_py_drift": None,
                "_check_scripts_non_py_drift": None,
                "_check_og_image_alt_drift": [],
                "_check_sparkle_drift": [],
                "_check_glee_dark_coverage": [],
                "_check_css_token_drift": [],
                "_check_template_metadata": [],
                "_check_offline_shell": [],
                "_check_mermaid_version_pin": [],
                "_check_mermaid_csp_alignment": [],
            }
            patches = [
                mock.patch.object(validate_site, "ROOT", root),
                mock.patch.object(
                    validate_site, "collect_html_files", return_value=[page_path]
                ),
                mock.patch.object(
                    validate_site,
                    "check_page",
                    return_value={
                        "issues": ["fixture page issue"],
                        "warnings": ["fixture page warning"],
                    },
                ),
                mock.patch.object(
                    validate_site,
                    "_check_css_lines_drift",
                    return_value="fixture global failure",
                ),
                mock.patch.object(
                    validate_site,
                    "_check_adr_index_sync",
                    return_value="fixture global warning",
                ),
            ]
            patches.extend(
                mock.patch.object(validate_site, name, return_value=value)
                for name, value in clean_checks.items()
            )

            with ExitStack() as stack:
                for patch in patches:
                    stack.enter_context(patch)
                self.assertEqual(
                    validate_site.main(
                        validated_commit="abcdef0123456789abcdef0123456789abcdef01"
                    ),
                    1,
                )

            report_path = next((root / "assets" / "audit").glob("validation-report-*.json"))
            report = json.loads(report_path.read_text(encoding="utf-8"))
            serialized_issue_count = sum(
                len(page["issues"]) for page in report["pages"]
            ) + len(report["global_issues"])
            serialized_warning_count = sum(
                len(page["warnings"]) for page in report["pages"]
            ) + len(report["global_warnings"])
            self.assertEqual(report["total_issues"], serialized_issue_count)
            self.assertEqual(report["total_warnings"], serialized_warning_count)
            self.assertEqual(report["total_issues"], 2)
            self.assertEqual(report["total_warnings"], 2)
            self.assertEqual(
                report["global_issues"],
                ["CSS-lines drift: fixture global failure"],
            )
            self.assertEqual(
                report["global_warnings"],
                ["ADR index drift: fixture global warning"],
            )
            self.assertEqual(
                report["provenance"]["validated_commit"],
                "abcdef0123456789abcdef0123456789abcdef01",
            )

    def test_main_preserves_unchanged_evidence_and_refreshes_global_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "assets").mkdir()
            page_path = root / "index.html"
            page_html = "<!doctype html>"
            page_path.write_text(page_html, encoding="utf-8")
            run_date = date(2026, 9, 10)
            run_times = [
                datetime(2026, 9, 10, 17, minute, tzinfo=timezone.utc)
                for minute in (0, 5, 10)
            ]
            clean_checks = {
                "_check_organization_identity_approval": [],
                "_check_stat_markers_drift": [],
                "_check_scripts_py_drift": None,
                "_check_scripts_non_py_drift": None,
                "_check_og_image_alt_drift": [],
                "_check_sparkle_drift": [],
                "_check_glee_dark_coverage": [],
                "_check_css_token_drift": [],
                "_check_template_metadata": [],
                "_check_offline_shell": [],
                "_check_mermaid_version_pin": [],
                "_check_mermaid_csp_alignment": [],
            }
            report_path = (
                root / "assets" / "audit" / "validation-report-2026-09-10.json"
            )
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(validate_site, "ROOT", root))
                stack.enter_context(mock.patch("builtins.print"))
                stack.enter_context(
                    mock.patch.object(
                        validate_site, "collect_html_files", return_value=[page_path]
                    )
                )
                # main() adds the path to each result; use a fresh result per run.
                page_check = stack.enter_context(
                    mock.patch.object(
                        validate_site,
                        "check_page",
                        side_effect=lambda *_: {
                            "issues": ["fixture page issue"],
                            "warnings": ["fixture page warning"],
                        },
                    )
                )
                global_check = stack.enter_context(
                    mock.patch.object(
                        validate_site,
                        "_check_css_lines_drift",
                        return_value="fixture global failure",
                    )
                )
                stack.enter_context(
                    mock.patch.object(
                        validate_site,
                        "_check_adr_index_sync",
                        return_value="fixture global warning",
                    )
                )
                for name, value in clean_checks.items():
                    stack.enter_context(
                        mock.patch.object(validate_site, name, return_value=value)
                    )
                clock = stack.enter_context(
                    mock.patch.object(validate_site, "datetime", wraps=datetime)
                )
                clock.now.side_effect = run_times
                calendar = stack.enter_context(mock.patch.object(validate_site, "date"))
                calendar.today.return_value = run_date

                self.assertEqual(validate_site.main(), 1)
                original_bytes = report_path.read_bytes()
                original_report = json.loads(original_bytes)
                self.assertEqual(original_report["generated_at"], "2026-09-10T17:00:00Z")
                self.assertEqual(original_report["run_date"], run_date.isoformat())
                self.assertEqual(original_report["scanned"], 1)
                self.assertEqual(
                    original_report["pages"],
                    [{
                        "issues": ["fixture page issue"],
                        "warnings": ["fixture page warning"],
                        "path": "index.html",
                    }],
                )
                self.assertEqual(
                    original_report["global_issues"],
                    ["CSS-lines drift: fixture global failure"],
                )
                self.assertEqual(
                    original_report["global_warnings"],
                    ["ADR index drift: fixture global warning"],
                )
                self.assertEqual(original_report["total_issues"], 2)
                self.assertEqual(original_report["total_warnings"], 2)

                self.assertEqual(validate_site.main(), 1)
                self.assertEqual(report_path.read_bytes(), original_bytes)
                self.assertEqual(
                    json.loads(report_path.read_bytes())["generated_at"],
                    original_report["generated_at"],
                )

                # Change only the detail, not the count, to test the full payload.
                global_check.return_value = "changed global failure"
                self.assertEqual(validate_site.main(), 1)
                self.assertNotEqual(report_path.read_bytes(), original_bytes)
                refreshed_report = json.loads(report_path.read_bytes())
                self.assertEqual(
                    refreshed_report,
                    {
                        **original_report,
                        "generated_at": "2026-09-10T17:10:00Z",
                        "global_issues": ["CSS-lines drift: changed global failure"],
                    },
                )
                self.assertEqual(list(report_path.parent.iterdir()), [report_path])
                self.assertEqual(
                    page_check.call_args_list,
                    [mock.call(Path("index.html"), page_html)] * 3,
                )
                self.assertEqual(
                    clock.now.call_args_list, [mock.call(timezone.utc)] * 3
                )

    def test_main_preserves_unchanged_evidence_for_same_validated_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "assets").mkdir()
            page_path = root / "index.html"
            page_html = "<!doctype html>"
            page_path.write_text(page_html, encoding="utf-8")
            run_date = date(2026, 9, 10)
            validated_commit = "abcdef0123456789abcdef0123456789abcdef01"
            global_checks = {
                "_check_organization_identity_approval": [],
                "_check_css_lines_drift": "fixture global failure",
                "_check_stat_markers_drift": [],
                "_check_adr_index_sync": "fixture global warning",
                "_check_scripts_py_drift": None,
                "_check_scripts_non_py_drift": None,
                "_check_og_image_alt_drift": [],
                "_check_sparkle_drift": [],
                "_check_glee_dark_coverage": [],
                "_check_css_token_drift": [],
                "_check_template_metadata": [],
                "_check_offline_shell": [],
                "_check_mermaid_version_pin": [],
                "_check_mermaid_csp_alignment": [],
            }
            report_path = (
                root / "assets" / "audit" / "validation-report-2026-09-10.json"
            )
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(validate_site, "ROOT", root))
                stack.enter_context(mock.patch("builtins.print"))
                stack.enter_context(
                    mock.patch.object(
                        validate_site, "collect_html_files", return_value=[page_path]
                    )
                )
                # main() adds the path; return fresh, identical findings each time.
                page_check = stack.enter_context(
                    mock.patch.object(
                        validate_site,
                        "check_page",
                        side_effect=lambda *_: {
                            "issues": ["fixture page issue"],
                            "warnings": ["fixture page warning"],
                        },
                    )
                )
                identity_history = stack.enter_context(
                    mock.patch.object(
                        validate_site,
                        "_last_owner_confirmed_identity_snapshot",
                        return_value=(None, None),
                    )
                )
                for name, value in global_checks.items():
                    stack.enter_context(
                        mock.patch.object(validate_site, name, return_value=value)
                    )
                clock = stack.enter_context(
                    mock.patch.object(validate_site, "datetime", wraps=datetime)
                )
                clock.now.side_effect = [
                    datetime(2026, 9, 10, 17, 0, tzinfo=timezone.utc),
                    datetime(2026, 9, 10, 17, 5, tzinfo=timezone.utc),
                ]
                calendar = stack.enter_context(mock.patch.object(validate_site, "date"))
                calendar.today.return_value = run_date

                self.assertEqual(validate_site.main(validated_commit=validated_commit), 1)
                original_bytes = report_path.read_bytes()
                original_report = json.loads(original_bytes)
                self.assertEqual(original_report["generated_at"], "2026-09-10T17:00:00Z")
                self.assertEqual(original_report["run_date"], run_date.isoformat())
                self.assertEqual(
                    original_report["provenance"], {"validated_commit": validated_commit}
                )
                self.assertEqual(original_report["scanned"], 1)
                self.assertEqual(original_report["total_issues"], 2)
                self.assertEqual(original_report["total_warnings"], 2)

                self.assertEqual(validate_site.main(validated_commit=validated_commit), 1)
                self.assertEqual(report_path.read_bytes(), original_bytes)
                repeated_report = json.loads(report_path.read_bytes())
                self.assertEqual(
                    repeated_report["generated_at"], original_report["generated_at"]
                )
                self.assertEqual(
                    repeated_report["provenance"], original_report["provenance"]
                )
                self.assertEqual(list(report_path.parent.iterdir()), [report_path])
                self.assertEqual(
                    identity_history.call_args_list, [mock.call(validated_commit)] * 2
                )
                self.assertEqual(
                    page_check.call_args_list,
                    [mock.call(Path("index.html"), page_html)] * 2,
                )
                self.assertEqual(clock.now.call_args_list, [mock.call(timezone.utc)] * 2)

    def test_main_refreshes_same_day_evidence_for_page_only_changes(self):
        for finding_type in ("issues", "warnings"):
            with self.subTest(finding_type=finding_type), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "assets").mkdir()
                page_path = root / "index.html"
                page_html = "<!doctype html>"
                page_path.write_text(page_html, encoding="utf-8")
                run_date = date(2026, 9, 10)
                global_checks = {
                    "_check_organization_identity_approval": [],
                    "_check_css_lines_drift": "fixture global failure",
                    "_check_stat_markers_drift": [],
                    "_check_adr_index_sync": "fixture global warning",
                    "_check_scripts_py_drift": None,
                    "_check_scripts_non_py_drift": None,
                    "_check_og_image_alt_drift": [],
                    "_check_sparkle_drift": [],
                    "_check_glee_dark_coverage": [],
                    "_check_css_token_drift": [],
                    "_check_template_metadata": [],
                    "_check_offline_shell": [],
                    "_check_mermaid_version_pin": [],
                    "_check_mermaid_csp_alignment": [],
                }
                original_page = {
                    "issues": ["fixture page issue"],
                    "warnings": ["fixture page warning"],
                }
                changed_page = {
                    **original_page,
                    finding_type: [f"changed page {finding_type} detail"],
                }
                report_path = (
                    root / "assets" / "audit" / "validation-report-2026-09-10.json"
                )
                with ExitStack() as stack:
                    stack.enter_context(mock.patch.object(validate_site, "ROOT", root))
                    stack.enter_context(mock.patch("builtins.print"))
                    stack.enter_context(
                        mock.patch.object(
                            validate_site, "collect_html_files", return_value=[page_path]
                        )
                    )
                    # main() adds the path; give each run its own result dictionary.
                    page_check = stack.enter_context(
                        mock.patch.object(
                            validate_site,
                            "check_page",
                            side_effect=[dict(original_page), dict(changed_page)],
                        )
                    )
                    stack.enter_context(
                        mock.patch.object(
                            validate_site,
                            "_last_owner_confirmed_identity_snapshot",
                            return_value=(None, None),
                        )
                    )
                    for name, value in global_checks.items():
                        stack.enter_context(
                            mock.patch.object(validate_site, name, return_value=value)
                        )
                    clock = stack.enter_context(
                        mock.patch.object(validate_site, "datetime", wraps=datetime)
                    )
                    clock.now.side_effect = [
                        datetime(2026, 9, 10, 17, 0, tzinfo=timezone.utc),
                        datetime(2026, 9, 10, 17, 5, tzinfo=timezone.utc),
                    ]
                    calendar = stack.enter_context(mock.patch.object(validate_site, "date"))
                    calendar.today.return_value = run_date

                    self.assertEqual(validate_site.main(), 1)
                    original_bytes = report_path.read_bytes()
                    original_report = json.loads(original_bytes)
                    self.assertEqual(
                        original_report["generated_at"], "2026-09-10T17:00:00Z"
                    )
                    self.assertEqual(original_report["run_date"], run_date.isoformat())
                    self.assertEqual(original_report["scanned"], 1)
                    self.assertEqual(
                        original_report["pages"], [{**original_page, "path": "index.html"}]
                    )
                    self.assertEqual(
                        original_report["global_issues"],
                        ["CSS-lines drift: fixture global failure"],
                    )
                    self.assertEqual(
                        original_report["global_warnings"],
                        ["ADR index drift: fixture global warning"],
                    )
                    self.assertEqual(original_report["total_issues"], 2)
                    self.assertEqual(original_report["total_warnings"], 2)
                    self.assertEqual(original_report["organization_identity_issues"], [])

                    self.assertEqual(validate_site.main(), 1)
                    self.assertNotEqual(report_path.read_bytes(), original_bytes)
                    self.assertEqual(
                        json.loads(report_path.read_bytes()),
                        {
                            **original_report,
                            "generated_at": "2026-09-10T17:05:00Z",
                            "pages": [{**changed_page, "path": "index.html"}],
                        },
                    )
                    self.assertEqual(list(report_path.parent.iterdir()), [report_path])
                    self.assertEqual(
                        page_check.call_args_list,
                        [mock.call(Path("index.html"), page_html)] * 2,
                    )
                    self.assertEqual(
                        clock.now.call_args_list, [mock.call(timezone.utc)] * 2
                    )

    def test_main_refreshes_same_day_evidence_for_commit_only_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "assets").mkdir()
            page_path = root / "index.html"
            page_html = "<!doctype html>"
            page_path.write_text(page_html, encoding="utf-8")
            run_date = date(2026, 9, 10)
            original_commit = "abcdef0123456789abcdef0123456789abcdef01"
            changed_commit = "abcdef0123456789abcdef0123456789abcdef02"
            global_checks = {
                "_check_organization_identity_approval": [],
                "_check_css_lines_drift": "fixture global failure",
                "_check_stat_markers_drift": [],
                "_check_adr_index_sync": "fixture global warning",
                "_check_scripts_py_drift": None,
                "_check_scripts_non_py_drift": None,
                "_check_og_image_alt_drift": [],
                "_check_sparkle_drift": [],
                "_check_glee_dark_coverage": [],
                "_check_css_token_drift": [],
                "_check_template_metadata": [],
                "_check_offline_shell": [],
                "_check_mermaid_version_pin": [],
                "_check_mermaid_csp_alignment": [],
            }
            report_path = (
                root / "assets" / "audit" / "validation-report-2026-09-10.json"
            )
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(validate_site, "ROOT", root))
                stack.enter_context(mock.patch("builtins.print"))
                stack.enter_context(
                    mock.patch.object(
                        validate_site, "collect_html_files", return_value=[page_path]
                    )
                )
                # main() adds the path; return a fresh result for each run.
                page_check = stack.enter_context(
                    mock.patch.object(
                        validate_site,
                        "check_page",
                        side_effect=lambda *_: {
                            "issues": ["fixture page issue"],
                            "warnings": ["fixture page warning"],
                        },
                    )
                )
                identity_history = stack.enter_context(
                    mock.patch.object(
                        validate_site,
                        "_last_owner_confirmed_identity_snapshot",
                        return_value=(None, None),
                    )
                )
                for name, value in global_checks.items():
                    stack.enter_context(
                        mock.patch.object(validate_site, name, return_value=value)
                    )
                clock = stack.enter_context(
                    mock.patch.object(validate_site, "datetime", wraps=datetime)
                )
                clock.now.side_effect = [
                    datetime(2026, 9, 10, 17, 0, tzinfo=timezone.utc),
                    datetime(2026, 9, 10, 17, 5, tzinfo=timezone.utc),
                ]
                calendar = stack.enter_context(mock.patch.object(validate_site, "date"))
                calendar.today.return_value = run_date

                self.assertEqual(
                    validate_site.main(validated_commit=original_commit), 1
                )
                original_bytes = report_path.read_bytes()
                original_report = json.loads(original_bytes)
                self.assertEqual(
                    original_report["provenance"]["validated_commit"], original_commit
                )
                self.assertEqual(
                    original_report["generated_at"], "2026-09-10T17:00:00Z"
                )
                self.assertEqual(original_report["run_date"], run_date.isoformat())
                self.assertEqual(original_report["scanned"], 1)
                self.assertEqual(
                    original_report["pages"],
                    [{
                        "issues": ["fixture page issue"],
                        "warnings": ["fixture page warning"],
                        "path": "index.html",
                    }],
                )
                self.assertEqual(
                    original_report["global_issues"],
                    ["CSS-lines drift: fixture global failure"],
                )
                self.assertEqual(
                    original_report["global_warnings"],
                    ["ADR index drift: fixture global warning"],
                )
                self.assertEqual(original_report["total_issues"], 2)
                self.assertEqual(original_report["total_warnings"], 2)
                self.assertEqual(original_report["organization_identity_issues"], [])

                self.assertEqual(
                    validate_site.main(validated_commit=changed_commit), 1
                )
                self.assertNotEqual(report_path.read_bytes(), original_bytes)
                self.assertEqual(
                    json.loads(report_path.read_bytes()),
                    {
                        **original_report,
                        "generated_at": "2026-09-10T17:05:00Z",
                        "provenance": {
                            **original_report["provenance"],
                            "validated_commit": changed_commit,
                        },
                    },
                )
                self.assertEqual(list(report_path.parent.iterdir()), [report_path])
                self.assertEqual(
                    identity_history.call_args_list,
                    [mock.call(original_commit), mock.call(changed_commit)],
                )
                self.assertEqual(
                    page_check.call_args_list,
                    [mock.call(Path("index.html"), page_html)] * 2,
                )
                self.assertEqual(
                    clock.now.call_args_list, [mock.call(timezone.utc)] * 2
                )

    def test_main_creates_next_day_evidence_without_changing_previous_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "assets").mkdir()
            page_path = root / "index.html"
            page_html = "<!doctype html>"
            page_path.write_text(page_html, encoding="utf-8")
            first_date = date(2026, 9, 10)
            next_date = date(2026, 9, 11)
            global_checks = {
                "_check_organization_identity_approval": [],
                "_check_css_lines_drift": "fixture global failure",
                "_check_stat_markers_drift": [],
                "_check_adr_index_sync": "fixture global warning",
                "_check_scripts_py_drift": None,
                "_check_scripts_non_py_drift": None,
                "_check_og_image_alt_drift": [],
                "_check_sparkle_drift": [],
                "_check_glee_dark_coverage": [],
                "_check_css_token_drift": [],
                "_check_template_metadata": [],
                "_check_offline_shell": [],
                "_check_mermaid_version_pin": [],
                "_check_mermaid_csp_alignment": [],
            }
            audit_dir = root / "assets" / "audit"
            first_path = audit_dir / "validation-report-2026-09-10.json"
            next_path = audit_dir / "validation-report-2026-09-11.json"
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(validate_site, "ROOT", root))
                stack.enter_context(mock.patch("builtins.print"))
                stack.enter_context(
                    mock.patch.object(
                        validate_site, "collect_html_files", return_value=[page_path]
                    )
                )
                # main() adds the path to each result; keep findings fresh but equal.
                page_check = stack.enter_context(
                    mock.patch.object(
                        validate_site,
                        "check_page",
                        side_effect=lambda *_: {
                            "issues": ["fixture page issue"],
                            "warnings": ["fixture page warning"],
                        },
                    )
                )
                for name, value in global_checks.items():
                    stack.enter_context(
                        mock.patch.object(validate_site, name, return_value=value)
                    )
                clock = stack.enter_context(
                    mock.patch.object(validate_site, "datetime", wraps=datetime)
                )
                clock.now.side_effect = [
                    datetime(2026, 9, 10, 17, 0, tzinfo=timezone.utc),
                    datetime(2026, 9, 11, 17, 5, tzinfo=timezone.utc),
                ]
                calendar = stack.enter_context(mock.patch.object(validate_site, "date"))
                calendar.today.return_value = first_date

                self.assertEqual(validate_site.main(), 1)
                original_bytes = first_path.read_bytes()
                original_report = json.loads(original_bytes)
                self.assertEqual(original_report["run_date"], first_date.isoformat())
                self.assertEqual(original_report["generated_at"], "2026-09-10T17:00:00Z")
                self.assertEqual(original_report["scanned"], 1)
                self.assertEqual(
                    original_report["pages"],
                    [{
                        "issues": ["fixture page issue"],
                        "warnings": ["fixture page warning"],
                        "path": "index.html",
                    }],
                )
                self.assertEqual(
                    original_report["global_issues"],
                    ["CSS-lines drift: fixture global failure"],
                )
                self.assertEqual(
                    original_report["global_warnings"],
                    ["ADR index drift: fixture global warning"],
                )
                self.assertEqual(original_report["total_issues"], 2)
                self.assertEqual(original_report["total_warnings"], 2)
                self.assertFalse(next_path.exists())

                calendar.today.return_value = next_date
                self.assertEqual(validate_site.main(), 1)
                self.assertEqual(first_path.read_bytes(), original_bytes)
                self.assertEqual(
                    json.loads(next_path.read_bytes()),
                    {
                        **original_report,
                        "run_date": next_date.isoformat(),
                        "generated_at": "2026-09-11T17:05:00Z",
                    },
                )
                self.assertEqual(set(audit_dir.iterdir()), {first_path, next_path})
                self.assertEqual(
                    page_check.call_args_list,
                    [mock.call(Path("index.html"), page_html)] * 2,
                )
                self.assertEqual(
                    clock.now.call_args_list, [mock.call(timezone.utc)] * 2
                )

    def test_main_creates_next_day_evidence_for_same_validated_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "assets").mkdir()
            page_path = root / "index.html"
            page_html = "<!doctype html>"
            page_path.write_text(page_html, encoding="utf-8")
            first_date = date(2026, 9, 10)
            next_date = date(2026, 9, 11)
            validated_commit = "abcdef0123456789abcdef0123456789abcdef01"
            global_checks = {
                "_check_organization_identity_approval": [],
                "_check_css_lines_drift": "fixture global failure",
                "_check_stat_markers_drift": [],
                "_check_adr_index_sync": "fixture global warning",
                "_check_scripts_py_drift": None,
                "_check_scripts_non_py_drift": None,
                "_check_og_image_alt_drift": [],
                "_check_sparkle_drift": [],
                "_check_glee_dark_coverage": [],
                "_check_css_token_drift": [],
                "_check_template_metadata": [],
                "_check_offline_shell": [],
                "_check_mermaid_version_pin": [],
                "_check_mermaid_csp_alignment": [],
            }
            audit_dir = root / "assets" / "audit"
            first_path = audit_dir / "validation-report-2026-09-10.json"
            next_path = audit_dir / "validation-report-2026-09-11.json"
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(validate_site, "ROOT", root))
                stack.enter_context(mock.patch("builtins.print"))
                stack.enter_context(
                    mock.patch.object(
                        validate_site, "collect_html_files", return_value=[page_path]
                    )
                )
                # main() adds the path; return fresh, identical findings each time.
                page_check = stack.enter_context(
                    mock.patch.object(
                        validate_site,
                        "check_page",
                        side_effect=lambda *_: {
                            "issues": ["fixture page issue"],
                            "warnings": ["fixture page warning"],
                        },
                    )
                )
                identity_history = stack.enter_context(
                    mock.patch.object(
                        validate_site,
                        "_last_owner_confirmed_identity_snapshot",
                        return_value=(None, None),
                    )
                )
                for name, value in global_checks.items():
                    stack.enter_context(
                        mock.patch.object(validate_site, name, return_value=value)
                    )
                clock = stack.enter_context(
                    mock.patch.object(validate_site, "datetime", wraps=datetime)
                )
                clock.now.side_effect = [
                    datetime(2026, 9, 10, 17, 0, tzinfo=timezone.utc),
                    datetime(2026, 9, 11, 17, 5, tzinfo=timezone.utc),
                ]
                calendar = stack.enter_context(mock.patch.object(validate_site, "date"))
                calendar.today.return_value = first_date

                self.assertEqual(validate_site.main(validated_commit=validated_commit), 1)
                original_bytes = first_path.read_bytes()
                original_report = json.loads(original_bytes)
                self.assertEqual(original_report["run_date"], first_date.isoformat())
                self.assertEqual(original_report["generated_at"], "2026-09-10T17:00:00Z")
                self.assertEqual(
                    original_report["provenance"], {"validated_commit": validated_commit}
                )
                self.assertEqual(original_report["scanned"], 1)
                self.assertEqual(
                    original_report["pages"],
                    [{
                        "issues": ["fixture page issue"],
                        "warnings": ["fixture page warning"],
                        "path": "index.html",
                    }],
                )
                self.assertEqual(
                    original_report["global_issues"],
                    ["CSS-lines drift: fixture global failure"],
                )
                self.assertEqual(
                    original_report["global_warnings"],
                    ["ADR index drift: fixture global warning"],
                )
                self.assertEqual(original_report["total_issues"], 2)
                self.assertEqual(original_report["total_warnings"], 2)
                self.assertFalse(next_path.exists())

                calendar.today.return_value = next_date
                self.assertEqual(validate_site.main(validated_commit=validated_commit), 1)
                self.assertEqual(first_path.read_bytes(), original_bytes)
                self.assertEqual(
                    json.loads(next_path.read_bytes()),
                    {
                        **original_report,
                        "run_date": next_date.isoformat(),
                        "generated_at": "2026-09-11T17:05:00Z",
                        "provenance": {"validated_commit": validated_commit},
                    },
                )
                self.assertEqual(set(audit_dir.iterdir()), {first_path, next_path})
                self.assertEqual(
                    identity_history.call_args_list, [mock.call(validated_commit)] * 2
                )
                self.assertEqual(
                    page_check.call_args_list,
                    [mock.call(Path("index.html"), page_html)] * 2,
                )
                self.assertEqual(clock.now.call_args_list, [mock.call(timezone.utc)] * 2)

    def test_main_recovers_after_later_report_save_failure_and_preserves_prior_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "assets").mkdir()
            page_path = root / "index.html"
            page_html = "<!doctype html>"
            page_path.write_text(page_html, encoding="utf-8")
            audit_dir = root / "assets" / "audit"
            first_path = audit_dir / "validation-report-2026-09-10.json"
            next_path = audit_dir / "validation-report-2026-09-11.json"
            validated_commit = "abcdef0123456789abcdef0123456789abcdef01"
            clean_checks = {
                "_check_organization_identity_approval": [],
                "_check_css_lines_drift": None,
                "_check_stat_markers_drift": [],
                "_check_adr_index_sync": None,
                "_check_scripts_py_drift": None,
                "_check_scripts_non_py_drift": None,
                "_check_og_image_alt_drift": [],
                "_check_sparkle_drift": [],
                "_check_glee_dark_coverage": [],
                "_check_css_token_drift": [],
                "_check_template_metadata": [],
                "_check_offline_shell": [],
                "_check_mermaid_version_pin": [],
                "_check_mermaid_csp_alignment": [],
            }
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(validate_site, "ROOT", root))
                output = stack.enter_context(mock.patch("builtins.print"))
                stack.enter_context(
                    mock.patch.object(
                        validate_site, "collect_html_files", return_value=[page_path]
                    )
                )
                page_check = stack.enter_context(
                    mock.patch.object(
                        validate_site,
                        "check_page",
                        side_effect=lambda *_: {"issues": [], "warnings": []},
                    )
                )
                identity_history = stack.enter_context(
                    mock.patch.object(
                        validate_site,
                        "_last_owner_confirmed_identity_snapshot",
                        return_value=(None, None),
                    )
                )
                for name, value in clean_checks.items():
                    stack.enter_context(
                        mock.patch.object(validate_site, name, return_value=value)
                    )
                clock = stack.enter_context(
                    mock.patch.object(validate_site, "datetime", wraps=datetime)
                )
                clock.now.side_effect = [
                    datetime(2026, 9, 10, 17, 0, tzinfo=timezone.utc),
                    datetime(2026, 9, 11, 17, 5, tzinfo=timezone.utc),
                    datetime(2026, 9, 11, 17, 10, tzinfo=timezone.utc),
                ]
                calendar = stack.enter_context(mock.patch.object(validate_site, "date"))
                calendar.today.return_value = date(2026, 9, 10)

                self.assertEqual(validate_site.main(validated_commit=validated_commit), 0)
                original_bytes = first_path.read_bytes()
                original_report = json.loads(original_bytes)
                self.assertEqual(original_report["run_date"], "2026-09-10")
                self.assertEqual(original_report["total_issues"], 0)
                self.assertEqual(original_report["total_warnings"], 0)
                output.reset_mock()
                calendar.today.return_value = date(2026, 9, 11)
                write_error = OSError("fixture evidence save failed")
                real_replace = Path.replace

                def fail_later_report(path, destination):
                    if destination == next_path:
                        self.assertEqual(
                            json.loads(path.read_text(encoding="utf-8")),
                            {
                                **original_report,
                                "run_date": "2026-09-11",
                                "generated_at": "2026-09-11T17:05:00Z",
                            },
                        )
                        raise write_error
                    return real_replace(path, destination)

                # Exercise the real report writer, failing only its later file save.
                with mock.patch.object(
                    Path, "replace", autospec=True, side_effect=fail_later_report
                ) as save:
                    with self.assertRaises(OSError) as raised:
                        validate_site.main(validated_commit=validated_commit)
                    self.assertIs(raised.exception, write_error)
                    save.assert_called_once()
                    staged_path, attempted_path = save.call_args.args
                    self.assertEqual(attempted_path, next_path)
                    self.assertEqual(staged_path.parent, audit_dir)
                    self.assertNotEqual(staged_path, next_path)
                    self.assertEqual(save.call_args.kwargs, {})

                output.assert_not_called()
                self.assertEqual(first_path.read_bytes(), original_bytes)
                self.assertFalse(next_path.exists())
                self.assertEqual(set(audit_dir.iterdir()), {first_path})

                # Remove the transient replacement failure and retry main on the
                # same day. Fresh findings must reach the real serializer and writer.
                finding = "retry warning with valid Unicode: café"
                page_check.side_effect = lambda *_: {
                    "issues": [], "warnings": [finding]
                }
                with mock.patch.object(
                    validate_site.tempfile,
                    "NamedTemporaryFile",
                    wraps=tempfile.NamedTemporaryFile,
                ) as staging:
                    self.assertEqual(
                        validate_site.main(validated_commit=validated_commit), 0
                    )
                    staging.assert_called_once_with(
                        mode="w", encoding="utf-8", dir=audit_dir,
                        prefix=f".{next_path.name}.", suffix=".tmp", delete=False,
                    )

                corrected_bytes = next_path.read_bytes()
                self.assertEqual(
                    json.loads(corrected_bytes),
                    {
                        **original_report,
                        "run_date": "2026-09-11",
                        "generated_at": "2026-09-11T17:10:00Z",
                        "pages": [{
                            "issues": [], "warnings": [finding], "path": "index.html",
                        }],
                        "total_warnings": 1,
                    },
                )
                self.assertIn(finding.encode("utf-8"), corrected_bytes)
                self.assertEqual(first_path.read_bytes(), original_bytes)
                self.assertFalse(staged_path.exists())
                self.assertEqual(set(audit_dir.iterdir()), {first_path, next_path})
                output.assert_any_call("  issues:   0")
                output.assert_any_call("  warnings: 1")
                self.assertEqual(
                    identity_history.call_args_list, [mock.call(validated_commit)] * 3
                )
                self.assertEqual(
                    page_check.call_args_list,
                    [mock.call(Path("index.html"), page_html)] * 3,
                )
                self.assertEqual(clock.now.call_args_list, [mock.call(timezone.utc)] * 3)

    def test_main_recovers_after_permission_denied_replacement_on_same_day(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit_dir = root / "assets" / "audit"
            audit_dir.mkdir(parents=True)
            report_path = audit_dir / "validation-report-2026-09-10.json"
            historical_path = audit_dir / "validation-report-2026-09-09.json"
            historical_bytes = b'{"generated_at": "2026-09-09T17:00:00Z"}\n'
            historical_path.write_bytes(historical_bytes)
            page_path = root / "index.html"
            page_html = "<!doctype html>"
            page_path.write_text(page_html, encoding="utf-8")
            validated_commit = "abcdef0123456789abcdef0123456789abcdef01"
            clean_checks = {
                "_check_organization_identity_approval": [],
                "_check_css_lines_drift": None,
                "_check_stat_markers_drift": [],
                "_check_adr_index_sync": None,
                "_check_scripts_py_drift": None,
                "_check_scripts_non_py_drift": None,
                "_check_og_image_alt_drift": [],
                "_check_sparkle_drift": [],
                "_check_glee_dark_coverage": [],
                "_check_css_token_drift": [],
                "_check_template_metadata": [],
                "_check_offline_shell": [],
                "_check_mermaid_version_pin": [],
                "_check_mermaid_csp_alignment": [],
            }
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(validate_site, "ROOT", root))
                output = stack.enter_context(mock.patch("builtins.print"))
                stack.enter_context(mock.patch.object(
                    validate_site, "collect_html_files", return_value=[page_path]
                ))
                page_check = stack.enter_context(mock.patch.object(
                    validate_site, "check_page",
                    side_effect=lambda *_: {"issues": [], "warnings": []},
                ))
                stack.enter_context(mock.patch.object(
                    validate_site, "_last_owner_confirmed_identity_snapshot",
                    return_value=(None, None),
                ))
                for name, value in clean_checks.items():
                    stack.enter_context(
                        mock.patch.object(validate_site, name, return_value=value)
                    )
                calendar = stack.enter_context(mock.patch.object(validate_site, "date"))
                calendar.today.return_value = date(2026, 9, 10)
                clock = stack.enter_context(
                    mock.patch.object(validate_site, "datetime", wraps=datetime)
                )
                clock.now.side_effect = [
                    datetime(2026, 9, 10, 17, 0, tzinfo=timezone.utc),
                    datetime(2026, 9, 10, 17, 5, tzinfo=timezone.utc),
                    datetime(2026, 9, 10, 17, 10, tzinfo=timezone.utc),
                ]

                self.assertEqual(validate_site.main(validated_commit=validated_commit), 0)
                original_bytes = report_path.read_bytes()
                original_report = json.loads(original_bytes)
                evidence = {
                    report_path: original_bytes,
                    historical_path: historical_bytes,
                }
                original_stats = {path: path.stat() for path in evidence}
                output.reset_mock()
                failed_warning = "warning from denied save"
                page_check.side_effect = lambda *_: {
                    "issues": [], "warnings": [failed_warning],
                }
                denied_error = PermissionError("fixture report replacement access denied")

                def deny_replacement(path, destination):
                    self.assertEqual(destination, report_path)
                    self.assertEqual(path.parent, audit_dir)
                    self.assertNotIn(path, evidence)
                    self.assertTrue(path.name.startswith(f".{report_path.name}."))
                    self.assertEqual(path.suffix, ".tmp")
                    self.assertEqual(json.loads(path.read_bytes()), {
                        **original_report,
                        "generated_at": "2026-09-10T17:05:00Z",
                        "pages": [{
                            "issues": [], "warnings": [failed_warning], "path": "index.html",
                        }],
                        "total_warnings": 1,
                    })
                    raise denied_error

                # Permissions are unreliable under privileged runners. Inject only
                # the final replacement denial; writing, closing and cleanup are real.
                with mock.patch.object(
                    Path, "replace", autospec=True, side_effect=deny_replacement
                ) as replacement:
                    with self.assertRaises(PermissionError) as raised:
                        validate_site.main(validated_commit=validated_commit)
                    self.assertIs(raised.exception, denied_error)
                    replacement.assert_called_once()
                    staged_path, destination = replacement.call_args.args
                    replacement.assert_called_once_with(staged_path, report_path)
                    self.assertEqual(destination, report_path)

                output.assert_not_called()
                self.assertFalse(staged_path.exists())
                self.assertEqual(set(audit_dir.iterdir()), set(evidence))
                for path, content in evidence.items():
                    self.assertEqual(path.read_bytes(), content)
                    self.assertEqual(path.stat().st_ino, original_stats[path].st_ino)
                    self.assertEqual(path.stat().st_mtime_ns, original_stats[path].st_mtime_ns)

                # Retry on the same date without any filesystem injections.
                finding = "fresh retry issue with valid Unicode: café"
                warning = "fresh retry warning"
                page_check.side_effect = lambda *_: {
                    "issues": [finding], "warnings": [warning],
                }
                self.assertEqual(validate_site.main(validated_commit=validated_commit), 1)
                saved_bytes = report_path.read_bytes()
                self.assertNotEqual(saved_bytes, original_bytes)
                self.assertEqual(json.loads(saved_bytes), {
                    **original_report,
                    "generated_at": "2026-09-10T17:10:00Z",
                    "pages": [{
                        "issues": [finding], "warnings": [warning], "path": "index.html",
                    }],
                    "total_issues": 1,
                    "total_warnings": 1,
                })
                self.assertIn(finding.encode("utf-8"), saved_bytes)
                self.assertEqual(historical_path.read_bytes(), historical_bytes)
                self.assertEqual(
                    historical_path.stat().st_mtime_ns,
                    original_stats[historical_path].st_mtime_ns,
                )
                self.assertFalse(staged_path.exists())
                self.assertEqual(set(audit_dir.iterdir()), set(evidence))
                self.assertEqual(list(root.rglob("*.tmp")), [])
                output.assert_any_call("  issues:   1")
                output.assert_any_call("  warnings: 1")
                output.assert_any_call(f"  detail:   {report_path.relative_to(root)}")
                self.assertEqual(
                    page_check.call_args_list,
                    [mock.call(Path("index.html"), page_html)] * 3,
                )
                self.assertEqual(clock.now.call_args_list, [mock.call(timezone.utc)] * 3)
                self.assertEqual(calendar.today.call_args_list, [mock.call()] * 6)

    def test_main_recovers_after_permission_denied_first_report_replacement_on_same_day(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit_dir = root / "assets" / "audit"
            audit_dir.mkdir(parents=True)
            report_path = audit_dir / "validation-report-2026-09-10.json"
            historical_path = audit_dir / "validation-report-2026-09-09.json"
            historical_bytes = b'{"generated_at": "2026-09-09T17:00:00Z"}\n'
            historical_path.write_bytes(historical_bytes)
            historical_stat = historical_path.stat()
            page_path = root / "index.html"
            page_html = "<!doctype html>"
            page_path.write_text(page_html, encoding="utf-8")
            validated_commit = "abcdef0123456789abcdef0123456789abcdef01"
            failed_warning = "warning from denied first save"
            failed_report = {
                "generated_at": "2026-09-10T17:05:00Z",
                "run_date": "2026-09-10",
                "report_type": "site-validation",
                "provenance": {"validated_commit": validated_commit},
                "scanned": 1,
                "total_issues": 0,
                "total_warnings": 1,
                "pages": [{
                    "issues": [], "warnings": [failed_warning], "path": "index.html",
                }],
                "global_issues": [],
                "global_warnings": [],
                "organization_identity_issues": [],
            }
            clean_checks = {
                "_check_organization_identity_approval": [],
                "_check_css_lines_drift": None,
                "_check_stat_markers_drift": [],
                "_check_adr_index_sync": None,
                "_check_scripts_py_drift": None,
                "_check_scripts_non_py_drift": None,
                "_check_og_image_alt_drift": [],
                "_check_sparkle_drift": [],
                "_check_glee_dark_coverage": [],
                "_check_css_token_drift": [],
                "_check_template_metadata": [],
                "_check_offline_shell": [],
                "_check_mermaid_version_pin": [],
                "_check_mermaid_csp_alignment": [],
            }
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(validate_site, "ROOT", root))
                output = stack.enter_context(mock.patch("builtins.print"))
                stack.enter_context(mock.patch.object(
                    validate_site, "collect_html_files", return_value=[page_path]
                ))
                page_check = stack.enter_context(mock.patch.object(
                    validate_site, "check_page",
                    side_effect=lambda *_: {"issues": [], "warnings": [failed_warning]},
                ))
                stack.enter_context(mock.patch.object(
                    validate_site, "_last_owner_confirmed_identity_snapshot",
                    return_value=(None, None),
                ))
                for name, value in clean_checks.items():
                    stack.enter_context(
                        mock.patch.object(validate_site, name, return_value=value)
                    )
                calendar = stack.enter_context(mock.patch.object(validate_site, "date"))
                calendar.today.return_value = date(2026, 9, 10)
                clock = stack.enter_context(
                    mock.patch.object(validate_site, "datetime", wraps=datetime)
                )
                clock.now.side_effect = [
                    datetime(2026, 9, 10, 17, 5, tzinfo=timezone.utc),
                    datetime(2026, 9, 10, 17, 10, tzinfo=timezone.utc),
                ]
                denied_error = PermissionError("fixture first report replacement access denied")

                def deny_replacement(path, destination):
                    self.assertEqual(destination, report_path)
                    self.assertFalse(report_path.exists())
                    self.assertEqual(path.parent, audit_dir)
                    self.assertNotEqual(path, historical_path)
                    self.assertTrue(path.name.startswith(f".{report_path.name}."))
                    self.assertEqual(path.suffix, ".tmp")
                    self.assertEqual(json.loads(path.read_bytes()), failed_report)
                    self.assertEqual(set(audit_dir.iterdir()), {historical_path, path})
                    raise denied_error

                # Keep the writer and staging I/O real; inject only the final
                # replacement denial, independent of runner permissions.
                self.assertFalse(report_path.exists())
                with mock.patch.object(
                    Path, "replace", autospec=True, side_effect=deny_replacement
                ) as replacement:
                    with self.assertRaises(PermissionError) as raised:
                        validate_site.main(validated_commit=validated_commit)
                    self.assertIs(raised.exception, denied_error)
                    replacement.assert_called_once()
                    staged_path, destination = replacement.call_args.args
                    replacement.assert_called_once_with(staged_path, report_path)
                    self.assertEqual(destination, report_path)

                output.assert_not_called()
                self.assertFalse(report_path.exists())
                self.assertFalse(staged_path.exists())
                self.assertEqual(set(audit_dir.iterdir()), {historical_path})
                self.assertEqual(list(root.rglob("*.tmp")), [])
                self.assertEqual(historical_path.read_bytes(), historical_bytes)
                self.assertEqual(historical_path.stat().st_ino, historical_stat.st_ino)
                self.assertEqual(historical_path.stat().st_mtime_ns, historical_stat.st_mtime_ns)

                # Retry main on the same date without any filesystem injections.
                finding = "fresh first-save retry issue with valid Unicode: café"
                warning = "fresh first-save retry warning"
                page_check.side_effect = lambda *_: {
                    "issues": [finding], "warnings": [warning],
                }
                self.assertEqual(validate_site.main(validated_commit=validated_commit), 1)
                saved_bytes = report_path.read_bytes()
                self.assertEqual(json.loads(saved_bytes), {
                    **failed_report,
                    "generated_at": "2026-09-10T17:10:00Z",
                    "pages": [{
                        "issues": [finding], "warnings": [warning], "path": "index.html",
                    }],
                    "total_issues": 1,
                })
                self.assertIn(finding.encode("utf-8"), saved_bytes)
                self.assertEqual(historical_path.read_bytes(), historical_bytes)
                self.assertEqual(historical_path.stat().st_ino, historical_stat.st_ino)
                self.assertEqual(historical_path.stat().st_mtime_ns, historical_stat.st_mtime_ns)
                self.assertFalse(staged_path.exists())
                self.assertEqual(set(audit_dir.iterdir()), {historical_path, report_path})
                self.assertEqual(list(root.rglob("*.tmp")), [])
                output.assert_any_call("  issues:   1")
                output.assert_any_call("  warnings: 1")
                output.assert_any_call(f"  detail:   {report_path.relative_to(root)}")
                self.assertEqual(
                    page_check.call_args_list,
                    [mock.call(Path("index.html"), page_html)] * 2,
                )
                self.assertEqual(clock.now.call_args_list, [mock.call(timezone.utc)] * 2)
                self.assertEqual(calendar.today.call_args_list, [mock.call()] * 4)

    def test_main_returns_success_after_denied_blocking_first_save_on_same_day(self):
        for scenario, retry_warnings in (
            ("warnings", ["fresh retry warning with valid Unicode: café"]),
            ("clean", []),
        ):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                audit_dir = root / "assets" / "audit"
                audit_dir.mkdir(parents=True)
                report_path = audit_dir / "validation-report-2026-09-10.json"
                historical_path = audit_dir / "validation-report-2026-09-09.json"
                historical_bytes = b'{"generated_at": "2026-09-09T17:00:00Z"}\n'
                historical_path.write_bytes(historical_bytes)
                historical_stat = historical_path.stat()
                page_path = root / "index.html"
                page_html = "<!doctype html>"
                page_path.write_text(page_html, encoding="utf-8")
                validated_commit = "abcdef0123456789abcdef0123456789abcdef01"
                failed_issue = "blocking issue from denied first save"
                failed_warning = "warning from denied first save"
                failed_report = {
                    "generated_at": "2026-09-10T17:05:00Z",
                    "run_date": "2026-09-10",
                    "report_type": "site-validation",
                    "provenance": {"validated_commit": validated_commit},
                    "scanned": 1,
                    "total_issues": 1,
                    "total_warnings": 1,
                    "pages": [{
                        "issues": [failed_issue], "warnings": [failed_warning],
                        "path": "index.html",
                    }],
                    "global_issues": [],
                    "global_warnings": [],
                    "organization_identity_issues": [],
                }
                clean_checks = {
                    "_check_organization_identity_approval": [],
                    "_check_css_lines_drift": None,
                    "_check_stat_markers_drift": [],
                    "_check_adr_index_sync": None,
                    "_check_scripts_py_drift": None,
                    "_check_scripts_non_py_drift": None,
                    "_check_og_image_alt_drift": [],
                    "_check_sparkle_drift": [],
                    "_check_glee_dark_coverage": [],
                    "_check_css_token_drift": [],
                    "_check_template_metadata": [],
                    "_check_offline_shell": [],
                    "_check_mermaid_version_pin": [],
                    "_check_mermaid_csp_alignment": [],
                }
                with ExitStack() as stack:
                    stack.enter_context(mock.patch.object(validate_site, "ROOT", root))
                    output = stack.enter_context(mock.patch("builtins.print"))
                    stack.enter_context(mock.patch.object(
                        validate_site, "collect_html_files", return_value=[page_path]
                    ))
                    page_check = stack.enter_context(mock.patch.object(
                        validate_site, "check_page",
                        side_effect=lambda *_: {
                            "issues": [failed_issue], "warnings": [failed_warning],
                        },
                    ))
                    stack.enter_context(mock.patch.object(
                        validate_site, "_last_owner_confirmed_identity_snapshot",
                        return_value=(None, None),
                    ))
                    for name, value in clean_checks.items():
                        stack.enter_context(
                            mock.patch.object(validate_site, name, return_value=value)
                        )
                    calendar = stack.enter_context(mock.patch.object(validate_site, "date"))
                    calendar.today.return_value = date(2026, 9, 10)
                    clock = stack.enter_context(
                        mock.patch.object(validate_site, "datetime", wraps=datetime)
                    )
                    clock.now.side_effect = [
                        datetime(2026, 9, 10, 17, 5, tzinfo=timezone.utc),
                        datetime(2026, 9, 10, 17, 10, tzinfo=timezone.utc),
                    ]
                    denied_error = PermissionError("fixture blocking report access denied")

                    def deny_replacement(path, destination):
                        self.assertEqual(destination, report_path)
                        self.assertFalse(report_path.exists())
                        self.assertEqual(path.parent, audit_dir)
                        self.assertTrue(path.name.startswith(f".{report_path.name}."))
                        self.assertEqual(path.suffix, ".tmp")
                        self.assertEqual(json.loads(path.read_bytes()), failed_report)
                        self.assertEqual(set(audit_dir.iterdir()), {historical_path, path})
                        raise denied_error

                    # Only the final replacement is denied; the real writer creates,
                    # flushes, closes and cleans up the staged blocking report.
                    with mock.patch.object(
                        Path, "replace", autospec=True, side_effect=deny_replacement
                    ) as replacement:
                        with self.assertRaises(PermissionError) as raised:
                            validate_site.main(validated_commit=validated_commit)
                        self.assertIs(raised.exception, denied_error)
                        replacement.assert_called_once()
                        staged_path, destination = replacement.call_args.args
                        self.assertEqual(destination, report_path)

                    # Blocking diagnostics precede the save, but a denied save
                    # must not print the successful completion summary.
                    self.assertEqual(output.call_args_list, [
                        mock.call("\nPages with issues:"),
                        mock.call("  - index.html"),
                        mock.call(f"      ! {failed_issue}"),
                    ])
                    output.reset_mock()
                    self.assertFalse(report_path.exists())
                    self.assertFalse(staged_path.exists())
                    self.assertEqual(set(audit_dir.iterdir()), {historical_path})
                    self.assertEqual(list(root.rglob("*.tmp")), [])
                    self.assertEqual(historical_path.read_bytes(), historical_bytes)
                    self.assertEqual(historical_path.stat().st_ino, historical_stat.st_ino)
                    self.assertEqual(
                        historical_path.stat().st_mtime_ns, historical_stat.st_mtime_ns,
                    )

                    # Retry on the same date with no filesystem injections and
                    # fresh, non-blocking findings instead of the failed run's issues.
                    page_check.side_effect = lambda *_: {
                        "issues": [], "warnings": list(retry_warnings),
                    }
                    self.assertEqual(
                        validate_site.main(validated_commit=validated_commit), 0,
                    )
                    saved_bytes = report_path.read_bytes()
                    self.assertEqual(json.loads(saved_bytes), {
                        **failed_report,
                        "generated_at": "2026-09-10T17:10:00Z",
                        "total_issues": 0,
                        "total_warnings": len(retry_warnings),
                        "pages": [{
                            "issues": [], "warnings": retry_warnings, "path": "index.html",
                        }],
                    })
                    self.assertNotIn(failed_issue.encode("utf-8"), saved_bytes)
                    self.assertNotIn(failed_warning.encode("utf-8"), saved_bytes)
                    self.assertEqual(historical_path.read_bytes(), historical_bytes)
                    self.assertEqual(historical_path.stat().st_ino, historical_stat.st_ino)
                    self.assertEqual(
                        historical_path.stat().st_mtime_ns, historical_stat.st_mtime_ns,
                    )
                    self.assertFalse(staged_path.exists())
                    self.assertEqual(set(audit_dir.iterdir()), {historical_path, report_path})
                    self.assertEqual(list(root.rglob("*.tmp")), [])
                    output.assert_any_call("  issues:   0")
                    output.assert_any_call(f"  warnings: {len(retry_warnings)}")
                    output.assert_any_call(f"  detail:   {report_path.relative_to(root)}")
                    self.assertEqual(
                        page_check.call_args_list,
                        [mock.call(Path("index.html"), page_html)] * 2,
                    )
                    self.assertEqual(clock.now.call_args_list, [mock.call(timezone.utc)] * 2)
                    self.assertEqual(calendar.today.call_args_list, [mock.call()] * 4)

    def test_main_returns_success_after_denied_global_blocking_save_on_same_day(self):
        for scenario, retry_warning in (
            ("warnings", "fresh global retry warning with valid Unicode: café"),
            ("clean", None),
        ):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                audit_dir = root / "assets" / "audit"
                audit_dir.mkdir(parents=True)
                report_path = audit_dir / "validation-report-2026-09-10.json"
                historical_path = audit_dir / "validation-report-2026-09-09.json"
                historical_bytes = b'{"generated_at": "2026-09-09T17:00:00Z"}\n'
                historical_path.write_bytes(historical_bytes)
                historical_stat = historical_path.stat()
                page_path = root / "index.html"
                page_html = "<!doctype html>"
                page_path.write_text(page_html, encoding="utf-8")
                validated_commit = "abcdef0123456789abcdef0123456789abcdef01"
                failed_issue = "blocking global issue from denied save"
                failed_warning = "global warning from denied save"
                clean_pages = [{"issues": [], "warnings": [], "path": "index.html"}]
                failed_report = {
                    "generated_at": "2026-09-10T17:05:00Z",
                    "run_date": "2026-09-10",
                    "report_type": "site-validation",
                    "provenance": {"validated_commit": validated_commit},
                    "scanned": 1,
                    "total_issues": 1,
                    "total_warnings": 1,
                    "pages": clean_pages,
                    "global_issues": [f"CSS-lines drift: {failed_issue}"],
                    "global_warnings": [f"ADR index drift: {failed_warning}"],
                    "organization_identity_issues": [],
                }
                global_checks = {
                    "_check_organization_identity_approval": [],
                    "_check_css_lines_drift": failed_issue,
                    "_check_stat_markers_drift": [],
                    "_check_adr_index_sync": failed_warning,
                    "_check_scripts_py_drift": None,
                    "_check_scripts_non_py_drift": None,
                    "_check_og_image_alt_drift": [],
                    "_check_sparkle_drift": [],
                    "_check_glee_dark_coverage": [],
                    "_check_css_token_drift": [],
                    "_check_template_metadata": [],
                    "_check_offline_shell": [],
                    "_check_mermaid_version_pin": [],
                    "_check_mermaid_csp_alignment": [],
                }
                with ExitStack() as stack:
                    stack.enter_context(mock.patch.object(validate_site, "ROOT", root))
                    output = stack.enter_context(mock.patch("builtins.print"))
                    stack.enter_context(mock.patch.object(
                        validate_site, "collect_html_files", return_value=[page_path],
                    ))
                    page_check = stack.enter_context(mock.patch.object(
                        validate_site, "check_page",
                        side_effect=lambda *_: {"issues": [], "warnings": []},
                    ))
                    stack.enter_context(mock.patch.object(
                        validate_site, "_last_owner_confirmed_identity_snapshot",
                        return_value=(None, None),
                    ))
                    checks = {
                        name: stack.enter_context(
                            mock.patch.object(validate_site, name, return_value=value)
                        )
                        for name, value in global_checks.items()
                    }
                    calendar = stack.enter_context(mock.patch.object(validate_site, "date"))
                    calendar.today.return_value = date(2026, 9, 10)
                    clock = stack.enter_context(
                        mock.patch.object(validate_site, "datetime", wraps=datetime)
                    )
                    clock.now.side_effect = [
                        datetime(2026, 9, 10, 17, 5, tzinfo=timezone.utc),
                        datetime(2026, 9, 10, 17, 10, tzinfo=timezone.utc),
                    ]
                    denied_error = PermissionError("fixture global report access denied")

                    def deny_replacement(path, destination):
                        self.assertEqual(destination, report_path)
                        self.assertFalse(report_path.exists())
                        self.assertEqual(path.parent, audit_dir)
                        self.assertTrue(path.name.startswith(f".{report_path.name}."))
                        self.assertEqual(path.suffix, ".tmp")
                        self.assertEqual(json.loads(path.read_bytes()), failed_report)
                        self.assertEqual(set(audit_dir.iterdir()), {historical_path, path})
                        raise denied_error

                    # Keep staging, writing, closing and cleanup real; deny only
                    # the final replacement of the globally blocking report.
                    with mock.patch.object(
                        Path, "replace", autospec=True, side_effect=deny_replacement,
                    ) as replacement:
                        with self.assertRaises(PermissionError) as raised:
                            validate_site.main(validated_commit=validated_commit)
                        self.assertIs(raised.exception, denied_error)
                        replacement.assert_called_once()
                        staged_path, destination = replacement.call_args.args
                        self.assertEqual(destination, report_path)

                    self.assertEqual(output.call_args_list, [
                        mock.call(f"\nCSS-lines drift: {failed_issue}"),
                        mock.call("  Fix: python3 scripts/sync-portfolio-stats.py"),
                        mock.call(f"\nADR index drift: {failed_warning}"),
                        mock.call(
                            "  Fix: update docs/adr/README.md index table and AGENTS.md section 2.2.1"
                        ),
                    ])
                    output.reset_mock()
                    self.assertFalse(report_path.exists())
                    self.assertFalse(staged_path.exists())
                    self.assertEqual(set(audit_dir.iterdir()), {historical_path})
                    self.assertEqual(list(root.rglob("*.tmp")), [])
                    self.assertEqual(historical_path.read_bytes(), historical_bytes)
                    self.assertEqual(historical_path.stat().st_ino, historical_stat.st_ino)
                    self.assertEqual(
                        historical_path.stat().st_mtime_ns, historical_stat.st_mtime_ns,
                    )

                    # Clear the global blocker and retry on the same date without
                    # filesystem injections, with warnings-only or clean results.
                    checks["_check_css_lines_drift"].return_value = None
                    checks["_check_adr_index_sync"].return_value = retry_warning
                    self.assertEqual(
                        validate_site.main(validated_commit=validated_commit), 0,
                    )
                    retry_warnings = (
                        [f"ADR index drift: {retry_warning}"] if retry_warning else []
                    )
                    saved_bytes = report_path.read_bytes()
                    self.assertEqual(json.loads(saved_bytes), {
                        **failed_report,
                        "generated_at": "2026-09-10T17:10:00Z",
                        "total_issues": 0,
                        "total_warnings": len(retry_warnings),
                        "global_issues": [],
                        "global_warnings": retry_warnings,
                    })
                    self.assertNotIn(failed_issue.encode("utf-8"), saved_bytes)
                    self.assertNotIn(failed_warning.encode("utf-8"), saved_bytes)
                    self.assertEqual(historical_path.read_bytes(), historical_bytes)
                    self.assertEqual(historical_path.stat().st_ino, historical_stat.st_ino)
                    self.assertEqual(
                        historical_path.stat().st_mtime_ns, historical_stat.st_mtime_ns,
                    )
                    self.assertFalse(staged_path.exists())
                    self.assertEqual(set(audit_dir.iterdir()), {historical_path, report_path})
                    self.assertEqual(list(root.rglob("*.tmp")), [])
                    output.assert_any_call("  issues:   0")
                    output.assert_any_call(f"  warnings: {len(retry_warnings)}")
                    output.assert_any_call(f"  detail:   {report_path.relative_to(root)}")
                    self.assertNotIn(failed_issue, str(output.call_args_list))
                    self.assertNotIn(failed_warning, str(output.call_args_list))
                    self.assertEqual(
                        page_check.call_args_list,
                        [mock.call(Path("index.html"), page_html)] * 2,
                    )
                    self.assertEqual(checks["_check_css_lines_drift"].call_count, 2)
                    self.assertEqual(checks["_check_adr_index_sync"].call_count, 2)
                    self.assertEqual(clock.now.call_args_list, [mock.call(timezone.utc)] * 2)
                    self.assertEqual(calendar.today.call_args_list, [mock.call()] * 4)

    def test_main_recovers_after_first_report_audit_directory_creation_failure_on_same_day(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "assets").mkdir()
            page_path = root / "index.html"
            page_html = "<!doctype html>"
            page_path.write_text(page_html, encoding="utf-8")
            audit_dir = root / "assets" / "audit"
            report_path = audit_dir / "validation-report-2026-09-10.json"
            validated_commit = "abcdef0123456789abcdef0123456789abcdef01"
            clean_checks = {
                "_check_organization_identity_approval": [],
                "_check_css_lines_drift": None,
                "_check_stat_markers_drift": [],
                "_check_adr_index_sync": None,
                "_check_scripts_py_drift": None,
                "_check_scripts_non_py_drift": None,
                "_check_og_image_alt_drift": [],
                "_check_sparkle_drift": [],
                "_check_glee_dark_coverage": [],
                "_check_css_token_drift": [],
                "_check_template_metadata": [],
                "_check_offline_shell": [],
                "_check_mermaid_version_pin": [],
                "_check_mermaid_csp_alignment": [],
            }
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(validate_site, "ROOT", root))
                output = stack.enter_context(mock.patch("builtins.print"))
                stack.enter_context(mock.patch.object(
                    validate_site, "collect_html_files", return_value=[page_path]
                ))
                page_check = stack.enter_context(mock.patch.object(
                    validate_site, "check_page",
                    side_effect=lambda *_: {"issues": [], "warnings": []},
                ))
                stack.enter_context(mock.patch.object(
                    validate_site, "_last_owner_confirmed_identity_snapshot",
                    return_value=(None, None),
                ))
                for name, value in clean_checks.items():
                    stack.enter_context(
                        mock.patch.object(validate_site, name, return_value=value)
                    )
                calendar = stack.enter_context(mock.patch.object(validate_site, "date"))
                calendar.today.return_value = date(2026, 9, 10)
                clock = stack.enter_context(
                    mock.patch.object(validate_site, "datetime", wraps=datetime)
                )
                clock.now.return_value = datetime(2026, 9, 10, 17, 5, tzinfo=timezone.utc)
                creation_error = OSError("fixture first-report audit directory creation failed")
                real_mkdir = Path.mkdir

                def fail_audit_mkdir(path, *args, **kwargs):
                    if path == audit_dir:
                        raise creation_error
                    return real_mkdir(path, *args, **kwargs)

                # Fail only main's audit-directory creation; keep unrelated
                # mkdir calls and the report writer's staging behavior real.
                self.assertFalse(audit_dir.exists())
                with mock.patch.object(
                    Path, "mkdir", autospec=True, side_effect=fail_audit_mkdir,
                ) as mkdir, mock.patch.object(
                    validate_site.tempfile, "NamedTemporaryFile",
                    wraps=validate_site.tempfile.NamedTemporaryFile,
                ) as staging:
                    with self.assertRaises(OSError) as raised:
                        validate_site.main(validated_commit=validated_commit)
                    self.assertIs(raised.exception, creation_error)
                    mkdir.assert_called_once_with(audit_dir, exist_ok=True)
                    staging.assert_not_called()
                self.assertFalse(audit_dir.exists())
                self.assertFalse(report_path.exists())
                self.assertEqual(set((root / "assets").iterdir()), set())
                self.assertEqual(list(root.rglob("*.tmp")), [])
                clock.now.assert_not_called()
                output.assert_not_called()

                # Remove the injection and retry on the same date with fresh
                # blocking findings, exercising real mkdir, staging and save.
                finding = "retry issue with valid Unicode: café"
                warning = "retry warning"
                page_check.side_effect = lambda *_: {
                    "issues": [finding], "warnings": [warning],
                }
                self.assertEqual(
                    validate_site.main(validated_commit=validated_commit), 1
                )
                saved_bytes = report_path.read_bytes()
                self.assertEqual(json.loads(saved_bytes), {
                    "generated_at": "2026-09-10T17:05:00Z",
                    "run_date": "2026-09-10",
                    "report_type": "site-validation",
                    "provenance": {"validated_commit": validated_commit},
                    "scanned": 1,
                    "total_issues": 1,
                    "total_warnings": 1,
                    "pages": [{
                        "issues": [finding], "warnings": [warning], "path": "index.html",
                    }],
                    "global_issues": [],
                    "global_warnings": [],
                    "organization_identity_issues": [],
                })
                self.assertIn(finding.encode("utf-8"), saved_bytes)
                self.assertEqual(set(audit_dir.iterdir()), {report_path})
                output.assert_any_call("  issues:   1")
                output.assert_any_call("  warnings: 1")
                self.assertEqual(
                    page_check.call_args_list,
                    [mock.call(Path("index.html"), page_html)] * 2,
                )
                clock.now.assert_called_once_with(timezone.utc)

    def test_main_recovers_after_file_blocks_audit_directory_on_same_day(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets_dir = root / "assets"
            assets_dir.mkdir()
            page_path = root / "index.html"
            page_html = "<!doctype html>"
            page_path.write_text(page_html, encoding="utf-8")
            audit_dir = assets_dir / "audit"
            blocking_bytes = b"existing audit file must remain intact\n"
            audit_dir.write_bytes(blocking_bytes)
            blocking_stat = audit_dir.stat()
            report_path = audit_dir / "validation-report-2026-09-10.json"
            validated_commit = "abcdef0123456789abcdef0123456789abcdef01"
            clean_checks = {
                "_check_organization_identity_approval": [],
                "_check_css_lines_drift": None,
                "_check_stat_markers_drift": [],
                "_check_adr_index_sync": None,
                "_check_scripts_py_drift": None,
                "_check_scripts_non_py_drift": None,
                "_check_og_image_alt_drift": [],
                "_check_sparkle_drift": [],
                "_check_glee_dark_coverage": [],
                "_check_css_token_drift": [],
                "_check_template_metadata": [],
                "_check_offline_shell": [],
                "_check_mermaid_version_pin": [],
                "_check_mermaid_csp_alignment": [],
            }
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(validate_site, "ROOT", root))
                output = stack.enter_context(mock.patch("builtins.print"))
                stack.enter_context(mock.patch.object(
                    validate_site, "collect_html_files", return_value=[page_path]
                ))
                page_check = stack.enter_context(mock.patch.object(
                    validate_site, "check_page",
                    side_effect=lambda *_: {"issues": [], "warnings": []},
                ))
                stack.enter_context(mock.patch.object(
                    validate_site, "_last_owner_confirmed_identity_snapshot",
                    return_value=(None, None),
                ))
                for name, value in clean_checks.items():
                    stack.enter_context(
                        mock.patch.object(validate_site, name, return_value=value)
                    )
                calendar = stack.enter_context(mock.patch.object(validate_site, "date"))
                calendar.today.return_value = date(2026, 9, 10)
                clock = stack.enter_context(
                    mock.patch.object(validate_site, "datetime", wraps=datetime)
                )
                clock.now.return_value = datetime(2026, 9, 10, 17, 5, tzinfo=timezone.utc)

                # Keep the filesystem real: mkdir must reject the existing file,
                # without replacing it or attempting to stage a report.
                with mock.patch.object(
                    validate_site.tempfile, "NamedTemporaryFile",
                    wraps=validate_site.tempfile.NamedTemporaryFile,
                ) as staging:
                    with self.assertRaises(FileExistsError) as raised:
                        validate_site.main(validated_commit=validated_commit)
                    self.assertEqual(raised.exception.filename, str(audit_dir))
                    staging.assert_not_called()
                self.assertTrue(audit_dir.is_file())
                self.assertEqual(audit_dir.read_bytes(), blocking_bytes)
                self.assertEqual(audit_dir.stat().st_ino, blocking_stat.st_ino)
                self.assertEqual(audit_dir.stat().st_mtime_ns, blocking_stat.st_mtime_ns)
                self.assertFalse(report_path.exists())
                self.assertEqual(set(assets_dir.iterdir()), {audit_dir})
                self.assertEqual(set(root.rglob("*")), {assets_dir, audit_dir, page_path})
                clock.now.assert_not_called()
                calendar.today.assert_not_called()
                output.assert_not_called()

                # Remove only the conflict and retry on the unchanged date.
                # New findings must replace the failed run's clean result.
                audit_dir.unlink()
                finding = "retry issue with valid Unicode: café"
                warning = "retry warning"
                page_check.side_effect = lambda *_: {
                    "issues": [finding], "warnings": [warning],
                }
                self.assertEqual(
                    validate_site.main(validated_commit=validated_commit), 1
                )
                saved_bytes = report_path.read_bytes()
                self.assertEqual(json.loads(saved_bytes), {
                    "generated_at": "2026-09-10T17:05:00Z",
                    "run_date": "2026-09-10",
                    "report_type": "site-validation",
                    "provenance": {"validated_commit": validated_commit},
                    "scanned": 1,
                    "total_issues": 1,
                    "total_warnings": 1,
                    "pages": [{
                        "issues": [finding], "warnings": [warning], "path": "index.html",
                    }],
                    "global_issues": [],
                    "global_warnings": [],
                    "organization_identity_issues": [],
                })
                self.assertIn(finding.encode("utf-8"), saved_bytes)
                self.assertTrue(audit_dir.is_dir())
                self.assertEqual(set(assets_dir.iterdir()), {audit_dir})
                self.assertEqual(set(audit_dir.iterdir()), {report_path})
                self.assertEqual(list(root.rglob("*.tmp")), [])
                output.assert_any_call("  issues:   1")
                output.assert_any_call("  warnings: 1")
                self.assertEqual(
                    page_check.call_args_list,
                    [mock.call(Path("index.html"), page_html)] * 2,
                )
                clock.now.assert_called_once_with(timezone.utc)
                self.assertEqual(calendar.today.call_args_list, [mock.call()] * 2)

    def test_main_recovers_after_directory_blocks_report_filename_on_same_day(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit_dir = root / "assets" / "audit"
            report_path = audit_dir / "validation-report-2026-09-10.json"
            report_path.mkdir(parents=True)
            nested_dir = report_path / "nested"
            nested_dir.mkdir()
            directory_contents = {
                report_path / "existing.json": b'{"evidence": "keep intact"}\n',
                nested_dir / "notes.txt": b"existing nested contents\n",
            }
            for path, content in directory_contents.items():
                path.write_bytes(content)
            original_stats = {
                path: path.stat()
                for path in [report_path, nested_dir, *directory_contents]
            }
            page_path = root / "index.html"
            page_html = "<!doctype html>"
            page_path.write_text(page_html, encoding="utf-8")
            validated_commit = "abcdef0123456789abcdef0123456789abcdef01"
            clean_checks = {
                "_check_organization_identity_approval": [],
                "_check_css_lines_drift": None,
                "_check_stat_markers_drift": [],
                "_check_adr_index_sync": None,
                "_check_scripts_py_drift": None,
                "_check_scripts_non_py_drift": None,
                "_check_og_image_alt_drift": [],
                "_check_sparkle_drift": [],
                "_check_glee_dark_coverage": [],
                "_check_css_token_drift": [],
                "_check_template_metadata": [],
                "_check_offline_shell": [],
                "_check_mermaid_version_pin": [],
                "_check_mermaid_csp_alignment": [],
            }
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(validate_site, "ROOT", root))
                output = stack.enter_context(mock.patch("builtins.print"))
                stack.enter_context(mock.patch.object(
                    validate_site, "collect_html_files", return_value=[page_path]
                ))
                page_check = stack.enter_context(mock.patch.object(
                    validate_site, "check_page",
                    side_effect=lambda *_: {"issues": [], "warnings": []},
                ))
                stack.enter_context(mock.patch.object(
                    validate_site, "_last_owner_confirmed_identity_snapshot",
                    return_value=(None, None),
                ))
                for name, value in clean_checks.items():
                    stack.enter_context(
                        mock.patch.object(validate_site, name, return_value=value)
                    )
                calendar = stack.enter_context(mock.patch.object(validate_site, "date"))
                calendar.today.return_value = date(2026, 9, 10)
                clock = stack.enter_context(
                    mock.patch.object(validate_site, "datetime", wraps=datetime)
                )
                clock.now.side_effect = [
                    datetime(2026, 9, 10, 17, 0, tzinfo=timezone.utc),
                    datetime(2026, 9, 10, 17, 5, tzinfo=timezone.utc),
                ]
                staged_paths = []
                real_temporary_file = validate_site.tempfile.NamedTemporaryFile

                def create_staging_file(**kwargs):
                    temporary = real_temporary_file(**kwargs)
                    staged_paths.append(Path(temporary.name))
                    return temporary

                # Real staging, replacement and cleanup: the directory blocks
                # the final report filename, not creation of its parent folder.
                with mock.patch.object(
                    validate_site.tempfile, "NamedTemporaryFile",
                    side_effect=create_staging_file,
                ) as staging:
                    # Windows reports this directory conflict as PermissionError.
                    with self.assertRaises((IsADirectoryError, PermissionError)) as raised:
                        validate_site.main(validated_commit=validated_commit)
                    staging.assert_called_once_with(
                        mode="w", encoding="utf-8", dir=audit_dir,
                        prefix=f".{report_path.name}.", suffix=".tmp", delete=False,
                    )
                self.assertEqual(raised.exception.filename, str(staged_paths[0]))
                self.assertEqual(raised.exception.filename2, str(report_path))
                self.assertFalse(staged_paths[0].exists())
                self.assertTrue(report_path.is_dir())
                for path, content in directory_contents.items():
                    self.assertEqual(path.read_bytes(), content)
                for path, original_stat in original_stats.items():
                    self.assertEqual(path.stat().st_ino, original_stat.st_ino)
                    self.assertEqual(path.stat().st_mtime_ns, original_stat.st_mtime_ns)
                self.assertEqual(
                    set(audit_dir.rglob("*")),
                    {report_path, nested_dir, *directory_contents},
                )
                output.assert_not_called()

                # Remove only the fixture conflict; retry on the same date
                # with changed findings and no filesystem mocks.
                for path in directory_contents:
                    path.unlink()
                nested_dir.rmdir()
                report_path.rmdir()
                finding = "retry issue with valid Unicode: café"
                warning = "retry warning"
                page_check.side_effect = lambda *_: {
                    "issues": [finding], "warnings": [warning],
                }
                self.assertEqual(
                    validate_site.main(validated_commit=validated_commit), 1
                )
                saved_bytes = report_path.read_bytes()
                self.assertEqual(json.loads(saved_bytes), {
                    "generated_at": "2026-09-10T17:05:00Z",
                    "run_date": "2026-09-10",
                    "report_type": "site-validation",
                    "provenance": {"validated_commit": validated_commit},
                    "scanned": 1,
                    "total_issues": 1,
                    "total_warnings": 1,
                    "pages": [{
                        "issues": [finding], "warnings": [warning], "path": "index.html",
                    }],
                    "global_issues": [],
                    "global_warnings": [],
                    "organization_identity_issues": [],
                })
                self.assertIn(finding.encode("utf-8"), saved_bytes)
                self.assertEqual(set(audit_dir.iterdir()), {report_path})
                self.assertEqual(list(root.rglob("*.tmp")), [])
                output.assert_any_call("  issues:   1")
                output.assert_any_call("  warnings: 1")
                self.assertEqual(
                    page_check.call_args_list,
                    [mock.call(Path("index.html"), page_html)] * 2,
                )
                self.assertEqual(clock.now.call_args_list, [mock.call(timezone.utc)] * 2)
                self.assertEqual(calendar.today.call_args_list, [mock.call()] * 4)

    def test_main_recovers_after_first_report_temporary_file_creation_failure_on_same_day(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "assets").mkdir()
            page_path = root / "index.html"
            page_html = "<!doctype html>"
            page_path.write_text(page_html, encoding="utf-8")
            audit_dir = root / "assets" / "audit"
            report_path = audit_dir / "validation-report-2026-09-10.json"
            validated_commit = "abcdef0123456789abcdef0123456789abcdef01"
            clean_checks = {
                "_check_organization_identity_approval": [],
                "_check_css_lines_drift": None,
                "_check_stat_markers_drift": [],
                "_check_adr_index_sync": None,
                "_check_scripts_py_drift": None,
                "_check_scripts_non_py_drift": None,
                "_check_og_image_alt_drift": [],
                "_check_sparkle_drift": [],
                "_check_glee_dark_coverage": [],
                "_check_css_token_drift": [],
                "_check_template_metadata": [],
                "_check_offline_shell": [],
                "_check_mermaid_version_pin": [],
                "_check_mermaid_csp_alignment": [],
            }
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(validate_site, "ROOT", root))
                output = stack.enter_context(mock.patch("builtins.print"))
                stack.enter_context(mock.patch.object(
                    validate_site, "collect_html_files", return_value=[page_path]
                ))
                page_check = stack.enter_context(mock.patch.object(
                    validate_site, "check_page",
                    side_effect=lambda *_: {"issues": [], "warnings": []},
                ))
                stack.enter_context(mock.patch.object(
                    validate_site, "_last_owner_confirmed_identity_snapshot",
                    return_value=(None, None),
                ))
                for name, value in clean_checks.items():
                    stack.enter_context(
                        mock.patch.object(validate_site, name, return_value=value)
                    )
                clock = stack.enter_context(
                    mock.patch.object(validate_site, "datetime", wraps=datetime)
                )
                clock.now.side_effect = [
                    datetime(2026, 9, 10, 17, 0, tzinfo=timezone.utc),
                    datetime(2026, 9, 10, 17, 5, tzinfo=timezone.utc),
                ]
                calendar = stack.enter_context(mock.patch.object(validate_site, "date"))
                calendar.today.return_value = date(2026, 9, 10)
                creation_error = OSError("fixture first-report temporary file creation failed")
                self.assertFalse(audit_dir.exists())

                # Keep main, serialization and cleanup real; fail only creation.
                with mock.patch.object(
                    validate_site.tempfile, "NamedTemporaryFile",
                    side_effect=creation_error,
                ) as staging:
                    with self.assertRaises(OSError) as raised:
                        validate_site.main(validated_commit=validated_commit)
                    self.assertIs(raised.exception, creation_error)
                    staging.assert_called_once_with(
                        mode="w", encoding="utf-8", dir=audit_dir,
                        prefix=f".{report_path.name}.", suffix=".tmp", delete=False,
                    )
                self.assertFalse(report_path.exists())
                self.assertEqual(set(audit_dir.iterdir()), set())
                output.assert_not_called()

                # Retry on the same date without injection, using fresh findings.
                finding = "retry issue with valid Unicode: café"
                warning = "retry warning"
                page_check.side_effect = lambda *_: {
                    "issues": [finding], "warnings": [warning],
                }
                self.assertEqual(
                    validate_site.main(validated_commit=validated_commit), 1
                )
                saved_bytes = report_path.read_bytes()
                self.assertEqual(json.loads(saved_bytes), {
                    "generated_at": "2026-09-10T17:05:00Z",
                    "run_date": "2026-09-10",
                    "report_type": "site-validation",
                    "provenance": {"validated_commit": validated_commit},
                    "scanned": 1,
                    "total_issues": 1,
                    "total_warnings": 1,
                    "pages": [{
                        "issues": [finding], "warnings": [warning], "path": "index.html",
                    }],
                    "global_issues": [],
                    "global_warnings": [],
                    "organization_identity_issues": [],
                })
                self.assertIn(finding.encode("utf-8"), saved_bytes)
                self.assertEqual(set(audit_dir.iterdir()), {report_path})
                output.assert_any_call("  issues:   1")
                output.assert_any_call("  warnings: 1")
                self.assertEqual(
                    page_check.call_args_list,
                    [mock.call(Path("index.html"), page_html)] * 2,
                )
                self.assertEqual(clock.now.call_args_list, [mock.call(timezone.utc)] * 2)

    def test_main_recovers_after_partial_first_report_write_on_same_day(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "assets").mkdir()
            page_path = root / "index.html"
            page_html = "<!doctype html>"
            page_path.write_text(page_html, encoding="utf-8")
            audit_dir = root / "assets" / "audit"
            report_path = audit_dir / "validation-report-2026-09-10.json"
            validated_commit = "abcdef0123456789abcdef0123456789abcdef01"
            clean_checks = {
                "_check_organization_identity_approval": [],
                "_check_css_lines_drift": None,
                "_check_stat_markers_drift": [],
                "_check_adr_index_sync": None,
                "_check_scripts_py_drift": None,
                "_check_scripts_non_py_drift": None,
                "_check_og_image_alt_drift": [],
                "_check_sparkle_drift": [],
                "_check_glee_dark_coverage": [],
                "_check_css_token_drift": [],
                "_check_template_metadata": [],
                "_check_offline_shell": [],
                "_check_mermaid_version_pin": [],
                "_check_mermaid_csp_alignment": [],
            }
            expected_report = {
                "generated_at": "2026-09-10T17:00:00Z",
                "run_date": "2026-09-10",
                "report_type": "site-validation",
                "provenance": {"validated_commit": validated_commit},
                "scanned": 1,
                "total_issues": 0,
                "total_warnings": 0,
                "pages": [{"issues": [], "warnings": [], "path": "index.html"}],
                "global_issues": [],
                "global_warnings": [],
                "organization_identity_issues": [],
            }
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(validate_site, "ROOT", root))
                output = stack.enter_context(mock.patch("builtins.print"))
                stack.enter_context(
                    mock.patch.object(
                        validate_site, "collect_html_files", return_value=[page_path]
                    )
                )
                page_check = stack.enter_context(
                    mock.patch.object(
                        validate_site, "check_page",
                        side_effect=lambda *_: {"issues": [], "warnings": []},
                    )
                )
                stack.enter_context(
                    mock.patch.object(
                        validate_site, "_last_owner_confirmed_identity_snapshot",
                        return_value=(None, None),
                    )
                )
                for name, value in clean_checks.items():
                    stack.enter_context(
                        mock.patch.object(validate_site, name, return_value=value)
                    )
                clock = stack.enter_context(
                    mock.patch.object(validate_site, "datetime", wraps=datetime)
                )
                clock.now.side_effect = [
                    datetime(2026, 9, 10, 17, 0, tzinfo=timezone.utc),
                    datetime(2026, 9, 10, 17, 5, tzinfo=timezone.utc),
                ]
                calendar = stack.enter_context(mock.patch.object(validate_site, "date"))
                calendar.today.return_value = date(2026, 9, 10)
                save_error = OSError("fixture first-report partial write failed")
                real_temporary_file = tempfile.NamedTemporaryFile
                staged_files = []
                self.assertFalse(audit_dir.exists())

                def stage_partial_file(*args, **kwargs):
                    temporary = real_temporary_file(*args, **kwargs)
                    staged_files.append(temporary)
                    staged_path = Path(temporary.name)
                    self.assertEqual(staged_path.parent, audit_dir)
                    self.assertNotEqual(staged_path, report_path)
                    real_write = temporary.write

                    def partial_write(content):
                        self.assertEqual(json.loads(content), expected_report)
                        self.assertEqual(
                            content, json.dumps(expected_report, indent=2, ensure_ascii=False)
                        )
                        real_write(content[:20])
                        temporary.flush()
                        self.assertEqual(
                            staged_path.read_text(encoding="utf-8"), content[:20]
                        )
                        self.assertFalse(report_path.exists())
                        self.assertEqual(set(audit_dir.iterdir()), {staged_path})
                        raise save_error

                    temporary.write = mock.Mock(side_effect=partial_write)
                    return temporary

                # Keep main, JSON serialization and file creation real; only the
                # first staged write fails after a prefix reaches the filesystem.
                with mock.patch.object(
                    validate_site.tempfile, "NamedTemporaryFile",
                    side_effect=stage_partial_file,
                ) as staging:
                    with self.assertRaises(OSError) as raised:
                        validate_site.main(validated_commit=validated_commit)
                    self.assertIs(raised.exception, save_error)
                    staging.assert_called_once_with(
                        mode="w", encoding="utf-8", dir=audit_dir,
                        prefix=f".{report_path.name}.", suffix=".tmp", delete=False,
                    )
                self.assertEqual(len(staged_files), 1)
                staged_file = staged_files[0]
                staged_file.write.assert_called_once()
                self.assertTrue(staged_file.closed)
                self.assertFalse(Path(staged_file.name).exists())
                self.assertFalse(report_path.exists())
                self.assertEqual(set(audit_dir.iterdir()), set())
                output.assert_not_called()

                # Retry the first-ever report on the same day with the injection
                # removed. A fresh warning must survive real UTF-8 serialization.
                finding = "retry warning with valid Unicode: café"
                page_check.side_effect = lambda *_: {
                    "issues": [], "warnings": [finding]
                }
                with mock.patch.object(
                    validate_site.tempfile, "NamedTemporaryFile",
                    wraps=real_temporary_file,
                ) as staging:
                    self.assertEqual(
                        validate_site.main(validated_commit=validated_commit), 0
                    )
                    staging.assert_called_once_with(
                        mode="w", encoding="utf-8", dir=audit_dir,
                        prefix=f".{report_path.name}.", suffix=".tmp", delete=False,
                    )
                saved_bytes = report_path.read_bytes()
                self.assertEqual(
                    json.loads(saved_bytes),
                    {
                        **expected_report,
                        "generated_at": "2026-09-10T17:05:00Z",
                        "total_warnings": 1,
                        "pages": [{
                            "issues": [], "warnings": [finding], "path": "index.html",
                        }],
                    },
                )
                self.assertIn(finding.encode("utf-8"), saved_bytes)
                self.assertFalse(Path(staged_file.name).exists())
                self.assertEqual(set(audit_dir.iterdir()), {report_path})
                output.assert_any_call("  issues:   0")
                output.assert_any_call("  warnings: 1")
                self.assertEqual(
                    page_check.call_args_list,
                    [mock.call(Path("index.html"), page_html)] * 2,
                )
                self.assertEqual(clock.now.call_args_list, [mock.call(timezone.utc)] * 2)

    def test_main_recovers_after_first_report_flush_or_close_failure_on_same_day(self):
        for failure in ("flush", "close"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "assets").mkdir()
                page_path = root / "index.html"
                page_html = "<!doctype html>"
                page_path.write_text(page_html, encoding="utf-8")
                audit_dir = root / "assets" / "audit"
                report_path = audit_dir / "validation-report-2026-09-10.json"
                validated_commit = "abcdef0123456789abcdef0123456789abcdef01"
                clean_checks = {
                    "_check_organization_identity_approval": [],
                    "_check_css_lines_drift": None,
                    "_check_stat_markers_drift": [],
                    "_check_adr_index_sync": None,
                    "_check_scripts_py_drift": None,
                    "_check_scripts_non_py_drift": None,
                    "_check_og_image_alt_drift": [],
                    "_check_sparkle_drift": [],
                    "_check_glee_dark_coverage": [],
                    "_check_css_token_drift": [],
                    "_check_template_metadata": [],
                    "_check_offline_shell": [],
                    "_check_mermaid_version_pin": [],
                    "_check_mermaid_csp_alignment": [],
                }
                expected_report = {
                    "generated_at": "2026-09-10T17:00:00Z",
                    "run_date": "2026-09-10",
                    "report_type": "site-validation",
                    "provenance": {"validated_commit": validated_commit},
                    "scanned": 1,
                    "total_issues": 0,
                    "total_warnings": 0,
                    "pages": [{"issues": [], "warnings": [], "path": "index.html"}],
                    "global_issues": [],
                    "global_warnings": [],
                    "organization_identity_issues": [],
                }
                save_error = OSError(f"fixture first-report {failure} failed")
                real_temporary_file = tempfile.NamedTemporaryFile
                staged_files = []

                class ExitFailureFile:
                    """Delegate staging I/O, injecting only the exit failure."""

                    def __init__(self, temporary):
                        self.temporary = temporary
                        self.name = temporary.name
                        self.write = mock.Mock(wraps=temporary.write)
                        self.flush = mock.Mock(
                            side_effect=save_error if failure == "flush" else temporary.flush
                        )
                        self.close = mock.Mock(side_effect=self.close_file)

                    def close_file(self):
                        # Always release the real handle, including on flush failure.
                        self.temporary.close()
                        if failure == "close":
                            raise save_error

                    def __enter__(self):
                        return self

                    def __exit__(self, exc_type, exc_value, traceback):
                        try:
                            self.flush()
                        finally:
                            self.close()

                def stage_file(*args, **kwargs):
                    staged = ExitFailureFile(real_temporary_file(*args, **kwargs))
                    staged_files.append(staged)
                    self.assertEqual(Path(staged.name).parent, audit_dir)
                    self.assertNotEqual(Path(staged.name), report_path)
                    return staged

                with ExitStack() as stack:
                    stack.enter_context(mock.patch.object(validate_site, "ROOT", root))
                    output = stack.enter_context(mock.patch("builtins.print"))
                    stack.enter_context(mock.patch.object(
                        validate_site, "collect_html_files", return_value=[page_path]
                    ))
                    page_check = stack.enter_context(mock.patch.object(
                        validate_site, "check_page",
                        side_effect=lambda *_: {"issues": [], "warnings": []},
                    ))
                    stack.enter_context(mock.patch.object(
                        validate_site, "_last_owner_confirmed_identity_snapshot",
                        return_value=(None, None),
                    ))
                    for name, value in clean_checks.items():
                        stack.enter_context(
                            mock.patch.object(validate_site, name, return_value=value)
                        )
                    clock = stack.enter_context(
                        mock.patch.object(validate_site, "datetime", wraps=datetime)
                    )
                    clock.now.side_effect = [
                        datetime(2026, 9, 10, 17, 0, tzinfo=timezone.utc),
                        datetime(2026, 9, 10, 17, 5, tzinfo=timezone.utc),
                    ]
                    calendar = stack.enter_context(mock.patch.object(validate_site, "date"))
                    calendar.today.return_value = date(2026, 9, 10)
                    self.assertFalse(audit_dir.exists())

                    # Main, serialization, staging writes and cleanup stay real.
                    with mock.patch.object(
                        validate_site.tempfile, "NamedTemporaryFile", side_effect=stage_file
                    ) as staging:
                        with self.assertRaises(OSError) as raised:
                            validate_site.main(validated_commit=validated_commit)
                        self.assertIs(raised.exception, save_error)
                        staging.assert_called_once_with(
                            mode="w", encoding="utf-8", dir=audit_dir,
                            prefix=f".{report_path.name}.", suffix=".tmp", delete=False,
                        )
                    self.assertEqual(len(staged_files), 1)
                    staged = staged_files[0]
                    staged.write.assert_called_once_with(
                        json.dumps(expected_report, indent=2, ensure_ascii=False)
                    )
                    staged.flush.assert_called_once_with()
                    staged.close.assert_called_once_with()
                    self.assertTrue(staged.temporary.closed)
                    self.assertFalse(Path(staged.name).exists())
                    self.assertFalse(report_path.exists())
                    self.assertEqual(set(audit_dir.iterdir()), set())
                    output.assert_not_called()

                    # Remove the injection and retry with new blocking findings.
                    finding = "retry issue with valid Unicode: café"
                    page_check.side_effect = lambda *_: {
                        "issues": [finding], "warnings": []
                    }
                    self.assertEqual(
                        validate_site.main(validated_commit=validated_commit), 1
                    )
                    saved_bytes = report_path.read_bytes()
                    self.assertEqual(json.loads(saved_bytes), {
                        **expected_report,
                        "generated_at": "2026-09-10T17:05:00Z",
                        "total_issues": 1,
                        "pages": [{
                            "issues": [finding], "warnings": [], "path": "index.html",
                        }],
                    })
                    self.assertIn(finding.encode("utf-8"), saved_bytes)
                    self.assertFalse(Path(staged.name).exists())
                    self.assertEqual(set(audit_dir.iterdir()), {report_path})
                    output.assert_any_call("  issues:   1")
                    output.assert_any_call("  warnings: 0")
                    self.assertEqual(
                        page_check.call_args_list,
                        [mock.call(Path("index.html"), page_html)] * 2,
                    )
                    self.assertEqual(clock.now.call_args_list, [mock.call(timezone.utc)] * 2)

    def test_main_recovers_after_unencodable_finding_and_preserves_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "assets").mkdir()
            page_path = root / "index.html"
            page_html = "<!doctype html>"
            page_path.write_text(page_html, encoding="utf-8")
            audit_dir = root / "assets" / "audit"
            historical_path = audit_dir / "validation-report-2026-09-10.json"
            same_day_path = audit_dir / "validation-report-2026-09-11.json"
            validated_commit = "abcdef0123456789abcdef0123456789abcdef01"
            clean_checks = {
                "_check_organization_identity_approval": [],
                "_check_css_lines_drift": None,
                "_check_stat_markers_drift": [],
                "_check_adr_index_sync": None,
                "_check_scripts_py_drift": None,
                "_check_scripts_non_py_drift": None,
                "_check_og_image_alt_drift": [],
                "_check_sparkle_drift": [],
                "_check_glee_dark_coverage": [],
                "_check_css_token_drift": [],
                "_check_template_metadata": [],
                "_check_offline_shell": [],
                "_check_mermaid_version_pin": [],
                "_check_mermaid_csp_alignment": [],
            }
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(validate_site, "ROOT", root))
                # Isolate console encoding so the failure must come from UTF-8 staging.
                output = stack.enter_context(mock.patch("builtins.print"))
                stack.enter_context(
                    mock.patch.object(
                        validate_site, "collect_html_files", return_value=[page_path]
                    )
                )
                page_check = stack.enter_context(
                    mock.patch.object(
                        validate_site,
                        "check_page",
                        side_effect=lambda *_: {"issues": [], "warnings": []},
                    )
                )
                stack.enter_context(
                    mock.patch.object(
                        validate_site,
                        "_last_owner_confirmed_identity_snapshot",
                        return_value=(None, None),
                    )
                )
                for name, value in clean_checks.items():
                    stack.enter_context(
                        mock.patch.object(validate_site, name, return_value=value)
                    )
                clock = stack.enter_context(
                    mock.patch.object(validate_site, "datetime", wraps=datetime)
                )
                clock.now.side_effect = [
                    datetime(2026, 9, 10, 17, 0, tzinfo=timezone.utc),
                    datetime(2026, 9, 11, 17, 5, tzinfo=timezone.utc),
                    datetime(2026, 9, 11, 17, 10, tzinfo=timezone.utc),
                    datetime(2026, 9, 11, 17, 15, tzinfo=timezone.utc),
                ]
                calendar = stack.enter_context(mock.patch.object(validate_site, "date"))
                for day in (date(2026, 9, 10), date(2026, 9, 11)):
                    calendar.today.return_value = day
                    self.assertEqual(
                        validate_site.main(validated_commit=validated_commit), 0
                    )
                evidence = {
                    path: path.read_bytes()
                    for path in (historical_path, same_day_path)
                }
                for path, original_bytes in evidence.items():
                    report = json.loads(original_bytes)
                    self.assertEqual(report["run_date"], path.stem.removeprefix("validation-report-"))
                    self.assertEqual(report["total_issues"], 0)
                    self.assertEqual(report["total_warnings"], 0)

                finding = "changed warning with lone surrogate: \ud800"
                # A warning-only run would otherwise return success; keep results fresh.
                page_check.side_effect = lambda *_: {
                    "issues": [], "warnings": [finding]
                }
                output.reset_mock()
                # Observe the real temporary file; do not inject a write exception.
                with mock.patch.object(
                    validate_site.tempfile,
                    "NamedTemporaryFile",
                    wraps=tempfile.NamedTemporaryFile,
                ) as staging:
                    with self.assertRaises(UnicodeEncodeError) as raised:
                        validate_site.main(validated_commit=validated_commit)
                    staging.assert_called_once_with(
                        mode="w", encoding="utf-8", dir=audit_dir,
                        prefix=f".{same_day_path.name}.", suffix=".tmp", delete=False,
                    )
                error = raised.exception
                self.assertEqual(error.encoding, "utf-8")
                self.assertIn(finding, error.object)
                self.assertEqual(error.object[error.start:error.end], "\ud800")
                for path, original_bytes in evidence.items():
                    self.assertEqual(path.read_bytes(), original_bytes)
                self.assertEqual(set(audit_dir.iterdir()), set(evidence))
                output.assert_not_called()

                # Correct the finding and retry main on the same day, with real
                # serialization and staging rather than calling the writer directly.
                finding = "corrected warning with valid Unicode: café"
                with mock.patch.object(
                    validate_site.tempfile,
                    "NamedTemporaryFile",
                    wraps=tempfile.NamedTemporaryFile,
                ) as staging:
                    self.assertEqual(
                        validate_site.main(validated_commit=validated_commit), 0
                    )
                    staging.assert_called_once_with(
                        mode="w", encoding="utf-8", dir=audit_dir,
                        prefix=f".{same_day_path.name}.", suffix=".tmp", delete=False,
                    )
                corrected_bytes = same_day_path.read_bytes()
                expected_report = json.loads(evidence[same_day_path])
                expected_report["generated_at"] = "2026-09-11T17:15:00Z"
                expected_report["total_warnings"] = 1
                expected_report["pages"][0]["warnings"] = [finding]
                self.assertNotEqual(corrected_bytes, evidence[same_day_path])
                self.assertEqual(json.loads(corrected_bytes), expected_report)
                self.assertIn(finding.encode("utf-8"), corrected_bytes)
                self.assertEqual(historical_path.read_bytes(), evidence[historical_path])
                self.assertEqual(set(audit_dir.iterdir()), set(evidence))
                output.assert_any_call("  issues:   0")
                output.assert_any_call("  warnings: 1")
                self.assertEqual(
                    page_check.call_args_list,
                    [mock.call(Path("index.html"), page_html)] * 4,
                )
                self.assertEqual(clock.now.call_args_list, [mock.call(timezone.utc)] * 4)

    def test_main_propagates_cleanup_failure_after_successful_report_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "assets").mkdir()
            page_path = root / "index.html"
            page_path.write_text("<!doctype html>", encoding="utf-8")
            audit_dir = root / "assets" / "audit"
            audit_dir.mkdir()
            report_path = audit_dir / "validation-report-2026-09-10.json"
            historical_evidence = {
                audit_dir / "validation-report-2026-09-09.json":
                    b'{"generated_at": "2026-09-09T17:00:00Z"}\n',
                audit_dir / "validation-report-2026-09-08.json":
                    b'{"generated_at": "2026-09-08T17:00:00Z"}\n',
            }
            for path, content in historical_evidence.items():
                path.write_bytes(content)
            original_commit = "abcdef0123456789abcdef0123456789abcdef01"
            changed_commit = "123456789abcdef0123456789abcdef0123456789"
            clean_checks = {
                "_check_organization_identity_approval": [],
                "_check_css_lines_drift": None,
                "_check_stat_markers_drift": [],
                "_check_adr_index_sync": None,
                "_check_scripts_py_drift": None,
                "_check_scripts_non_py_drift": None,
                "_check_og_image_alt_drift": [],
                "_check_sparkle_drift": [],
                "_check_glee_dark_coverage": [],
                "_check_css_token_drift": [],
                "_check_template_metadata": [],
                "_check_offline_shell": [],
                "_check_mermaid_version_pin": [],
                "_check_mermaid_csp_alignment": [],
            }
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(validate_site, "ROOT", root))
                output = stack.enter_context(mock.patch("builtins.print"))
                stack.enter_context(
                    mock.patch.object(
                        validate_site, "collect_html_files", return_value=[page_path]
                    )
                )
                stack.enter_context(
                    mock.patch.object(
                        validate_site, "check_page",
                        side_effect=lambda *_: {"issues": [], "warnings": []},
                    )
                )
                stack.enter_context(
                    mock.patch.object(
                        validate_site, "_last_owner_confirmed_identity_snapshot",
                        return_value=(None, None),
                    )
                )
                for name, value in clean_checks.items():
                    stack.enter_context(
                        mock.patch.object(validate_site, name, return_value=value)
                    )
                clock = stack.enter_context(
                    mock.patch.object(validate_site, "datetime", wraps=datetime)
                )
                clock.now.side_effect = [
                    datetime(2026, 9, 10, 17, 0, tzinfo=timezone.utc),
                    datetime(2026, 9, 10, 17, 5, tzinfo=timezone.utc),
                ]
                calendar = stack.enter_context(mock.patch.object(validate_site, "date"))
                calendar.today.return_value = date(2026, 9, 10)

                self.assertEqual(validate_site.main(validated_commit=original_commit), 0)
                original_bytes = report_path.read_bytes()
                original_report = json.loads(original_bytes)
                expected_report = {
                    **original_report,
                    "generated_at": "2026-09-10T17:05:00Z",
                    "provenance": {"validated_commit": changed_commit},
                }
                serialized = json.dumps(
                    expected_report, indent=2, ensure_ascii=False
                ).encode("utf-8")
                output.reset_mock()
                cleanup_error = OSError("fixture cleanup failed after successful save")
                real_replace = Path.replace
                staged_paths = []

                def commit_report(path, destination):
                    self.assertEqual(destination, report_path)
                    self.assertEqual(path.parent, audit_dir)
                    self.assertNotEqual(path, report_path)
                    self.assertNotIn(path, historical_evidence)
                    self.assertEqual(path.read_text(encoding="utf-8"), serialized.decode("utf-8"))
                    staged_paths.append(path)
                    return real_replace(path, destination)

                def fail_cleanup(path, *, missing_ok=False):
                    self.assertEqual(path, staged_paths[0])
                    self.assertTrue(missing_ok)
                    self.assertFalse(path.exists())
                    self.assertEqual(report_path.read_text(encoding="utf-8"), serialized.decode("utf-8"))
                    raise cleanup_error

                # Keep main and its writer real; fail only cleanup after replacement.
                with mock.patch.object(
                    Path, "replace", autospec=True, side_effect=commit_report
                ) as replace, mock.patch.object(
                    Path, "unlink", autospec=True, side_effect=fail_cleanup
                ) as unlink:
                    with self.assertRaises(OSError) as raised:
                        validate_site.main(validated_commit=changed_commit)
                    self.assertIs(raised.exception, cleanup_error)
                    self.assertIsNone(raised.exception.__cause__)
                    self.assertEqual(len(staged_paths), 1)
                    staged_path = staged_paths[0]
                    replace.assert_called_once_with(staged_path, report_path)
                    unlink.assert_called_once_with(staged_path, missing_ok=True)

                output.assert_not_called()
                self.assertNotEqual(report_path.read_bytes(), original_bytes)
                self.assertEqual(report_path.read_text(encoding="utf-8"), serialized.decode("utf-8"))
                saved_report = json.loads(report_path.read_bytes())
                self.assertEqual(saved_report, expected_report)
                self.assertEqual(saved_report["report_type"], "site-validation")
                self.assertEqual(saved_report["run_date"], "2026-09-10")
                self.assertEqual(saved_report["scanned"], 1)
                self.assertEqual(saved_report["total_issues"], 0)
                self.assertEqual(saved_report["total_warnings"], 0)
                for path, content in historical_evidence.items():
                    self.assertEqual(path.read_bytes(), content)
                self.assertFalse(staged_path.exists())
                self.assertEqual(
                    set(audit_dir.iterdir()), set(historical_evidence) | {report_path}
                )

    def test_temporary_file_creation_failure_leaves_first_report_absent(self):
        with tempfile.TemporaryDirectory() as directory:
            audit_dir = Path(directory) / "assets" / "audit"
            audit_dir.mkdir(parents=True)
            report_path = audit_dir / "validation-report-2026-09-10.json"
            historical_evidence = {
                audit_dir / "validation-report-2026-09-09.json":
                    b'{"generated_at": "2026-09-09T17:00:00Z"}\n',
                audit_dir / "validation-report-2026-09-08.json":
                    b'{"generated_at": "2026-09-08T17:00:00Z"}\n',
            }
            for path, content in historical_evidence.items():
                path.write_bytes(content)
            report = {
                "generated_at": "2026-09-10T17:00:00Z",
                "run_date": "2026-09-10",
                "total_issues": 0,
            }
            self.assertFalse(report_path.exists())
            creation_error = OSError("fixture first-report temporary-file creation failed")

            with mock.patch.object(
                validate_site.tempfile, "NamedTemporaryFile", side_effect=creation_error
            ) as create_temporary, mock.patch.object(
                Path, "replace", autospec=True
            ) as replace, mock.patch.object(
                Path, "unlink", autospec=True
            ) as unlink:
                with self.assertRaises(OSError) as raised:
                    validate_site._write_validation_report(report_path, report)
                self.assertIs(raised.exception, creation_error)
                create_temporary.assert_called_once_with(
                    mode="w", encoding="utf-8", dir=audit_dir,
                    prefix=f".{report_path.name}.", suffix=".tmp", delete=False,
                )
                replace.assert_not_called()
                unlink.assert_not_called()

            self.assertFalse(report_path.exists())
            for path, content in historical_evidence.items():
                self.assertEqual(path.read_bytes(), content)
            self.assertEqual(set(audit_dir.iterdir()), set(historical_evidence))

    def test_temporary_file_creation_failure_preserves_existing_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            audit_dir = Path(directory) / "assets" / "audit"
            audit_dir.mkdir(parents=True)
            report_path = audit_dir / "validation-report-2026-09-10.json"
            original = {
                "generated_at": "2026-09-10T17:00:00Z",
                "run_date": "2026-09-10",
                "total_issues": 0,
            }
            evidence = {
                report_path: (json.dumps(original) + "\n").encode("utf-8"),
                audit_dir / "validation-report-2026-09-09.json":
                    b'{"generated_at": "2026-09-09T17:00:00Z"}\n',
                audit_dir / "validation-report-2026-09-08.json":
                    b'{"generated_at": "2026-09-08T17:00:00Z"}\n',
            }
            for path, content in evidence.items():
                path.write_bytes(content)
            changed = {
                **original, "generated_at": "2026-09-10T17:05:00Z",
                "total_issues": 1,
            }
            creation_error = OSError("fixture temporary-file creation failed")

            # Fail before the writer can assign a staged path.
            with mock.patch.object(
                validate_site.tempfile, "NamedTemporaryFile", side_effect=creation_error
            ) as create_temporary, mock.patch.object(
                Path, "replace", autospec=True
            ) as replace, mock.patch.object(
                Path, "unlink", autospec=True
            ) as unlink:
                with self.assertRaises(OSError) as raised:
                    validate_site._write_validation_report(report_path, changed)
                self.assertIs(raised.exception, creation_error)
                create_temporary.assert_called_once_with(
                    mode="w", encoding="utf-8", dir=audit_dir,
                    prefix=f".{report_path.name}.", suffix=".tmp", delete=False,
                )
                replace.assert_not_called()
                unlink.assert_not_called()

            for path, content in evidence.items():
                self.assertEqual(path.read_bytes(), content)
            self.assertEqual(set(audit_dir.iterdir()), set(evidence))

    def test_serialization_failure_preserves_evidence_and_allows_corrected_retry(self):
        circular_issues = []
        circular_issues.append(circular_issues)
        cases = (
            ("non-serializable value", {object()}, TypeError,
             "Object of type set is not JSON serializable"),
            ("circular reference", circular_issues, ValueError,
             "Circular reference detected"),
        )
        for failure, invalid_issues, error_type, message in cases:
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                audit_dir = Path(directory) / "assets" / "audit"
                audit_dir.mkdir(parents=True)
                report_path = audit_dir / "validation-report-2026-09-10.json"
                original = {
                    "generated_at": "2026-09-10T17:00:00Z",
                    "run_date": "2026-09-10",
                    "total_issues": 0,
                }
                evidence = {
                    report_path: (json.dumps(original) + "\n").encode("utf-8"),
                    audit_dir / "validation-report-2026-09-09.json":
                        b'{"generated_at": "2026-09-09T17:00:00Z"}\n',
                    audit_dir / "validation-report-2026-09-08.json":
                        b'{"generated_at": "2026-09-08T17:00:00Z"}\n',
                }
                for path, content in evidence.items():
                    path.write_bytes(content)
                changed = {
                    **original, "generated_at": "2026-09-10T17:05:00Z",
                    "total_issues": 1,
                    "global_issues": ["Changed validation finding"],
                }
                invalid = {**changed, "global_issues": invalid_issues}

                # Let the real encoder reject the payload before any save operation.
                with mock.patch.object(
                    validate_site.json, "dumps", wraps=json.dumps
                ) as dumps, mock.patch.object(
                    validate_site.tempfile, "NamedTemporaryFile"
                ) as create_temporary, mock.patch.object(
                    Path, "replace", autospec=True
                ) as replace, mock.patch.object(
                    Path, "unlink", autospec=True
                ) as unlink:
                    with self.assertRaisesRegex(error_type, message):
                        validate_site._write_validation_report(report_path, invalid)
                    dumps.assert_called_once_with(invalid, indent=2, ensure_ascii=False)
                    create_temporary.assert_not_called()
                    replace.assert_not_called()
                    unlink.assert_not_called()

                for path, content in evidence.items():
                    self.assertEqual(path.read_bytes(), content)
                self.assertEqual(set(audit_dir.iterdir()), set(evidence))

                # Correct the payload and publish to the same destination with real I/O.
                self.assertIs(
                    validate_site._write_validation_report(report_path, changed), True
                )
                self.assertNotEqual(report_path.read_bytes(), evidence[report_path])
                self.assertEqual(
                    report_path.read_text(encoding="utf-8"),
                    json.dumps(changed, indent=2, ensure_ascii=False),
                )
                self.assertEqual(json.loads(report_path.read_bytes()), changed)
                for path, content in evidence.items():
                    if path != report_path:
                        self.assertEqual(path.read_bytes(), content)
                self.assertEqual(set(audit_dir.iterdir()), set(evidence))

    def test_utf8_encoding_failure_preserves_evidence_and_cleans_staged_file(self):
        with tempfile.TemporaryDirectory() as directory:
            audit_dir = Path(directory) / "assets" / "audit"
            audit_dir.mkdir(parents=True)
            report_path = audit_dir / "validation-report-2026-09-10.json"
            original = {
                "generated_at": "2026-09-10T17:00:00Z",
                "run_date": "2026-09-10",
                "total_issues": 0,
            }
            evidence = {
                report_path: (json.dumps(original) + "\n").encode("utf-8"),
                audit_dir / "validation-report-2026-09-09.json":
                    b'{"generated_at": "2026-09-09T17:00:00Z"}\n',
                audit_dir / "validation-report-2026-09-08.json":
                    b'{"generated_at": "2026-09-08T17:00:00Z"}\n',
            }
            for path, content in evidence.items():
                path.write_bytes(content)
            invalid = {
                **original, "generated_at": "2026-09-10T17:05:00Z",
                "total_issues": 1,
                "global_issues": ["Finding with lone surrogate: \ud800"],
            }
            # JSON serialization succeeds; the real UTF-8 text write rejects it.
            serialized = json.dumps(invalid, indent=2, ensure_ascii=False)
            self.assertIn("\ud800", serialized)
            staged_files = []
            encoding_errors = []
            real_temporary_file = tempfile.NamedTemporaryFile
            real_unlink = Path.unlink

            def stage_file(*args, **kwargs):
                temporary = real_temporary_file(*args, **kwargs)
                staged_files.append(temporary)
                staged_path = Path(temporary.name)
                self.assertEqual(staged_path.parent, audit_dir)
                self.assertNotIn(staged_path, evidence)
                real_write = temporary.write

                def observe_write(content):
                    self.assertEqual(content, serialized)
                    try:
                        return real_write(content)
                    except UnicodeEncodeError as error:
                        encoding_errors.append(error)
                        raise

                temporary.write = mock.Mock(side_effect=observe_write)
                return temporary

            def cleanup(path, *, missing_ok=False):
                self.assertEqual(path, Path(staged_files[0].name))
                self.assertTrue(staged_files[0].closed)
                self.assertTrue(path.exists())
                return real_unlink(path, missing_ok=missing_ok)

            with mock.patch.object(
                validate_site.json, "dumps", wraps=json.dumps
            ) as dumps, mock.patch.object(
                validate_site.tempfile, "NamedTemporaryFile", side_effect=stage_file
            ) as create_temporary, mock.patch.object(
                Path, "replace", autospec=True
            ) as replace, mock.patch.object(
                Path, "unlink", autospec=True, side_effect=cleanup
            ) as unlink:
                with self.assertRaises(UnicodeEncodeError) as raised:
                    validate_site._write_validation_report(report_path, invalid)
                dumps.assert_called_once_with(invalid, indent=2, ensure_ascii=False)
                create_temporary.assert_called_once()
                self.assertEqual(len(staged_files), 1)
                self.assertEqual(len(encoding_errors), 1)
                self.assertIs(raised.exception, encoding_errors[0])
                self.assertEqual(raised.exception.encoding, "utf-8")
                # Windows text streams translate LF to CRLF before encoding.
                self.assertEqual(
                    raised.exception.object.replace("\r\n", "\n"), serialized
                )
                staged_path = Path(staged_files[0].name)
                staged_files[0].write.assert_called_once_with(serialized)
                replace.assert_not_called()
                unlink.assert_called_once_with(staged_path, missing_ok=True)

            self.assertFalse(staged_path.exists())
            for path, content in evidence.items():
                self.assertEqual(path.read_bytes(), content)
            self.assertEqual(set(audit_dir.iterdir()), set(evidence))

    def test_invalid_incoming_timestamp_rejected_even_when_payload_is_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            audit_dir = Path(directory) / "assets" / "audit"
            audit_dir.mkdir(parents=True)
            report_path = audit_dir / "validation-report-2026-09-10.json"
            original = {
                "generated_at": "2026-09-10T17:00:00Z",
                "run_date": "2026-09-10",
                "report_type": "site-validation",
                "scanned": 1,
                "total_issues": 0,
                "total_warnings": 0,
                "global_issues": [],
                "global_warnings": [],
                "pages": [{"issues": [], "warnings": [], "path": "index.html"}],
            }
            evidence = {
                report_path: (json.dumps(original) + "\n").encode("utf-8"),
                audit_dir / "validation-report-2026-09-09.json":
                    b'{"generated_at": "2026-09-09T17:00:00Z"}\n',
                audit_dir / "validation-report-2026-09-08.json":
                    b'{"generated_at": "2026-09-08T17:00:00Z"}\n',
            }
            for path, content in evidence.items():
                path.write_bytes(content)
            invalid = {**original, "generated_at": {object()}}

            # Timestamp metadata is ignored for idempotency, not JSON validation.
            with mock.patch.object(
                validate_site.json, "dumps", wraps=json.dumps
            ) as dumps, mock.patch.object(
                validate_site.tempfile, "NamedTemporaryFile"
            ) as create_temporary, mock.patch.object(
                Path, "replace", autospec=True
            ) as replace, mock.patch.object(
                Path, "unlink", autospec=True
            ) as unlink:
                with self.assertRaisesRegex(
                    TypeError, "Object of type set is not JSON serializable"
                ):
                    validate_site._write_validation_report(report_path, invalid)
                dumps.assert_called_once_with(invalid, indent=2, ensure_ascii=False)
                create_temporary.assert_not_called()
                replace.assert_not_called()
                unlink.assert_not_called()

            for path, content in evidence.items():
                self.assertEqual(path.read_bytes(), content)
            self.assertEqual(set(audit_dir.iterdir()), set(evidence))

    def test_first_save_serialization_failure_leaves_report_absent_and_allows_retry(self):
        circular_issues = []
        circular_issues.append(circular_issues)
        cases = (
            ("non-serializable value", {object()}, TypeError,
             "Object of type set is not JSON serializable"),
            ("circular reference", circular_issues, ValueError,
             "Circular reference detected"),
        )
        for failure, invalid_issues, error_type, message in cases:
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                audit_dir = Path(directory) / "assets" / "audit"
                audit_dir.mkdir(parents=True)
                report_path = audit_dir / "validation-report-2026-09-10.json"
                historical_evidence = {
                    audit_dir / "validation-report-2026-09-09.json":
                        b'{"generated_at": "2026-09-09T17:00:00Z"}\n',
                    audit_dir / "validation-report-2026-09-08.json":
                        b'{"generated_at": "2026-09-08T17:00:00Z"}\n',
                }
                for path, content in historical_evidence.items():
                    path.write_bytes(content)
                corrected = {
                    "generated_at": "2026-09-10T17:00:00Z",
                    "run_date": "2026-09-10",
                    "total_issues": 1,
                    "global_issues": ["Validation finding"],
                }
                invalid = {**corrected, "global_issues": invalid_issues}
                self.assertFalse(report_path.exists())

                # Use the real encoder, observing that rejection precedes staging.
                with mock.patch.object(
                    validate_site.json, "dumps", wraps=json.dumps
                ) as dumps, mock.patch.object(
                    validate_site.tempfile, "NamedTemporaryFile"
                ) as create_temporary, mock.patch.object(
                    Path, "replace", autospec=True
                ) as replace, mock.patch.object(
                    Path, "unlink", autospec=True
                ) as unlink:
                    with self.assertRaisesRegex(error_type, message):
                        validate_site._write_validation_report(report_path, invalid)
                    dumps.assert_called_once_with(invalid, indent=2, ensure_ascii=False)
                    create_temporary.assert_not_called()
                    replace.assert_not_called()
                    unlink.assert_not_called()

                self.assertFalse(report_path.exists())
                for path, content in historical_evidence.items():
                    self.assertEqual(path.read_bytes(), content)
                self.assertEqual(set(audit_dir.iterdir()), set(historical_evidence))

                # Publish the corrected payload to the same destination with real I/O.
                self.assertIs(
                    validate_site._write_validation_report(report_path, corrected), True
                )
                self.assertEqual(
                    report_path.read_text(encoding="utf-8"),
                    json.dumps(corrected, indent=2, ensure_ascii=False),
                )
                self.assertEqual(json.loads(report_path.read_bytes()), corrected)
                for path, content in historical_evidence.items():
                    self.assertEqual(path.read_bytes(), content)
                self.assertEqual(
                    set(audit_dir.iterdir()), set(historical_evidence) | {report_path}
                )

    def test_retry_after_failed_first_save_publishes_report_and_preserves_history(self):
        for failure in ("partial write", "replacement"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                audit_dir = Path(directory) / "assets" / "audit"
                audit_dir.mkdir(parents=True)
                report_path = audit_dir / "validation-report-2026-09-10.json"
                historical_evidence = {
                    audit_dir / "validation-report-2026-09-09.json":
                        b'{"generated_at": "2026-09-09T17:00:00Z"}\n',
                    audit_dir / "validation-report-2026-09-08.json":
                        b'{"generated_at": "2026-09-08T17:00:00Z"}\n',
                }
                for path, content in historical_evidence.items():
                    path.write_bytes(content)
                report = {
                    "generated_at": "2026-09-10T17:00:00Z",
                    "run_date": "2026-09-10",
                    "total_issues": 0,
                }
                serialized = json.dumps(report, indent=2, ensure_ascii=False)
                save_error = OSError(f"fixture first-report {failure} failed")
                staged_files = []
                real_temporary_file = tempfile.NamedTemporaryFile
                real_unlink = Path.unlink
                self.assertFalse(report_path.exists())

                def stage_file(*args, **kwargs):
                    temporary = real_temporary_file(*args, **kwargs)
                    staged_files.append(temporary)
                    staged_path = Path(temporary.name)
                    self.assertEqual(staged_path.parent, audit_dir)
                    self.assertNotIn(staged_path, historical_evidence)
                    self.assertNotEqual(staged_path, report_path)
                    if failure == "partial write":
                        real_write = temporary.write

                        def partial_write(content):
                            self.assertEqual(content, serialized)
                            real_write(content[:20])
                            temporary.flush()
                            self.assertEqual(
                                staged_path.read_text(encoding="utf-8"), serialized[:20]
                            )
                            self.assertFalse(report_path.exists())
                            raise save_error

                        temporary.write = mock.Mock(side_effect=partial_write)
                    return temporary

                def fail_replace(path, destination):
                    self.assertEqual(destination, report_path)
                    self.assertTrue(staged_files[0].closed)
                    self.assertEqual(path.read_text(encoding="utf-8"), serialized)
                    self.assertFalse(report_path.exists())
                    raise save_error

                def cleanup(path, *, missing_ok=False):
                    self.assertEqual(path, Path(staged_files[0].name))
                    self.assertTrue(staged_files[0].closed)
                    self.assertTrue(path.exists())
                    return real_unlink(path, missing_ok=missing_ok)

                # Exercise real staging and cleanup; only the save operation fails.
                with mock.patch.object(
                    validate_site.tempfile, "NamedTemporaryFile", side_effect=stage_file
                ), mock.patch.object(
                    Path, "replace", autospec=True, side_effect=fail_replace
                ) as replace, mock.patch.object(
                    Path, "unlink", autospec=True, side_effect=cleanup
                ) as unlink:
                    with self.assertRaises(OSError) as raised:
                        validate_site._write_validation_report(report_path, report)
                    self.assertIs(raised.exception, save_error)
                    self.assertEqual(len(staged_files), 1)
                    staged_path = Path(staged_files[0].name)
                    unlink.assert_called_once_with(staged_path, missing_ok=True)
                    if failure == "partial write":
                        replace.assert_not_called()
                    else:
                        replace.assert_called_once_with(staged_path, report_path)

                self.assertFalse(report_path.exists())
                self.assertFalse(staged_path.exists())
                for path, content in historical_evidence.items():
                    self.assertEqual(path.read_bytes(), content)
                self.assertEqual(set(audit_dir.iterdir()), set(historical_evidence))

                # Retry the same destination with all failure injections removed.
                self.assertIs(
                    validate_site._write_validation_report(report_path, report), True
                )
                self.assertEqual(report_path.read_text(encoding="utf-8"), serialized)
                self.assertEqual(
                    json.loads(report_path.read_text(encoding="utf-8")), report
                )
                self.assertFalse(staged_path.exists())
                for path, content in historical_evidence.items():
                    self.assertEqual(path.read_bytes(), content)
                self.assertEqual(
                    set(audit_dir.iterdir()), set(historical_evidence) | {report_path}
                )

    def test_retry_after_failed_update_replaces_same_day_and_preserves_history(self):
        for failure in ("partial write", "replacement"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                audit_dir = Path(directory) / "assets" / "audit"
                audit_dir.mkdir(parents=True)
                report_path = audit_dir / "validation-report-2026-09-10.json"
                original = {
                    "generated_at": "2026-09-10T17:00:00Z",
                    "run_date": "2026-09-10",
                    "total_issues": 0,
                }
                evidence = {
                    report_path: (json.dumps(original) + "\n").encode("utf-8"),
                    audit_dir / "validation-report-2026-09-09.json":
                        b'{"generated_at": "2026-09-09T17:00:00Z"}\n',
                    audit_dir / "validation-report-2026-09-08.json":
                        b'{"generated_at": "2026-09-08T17:00:00Z"}\n',
                }
                for path, content in evidence.items():
                    path.write_bytes(content)
                changed = {
                    **original, "generated_at": "2026-09-10T17:05:00Z",
                    "total_issues": 1,
                }
                serialized = json.dumps(changed, indent=2, ensure_ascii=False)
                save_error = OSError(f"fixture {failure} failed")
                staged_paths = []
                real_temporary_file = tempfile.NamedTemporaryFile
                real_unlink = Path.unlink

                def stage_file(*args, **kwargs):
                    temporary = real_temporary_file(*args, **kwargs)
                    staged_path = Path(temporary.name)
                    staged_paths.append(staged_path)
                    self.assertEqual(staged_path.parent, audit_dir)
                    self.assertNotIn(staged_path, evidence)
                    if failure == "partial write":
                        real_write = temporary.write

                        def partial_write(content):
                            real_write(content[:20])
                            temporary.flush()
                            self.assertEqual(staged_path.read_text(encoding="utf-8"), content[:20])
                            raise save_error

                        temporary.write = mock.Mock(side_effect=partial_write)
                    return temporary

                def fail_replace(path, destination):
                    self.assertEqual(destination, report_path)
                    self.assertEqual(path.read_text(encoding="utf-8"), serialized)
                    raise save_error

                with mock.patch.object(
                    validate_site.tempfile, "NamedTemporaryFile", side_effect=stage_file
                ), mock.patch.object(
                    Path, "replace", autospec=True, side_effect=fail_replace
                ) as replace, mock.patch.object(
                    Path, "unlink", autospec=True, side_effect=real_unlink
                ) as unlink:
                    with self.assertRaises(OSError) as raised:
                        validate_site._write_validation_report(report_path, changed)
                    self.assertIs(raised.exception, save_error)
                    self.assertEqual(len(staged_paths), 1)
                    staged_path = staged_paths[0]
                    unlink.assert_called_once_with(staged_path, missing_ok=True)
                    if failure == "partial write":
                        replace.assert_not_called()
                    else:
                        replace.assert_called_once_with(staged_path, report_path)

                self.assertFalse(staged_path.exists())
                for path, content in evidence.items():
                    self.assertEqual(path.read_bytes(), content)
                self.assertEqual(set(audit_dir.iterdir()), set(evidence))

                # Retry the changed payload at the same destination without injections.
                self.assertIs(
                    validate_site._write_validation_report(report_path, changed), True
                )
                self.assertEqual(report_path.read_text(encoding="utf-8"), serialized)
                self.assertEqual(
                    json.loads(report_path.read_text(encoding="utf-8")), changed
                )
                self.assertFalse(staged_path.exists())
                for path, content in evidence.items():
                    if path != report_path:
                        self.assertEqual(path.read_bytes(), content)
                self.assertEqual(set(audit_dir.iterdir()), set(evidence))

    def test_cleanup_failure_keeps_original_save_error_and_preserves_evidence(self):
        for failure in ("partial write", "replacement"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                audit_dir = Path(directory) / "assets" / "audit"
                audit_dir.mkdir(parents=True)
                report_path = audit_dir / "validation-report-2026-09-10.json"
                original = {
                    "generated_at": "2026-09-10T17:00:00Z",
                    "run_date": "2026-09-10",
                    "total_issues": 0,
                }
                evidence = {
                    report_path: (json.dumps(original) + "\n").encode("utf-8"),
                    audit_dir / "validation-report-2026-09-09.json":
                        b'{"generated_at": "2026-09-09T17:00:00Z"}\n',
                    audit_dir / "validation-report-2026-09-08.json":
                        b'{"generated_at": "2026-09-08T17:00:00Z"}\n',
                }
                for path, content in evidence.items():
                    path.write_bytes(content)
                changed = {
                    **original, "generated_at": "2026-09-10T17:05:00Z",
                    "total_issues": 1,
                }
                serialized = json.dumps(changed, indent=2, ensure_ascii=False)
                save_error = OSError(f"fixture {failure} failed")
                cleanup_error = OSError("fixture staged-file cleanup failed")
                staged_files = []
                real_temporary_file = tempfile.NamedTemporaryFile

                def stage_file(*args, **kwargs):
                    temporary = real_temporary_file(*args, **kwargs)
                    staged_files.append(temporary)
                    staged_path = Path(temporary.name)
                    self.assertEqual(staged_path.parent, audit_dir)
                    self.assertNotIn(staged_path, evidence)
                    if failure == "partial write":
                        real_write = temporary.write

                        def partial_write(content):
                            real_write(content[:20])
                            temporary.flush()
                            raise save_error

                        temporary.write = mock.Mock(side_effect=partial_write)
                    return temporary

                def fail_replace(path, destination):
                    self.assertEqual(destination, report_path)
                    self.assertEqual(path.read_text(encoding="utf-8"), serialized)
                    raise save_error

                def fail_cleanup(path, *, missing_ok=False):
                    self.assertEqual(path, Path(staged_files[0].name))
                    self.assertTrue(missing_ok)
                    self.assertTrue(staged_files[0].closed)
                    raise cleanup_error

                with mock.patch.object(
                    validate_site.tempfile, "NamedTemporaryFile", side_effect=stage_file
                ), mock.patch.object(
                    Path, "replace", autospec=True, side_effect=fail_replace
                ) as replace, mock.patch.object(
                    Path, "unlink", autospec=True, side_effect=fail_cleanup
                ) as unlink:
                    with self.assertRaises(OSError) as raised:
                        validate_site._write_validation_report(report_path, changed)
                    # The save failure is primary; cleanup remains explicitly chained.
                    self.assertIs(raised.exception, save_error)
                    self.assertIs(raised.exception.__cause__, cleanup_error)
                    self.assertEqual(len(staged_files), 1)
                    staged_path = Path(staged_files[0].name)
                    unlink.assert_called_once_with(staged_path, missing_ok=True)
                    if failure == "partial write":
                        replace.assert_not_called()
                    else:
                        replace.assert_called_once_with(staged_path, report_path)

                for path, content in evidence.items():
                    self.assertEqual(path.read_bytes(), content)
                # Failed cleanup leaves only the staged file, never damaged evidence.
                expected_staged = serialized[:20] if failure == "partial write" else serialized
                self.assertEqual(staged_path.read_text(encoding="utf-8"), expected_staged)
                self.assertEqual(set(audit_dir.iterdir()), set(evidence) | {staged_path})

    def test_cleanup_failure_after_successful_save_propagates_and_preserves_history(self):
        with tempfile.TemporaryDirectory() as directory:
            audit_dir = Path(directory) / "assets" / "audit"
            audit_dir.mkdir(parents=True)
            report_path = audit_dir / "validation-report-2026-09-10.json"
            original = {
                "generated_at": "2026-09-10T17:00:00Z",
                "run_date": "2026-09-10",
                "total_issues": 0,
            }
            report_path.write_bytes((json.dumps(original) + "\n").encode("utf-8"))
            historical_evidence = {
                audit_dir / "validation-report-2026-09-09.json":
                    b'{"generated_at": "2026-09-09T17:00:00Z"}\n',
                audit_dir / "validation-report-2026-09-08.json":
                    b'{"generated_at": "2026-09-08T17:00:00Z"}\n',
            }
            for path, content in historical_evidence.items():
                path.write_bytes(content)
            changed = {
                **original, "generated_at": "2026-09-10T17:05:00Z",
                "total_issues": 1,
            }
            serialized = json.dumps(changed, indent=2, ensure_ascii=False).encode("utf-8")
            cleanup_error = OSError("fixture cleanup failed after successful save")
            staged_files = []
            real_temporary_file = tempfile.NamedTemporaryFile
            real_replace = Path.replace

            def stage_file(*args, **kwargs):
                temporary = real_temporary_file(*args, **kwargs)
                staged_files.append(temporary)
                self.assertEqual(Path(temporary.name).parent, audit_dir)
                self.assertNotEqual(Path(temporary.name), report_path)
                self.assertNotIn(Path(temporary.name), historical_evidence)
                return temporary

            def commit_report(path, destination):
                self.assertEqual(destination, report_path)
                self.assertTrue(staged_files[0].closed)
                self.assertEqual(path.read_text(encoding="utf-8"), serialized.decode("utf-8"))
                return real_replace(path, destination)

            def fail_cleanup(path, *, missing_ok=False):
                self.assertEqual(path, Path(staged_files[0].name))
                self.assertTrue(missing_ok)
                self.assertTrue(staged_files[0].closed)
                # Replacement already committed the report and removed the staged path.
                self.assertFalse(path.exists())
                self.assertEqual(report_path.read_text(encoding="utf-8"), serialized.decode("utf-8"))
                raise cleanup_error

            with mock.patch.object(
                validate_site.tempfile, "NamedTemporaryFile", side_effect=stage_file
            ), mock.patch.object(
                Path, "replace", autospec=True, side_effect=commit_report
            ) as replace, mock.patch.object(
                Path, "unlink", autospec=True, side_effect=fail_cleanup
            ) as unlink:
                with self.assertRaises(OSError) as raised:
                    validate_site._write_validation_report(report_path, changed)
                self.assertIs(raised.exception, cleanup_error)
                self.assertIsNone(raised.exception.__cause__)
                self.assertEqual(len(staged_files), 1)
                staged_path = Path(staged_files[0].name)
                replace.assert_called_once_with(staged_path, report_path)
                unlink.assert_called_once_with(staged_path, missing_ok=True)

            self.assertEqual(json.loads(report_path.read_bytes()), changed)
            self.assertEqual(report_path.read_text(encoding="utf-8"), serialized.decode("utf-8"))
            for path, content in historical_evidence.items():
                self.assertEqual(path.read_bytes(), content)
            self.assertFalse(staged_path.exists())
            self.assertEqual(set(audit_dir.iterdir()), set(historical_evidence) | {report_path})

    def test_context_exit_failure_preserves_same_day_and_historical_evidence(self):
        for failure in ("flush", "close"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                audit_dir = Path(directory) / "assets" / "audit"
                audit_dir.mkdir(parents=True)
                report_path = audit_dir / "validation-report-2026-09-10.json"
                original = {
                    "generated_at": "2026-09-10T17:00:00Z",
                    "run_date": "2026-09-10",
                    "total_issues": 0,
                }
                evidence = {
                    report_path: (json.dumps(original) + "\n").encode("utf-8"),
                    audit_dir / "validation-report-2026-09-09.json":
                        b'{"generated_at": "2026-09-09T17:00:00Z"}\n',
                    audit_dir / "validation-report-2026-09-08.json":
                        b'{"generated_at": "2026-09-08T17:00:00Z"}\n',
                }
                for path, content in evidence.items():
                    path.write_bytes(content)
                changed = {
                    **original, "generated_at": "2026-09-10T17:05:00Z",
                    "total_issues": 1,
                }
                serialized = json.dumps(changed, indent=2, ensure_ascii=False)
                save_error = OSError(f"fixture {failure} failed on context exit")
                staged_files = []
                real_temporary_file = tempfile.NamedTemporaryFile

                class ExitFailureFile:
                    """Use real staging I/O, failing only during context exit."""

                    def __init__(self, temporary):
                        self.temporary = temporary
                        self.name = temporary.name
                        self.write = mock.Mock(wraps=temporary.write)
                        self.flush = mock.Mock(
                            side_effect=save_error if failure == "flush" else temporary.flush
                        )
                        self.close = mock.Mock(side_effect=self.close_file)

                    def close_file(self):
                        # Release the real handle even when simulating a close error.
                        self.temporary.close()
                        if failure == "close":
                            raise save_error

                    def __enter__(self):
                        return self

                    def __exit__(self, exc_type, exc_value, traceback):
                        try:
                            self.flush()
                        finally:
                            self.close()

                def stage_file(*args, **kwargs):
                    staged = ExitFailureFile(real_temporary_file(*args, **kwargs))
                    staged_files.append(staged)
                    self.assertEqual(Path(staged.name).parent, audit_dir)
                    self.assertNotIn(Path(staged.name), evidence)
                    return staged

                with mock.patch.object(
                    validate_site.tempfile, "NamedTemporaryFile", side_effect=stage_file
                ), mock.patch.object(Path, "replace", autospec=True) as replace:
                    with self.assertRaises(OSError) as raised:
                        validate_site._write_validation_report(report_path, changed)
                    self.assertIs(raised.exception, save_error)
                    replace.assert_not_called()

                self.assertEqual(len(staged_files), 1)
                staged = staged_files[0]
                staged.write.assert_called_once_with(serialized)
                staged.flush.assert_called_once_with()
                staged.close.assert_called_once_with()
                self.assertTrue(staged.temporary.closed)
                self.assertFalse(Path(staged.name).exists())
                for path, content in evidence.items():
                    self.assertEqual(path.read_bytes(), content)
                self.assertEqual(set(audit_dir.iterdir()), set(evidence))

    def test_unchanged_payload_preserves_report_bytes_and_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "validation-report-2026-09-10.json"
            report = {
                "generated_at": "2026-09-10T17:00:00Z",
                "run_date": "2026-09-10",
                "report_type": "site-validation",
                "scanned": 1,
                "total_issues": 0,
                "total_warnings": 0,
                "pages": [{"issues": [], "warnings": [], "path": "index.html"}],
            }

            self.assertTrue(validate_site._write_validation_report(report_path, report))
            original_bytes = report_path.read_bytes()

            rerun_report = {**report, "generated_at": "2026-09-10T17:05:00Z"}
            self.assertFalse(
                validate_site._write_validation_report(report_path, rerun_report)
            )
            self.assertEqual(report_path.read_bytes(), original_bytes)
            self.assertEqual(
                json.loads(report_path.read_text(encoding="utf-8"))["generated_at"],
                "2026-09-10T17:00:00Z",
            )

    def test_unusable_report_is_replaced_with_current_utc_evidence(self):
        current = {
            "generated_at": "2026-09-10T17:05:00Z",
            "run_date": "2026-09-10",
            "report_type": "site-validation",
            "scanned": 1,
            "total_issues": 0,
            "total_warnings": 0,
            "global_issues": [],
            "global_warnings": [],
            "pages": [{"issues": [], "warnings": [], "path": "index.html"}],
        }
        payload = {key: value for key, value in current.items() if key != "generated_at"}
        cases = {
            "malformed JSON": '{"generated_at":',
            "empty file": "",
            "JSON array": json.dumps([current]),
            "JSON string": json.dumps("2026-09-10T17:00:00Z"),
            "JSON number": "123",
            "JSON boolean": "true",
            "JSON null": "null",
            "missing timestamp": json.dumps(payload),
            "null timestamp": json.dumps({**payload, "generated_at": None}),
            "numeric timestamp": json.dumps({**payload, "generated_at": 123}),
            "empty timestamp": json.dumps({**payload, "generated_at": ""}),
            "malformed timestamp": json.dumps({**payload, "generated_at": "not-a-date"}),
            "malformed UTC timestamp": json.dumps(
                {**payload, "generated_at": "not-a-dateZ"}
            ),
            "impossible calendar date": json.dumps(
                {**payload, "generated_at": "2026-02-30T17:00:00Z"}
            ),
            "non-leap-year February date": json.dumps(
                {**payload, "generated_at": "2026-02-29T17:00:00Z"}
            ),
            "impossible month": json.dumps(
                {**payload, "generated_at": "2026-13-10T17:00:00Z"}
            ),
            "impossible time": json.dumps(
                {**payload, "generated_at": "2026-09-10T25:00:00Z"}
            ),
            "date without time": json.dumps(
                {**payload, "generated_at": "2026-09-10Z"}
            ),
            "timestamp without timezone": json.dumps(
                {**payload, "generated_at": "2026-09-10T17:00:00"}
            ),
            "timestamp without UTC suffix": json.dumps(
                {**payload, "generated_at": "2026-09-10T17:00:00+00:00"}
            ),
        }
        for scenario, damaged in cases.items():
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as directory:
                audit_dir = Path(directory) / "assets" / "audit"
                audit_dir.mkdir(parents=True)
                report_path = audit_dir / "validation-report-2026-09-10.json"
                previous_path = audit_dir / "validation-report-2026-09-09.json"
                previous_bytes = b'{"generated_at": "2026-09-09T17:00:00Z"}\n'
                previous_path.write_bytes(previous_bytes)
                report_path.write_text(damaged, encoding="utf-8")

                self.assertTrue(validate_site._write_validation_report(report_path, current))

                replaced = json.loads(report_path.read_text(encoding="utf-8"))
                self.assertEqual(replaced, current)
                self.assertEqual(
                    report_path.read_text(encoding="utf-8"),
                    json.dumps(current, indent=2, ensure_ascii=False),
                )
                self.assertEqual(replaced["generated_at"], "2026-09-10T17:05:00Z")
                self.assertEqual(
                    datetime.fromisoformat(replaced["generated_at"].replace("Z", "+00:00")),
                    datetime(2026, 9, 10, 17, 5, tzinfo=timezone.utc),
                )
                self.assertEqual(previous_path.read_bytes(), previous_bytes)
                self.assertEqual(set(audit_dir.iterdir()), {previous_path, report_path})

    def test_invalid_utf8_report_is_replaced_without_changing_historical_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            audit_dir = Path(directory) / "assets" / "audit"
            audit_dir.mkdir(parents=True)
            report_path = audit_dir / "validation-report-2026-09-10.json"
            historical_reports = {
                audit_dir / "validation-report-2026-09-08.json":
                    b'{"generated_at": "2026-09-08T17:00:00Z"}\n',
                audit_dir / "validation-report-2026-09-09.json":
                    b'{"generated_at": "2026-09-09T17:00:00Z"}\n',
            }
            for path, content in historical_reports.items():
                path.write_bytes(content)
            report_path.write_bytes(b'{"generated_at": "\xff"}')
            current = {
                "generated_at": "2026-09-10T17:05:00Z",
                "run_date": "2026-09-10",
                "report_type": "site-validation",
                "scanned": 1,
                "total_issues": 0,
                "total_warnings": 0,
                "pages": [{"path": "caf\u00e9/index.html", "issues": [], "warnings": []}],
            }

            self.assertTrue(validate_site._write_validation_report(report_path, current))

            self.assertEqual(
                json.loads(report_path.read_text(encoding="utf-8")), current
            )
            self.assertEqual(
                report_path.read_text(encoding="utf-8"),
                json.dumps(current, indent=2, ensure_ascii=False),
            )
            for path, content in historical_reports.items():
                self.assertEqual(path.read_bytes(), content)
            self.assertEqual(
                set(audit_dir.iterdir()), set(historical_reports) | {report_path}
            )

    def test_valid_utc_timestamps_preserve_original_formatting(self):
        for timestamp in (
            "2026-09-10T17:00:00Z",
            "2026-09-10T17:00:00.123456Z",
            "2024-02-29T17:00:00Z",
        ):
            with self.subTest(timestamp=timestamp), tempfile.TemporaryDirectory() as directory:
                report_path = Path(directory) / "validation-report.json"
                existing = {"generated_at": timestamp, "scanned": 1, "pages": []}
                original_bytes = (json.dumps(existing) + "\n").encode("utf-8")
                report_path.write_bytes(original_bytes)
                current = {**existing, "generated_at": "2026-09-10T17:05:00Z"}

                self.assertFalse(validate_site._write_validation_report(report_path, current))
                self.assertEqual(report_path.read_bytes(), original_bytes)

    def test_changed_payload_refreshes_report_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "validation-report-2026-09-10.json"
            original = {
                "generated_at": "2026-09-10T17:00:00Z",
                "run_date": "2026-09-10",
                "report_type": "site-validation",
                "scanned": 1,
                "total_issues": 0,
                "total_warnings": 0,
                "pages": [{"issues": [], "warnings": [], "path": "index.html"}],
            }
            changed = {
                **original,
                "generated_at": "2026-09-10T17:05:00Z",
                "total_warnings": 1,
            }

            validate_site._write_validation_report(report_path, original)
            self.assertTrue(
                validate_site._write_validation_report(report_path, changed)
            )
            self.assertEqual(
                json.loads(report_path.read_text(encoding="utf-8")),
                changed,
            )


if __name__ == "__main__":
    unittest.main()

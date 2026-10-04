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
                    report_path.read_bytes(),
                    json.dumps(current, indent=2, ensure_ascii=False).encode("utf-8"),
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
                report_path.read_bytes(),
                json.dumps(current, indent=2, ensure_ascii=False).encode("utf-8"),
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
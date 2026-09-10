#!/usr/bin/env python3
"""Regression tests for the Organization identity approval contract."""
from __future__ import annotations

import importlib.util
import json
from datetime import date
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


_SCRIPT = Path(__file__).resolve().parent.parent / "validate-site.py"
_ROOT = _SCRIPT.parents[1]
_SPEC = importlib.util.spec_from_file_location("_validate_site", _SCRIPT)
validate_site = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(validate_site)


ORGANIZATION_TEMPLATE = """\
<!doctype html>
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@graph": [{{
    "@type": "Organization",
    "sameAs": {same_as}
  }}]
}}
</script>
"""

EVIDENCE_TEMPLATE = """\
# Evidence

## Organization identities

The approved identities live in the schema-checked
[approval record](organization-identity-approval.json).
"""

APPROVAL_TEMPLATE = {
    "schema": 1,
    "record_type": "organization-identity-approval",
    "approval_date": "2026-09-09",
    "reviewer_confirmation": {
        "status": "confirmed",
        "statement": "Owner confirmed the identities.",
    },
    "approved_urls": [],
}


class OrganizationIdentityApprovalTests(unittest.TestCase):
    def _run_check(self, published: list[str], approved: list[str]) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs").mkdir()
            (root / "index.html").write_text(
                ORGANIZATION_TEMPLATE.format(
                    same_as=json.dumps(published)
                ),
                encoding="utf-8",
            )
            (root / "docs" / "discovery-evidence.md").write_text(
                EVIDENCE_TEMPLATE, encoding="utf-8"
            )
            record = {**APPROVAL_TEMPLATE, "approved_urls": approved}
            (root / "docs" / "organization-identity-approval.json").write_text(
                json.dumps(record), encoding="utf-8"
            )

            original_root = validate_site.ROOT
            validate_site.ROOT = root
            try:
                return validate_site._check_organization_identity_approval()
            finally:
                validate_site.ROOT = original_root

    def test_matching_lists_pass(self):
        urls = ["https://example.com/one", "https://example.com/two"]

        self.assertEqual(self._run_check(urls, urls), [])

    def test_published_identity_without_approval_fails(self):
        published = [
            "https://example.com/one",
            "https://example.com/two",
            "https://example.com/new",
        ]
        approved = ["https://example.com/one", "https://example.com/two"]

        issues = self._run_check(published, approved)

        self.assertTrue(any("missing from owner approval" in issue for issue in issues))
        self.assertFalse(any("missing from homepage sameAs" in issue for issue in issues))

    def test_approval_identity_without_publication_fails(self):
        published = ["https://example.com/one", "https://example.com/two"]
        approved = [
            "https://example.com/one",
            "https://example.com/two",
            "https://example.com/new",
        ]

        issues = self._run_check(published, approved)

        self.assertTrue(any("missing from homepage sameAs" in issue for issue in issues))
        self.assertFalse(any("missing from owner approval" in issue for issue in issues))

    def test_missing_approval_record_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs").mkdir()
            (root / "index.html").write_text(
                ORGANIZATION_TEMPLATE.format(
                    same_as='["https://example.com/one", "https://example.com/two"]'
                ),
                encoding="utf-8",
            )
            (root / "docs" / "discovery-evidence.md").write_text(
                EVIDENCE_TEMPLATE, encoding="utf-8"
            )

            original_root = validate_site.ROOT
            validate_site.ROOT = root
            try:
                issues = validate_site._check_organization_identity_approval()
            finally:
                validate_site.ROOT = original_root

        self.assertTrue(
            any("organization-identity-approval.json is missing" in issue for issue in issues)
        )

    def test_invalid_approval_schema_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs").mkdir()
            (root / "index.html").write_text(
                ORGANIZATION_TEMPLATE.format(
                    same_as='["https://example.com/one"]'
                ),
                encoding="utf-8",
            )
            (root / "docs" / "discovery-evidence.md").write_text(
                EVIDENCE_TEMPLATE, encoding="utf-8"
            )
            record = {**APPROVAL_TEMPLATE, "approved_urls": ["not-a-url"]}
            (root / "docs" / "organization-identity-approval.json").write_text(
                json.dumps(record), encoding="utf-8"
            )

            original_root = validate_site.ROOT
            validate_site.ROOT = root
            try:
                issues = validate_site._check_organization_identity_approval()
            finally:
                validate_site.ROOT = original_root

        self.assertTrue(
            any("approved_urls must contain only absolute HTTP(S) URLs" in issue for issue in issues)
        )

    def test_documentation_must_link_to_approval_record(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs").mkdir()
            (root / "index.html").write_text(
                ORGANIZATION_TEMPLATE.format(
                    same_as='["https://example.com/one"]'
                ),
                encoding="utf-8",
            )
            (root / "docs" / "discovery-evidence.md").write_text(
                "# Evidence\n\n## Organization identities\n\nNo link.\n",
                encoding="utf-8",
            )
            record = {**APPROVAL_TEMPLATE, "approved_urls": ["https://example.com/one"]}
            (root / "docs" / "organization-identity-approval.json").write_text(
                json.dumps(record), encoding="utf-8"
            )

            original_root = validate_site.ROOT
            validate_site.ROOT = root
            try:
                issues = validate_site._check_organization_identity_approval()
            finally:
                validate_site.ROOT = original_root

        self.assertTrue(
            any("documentation must link" in issue for issue in issues)
        )

    def test_release_validator_command_blocks_unapproved_identity(self):
        approval_record = _ROOT / "docs" / "organization-identity-approval.json"
        report = (
            _ROOT
            / "assets"
            / "audit"
            / f"validation-report-{date.today().isoformat()}.json"
        )
        original_record = approval_record.read_bytes()
        original_report = report.read_bytes() if report.exists() else None
        record = json.loads(original_record)
        record["approved_urls"].append("https://example.com/unapproved-identity")
        approval_record.write_text(json.dumps(record), encoding="utf-8")
        try:
            result = subprocess.run(
                [sys.executable, str(_SCRIPT)],
                cwd=_ROOT,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        finally:
            approval_record.write_bytes(original_record)
            if original_report is None:
                report.unlink(missing_ok=True)
            else:
                report.write_bytes(original_report)

        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, output)
        self.assertIn(
            "owner-approved URL(s) missing from homepage sameAs: "
            "https://example.com/unapproved-identity",
            output,
        )

    def test_release_validator_command_blocks_removed_homepage_identity(self):
        homepage = _ROOT / "index.html"
        report = (
            _ROOT
            / "assets"
            / "audit"
            / f"validation-report-{date.today().isoformat()}.json"
        )
        original_homepage = homepage.read_bytes()
        original_report = report.read_bytes() if report.exists() else None
        approval_record = json.loads(
            (_ROOT / "docs" / "organization-identity-approval.json").read_text(
                encoding="utf-8"
            )
        )
        removed_url = approval_record["approved_urls"][0]
        homepage_text = original_homepage.decode("utf-8")
        identity_line = f'            "{removed_url}",\n'
        self.assertIn(identity_line, homepage_text)
        homepage.write_text(
            homepage_text.replace(identity_line, "", 1),
            encoding="utf-8",
        )
        try:
            result = subprocess.run(
                [sys.executable, str(_SCRIPT)],
                cwd=_ROOT,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        finally:
            homepage.write_bytes(original_homepage)
            if original_report is None:
                report.unlink(missing_ok=True)
            else:
                report.write_bytes(original_report)

        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, output)
        self.assertIn(
            "owner-approved URL(s) missing from homepage sameAs: " + removed_url,
            output,
        )


if __name__ == "__main__":
    unittest.main()
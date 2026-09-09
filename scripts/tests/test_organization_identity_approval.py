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

{urls}
"""


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
                EVIDENCE_TEMPLATE.format(
                    urls="\n".join(f"- `{url}`" for url in approved)
                ),
                encoding="utf-8",
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

    def test_missing_approval_section_fails(self):
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
                "# Evidence\n", encoding="utf-8"
            )

            original_root = validate_site.ROOT
            validate_site.ROOT = root
            try:
                issues = validate_site._check_organization_identity_approval()
            finally:
                validate_site.ROOT = original_root

        self.assertTrue(any("no '## Organization identities' section" in issue for issue in issues))

    def test_release_validator_command_blocks_unapproved_identity(self):
        evidence = _ROOT / "docs" / "discovery-evidence.md"
        report = (
            _ROOT
            / "assets"
            / "audit"
            / f"validation-report-{date.today().isoformat()}.json"
        )
        original_evidence = evidence.read_bytes()
        original_report = report.read_bytes() if report.exists() else None
        evidence.write_bytes(
            original_evidence
            + b"\n- `https://example.com/unapproved-identity`\n"
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
            evidence.write_bytes(original_evidence)
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


if __name__ == "__main__":
    unittest.main()
#!/usr/bin/env python3
"""Regression tests for scripts/audit-site.py discovery checks."""
from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch


_SCRIPT = Path(__file__).resolve().parent.parent / "audit-site.py"
_SPEC = importlib.util.spec_from_file_location("_audit_site", _SCRIPT)
_MODULE = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_MODULE)

ORIGIN = "https://glee-fully.tools"


def social_image_fixture(
    extension: str, width: int = 1200, height: int = 630, *,
    webp_encoding: str = "VP8X",
) -> bytes:
    if extension == "png":
        return (
            b"\x89PNG\r\n\x1a\n"
            + (13).to_bytes(4, "big")
            + b"IHDR"
            + width.to_bytes(4, "big")
            + height.to_bytes(4, "big")
            + b"\x08\x02\x00\x00\x00"
        )
    if extension == "jpg":
        frame = (
            b"\x08"
            + height.to_bytes(2, "big")
            + width.to_bytes(2, "big")
            + b"\x03\x01\x11\x00\x02\x11\x00\x03\x11\x00"
        )
        return b"\xff\xd8\xff\xc0" + (len(frame) + 2).to_bytes(2, "big") + frame
    if extension == "gif":
        return (
            b"GIF89a"
            + width.to_bytes(2, "little")
            + height.to_bytes(2, "little")
            + b"\x00\x00\x00"
        )
    if extension == "webp":
        if webp_encoding == "VP8X":
            data = (
                b"\x00\x00\x00\x00"
                + (width - 1).to_bytes(3, "little")
                + (height - 1).to_bytes(3, "little")
            )
        elif webp_encoding == "VP8 ":
            data = (
                b"\x00\x00\x00\x9d\x01\x2a"
                + width.to_bytes(2, "little")
                + height.to_bytes(2, "little")
            )
        elif webp_encoding == "VP8L":
            width_minus_one = width - 1
            height_minus_one = height - 1
            data = bytes(
                (
                    0x2F,
                    width_minus_one & 0xFF,
                    ((width_minus_one >> 8) & 0x3F)
                    | ((height_minus_one & 0x03) << 6),
                    (height_minus_one >> 2) & 0xFF,
                    (height_minus_one >> 10) & 0x0F,
                )
            )
        else:
            raise ValueError(f"Unsupported WebP encoding: {webp_encoding}")
        chunk = (
            webp_encoding.encode("ascii")
            + len(data).to_bytes(4, "little")
            + data
        )
        body = b"WEBP" + chunk
        return b"RIFF" + len(body).to_bytes(4, "little") + body
    raise ValueError(f"Unsupported fixture format: {extension}")


IMAGE_SIGNATURES = {
    extension: social_image_fixture(extension)
    for extension in ("png", "jpg", "gif", "webp")
}


class AuditSiteTests(unittest.TestCase):
    def run_cli_fixture(self, root: Path, report: str, stdout) -> int:
        page = root / "caf\u00e9-\u2603" / "index.html"
        with ExitStack() as stack:
            for name, value in {
                "iter_html_files": [page],
                "audit_page": ["Missing description"],
                "reconcile_sitemap": ([], [], []),
                "reconcile_search_index": [],
                "check_search_index_freshness": [],
                "scan_repo_cruft": [],
            }.items():
                stack.enter_context(patch.object(_MODULE, name, return_value=value))
            stack.enter_context(patch.object(_MODULE, "ROOT", root))
            stack.enter_context(patch.object(_MODULE.sys, "argv", [str(_SCRIPT), "--report", report]))
            stack.enter_context(patch.object(_MODULE.sys, "stdout", stdout))
            stack.enter_context(patch.object(_MODULE.sys, "stderr", io.StringIO()))
            return _MODULE.main()

    def test_external_report_and_legacy_console_preserve_advisory_findings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            report = Path(directory) / "reports-\u2603" / "audit.md"
            with io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict") as console:
                result = self.run_cli_fixture(root, str(report), console)
                console.flush()
                output = console.buffer.getvalue().decode("utf-8")
            self.assertEqual(result, 0, "Findings remain advisory")
            self.assertIn(str(report.resolve()), output)
            self.assertIn("caf\u00e9-\u2603/index.html", output)
            self.assertIn("Total issues found: 1", output)
            self.assertIn("Missing description", report.read_text(encoding="utf-8"))

    def test_relative_report_is_rooted_in_repo_with_nonreconfigurable_console(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            console = io.StringIO()
            self.assertEqual(self.run_cli_fixture(root, "reports/audit.md", console), 0)
            self.assertTrue((root / "reports/audit.md").is_file())
            self.assertIn("Report written to reports/audit.md", console.getvalue())
            self.assertIn("Total issues found: 1", console.getvalue())

    def test_external_report_prints_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            report = Path(directory) / "external" / "audit.md"
            console = io.StringIO()
            self.assertEqual(self.run_cli_fixture(root, str(report), console), 0)
            self.assertIn(str(report.resolve()), console.getvalue())
            self.assertIn("Missing description", report.read_text(encoding="utf-8"))

    def og_image_findings(
        self, root: Path, url: str, *later_urls: str, image_type: str = "",
        declared_width: str | None = None, declared_height: str | None = None,
        include_recommendations: bool = False,
    ) -> list[str]:
        page = root / "content" / "index.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(
            "\n".join(
                f'<meta property="og:image" content="{image_url}">'
                + (
                    f'<meta property="og:image:type" content="{image_type}">'
                    if image_type
                    else ""
                )
                + (f'<meta property="og:image:width" content="{declared_width}">'
                   if declared_width is not None else "")
                + (f'<meta property="og:image:height" content="{declared_height}">'
                   if declared_height is not None else "")
                for image_url in (url, *later_urls)
            ),
            encoding="utf-8",
        )
        with patch.object(_MODULE, "ROOT", root), patch.object(
            _MODULE, "site_origin", return_value=ORIGIN
        ):
            return [
                issue for issue in _MODULE.audit_page(page)
                if issue.startswith("og:image") or (
                    include_recommendations and issue.startswith("Recommended og:image")
                )
            ]

    def test_matching_local_og_image_type_is_accepted(self) -> None:
        mime_types = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "gif": "image/gif",
            "webp": "image/webp",
        }
        for extension, mime_type in mime_types.items():
            with (
                self.subTest(extension=extension),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory) / "repo"
                image_dir = root / "assets" / "social"
                image_dir.mkdir(parents=True)
                (image_dir / f"hero.{extension}").write_bytes(
                    IMAGE_SIGNATURES[extension]
                )

                findings = self.og_image_findings(
                    root,
                    f"{ORIGIN}/assets/social/hero.{extension}",
                    image_type=mime_type,
                )

                self.assertEqual(findings, [])

    def test_each_og_image_type_without_a_preceding_image_url_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / "index.html"
            page.write_text(
                '<meta property="og:image:type" content="image/png">'
                '<meta property="og:image:type" content="image/webp">'
                '<meta property="og:image" content="">'
                '<meta property="og:image:type" content="image/jpeg">',
                encoding="utf-8",
            )

            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ):
                findings = [
                    issue
                    for issue in _MODULE.audit_page(page)
                    if issue.startswith("og:image:type")
                ]

            self.assertEqual(len(findings), 3)
            self.assertEqual(
                findings,
                ["og:image:type without a preceding non-empty og:image URL"] * 3,
            )

    def test_orphan_image_type_is_not_attached_to_a_later_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            images = root / "assets"
            images.mkdir()
            (images / "hero.jpg").write_bytes(IMAGE_SIGNATURES["jpg"])
            page = root / "index.html"
            page.write_text(
                '<meta property="og:image:type" content="image/png">'
                '<meta property="og:image" content="/assets/hero.jpg">', encoding="utf-8"
            )
            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ):
                issues = _MODULE.audit_page(page)

            findings = [issue for issue in issues if issue.startswith("og:image:type")]
            self.assertEqual(findings, ["og:image:type without a preceding non-empty og:image URL"])

    def test_image_type_after_blank_root_and_secure_url_is_orphaned(self) -> None:
        for root_attributes in ('', ' content=""', ' content="   "'):
            with self.subTest(root_attributes=root_attributes), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                page = root / "index.html"
                page.write_text(
                    f'<meta property="og:image"{root_attributes}>'
                    '<meta property="og:image:secure_url" content="https://external.test/secure.png">'
                    '<meta property="og:image:type" content="image/png">', encoding="utf-8"
                )
                with patch.object(_MODULE, "ROOT", root), patch.object(
                    _MODULE, "site_origin", return_value=ORIGIN
                ):
                    issues = _MODULE.audit_page(page)

                findings = [issue for issue in issues if issue.startswith("og:image:type")]
                self.assertEqual(findings, ["og:image:type without a preceding non-empty og:image URL"])
                self.assertIn("og:image declaration is missing a non-empty content URL", issues)

    def test_orphan_image_type_does_not_inject_untrusted_text_into_reports(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / "index.html"
            page.write_text(
                '<meta property="og:image:type" content="image/png&#10;`Injected report line`">',
                encoding="utf-8",
            )
            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ):
                issues = _MODULE.audit_page(page)

            findings = [issue for issue in issues if issue.startswith("og:image:type")]
            self.assertEqual(findings, ["og:image:type without a preceding non-empty og:image URL"])
            self.assertFalse(any("Injected report line" in issue for issue in issues))

    def test_image_type_binds_to_alias_root_across_secure_alternate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            images = root / "assets"
            images.mkdir()
            (images / "primary.jpg").write_bytes(IMAGE_SIGNATURES["jpg"])
            (images / "secure.png").write_bytes(IMAGE_SIGNATURES["png"])
            page = root / "index.html"
            page.write_text(
                '<meta property="og:image:url" content="/assets/primary.jpg">'
                '<meta property="og:image:secure_url" content="/assets/secure.png">'
                '<meta property="og:image:type" content="image/png">', encoding="utf-8"
            )
            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ):
                issues = _MODULE.audit_page(page)

            findings = [issue for issue in issues if issue.startswith("og:image:type")]
            self.assertEqual(len(findings), 1)
            self.assertIn("primary.jpg", findings[0])
            self.assertIn("expected `image/jpeg`", findings[0])

    def test_duplicate_image_types_keep_last_value_for_the_root(self) -> None:
        for last_type, expected_mismatch in (("image/jpeg", False), ("image/png", True), ("", False)):
            with self.subTest(last_type=last_type), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                images = root / "assets"
                images.mkdir()
                (images / "primary.jpg").write_bytes(IMAGE_SIGNATURES["jpg"])
                page = root / "index.html"
                page.write_text(
                    '<meta property="og:image" content="/assets/primary.jpg">'
                    '<meta property="og:image:type" content="image/png">'
                    f'<meta property="og:image:type" content="{last_type}">', encoding="utf-8"
                )
                with patch.object(_MODULE, "ROOT", root), patch.object(
                    _MODULE, "site_origin", return_value=ORIGIN
                ):
                    issues = _MODULE.audit_page(page)

                findings = [issue for issue in issues if issue.startswith("og:image:type")]
                self.assertEqual(len(findings), int(expected_mismatch))
                if expected_mismatch:
                    self.assertIn("expected `image/jpeg`", findings[0])

    def test_conflicting_og_image_types_do_not_echo_values_or_image_url(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            image_dir = root / "assets" / "social"
            image_dir.mkdir(parents=True)
            (image_dir / "share.png").write_bytes(IMAGE_SIGNATURES["png"])
            page = root / "index.html"
            image_url = f"{ORIGIN}/assets/social/share.png"
            page.write_text(
                f'<meta property="og:image" content="{image_url}">'
                '<meta property="og:image:type" content="image/jpeg">'
                '<meta property="og:image:type" content="image/png">',
                encoding="utf-8",
            )

            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ):
                issues = _MODULE.audit_page(page)

            findings = [
                issue for issue in issues
                if issue.startswith("Conflicting og:image:type")
            ]
            self.assertEqual(findings, ["Conflicting og:image:type declarations"])
            self.assertFalse(any(issue.startswith("og:image:type declares") for issue in issues))

    def test_repeated_identical_og_image_types_are_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / "index.html"
            page.write_text(
                '<meta property="og:image" '
                'content="https://external.test/share.png">'
                '<meta property="og:image:type" content="image/png">'
                '<meta property="og:image:type" content="image/png">',
                encoding="utf-8",
            )

            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ):
                findings = [
                    issue for issue in _MODULE.audit_page(page)
                    if issue.startswith("Conflicting og:image:type")
                ]

            self.assertEqual(findings, [])

    def test_conflicting_types_are_reported_in_either_order(self) -> None:
        for types in (("image/png", "image/jpeg"), ("image/jpeg", "image/png")):
            with self.subTest(types=types), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                page = root / "index.html"
                page.write_text(
                    '<meta property="og:image" content="https://external.test/image.png">'
                    + ''.join(f'<meta property="og:image:type" content="{value}">' for value in types),
                    encoding="utf-8",
                )
                with patch.object(_MODULE, "ROOT", root), patch.object(
                    _MODULE, "site_origin", return_value=ORIGIN
                ):
                    issues = _MODULE.audit_page(page)

                findings = [issue for issue in issues if issue.startswith("Conflicting og:image:type")]
                self.assertEqual(findings, ["Conflicting og:image:type declarations"])

    def test_equivalent_and_blank_types_do_not_create_conflicts(self) -> None:
        for types in (("image/png", "&#9;IMAGE/PNG&#160;"), ("", "image/png", "  "), ("", "  ")):
            with self.subTest(types=types), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                page = root / "index.html"
                page.write_text(
                    '<meta property="og:image" content="https://external.test/image.png">'
                    + ''.join(f'<meta property="og:image:type" content="{value}">' for value in types),
                    encoding="utf-8",
                )
                with patch.object(_MODULE, "ROOT", root), patch.object(
                    _MODULE, "site_origin", return_value=ORIGIN
                ):
                    issues = _MODULE.audit_page(page)

                self.assertFalse(any(issue.startswith("Conflicting og:image:type") for issue in issues))

    def test_conflicting_types_are_grouped_by_root_not_secure_alternate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / "index.html"
            page.write_text(
                '<meta property="og:image" content="https://external.test/first.png">'
                '<meta property="og:image:type" content="image/png">'
                '<meta property="og:image:url" content="https://external.test/second.png">'
                '<meta property="og:image:type" content="image/png">'
                '<meta property="og:image:secure_url" content="https://external.test/secure.png">'
                '<meta property="og:image:alt" content="Second image">'
                '<meta property="og:image:type" content="image/jpeg">', encoding="utf-8"
            )
            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ):
                issues = _MODULE.audit_page(page)

            findings = [issue for issue in issues if issue.startswith("Conflicting og:image:type")]
            self.assertEqual(findings, ["Conflicting og:image:type declarations (image 2)"])

    def test_conflict_diagnostic_does_not_echo_untrusted_type_or_url(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / "index.html"
            page.write_text(
                '<meta property="og:image" content="https://external.test/x&#10;`URL injection`">'
                '<meta property="og:image:type" content="image/png&#10;`TYPE injection`">'
                '<meta property="og:image:type" content="image/jpeg">', encoding="utf-8"
            )
            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ):
                issues = _MODULE.audit_page(page)

            findings = [issue for issue in issues if issue.startswith("Conflicting og:image:type")]
            self.assertEqual(findings, ["Conflicting og:image:type declarations"])
            self.assertNotIn("injection", findings[0].lower())

    def test_mismatching_local_og_image_type_is_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            image_dir = root / "assets" / "social"
            image_dir.mkdir(parents=True)
            (image_dir / "hero.png").write_bytes(IMAGE_SIGNATURES["png"])

            findings = self.og_image_findings(
                root,
                f"{ORIGIN}/assets/social/hero.png",
                image_type="image/svg+xml",
            )

            self.assertEqual(len(findings), 1)
            self.assertIn("og:image:type declares `image/svg+xml`", findings[0])
            self.assertIn("local file is PNG", findings[0])
            self.assertIn("expected `image/png`", findings[0])

    def test_external_og_image_type_is_not_checked_locally(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            external_url = "https://external.test/image.png"
            with patch.object(
                _MODULE, "link_target", wraps=_MODULE.link_target
            ) as resolve:
                findings = self.og_image_findings(
                    root, external_url, image_type="image/svg+xml"
                )

            self.assertEqual(findings, [])
            resolve.assert_not_called()

    def test_each_local_og_image_type_is_compared_with_its_own_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            image_dir = root / "assets" / "social"
            image_dir.mkdir(parents=True)
            (image_dir / "hero.png").write_bytes(IMAGE_SIGNATURES["png"])
            (image_dir / "share.jpg").write_bytes(IMAGE_SIGNATURES["jpg"])
            page = root / "index.html"
            page.write_text(
                '<meta property="og:image" content="/assets/social/hero.png">'
                '<meta property="og:image:type" content="image/png">'
                '<meta property="og:image" content="/assets/social/share.jpg">'
                '<meta property="og:image:type" content="image/png">',
                encoding="utf-8",
            )

            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ):
                findings = [
                    issue for issue in _MODULE.audit_page(page)
                    if issue.startswith("og:image")
                ]

            self.assertEqual(len(findings), 1)
            self.assertIn("share.jpg", findings[0])
            self.assertIn("expected `image/jpeg`", findings[0])

    def test_every_later_local_og_image_is_checked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            images = root / "assets" / "social"
            images.mkdir(parents=True)
            (images / "hero.png").write_bytes(IMAGE_SIGNATURES["png"])
            invalid = (
                f"{ORIGIN}/assets/social/missing.png",
                f"{ORIGIN}/%2e%2e/outside.png",
            )
            findings = self.og_image_findings(
                root, f"{ORIGIN}/assets/social/hero.png?v=2", *invalid
            )
            self.assertEqual(len(findings), 2)
            for finding, url in zip(findings, invalid):
                self.assertIn(url, finding)
                self.assertIn("safe file inside", finding)

    def test_invalid_local_og_image_url_alias_is_checked_after_valid_image(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            images = root / "assets" / "social"
            images.mkdir(parents=True)
            (images / "hero.png").write_bytes(IMAGE_SIGNATURES["png"])
            page = root / "index.html"
            page.write_text(
                '<meta property="og:image" content="/assets/social/hero.png">'
                '<meta property="og:image:url" content="/%2e%2e/outside.png">',
                encoding="utf-8",
            )
            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ):
                issues = _MODULE.audit_page(page)
                findings = [issue for issue in issues if issue.startswith("og:image")]

            self.assertNotIn("Missing og:image", issues)
            self.assertEqual(len(findings), 1)
            self.assertIn("/%2e%2e/outside.png", findings[0])
            self.assertIn("safe file inside", findings[0])

    def test_unsafe_local_og_image_secure_url_is_checked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            page = root / "index.html"
            page.write_text(
                '<meta property="og:image:secure_url" '
                'content="/%2e%2e/outside.png">',
                encoding="utf-8",
            )
            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ):
                findings = [
                    issue for issue in _MODULE.audit_page(page)
                    if issue.startswith("og:image")
                ]

            self.assertEqual(len(findings), 1)
            self.assertIn("/%2e%2e/outside.png", findings[0])
            self.assertIn("safe file inside", findings[0])

    def test_secure_url_does_not_redirect_type_from_its_root(self) -> None:
        for type_before_alternate in (True, False):
            with self.subTest(type_before_alternate=type_before_alternate), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                images = root / "assets"
                images.mkdir()
                (images / "primary.png").write_bytes(IMAGE_SIGNATURES["png"])
                (images / "second.jpg").write_bytes(IMAGE_SIGNATURES["jpg"])
                (images / "alternate.jpg").write_bytes(IMAGE_SIGNATURES["jpg"])
                (images / "alternate.png").write_bytes(IMAGE_SIGNATURES["png"])
                image_type = '<meta property="og:image:type" content="image/png">'

                def group(primary: str, alternate: str) -> str:
                    root_tag = f'<meta property="og:image" content="/assets/{primary}">'
                    secure_tag = (
                        f'<meta property="og:image:secure_url" content="/assets/{alternate}">'
                    )
                    return root_tag + (image_type + secure_tag if type_before_alternate
                                       else secure_tag + image_type)

                page = root / "index.html"
                page.write_text(
                    group("primary.png", "alternate.jpg")
                    + group("second.jpg", "alternate.png"), encoding="utf-8"
                )
                with patch.object(_MODULE, "ROOT", root), patch.object(
                    _MODULE, "site_origin", return_value=ORIGIN
                ):
                    issues = _MODULE.audit_page(page)

                findings = [issue for issue in issues if issue.startswith("og:image")]
                self.assertNotIn("Missing og:image", issues)
                self.assertEqual(len(findings), 1)
                self.assertIn("second.jpg", findings[0])
                self.assertIn("expected `image/jpeg`", findings[0])

    def test_orphan_secure_url_is_validated_but_does_not_supply_primary(self) -> None:
        for attributes, expected in (
            ('', "missing a non-empty content URL"),
            (' content=""', "missing a non-empty content URL"),
            (' content="   "', "missing a non-empty content URL"),
            (' content="/%2e%2e/outside.png"', "safe file inside"),
        ):
            with self.subTest(attributes=attributes), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                page = root / "index.html"
                page.write_text(
                    f'<meta property="og:image:secure_url"{attributes}>', encoding="utf-8"
                )
                with patch.object(_MODULE, "ROOT", root), patch.object(
                    _MODULE, "site_origin", return_value=ORIGIN
                ):
                    issues = _MODULE.audit_page(page)

                self.assertIn("Missing og:image", issues)
                self.assertTrue(any(expected in issue for issue in issues))

    def test_valid_local_og_image_url_alias_satisfies_required_image_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            images = root / "assets" / "social"
            images.mkdir(parents=True)
            (images / "hero.png").write_bytes(IMAGE_SIGNATURES["png"])
            page = root / "index.html"
            page.write_text(
                '<meta property="og:image:url" content="/assets/social/hero.png">',
                encoding="utf-8",
            )
            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ):
                issues = _MODULE.audit_page(page)

            self.assertNotIn("Missing og:image", issues)
            self.assertFalse(any(issue.startswith("og:image") for issue in issues))

    def test_missing_og_image_and_url_alias_reports_required_image_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            page = root / "index.html"
            page.write_text("<html></html>", encoding="utf-8")
            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ):
                issues = _MODULE.audit_page(page)

            self.assertIn("Missing og:image", issues)

    def test_blank_og_image_url_alias_is_reported(self) -> None:
        for attributes in ('', ' content=""', ' content="   "'):
            with self.subTest(attributes=attributes), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                page = root / "index.html"
                page.write_text(
                    f'<meta property="og:image:url"{attributes}>', encoding="utf-8"
                )
                with patch.object(_MODULE, "ROOT", root), patch.object(
                    _MODULE, "site_origin", return_value=ORIGIN
                ):
                    issues = _MODULE.audit_page(page)

                self.assertNotIn("Missing og:image", issues)
                self.assertIn(
                    "og:image declaration is missing a non-empty content URL", issues
                )

    def test_offline_exemption_keeps_declared_alias_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / "offline.html"
            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ):
                page.write_text("<html></html>", encoding="utf-8")
                without_image = _MODULE.audit_page(page)
                page.write_text('<meta property="og:image:url" content="">', encoding="utf-8")
                with_blank_alias = _MODULE.audit_page(page)

            for issues in (without_image, with_blank_alias):
                for required in ("og:title", "og:description", "og:image", "og:url"):
                    self.assertNotIn(f"Missing {required}", issues)
            self.assertIn(
                "og:image declaration is missing a non-empty content URL", with_blank_alias
            )

    def test_blank_open_graph_text_metadata_is_reported_and_populated_values_pass(self) -> None:
        fields = ("og:title", "og:description", "og:url")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / "index.html"

            for field in fields:
                for value in ("", "   ", "\n\t"):
                    with self.subTest(field=field, value=value):
                        tags = "".join(
                            f'<meta property="{name}" content="'
                            f'{"Populated value" if name != field else value}">'
                            for name in fields
                        )
                        page.write_text(tags, encoding="utf-8")
                        with patch.object(_MODULE, "ROOT", root), patch.object(
                            _MODULE, "site_origin", return_value=ORIGIN
                        ):
                            issues = _MODULE.audit_page(page)

                        self.assertIn(f"Blank {field}", issues)

            page.write_text(
                "".join(
                    f'<meta property="{field}" content="Populated value">'
                    for field in fields
                ),
                encoding="utf-8",
            )
            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ):
                issues = _MODULE.audit_page(page)

            self.assertFalse(
                any(issue.startswith("Blank og:") for issue in issues)
            )

    def test_duplicate_blank_text_metadata_is_reported_in_either_order(self) -> None:
        fields = ("og:title", "og:description", "og:url")
        for field in fields:
            for blank_first in (True, False):
                with self.subTest(field=field, blank_first=blank_first), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    page = root / "index.html"
                    other_tags = "".join(
                        f'<meta property="{name}" content="Populated value">'
                        for name in fields if name != field
                    )
                    blank = f'<meta property="{field}" content=" ">'
                    populated = f'<meta property="{field}" content="Populated value">'
                    page.write_text(
                        other_tags + (blank + populated if blank_first else populated + blank),
                        encoding="utf-8",
                    )
                    with patch.object(_MODULE, "ROOT", root), patch.object(
                        _MODULE, "site_origin", return_value=ORIGIN
                    ):
                        issues = _MODULE.audit_page(page)

                    self.assertIn(f"Blank {field}", issues)
                    self.assertNotIn(f"Missing {field}", issues)
                    self.assertEqual(issues.count(f"Blank {field}"), 1)

    def test_missing_and_contentless_open_graph_text_have_distinct_findings(self) -> None:
        for field in ("og:title", "og:description", "og:url"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                page = root / "index.html"
                with patch.object(_MODULE, "ROOT", root), patch.object(
                    _MODULE, "site_origin", return_value=ORIGIN
                ):
                    page.write_text("<html></html>", encoding="utf-8")
                    missing = _MODULE.audit_page(page)
                    page.write_text(f'<meta property="{field}">', encoding="utf-8")
                    contentless = _MODULE.audit_page(page)

                self.assertIn(f"Missing {field}", missing)
                self.assertNotIn(f"Blank {field}", missing)
                self.assertIn(f"Blank {field}", contentless)
                self.assertNotIn(f"Missing {field}", contentless)

    def test_open_graph_text_normalizes_case_and_decoded_whitespace(self) -> None:
        for field in ("og:title", "og:description", "og:url"):
            for value in ("&#9;&#10;", "&#160;"):
                with self.subTest(field=field, value=value), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    page = root / "index.html"
                    page.write_text(
                        f'<META PROPERTY="{field.upper()}" CONTENT="{value}">',
                        encoding="utf-8",
                    )
                    with patch.object(_MODULE, "ROOT", root), patch.object(
                        _MODULE, "site_origin", return_value=ORIGIN
                    ):
                        issues = _MODULE.audit_page(page)

                    self.assertIn(f"Blank {field}", issues)
                    self.assertNotIn(f"Missing {field}", issues)

    def test_offline_fallback_exempts_blank_and_missing_open_graph_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / "offline.html"
            page.write_text('<meta property="og:title" content=" ">', encoding="utf-8")
            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ):
                issues = _MODULE.audit_page(page)

            for field in ("og:title", "og:description", "og:url"):
                self.assertNotIn(f"Blank {field}", issues)
                self.assertNotIn(f"Missing {field}", issues)

    def test_open_graph_image_alt_is_required_nonblank_and_populated_values_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / "index.html"
            image = '<meta property="og:image" content="https://example.test/share.png">'

            page.write_text(image, encoding="utf-8")
            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ):
                issues = _MODULE.audit_page(page)
            self.assertIn("Missing og:image:alt", issues)

            for value in ("", "   ", "\n\t"):
                with self.subTest(value=value):
                    page.write_text(
                        image + f'<meta property="og:image:alt" content="{value}">',
                        encoding="utf-8",
                    )
                    with patch.object(_MODULE, "ROOT", root), patch.object(
                        _MODULE, "site_origin", return_value=ORIGIN
                    ):
                        issues = _MODULE.audit_page(page)
                    self.assertIn("Blank og:image:alt", issues)
                    self.assertNotIn("Missing og:image:alt", issues)

            page.write_text(
                image + '<meta property="og:image:alt" content="A bright yellow umbrella">',
                encoding="utf-8",
            )
            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ):
                issues = _MODULE.audit_page(page)
            self.assertNotIn("Missing og:image:alt", issues)
            self.assertNotIn("Blank og:image:alt", issues)


    def test_open_graph_image_alt_is_not_required_without_a_social_image(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / "index.html"
            page.write_text("<html></html>", encoding="utf-8")
            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ):
                issues = _MODULE.audit_page(page)

            self.assertNotIn("Missing og:image:alt", issues)
            self.assertNotIn("Blank og:image:alt", issues)

    def test_each_open_graph_image_root_requires_its_own_alt(self) -> None:
        for second_kind in ("og:image", "og:image:url"):
            for second_alt, expected in (
                ("", "Missing og:image:alt (image 2)"),
                ('<meta property="og:image:alt" content="  ">',
                 "Blank og:image:alt (image 2)"),
            ):
                with self.subTest(second_kind=second_kind, second_alt=second_alt), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    page = root / "index.html"
                    page.write_text(
                        '<meta property="og:image" content="https://external.test/first.png">'
                        '<meta property="og:image:alt" content="First image">'
                        f'<meta property="{second_kind}" content="https://external.test/second.png">'
                        + second_alt,
                        encoding="utf-8",
                    )
                    with patch.object(_MODULE, "ROOT", root), patch.object(
                        _MODULE, "site_origin", return_value=ORIGIN
                    ):
                        issues = _MODULE.audit_page(page)

                    alt_findings = [issue for issue in issues if "og:image:alt" in issue]
                    self.assertEqual(alt_findings, [expected])

    def test_secure_url_does_not_start_a_new_alt_group(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / "index.html"
            page.write_text(
                '<meta property="og:image:url" content="https://external.test/first.png">'
                '<meta property="og:image:secure_url" content="https://external.test/secure.png">'
                '<meta property="og:image:alt" content="First image">'
                '<meta property="og:image" content="https://external.test/second.png">'
                '<meta property="og:image:alt" content="Second image">',
                encoding="utf-8",
            )
            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ):
                issues = _MODULE.audit_page(page)

            self.assertFalse(any("og:image:alt" in issue for issue in issues))

    def test_orphan_alt_cannot_satisfy_a_later_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / "index.html"
            page.write_text(
                '<meta property="og:image:alt" content="Orphan description">'
                '<meta property="og:image" content="https://external.test/first.png">',
                encoding="utf-8",
            )
            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ):
                issues = _MODULE.audit_page(page)

            self.assertIn("Missing og:image:alt", issues)

    def test_duplicate_image_alts_report_any_blank_in_either_order(self) -> None:
        for blank_first in (True, False):
            with self.subTest(blank_first=blank_first), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                page = root / "index.html"
                blank = '<meta property="og:image:alt" content="&#9;&#160;">'
                valid = '<meta property="og:image:alt" content="Meaningful description">'
                page.write_text(
                    '<meta property="og:image" content="https://external.test/first.png">'
                    + (blank + valid if blank_first else valid + blank),
                    encoding="utf-8",
                )
                with patch.object(_MODULE, "ROOT", root), patch.object(
                    _MODULE, "site_origin", return_value=ORIGIN
                ):
                    issues = _MODULE.audit_page(page)

                self.assertEqual(issues.count("Blank og:image:alt"), 1)
                self.assertNotIn("Missing og:image:alt", issues)

    def test_image_alt_parser_handles_case_attribute_order_and_missing_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / "index.html"
            page.write_text(
                '<META CONTENT="https://external.test/image.png" PROPERTY="OG:IMAGE:URL">'
                '<META PROPERTY="OG:IMAGE:ALT">', encoding="utf-8"
            )
            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ):
                issues = _MODULE.audit_page(page)

            self.assertIn("Blank og:image:alt", issues)
            self.assertNotIn("Missing og:image:alt", issues)

    def test_offline_exempts_image_alt_requirements(self) -> None:
        for alt in ("", '<meta property="og:image:alt" content=" ">'):
            with self.subTest(alt=alt), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                page = root / "offline.html"
                page.write_text(
                    '<meta property="og:image" content="https://external.test/image.png">' + alt,
                    encoding="utf-8",
                )
                with patch.object(_MODULE, "ROOT", root), patch.object(
                    _MODULE, "site_origin", return_value=ORIGIN
                ):
                    issues = _MODULE.audit_page(page)

                self.assertFalse(any("og:image:alt" in issue for issue in issues))


    def test_later_og_images_with_missing_or_blank_content_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            images = root / "assets"
            images.mkdir(parents=True)
            (images / "hero.png").write_bytes(IMAGE_SIGNATURES["png"])
            page = root / "index.html"
            page.write_text(
                '<meta property="og:image" content="/assets/hero.png">'
                '<meta property="og:image">'
                '<meta property="og:image" content="">'
                '<meta property="og:image" content="   ">',
                encoding="utf-8",
            )
            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ):
                findings = [
                    issue for issue in _MODULE.audit_page(page)
                    if issue.startswith("og:image")
                ]

            self.assertEqual(len(findings), 3)
            self.assertTrue(all("missing a non-empty content URL" in x for x in findings))

    def test_external_og_image_url_alias_is_not_resolved_locally(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            page = root / "index.html"
            page.write_text(
                '<meta property="og:image:url" '
                'content="https://external.test/image.png">',
                encoding="utf-8",
            )
            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ), patch.object(_MODULE, "link_target", wraps=_MODULE.link_target) as resolve:
                findings = [
                    issue for issue in _MODULE.audit_page(page)
                    if issue.startswith("og:image")
                ]

            self.assertEqual(findings, [])
            resolve.assert_not_called()

    def test_external_og_image_secure_url_is_not_resolved_locally(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            page = root / "index.html"
            page.write_text(
                '<meta property="og:image:secure_url" '
                'content="https://external.test/image.png">',
                encoding="utf-8",
            )
            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ), patch.object(
                _MODULE, "link_target", wraps=_MODULE.link_target
            ) as resolve, patch(
                "socket.socket.connect", side_effect=AssertionError("unexpected network")
            ), patch(
                "socket.create_connection", side_effect=AssertionError("unexpected network")
            ):
                findings = [
                    issue for issue in _MODULE.audit_page(page)
                    if issue.startswith("og:image")
                ]

            self.assertEqual(findings, [])
            resolve.assert_not_called()

    def test_external_images_in_any_position_are_not_resolved_locally(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            images = root / "assets" / "social"
            images.mkdir(parents=True)
            (images / "hero.png").write_bytes(IMAGE_SIGNATURES["png"])
            local = f"{ORIGIN}/assets/social/hero.png"
            with patch.object(_MODULE, "link_target", wraps=_MODULE.link_target) as resolve:
                self.assertEqual(self.og_image_findings(
                    root, "https://external.test/first.png", local,
                    "https://glee-fully.tools.attacker.test/later.png"
                ), [])
            self.assertEqual(resolve.call_count, 1)
            self.assertEqual(resolve.call_args.args[0], local)

    def test_later_image_tag_attribute_order_quotes_and_entities(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            page = root / "index.html"
            images = root / "assets"
            images.mkdir(parents=True)
            (images / "hero.png").write_bytes(IMAGE_SIGNATURES["png"])
            page.write_text(
                '<meta property="og:image" content="/assets/hero.png">'
                "<META content='/assets/missing.png?v=1&amp;width=2' PROPERTY='og:image'>"
                '<!-- <meta property="og:image" content="/ignored.png"> -->',
                encoding="utf-8",
            )
            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ):
                findings = [x for x in _MODULE.audit_page(page) if x.startswith("og:image")]
            self.assertEqual(len(findings), 1)
            self.assertIn("/assets/missing.png?v=1&width=2", findings[0])

    def test_later_name_based_og_image_uses_the_metadata_key_policy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            images = root / "assets"
            images.mkdir(parents=True)
            (images / "hero.png").write_bytes(IMAGE_SIGNATURES["png"])
            page = root / "index.html"
            page.write_text(
                '<meta property="og:image" content="/assets/hero.png">'
                '<meta name="og:image" content="/assets/missing.png">'
                '<meta name="og:image" content="/%2e%2e/outside.png">'
                '<meta name="og:image" content="https://external.test/image.png">',
                encoding="utf-8",
            )
            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ):
                findings = [x for x in _MODULE.audit_page(page) if x.startswith("og:image")]
            self.assertEqual(len(findings), 2)
            self.assertIn("/assets/missing.png", findings[0])
            self.assertIn("/%2e%2e/outside.png", findings[1])

    def assert_invalid_og_images_stay_inside_root(
        self, root: Path, urls: tuple[str, ...]
    ) -> None:
        root_resolved = root.resolve()
        original_exists = Path.exists
        original_is_file = Path.is_file

        def guard_outside(method):
            def checked(path):
                resolved = path.resolve()
                try:
                    resolved.relative_to(root_resolved)
                except ValueError as exc:
                    raise AssertionError(
                        f"auditor checked a file outside the repository: {path}"
                    ) from exc
                return method(path)
            return checked

        with patch.object(
            Path, "exists", autospec=True, side_effect=guard_outside(original_exists)
        ), patch.object(
            Path, "is_file", autospec=True, side_effect=guard_outside(original_is_file)
        ):
            for url in urls:
                with self.subTest(url=url):
                    findings = self.og_image_findings(root, url)
                    self.assertEqual(len(findings), 1)
                    self.assertIn(
                        "does not resolve to a safe file inside", findings[0]
                    )
                    self.assertIn(url, findings[0])

    def test_local_og_images_resolve_queries_and_percent_encoded_filenames(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            image_dir = root / "assets" / "social"
            image_dir.mkdir(parents=True)
            (image_dir / "hero.png").write_bytes(IMAGE_SIGNATURES["png"])
            (image_dir / "hero card.png").write_bytes(IMAGE_SIGNATURES["png"])
            for url in (
                f"{ORIGIN}/assets/social/hero.png?v=2",
                f"{ORIGIN}/assets/social/hero%20card.png?width=1200",
            ):
                with self.subTest(url=url):
                    self.assertEqual(self.og_image_findings(root, url), [])

    def test_existing_non_image_file_is_reported_even_when_it_has_image_extension(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            image_dir = root / "assets" / "social"
            image_dir.mkdir(parents=True)
            (image_dir / "document.png").write_bytes(b"%PDF-1.7\n")
            url = f"{ORIGIN}/assets/social/document.png"

            findings = self.og_image_findings(root, url)

            self.assertEqual(len(findings), 1)
            self.assertIn("supported image signature", findings[0])
            self.assertIn("PNG, JPEG, GIF, WebP", findings[0])

    def test_supported_social_image_signatures_are_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            image_dir = root / "assets" / "social"
            image_dir.mkdir(parents=True)
            for extension, signature in IMAGE_SIGNATURES.items():
                (image_dir / f"card.{extension}").write_bytes(signature)

            for extension in IMAGE_SIGNATURES:
                with self.subTest(extension=extension):
                    url = f"{ORIGIN}/assets/social/card.{extension}"
                    self.assertEqual(self.og_image_findings(root, url), [])

    def test_all_webp_encodings_report_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            image_dir = root / "assets" / "social"
            image_dir.mkdir(parents=True)
            for encoding in ("VP8X", "VP8 ", "VP8L"):
                with self.subTest(encoding=encoding):
                    filename = f"{encoding.strip().lower()}.webp"
                    (image_dir / filename).write_bytes(
                        social_image_fixture("webp", webp_encoding=encoding)
                    )
                    findings = self.og_image_findings(
                        root, f"{ORIGIN}/assets/social/{filename}"
                    )
                    self.assertEqual(findings, [])

    def test_matching_og_image_dimensions_are_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            image_dir = root / "assets" / "social"
            image_dir.mkdir(parents=True)
            (image_dir / "hero.png").write_bytes(
                social_image_fixture("png", width=1200, height=630)
            )

            findings = self.og_image_findings(
                root, f"{ORIGIN}/assets/social/hero.png",
                declared_width="1200", declared_height="630"
            )

            self.assertEqual(findings, [])


    def test_missing_malformed_and_mismatched_og_image_dimensions_are_reported(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            image_dir = root / "assets" / "social"
            image_dir.mkdir(parents=True)
            (image_dir / "hero.png").write_bytes(
                social_image_fixture("png", width=1200, height=630)
            )
            url = f"{ORIGIN}/assets/social/hero.png"

            missing = self.og_image_findings(
                root, url, declared_width=None, declared_height=None,
                include_recommendations=True,
            )
            self.assertEqual(len(missing), 2)
            self.assertTrue(
                any("Recommended og:image:width for local images" in issue for issue in missing)
            )
            self.assertTrue(
                any("Recommended og:image:height for local images" in issue for issue in missing)
            )

            malformed = self.og_image_findings(
                root, url, declared_width="wide", declared_height="0"
            )
            self.assertEqual(len(malformed), 2)
            self.assertTrue(
                any(
                    "og:image:width declaration is invalid or exceeds the supported range" in issue
                    for issue in malformed
                )
            )
            self.assertTrue(
                any(
                    "og:image:height declaration is invalid or exceeds the supported range" in issue
                    for issue in malformed
                )
            )

            mismatched = self.og_image_findings(
                root, url, declared_width="1201", declared_height="631"
            )
            self.assertEqual(len(mismatched), 2)
            self.assertTrue(
                any("og:image:width does not match the local image" in issue for issue in mismatched)
            )
            self.assertTrue(
                any("og:image:height does not match the local image" in issue for issue in mismatched)
            )

    def test_dimension_values_are_bounded_positive_ascii_decimals(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            images = root / "assets"
            images.mkdir()
            (images / "hero.png").write_bytes(IMAGE_SIGNATURES["png"])
            url = f"{ORIGIN}/assets/hero.png"
            for value in ("", "  ", "0", "-1", "1.5", "１２", "9" * 5000):
                with self.subTest(value=value[:30]):
                    issues = self.og_image_findings(
                        root, url, declared_width=value, declared_height="630",
                        include_recommendations=True,
                    )
                    self.assertEqual(
                        issues,
                        ["og:image:width declaration is invalid or exceeds the supported range"],
                    )
            self.assertEqual(
                self.og_image_findings(root, url, declared_width=" 1200 ", declared_height="630"),
                [],
            )

    def test_dimensions_are_attached_to_each_root_not_secure_alternate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            images = root / "assets"
            images.mkdir()
            for name in ("first.png", "second.png", "secure.png"):
                (images / name).write_bytes(IMAGE_SIGNATURES["png"])
            page = root / "index.html"
            page.write_text(
                '<meta property="og:image" content="/assets/first.png">'
                '<meta property="og:image:width" content="1200">'
                '<meta property="og:image:height" content="630">'
                '<meta property="og:image:url" content="/assets/second.png">'
                '<meta property="og:image:secure_url" content="/assets/secure.png">'
                '<meta property="og:image:width" content="1201">'
                '<meta property="og:image:height" content="630">', encoding="utf-8"
            )
            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ):
                issues = _MODULE.audit_page(page)

            dimension_findings = [
                issue for issue in issues
                if issue.startswith(("og:image:width", "og:image:height", "Recommended og:image:"))
            ]
            self.assertEqual(dimension_findings, ["og:image:width does not match the local image (image 2)"])

    def test_every_declared_dimension_is_checked_without_recommending_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            images = root / "assets"
            images.mkdir()
            (images / "hero.png").write_bytes(IMAGE_SIGNATURES["png"])
            page = root / "index.html"
            page.write_text(
                '<meta property="og:image" content="/assets/hero.png">'
                '<meta property="og:image:width" content="1200">'
                '<meta property="og:image:width" content="1201">'
                '<meta property="og:image:height" content="630">'
                '<meta property="og:image:height" content="">', encoding="utf-8"
            )
            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ):
                issues = _MODULE.audit_page(page)

            findings = [issue for issue in issues if issue.startswith(("og:image:width", "og:image:height", "Recommended og:image:"))]
            self.assertEqual(findings, [
                "og:image:width does not match the local image",
                "og:image:height declaration is invalid or exceeds the supported range",
            ])

    def test_external_image_dimensions_do_not_trigger_local_or_network_access(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / "index.html"
            page.write_text(
                '<meta property="og:image" content="https://external.test/image.png">'
                '<meta property="og:image:width" content="invalid">', encoding="utf-8"
            )
            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ), patch.object(_MODULE, "link_target", wraps=_MODULE.link_target) as resolve, patch(
                "socket.socket.connect", side_effect=AssertionError("unexpected network")
            ), patch("socket.create_connection", side_effect=AssertionError("unexpected network")):
                issues = _MODULE.audit_page(page)

            resolve.assert_not_called()
            self.assertFalse(any(issue.startswith(("og:image:width", "og:image:height", "Recommended og:image:")) for issue in issues))

    def test_dimension_diagnostics_do_not_echo_hostile_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            images = root / "assets"
            images.mkdir()
            (images / "hero.png").write_bytes(IMAGE_SIGNATURES["png"])
            page = root / "index.html"
            page.write_text(
                '<meta property="og:image" content="/assets/hero.png">'
                '<meta property="og:image:width" content="1200&#10;`Injected text`">'
                '<meta property="og:image:height" content="631">', encoding="utf-8"
            )
            with patch.object(_MODULE, "ROOT", root), patch.object(
                _MODULE, "site_origin", return_value=ORIGIN
            ):
                issues = _MODULE.audit_page(page)

            findings = [issue for issue in issues if issue.startswith(("og:image:width", "og:image:height"))]
            self.assertEqual(findings, [
                "og:image:width declaration is invalid or exceeds the supported range",
                "og:image:height does not match the local image",
            ])
            self.assertFalse(any("Injected text" in issue for issue in findings))


    def test_undersized_local_social_image_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            image_dir = root / "assets" / "social"
            image_dir.mkdir(parents=True)
            (image_dir / "small.png").write_bytes(
                social_image_fixture("png", width=600, height=315)
            )

            findings = self.og_image_findings(
                root, f"{ORIGIN}/assets/social/small.png"
            )

            self.assertEqual(len(findings), 1)
            self.assertIn("og:image is 600x315", findings[0])
            self.assertIn("minimum is 1200x630", findings[0])

    def test_local_social_image_with_unsuitable_aspect_ratio_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            image_dir = root / "assets" / "social"
            image_dir.mkdir(parents=True)
            (image_dir / "square.jpg").write_bytes(
                social_image_fixture("jpg", width=1200, height=1200)
            )

            findings = self.og_image_findings(
                root, f"{ORIGIN}/assets/social/square.jpg"
            )

            self.assertEqual(len(findings), 1)
            self.assertIn("aspect ratio is 1.000:1", findings[0])
            self.assertIn("expected 1.85:1–1.96:1", findings[0])

    def test_truncated_supported_social_image_is_reported_as_malformed(self) -> None:
        malformed_images = {
            "png": b"\x89PNG\r\n\x1a\n",
            "jpg": b"\xff\xd8\xff",
            "gif": b"GIF89a",
            "webp": b"RIFF\x00\x00\x00\x00WEBP",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            image_dir = root / "assets" / "social"
            image_dir.mkdir(parents=True)
            for extension, data in malformed_images.items():
                with self.subTest(extension=extension):
                    (image_dir / f"broken.{extension}").write_bytes(data)

                    findings = self.og_image_findings(
                        root, f"{ORIGIN}/assets/social/broken.{extension}"
                    )

                    self.assertEqual(len(findings), 1)
                    self.assertIn("dimensions could not be inspected", findings[0])
                    self.assertIn("malformed or truncated", findings[0])

    def test_og_image_directory_routes_do_not_accept_html_index_fallbacks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            image_route = root / "assets" / "social" / "album"
            image_route.mkdir(parents=True)
            (image_route / "index.html").write_text("<html></html>", encoding="utf-8")
            url = f"{ORIGIN}/assets/social/album/"
            findings = self.og_image_findings(root, url)
            self.assertEqual(len(findings), 1)
            self.assertIn("not an image file", findings[0])

    def test_external_og_image_is_not_resolved_as_a_local_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            url = "https://glee-fully.tools.attacker.test/assets/social/missing.png"
            with patch.object(_MODULE, "link_target", wraps=_MODULE.link_target) as resolve:
                self.assertEqual(self.og_image_findings(root, url), [])
            resolve.assert_not_called()

    def test_traversal_and_missing_og_images_are_actionable_without_outside_checks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            image_dir = root / "assets" / "social"
            image_dir.mkdir(parents=True)
            outside = Path(directory) / "outside.png"
            outside.write_bytes(b"outside")
            self.assert_invalid_og_images_stay_inside_root(
                root,
                (
                    f"{ORIGIN}/%2e%2e/outside.png",
                    f"{ORIGIN}/assets/social/missing.png",
                ),
            )

    def test_symlink_escaping_og_image_is_actionable_without_outside_checks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            image_dir = root / "assets" / "social"
            image_dir.mkdir(parents=True)
            outside = Path(directory) / "outside.png"
            outside.write_bytes(b"outside")
            escaped_link = image_dir / "escaped.png"
            try:
                escaped_link.symlink_to(outside)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"File symlinks unavailable: {exc}")
            self.assert_invalid_og_images_stay_inside_root(
                root, (f"{ORIGIN}/assets/social/escaped.png",)
            )

    def test_symlinked_root_keeps_report_display_relative(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            actual = Path(directory) / "actual"
            actual.mkdir()
            alias = Path(directory) / "alias"
            try:
                alias.symlink_to(actual, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"Directory symlinks unavailable: {exc}")
            console = io.StringIO()
            self.assertEqual(self.run_cli_fixture(alias, "reports/audit.md", console), 0)
            self.assertTrue((actual / "reports/audit.md").is_file())
            self.assertIn("Report written to reports/audit.md", console.getvalue())
            self.assertIn("Total issues found: 1", console.getvalue())

    def test_post_merge_hook_has_durable_lf_checkout_policy(self) -> None:
        repo = _SCRIPT.parent.parent
        attributes = subprocess.check_output(
            ["git", "check-attr", "eol", "--", "scripts/post-merge.sh"],
            cwd=repo, text=True,
        )
        self.assertEqual(attributes.strip(), "scripts/post-merge.sh: eol: lf")
        self.assertNotIn(b"\r\n", (repo / "scripts/post-merge.sh").read_bytes())

    def test_utf8_index_and_offline_fallback_share_discovery_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            about = root / "about" / "index.html"
            offline = root / "offline.html"
            about.parent.mkdir(parents=True)
            about.write_text("<title>About</title>", encoding="utf-8")
            offline.write_text("<title>Offline</title>", encoding="utf-8")
            (root / "assets" / "data").mkdir(parents=True)
            (root / "assets" / "data" / "search-index.json").write_text(
                json.dumps(
                    {"pages": [{"url": "https://glee-fully.tools/about/", "title": "Café"}]},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (root / "sitemap.xml").write_text(
                "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"
                "<url><loc>https://glee-fully.tools/about/</loc></url></urlset>",
                encoding="utf-8",
            )

            old_root = _MODULE.ROOT
            try:
                _MODULE.ROOT = root
                files = [about, offline]
                self.assertEqual(_MODULE.reconcile_search_index(files), [])
                self.assertEqual(_MODULE.reconcile_sitemap(files), ([], [], []))
            finally:
                _MODULE.ROOT = old_root

    def test_invalid_utf8_index_is_reported_without_aborting_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index = root / "assets" / "data" / "search-index.json"
            index.parent.mkdir(parents=True)
            index.write_bytes(b'{"pages": [{"title": "\xff"}]}')
            page = root / "about" / "index.html"
            console = io.StringIO()
            with ExitStack() as stack:
                stack.enter_context(patch.object(_MODULE, "ROOT", root))
                findings = _MODULE.reconcile_search_index([page])
                self.assertEqual(len(findings), 1)
                self.assertIn("search-index.json is unreadable:", findings[0])
                self.assertIn("utf-8", findings[0])
                stack.enter_context(patch.object(_MODULE, "iter_html_files", return_value=[page]))
                stack.enter_context(patch.object(_MODULE, "audit_page", return_value=["Missing description"]))
                stack.enter_context(patch.object(_MODULE, "reconcile_sitemap", return_value=([], [], [])))
                freshness = stack.enter_context(patch.object(
                    _MODULE, "check_search_index_freshness", return_value=[],
                ))
                cruft = stack.enter_context(patch.object(
                    _MODULE, "scan_repo_cruft", return_value=["Unexpected fixture file"],
                ))
                stack.enter_context(patch.object(
                    _MODULE.sys, "argv", [str(_SCRIPT), "--report", "reports/audit.md"],
                ))
                stack.enter_context(patch.object(_MODULE.sys, "stdout", console))
                stack.enter_context(patch.object(_MODULE.sys, "stderr", io.StringIO()))
                self.assertEqual(_MODULE.main(), 0, "Unreadable-index findings remain advisory")
                freshness.assert_called_once_with([page])
                cruft.assert_called_once_with()
            report = (root / "reports" / "audit.md").read_text(encoding="utf-8")
            self.assertIn(findings[0], report)
            self.assertIn("Missing description", report)
            self.assertIn("Unexpected fixture file", report)
            self.assertIn("Total issues found: 3", console.getvalue())
            self.assertEqual(index.read_bytes(), b'{"pages": [{"title": "\xff"}]}')

    def assert_unreadable_index_report(self, root: Path, detail: str) -> None:
        page = root / "about" / "index.html"
        console = io.StringIO()
        with ExitStack() as stack:
            stack.enter_context(patch.object(_MODULE, "ROOT", root))
            findings = _MODULE.reconcile_search_index([page])
            self.assertEqual(len(findings), 1)
            self.assertTrue(findings[0].startswith("search-index.json is unreadable:"))
            self.assertIn(detail, findings[0])
            stack.enter_context(patch.object(_MODULE, "iter_html_files", return_value=[page]))
            stack.enter_context(patch.object(_MODULE, "audit_page", return_value=["Missing description"]))
            stack.enter_context(patch.object(_MODULE, "reconcile_sitemap", return_value=([], [], [])))
            freshness = stack.enter_context(patch.object(
                _MODULE, "check_search_index_freshness", return_value=[],
            ))
            cruft = stack.enter_context(patch.object(
                _MODULE, "scan_repo_cruft", return_value=["Unexpected fixture file"],
            ))
            stack.enter_context(patch.object(
                _MODULE.sys, "argv", [str(_SCRIPT), "--report", "reports/audit.md"],
            ))
            stack.enter_context(patch.object(_MODULE.sys, "stdout", console))
            stack.enter_context(patch.object(_MODULE.sys, "stderr", io.StringIO()))
            self.assertEqual(_MODULE.main(), 0, "Unreadable-index findings remain advisory")
            freshness.assert_called_once_with([page])
            cruft.assert_called_once_with()
        report = (root / "reports" / "audit.md").read_text(encoding="utf-8")
        self.assertIn(findings[0], report)
        self.assertIn("Missing description", report)
        self.assertIn("Unexpected fixture file", report)
        self.assertIn("Report written to reports/audit.md", console.getvalue())
        self.assertIn("Total issues found: 3", console.getvalue())

    def test_malformed_json_index_is_reported_without_aborting_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index = root / "assets" / "data" / "search-index.json"
            index.parent.mkdir(parents=True)
            content = '{"pages": [}'
            index.write_text(content, encoding="utf-8")
            self.assert_unreadable_index_report(root, "Expecting value")
            self.assertEqual(index.read_text(encoding="utf-8"), content)

    def test_unexpected_pages_shape_is_reported_without_aborting_audit(self) -> None:
        for pages, shape in [({"url": "/about/"}, "dict"), (None, "NoneType")]:
            with self.subTest(shape=shape), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                index = root / "assets" / "data" / "search-index.json"
                index.parent.mkdir(parents=True)
                content = json.dumps({"pages": pages})
                index.write_text(content, encoding="utf-8")
                page = root / "about" / "index.html"
                console = io.StringIO()
                finding = f"search-index.json has unexpected shape: {shape}"
                with ExitStack() as stack:
                    stack.enter_context(patch.object(_MODULE, "ROOT", root))
                    self.assertEqual(_MODULE.reconcile_search_index([page]), [finding])
                    stack.enter_context(patch.object(
                        _MODULE, "iter_html_files", return_value=[page],
                    ))
                    stack.enter_context(patch.object(
                        _MODULE, "audit_page", return_value=["Missing description"],
                    ))
                    stack.enter_context(patch.object(
                        _MODULE, "reconcile_sitemap", return_value=([], [], []),
                    ))
                    freshness = stack.enter_context(patch.object(
                        _MODULE, "check_search_index_freshness",
                        return_value=["Fixture search-index freshness finding"],
                    ))
                    cruft = stack.enter_context(patch.object(
                        _MODULE, "scan_repo_cruft", return_value=["Unexpected fixture file"],
                    ))
                    stack.enter_context(patch.object(
                        _MODULE.sys, "argv", [str(_SCRIPT), "--report", "reports/audit.md"],
                    ))
                    stack.enter_context(patch.object(_MODULE.sys, "stdout", console))
                    stack.enter_context(patch.object(_MODULE.sys, "stderr", io.StringIO()))
                    self.assertEqual(_MODULE.main(), 0, "Unexpected-shape findings remain advisory")
                    freshness.assert_called_once_with([page])
                    cruft.assert_called_once_with()
                report = (root / "reports" / "audit.md").read_text(encoding="utf-8")
                self.assertIn(finding, report)
                self.assertIn("Missing description", report)
                self.assertIn("Fixture search-index freshness finding", report)
                self.assertIn("Unexpected fixture file", report)
                self.assertIn("**Total issues:** 4", report)
                self.assertIn("Report written to reports/audit.md", console.getvalue())
                self.assertIn("Total issues found: 4", console.getvalue())
                self.assertEqual(index.read_text(encoding="utf-8"), content)

    def test_index_read_oserror_is_reported_without_aborting_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index = root / "assets" / "data" / "search-index.json"
            index.parent.mkdir(parents=True)
            content = '{"pages": []}'
            index.write_text(content, encoding="utf-8")
            original_read_text = Path.read_text

            def read_text(path, *args, **kwargs):
                if path == index:
                    raise OSError("simulated index read failure")
                return original_read_text(path, *args, **kwargs)

            with patch.object(Path, "read_text", autospec=True, side_effect=read_text) as read:
                self.assert_unreadable_index_report(root, "simulated index read failure")
                index_reads = [call for call in read.call_args_list if call.args[0] == index]
                self.assertEqual(len(index_reads), 2)
                for call in index_reads:
                    self.assertEqual(call.kwargs, {"encoding": "utf-8"})
            self.assertEqual(index.read_text(encoding="utf-8"), content)

    def test_freshness_uses_generator_check_instead_of_mtime(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index = root / "assets" / "data" / "search-index.json"
            builder = root / "scripts" / "build-search-index.py"
            index.parent.mkdir(parents=True)
            builder.parent.mkdir(parents=True)
            index.write_text('{"pages": []}', encoding="utf-8")
            builder.write_text("", encoding="utf-8")
            old_root = _MODULE.ROOT
            try:
                _MODULE.ROOT = root
                with patch.object(
                    _MODULE.subprocess,
                    "run",
                    return_value=type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
                ) as run:
                    self.assertEqual(_MODULE.check_search_index_freshness([]), [])
                self.assertEqual(run.call_args.args[0][-1], "--check")
            finally:
                _MODULE.ROOT = old_root


if __name__ == "__main__":
    unittest.main()

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
        self, root: Path, url: str, *later_urls: str, image_type: str = ""
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
                for image_url in (url, *later_urls)
            ),
            encoding="utf-8",
        )
        with patch.object(_MODULE, "ROOT", root), patch.object(
            _MODULE, "site_origin", return_value=ORIGIN
        ):
            return [
                issue for issue in _MODULE.audit_page(page)
                if issue.startswith("og:image")
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
                findings = [
                    issue for issue in _MODULE.audit_page(page)
                    if issue.startswith("og:image")
                ]

            self.assertEqual(len(findings), 1)
            self.assertIn("/%2e%2e/outside.png", findings[0])
            self.assertIn("safe file inside", findings[0])

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

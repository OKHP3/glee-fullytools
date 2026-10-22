#!/usr/bin/env python3
"""
audit-site.py — static-site auditor for glee-fully.tools.

Walks every .html file in the repo (excluding .local/, attached_assets/,
node_modules/, .cache/, .git/, .vscode/) and produces a Markdown report.

Per-page checks actually emitted as issues:
  * <title> length (<=70) and presence
  * <meta name="description"> length (<=165) and presence
  * exactly one <h1>
  * heading level order — no level may jump by more than 1 going
    deeper (e.g. h3 after h1 is a violation; h1 after h3 is fine).
    Headings inside <footer> are excluded because the footer uses a
    well-validated h3/h4 pattern that does not reflect the page's
    content outline.
  * canonical link presence
  * required Open Graph fields: og:title, og:description, og:image, og:url
  * <html lang="..."> presence
  * every <img> has alt, width, and height attributes
  * external target="_blank" links carry rel="noopener noreferrer"
  * known placeholder strings (ASK-JAMIE-GPT-ID-HERE, the old SearchAction
    target ?s={search_term_string}, generic YOUR-...)
  * theme-color resolves to the Glee-fully.tools brand color (#d35b2d)
  * any page embedding a Mermaid diagram carries the OKH affiliate
    referral link (mermaidchart.cello.so) styled with `mermaid-referral-link`
  * bare or generic link text ("read more", "click here", "here",
    bare "→", etc.) — aria-label is used as the accessible text
    when present, so navigation arrows that include aria-label
    context are not flagged
  * no duplicate `id="..."` attributes within a single page (would
    break anchor navigation and JS lookups)
  * every in-page anchor link (`href="#foo"`) resolves to a real
    `id="foo"` on the same page
  * og:image URL (when it points to glee-fully.tools) resolves to a
    supported raster image (PNG, JPEG, GIF, or WebP) on disk, checked by
    file signature (URL-decoded to handle %20 etc.)

Cross-file / repo-wide checks:
  * no leftover backup / OS-junk files (.bak, .orig, .swp, .DS_Store, ~)
    in production directories
  * search-index.json mtime is newer than every public HTML file
    (catches stale indexes after content edits)

Modern (2025/2026) baseline checks — see also scripts/apply-modern-baseline.py:
  * every page carries `<meta name="referrer">` (privacy)
  * every page carries `<meta http-equiv="Content-Security-Policy">`
    with the expected allow-list keywords
  * every <img> declares a `loading=` attribute (lazy or eager) — no
    silent defaults
  * theme.css contains a global `prefers-reduced-motion` umbrella rule

Cross-file reconciliation (best-effort; failures are reported as issues
rather than crashing the run):
  * sitemap.xml entries vs HTML files on disk
  * search-index.json entries vs HTML files on disk

Usage:
    python3 scripts/audit-site.py
    python3 scripts/audit-site.py --report assets/docs/audit-report.md
    python3 scripts/audit-site.py --quiet
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from urllib.parse import urlsplit
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Tuple
from xml.etree import ElementTree as ET

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from public_inventory import collect_html_files, site_origin
from public_paths import discovery_path, link_target

ROOT = Path(__file__).resolve().parent.parent
EXCLUDE_DIRS = {".local", ".agents", "attached_assets", "node_modules", ".cache",
                ".pythonlibs", ".git", "templates"}
# These utility fallbacks are intentionally public files but are not discoverable
# content: they belong neither in the sitemap nor in the client-side search index.
EXCLUDE_FROM_DISCOVERY = {"404.html", "under-construction.html", "offline.html"}
EXCLUDE_FROM_SITEMAP = EXCLUDE_FROM_DISCOVERY
EXCLUDE_FROM_SEARCH_INDEX = EXCLUDE_FROM_DISCOVERY

# Title / description recommended length budgets
TITLE_MAX = 70
DESC_MAX = 165

# Brand-correct theme color
EXPECTED_THEME_COLOR = "#d35b2d"
EXPECTED_BG_COLOR = "#f5f0ea"

# Social-preview support is intentionally limited to widely supported raster
# formats. SVG and other formats are excluded because major sharing platforms
# do not consistently render them as social cards.
# The site's shared sharing card is 1200x630. Require at least that many pixels
# in each dimension and allow small crop/rounding differences around its 1.90:1
# shape (1.85:1–1.96:1).
SOCIAL_IMAGE_MIN_WIDTH = 1200
SOCIAL_IMAGE_MIN_HEIGHT = 630
SOCIAL_IMAGE_MIN_ASPECT_RATIO = 1.85
SOCIAL_IMAGE_MAX_ASPECT_RATIO = 1.96
SOCIAL_IMAGE_SIGNATURES = {
    "PNG": lambda header: header.startswith(b"\x89PNG\r\n\x1a\n"),
    "JPEG": lambda header: header.startswith(b"\xff\xd8\xff"),
    "GIF": lambda header: header.startswith((b"GIF87a", b"GIF89a")),
    "WebP": lambda header: (
        len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP"
    ),
}


def _social_image_dimensions(image_file, image_format: str) -> Tuple[int, int] | None:
    """Read raster dimensions from a local image header; return None if malformed."""
    image_file.seek(0)
    if image_format == "PNG":
        header = image_file.read(24)
        if (
            len(header) < 24
            or header[:8] != b"\x89PNG\r\n\x1a\n"
            or int.from_bytes(header[8:12], "big") != 13
            or header[12:16] != b"IHDR"
        ):
            return None
        width = int.from_bytes(header[16:20], "big")
        height = int.from_bytes(header[20:24], "big")
    elif image_format == "GIF":
        header = image_file.read(13)
        if len(header) < 13 or header[:6] not in (b"GIF87a", b"GIF89a"):
            return None
        width = int.from_bytes(header[6:8], "little")
        height = int.from_bytes(header[8:10], "little")
    elif image_format == "WebP":
        header = image_file.read(30)
        if len(header) < 20 or header[:4] != b"RIFF" or header[8:12] != b"WEBP":
            return None
        chunk_type = header[12:16]
        chunk_size = int.from_bytes(header[16:20], "little")
        riff_size = int.from_bytes(header[4:8], "little")
        if riff_size < 12 + chunk_size:
            return None
        if chunk_type == b"VP8X" and chunk_size >= 10 and len(header) >= 30:
            width = 1 + int.from_bytes(header[24:27], "little")
            height = 1 + int.from_bytes(header[27:30], "little")
        elif (
            chunk_type == b"VP8 "
            and chunk_size >= 10
            and len(header) >= 30
        ):
            if header[23:26] != b"\x9d\x01\x2a":
                return None
            width = int.from_bytes(header[26:28], "little") & 0x3FFF
            height = int.from_bytes(header[28:30], "little") & 0x3FFF
        elif (
            chunk_type == b"VP8L"
            and chunk_size >= 5
            and len(header) >= 25
        ):
            if header[20] != 0x2F:
                return None
            width = 1 + header[21] + ((header[22] & 0x3F) << 8)
            height = 1 + (header[22] >> 6) + (header[23] << 2) + (
                (header[24] & 0x0F) << 10
            )
        else:
            return None
    elif image_format == "JPEG":
        # JPEG dimensions are stored in a Start Of Frame segment, which may
        # follow variable-sized metadata segments.
        image_file.seek(2)
        while True:
            marker_prefix = image_file.read(1)
            if marker_prefix != b"\xff":
                if not marker_prefix:
                    return None
                continue
            marker_byte = image_file.read(1)
            while marker_byte == b"\xff":
                marker_byte = image_file.read(1)
            if not marker_byte:
                return None
            marker = marker_byte[0]
            if marker in {0xD8, 0xD9, 0x01} or 0xD0 <= marker <= 0xD7:
                if marker == 0xD9:
                    return None
                continue
            if marker == 0xDA:  # Start Of Scan before dimensions is malformed.
                return None
            length_bytes = image_file.read(2)
            if len(length_bytes) != 2:
                return None
            segment_length = int.from_bytes(length_bytes, "big")
            if segment_length < 2:
                return None
            segment = image_file.read(segment_length - 2)
            if len(segment) != segment_length - 2:
                return None
            is_start_of_frame = marker in {
                0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
            }
            if is_start_of_frame:
                if len(segment) < 5:
                    return None
                height = int.from_bytes(segment[1:3], "big")
                width = int.from_bytes(segment[3:5], "big")
                break
    else:  # pragma: no cover - callers use SOCIAL_IMAGE_SIGNATURES
        return None

    if width <= 0 or height <= 0:
        return None
    return width, height


def iter_html_files() -> List[Path]:
    return collect_html_files(ROOT)


class PageParser(HTMLParser):
    """Lightweight extractor for the bits we need to audit."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._in_title = False
        self.h1_count = 0
        self._in_h1 = False
        # heading-order tracking (footer headings excluded)
        self.headings: List[int] = []   # ordered heading levels outside <footer>
        self._in_footer: int = 0        # nesting depth inside <footer>
        self.metas: Dict[str, str] = {}
        self.og_images: List[Dict[str, str]] = []
        self._current_og_image: int | None = None
        self.canonical = ""
        self.images: List[Dict[str, str]] = []
        self.external_links: List[Dict[str, str]] = []
        self.placeholder_hits: List[str] = []
        self.has_jsonld_website = False
        self.has_jsonld_breadcrumb = False
        self.has_jsonld_article = False
        self._jsonld_collect = False
        self._jsonld_buf: List[str] = []

    def handle_starttag(self, tag: str, attrs):
        a = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "h1":
            self.h1_count += 1
            self._in_h1 = True
            if self._in_footer == 0:
                self.headings.append(1)
        elif tag == "footer":
            self._in_footer += 1
        elif tag in ("h2", "h3", "h4", "h5", "h6"):
            if self._in_footer == 0:
                self.headings.append(int(tag[1]))
        elif tag == "meta":
            key = a.get("name") or a.get("property") or a.get("http-equiv")
            if key and key.lower() in {
                "og:image",
                "og:image:url",
                "og:image:secure_url",
            }:
                self.og_images.append(
                    {"url": a.get("content", "") or "", "type": ""}
                )
                self._current_og_image = len(self.og_images) - 1
            elif key and key.lower() == "og:image:type":
                if self._current_og_image is not None:
                    self.og_images[self._current_og_image]["type"] = (
                        a.get("content", "") or ""
                    )
            if key:
                self.metas[key.lower()] = a.get("content", "") or ""
        elif tag == "link" and a.get("rel", "").lower() == "canonical":
            self.canonical = a.get("href", "") or ""
        elif tag == "img":
            self.images.append(
                {
                    "src": a.get("src", ""),
                    "alt": a.get("alt"),
                    "width": a.get("width"),
                    "height": a.get("height"),
                    "loading": a.get("loading"),
                }
            )
        elif tag == "a":
            href = a.get("href", "") or ""
            if a.get("target") == "_blank" and href.startswith(("http://", "https://")):
                rel = (a.get("rel") or "").lower()
                self.external_links.append({"href": href, "rel": rel})
        elif tag == "script" and a.get("type") == "application/ld+json":
            self._jsonld_collect = True
            self._jsonld_buf = []

    def handle_endtag(self, tag: str):
        if tag == "title":
            self._in_title = False
        elif tag == "h1":
            self._in_h1 = False
        elif tag == "footer":
            self._in_footer = max(0, self._in_footer - 1)
        elif tag == "script" and self._jsonld_collect:
            self._jsonld_collect = False
            blob = "".join(self._jsonld_buf).strip()
            if '"WebSite"' in blob:
                self.has_jsonld_website = True
            if '"BreadcrumbList"' in blob:
                self.has_jsonld_breadcrumb = True
            if '"Article"' in blob or '"NewsArticle"' in blob:
                self.has_jsonld_article = True

    def handle_data(self, data: str):
        if self._in_title:
            self.title += data
        if self._jsonld_collect:
            self._jsonld_buf.append(data)


PLACEHOLDER_PATTERNS = [
    ("YOUR-GLEE-PLACEHOLDER", "Generic placeholder"),
    ("?s={search_term_string}", "Old SearchAction target"),
    ("YOUR-", "Generic placeholder"),
]
BARE_NOOPENER = re.compile(r'\brel="noopener"(?!\s*noreferrer)')

# Link text patterns that are bare/generic and fail WCAG 2.4.4.
# aria-label overrides visible text, so labeled arrows are safe.
BARE_LINK_TEXTS = frozenset({
    "read more", "click here", "here", "→",
    "↑", "↓", "←", "↗", "↘",
    "more", "learn more", "click",
})


def _og_image_issues(
    url: str, declared_type: str, source_dir: Path, root: Path, origin: str
) -> List[str]:
    """Validate local og:image paths and signatures without fetching URLs."""
    if not url.strip():
        return ["og:image declaration is missing a non-empty content URL"]

    try:
        parsed = urlsplit(url)
        expected_origin = urlsplit(origin)
    except ValueError:
        return [f"og:image URL is malformed or unsafe: {url}"]

    if parsed.scheme or parsed.netloc:
        actual_origin = (parsed.scheme or expected_origin.scheme, parsed.netloc)
        if actual_origin != (expected_origin.scheme, expected_origin.netloc):
            return []

    target = link_target(url, source_dir, root, origin)
    if target is None:
        return [(
            "og:image path does not resolve to a safe file inside "
            f"the repository: {url}"
        )]
    if target.suffix.lower() in {".html", ".htm"}:
        return [f"og:image path resolves to an HTML page, not an image file: {url}"]
    try:
        with target.open("rb") as image_file:
            header = image_file.read(12)
    except OSError:
        return [f"og:image file could not be inspected: {url}"]
    detected_format = next(
        (
            image_format
            for image_format, matches in SOCIAL_IMAGE_SIGNATURES.items()
            if matches(header)
        ),
        None,
    )
    if detected_format is None:
        supported = ", ".join(SOCIAL_IMAGE_SIGNATURES)
        return [(
            "og:image file does not have a supported image signature "
            f"({supported}): {url}"
        )]
    try:
        with target.open("rb") as image_file:
            dimensions = _social_image_dimensions(image_file, detected_format)
    except OSError:
        return [f"og:image file could not be inspected: {url}"]
    if dimensions is None:
        return [f"og:image dimensions could not be inspected (malformed or truncated file): {url}"]
    width, height = dimensions
    issues = []
    if width < SOCIAL_IMAGE_MIN_WIDTH or height < SOCIAL_IMAGE_MIN_HEIGHT:
        issues.append(
            f"og:image is {width}x{height}; minimum is "
            f"{SOCIAL_IMAGE_MIN_WIDTH}x{SOCIAL_IMAGE_MIN_HEIGHT}: {url}"
        )
    aspect_ratio = width / height
    if not SOCIAL_IMAGE_MIN_ASPECT_RATIO <= aspect_ratio <= SOCIAL_IMAGE_MAX_ASPECT_RATIO:
        issues.append(
            f"og:image aspect ratio is {aspect_ratio:.3f}:1; expected "
            f"{SOCIAL_IMAGE_MIN_ASPECT_RATIO:.2f}:1–"
            f"{SOCIAL_IMAGE_MAX_ASPECT_RATIO:.2f}:1: {url}"
        )
    declared_type = declared_type.strip().lower()
    if declared_type:
        expected_type = {
            "PNG": "image/png",
            "JPEG": "image/jpeg",
            "GIF": "image/gif",
            "WebP": "image/webp",
        }[detected_format]
        if declared_type != expected_type:
            issues.append(
                f"og:image:type declares `{declared_type}`, but the local file "
                f"is {detected_format} (expected `{expected_type}`): {url}"
            )
    return issues


def audit_page(path: Path) -> List[str]:
    rel = path.relative_to(ROOT).as_posix()
    src = path.read_text(encoding="utf-8", errors="replace")
    issues: List[str] = []

    # placeholder text scan (raw)
    for needle, label in PLACEHOLDER_PATTERNS:
        if needle in src:
            issues.append(f"{label}: `{needle}` present")
    if BARE_NOOPENER.search(src):
        issues.append('Bare rel="noopener" without noreferrer present')

    # Mermaid referral-link policy: any page that embeds a Mermaid diagram
    # must carry the OKH affiliate link (mermaidchart.cello.so) styled with
    # `mermaid-referral-link`. See replit.md "Mermaid pages" section.
    if re.search(r'<pre[^>]*class="[^"]*\bmermaid\b', src):
        if "mermaidchart.cello.so" not in src:
            issues.append(
                "Mermaid diagram present but missing referral link "
                "(https://mermaidchart.cello.so/UhVlNtC2MlS)"
            )
        if "mermaid-referral-link" not in src:
            issues.append(
                "Mermaid diagram present but missing `mermaid-referral-link` "
                "class (hot-pink styling)"
            )

    # Bare / generic link text — fails WCAG 2.4.4 (Link Purpose)
    # aria-label (if present) is used as the accessible label,
    # which means labeled navigation arrows are not flagged.
    for _lm in re.finditer(r'<a\b([^>]*)>(.*?)</a>', src,
                           re.DOTALL | re.IGNORECASE):
        _attrs = _lm.group(1)
        _inner = _lm.group(2)
        _aria = re.search(r'aria-label="([^"]*)"', _attrs, re.IGNORECASE)
        _aria_label = _aria.group(1).strip() if _aria else ""
        _visible = re.sub(r'<[^>]+>', '', _inner).strip()
        _visible = re.sub(r'\s+', ' ', _visible)
        _accessible = _aria_label if _aria_label else _visible
        if _accessible.lower().strip() in BARE_LINK_TEXTS:
            _href = re.search(r'href="([^"]*)"', _attrs, re.IGNORECASE)
            _href_val = _href.group(1) if _href else "(no href)"
            issues.append(
                f'Generic link text "{_accessible}": {_href_val}'
            )

    # duplicate-id scan — duplicate ids break anchor navigation, JS
    # querySelector calls, and screen-reader landmark announcements
    from collections import Counter
    all_ids = re.findall(r'\sid="([^"]+)"', src)
    for dup_id, count in Counter(all_ids).items():
        if count > 1:
            issues.append(f'Duplicate id="{dup_id}" appears {count} times')

    # in-page anchor sanity — every href="#foo" must point to a real
    # id="foo" on the same page (skip "#" alone and "#main" since main
    # may be added by skip-link landmark patterns at runtime)
    id_set = set(all_ids)
    anchors = re.findall(r'href="#([^"]+)"', src)
    for anchor in set(anchors):
        if anchor and anchor not in id_set:
            issues.append(f'In-page anchor href="#{anchor}" has no matching id')

    # Modern (2025/2026) baseline — security meta tags
    if 'name="referrer"' not in src:
        issues.append('Missing <meta name="referrer"> — modern privacy baseline')
    if 'http-equiv="Content-Security-Policy"' not in src:
        issues.append('Missing CSP meta tag — modern security baseline')
    elif "default-src 'self'" not in src:
        issues.append("CSP meta present but missing `default-src 'self'`")

    # Image perf — every <img> must declare loading= explicitly (no
    # silent default). Lazy or eager are both acceptable choices.
    for raw_img in re.findall(r'<img\b[^>]*>', src):
        if "loading=" not in raw_img:
            src_attr = re.search(r'src="([^"]+)"', raw_img)
            label = src_attr.group(1) if src_attr else "(no src)"
            issues.append(f"Image missing loading= attribute: {label}")

    # theme-color check — modern pattern uses a light/dark media-queried
    # pair. Accept both the legacy single tag and the new pair, but require
    # the brand teal to appear in at least one tag (it's the dark-mode and
    # historical default color).
    theme_colors = re.findall(
        r'<meta\s+name="theme-color"\s+[^>]*content="([^"]+)"', src
    )
    if not theme_colors:
        issues.append("Missing <meta name=\"theme-color\"> entirely")
    elif EXPECTED_THEME_COLOR not in [c.lower() for c in theme_colors]:
        issues.append(
            f"theme-color values {theme_colors} do not include the "
            f"expected brand color `{EXPECTED_THEME_COLOR}`"
        )

    # parse for structural checks
    p = PageParser()
    try:
        p.feed(src)
    except Exception as exc:  # pragma: no cover
        issues.append(f"HTML parser raised: {exc!r}")
        return issues

    # Check every declared social image, including later tags. The parser
    # handles attribute order, quotes and character references consistently.
    # External images remain outside the local filesystem audit.
    for image in p.og_images:
        image_issues = _og_image_issues(
            image["url"], image["type"], path.parent, ROOT, site_origin()
        )
        issues.extend(image_issues)

    title = p.title.strip()
    if not title:
        issues.append("Missing <title>")
    elif len(title) > TITLE_MAX:
        issues.append(f"Title is {len(title)} chars (>{TITLE_MAX})")

    desc = p.metas.get("description", "").strip()
    if not desc:
        issues.append("Missing meta description")
    elif len(desc) > DESC_MAX:
        issues.append(f"Description is {len(desc)} chars (>{DESC_MAX})")

    if "html lang=" not in src and "<html lang=" not in src:
        issues.append("Missing lang attribute on <html>")

    if p.h1_count == 0:
        issues.append("No <h1> found")
    elif p.h1_count > 1:
        issues.append(f"{p.h1_count} <h1> elements (should be 1)")

    # Heading order — no heading may jump more than one level deeper.
    # Going back up (e.g. h3 → h1) is always allowed.
    # Footer headings are already excluded by PageParser.
    _prev_level = 0
    for _level in p.headings:
        if _prev_level > 0 and _level > _prev_level + 1:
            issues.append(
                f"Heading order: h{_level} follows h{_prev_level} "
                f"(skips level — footer headings excluded)"
            )
        _prev_level = _level

    if not p.canonical:
        issues.append("Missing canonical link")

    # The offline fallback is intentionally noindex and is excluded from the
    # social-card family; it does not need social-preview metadata.
    if rel != "offline.html":
        for required in ("og:title", "og:description", "og:url"):
            if required not in p.metas:
                issues.append(f"Missing {required}")
            elif not p.metas[required].strip():
                issues.append(f"Blank {required}")
        has_social_image = bool({"og:image", "og:image:url"} & p.metas.keys())
        if not has_social_image:
            issues.append("Missing og:image")
        else:
            image_alt = p.metas.get("og:image:alt")
            if image_alt is None:
                issues.append("Missing og:image:alt")
            elif not image_alt.strip():
                issues.append("Blank og:image:alt")

    # image hygiene
    for img in p.images:
        src_attr = img["src"] or "(no src)"
        if img["alt"] is None:
            issues.append(f"Image missing alt: {src_attr}")
        if img["width"] is None or img["height"] is None:
            issues.append(f"Image missing width/height: {src_attr}")

    # external link hygiene (we already raw-checked, but report each link missing noreferrer)
    for link in p.external_links:
        rel_attr = link["rel"]
        if "noreferrer" not in rel_attr or "noopener" not in rel_attr:
            issues.append(
                f'External target=_blank link lacks noopener+noreferrer: {link["href"]}'
            )

    return issues


def parse_sitemap() -> Tuple[List[str], List[str]]:
    """Return (urls, errors). Never raises."""
    sitemap = ROOT / "sitemap.xml"
    if not sitemap.exists():
        return [], ["sitemap.xml is missing"]
    try:
        tree = ET.parse(sitemap)
    except ET.ParseError as exc:
        return [], [f"sitemap.xml is unparseable: {exc}"]
    locs = [
        (loc.text or "").strip()
        for loc in tree.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
    ]
    return [u for u in locs if u], []


def url_to_relpath(url: str) -> str | None:
    """Map a rooted discovery URL, rejecting foreign or escaping URLs."""
    path = discovery_path(url, ROOT, site_origin())
    return path.as_posix() if path is not None else None


def reconcile_sitemap(html_files: List[Path]) -> Tuple[List[str], List[str], List[str]]:
    """Return (in_sitemap_not_on_disk, on_disk_not_in_sitemap, errors)."""
    rels_on_disk = {p.relative_to(ROOT).as_posix() for p in html_files}
    rels_on_disk -= EXCLUDE_FROM_SITEMAP
    sitemap_urls, errors = parse_sitemap()
    if errors:
        return [], [], errors
    rels_in_sitemap = set()
    for url in sitemap_urls:
        relative = url_to_relpath(url)
        if relative is None:
            errors.append(f"Invalid sitemap discovery URL: {url}")
        else:
            rels_in_sitemap.add(relative)
    in_sitemap_missing_disk = sorted(rels_in_sitemap - rels_on_disk)
    on_disk_missing_sitemap = sorted(rels_on_disk - rels_in_sitemap)
    return in_sitemap_missing_disk, on_disk_missing_sitemap, errors


CRUFT_PATTERNS = ("*.bak", "*.orig", "*.swp", "*.swo", ".DS_Store", "Thumbs.db", "*~")


def scan_repo_cruft() -> List[str]:
    """Find leftover backup / OS-junk files in production directories."""
    issues: List[str] = []
    for pattern in CRUFT_PATTERNS:
        for p in ROOT.rglob(pattern):
            if any(part in EXCLUDE_DIRS for part in p.parts):
                continue
            issues.append(f"Repo cruft (delete me): {p.relative_to(ROOT).as_posix()}")
    return issues


def check_search_index_freshness(html_files: List[Path]) -> List[str]:
    """Use the canonical generator to detect content drift in the index.

    Filesystem mtimes are not reliable provenance: a checkout, copy, or archive
    extraction can make pages newer than a generated JSON file without changing
    their content. The builder's check mode compares the actual generated
    payload and ignores its volatile generated_at field.
    """
    idx = ROOT / "assets/data/search-index.json"
    if not idx.exists():
        return []  # missing-index is already caught by reconcile_search_index
    builder = ROOT / "scripts" / "build-search-index.py"
    if not builder.is_file():
        return ["search-index freshness could not be checked: build-search-index.py is missing"]
    result = subprocess.run(
        [sys.executable, str(builder), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode == 0:
        return []
    detail = (result.stderr or result.stdout).strip().splitlines()
    detail_text = detail[-1] if detail else "generator check failed without details"
    return [
        "search-index.json content is stale — rebuild with python3 scripts/build-search-index.py. "
        f"Generator check: {detail_text}"
    ]


def reconcile_search_index(html_files: List[Path]) -> List[str]:
    idx = ROOT / "assets/data/search-index.json"
    if not idx.exists():
        return ["search-index.json missing"]
    try:
        data = json.loads(idx.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"search-index.json is unreadable: {exc}"]
    try:
        pages = data.get("pages", data) if isinstance(data, dict) else data
        if not isinstance(pages, list):
            return [f"search-index.json has unexpected shape: {type(pages).__name__}"]
        indexed_urls = {item.get("url", "") for item in pages if isinstance(item, dict)}
        template_urls = sorted(
            u for u in indexed_urls
            if re.search(r"/assets/templates/", u)
        )
        if template_urls:
            return [
                f"search-index.json contains a template-scaffold URL "
                f"(re-run build-search-index.py after fixing EXCLUDE_DIRS): {u}"
                for u in template_urls
            ]
        indexed_rels = set()
        invalid_urls = []
        for url in indexed_urls:
            relative = url_to_relpath(url)
            if relative is None:
                invalid_urls.append(f"Invalid search-index discovery URL: {url}")
            else:
                indexed_rels.add(relative)
        rels_on_disk = {p.relative_to(ROOT).as_posix() for p in html_files}
        rels_on_disk -= EXCLUDE_FROM_SEARCH_INDEX
        missing = sorted(rels_on_disk - indexed_rels)
        return invalid_urls + [f"Page on disk not in search index: {p}" for p in missing]
    except Exception as exc:  # pragma: no cover — defensive
        return [f"search-index reconciliation crashed: {exc!r}"]


def render_report(per_page: Dict[str, List[str]],
                  sitemap_missing_disk: List[str],
                  disk_missing_sitemap: List[str],
                  search_issues: List[str]) -> str:
    total_issues = sum(len(v) for v in per_page.values()) + \
                   len(sitemap_missing_disk) + len(disk_missing_sitemap) + len(search_issues)
    lines = [
        "# Glee-fully.tools — Automated Site Audit",
        "",
        f"**Generated at (UTC):** {datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}",
        f"**Run date:** {date.today().isoformat()}",
        f"**Pages scanned:** {len(per_page)}  ",
        f"**Total issues:** {total_issues}",
        "",
        "## Sitemap reconciliation",
        "",
    ]
    if not sitemap_missing_disk and not disk_missing_sitemap:
        lines.append("- OK — sitemap and on-disk pages are in sync.")
    if sitemap_missing_disk:
        lines.append("- **Sitemap entries with no file on disk:**")
        for x in sitemap_missing_disk:
            lines.append(f"  - `{x}`")
    if disk_missing_sitemap:
        lines.append("- **Pages on disk not listed in sitemap.xml:**")
        for x in disk_missing_sitemap:
            lines.append(f"  - `{x}`")
    lines += ["", "## Search-index reconciliation", ""]
    if not search_issues:
        lines.append("- OK — every public page is covered by the search index.")
    else:
        for x in search_issues:
            lines.append(f"- {x}")
    lines += ["", "## Per-page issues", ""]
    for page, issues in sorted(per_page.items()):
        if not issues:
            continue
        lines.append(f"### `{page}`")
        for issue in issues:
            lines.append(f"- {issue}")
        lines.append("")
    if all(not v for v in per_page.values()):
        lines.append("_No per-page issues found._")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default="assets/docs/audit-report.md",
                        help="Path to write the Markdown report. Relative paths are rooted at the repository.")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress per-page console output.")
    args = parser.parse_args()

    # Console output can include Unicode page names and external report paths.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass

    html_files = iter_html_files()
    per_page: Dict[str, List[str]] = {}
    for path in html_files:
        rel = path.relative_to(ROOT).as_posix()
        per_page[rel] = audit_page(path)
        if not args.quiet:
            count = len(per_page[rel])
            flag = "OK " if count == 0 else f"{count:>3}"
            print(f"  [{flag}] {rel}")

    sitemap_missing_disk, disk_missing_sitemap, sitemap_errors = reconcile_sitemap(html_files)
    search_issues = reconcile_search_index(html_files)
    search_issues.extend(check_search_index_freshness(html_files))
    cruft_issues = scan_repo_cruft()
    if sitemap_errors:
        # Surface sitemap parse errors as issues against sitemap.xml itself.
        per_page["sitemap.xml"] = per_page.get("sitemap.xml", []) + sitemap_errors
    if cruft_issues:
        per_page["(repo cruft)"] = cruft_issues

    report = render_report(per_page, sitemap_missing_disk, disk_missing_sitemap, search_issues)
    out = Path(args.report).expanduser()
    report_is_relative = not out.is_absolute()
    if report_is_relative:
        out = ROOT / out
    out = out.absolute() if report_is_relative else out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    try:
        display_out = out.relative_to(ROOT).as_posix()
    except ValueError:
        display_out = str(out)
    print(f"\nReport written to {display_out}")

    total = sum(len(v) for v in per_page.values()) + len(sitemap_missing_disk) + \
            len(disk_missing_sitemap) + len(search_issues)
    # cruft was already added into per_page above, so it's already in the sum
    print(f"Total issues found: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

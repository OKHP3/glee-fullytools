#!/usr/bin/env python3
"""Normalize external new-tab links and the shared navigation-logo loading hint.

For published HTML files only, this script:
  * ensures external ``target="_blank"`` links include both ``noopener`` and
    ``noreferrer`` in their ``rel`` attribute; and
  * adds ``loading="lazy"`` to the shared 40px butterfly navigation image.

It is idempotent: a second run makes no changes. Use ``--check`` in CI or
before a release to report whether the generated HTML is current.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent.parent
EXCLUDE_DIRS = {
    ".agents",
    ".cache",
    ".git",
    ".local",
    ".pythonlibs",
    "attached_assets",
    "node_modules",
    "templates",
}
SAME_ORIGIN_HOSTS = {"glee-fully.tools", "www.glee-fully.tools"}
BUTTERFLY_LOGO = "glee-fully-tools-butterfly-waiting-square-1024.png"

ANCHOR_TAG = re.compile(r"<a\b[^>]*>", re.IGNORECASE)
IMAGE_TAG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
TARGET_BLANK = re.compile(r"\btarget\s*=\s*([\"'])_blank\1", re.IGNORECASE)
REL_ATTRIBUTE = re.compile(r"(\brel\s*=\s*)([\"'])(.*?)\2", re.IGNORECASE | re.DOTALL)
HREF_ATTRIBUTE = re.compile(r"\bhref\s*=\s*([\"'])(.*?)\1", re.IGNORECASE | re.DOTALL)
SRC_ATTRIBUTE = re.compile(r"\bsrc\s*=\s*([\"'])(.*?)\1", re.IGNORECASE | re.DOTALL)
LOADING_ATTRIBUTE = re.compile(r"\bloading\s*=", re.IGNORECASE)


def iter_html_files() -> list[Path]:
    """Return published HTML files, excluding project and template trees."""
    return sorted(
        path
        for path in ROOT.rglob("*.html")
        if not any(part in EXCLUDE_DIRS for part in path.relative_to(ROOT).parts)
    )


def is_external_url(href: str) -> bool:
    """Whether *href* points off the production site over HTTP(S)."""
    parsed = urlparse(href)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    return bool(host) and host not in SAME_ORIGIN_HOSTS


def append_attribute(tag: str, attribute: str) -> str:
    """Insert one HTML attribute before a tag's existing closing delimiter."""
    closing = "/>" if tag.rstrip().endswith("/>") else ">"
    body = tag.rstrip()[: -len(closing)].rstrip()
    return f"{body} {attribute}{closing}"


def normalize_link(tag: str) -> tuple[str, bool]:
    """Add rel protections to one external new-tab anchor without other edits."""
    if not TARGET_BLANK.search(tag):
        return tag, False

    href_match = HREF_ATTRIBUTE.search(tag)
    if not href_match or not is_external_url(href_match.group(2).strip()):
        return tag, False

    rel_match = REL_ATTRIBUTE.search(tag)
    if not rel_match:
        return append_attribute(tag, 'rel="noopener noreferrer"'), True

    tokens = rel_match.group(3).split()
    existing = {token.lower() for token in tokens}
    missing = [token for token in ("noopener", "noreferrer") if token not in existing]
    if not missing:
        return tag, False

    value = " ".join([*tokens, *missing])
    normalized = f"{rel_match.group(1)}{rel_match.group(2)}{value}{rel_match.group(2)}"
    return tag[: rel_match.start()] + normalized + tag[rel_match.end() :], True


def normalize_logo_loading(tag: str) -> tuple[str, bool]:
    """Add a lazy-loading hint to the small shared butterfly navigation image."""
    src_match = SRC_ATTRIBUTE.search(tag)
    if not src_match or BUTTERFLY_LOGO not in src_match.group(2):
        return tag, False
    if LOADING_ATTRIBUTE.search(tag):
        return tag, False
    return append_attribute(tag, 'loading="lazy"'), True


def trim_affected_line_whitespace(source: str) -> tuple[str, int]:
    """Remove trailing whitespace only from lines this normalizer owns."""
    fixed = 0
    lines: list[str] = []
    for line in source.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        newline = line[len(content) :]
        is_affected = (
            BUTTERFLY_LOGO in content
            or (
                TARGET_BLANK.search(content) is not None
                and HREF_ATTRIBUTE.search(content) is not None
                and is_external_url(HREF_ATTRIBUTE.search(content).group(2).strip())
            )
        )
        trimmed = content.rstrip(" \t")
        if is_affected and trimmed != content:
            fixed += 1
            content = trimmed
        lines.append(content + newline)
    return "".join(lines), fixed


def transform_page(source: str) -> tuple[str, int, int, int]:
    """Apply safe normalizations and return source plus each fix count."""
    links_fixed = 0
    images_fixed = 0

    def replace_anchor(match: re.Match[str]) -> str:
        nonlocal links_fixed
        tag, changed = normalize_link(match.group(0))
        links_fixed += int(changed)
        return tag

    def replace_image(match: re.Match[str]) -> str:
        nonlocal images_fixed
        tag, changed = normalize_logo_loading(match.group(0))
        images_fixed += int(changed)
        return tag

    source = ANCHOR_TAG.sub(replace_anchor, source)
    source = IMAGE_TAG.sub(replace_image, source)
    source, whitespace_fixed = trim_affected_line_whitespace(source)
    return source, links_fixed, images_fixed, whitespace_fixed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 when any published HTML needs normalization; do not write files",
    )
    args = parser.parse_args()

    changed_pages = 0
    links_fixed = 0
    images_fixed = 0
    whitespace_fixed = 0
    pending_pages = 0

    for path in iter_html_files():
        source = path.read_text(encoding="utf-8")
        normalized, page_links, page_images, page_whitespace = transform_page(source)
        if normalized == source:
            continue

        pending_pages += 1
        links_fixed += page_links
        images_fixed += page_images
        whitespace_fixed += page_whitespace
        if args.check:
            print(f"  stale  {path.relative_to(ROOT)}")
            continue

        path.write_text(normalized, encoding="utf-8")
        changed_pages += 1
        print(f"  fixed  {path.relative_to(ROOT)}")

    if args.check:
        if pending_pages:
            print(f"\nHTML normalization is stale in {pending_pages} page(s).")
            return 1
        print("\nExternal-link rel values and butterfly image loading are current.")
        return 0

    print(f"\nUpdated {changed_pages} page(s).")
    print(f"  External links protected: {links_fixed}")
    print(f"  Butterfly images lazy-loaded: {images_fixed}")
    print(f"  Affected lines whitespace-cleaned: {whitespace_fixed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
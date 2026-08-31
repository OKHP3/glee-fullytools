#!/usr/bin/env python3
"""Synchronize published pages to the shared 1200×630 social-sharing card.

Updates the existing Open Graph and Twitter image metadata on every published
social-preview page. The script intentionally excludes source templates and the
noindex offline shell: it keeps the published site in sync without changing
template-specific or fallback metadata.

Run normally to write updates, or use ``--check`` to verify that every page
already references the shared landscape card.
"""

from __future__ import annotations

import argparse
import re
import struct
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
EXCLUDE_DIRS = {
    ".agents",
    ".cache",
    ".git",
    ".local",
    ".pythonlibs",
    "assets",
    "attached_assets",
    "node_modules",
}
SKIP_FILES = {"offline.html"}
CARD_PATH = "/assets/img/glee-fully-tools-social-card-1200x630.png"
CARD_URL = f"https://glee-fully.tools{CARD_PATH}"
CARD_ALT = "Glee-fully Personalizable Tools — joyful tools for life, work, and wonder"

META_TAG = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
ATTR = re.compile(r"\b([:\w-]+)\s*=\s*([\"'])(.*?)\2", re.IGNORECASE | re.DOTALL)

TARGETS = {
    ("property", "og:image"): CARD_URL,
    ("property", "og:image:width"): "1200",
    ("property", "og:image:height"): "630",
    ("property", "og:image:alt"): CARD_ALT,
    ("name", "twitter:image"): CARD_URL,
    ("name", "twitter:image:alt"): CARD_ALT,
}
REQUIRED = {
    ("property", "og:image"),
    ("property", "og:image:width"),
    ("property", "og:image:height"),
    ("property", "og:image:alt"),
    ("name", "twitter:image"),
    ("name", "twitter:image:alt"),
}


def iter_html_files() -> list[Path]:
    """Return every published HTML page in deterministic order."""
    return sorted(
        path
        for path in ROOT.rglob("*.html")
        if path.name not in SKIP_FILES
        and not any(part in EXCLUDE_DIRS for part in path.relative_to(ROOT).parts)
    )


def card_dimensions() -> tuple[int, int]:
    """Read and validate the approved card's PNG dimensions."""
    card = ROOT / CARD_PATH.lstrip("/")
    try:
        with card.open("rb") as handle:
            header = handle.read(24)
    except OSError as error:
        raise ValueError(f"approved card is not readable: {card}") from error
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError(f"approved card is not a valid PNG: {card}")
    return struct.unpack(">II", header[16:24])


def attributes(tag: str) -> dict[str, str]:
    """Read lowercased HTML attributes without altering the original tag."""
    return {name.lower(): value for name, _, value in ATTR.findall(tag)}


def set_content(tag: str, value: str) -> str:
    """Replace a meta tag's content value while preserving its attribute order."""
    content = re.compile(r"(\bcontent\s*=\s*)([\"'])(.*?)\2", re.IGNORECASE | re.DOTALL)
    match = content.search(tag)
    if not match:
        raise ValueError(f"Metadata tag has no content attribute: {tag}")
    replacement = f"{match.group(1)}{match.group(2)}{value}{match.group(2)}"
    return tag[: match.start()] + replacement + tag[match.end() :]


def transform_page(source: str) -> tuple[str, int, set[tuple[str, str]]]:
    """Update known social metadata and return (source, edits, keys_seen)."""
    changes = 0
    seen: set[tuple[str, str]] = set()

    def replace_meta(match: re.Match[str]) -> str:
        nonlocal changes
        tag = match.group(0)
        attrs = attributes(tag)
        for attr_name in ("property", "name"):
            key = (attr_name, attrs.get(attr_name, "").lower())
            expected = TARGETS.get(key)
            if expected is None:
                continue
            seen.add(key)
            if attrs.get("content") != expected:
                changes += 1
                return set_content(tag, expected)
            return tag
        return tag

    return META_TAG.sub(replace_meta, source), changes, seen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if any published page is missing or has stale card metadata",
    )
    args = parser.parse_args()

    try:
        dimensions = card_dimensions()
    except ValueError as error:
        print(f"Social-card asset: {error}", file=sys.stderr)
        return 1
    if dimensions != (1200, 630):
        print(
            "Social-card asset: expected 1200×630 PNG, "
            f"found {dimensions[0]}×{dimensions[1]}",
            file=sys.stderr,
        )
        return 1

    stale_pages: list[str] = []
    total_changes = 0
    missing_metadata: list[str] = []

    for path in iter_html_files():
        source = path.read_text(encoding="utf-8")
        updated, changes, seen = transform_page(source)
        missing = REQUIRED - seen
        rel = path.relative_to(ROOT).as_posix()
        if missing:
            missing_metadata.append(
                f"{rel}: missing {', '.join('/'.join(key) for key in sorted(missing))}"
            )
        if updated != source:
            stale_pages.append(rel)
            total_changes += changes
            if not args.check:
                path.write_text(updated, encoding="utf-8")
                print(f"  updated  {rel}")

    if missing_metadata:
        print("\nMissing required social metadata:", file=sys.stderr)
        for message in missing_metadata:
            print(f"  ! {message}", file=sys.stderr)
        return 1

    if args.check:
        if stale_pages:
            print(f"\nSocial-card metadata is stale in {len(stale_pages)} page(s).")
            return 1
        print(f"\nSocial-card metadata is current across {len(iter_html_files())} published pages.")
        return 0

    print(f"\nUpdated {len(stale_pages)} page(s); {total_changes} metadata value(s) synchronized.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
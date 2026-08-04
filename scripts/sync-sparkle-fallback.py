#!/usr/bin/env python3
"""
sync-sparkle-fallback.py — Sync static [data-sparkle-link] fallback from sparkle.json
========================================================================================
All HTML pages carry a hard-coded href + text inside <a data-sparkle-link> as a no-JS
fallback.  The runtime loader (app.js §6) overwrites this live, but users with
JavaScript blocked or slow still see the static markup.

This script reads assets/data/sparkle.json (single source of truth) and rewrites the
href attribute and text content of every <a data-sparkle-link> element in every HTML
file so the static markup always matches the live JSON.

Text format mirrors the JS loader exactly (app.js §6, line ~752):
  {emoji} {label} — {description} {suffix}

Usage:
    python3 scripts/sync-sparkle-fallback.py          # update files in place
    python3 scripts/sync-sparkle-fallback.py --dry-run # report without writing

Safe to re-run: skips any file whose href + text are already correct.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
SPARKLE_JSON = ROOT / "assets" / "data" / "sparkle.json"

SKIP_DIRS = {
    "node_modules", ".git", ".local", ".pythonlibs", ".cache",
    ".agents", "__pycache__", "assets",
}

# Matches the full  <a … data-sparkle-link …>…text…</a>  block.
# Group 1: opening tag (the full <a …>)
# Group 2: text content between the tags (may contain whitespace/newlines)
# Group 3: closing </a>
SPARKLE_BLOCK_RE = re.compile(
    r'(<a\b[^>]*\bdata-sparkle-link\b[^>]*>)(.*?)(</a>)',
    re.DOTALL,
)

# Matches the href="…" attribute inside an opening tag
HREF_RE = re.compile(r'\bhref="[^"]*"')


# ── Helpers ─────────────────────────────────────────────────────────────────

def build_text(data: dict) -> str:
    """Build display text using the same formula as app.js §6."""
    parts = []
    if data.get("emoji"):
        parts.append(data["emoji"] + " ")
    if data.get("label"):
        parts.append(data["label"])
    if data.get("description"):
        parts.append(" \u2014 " + data["description"])
    if data.get("suffix"):
        parts.append(" " + data["suffix"])
    return "".join(parts)


def collect_html_files() -> list[Path]:
    files: list[Path] = []
    for p in ROOT.rglob("*.html"):
        # Skip directories we never want to touch
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        files.append(p)
    files.sort()
    return files


def patch_file(path: Path, new_href: str, new_text: str, dry_run: bool) -> bool:
    """
    Patch all [data-sparkle-link] elements in *path*.
    Returns True if the file was (or would be) changed.
    """
    original = path.read_text(encoding="utf-8")

    changed = False

    def replacer(m: re.Match) -> str:
        nonlocal changed
        opening_tag = m.group(1)
        closing_tag = m.group(3)

        # 1. Update href inside the opening tag
        if HREF_RE.search(opening_tag):
            new_opening = HREF_RE.sub(f'href="{new_href}"', opening_tag)
        else:
            # No href attr yet — insert one before data-sparkle-link
            new_opening = opening_tag.replace(
                "data-sparkle-link",
                f'href="{new_href}" data-sparkle-link',
            )

        # 2. Preserve existing indentation of the text line
        #    Look at the whitespace that precedes the old text content.
        old_inner = m.group(2)
        leading_ws_match = re.match(r'(\s*)', old_inner)
        indent = leading_ws_match.group(1) if leading_ws_match else "\n          "
        # Normalise: ensure it starts with a newline + same indent
        if "\n" not in indent:
            indent = "\n          "
        trailing_ws = re.search(r'\s*$', old_inner)
        trail = trailing_ws.group(0) if trailing_ws else "\n        "
        if "\n" not in trail:
            trail = "\n        "

        new_inner = indent + new_text + trail

        replacement = new_opening + new_inner + closing_tag

        if replacement != m.group(0):
            changed = True

        return replacement

    patched = SPARKLE_BLOCK_RE.sub(replacer, original)

    if changed:
        if not dry_run:
            path.write_text(patched, encoding="utf-8")
        return True
    return False


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report changes without writing files",
    )
    args = parser.parse_args()

    # Load sparkle.json
    if not SPARKLE_JSON.exists():
        print(f"ERROR: {SPARKLE_JSON} not found", file=sys.stderr)
        sys.exit(1)

    data = json.loads(SPARKLE_JSON.read_text(encoding="utf-8"))
    new_href = data.get("url", "")
    new_text = build_text(data)

    if not new_href:
        print("ERROR: sparkle.json missing 'url' field", file=sys.stderr)
        sys.exit(1)
    if not new_text:
        print("ERROR: sparkle.json produced empty text", file=sys.stderr)
        sys.exit(1)

    print(f"Sparkle target  href : {new_href}")
    print(f"Sparkle target  text : {new_text}")
    if args.dry_run:
        print("(dry-run — no files will be written)\n")

    html_files = collect_html_files()
    updated: list[Path] = []
    skipped: list[Path] = []
    no_sparkle: list[Path] = []

    for path in html_files:
        content = path.read_text(encoding="utf-8")
        if "data-sparkle-link" not in content:
            no_sparkle.append(path)
            continue

        changed = patch_file(path, new_href, new_text, dry_run=args.dry_run)
        if changed:
            updated.append(path)
            verb = "would update" if args.dry_run else "updated"
            print(f"  {verb}: {path.relative_to(ROOT)}")
        else:
            skipped.append(path)

    print()
    print(f"Files with [data-sparkle-link] : {len(updated) + len(skipped)}")
    print(f"  Already correct (skipped)    : {len(skipped)}")
    print(f"  {'Would be updated' if args.dry_run else 'Updated'}              : {len(updated)}")
    print(f"Files without sparkle link     : {len(no_sparkle)}")

    if args.dry_run and updated:
        print("\nRe-run without --dry-run to apply changes.")


if __name__ == "__main__":
    main()

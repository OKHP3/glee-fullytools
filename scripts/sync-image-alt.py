#!/usr/bin/env python3
"""
sync-image-alt.py — Sync og:image:alt / twitter:image:alt from SVG aria-labels
================================================================================
For every tool page whose og:image points to a local .svg file, this script:

  1. Resolves the SVG path on disk relative to the site root
  2. Reads the svg[aria-label] attribute (source of truth for the description)
  3. Reads the tool name from og:title (the part before the em-dash separator)
  4. Builds the canonical alt:  "Glee-fully {tool_name} — {aria_label}"
  5. Updates og:image:alt and twitter:image:alt in the HTML file if they differ

Usage:
    python3 scripts/sync-image-alt.py          # update files in place
    python3 scripts/sync-image-alt.py --dry-run # report without writing

Safe to re-run: skips any file whose alt values are already correct.
"""
from __future__ import annotations

import argparse
import html as html_module
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {
    "node_modules", ".local", ".git", "attached_assets",
    "assets", ".pythonlibs", ".cache", ".agents",
}
SITE = "https://glee-fully.tools/"


def extract_svg_aria_label(svg_path: Path) -> str | None:
    """Return the aria-label attribute value from the root <svg> element."""
    text = svg_path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'<svg\b[^>]*\baria-label="([^"]+)"', text)
    return m.group(1) if m else None


def extract_tool_name(html_text: str) -> str | None:
    """Extract the tool name from og:title (the part before the em-dash separator)."""
    m = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', html_text)
    if not m:
        return None
    raw = html_module.unescape(m.group(1))
    # Split on " — " (em dash, U+2014) or " - " (plain hyphen) as fallback
    for sep in (" \u2014 ", " - "):
        idx = raw.find(sep)
        if idx != -1:
            return raw[:idx].strip()
    return raw.strip()


def update_meta(html_text: str, attr: str, new_value: str) -> tuple[str, bool]:
    """Replace the content="..." of a specific meta tag. Returns (new_html, changed)."""
    # Match og:image:alt  →  property="og:image:alt"
    # Match twitter:image:alt  →  name="twitter:image:alt"
    if attr.startswith("og:"):
        pattern = rf'(<meta\s+property="{re.escape(attr)}"\s+content=")([^"]*)(")' 
    else:
        pattern = rf'(<meta\s+name="{re.escape(attr)}"\s+content=")([^"]*)(")' 
    m = re.search(pattern, html_text)
    if not m:
        return html_text, False
    current = html_module.unescape(m.group(2))
    if current == new_value:
        return html_text, False
    new_html = html_text[:m.start(2)] + new_value + html_text[m.end(2):]
    return new_html, True


def process_page(path: Path, dry_run: bool) -> tuple[int, int]:
    """Process one HTML file. Returns (updated_count, warning_count)."""
    html_text = path.read_text(encoding="utf-8", errors="replace")

    # Only process pages with a .svg og:image URL
    img_m = re.search(r'<meta\s+property="og:image"\s+content="([^"]+\.svg)"', html_text)
    if not img_m:
        return 0, 0

    img_url = img_m.group(1)
    if not img_url.startswith(SITE):
        return 0, 0

    svg_rel = img_url[len(SITE):]          # e.g. assets/img/tool-ettes/01a-…svg
    svg_path = ROOT / svg_rel
    if not svg_path.exists():
        print(f"  WARN  {path.relative_to(ROOT)}: SVG not found at {svg_rel}")
        return 0, 1

    aria_label = extract_svg_aria_label(svg_path)
    if not aria_label:
        print(f"  WARN  {path.relative_to(ROOT)}: SVG {svg_rel} has no aria-label")
        return 0, 1

    tool_name = extract_tool_name(html_text)
    if not tool_name:
        print(f"  WARN  {path.relative_to(ROOT)}: could not extract tool name from og:title")
        return 0, 1

    expected_alt = f"Glee-fully {tool_name} \u2014 {aria_label}"

    updated = 0
    for attr in ("og:image:alt", "twitter:image:alt"):
        new_html, changed = update_meta(html_text, attr, expected_alt)
        if changed:
            rel = path.relative_to(ROOT)
            if dry_run:
                print(f"  DRY   {rel}: would update {attr}")
                print(f"        → {expected_alt!r}")
            else:
                html_text = new_html
                print(f"  +     {rel}: updated {attr}")
            updated += 1

    if updated and not dry_run:
        path.write_text(html_text, encoding="utf-8")

    return updated, 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing")
    args = parser.parse_args()

    total_updated = 0
    total_warnings = 0

    for path in sorted(ROOT.rglob("*.html")):
        rel = path.relative_to(ROOT)
        if any(s in rel.parts for s in SKIP_DIRS):
            continue
        updated, warnings = process_page(path, dry_run=args.dry_run)
        total_updated += updated
        total_warnings += warnings

    label = "would update" if args.dry_run else "updated"
    print(f"\n{label}: {total_updated} meta tag(s)  warnings: {total_warnings}")
    return 1 if total_warnings else 0


if __name__ == "__main__":
    sys.exit(main())

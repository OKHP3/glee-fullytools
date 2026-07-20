#!/usr/bin/env python3
"""
Fix footer nav consistency site-wide (idempotent).

Changes applied:
  1. Ensure /search/ appears in footer Navigation list on every page
     (inserted after the /toolbox/ item, or after /#why if toolbox not found).
  2. Ensure /showcase/ appears in footer Navigation list on every page
     (inserted after the /about/ item, before /contact/).
  3. Normalise the /showcase/ line indentation to match siblings.

Safe to re-run — every insertion checks footer-scoped presence only.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

SKIP_SEARCH_SELF   = {"search/index.html"}   # the search page itself
SKIP_SHOWCASE_SELF = {"showcase/index.html"}  # the showcase page itself


def find_pages(root: Path):
    pages = list(root.rglob("*/index.html")) + [root / "index.html"]
    skip = {"assets/templates", ".pythonlibs", "node_modules", ".local", ".agents"}
    return [p for p in pages if not any(s in str(p) for s in skip)]


def split_footer(html: str):
    """Return (pre, footer_inner, post) or None if no <footer>."""
    m = re.search(r'(<footer[^>]*>)(.*?)(</footer>)', html, re.DOTALL)
    if not m:
        return None
    return html[: m.start()], m.group(1), m.group(2), m.group(3), html[m.end():]


def ensure_footer_item(html: str, anchor_href: str, new_item: str) -> tuple[str, bool]:
    """
    Insert new_item immediately after the <li> containing anchor_href,
    but only if new_item's href is not already in the footer.
    Returns (new_html, changed).
    """
    parts = split_footer(html)
    if not parts:
        return html, False
    pre, ftag, footer_inner, fclose, post = parts

    new_href = re.search(r'href="([^"]+)"', new_item).group(1)
    # Check presence ONLY within the footer
    if new_href in footer_inner:
        return html, False

    # Find the anchor item inside the footer
    anchor_re = re.compile(
        r'(<li><a\s+href="' + re.escape(anchor_href) + r'"[^>]*>.*?</a></li>)',
        re.DOTALL,
    )
    m = anchor_re.search(footer_inner)
    if not m:
        return html, False

    # Detect indentation of the anchor line
    line_start = footer_inner.rfind("\n", 0, m.start()) + 1
    indent = ""
    for ch in footer_inner[line_start:]:
        if ch in (" ", "\t"):
            indent += ch
        else:
            break

    replacement = m.group(1) + "\n" + indent + new_item
    new_footer_inner = (
        footer_inner[: m.start()] + replacement + footer_inner[m.end():]
    )
    new_html = pre + ftag + new_footer_inner + fclose + post
    return new_html, True


def normalise_showcase_indent(html: str) -> tuple[str, bool]:
    """Fix /showcase/ <li> if it has wrong leading whitespace vs its /about/ sibling."""
    about_m = re.search(r'( +)<li><a href="/about/', html)
    showcase_m = re.search(r'( +)<li><a href="/showcase/', html)
    if not about_m or not showcase_m:
        return html, False
    correct = about_m.group(1)
    actual = showcase_m.group(1)
    if correct == actual:
        return html, False
    fixed = re.sub(
        r'( +)(<li><a href="/showcase/")',
        correct + r'\2',
        html,
        count=1,
    )
    return fixed, fixed != html


def main():
    pages = find_pages(ROOT)
    total = 0
    search_added = 0
    showcase_added = 0
    indent_fixed = 0

    for p in sorted(pages):
        rel = str(p.relative_to(ROOT))
        html = p.read_text(encoding="utf-8", errors="replace")
        changed = False

        # 1. Add /search/ (skip the search page itself)
        if rel not in SKIP_SEARCH_SELF:
            # Try to anchor on /toolbox/ first, fall back to /#why
            html, c1 = ensure_footer_item(
                html,
                anchor_href="/toolbox/",
                new_item='<li><a href="/search/">Search</a></li>',
            )
            if not c1:
                # For homepage the /toolbox/ footer item is "Opening the Toolbox"
                # but href is still /toolbox/, so try anchoring on /#why instead
                html, c1 = ensure_footer_item(
                    html,
                    anchor_href="/#why",
                    new_item='<li><a href="/search/">Search</a></li>',
                )
            if c1:
                search_added += 1
                changed = True

        # 2. Add /showcase/ (skip the showcase page itself)
        if rel not in SKIP_SHOWCASE_SELF:
            html, c2 = ensure_footer_item(
                html,
                anchor_href="/about/",
                new_item='<li><a href="/showcase/">Showcase</a></li>',
            )
            if c2:
                showcase_added += 1
                changed = True

        # 3. Normalise /showcase/ indentation
        html, c3 = normalise_showcase_indent(html)
        if c3:
            indent_fixed += 1
            changed = True

        if changed:
            p.write_text(html, encoding="utf-8")
            total += 1

    print(f"Pages modified     : {total}")
    print(f"  /search/ added   : {search_added}")
    print(f"  /showcase/ added : {showcase_added}")
    print(f"  indent fixed     : {indent_fixed}")


if __name__ == "__main__":
    main()

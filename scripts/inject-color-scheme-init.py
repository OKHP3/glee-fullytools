#!/usr/bin/env python3
"""
inject-color-scheme-init.py

Injects a tiny blocking inline <script> into every HTML page's <head>
so the browser applies the user's saved color-scheme preference from
localStorage BEFORE CSS is painted — preventing a flash of the wrong theme.

The script sets data-color-scheme="dark" or "light" on <html> using the
brand-specific localStorage key written by the color-scheme toggle in app.js:

  Brand        localStorage key             Repo / site
  ───────────  ───────────────────────────  ──────────────────────────
  glee         glee-color-scheme            OKHP3/glee-fully.tools
  askjamie     askjamie-color-scheme        OKHP3/AskJamie (askjamie.bot)

Injection point  : immediately after <meta charset="utf-8" ...> on the
                   first matching line in <head>.
Idempotency guard: <!-- AUTOGEN:COLOR-SCHEME-INIT --> marker — pages that
                   already have the marker are skipped.

Usage:
  # Glee (default) — run from glee-fully.tools repo root
  python3 scripts/inject-color-scheme-init.py

  # AskJamie — run from the OKHP3/AskJamie repo root
  python3 scripts/inject-color-scheme-init.py --brand askjamie

  # Target a different directory (e.g. sibling-sync copy)
  python3 scripts/inject-color-scheme-init.py --brand askjamie --root .local/sibling-sync/for-askjamie
"""

import argparse
import re
from pathlib import Path

# ── Brand registry ────────────────────────────────────────────────────────────
BRANDS = {
    "glee": {
        "ls_key": "glee-color-scheme",
        "description": "Glee-fully Personalizable Tools (glee-fully.tools)",
    },
    "askjamie": {
        "ls_key": "askjamie-color-scheme",
        "description": "AskJamie™ (askjamie.bot)",
    },
}

SKIP = {'assets/', 'attached_assets/', '.local/', '.agents/', '.pythonlibs/', 'node_modules/'}

MARKER = '<!-- AUTOGEN:COLOR-SCHEME-INIT -->'

CHARSET_RE = re.compile(
    r'(<meta\s[^>]*charset\s*=\s*["\']?utf-8["\']?[^>]*>)',
    re.IGNORECASE,
)


def build_snippet(ls_key: str) -> str:
    """Return the full marker + inline script block for the given localStorage key."""
    return (
        "<!-- AUTOGEN:COLOR-SCHEME-INIT -->\n"
        "    <script>"
        f"(function(){{try{{var s=localStorage.getItem('{ls_key}');"
        "if(s==='dark'||s==='light')"
        "document.documentElement.setAttribute('data-color-scheme',s);"
        "}catch(e){}}})();"
        "</script>"
    )


def collect_pages(root: Path, skip: set[str]) -> list[Path]:
    return [
        p for p in root.rglob("*.html")
        if not any(s in str(p) for s in skip)
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inject anti-FOSC color-scheme init script into HTML pages."
    )
    parser.add_argument(
        "--brand",
        choices=list(BRANDS.keys()),
        default="glee",
        help=(
            "Which brand's localStorage key to use. "
            "'glee' uses 'glee-color-scheme' (default); "
            "'askjamie' uses 'askjamie-color-scheme'. "
            "Run from the target brand's repo root, or combine with --root."
        ),
    )
    parser.add_argument(
        "--root",
        default=".",
        help=(
            "Directory to scan for HTML files (default: current directory). "
            "Useful when injecting into a sibling-sync copy or a checked-out "
            "AskJamie repo at a non-standard path."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be injected without writing any files.",
    )
    args = parser.parse_args()

    brand_cfg = BRANDS[args.brand]
    ls_key    = brand_cfg["ls_key"]
    snippet   = build_snippet(ls_key)
    root      = Path(args.root).resolve()

    # When targeting a custom --root, don't apply the default SKIP filters
    # (they're relative to the repo root and would miss or wrongly skip paths).
    skip = SKIP if args.root == "." else set()

    print(f"Brand     : {args.brand}  ({brand_cfg['description']})")
    print(f"LS key    : {ls_key}")
    print(f"Root      : {root}")
    print(f"Dry-run   : {args.dry_run}")
    print()

    pages = collect_pages(root, skip)

    injected = 0
    skipped  = 0

    for page in sorted(pages):
        text = page.read_text(encoding="utf-8", errors="replace")

        if MARKER in text:
            skipped += 1
            continue

        m = CHARSET_RE.search(text)
        if not m:
            print(f"  WARN  no <meta charset> found: {page}")
            skipped += 1
            continue

        if args.dry_run:
            print(f"  would inject: {page}")
            injected += 1
            continue

        insert_pos = m.end()
        new_text   = text[:insert_pos] + "\n    " + snippet + text[insert_pos:]
        page.write_text(new_text, encoding="utf-8")
        injected += 1
        print(f"  injected: {page}")

    label = "would inject" if args.dry_run else "injected"
    print(f"\nColor-scheme init {label} into {injected} pages; {skipped} already up-to-date.")


if __name__ == "__main__":
    main()

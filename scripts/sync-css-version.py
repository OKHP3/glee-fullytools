#!/usr/bin/env python3
"""sync-css-version.py — Idempotent CSS cache-buster for theme.css references.

Computes the first 8 hex characters of the SHA-256 of assets/css/theme.css
and rewrites every `theme.css?v=<token>` reference in all HTML pages to
`theme.css?v=<hash>`.

Re-running is safe: if the hash hasn't changed no files are touched.

Usage:
    python3 scripts/sync-css-version.py
    python3 scripts/sync-css-version.py --check

Exit codes:
    0  — all files are up to date (or were just updated)
    1  — error, or stale references when using --check
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
THEME_CSS = REPO / "assets" / "css" / "theme.css"

SKIP_DIRS = {
    "node_modules", ".local", ".git", "attached_assets",
    ".pythonlibs", ".cache", ".agents",
}

# Matches any theme.css?v=<token> reference in an HTML file.
# Capture group 1 = the existing token (anything up to the next quote/space).
CSS_REF_RE = re.compile(r"(theme\.css\?v=)([^\"' >]+)")


def css_hash(path: Path) -> str:
    """Return a stable 8-char hash for the CSS payload."""
    normalized = path.read_bytes().replace(b"\r\n", b"\n")
    digest = hashlib.sha256(normalized).hexdigest()
    return digest[:8]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report stale references without changing files; exits 1 when found",
    )
    args = parser.parse_args()

    if not THEME_CSS.exists():
        print(f"ERROR: {THEME_CSS.relative_to(REPO)} not found", file=sys.stderr)
        return 1

    token = css_hash(THEME_CSS)
    replacement = rf"\g<1>{token}"

    html_files = sorted(
        p for p in REPO.rglob("*.html")
        if not any(s in p.parts for s in SKIP_DIRS)
        and not any(s in p.relative_to(REPO).parts for s in {"assets"})
    )

    if not html_files:
        print("ERROR: no HTML files found", file=sys.stderr)
        return 1

    updated = 0
    unchanged = 0
    for path in html_files:
        src = path.read_text(encoding="utf-8", errors="replace")
        patched = CSS_REF_RE.sub(replacement, src)
        if patched == src:
            unchanged += 1
        else:
            if args.check:
                print(f"  STALE: {path.relative_to(REPO).as_posix()}")
            else:
                path.write_text(patched, encoding="utf-8")
            updated += 1

    if args.check and updated:
        print(
            f"ERROR: {updated} HTML file(s) have stale theme.css cache tokens. "
            "Run python3 scripts/sync-css-version.py before release."
        )
        return 1
    if updated:
        print(f"  CSS token -> {token}  ({updated} file(s) updated, {unchanged} already current)")
    else:
        print(f"  CSS token -> {token}  (all {unchanged} file(s) already current)")

    return 0


if __name__ == "__main__":
    sys.exit(main())

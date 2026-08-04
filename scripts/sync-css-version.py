#!/usr/bin/env python3
"""sync-css-version.py — Idempotent CSS cache-buster for theme.css references.

Computes the first 8 hex characters of the SHA-256 of assets/css/theme.css
and rewrites every `theme.css?v=<token>` reference in all HTML pages to
`theme.css?v=<hash>`.

Re-running is safe: if the hash hasn't changed no files are touched.

Usage:
    python3 scripts/sync-css-version.py

Exit codes:
    0  — all files are up to date (or were just updated)
    1  — error (CSS file missing, no HTML files found, etc.)
"""

from __future__ import annotations

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
    """Return the first 8 hex chars of the SHA-256 of *path*."""
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest[:8]


def main() -> int:
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
            path.write_text(patched, encoding="utf-8")
            updated += 1

    if updated:
        print(f"  CSS token → {token}  ({updated} file(s) updated, {unchanged} already current)")
    else:
        print(f"  CSS token → {token}  (all {unchanged} file(s) already current)")

    return 0


if __name__ == "__main__":
    sys.exit(main())

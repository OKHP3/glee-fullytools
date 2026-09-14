#!/usr/bin/env python3
"""sync-css-version.py - Idempotent cache-buster for CSS and JavaScript references.

Computes the first 8 hex characters of the SHA-256 of assets/css/theme.css
and rewrites every `theme.css?v=<token>` reference in all HTML pages to the
current hash. The same normalized-content hash is applied to the shared
JavaScript assets in HTML and the service-worker precache list.

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
JS_REF_RE = re.compile(
    r"(?<![A-Za-z0-9._/-])(?P<prefix>(?:/)?assets/js/(?P<asset>app|glee-site-enhancements|universe-map|color-scheme-init)\.js)"
    r"(?P<query>\?[^\"' >#]*)?(?P<fragment>#[^\"' >]*)?"
)
SEARCH_INDEX_REF_RE = re.compile(
    r"(?P<prefix>(?:/)?assets/data/search-index\.json)(?P<query>\?[^\"' >#]*)?(?P<fragment>#[^\"' >]*)?"
)
JS_ASSETS = {
    "color-scheme-init": "assets/js/color-scheme-init.js",
    "app": "assets/js/app.js",
    "universe-map": "assets/js/universe-map.js",
    "glee-site-enhancements": "assets/js/glee-site-enhancements.js",
}


def css_hash(path: Path) -> str:
    """Return a stable 8-char hash for the CSS payload."""
    normalized = path.read_bytes().replace(b"\r\n", b"\n")
    digest = hashlib.sha256(normalized).hexdigest()
    return digest[:8]


def normalized_hash_bytes(payload: bytes) -> str:
    """Return a stable 8-char hash for bytes, independent of CRLF."""
    normalized = payload.replace(b"\r\n", b"\n")
    return hashlib.sha256(normalized).hexdigest()[:8]


def normalized_hash(path: Path) -> str:
    """Return a stable 8-char hash for a text asset, independent of CRLF."""
    return normalized_hash_bytes(path.read_bytes())


def update_version_query(query: str | None, token: str, fragment: str = "") -> str:
    """Replace or append the v query parameter while preserving other params."""
    if not query or query == "?":
        return f"?v={token}{fragment}"
    parts = query[1:].split("&")
    for index, part in enumerate(parts):
        if part.split("=", 1)[0] == "v":
            parts[index] = f"v={token}"
            return "?" + "&".join(parts) + fragment
    return "?" + "&".join([*parts, f"v={token}"]) + fragment


def javascript_tokens(repo: Path) -> dict[str, str]:
    """Return current normalized hashes for JavaScript assets present in repo."""
    return {
        name: normalized_hash(repo / relative_path)
        for name, relative_path in JS_ASSETS.items()
        if (repo / relative_path).exists()
    }


def rewrite_javascript_refs(source: str, tokens: dict[str, str]) -> str:
    """Version known JavaScript URLs without disturbing other query parameters."""
    def replace(match: re.Match[str]) -> str:
        asset = match.group("asset")
        token = tokens.get(asset)
        if token is None:
            return match.group(0)
        return match.group("prefix") + update_version_query(
            match.group("query"), token, match.group("fragment") or ""
        )

    return JS_REF_RE.sub(replace, source)


def rewrite_search_index_refs(source: str, token: str) -> str:
    """Version the English search index so old service workers cannot win."""
    def replace(match: re.Match[str]) -> str:
        return match.group("prefix") + update_version_query(
            match.group("query"), token, match.group("fragment") or ""
        )

    return SEARCH_INDEX_REF_RE.sub(replace, source)


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
    search_index = REPO / "assets" / "data" / "search-index.json"
    search_index_token = normalized_hash(search_index) if search_index.exists() else None
    js_tokens: dict[str, str] = {}
    app_path = REPO / JS_ASSETS["app"]
    enhancement_path = REPO / JS_ASSETS["glee-site-enhancements"]
    stale = False
    if enhancement_path.exists():
        enhancement_token = normalized_hash(enhancement_path)
        js_tokens["glee-site-enhancements"] = enhancement_token
    if app_path.exists():
        app_source = app_path.read_text(encoding="utf-8", errors="replace")
        app_patched = (
            rewrite_javascript_refs(app_source, {"glee-site-enhancements": js_tokens["glee-site-enhancements"]})
            if "glee-site-enhancements" in js_tokens
            else app_source
        )
        if search_index_token:
            app_patched = rewrite_search_index_refs(app_patched, search_index_token)
        if app_patched != app_source:
            stale = True
            if args.check:
                print("  STALE: assets/js/app.js adapter import")
            else:
                app_path.write_text(app_patched, encoding="utf-8")
        js_tokens["app"] = normalized_hash_bytes(app_patched.encode("utf-8"))
    js_tokens.update(
        {name: token for name, token in javascript_tokens(REPO).items() if name not in js_tokens}
    )
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
        patched = rewrite_javascript_refs(patched, js_tokens)
        if search_index_token:
            patched = rewrite_search_index_refs(patched, search_index_token)
        if patched == src:
            unchanged += 1
        else:
            if args.check:
                print(f"  STALE: {path.relative_to(REPO).as_posix()}")
                stale = True
            else:
                path.write_text(patched, encoding="utf-8")
            updated += 1

    if updated:
        print(f"  CSS token -> {token}  ({updated} file(s) updated, {unchanged} already current)")
    else:
        print(f"  CSS token -> {token}  (all {unchanged} file(s) already current)")

    worker = REPO / "sw.js"
    if worker.exists():
        source = worker.read_text(encoding="utf-8")
        patched = CSS_REF_RE.sub(replacement, source)
        patched = rewrite_javascript_refs(patched, js_tokens)
        if search_index_token:
            patched = rewrite_search_index_refs(patched, search_index_token)
        entries = re.search(r"const PRECACHE_URLS\s*=\s*\[(.*?)\];", patched, re.S)
        if not entries:
            print("ERROR: service-worker precache list is missing")
            return 1
        digest = hashlib.sha256()
        for entry in re.findall(r'"([^"\n]+)"', entries.group(1)):
            local_path = REPO / entry.split("?", 1)[0].lstrip("/")
            if local_path.is_dir():
                local_path /= "index.html"
            digest.update(entry.encode("utf-8"))
            digest.update(local_path.read_bytes().replace(b"\r\n", b"\n"))
        version = str(int(digest.hexdigest()[:16], 16))
        patched = re.sub(r'glee-fully-shell-v\d+', 'glee-fully-shell-v' + version, patched)
        if patched != source:
            if args.check:
                print("ERROR: offline shell is stale. Run scripts/sync-css-version.py after all content generators.")
                return 1
            worker.write_text(patched, encoding="utf-8")
            print("  Offline shell version and precache URLs synchronized")
    if args.check and updated:
        print(
            f"ERROR: {updated} HTML file(s) have stale cache tokens. "
            "Run python3 scripts/sync-css-version.py before release."
        )
        stale = True
    return 1 if args.check and stale else 0


if __name__ == "__main__":
    sys.exit(main())

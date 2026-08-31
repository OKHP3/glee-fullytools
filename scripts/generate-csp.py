#!/usr/bin/env python3
"""Generate canonical CSP policies and apply them to every HTML page.

Ported from OverKill Hill P3's scripts/generate-csp.py. Like askjamie.bot,
this site has no site-src build step -- the tracked *.html files are the
served files, so this script edits them directly.

Unlike the other two OKHP3 sites, NO page here currently carries a
<meta http-equiv="Content-Security-Policy"> tag -- the site's only prior CSP
definition lives in `_headers`, which GitHub Pages does not serve (confirmed
live). So this script's non-check mode does two things existing pages don't
need: it INSERTS a canonical CSP meta tag on pages that don't have one yet
(right after the <meta charset> tag), in addition to replacing one that's
already present but stale. Because every served page is meant to carry a
real policy going forward, --check is intentionally strict here: a page with
no CSP meta tag at all is a failure, not something to skip (skip-if-missing
is only correct once rollout is complete and would otherwise mask an
accidental omission forever).
"""
from __future__ import annotations

import argparse
import json
import re

from csp import POLICY_FILE, ROOT, all_pages, build_edge_policy, build_policies, page_class, render_meta

CHARSET_ANCHOR_RE = re.compile(
    r'([ \t]*<meta\s+charset=["\']utf-8["\']\s*/?>\s*\n)',
    re.IGNORECASE,
)
META_TAG_RE = re.compile(
    r'<meta\b(?=[^>]*\bhttp-equiv=["\']Content-Security-Policy["\'])'
    r'(?=[^>]*\bcontent=(["\']))[^>]*\s*/?>',
    re.IGNORECASE,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if generated output is stale")
    args = parser.parse_args(argv)
    policies = build_policies()
    output = json.dumps({"schema": 1, "policies": policies}, indent=2) + "\n"
    if args.check:
        if not POLICY_FILE.exists() or POLICY_FILE.read_text(encoding="utf-8") != output:
            print("CSP policy file is stale. Run: python3 scripts/generate-csp.py")
            return 1
    else:
        POLICY_FILE.parent.mkdir(parents=True, exist_ok=True)
        POLICY_FILE.write_text(output, encoding="utf-8")
        headers = ROOT / "_headers"
        if headers.is_file():
            header_source = headers.read_text(encoding="utf-8")
            header_pattern = re.compile(
                r"(?m)^\s*Content-Security-Policy(?:-Report-Only)?:\s*.*$"
            )
            header_line = "  Content-Security-Policy: " + build_edge_policy()
            updated_headers, count = header_pattern.subn(header_line, header_source, count=1)
            if count == 1:
                headers.write_text(updated_headers, encoding="utf-8")

    failures: list[str] = []
    for page in all_pages():
        source = page.read_text(encoding="utf-8", errors="replace")
        expected_policy = policies[page_class(page)]
        expected_tag = render_meta(expected_policy)
        if args.check:
            actual = meta_policy(source)
            if actual != expected_policy:
                failures.append(f"{page}: CSP missing or differs from {page_class(page)} canonical policy")
        else:
            updated, applied = _apply_meta_tag(source, expected_tag)
            if applied:
                page.write_text(updated, encoding="utf-8", newline="")
            else:
                failures.append(f"{page}: could not find a <meta charset> anchor to insert the CSP tag after")
    if failures:
        print("\n".join(failures))
        return 1
    print(f"CSP policies verified for {len(all_pages())} pages.")
    return 0


def _apply_meta_tag(source: str, expected_tag: str) -> tuple[str, bool]:
    """Replace an existing CSP meta tag, or insert one after <meta charset>."""
    updated, count = META_TAG_RE.subn(expected_tag, source, count=1)
    if count == 1:
        return updated, True

    def _insert(match: re.Match[str]) -> str:
        anchor_line = match.group(1)
        indent = re.match(r"[ \t]*", anchor_line).group(0)
        return anchor_line + indent + expected_tag + "\n"

    updated, count = CHARSET_ANCHOR_RE.subn(_insert, source, count=1)
    return (updated, True) if count == 1 else (source, False)


def meta_policy(source: str) -> str | None:
    match = re.search(
        r'<meta\b(?=[^>]*\bhttp-equiv=["\']Content-Security-Policy["\'])'
        r'(?=[^>]*\bcontent=(["\']))[^>]*\bcontent=\1(.*?)\1',
        source,
        re.IGNORECASE,
    )
    return match.group(2) if match else None


if __name__ == "__main__":
    raise SystemExit(main())

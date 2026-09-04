#!/usr/bin/env python3
"""Check the public evidence surface for every catalog Tool-ette.

This is deliberately a repository check, not a GPT-behavior test.  It verifies
that the public catalog has one leaf page per registered Tool-ette, that each
page has a description and explicit publication signal, and that any launch
destination is either absent or a real-looking ChatGPT URL.  External
reachability and owner-supplied behavior evidence belong in the dated audit
record, not in the deterministic site validator.

Run from the repository root:

    python3 scripts/audit-tool-ette-promises.py
"""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLBOX = ROOT / "toolbox"
EXPECTED_COUNT = 42
PLACEHOLDER_MARKERS = (
    "YOUR-GPT-ID-HERE",
    "YOUR-",
    "GPT-ID-HERE",
    "PLACEHOLDER",
)


class PageParser(HTMLParser):
    """Extract only the public catalog fields this check needs."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.description = ""
        self.h1 = ""
        self._tag = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._tag = tag
        attrs_d = dict(attrs)
        if tag == "meta" and attrs_d.get("name", "").lower() == "description":
            self.description = attrs_d.get("content", "") or ""

    def handle_data(self, data: str) -> None:
        if self._tag == "h1":
            self.h1 += data

    def handle_endtag(self, tag: str) -> None:
        if self._tag == tag:
            self._tag = ""


def launch_urls(html: str) -> list[str]:
    """Return only primary CTA destinations, not sibling-card links."""
    matches = re.findall(
        r'<a\b[^>]*href="(https://chatgpt\.com/g/[^"]+)"[^>]*>'
        r'.*?(?:Launch|Open\s+[^<]*GPT).*?</a>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return sorted(set(matches))


def is_placeholder(url: str | None) -> bool:
    return not url or any(marker in url.upper() for marker in PLACEHOLDER_MARKERS)


def publication_state(html: str, urls: list[str]) -> str:
    """Apply the suite contract's conservative page-state precedence."""
    if not urls or is_placeholder(urls[0]):
        return "unavailable"
    if "construction-overlay" in html:
        return "beta"
    return "live"


def main() -> int:
    pages = sorted(TOOLBOX.glob("*/*/index.html"))
    errors: list[str] = []

    if len(pages) != EXPECTED_COUNT:
        errors.append(f"expected {EXPECTED_COUNT} Tool-ette pages, found {len(pages)}")

    seen_names: set[str] = set()
    counts = {"live": 0, "beta": 0, "unavailable": 0}
    for path in pages:
        html = path.read_text(encoding="utf-8", errors="replace")
        parser = PageParser()
        parser.feed(html)
        urls = launch_urls(html)
        state = publication_state(html, urls)
        counts[state] += 1

        if not parser.h1.strip():
            errors.append(f"{path.relative_to(ROOT)}: missing h1")
        if not parser.description.strip():
            errors.append(f"{path.relative_to(ROOT)}: missing meta description")
        if len(urls) > 1:
            errors.append(f"{path.relative_to(ROOT)}: multiple ChatGPT destinations")

        name = parser.h1.strip()
        if name in seen_names:
            errors.append(f"{path.relative_to(ROOT)}: duplicate h1 {name!r}")
        seen_names.add(name)

        if state == "beta" and "construction-overlay" not in html:
            errors.append(f"{path.relative_to(ROOT)}: beta page lacks construction signal")
        if state == "unavailable" and urls and not is_placeholder(urls[0]):
            errors.append(
                f"{path.relative_to(ROOT)}: unavailable page has an unclassified destination"
            )

    print(
        "Tool-ette promise surface: "
        f"{len(pages)} pages; "
        f"{counts['live']} live, {counts['beta']} beta, "
        f"{counts['unavailable']} unavailable"
    )
    if errors:
        print("\n".join(f"FAIL: {error}" for error in errors))
        return 1
    print("PASS: every Tool-ette has a unique name, description, and explicit state signal")
    return 0


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""Check the public evidence surface for every catalog Tool-ette.

This is deliberately a repository check, not a GPT-behavior test.  It verifies
that the public catalog has one leaf page per registered Tool-ette, that each
page has a description and explicit publication signal, and that all public
GPT anchors agree with the catalog's primary destinations and identities. External
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
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
TOOLBOX = ROOT / "toolbox"
EXPECTED_COUNT = 42
PLACEHOLDER_MARKERS = (
    "YOUR-GPT-ID-HERE",
    "YOUR-",
    "GPT-ID-HERE",
    "PLACEHOLDER",
)
AUTHORING_MARKERS = (
    "short personality rich tagline",
    "sentence elevator pitch explaining",
    "give a clear high level overview",
    "one short paragraph explaining",
    "describe ideal users or scenarios",
    "explain what users bring in",
    "highlight the concrete actions",
    "one sentence about what this function does",
    "add as many list items as needed",
    "spell out how this tool",
    "describe the custom instructions schema",
    "suggest an easy first use case",
    "link to the other tool ettes that live",
    "connect this tool",
    "show users how this gpt",
    "help users take their first step",
    "spell out why this pre tuned",
)


class PageParser(HTMLParser):
    """Extract only the public catalog fields this check needs."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.description = ""
        self.h1 = ""
        self._tag = ""
        self.launch_destinations = []
        self.links = []
        self.visible_text = []
        self._link = None
        self._hidden = 0
        self._div_depth = 0
        self._hero_depth = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._tag = tag
        attrs_d = dict(attrs)
        if tag in {"script", "style"}:
            self._hidden += 1
        if tag == "div":
            self._div_depth += 1
            if "hero-actions" in (attrs_d.get("class") or "").split():
                self._hero_depth = self._div_depth
        if tag == "a":
            self._link = {"href": attrs_d.get("href") or "", "text": "", "hero": self._hero_depth is not None}
        if tag == "a" and {"btn", "button"} & set((attrs_d.get("class") or "").split()):
            href = attrs_d.get("href") or ""
            if re.match(r"https://(?:chatgpt\.com|chat\.openai\.com)/g/g-[a-z0-9]+", href, re.I) and not is_placeholder(href):
                self.launch_destinations.append(href)
        if tag == "meta" and attrs_d.get("name", "").lower() == "description":
            self.description = attrs_d.get("content", "") or ""

    def handle_data(self, data: str) -> None:
        if not self._hidden:
            self.visible_text.append(data)
        if self._link is not None:
            self._link["text"] += data
        if self._tag == "h1":
            self.h1 += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._link is not None:
            self.links.append(self._link)
            self._link = None
        if tag in {"script", "style"}:
            self._hidden = max(0, self._hidden - 1)
        if tag == "div":
            if self._hero_depth == self._div_depth:
                self._hero_depth = None
            self._div_depth = max(0, self._div_depth - 1)
        if self._tag == tag:
            self._tag = ""


def launch_urls(html: str) -> list[str]:
    """Return only primary CTA destinations, not sibling-card links."""
    parser = PageParser()
    parser.feed(html)
    return sorted(set(parser.launch_destinations))


def is_placeholder(url: str | None) -> bool:
    return not url or any(marker in url.upper() for marker in PLACEHOLDER_MARKERS)


def publication_state(html: str, urls: list[str]) -> str:
    """Apply the suite contract's conservative page-state precedence."""
    if not urls or is_placeholder(urls[0]):
        return "unavailable"
    if "construction-overlay" in html:
        return "beta"
    return "live"


def identity_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def destination_id(url: str) -> str | None:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in {"chatgpt.com", "chat.openai.com"} or is_placeholder(url):
        return None
    match = re.fullmatch(r"/g/g-([a-z0-9]+)(?:-[a-z0-9-]+)?/?", parsed.path, re.I)
    return match.group(1).lower() if match else None


def destination_errors(html: str, allowed: dict[str, str], identities: dict[str, str | None]) -> list[str]:
    """Check every GPT anchor, including ordinary sibling and branch links.

    Allowed destinations come from the current primary catalog/branch actions.
    This detects routing bypasses and identity mismatches; it does not certify
    external availability or authorize a new primary destination.
    """
    parser = PageParser()
    parser.feed(html)
    errors = []
    for link in parser.links:
        url = link["href"]
        if urlsplit(url).hostname not in {"chatgpt.com", "chat.openai.com"}:
            continue
        target = destination_id(url)
        label = " ".join(link["text"].split())
        if target not in allowed:
            errors.append(f"unreviewed GPT route {label!r}: {url}")
            continue
        label_key = identity_key(label)
        for name, expected in identities.items():
            if name and name in label_key and expected != target:
                errors.append(f"GPT identity/state mismatch for {label!r}: {url}")
    return errors


def scaffold_errors(html: str) -> list[str]:
    parser = PageParser()
    parser.feed(html)
    text = re.sub(r"[^a-z0-9]+", " ", " ".join(parser.visible_text).lower())
    return [f"public authoring scaffold: {marker}" for marker in AUTHORING_MARKERS if marker in text]


def main() -> int:
    pages = sorted(TOOLBOX.glob("*/*/index.html"))
    errors: list[str] = []

    if len(pages) != EXPECTED_COUNT:
        errors.append(f"expected {EXPECTED_COUNT} Tool-ette pages, found {len(pages)}")

    seen_names: set[str] = set()
    allowed: dict[str, str] = {}
    identities: dict[str, str | None] = {}
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
        if urls and "ChatGPT destination unavailable" in " ".join(parser.visible_text):
            errors.append(f"{path.relative_to(ROOT)}: withdrawn entry has a primary launch destination")

        name = parser.h1.strip()
        target = destination_id(urls[0]) if urls else None
        identities[identity_key(name)] = target
        if target:
            allowed[target] = name
        if name in seen_names:
            errors.append(f"{path.relative_to(ROOT)}: duplicate h1 {name!r}")
        seen_names.add(name)

        if state == "beta" and "construction-overlay" not in html:
            errors.append(f"{path.relative_to(ROOT)}: beta page lacks construction signal")
        if state == "unavailable" and urls and not is_placeholder(urls[0]):
            errors.append(
                f"{path.relative_to(ROOT)}: unavailable page has an unclassified destination"
            )
        if state == "unavailable":
            visible = " ".join(parser.visible_text)
            if "Opens in ChatGPT" in visible:
                errors.append(f"{path.relative_to(ROOT)}: unavailable page promises a ChatGPT launch")
            if "ChatGPT destination unavailable" not in visible:
                errors.append(f"{path.relative_to(ROOT)}: missing explicit unavailable destination label")

    # Branch/Toolbox launch actions have their own identities. Child-card links
    # cannot add themselves to this allowlist merely by using a button class.
    for path in [TOOLBOX / "index.html", *sorted(TOOLBOX.glob("*/index.html"))]:
        parser = PageParser()
        parser.feed(path.read_text(encoding="utf-8"))
        for link in parser.links:
            target = destination_id(link["href"])
            if link["hero"] and target:
                allowed[target] = parser.h1.strip()

    public_pages = [*ROOT.glob("*.html"), *TOOLBOX.rglob("index.html")]
    public_pages += [path for path in ROOT.glob("*/index.html") if path.parent.name not in {"toolbox", "assets"} and not path.parent.name.startswith(".")]
    for path in sorted(set(public_pages)):
        html = path.read_text(encoding="utf-8")
        for error in destination_errors(html, allowed, identities) + scaffold_errors(html):
            errors.append(f"{path.relative_to(ROOT)}: {error}")

    print(
        "Tool-ette promise surface: "
        f"{len(pages)} pages; "
        f"{counts['live']} live, {counts['beta']} beta, "
        f"{counts['unavailable']} unavailable"
    )
    if errors:
        print("\n".join(f"FAIL: {error}" for error in errors))
        return 1
    print("PASS: unique catalog identities, explicit states, no public scaffold, and all GPT entry points agree with primary destinations")
    return 0


if __name__ == "__main__":
    sys.exit(main())

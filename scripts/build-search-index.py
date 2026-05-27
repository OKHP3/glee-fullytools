#!/usr/bin/env python3
"""
Build a static client-side search index from every published HTML page.

Walks every *.html in the repo (excluding 404 / under-construction / partials),
extracts title / description / canonical URL / h1-h3 headings / visible body
text, and writes assets/data/search-index.json.

Run from repo root:
    python3 scripts/build-search-index.py

The output JSON is loaded by /assets/js/search.js at runtime.
"""

from __future__ import annotations

import json
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EXCLUDE_FILES = {"404.html", "under-construction.html"}
EXCLUDE_DIRS = {".git", ".local", ".cache", "node_modules", "attached_assets",
                "tools", ".github", ".vscode", ".agents", ".pythonlibs"}

SKIP_TAGS = {"script", "style", "noscript", "svg", "template"}
HEADING_TAGS = {"h1", "h2", "h3"}


class PageParser(HTMLParser):
    """Pulls title, meta description, canonical URL, headings, and body text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: str = ""
        self.description: str = ""
        self.canonical: str = ""
        self.keywords: str = ""
        self.headings: list[str] = []
        self.body_chunks: list[str] = []

        self._in_title = False
        self._in_head = False
        self._in_body = False
        self._skip_depth = 0
        self._heading_tag: str | None = None
        self._heading_buf: list[str] = []
        self._aria_hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_d = {k: (v or "") for k, v in attrs}

        if tag == "head":
            self._in_head = True
        elif tag == "body":
            self._in_body = True
        elif tag == "title" and self._in_head:
            self._in_title = True
        elif tag == "meta" and self._in_head:
            name = attrs_d.get("name", "").lower()
            prop = attrs_d.get("property", "").lower()
            content = attrs_d.get("content", "").strip()
            if name == "description" and content and not self.description:
                self.description = content
            elif prop == "og:description" and content and not self.description:
                self.description = content
            elif name == "keywords" and content:
                self.keywords = content
        elif tag == "link" and self._in_head:
            if attrs_d.get("rel", "").lower() == "canonical":
                self.canonical = attrs_d.get("href", "").strip()

        if tag in SKIP_TAGS:
            self._skip_depth += 1

        # Skip aria-hidden subtrees (decorative)
        if attrs_d.get("aria-hidden", "").lower() == "true":
            self._aria_hidden_depth += 1

        if self._in_body and tag in HEADING_TAGS and self._skip_depth == 0:
            self._heading_tag = tag
            self._heading_buf = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "head":
            self._in_head = False
        elif tag == "body":
            self._in_body = False
        elif tag == "title":
            self._in_title = False
        if tag in SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if self._aria_hidden_depth > 0 and tag not in SKIP_TAGS:
            # decrement only if this tag is the one currently hiding; coarse approximation
            self._aria_hidden_depth -= 1
            if self._aria_hidden_depth < 0:
                self._aria_hidden_depth = 0
        if tag in HEADING_TAGS and self._heading_tag == tag:
            text = clean_text("".join(self._heading_buf))
            if text:
                self.headings.append(text)
            self._heading_tag = None
            self._heading_buf = []

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
            return
        if not self._in_body or self._skip_depth > 0:
            return
        if self._aria_hidden_depth > 0:
            return
        if self._heading_tag is not None:
            self._heading_buf.append(data)
        text = data.strip()
        if text:
            self.body_chunks.append(text)


WS_RE = re.compile(r"\s+")
NBSP = "\u00a0"
NB_HYPHEN = "\u2011"


def clean_text(s: str) -> str:
    s = s.replace(NBSP, " ").replace(NB_HYPHEN, "-")
    return WS_RE.sub(" ", s).strip()


def derive_url(file_path: Path) -> str:
    """Convert a repo-relative file path to a canonical site URL path."""
    rel = file_path.relative_to(REPO_ROOT).as_posix()
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    return "/" + rel


def derive_section(url: str) -> str:
    """Human-readable section name for filtering / grouping."""
    if url == "/":
        return "Home"
    if url.startswith("/toolbox/"):
        parts = [p for p in url.split("/") if p]
        if len(parts) == 1:
            return "Toolbox"
        if len(parts) == 2:
            return "Branch"
        return "Tool"
    if url.startswith("/about/"):
        return "About"
    if url.startswith("/contact/"):
        return "Contact"
    if url.startswith("/legal/"):
        return "Legal"
    if url.startswith("/persona/"):
        return "Persona"
    if url.startswith("/ecosystem/"):
        return "Ecosystem"
    if url.startswith("/universe/"):
        return "Universe"
    if url.startswith("/showcase/"):
        return "Showcase"
    return "Page"


def derive_branch(url: str) -> str:
    """For toolbox tools, the branch slug they belong to (e.g. '01-discovered-careers')."""
    if not url.startswith("/toolbox/"):
        return ""
    parts = [p for p in url.split("/") if p]
    if len(parts) >= 2:
        return parts[1] if parts[1] != "toolbox" else ""
    return ""


def collect_html_files() -> list[Path]:
    files: list[Path] = []
    for path in REPO_ROOT.rglob("*.html"):
        if any(part in EXCLUDE_DIRS for part in path.relative_to(REPO_ROOT).parts):
            continue
        if path.name in EXCLUDE_FILES:
            continue
        files.append(path)
    return sorted(files)


def trim_text(text: str, max_words: int = 220) -> str:
    """Cap body text so the index stays small (~3-5 KB per page)."""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


def build_entry(path: Path) -> dict | None:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    parser = PageParser()
    try:
        parser.feed(raw)
    except Exception as exc:
        print(f"  ! parse error in {path}: {exc}", file=sys.stderr)
        return None

    title = clean_text(parser.title)
    description = clean_text(parser.description)
    canonical = parser.canonical.strip() or ""

    # The file path is the AUTHORITATIVE source of URL. Canonical can only
    # OVERRIDE when it points to a different path *within the same site*
    # AND the file path is not the homepage. This guards against the failure
    # mode where an inner page mistakenly declares canonical="https://site/"
    # — that's a real SEO bug we want to expose, not propagate.
    url = derive_url(path)
    file_is_home = url == "/"

    if canonical:
        m = re.match(r"https?://[^/]+(/.*)?$", canonical)
        if m:
            canonical_path = m.group(1) or "/"
            if canonical_path == "/" and not file_is_home:
                # Broken canonical — log loudly, keep the file-derived URL
                print(
                    f"  ! canonical points to homepage but file is {path.relative_to(REPO_ROOT)} "
                    f"— ignoring canonical, using {url}",
                    file=sys.stderr,
                )
            else:
                url = canonical_path

    body_text = clean_text(" ".join(parser.body_chunks))
    body_text = trim_text(body_text, max_words=220)

    headings = [clean_text(h) for h in parser.headings if clean_text(h)]
    # Dedupe headings while preserving order
    seen = set()
    unique_headings = []
    for h in headings:
        if h.lower() not in seen:
            seen.add(h.lower())
            unique_headings.append(h)

    section = derive_section(url)
    branch = derive_branch(url)

    if not title:
        return None

    return {
        "url": url,
        "title": title,
        "description": description,
        "section": section,
        "branch": branch,
        "headings": unique_headings[:12],
        "keywords": parser.keywords,
        "body": body_text,
    }


def main() -> int:
    out_path = REPO_ROOT / "assets" / "data" / "search-index.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    entries: list[dict] = []
    files = collect_html_files()
    print(f"Indexing {len(files)} HTML pages…")
    for path in files:
        entry = build_entry(path)
        if entry is None:
            print(f"  - skipped (no title): {path.relative_to(REPO_ROOT)}")
            continue
        entries.append(entry)

    # Validation: catch duplicate URLs and ensure no non-home page resolves to "/"
    seen_urls: dict[str, str] = {}
    duplicates: list[tuple[str, str, str]] = []
    bad_home: list[str] = []
    for e in entries:
        u = e["url"]
        if u in seen_urls and seen_urls[u] != e["title"]:
            duplicates.append((u, seen_urls[u], e["title"]))
        seen_urls.setdefault(u, e["title"])
        if u == "/" and e["section"] != "Home":
            bad_home.append(e["title"])

    if duplicates:
        print("\n!! DUPLICATE URLs in index:", file=sys.stderr)
        for u, t1, t2 in duplicates:
            print(f"   {u}\n     - {t1}\n     - {t2}", file=sys.stderr)
    if bad_home:
        print("\n!! Non-home pages resolved to '/':", file=sys.stderr)
        for t in bad_home:
            print(f"   - {t}", file=sys.stderr)
    if duplicates or bad_home:
        print("\nIndex written but VALIDATION FAILED — please review.", file=sys.stderr)

    payload = {
        "generated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "version": 1,
        "site": "https://glee-fully.tools",
        "count": len(entries),
        "pages": entries,
    }

    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    size_kb = out_path.stat().st_size / 1024
    print(f"\nWrote {out_path.relative_to(REPO_ROOT)} — {len(entries)} pages, {size_kb:.1f} KB")
    return 0 if not (duplicates or bad_home) else 2


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Read-only evidence-boundary check for the current Tool-ette catalog.

The current catalog has no independently verified application configuration,
pricing, or application screenshots. It describes WebPages and intended uses.
If reviewed application evidence is added later, narrow this check's scope in
the same reviewed change; this is not a universal ban on application schema.
"""

from __future__ import annotations

import argparse
import json
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class CatalogParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.canonical = ""
        self.documents = []
        self._script = None
        self.evidence_text = []
        self._evidence = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonical = attrs.get("href", "")
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self._script = []
        if tag == "p" and attrs.get("id") == "catalog-evidence":
            self._evidence = "hidden" not in attrs and attrs.get("aria-hidden") != "true"

    def handle_data(self, data):
        if self._script is not None:
            self._script.append(data)
        elif self._evidence:
            self.evidence_text.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._script is not None:
            self.documents.append("".join(self._script))
            self._script = None
        if tag == "p":
            self._evidence = False


def nodes(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from nodes(child)


def check_claims(html, *, unverified_application=True):
    """Inspect claims; callers may explicitly scope a verified future product."""
    parser = CatalogParser()
    parser.feed(html)
    errors = []
    graph = []
    for document in parser.documents:
        try:
            graph.extend(nodes(json.loads(document)))
        except (ValueError, TypeError) as exc:
            errors.append(f"Invalid JSON-LD: {exc}")
    if not parser.canonical:
        errors.append("Missing canonical URL")
    if not graph:
        errors.append("Missing structured data")
    if unverified_application:
        pages = [node for node in graph if node.get("@type") == "WebPage"
                 and node.get("url") == parser.canonical]
        if len(pages) != 1:
            errors.append("Unverified catalog detail needs one canonical WebPage")
        for node in graph:
            types = node.get("@type", [])
            types = [types] if isinstance(types, str) else types
            if "SoftwareApplication" in types:
                errors.append("Application identity has no reviewed evidence")
            for key in ("offers", "isAccessibleForFree", "operatingSystem", "applicationCategory"):
                if key in node:
                    errors.append(f"Unverified application claim: {key}")
        evidence = " ".join(parser.evidence_text).lower()
        if not all(phrase in evidence for phrase in ("intended use", "not verified", "own notes")):
            errors.append("Missing visible intended-use and provider boundary")
    for node in graph:
        if "screenshot" in node:
            images = json.dumps(node["screenshot"]).lower()
            if "illustration" in images:
                errors.append("Concept illustration is not an application screenshot")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    pages = sorted((ROOT / "toolbox").glob("*/*/index.html"))
    results = [{"path": page.relative_to(ROOT).as_posix(),
                "errors": check_claims(page.read_text(encoding="utf-8"))}
               for page in pages]
    report = {"pages": len(pages), "errors": sum(len(row["errors"]) for row in results),
              "results": results}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(not pages or report["errors"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())

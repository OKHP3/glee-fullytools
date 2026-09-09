#!/usr/bin/env python3
"""Check sanitized search-console coverage records against the public sitemap.

This is deliberately a local, credential-free check.  The sitemap supplies
the exact public URL set while ``config/public-inventory.json`` supplies the
canonical origin, HTML boundary, and catalog URL rules.  The evidence file
stores only aggregate, non-secret scope metadata for Google and Bing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent.parent
CONFIG_NAME = Path("config/public-inventory.json")
SITEMAP_NAME = Path("sitemap.xml")
EVIDENCE_NAME = Path("docs/discovery-evidence.md")
SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"
RECORD_HEADING = "## Sanitized coverage record"
RECORD_PATTERN = re.compile(
    rf"{re.escape(RECORD_HEADING)}.*?```json\s*(.*?)\s*```",
    re.IGNORECASE | re.DOTALL,
)
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SCOPE_SOURCE = "config/public-inventory.json + sitemap.xml"


def load_inventory(root: Path) -> dict:
    return json.loads((root / CONFIG_NAME).read_text(encoding="utf-8"))


def _is_scoped_html(path: Path, root: Path, inventory: dict) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return False
    for excluded in inventory["html_scope"]["excluded_directories"]:
        excluded_parts = Path(excluded).parts
        if relative.parts[: len(excluded_parts)] == excluded_parts:
            return False
    return path.suffix.lower() == ".html"


def _path_for_url(url: str, origin: str) -> Path | None:
    parsed = urlsplit(url)
    expected = urlsplit(origin)
    if (
        parsed.scheme != expected.scheme
        or parsed.netloc != expected.netloc
        or parsed.query
        or parsed.fragment
    ):
        return None
    path = parsed.path or "/"
    if path == "/":
        return Path("index.html")
    if path.endswith("/"):
        return Path(path.lstrip("/")) / "index.html"
    return Path(path.lstrip("/"))


def _page_type(url: str, origin: str, inventory: dict) -> str:
    parsed = urlsplit(url)
    path = parsed.path or "/"
    catalog = inventory["catalog"]
    if path == "/":
        return "home"
    if re.match(catalog["toolbox_hub"], path):
        return "toolbox_hub"
    if re.match(catalog["tool_ette"], path):
        return "tool-ette"
    if re.match(catalog["branch"], path):
        return "branch"
    return "supporting"


def _scope_digest(urls: set[str]) -> str:
    canonical = "\n".join(sorted(urls))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def derive_scope(root: Path) -> tuple[dict, list[str]]:
    """Return current sitemap scope metadata and actionable structural issues."""
    issues: list[str] = []
    try:
        inventory = load_inventory(root)
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        return {}, [f"{CONFIG_NAME} could not be read: {exc}"]

    origin = str(inventory.get("site", "")).rstrip("/")
    if not origin:
        issues.append(f"{CONFIG_NAME} has no site origin")
    if not inventory.get("discovery", {}).get("sitemap"):
        issues.append(f"{CONFIG_NAME} disables sitemap discovery; coverage scope cannot be checked")

    sitemap = root / SITEMAP_NAME
    if not sitemap.is_file():
        return {}, issues + [f"{SITEMAP_NAME} is missing"]
    try:
        tree = ET.parse(sitemap)
    except ET.ParseError as exc:
        return {}, issues + [f"{SITEMAP_NAME} is unparseable: {exc}"]

    locs = [
        (element.text or "").strip()
        for element in tree.iter(f"{{{SITEMAP_NAMESPACE}}}loc")
    ]
    if not locs:
        issues.append(f"{SITEMAP_NAME} contains no URL locations")
    duplicates = sorted({url for url in locs if locs.count(url) > 1})
    if duplicates:
        issues.append(f"{SITEMAP_NAME} contains duplicate URLs: {', '.join(duplicates)}")

    urls = {url for url in locs if url}
    for url in sorted(urls):
        relative = _path_for_url(url, origin)
        if relative is None:
            issues.append(f"sitemap URL is outside the configured site origin or has a query: {url}")
            continue
        if ".." in relative.parts:
            issues.append(f"sitemap URL escapes the repository path boundary: {url}")
            continue
        path = root / relative
        if not path.is_file():
            issues.append(f"sitemap URL has no matching public HTML file: {url}")
        elif not _is_scoped_html(path, root, inventory):
            issues.append(f"sitemap URL points outside the configured HTML scope: {url}")
        elif path.name in set(inventory["html_scope"]["excluded_files"]):
            issues.append(f"sitemap URL points to an excluded HTML file: {url}")

    breakdown = {
        kind: sum(_page_type(url, origin, inventory) == kind for url in urls)
        for kind in ("home", "toolbox_hub", "branch", "tool-ette", "supporting")
    }
    return {
        "site": origin,
        "url_count": len(urls),
        "url_sha256": _scope_digest(urls),
        "breakdown": breakdown,
    }, issues


def load_coverage_record(root: Path) -> tuple[dict, list[str]]:
    evidence = root / EVIDENCE_NAME
    if not evidence.is_file():
        return {}, [f"{EVIDENCE_NAME} is missing"]
    text = evidence.read_text(encoding="utf-8")
    match = RECORD_PATTERN.search(text)
    if not match:
        return {}, [
            f"{EVIDENCE_NAME} has no JSON block under {RECORD_HEADING}"
        ]
    try:
        record = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        return {}, [f"{EVIDENCE_NAME} coverage record is invalid JSON: {exc}"]
    if not isinstance(record, dict):
        return {}, [f"{EVIDENCE_NAME} coverage record must be a JSON object"]
    return record, []


def _valid_date(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _check_scope_values(label: str, recorded: object, current: dict) -> list[str]:
    if not isinstance(recorded, dict):
        return [f"{label} is missing its scope object"]
    issues: list[str] = []
    if recorded.get("url_count") != current["url_count"]:
        issues.append(
            f"{label} scope is stale: recorded {recorded.get('url_count')!r} URLs; "
            f"current sitemap has {current['url_count']}"
        )
    digest = recorded.get("url_sha256")
    if not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest):
        issues.append(f"{label} scope digest is not a lowercase SHA-256 value")
    if digest != current["url_sha256"]:
        issues.append(
            f"{label} URL scope digest does not match the current sitemap "
            f"(recorded {digest!r}; current {current['url_sha256']})"
        )
    return issues


def check_record(current: dict, record: dict) -> list[str]:
    issues: list[str] = []
    if record.get("schema") != 1:
        issues.append("coverage record schema must be 1")
    review_date = record.get("review_date")
    if not _valid_date(review_date):
        issues.append("coverage record review_date must be an ISO date (YYYY-MM-DD)")

    overall_scope = record.get("scope")
    if isinstance(overall_scope, dict) and overall_scope.get("source") != SCOPE_SOURCE:
        issues.append(
            f"overall scope source must be {SCOPE_SOURCE!r}"
        )
    issues.extend(_check_scope_values("overall", overall_scope, current))
    records = record.get("records")
    if not isinstance(records, dict):
        return issues + ["coverage record must contain Google and Bing records"]

    expected = {
        "google-search-console": "Google Search Console",
        "bing-webmaster-tools": "Bing Webmaster Tools",
    }
    for key, label in expected.items():
        entry = records.get(key)
        if not isinstance(entry, dict):
            issues.append(f"coverage record is missing {label}")
            continue
        if entry.get("review_date") != review_date:
            issues.append(
                f"{label} review date {entry.get('review_date')!r} does not match "
                f"the record review date {review_date!r}"
            )
        issues.extend(_check_scope_values(label, entry.get("scope"), current))
    return issues


def check(root: Path) -> tuple[dict, list[str]]:
    current, scope_issues = derive_scope(root)
    if not current:
        return {}, scope_issues
    record, record_issues = load_coverage_record(root)
    return current, scope_issues + record_issues + check_record(current, record)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="repository root to check (default: current repository)",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    current, issues = check(root)
    if issues:
        for issue in issues:
            print(f"ERROR: {issue}", file=sys.stderr)
        return 1
    print(
        "Search coverage scope is current: "
        f"{current['url_count']} sitemap URLs; "
        f"sha256={current['url_sha256']}"
    )
    print("Google Search Console: review date and URL scope match")
    print("Bing Webmaster Tools: review date and URL scope match")
    return 0


if __name__ == "__main__":
    sys.exit(main())
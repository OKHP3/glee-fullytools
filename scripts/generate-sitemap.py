#!/usr/bin/env python3
"""Generate the sitemap from the shared public inventory and search index."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from public_inventory import is_discoverable, sitemap_settings, site_origin

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "assets" / "data" / "search-index.json"
OUTPUT = ROOT / "sitemap.xml"


def render() -> str:
    if not INDEX.exists():
        raise FileNotFoundError(f"{INDEX.relative_to(ROOT)} is missing; build the search index first")
    payload = json.loads(INDEX.read_text(encoding="utf-8"))
    pages = payload.get("pages", [])
    urls = [
        page["url"] for page in pages
        if isinstance(page, dict)
        and page.get("url")
        and is_discoverable(page["url"], "sitemap")
    ]
    urls = sorted(set(urls), key=lambda url: (url != "/", url))
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        "",
    ]
    for path in urls:
        lastmod, changefreq, priority = sitemap_settings(path)
        loc = escape(site_origin() + path)
        lines.extend([
            "  <url>",
            f"    <loc>{loc}</loc>",
            f"    <lastmod>{lastmod}</lastmod>",
            f"    <changefreq>{changefreq}</changefreq>",
            f"    <priority>{priority}</priority>",
            "  </url>",
        ])
    lines.extend(["</urlset>", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if sitemap.xml is stale")
    args = parser.parse_args()
    rendered = render()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != rendered:
            print("ERROR: sitemap.xml is stale; run python3 scripts/generate-sitemap.py", file=sys.stderr)
            return 1
        print(f"Committed sitemap.xml is current")
        return 0
    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"Wrote sitemap.xml - {rendered.count('<url>')} URLs")
    return 0


if __name__ == "__main__":
    sys.exit(main())

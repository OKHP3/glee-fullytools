#!/usr/bin/env python3
"""Generate the Atom update feed from the shared public inventory."""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

from public_inventory import is_discoverable, site_origin, load_inventory

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "assets" / "data" / "search-index.json"
OUTPUT = ROOT / "feed.xml"


def render() -> str:
    if not INDEX.exists():
        raise FileNotFoundError(f"{INDEX.relative_to(ROOT)} is missing; build the search index first")
    payload = json.loads(INDEX.read_text(encoding="utf-8"))
    pages = [
        page for page in payload.get("pages", [])
        if isinstance(page, dict)
        and page.get("url")
        and is_discoverable(page["url"], "feed")
    ]
    pages.sort(key=lambda page: page["url"])
    updated = load_inventory()["sitemap"]["lastmod"] + "T00:00:00Z"
    items: list[str] = []
    for page in pages:
        url = html.escape(site_origin() + page["url"], quote=True)
        title = html.escape(page.get("title", "").split(" — ")[0])
        summary = html.escape(page.get("description", ""))
        items.append(
            "  <entry>\n"
            f"    <title>{title}</title>\n"
            f'    <link href="{url}" />\n'
            f"    <id>{url}</id>\n"
            f"    <updated>{updated}</updated>\n"
            f"    <summary>{summary}</summary>\n"
            "  </entry>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<feed xmlns="http://www.w3.org/2005/Atom">\n'
        '  <title>Glee-fully Personalizable Tools™ — New &amp; Updated</title>\n'
        f'  <link href="{site_origin()}/feed.xml" rel="self" />\n'
        f'  <link href="{site_origin()}/" />\n'
        f'  <id>{site_origin()}/</id>\n'
        f"  <updated>{updated}</updated>\n"
        '  <author><name>Glee-fully Personalizable Tools™</name></author>\n'
        '  <subtitle>The retro-bright toolbox of Custom GPTs for life, work, and wonder.</subtitle>\n'
        + "\n".join(items)
        + "\n</feed>\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if feed.xml is stale")
    args = parser.parse_args()
    rendered = render()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != rendered:
            print("ERROR: feed.xml is stale; run python3 scripts/generate-feed.py", file=sys.stderr)
            return 1
        print("Committed feed.xml is current")
        return 0
    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"Wrote feed.xml - {rendered.count('<entry>')} entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())

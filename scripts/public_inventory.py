#!/usr/bin/env python3
"""Shared public-inventory scope for discovery and release tooling.

The JSON contract in ``config/public-inventory.json`` is intentionally small:
it defines which HTML files are public discovery pages, which URL shapes are
catalog entries, and which output families include each page. Generators still
read titles and descriptions from HTML, but they must not invent their own
scope rules.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "public-inventory.json"


def load_inventory() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def site_origin() -> str:
    return load_inventory()["site"].rstrip("/")


def _excluded_parts() -> set[str]:
    return set(load_inventory()["html_scope"]["excluded_directories"])


def _excluded_files() -> set[str]:
    return set(load_inventory()["html_scope"]["excluded_files"])


def is_scoped_html(path: Path, root: Path = ROOT) -> bool:
    """Whether an HTML file is inside the validator's public HTML boundary."""
    try:
        rel = path.relative_to(root)
    except ValueError:
        return False
    for excluded in _excluded_parts():
        excluded_parts = Path(excluded).parts
        if rel.parts[:len(excluded_parts)] == excluded_parts:
            return False
    return path.suffix.lower() == ".html"


def collect_html_files(root: Path = ROOT) -> list[Path]:
    """Return all validator-scoped HTML files, including utility fallbacks."""
    return sorted(
        path for path in root.rglob("*.html")
        if is_scoped_html(path, root)
    )


def is_indexable_path(path: Path, root: Path = ROOT) -> bool:
    return is_scoped_html(path, root) and path.name not in _excluded_files()


def collect_indexable_html_files(root: Path = ROOT) -> list[Path]:
    return sorted(
        path for path in collect_html_files(root)
        if is_indexable_path(path, root)
    )


def derive_url(path: Path, root: Path = ROOT) -> str:
    rel = path.relative_to(root).as_posix()
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    return "/" + rel


def _pattern(name: str) -> re.Pattern[str]:
    return re.compile(load_inventory()["catalog"][name])


def page_type(url: str) -> str:
    if url == "/":
        return "home"
    if _pattern("toolbox_hub").match(url):
        return "toolbox_hub"
    if _pattern("tool_ette").match(url):
        return "tool-ette"
    if _pattern("branch").match(url):
        return "branch"
    return "supporting"


def is_discoverable(url: str, output: str) -> bool:
    """Return whether a URL belongs in sitemap/search/feed output."""
    config = load_inventory()["discovery"]
    kind = page_type(url)
    if output == "feed":
        return kind in config["feed_types"]
    if output in ("sitemap", "search"):
        return bool(config[output])
    raise ValueError(f"unknown inventory output: {output}")


def iter_indexable_urls(root: Path = ROOT) -> Iterable[str]:
    for path in collect_indexable_html_files(root):
        url = derive_url(path, root)
        if is_discoverable(url, "search"):
            yield url


def sitemap_settings(url: str) -> tuple[str, str, str]:
    config = load_inventory()["sitemap"]
    kind = page_type(url)
    changefreq = config["changefreq"].get(kind, config["changefreq"]["supporting"])
    priority = config["priority"].get(kind, config["priority"]["supporting"])
    return config["lastmod"], changefreq, priority


def is_counted_destination(url: str) -> bool:
    """Whether a Tool-ette destination is included in public catalog stats."""
    return url not in set(load_inventory()["catalog"]["destination_exclusions"])


def expected_public_top_level() -> set[str]:
    """Top-level files/directories allowed in a Pages artifact."""
    return {
        "404.html",
        "CNAME",
        "_headers",
        ".nojekyll",
        "about",
        "arcade",
        "assets",
        "contact",
        "ecosystem",
        "foundry",
        "favicon.ico",
        "feed.xml",
        "humans.txt",
        "index.html",
        "legal",
        "llms.txt",
        "offline.html",
        "persona",
        "robots.txt",
        "search",
        "showcase",
        "site.webmanifest",
        "sitemap.xml",
        "sw.js",
        "toolbox",
        "universe",
        "under-construction.html",
        "release-provenance.json",
        ".well-known",
    }


def forbidden_artifact_parts() -> set[str]:
    """Names that must never cross the source-to-Pages publication boundary."""
    return {
        ".agents",
        ".cache",
        ".git",
        ".github",
        ".local",
        ".pythonlibs",
        ".vscode",
        "attached_assets",
        "attached-assets",
        "audit",
        "docs",
        "node_modules",
        "package-lock.json",
        "package.json",
        "replit.md",
        ".replit",
        "scripts",
        "templates",
        "downloads",
    }

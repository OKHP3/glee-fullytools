"""Targeted regression checks for the public FoundRy feature page."""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET


REPO_ROOT = Path(__file__).resolve().parents[2]
FOUNDRY = REPO_ROOT / "foundry" / "index.html"
SITEMAP = REPO_ROOT / "sitemap.xml"
SEARCH_INDEX = REPO_ROOT / "assets" / "data" / "search-index.json"
FOUNDRY_URL = "https://glee-fully.tools/foundry/"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class FoundryPageTests(unittest.TestCase):
    def setUp(self):
        self.html = read_text(FOUNDRY)

    def test_foundry_route_and_metadata_are_published(self):
        self.assertIn('<link rel="canonical" href="https://glee-fully.tools/foundry/" />', self.html)
        self.assertIn('<meta property="og:url" content="https://glee-fully.tools/foundry/" />', self.html)
        self.assertIn('<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1" />', self.html)
        self.assertIn('<meta name="description" content="Meet the Glee-fully FoundRy: a locally run workbench with public source for shaping useful GPTs, Agent Skills, workflows and web tools, with clear briefs, recorded evidence and portable packages." />', self.html)
        self.assertIn('<title>Glee‑fully FoundRy | Glee‑fully Personalizable Tools™</title>', self.html)

    def test_foundry_source_cta_and_local_only_boundary_remain_explicit(self):
        self.assertIn('href="https://github.com/OKHP3/Glee-fullyTools-FoundRy"', self.html)
        self.assertIn('Open the GitHub repository', self.html)
        self.assertIn("This public page introduces that work. There is currently no hosted builder, account sign-up or embedded application here.", self.html)
        self.assertIn('This feature page does not host the builder.', self.html)
        self.assertIn("The local application saves projects on the builder’s computer.", self.html)

    def test_foundry_is_listed_in_sitemap_and_search_index(self):
        sitemap = ET.fromstring(read_text(SITEMAP))
        urls = {url.findtext("{*}loc") for url in sitemap.findall("{*}url")}
        self.assertIn(FOUNDRY_URL, urls)

        search_index = json.loads(read_text(SEARCH_INDEX))
        pages = search_index["pages"]
        match = next((page for page in pages if page["url"] == "/foundry/"), None)
        self.assertIsNotNone(match, "FoundRy is missing from the search index")
        self.assertEqual(match["title"], "Glee-fully FoundRy | Glee-fully Personalizable Tools™")
        self.assertEqual(match["url"], "/foundry/")
        self.assertIn("public source", match["description"])


if __name__ == "__main__":
    unittest.main()

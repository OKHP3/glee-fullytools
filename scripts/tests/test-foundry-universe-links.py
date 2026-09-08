"""Source-backed link contract for the FoundRy page and universe map."""
import json
import re
import tempfile
import unittest
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FOUNDRY_PAGE = ROOT / "foundry/index.html"
UNIVERSE_MAP = ROOT / "assets/data/universe-map.json"


@dataclass(frozen=True)
class Link:
    href: str
    target: str | None
    rel: frozenset[str]
    text: str


class AnchorCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[Link] = []
        self._current: dict[str, str | None] | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        data = {name: value for name, value in attrs}
        self._current = {
            "href": data.get("href"),
            "target": data.get("target"),
            "rel": data.get("rel"),
        }
        self._text = []

    def handle_data(self, data):
        if self._current is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag != "a" or self._current is None:
            return
        rel = frozenset(filter(None, re.split(r"\s+", self._current["rel"] or "")))
        self.links.append(
            Link(
                href=self._current["href"] or "",
                target=self._current["target"],
                rel=rel,
                text=" ".join(part.strip() for part in self._text).strip(),
            )
        )
        self._current = None
        self._text = []


def read_foundry_links(path: Path) -> list[Link]:
    parser = AnchorCollector()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser.links


def read_root_universe_nodes(path: Path) -> set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    for diagram in data["diagrams"]:
        if (
            diagram["parent"] == "https://glee-fully.tools/"
            and "https://glee-fully.tools/foundry/" in diagram["nodes"]
        ):
            return set(diagram["nodes"])
    raise AssertionError("root universe diagram with FoundRy node was not found")


class FoundryUniverseLinkTests(unittest.TestCase):
    def assert_link(self, links, text, href, *, target=None, rel=frozenset()):
        for link in links:
            if link.text == text:
                self.assertEqual(link.href, href)
                self.assertEqual(link.target, target)
                self.assertEqual(link.rel, rel)
                return
        self.fail(f"missing link text: {text!r}")

    def test_rel_token_order_is_not_semantic(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "links.html"
            fixture.write_text(
                '<a href="https://example.test" target="_blank" rel="noreferrer noopener">Example</a>',
                encoding="utf-8",
            )
            self.assert_link(
                read_foundry_links(fixture),
                "Example",
                "https://example.test",
                target="_blank",
                rel=frozenset(("noopener", "noreferrer")),
            )

    def test_foundry_page_and_universe_map_declare_the_same_core_relationships(self):
        links = read_foundry_links(FOUNDRY_PAGE)
        nodes = read_root_universe_nodes(UNIVERSE_MAP)

        self.assert_link(
            links,
            "Open the GitHub repository",
            "https://github.com/OKHP3/Glee-fullyTools-FoundRy",
            target="_blank",
            rel=frozenset(("noopener", "noreferrer")),
        )
        self.assert_link(
            links,
            "Skillz",
            "https://okhp3.github.io/skillz/",
            target="_blank",
            rel=frozenset(("noopener", "noreferrer")),
        )
        self.assert_link(links, "our universe map", "/universe/")
        self.assert_link(links, "OKHP³™ Universe", "/universe/")

        self.assertIn("https://glee-fully.tools/foundry/", nodes)
        self.assertIn("https://glee-fully.tools/universe/", nodes)

    def test_changed_destination_is_rejected_in_a_synthetic_fixture(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            foundry = root / "foundry/index.html"
            universe = root / "assets/data/universe-map.json"
            foundry.parent.mkdir(parents=True)
            universe.parent.mkdir(parents=True)
            foundry.write_text(FOUNDRY_PAGE.read_text(encoding="utf-8"), encoding="utf-8")
            universe.write_text(UNIVERSE_MAP.read_text(encoding="utf-8"), encoding="utf-8")

            text = foundry.read_text(encoding="utf-8").replace(
                "https://okhp3.github.io/skillz/",
                "https://okhp3.github.io/skillz/bad/",
                1,
            )
            foundry.write_text(text, encoding="utf-8")

            links = read_foundry_links(foundry)
            with self.assertRaises(AssertionError):
                self.assert_link(
                    links,
                    "Skillz",
                    "https://okhp3.github.io/skillz/",
                    target="_blank",
                    rel=("noopener", "noreferrer"),
                )


if __name__ == "__main__":
    unittest.main()

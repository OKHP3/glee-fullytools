"""Required public assets stay crawlable; named AI bot choices remain explicit."""

from pathlib import Path
import unittest
from urllib.robotparser import RobotFileParser


ROOT = Path(__file__).resolve().parents[2]
PUBLIC_PATHS = (
    "/",
    "/toolbox/01-discovered-careers/01a-resume-builder/",
    "/assets/css/theme.css",
    "/assets/js/app.js",
    "/assets/js/glee-site-enhancements.js",
    "/assets/img/favicons/android-chrome-192x192.png",
    "/assets/data/search-index.json",
    "/assets/data/sparkle.json",
    "/site.webmanifest",
)
INTERNAL_PATHS = (
    "/assets/audit/example.json",
    "/assets/docs/example.md",
    "/assets/templates/template--homepage.html",
)


class CrawlerPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = RobotFileParser()
        self.policy.parse((ROOT / "robots.txt").read_text().splitlines())

    def check_paths(self, agent, paths, allowed):
        for path in paths:
            with self.subTest(agent=agent, path=path):
                self.assertEqual(
                    self.policy.can_fetch(agent, "https://glee-fully.tools" + path),
                    allowed,
                )

    def test_general_crawlers_can_render_public_pages(self):
        for agent in ("Googlebot", "Bingbot", "ExampleCrawler"):
            self.check_paths(agent, PUBLIC_PATHS, True)

    def test_general_crawlers_skip_internal_artifacts(self):
        for agent in ("Googlebot", "Bingbot", "ExampleCrawler"):
            self.check_paths(agent, INTERNAL_PATHS, False)

    def test_gptbot_remains_disallowed(self):
        self.check_paths("GPTBot", PUBLIC_PATHS + INTERNAL_PATHS, False)

    def test_named_search_and_user_agents_keep_explicit_allow_policy(self):
        # Named groups do not inherit the wildcard group's internal exclusions.
        for agent in ("OAI-SearchBot", "ChatGPT-User"):
            self.check_paths(agent, PUBLIC_PATHS + INTERNAL_PATHS, True)

    def test_canonical_sitemap_is_declared(self):
        self.assertEqual(
            self.policy.site_maps(), ["https://glee-fully.tools/sitemap.xml"]
        )


if __name__ == "__main__":
    unittest.main()

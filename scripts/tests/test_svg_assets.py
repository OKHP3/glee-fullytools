"""Require source SVG images to parse, complementing actual browser decode QA."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]


class SvgAssets(unittest.TestCase):
    def test_all_public_svg_images_parse(self):
        paths = sorted((ROOT / "assets/img").rglob("*.svg"))
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                root = ET.parse(path).getroot()
                self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")


if __name__ == "__main__":
    unittest.main()

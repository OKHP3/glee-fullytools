"""Exercise page addition/removal, failure preservation, and index feedback."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class UniverseIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'universe').mkdir()
        (self.root / 'assets/data').mkdir(parents=True)
        self.page = self.root / 'universe/index.html'
        self.page.write_text('before<!-- AUTOGEN:UNIVERSE-MAP -->old<!-- /AUTOGEN:UNIVERSE-MAP -->after')
        self.index = self.root / 'assets/data/search-index.json'
        self.config = self.root / 'universe-map.config.json'
        self.config.write_text(json.dumps({'schema': 1, 'sites': [{'origin': 'https://glee-fully.tools', 'title': 'Glee', 'index': 'assets/data/search-index.json'}]}))
        self.sync = module('universe_sync', ROOT / 'scripts/sync-universe-map.py')

    def write_index(self, extra=True):
        rows = [{'url': '/', 'title': 'Glee', 'description': 'Home'}]
        if extra:
            rows.append({'url': '/new/', 'title': 'New page', 'description': '<script>unsafe</script>'})
        self.index.write_text(json.dumps({'pages': rows}))

    def test_add_remove_and_repeat_without_touching_authored_content(self):
        self.write_index()
        self.sync.sync(self.root)
        first = self.page.read_bytes()
        self.assertIn(b'https://glee-fully.tools/new/', first)
        self.assertNotIn(b'<script>unsafe</script>', first)
        self.sync.sync(self.root)
        self.assertEqual(first, self.page.read_bytes())
        self.write_index(False)
        self.sync.sync(self.root)
        self.assertNotIn(b'https://glee-fully.tools/new/', self.page.read_bytes())
        self.assertTrue(self.page.read_text().startswith('before'))
        self.assertTrue(self.page.read_text().endswith('after'))

    def test_check_is_read_only_and_detects_staleness(self):
        self.write_index()
        before = self.page.read_bytes()
        with self.assertRaises(ValueError):
            self.sync.sync(self.root, check=True)
        self.assertEqual(before, self.page.read_bytes())
        self.sync.sync(self.root)
        self.sync.sync(self.root, check=True)

    def test_bad_index_preserves_last_map(self):
        self.write_index()
        self.sync.sync(self.root)
        before = self.page.read_bytes()
        self.index.write_text('{"pages": []}')
        with self.assertRaises(ValueError):
            self.sync.sync(self.root)
        self.assertEqual(before, self.page.read_bytes())

    def test_missing_or_duplicate_markers_fail_before_writes(self):
        self.write_index()
        for value in ['no marker', self.page.read_text() * 2]:
            self.page.write_text(value)
            with self.assertRaises(ValueError):
                self.sync.sync(self.root)
            self.assertEqual(value, self.page.read_text())

    def test_generated_content_is_excluded_from_search(self):
        indexer = module('universe_indexer', ROOT / 'scripts/build-search-index.py')
        content = '<main>Authored<!-- AUTOGEN:UNIVERSE-MAP --><h2>Generated</h2><!-- /AUTOGEN:UNIVERSE-MAP -->Tail</main>'
        self.assertEqual(indexer.strip_universe_map(content), '<main>AuthoredTail</main>')

    def test_origin_with_trailing_slash_keeps_catalog_overlay_valid(self):
        self.write_index(False)
        config = json.loads(self.config.read_text())
        config['sites'][0]['origin'] += '/'
        self.config.write_text(json.dumps(config))
        (self.root / 'scripts').mkdir()
        (self.root / 'scripts/audit-tool-ette-promises.py').write_text(
            'def launch_urls(source): return []\ndef publication_state(source, urls): return "unavailable"\n')
        tool = self.root / 'toolbox/branch/tool/index.html'
        tool.parent.mkdir(parents=True)
        tool.write_text('<h1>Tool</h1>')
        index = json.loads(self.index.read_text())
        index['pages'].append({'url': '/toolbox/branch/tool/', 'title': 'Tool'})
        self.index.write_text(json.dumps(index))
        self.sync.sync(self.root)
        self.assertIn('Catalog: unavailable', self.page.read_text())


if __name__ == '__main__':
    unittest.main()

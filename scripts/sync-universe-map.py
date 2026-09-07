#!/usr/bin/env python3
"""Publish the local index as bounded maps using the installed portable skill."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import runpy
import tempfile

ROOT = Path(__file__).resolve().parents[1]
START = '<!-- AUTOGEN:UNIVERSE-MAP -->'
END = '<!-- /AUTOGEN:UNIVERSE-MAP -->'


def generate(root):
    config = json.loads((root / 'universe-map.config.json').read_text(encoding='utf-8'))
    for site in config['sites']:
        site['origin'] = site['origin'].rstrip('/')
        site['index'] = str((root / site['index']).resolve())
    # Reuse the existing publication contract; never infer GPT readiness from indexing.
    authority = root / 'scripts/audit-tool-ette-promises.py'
    if authority.exists():
        audit = runpy.run_path(str(authority))
        overlays = config.setdefault('overlay', {}).setdefault('pages', {})
        index = json.loads(Path(config['sites'][0]['index']).read_text(encoding='utf-8'))
        for entry in index['pages']:
            path = entry['url']
            if path.startswith('/toolbox/') and len(path.strip('/').split('/')) == 3:
                source = (root / path.strip('/') / 'index.html').read_text(encoding='utf-8')
                state = audit['publication_state'](source, audit['launch_urls'](source))
                overlays.setdefault(config['sites'][0]['origin'] + path, {})['status'] = 'Catalog: ' + state
    script = ROOT / '.agents/skills/okhp3-universe-map/scripts/build-universe-map.py'
    spec = importlib.util.spec_from_file_location('universe_generator', script)
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    with tempfile.TemporaryDirectory(prefix='glee-universe-') as temp:
        config_path = Path(temp) / 'config.json'
        config_path.write_text(json.dumps(config), encoding='utf-8')
        outputs = generator.build(config_path)
    report = json.loads(outputs['universe-map.json'])
    # Do not publish machine-specific absolute paths in provenance.
    report['config_sha256'] = hashlib.sha256((root / 'universe-map.config.json').read_bytes().replace(b'\r\n', b'\n')).hexdigest()
    report['status_authority'] = 'scripts/audit-tool-ette-promises.py'
    fragment = outputs['universe-map.html-fragment']
    fragment = fragment.replace('<section aria-label="Universe map">', '<section id="universe-generated-map" class="universe-map" aria-label="Glee-fully page map">')
    fragment = fragment.replace('<pre class="mermaid">', '<div class="mermaid-scroll-wrap" tabindex="0" role="region" aria-label="Scrollable page diagram"><pre class="mermaid" hidden>')
    fragment = fragment.replace('</pre><ul>', '</pre></div><ul>')
    # Strict Mermaid renders graphics; the adjacent ordinary links remain usable
    # with keyboards, assistive technology, and JavaScript disabled.
    return fragment, json.dumps(report, ensure_ascii=False, indent=2) + '\n'


def sync(root=ROOT, check=False):
    page = root / 'universe/index.html'
    original = page.read_text(encoding='utf-8')
    if original.count(START) != 1 or original.count(END) != 1 or original.index(START) > original.index(END):
        raise ValueError('Universe page requires exactly one ordered AUTOGEN:UNIVERSE-MAP block')
    fragment, report = generate(root)
    rendered = re.sub(re.escape(START) + r'.*?' + re.escape(END), lambda _: fragment.rstrip(), original, flags=re.S)
    files = {page: rendered, root / 'assets/data/universe-map.json': report}
    stale = [path for path, value in files.items() if not path.exists() or path.read_text(encoding='utf-8') != value]
    if check and stale:
        raise ValueError('Stale universe output: ' + ', '.join(str(p.relative_to(root)) for p in stale))
    if not check:
        for path in stale:
            path.write_text(files[path], encoding='utf-8', newline='\n')
    print('Universe map current' if check else f'Universe map updated: {len(stale)} files')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    try:
        sync(check=args.check)
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f'ERROR: {error}\n')

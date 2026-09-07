"""Read source/runtime/upstream provenance; write only the requested evidence JSON."""
import argparse
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import urllib.request

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]

def command(*arguments):
    result = subprocess.run(arguments, cwd=root, capture_output=True, text=True,
                            encoding='utf-8', errors='replace', timeout=45)
    return {'command': list(arguments), 'exit_code': result.returncode,
            'stdout': result.stdout.strip(), 'stderr': result.stderr.strip()}

report = {'captured_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'python': {'executable': sys.executable, 'version': sys.version,
                     'bs4_import_available': importlib.util.find_spec('bs4') is not None,
                     'playwright_import_available': importlib.util.find_spec('playwright') is not None},
          'head': command('git', 'rev-parse', 'HEAD'), 'sources': {}, 'actions': {}, 'pypi': {}}
for name in ['package.json', 'package-lock.json', '.replit', '.github/dependabot.yml',
             'scripts/check-workflow-actions.py']:
    data = (root / name).read_bytes()
    report['sources'][name] = {'sha256': hashlib.sha256(data).hexdigest()}
    if name.endswith('.json'):
        report['sources'][name]['content'] = json.loads(data)
    else:
        report['sources'][name]['content'] = data.decode('utf-8')
for action, version in [('checkout', 7), ('setup-python', 7), ('upload-artifact', 7),
                        ('download-artifact', 8), ('configure-pages', 6),
                        ('upload-pages-artifact', 5), ('deploy-pages', 5), ('github-script', 9)]:
    result = command('gh', 'api', f'repos/actions/{action}/git/ref/tags/v{version}')
    if result['exit_code'] == 0:
        result['response'] = json.loads(result.pop('stdout'))
        obj = result['response']['object']
        if obj['type'] == 'tag':
            result['dereferenced'] = command('gh', 'api', f'repos/actions/{action}/git/tags/{obj["sha"]}')
    report['actions'][f'actions/{action}@v{version}'] = result
for name, version in [('playwright', '1.62.0'), ('beautifulsoup4', '4.15.0')]:
    url = f'https://pypi.org/pypi/{name}/{version}/json'
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            payload = json.load(response)
        report['pypi'][name] = {'url': url, 'version': payload['info']['version'],
                              'requires_python': payload['info']['requires_python'],
                              'files': [{key: item[key] for key in ['filename', 'upload_time_iso_8601', 'digests', 'url']}
                                        for item in payload['urls']]}
    except Exception as error:
        report['pypi'][name] = {'url': url, 'status': 'NOT RUN', 'error': str(error)}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(args.output)
print(json.dumps({'actions_failed': [key for key, value in report['actions'].items() if value['exit_code']],
                  'pypi_failed': [key for key, value in report['pypi'].items() if value.get('status') == 'NOT RUN']}))
if (any(value['exit_code'] for value in report['actions'].values()) or
        any(value.get('status') == 'NOT RUN' for value in report['pypi'].values())):
    raise SystemExit(1)

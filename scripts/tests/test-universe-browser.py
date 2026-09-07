"""Browser acceptance for generated maps; uses the release's Playwright runtime."""
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
BASE = os.environ.get('UNIVERSE_BASE_URL', 'http://127.0.0.1:5000')


def local_http_fixture(page):
    # WebKit upgrades loopback HTTP assets under the production HTTPS policy.
    # Remove only this directive in the local response, never production files.
    if urlsplit(BASE).scheme == 'http' and urlsplit(BASE).hostname in {'127.0.0.1', 'localhost'}:
        def serve(route):
            response = route.fetch()
            route.fulfill(response=response, body=response.text().replace('upgrade-insecure-requests', ''))
        page.route(BASE + '/universe/', serve)


def main():
    expected = json.loads((ROOT / 'assets/data/universe-map.json').read_text(encoding='utf-8'))
    urls = {urlsplit(node['url']).path for node in expected['nodes'] if node['url']}
    evidence = []
    with sync_playwright() as runtime:
        for name in ('chromium', 'firefox', 'webkit'):
            browser = getattr(runtime, name).launch()
            for width, theme in ((390, 'light'), (1440, 'dark')):
                print(f'Checking {name}: {width}px / {theme}', flush=True)
                page = browser.new_page(viewport={'width': width, 'height': 900}, color_scheme=theme)
                local_http_fixture(page)
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(BASE + '/universe/')
                groups = page.locator('.universe-map details')
                for group in groups.all():
                    group.locator('summary').click()
                    group.locator('pre[data-rendered="true"] svg').wait_for()
                    assert group.locator('svg a[tabindex="0"]').count() == group.locator('li a').count()
                actual = {urlsplit(link.get_attribute('href')).path for link in page.locator('.universe-map li a').all()}
                assert urls == actual
                assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
                link = page.locator('.universe-map svg a').first
                link.focus()
                assert link.evaluate('(node) => document.activeElement === node')
                assert not errors, errors
                evidence.append({'engine': name, 'width': width, 'theme': theme, 'pages': len(actual), 'diagrams': groups.count(), 'errors': errors})
                page.close()
            page = browser.new_page(java_script_enabled=False)
            local_http_fixture(page)
            page.goto(BASE + '/universe/')
            page.locator('.universe-map summary').first.click()
            assert page.locator('.universe-map li a').first.is_visible()
            assert page.locator('.universe-map pre').first.is_hidden()
            page.close()
            page = browser.new_page()
            local_http_fixture(page)
            page.route('**/assets/vendor/mermaid/**', lambda route: route.abort())
            page.goto(BASE + '/universe/')
            page.locator('.universe-map summary').first.click()
            assert page.locator('.universe-map li a').first.is_visible()
            page.close()
            browser.close()
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()

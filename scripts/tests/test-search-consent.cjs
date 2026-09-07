// Run with an existing Playwright installation available through NODE_PATH.
const assert = require('node:assert/strict');
const { readFileSync, mkdirSync } = require('node:fs');
const { resolve, extname } = require('node:path');
const { createServer } = require('node:http');
const { spawnSync } = require('node:child_process');
const { chromium } = require('playwright');
const root = resolve(__dirname, '../..');
const python = process.env.SEARCH_TEST_PYTHON || 'python3';
const built = spawnSync(python, ['-X', 'utf8', '-c',
  'import runpy,json; b=runpy.run_path("scripts/build-search-index.py"); print(json.dumps({"pages":[e for p in b["collect_html_files"]() if (e:=b["build_entry"](p))]}))'],
  { cwd: root, encoding: 'utf8' });
if (built.status !== 0) throw new Error(built.stderr);
const index = JSON.parse(built.stdout);
const mime = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.css': 'text/css', '.svg': 'image/svg+xml' };
const server = createServer((request, response) => {
  const url = new URL(request.url, 'http://localhost');
  if (url.pathname === '/assets/data/search-index.json') {
    response.writeHead(200, {'content-type': 'application/json'}); response.end(JSON.stringify(index)); return;
  }
  let pathname = decodeURIComponent(url.pathname);
  if (pathname.endsWith('/')) pathname += 'index.html';
  const path = resolve(root, '.' + pathname);
  if (!path.startsWith(root + require('node:path').sep)) { response.writeHead(403); response.end(); return; }
  try { const body = readFileSync(path); response.writeHead(200, {'content-type': mime[extname(path)] || 'application/octet-stream'}); response.end(body); }
  catch { response.writeHead(404); response.end(); }
});

(async () => {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const origin = 'http://127.0.0.1:' + server.address().port;
  const browser = await chromium.launch({ headless: true });
  let failed = 0;
  const run = async (name, fn, setup, contextOptions) => {
    const context = await browser.newContext({ serviceWorkers: 'block', ...contextOptions });
    const analyticsRequests = [];
    await context.route('**/*', route => {
      const url = route.request().url();
      if (url.startsWith(origin)) return route.continue();
      if (/googletagmanager|google-analytics/.test(url)) analyticsRequests.push(url);
      return route.fulfill({status: 200, body: ''});
    });
    if (setup) await context.addInitScript(setup);
    const page = await context.newPage();
    page.setDefaultTimeout(6000);
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    try { await fn(page, context, analyticsRequests); assert.deepEqual(errors, []); console.log('PASS ' + name); }
    catch (error) { failed++; console.error('FAIL ' + name + ': ' + error.message); }
    finally { await context.close(); }
  };
  try {
    await run('automatic service-worker registration after a late adapter import', async (page, context) => {
      let releaseAdapter;
      let adapterIntercepted = false;
      const gate = new Promise(resolve => { releaseAdapter = resolve; });
      await context.route(/\/assets\/js\/glee-site-enhancements\.js(?:\?|$)/, async route => {
        adapterIntercepted = true;
        await gate;
        await route.continue();
      });
      try {
        await page.goto(origin + '/', { waitUntil: 'domcontentloaded' });
        await page.waitForFunction(() => document.readyState === 'complete');
      } finally { releaseAdapter(); }
      assert.equal(adapterIntercepted, true, 'late adapter route intercepted the requested URL');
      await page.waitForFunction(() => window.gleeAnalytics);
      await page.waitForFunction(() => navigator.serviceWorker.controller !== null, null, { timeout: 15000 });
      assert.equal(await page.evaluate(async () => Boolean((await navigator.serviceWorker.getRegistration('/'))?.active)), true);
      assert.equal(await page.evaluate(() => navigator.serviceWorker.controller.scriptURL), origin + '/sw.js');
    }, undefined, { serviceWorkers: 'allow' });
    await run('Glee modal identity, suggestions, publication state, focus return', async page => {
      await page.goto(origin + '/');
      const trigger = page.locator('.okh-search-trigger');
      await trigger.click();
      assert.equal(await page.locator('.okh-search-overlay').getAttribute('aria-label'), 'Search Glee‑fully Tools');
      const suggestions = await page.locator('.okh-search-hint-list button').allTextContents();
      assert.deepEqual(suggestions, ['resume', 'budget', 'scheduling', 'travel', 'journal']);
      for (const term of suggestions) {
        await page.locator('.okh-search-input').fill(term);
        assert.ok(await page.locator('.okh-search-results .okh-search-result').count() > 0, term);
      }
      await page.locator('.okh-search-input').fill('scheduling');
      await page.waitForFunction(() => document.querySelector('.okh-search-results').textContent.includes('Unavailable'));
      assert.match(await page.locator('.okh-search-results').innerText(), /Scheduling Wizard/);
      assert.match(await page.locator('.okh-search-footer a').getAttribute('href'), /q=scheduling/);
      await page.keyboard.press('Escape');
      assert.equal(await trigger.evaluate(el => el === document.activeElement), true);
    });
    await run('inline query, category, history, reload and keyboard', async page => {
      await page.goto(origin + '/search/?q=resume');
      const input = page.locator('[data-glee-search-inline-input]');
      await page.waitForFunction(() => document.querySelector('[data-glee-search-inline-results] a'));
      await input.fill('budget');
      await page.waitForFunction(() => new URL(location.href).searchParams.get('q') === 'budget');
      const budgetFirst = await page.locator('[data-glee-search-inline-results] a').first().getAttribute('href');
      const chip = page.locator('[data-glee-search-inline-categories] button').filter({hasText: /^Tool-ette/});
      await chip.click();
      assert.equal(new URL(page.url()).searchParams.get('cat'), 'Tool-ette');
      await page.goBack();
      assert.equal(await input.inputValue(), 'budget');
      assert.equal(new URL(page.url()).searchParams.get('cat'), null);
      await page.goBack();
      assert.equal(await input.inputValue(), 'resume');
      await page.goForward();
      await page.reload();
      await page.waitForFunction(() => document.querySelector('[data-glee-search-inline-results] a'));
      assert.equal(await input.inputValue(), 'budget');
      assert.equal(await page.locator('[data-glee-search-inline-results] a').first().getAttribute('href'), budgetFirst);
      await input.press('ArrowDown');
      const selected = await page.locator('[data-glee-search-inline-results] a[data-active="true"]').getAttribute('href');
      await input.press('Enter');
      await page.waitForURL(origin + selected);
    });
    await run('inline and modal share ranking and retry failed index', async (page, context) => {
      let failedOnce = false;
      await context.route('**/assets/data/search-index.json', route => {
        if (!failedOnce) { failedOnce = true; return route.fulfill({status: 503, body: 'unavailable'}); }
        return route.continue();
      });
      await page.goto(origin + '/search/?q=resume');
      await page.getByRole('button', {name: 'Retry search index', exact: true}).click();
      await page.waitForFunction(() => document.querySelector('[data-glee-search-inline-results] a'));
      const inline = await page.locator('[data-glee-search-inline-results] a').first().getAttribute('href');
      await page.locator('.okh-search-trigger').click();
      await page.locator('.okh-search-input').fill('resume');
      await page.waitForFunction(() => document.querySelector('.okh-search-results .okh-search-result'));
      assert.equal(await page.locator('.okh-search-results .okh-search-result').first().getAttribute('href'), inline);
    });
    await run('deep function discovery and responsive search rendering', async page => {
      await page.goto(origin + '/search/?q=seniority');
      await page.waitForFunction(() => document.querySelector('[data-glee-search-inline-results] a'));
      assert.ok((await page.locator('[data-glee-search-inline-results] a').evaluateAll(links => links.map(a => a.getAttribute('href'))))
        .includes('/toolbox/01-discovered-careers/01a-resume-builder/'));
      for (const width of [1280, 375]) {
        await page.setViewportSize({ width, height: 900 });
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
        if (process.env.SEARCH_TEST_SCREENSHOTS) {
          mkdirSync(process.env.SEARCH_TEST_SCREENSHOTS, { recursive: true });
          await page.screenshot({path: resolve(process.env.SEARCH_TEST_SCREENSHOTS, 'search-' + width + '.png')});
        }
      }
    });
    await run('shared sibling search default and entries schema still work', async (page, context) => {
      await context.route('**/sibling-test/**', route => route.fulfill({ contentType: 'text/html', body:
        '<html lang="en"><head><title>Sibling search fixture</title><script defer src="/assets/js/app.js"></script></head>' +
        '<body><header class="site-header"></header><main><input id="search-page-input"><div id="search-stats"></div>' +
        '<div id="search-categories"></div><div id="search-results"></div></main></body></html>' }));
      await context.route('**/assets/data/search-index.json', route => route.fulfill({ json: { entries: [
        {title: 'Mermaid overview', category: 'Article', url: '/mermaid/', body: 'diagram guidance'}
      ]} }));
      await page.goto(origin + '/sibling-test/?q=mermaid');
      await page.waitForFunction(() => document.querySelector('#search-results a'));
      assert.match(await page.locator('#search-results').innerText(), /Mermaid overview/);
      await page.locator('.okh-search-trigger').click();
      assert.equal(await page.locator('.okh-search-overlay').getAttribute('aria-label'), 'Search OverKill Hill');
    });
    for (const [brand, locale, expectedIndex, fallback] of [
      ['glee-main', 'en', 'search-index.json', false],
      ['glee-main', 'en-US', 'search-index.json', false],
      ['glee-main', 'en-GB', 'search-index.json', false],
      ['glee-main', 'fr-FR', 'search-index.fr.json', false],
      ['glee-main', 'fr-CA', 'search-index.fr.json', false],
      ['glee-main', 'es-ES', 'search-index.json', true],
      ['glee-main', 'es-MX', 'search-index.json', true],
      ['', 'fr-FR', 'search-index.fr.json', false],
      ['askjamie-main', 'es-MX', 'search-index.json', true],
    ]) {
      await run('catalog locale boundary ' + brand + ' ' + locale, async (page, context) => {
        const requestedIndexes = [];
        await context.route('**/locale-fixture/**', route => route.fulfill({ contentType: 'text/html', body:
          '<html lang="' + locale + '"><head><title>Locale fixture</title><script defer src="/assets/js/app.js"></script></head>' +
          '<body class="' + brand + '"><header class="site-header"></header><main>' +
          '<input id="search-page-input"><div id="search-stats"></div><div id="search-categories"></div>' +
          '<div id="search-results"></div></main></body></html>' }));
        await context.route(/\/assets\/data\/search-index[^/]*\.json(?:\?|$)/, route => {
          requestedIndexes.push(new URL(route.request().url()).pathname.split('/').pop());
          return route.fulfill({ json: { entries: [
            {title: 'Resume fixture', category: 'Guide', url: '/resume/', body: 'resume guidance'}
          ]} });
        });
        await page.goto(origin + '/locale-fixture/?q=resume');
        await page.waitForFunction(() => document.querySelector('#search-results a'));
        assert.deepEqual(requestedIndexes, [expectedIndex], 'only the declared brand catalog is requested');
        assert.equal((await page.locator('#search-stats').innerText()).includes('Search English content.'), fallback,
          'undeclared exact locale has an explicit English fallback notice');
      });
    }
    for (const initial of [null, 'granted', 'denied']) {
      await run('consent hydration ' + initial, async (page, context, requests) => {
        await page.goto(origin + '/legal/');
        await page.waitForFunction(() => window.gleeAnalytics);
        const enabled = initial === 'granted';
        assert.match(await page.locator('[data-analytics-status]').innerText(), enabled ? /is on/ : /is off/);
        assert.equal(await page.evaluate(() => window['ga-disable-G-89W66VMGPB']), !enabled);
        assert.equal(requests.length > 0, enabled);
        await page.reload();
        await page.waitForFunction(() => window.gleeAnalytics);
        assert.match(await page.locator('[data-analytics-status]').innerText(), enabled ? /is on/ : /is off/);
      }, initial ? 'localStorage.setItem("glee-analytics-consent", ' + JSON.stringify(initial) + ');' : undefined);
    }
    await run('enable disable re-enable and reload use the saved choice', async page => {
      await page.goto(origin + '/legal/');
      await page.waitForFunction(() => window.gleeAnalytics);
      for (const choice of ['granted', 'denied', 'granted', 'denied']) {
        await page.locator('[data-analytics-action="' + choice + '"]').click();
        assert.equal(await page.evaluate(() => window.gleeAnalytics.status()), choice);
        assert.match(await page.locator('[data-analytics-status]').innerText(), choice === 'granted' ? /is on/ : /is off/);
        assert.equal(await page.evaluate(() => window['ga-disable-G-89W66VMGPB']), choice !== 'granted');
      }
      assert.equal(await page.locator('script[data-glee-analytics]').count(), 1);
      await page.reload();
      await page.waitForFunction(() => window.gleeAnalytics);
      assert.match(await page.locator('[data-analytics-status]').innerText(), /is off/);
      assert.equal(await page.locator('script[data-glee-analytics]').count(), 0);
    });
    await run('storage exceptions remain truthful and controls stay usable', async page => {
      await page.goto(origin + '/legal/');
      await page.waitForFunction(() => window.gleeAnalytics);
      await page.locator('[data-analytics-action="granted"]').click();
      assert.match(await page.locator('[data-analytics-status]').innerText(), /is on for this page.*could not be saved/i);
      assert.equal(await page.evaluate(() => window.gleeAnalytics.status()), 'granted');
      await page.reload();
      await page.waitForFunction(() => window.gleeAnalytics);
      assert.match(await page.locator('[data-analytics-status]').innerText(), /is off/);
    }, () => {
      Storage.prototype.getItem = () => { throw new Error('Storage unavailable'); };
      Storage.prototype.setItem = () => { throw new Error('Storage unavailable'); };
    });
  } finally { await browser.close(); await new Promise(resolve => server.close(resolve)); }
  process.exitCode = failed ? 1 : 0;
})();

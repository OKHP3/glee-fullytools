const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { createHash } = require('node:crypto');
const vm = require('node:vm');
const { chromium } = require('playwright');

const root = path.resolve(__dirname, '../..');
const app = fs.readFileSync(path.join(root, 'assets/js/app.js'), 'utf8');
const selection = app.slice(app.indexOf('  const SEARCH_INDEXES'), app.indexOf('  const usesEnglishFallback'));

test('search metadata is a hash only and preserves locale routing', () => {
  const selected = (lang, content) => vm.runInNewContext(selection + '\nINDEX_URL;', {
    document: { documentElement: { lang }, querySelector: () => content === null ? null : { content } },
  });
  assert.equal(selected('en-US', '1234abcd'), '/assets/data/search-index.json?v=1234abcd');
  assert.equal(selected('de-DE', '1234abcd'), '/assets/data/search-index.json?v=1234abcd');
  assert.equal(selected('es-MX', '1234abcd'), '/assets/data/search-index.json?v=1234abcd');
  assert.equal(selected('fr-FR', '1234abcd'), '/assets/data/search-index.fr.json');
  for (const invalid of [null, '', 'https://foreign.example/index.json', '1234ABCD', '1234abcd&x=1']) {
    assert.equal(selected('en-US', invalid), '/assets/data/search-index.json');
  }
});

test('returning visitors bypass an old unversioned index and search offline after worker activation',
  { timeout: 90000 }, async () => {
    const payload = label => JSON.stringify({ pages: [{
      title: `Cache probe ${label}`, url: '/foundry/', description: 'Cache probe fixture',
      body: 'Cache probe fixture', headings: [], category: 'Page',
    }] });
    const oldIndex = payload('old');
    const newIndex = payload('new');
    const version = createHash('sha256').update(newIndex).digest('hex').slice(0, 8);
    const key = `/assets/data/search-index.json?v=${version}`;
    const worker = fs.readFileSync(path.join(root, 'sw.js'), 'utf8');
    const oldCache = 'glee-fully-shell-v101';
    const newCache = 'glee-fully-shell-v102';
    const requests = [];
    let currentIndex = false;
    let currentWorker = false;
    const server = http.createServer((request, response) => {
      const url = new URL(request.url, 'http://localhost');
      requests.push(url.pathname + url.search);
      response.setHeader('Cache-Control', 'no-store');
      if (url.pathname === '/assets/data/search-index.json') {
        response.setHeader('Content-Type', 'application/json');
        response.end(currentIndex ? newIndex : oldIndex);
        return;
      }
      if (url.pathname === '/sw.js') {
        response.setHeader('Content-Type', 'text/javascript');
        // Exercise the real handler with a prior unversioned cache key.
        // Only the test server changes these two fixture identities.
        response.end(worker.replace(/glee-fully-shell-v\d+/, currentWorker ? newCache : oldCache)
          .replace(/\/assets\/data\/search-index\.json\?v=[a-f0-9]{8}/g,
            currentWorker ? key : '/assets/data/search-index.json'));
        return;
      }
      let file = path.resolve(root, '.' + decodeURIComponent(url.pathname));
      if (file !== root && !file.startsWith(root + path.sep)) { response.writeHead(403).end(); return; }
      try {
        if (fs.statSync(file).isDirectory()) file = path.join(file, 'index.html');
        const types = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript',
          '.json': 'application/json', '.css': 'text/css', '.svg': 'image/svg+xml',
          '.png': 'image/png', '.webp': 'image/webp', '.woff2': 'font/woff2' };
        response.setHeader('Content-Type', types[path.extname(file)] || 'application/octet-stream');
        let bytes = fs.readFileSync(file);
        if (file.endsWith('.html')) {
          bytes = bytes.toString().replace(/<meta name="search-index-version" content="[^"]*">/,
            currentIndex && process.env.SEARCH_CACHE_FAULT !== 'metadata'
              ? `<meta name="search-index-version" content="${version}">` : '');
        }
        response.end(bytes);
      } catch { response.writeHead(404).end(); }
    });
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const base = `http://127.0.0.1:${server.address().port}`;
    let browser;
    const stopServer = () => new Promise(resolve => {
      if (!server.listening) { resolve(); return; }
      server.closeAllConnections();
      server.close(resolve);
    });
    try {
      browser = await chromium.launch();
      const context = await browser.newContext();
      await context.route('**/*', route => route.request().url().startsWith(base + '/')
        ? route.continue() : route.abort());
      let page = await context.newPage();
      page.setDefaultTimeout(15000);
      const results = () => page.locator('[data-glee-search-inline-results]');
      await page.goto(base + '/search/?q=probe');
      await results().getByText('Cache probe old', { exact: true }).waitFor();
      await page.waitForFunction(() => !!navigator.serviceWorker.controller);
      await page.reload();
      await results().getByText('Cache probe old', { exact: true }).waitFor();
      assert.equal(await page.evaluate(async cache => {
        const response = await (await caches.open(cache)).match('/assets/data/search-index.json');
        return (await response.json()).pages[0].title;
      }, oldCache), 'Cache probe old');

      currentIndex = true;
      await page.reload();
      await results().getByText('Cache probe new', { exact: true }).waitFor();
      assert.ok(requests.includes(key), 'current metadata selects the new network cache key');
      assert.equal(await page.evaluate(async cache => (await caches.keys()).includes(cache), oldCache), true,
        'the old worker remains installed while the new index is fetched');

      currentWorker = true;
      await page.evaluate(async () => (await navigator.serviceWorker.getRegistration()).update());
      await page.waitForFunction(async () => !!(await navigator.serviceWorker.getRegistration()).waiting);
      await page.close();
      page = await context.newPage();
      page.setDefaultTimeout(15000);
      await page.goto(base + '/search/?q=probe');
      await page.waitForFunction(async old => !(await caches.keys()).includes(old), oldCache);
      await page.waitForFunction(() => !!navigator.serviceWorker.controller);
      assert.equal(await page.evaluate(async ({ cache, key }) => {
        const response = await (await caches.open(cache)).match(key);
        return (await response.json()).pages[0].title;
      }, { cache: newCache, key }), 'Cache probe new');
      await context.setOffline(true);
      // Stop the test server too: browser offline emulation alone can leave
      // localhost reachable to service-worker fetches in some environments.
      await stopServer();
      await page.reload();
      await results().getByText('Cache probe new', { exact: true }).waitFor();
    } finally {
      await browser?.close();
      await stopServer();
    }
  });

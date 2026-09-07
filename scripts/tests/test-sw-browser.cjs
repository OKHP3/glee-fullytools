// Real Chromium worker journeys. Uses an existing Playwright installation and
// browser; run with NODE_PATH pointing to that installation when needed.
// Optional PUBLIC_SITE_DIR points at the staged artifact instead of the checkout.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');
const root = path.resolve(process.env.PUBLIC_SITE_DIR || path.join(__dirname, '../..'));
const types = { '.html': 'text/html', '.js': 'application/javascript', '.mjs': 'application/javascript',
  '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml',
  '.png': 'image/png', '.webp': 'image/webp', '.ico': 'image/x-icon', '.webmanifest': 'application/manifest+json' };
const server = http.createServer(async (request, response) => {
  const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
  let file = path.resolve(root, '.' + pathname);
  if (file !== root && !file.startsWith(root + path.sep)) { response.writeHead(403).end(); return; }
  try {
    if ((await fs.stat(file)).isDirectory()) file = path.join(file, 'index.html');
    const data = await fs.readFile(file);
    response.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream',
      'Cache-Control': 'no-store' }).end(data);
  } catch { response.writeHead(404, { 'Content-Type': 'text/plain' }).end('Not found'); }
});

(async () => {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  let browser;
  try {
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext();
    await context.route('**/*', route => route.request().url().startsWith(base) ? route.continue() : route.abort());
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    context.on('requestfailed', request => errors.push(`${request.url()}: ${request.failure()?.errorText}`));
    await page.goto(base, { waitUntil: 'load' });
    // This runner isolates the worker's lifecycle from the adapter's load timing.
    await page.evaluate(() => navigator.serviceWorker.register('/sw.js', { scope: '/' }));
    await page.waitForFunction(async () => !!(await navigator.serviceWorker.getRegistration())?.active,
      null, { timeout: 15000 }).catch(error => {
        throw new Error(`Worker did not become active: ${error.message}; page errors: ${errors.join('; ')}`);
      });
    await page.waitForFunction(() => !!navigator.serviceWorker.controller, null, { timeout: 15000 }).catch(async error => {
      const state = await page.evaluate(async () => {
        const registration = await navigator.serviceWorker.getRegistration();
        return { readyState: document.readyState, url: location.href, active: registration?.active?.state,
          installing: registration?.installing?.state, waiting: registration?.waiting?.state,
          scope: registration?.scope, caches: await caches.keys() };
      });
      throw new Error(`Worker did not claim page: ${error.message}; state: ${JSON.stringify(state)}; page errors: ${errors.join('; ')}`);
    });
    const worker = context.serviceWorkers()[0];
    assert.ok(worker, 'installed worker exists');

    // Storage failures occur inside the actual service-worker global.
    await worker.evaluate(() => {
      self.originalCachePut = Cache.prototype.put;
      Cache.prototype.put = () => Promise.reject(new Error('QuotaExceededError'));
    });
    await page.goto(base + '/toolbox/01-discovered-careers/', { waitUntil: 'domcontentloaded' });
    assert.match(await page.locator('h1').innerText(), /Careers/i);
    await worker.evaluate(() => {
      Cache.prototype.put = self.originalCachePut;
      self.originalCacheOpen = caches.open.bind(caches);
      caches.open = () => Promise.reject(new Error('Storage unavailable'));
    });
    await page.goto(base + '/about/', { waitUntil: 'domcontentloaded' });
    assert.doesNotMatch(await page.title(), /offline/i);
    await worker.evaluate(() => { caches.open = self.originalCacheOpen; });

    // Many query URLs retain one shell; the page URL still carries the query.
    for (let i = 0; i < 12; i++) {
      await page.goto(base + `/search/?q=resume&case=${i}`, { waitUntil: 'domcontentloaded' });
    }
    const keys = await worker.evaluate(async () => {
      const name = (await caches.keys()).find(name => name.startsWith('glee-fully-shell-'));
      return (await (await caches.open(name)).keys()).map(request => request.url);
    });
    assert.equal(keys.filter(url => new URL(url).pathname === '/search/').length, 1);
    assert.ok(keys.some(url => new URL(url).pathname === '/assets/js/glee-site-enhancements.js'),
      'Glee adapter is included in the installed cache');

    // Clear ordinary HTTP cache so it cannot conceal a missing shell dependency.
    const cdp = await context.newCDPSession(page);
    await cdp.send('Network.clearBrowserCache');
    await context.setOffline(true);
    const adapter = page.waitForResponse(response =>
      new URL(response.url()).pathname.endsWith('/assets/js/glee-site-enhancements.js'));
    await page.goto(base + '/search/?q=resume&case=offline', { waitUntil: 'load' });
    const adapterResponse = await adapter;
    assert.equal(adapterResponse.status(), 200);
    assert.equal(adapterResponse.fromServiceWorker(), true);
    assert.ok(page.url().endsWith('case=offline'));
    await page.waitForFunction(() => document.querySelector('[data-glee-search-inline-results] a'));
    await page.goto(base + '/toolbox/01-discovered-careers/01a-resume-builder/', { waitUntil: 'load' });
    assert.match(await page.title(), /offline/i, 'unvisited page uses honest offline fallback');
    await context.setOffline(false);
    await page.goto(base + '/toolbox/01-discovered-careers/01a-resume-builder/', { waitUntil: 'domcontentloaded' });
    assert.match(await page.locator('h1').innerText(), /Resume/i);
    console.log(JSON.stringify({ status: 'passed', browser: 'Chromium', publicSiteDirectory: root,
      checks: ['quota failure keeps online page', 'unavailable storage keeps online page',
        'query shell deduplication', 'cold offline adapter from service worker',
        'offline query and search results', 'uncached offline fallback', 'reconnect navigation'] }, null, 2));
  } finally {
    if (browser) await browser.close();
    server.closeAllConnections();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });

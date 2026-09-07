/* Diagnostic fixture for WebKit's local HTTP handling under the shipped CSP. */
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { chromium, webkit } = require('playwright');

const root = path.resolve(__dirname, '../..');
const mime = {'.css': 'text/css', '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.webp': 'image/webp'};
const server = http.createServer((request, response) => {
  let pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
  if (pathname.endsWith('/')) pathname += 'index.html';
  const file = path.resolve(root, '.' + pathname);
  if (!file.startsWith(root + path.sep)) { response.writeHead(403); response.end(); return; }
  try {
    response.writeHead(200, {'content-type': mime[path.extname(file)] || 'text/plain'});
    response.end(fs.readFileSync(file));
  } catch { response.writeHead(404); response.end(); }
});

(async () => {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  const browser = await webkit.launch({headless: true});
  const context = await browser.newContext({serviceWorkers: 'block'});
  const stripLocalCsp = process.env.STRIP_LOCAL_CSP === '1';
  if (stripLocalCsp) {
    await context.route('**/*', async route => {
      const requestUrl = new URL(route.request().url());
      if (route.request().isNavigationRequest() && requestUrl.origin === base) {
        const response = await route.fetch();
        if ((response.headers()['content-type'] || '').includes('text/html')) {
          await route.fulfill({response, body: (await response.text()).replace('; upgrade-insecure-requests', '')});
        } else {
          await route.fulfill({response});
        }
      } else {
        await route.continue();
      }
    });
  }
  const requests = [];
  context.on('request', request => requests.push({url: request.url(), failure: null}));
  context.on('requestfailed', request => {
    const item = requests.find(entry => entry.url === request.url() && !entry.failure);
    if (item) item.failure = request.failure();
  });
  const page = await context.newPage();
  const pageErrors = [];
  const consoleErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()); });
  let error = null;
  try { await page.goto(base + '/', {waitUntil: 'load', timeout: 5000}); }
  catch (caught) { error = caught.message; }
  await page.waitForTimeout(1000);
  const result = {base, stripLocalCsp, error, analytics: await page.evaluate(() => typeof window.gleeAnalytics), pageErrors, consoleErrors, requests};
  const output = JSON.stringify(result, null, 2) + '\n';
  if (process.env.DIAGNOSTIC_OUTPUT) fs.writeFileSync(process.env.DIAGNOSTIC_OUTPUT, output);
  console.log(output);
  await context.close(); await browser.close(); await new Promise(resolve => server.close(resolve));
})().catch(error => { console.error(error); process.exitCode = 1; });

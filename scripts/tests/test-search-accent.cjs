/* Regression coverage for the accent-folding search contract.
   Run with NODE_PATH pointing to the installed Playwright package. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { chromium } = require('playwright');

const root = path.resolve(__dirname, '../..');
const mime = {
  '.css': 'text/css', '.html': 'text/html', '.js': 'text/javascript',
  '.json': 'application/json', '.svg': 'image/svg+xml',
};

function serve(request, response) {
  const url = new URL(request.url, 'http://localhost');
  let pathname = decodeURIComponent(url.pathname);
  if (pathname === '/assets/data/search-index.json') {
    pathname = '/assets/data/search-index.json';
  } else if (pathname.endsWith('/')) {
    pathname += 'index.html';
  }
  const file = path.resolve(root, '.' + pathname);
  if (!file.startsWith(root + path.sep)) {
    response.writeHead(403); response.end(); return;
  }
  try {
    response.writeHead(200, {'content-type': mime[path.extname(file)] || 'application/octet-stream'});
    response.end(fs.readFileSync(file));
  } catch {
    response.writeHead(404); response.end();
  }
}

(async () => {
  const server = http.createServer(serve);
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch({headless: true});
  try {
    const context = await browser.newContext({serviceWorkers: 'block'});
    await context.route('**/*', route => {
      const url = new URL(route.request().url());
      return url.origin === base ? route.continue() : route.abort();
    });
    const page = await context.newPage();
    await page.goto(base + '/', {waitUntil: 'load'});
    await page.locator('.okh-search-trigger').click();
    const input = page.locator('.okh-search-input');
    const resultLinks = page.locator('.okh-search-results .okh-search-result');
    const expected = '/toolbox/01-discovered-careers/01a-resume-builder/';
    const queries = ['resume', 'résumé', 're\u0301sume\u0301'];
    const evidence = {};
    for (const query of queries) {
      await input.fill(query);
      await page.waitForTimeout(200);
      const hrefs = await resultLinks.evaluateAll(links => links.map(link => link.getAttribute('href')));
      evidence[query] = hrefs.slice(0, 3);
      assert.equal(hrefs[0], expected, `accented query ranked ${hrefs[0]} first: ${query}`);
    }

    const fixtureContext = await browser.newContext({serviceWorkers: 'block'});
    await fixtureContext.route('**/assets/data/search-index.json', route => route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({pages: [
        {url: '/travel/', title: '旅行計画', description: '旅行計画の案内', category: 'Guide', headings: [], body: ''},
        {url: '/resume-builder/', title: 'Resume Builder', description: 'Build a resume', category: 'Tool-ette', headings: [], body: ''},
        {url: '/resume-builder-guide/', title: 'Resume Builder Guide', description: 'A guide', category: 'Guide', headings: [], body: ''},
      ]}),
    }));
    const fixturePage = await fixtureContext.newPage();
    await fixturePage.goto(base + '/', {waitUntil: 'load'});
    await fixturePage.locator('.okh-search-trigger').click();
    const fixtureInput = fixturePage.locator('.okh-search-input');
    await fixtureInput.fill('旅行');
    await fixturePage.waitForTimeout(150);
    assert.equal(await fixturePage.locator('.okh-search-result').first().getAttribute('href'), '/travel/',
      'Unicode-letter query did not produce the Japanese catalog result');
    await fixtureInput.fill('resume builder');
    await fixturePage.waitForTimeout(150);
    assert.equal(await fixturePage.locator('.okh-search-result').first().getAttribute('href'), '/resume-builder/',
      'multiword ranking changed for Resume Builder');
    evidence.unicode_and_multiword = {
      unicode: '/travel/', multiword: '/resume-builder/',
    };
    await fixtureContext.close();

    await page.goto(base + '/search/?q=resume', {waitUntil: 'load'});
    const category = page.locator('[data-glee-search-inline-categories] button[data-cat="Tool-ette"]');
    await category.click();
    const categoryLinks = page.locator('[data-glee-search-inline-results] a');
    const categoryHrefs = await categoryLinks.evaluateAll(links => links.map(link => link.getAttribute('href')));
    assert.ok(categoryHrefs.length > 0, 'Tool-ette category returned no results');
    assert.equal(categoryHrefs[0], expected, 'category ranking changed for Resume Builder');
    evidence.category = categoryHrefs.slice(0, 3);
    console.log(JSON.stringify({status: 'PASS', evidence}, null, 2));
    await context.close();
  } finally {
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => {
  console.error(JSON.stringify({status: 'FAIL', error: error.message}, null, 2));
  process.exitCode = 1;
});

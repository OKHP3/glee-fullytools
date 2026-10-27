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

async function acknowledgeTransition(context) {
  await context.addInitScript(() => {
    sessionStorage.setItem('glee-gpt-transition-2026-09', 'acknowledged');
  });
}

(async () => {
  const server = http.createServer(serve);
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch({headless: true});
  try {
    // Hold the dynamic module until after the search overlay opens. The
    // acknowledged fixture must stay usable even when initialization is late.
    const delayedContext = await browser.newContext({serviceWorkers: 'block'});
    let releaseModule;
    let markRequested;
    let requestTimer;
    let delayedModuleVerified = false;
    const moduleGate = new Promise(resolve => { releaseModule = resolve; });
    const moduleRequested = new Promise(resolve => { markRequested = resolve; });
    try {
      await acknowledgeTransition(delayedContext);
      await delayedContext.route('**/*', route => {
        const url = new URL(route.request().url());
        return url.origin === base ? route.continue() : route.abort();
      });
      await delayedContext.route('**/assets/js/glee-site-enhancements.js*', async route => {
        markRequested();
        await moduleGate;
        await route.continue();
      });
      const delayedPage = await delayedContext.newPage();
      await delayedPage.goto(base + '/', {waitUntil: 'load'});
      await Promise.race([
        moduleRequested,
        new Promise((_, reject) => { requestTimer = setTimeout(() => reject(new Error('dynamic module was not requested')), 5000); }),
      ]);
      clearTimeout(requestTimer);
      await delayedPage.locator('.okh-search-trigger').click();
      assert.equal(await delayedPage.locator('.okh-search-overlay').getAttribute('data-open'), 'true');
      releaseModule();
      await delayedPage.locator('[data-transition-open]').waitFor({state: 'visible'});
      assert.equal(await delayedPage.locator('.glee-transition-dialog').evaluate(dialog => dialog.open), false);
      assert.equal(await delayedPage.locator('.okh-search-overlay').getAttribute('data-open'), 'true');
      delayedModuleVerified = true;
    } finally {
      clearTimeout(requestTimer);
      releaseModule();
      await delayedContext.close();
    }
    const context = await browser.newContext({serviceWorkers: 'block'});
    await acknowledgeTransition(context);
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
    const evidence = {delayed_module: delayedModuleVerified};
    for (const query of queries) {
      await input.fill(query);
      await page.waitForTimeout(200);
      const hrefs = await resultLinks.evaluateAll(links => links.map(link => link.getAttribute('href')));
      evidence[query] = hrefs.slice(0, 3);
      assert.equal(hrefs[0], expected, `accented query ranked ${hrefs[0]} first: ${query}`);
    }
    const indexed = JSON.parse(fs.readFileSync(path.join(root, 'assets/data/search-index.json'), 'utf8'));
    const chapter = indexed.pages.find(entry => entry.url === '/next-chapter/');
    assert.ok(chapter, 'the current index contains the Next Chapter route');
    await input.fill('nextchapter');
    const overlayResult = page.locator('.okh-search-results a[href="/next-chapter/"]');
    assert.equal(await overlayResult.count(), 1, 'overlay finds a joined route name');
    assert.equal(await overlayResult.locator('.okh-search-result-title').innerText(), chapter.title);
    await input.fill('nextchapterzz');
    assert.equal(await overlayResult.count(), 0, 'overlay rejects a near-miss route');
    assert.match(await page.locator('.okh-search-status').textContent(), /No search results/);
    evidence.joined_overlay = {route: chapter.url, titlePreserved: true, nearMissRejected: true};

    const fixtureContext = await browser.newContext({serviceWorkers: 'block'});
    await acknowledgeTransition(fixtureContext);
    await fixtureContext.route('**/*', route => {
      const url = new URL(route.request().url());
      return url.origin === base ? route.continue() : route.abort();
    });
    await fixtureContext.route('**/assets/data/search-index.json*', route => route.fulfill({
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
    await page.goto(base + '/search/?q=nextchapter', {waitUntil: 'load'});
    await page.waitForFunction(() => {
      const status = document.querySelector('[data-glee-search-inline-status]');
      return status && !status.textContent.includes('Loading index');
    });
    const dedicatedResult = page.locator('[data-glee-search-inline-results] a[href="/next-chapter/"]');
    assert.equal(await dedicatedResult.count(), 1, 'dedicated search finds a joined route name');
    assert.equal(await dedicatedResult.locator('.okh-search-result-title').innerText(), chapter.title);
    await page.locator('[data-glee-search-inline-input]').fill('nextchapterzz');
    assert.equal(await dedicatedResult.count(), 0, 'dedicated search rejects a near-miss route');
    assert.match(await page.locator('[data-glee-search-inline-status]').textContent(), /^0 results/);
    evidence.joined_page = {route: chapter.url, titlePreserved: true, nearMissRejected: true};
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

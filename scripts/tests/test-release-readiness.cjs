// Focused cross-engine release journeys using an existing Node Playwright runtime.
// No installation or generated-data substitution. HTTP fixtures remove only CSP's
// upgrade-insecure-requests directive; production source bytes remain unchanged.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const http = require('node:http');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { createHash } = require('node:crypto');
const playwright = require('playwright');
const root = path.resolve(__dirname, '../..');
const output = process.env.RELEASE_READINESS_OUTPUT;
const engines = (process.env.RELEASE_READINESS_ENGINES || 'firefox,webkit').split(',');
const types = { '.html': 'text/html', '.js': 'application/javascript', '.mjs': 'application/javascript',
  '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png',
  '.webp': 'image/webp', '.ico': 'image/x-icon', '.webmanifest': 'application/manifest+json' };
const served = {};
const server = http.createServer(async (request, response) => {
  const url = new URL(request.url, 'http://localhost');
  let file = path.resolve(root, '.' + decodeURIComponent(url.pathname));
  if (file !== root && !file.startsWith(root + path.sep)) { response.writeHead(403).end(); return; }
  try {
    if ((await fs.stat(file)).isDirectory()) file = path.join(file, 'index.html');
    let body = await fs.readFile(file);
    const relative = path.relative(root, file).split(path.sep).join('/');
    served[relative] = createHash('sha256').update(body).digest('hex');
    if (file.endsWith('.html')) body = body.toString('utf8').replace(/upgrade-insecure-requests;?\s*/g, '');
    response.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream',
      'Cache-Control': 'no-store' }).end(body);
  } catch { response.writeHead(404, { 'Content-Type': 'text/plain' }).end('Not found'); }
});

(async () => {
  const report = { generatedAt: new Date().toISOString(),
    commit: spawnSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).stdout.trim(),
    node: process.version, playwright: require('playwright/package.json').version,
    fixture: 'Local HTTP; only upgrade-insecure-requests removed; service workers and third parties blocked; actual committed search JSON served.',
    checks: [], limitations: [], servedSha256: served };
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  for (const engine of engines) {
    let browser;
    const check = async (name, operation) => {
      try { report.checks.push({ engine, name, status: 'PASS', evidence: await operation() }); }
      catch (error) { report.checks.push({ engine, name, status: 'FAIL', error: error.message }); }
    };
    try {
      browser = await playwright[engine].launch({ headless: true });
      const context = await browser.newContext({ serviceWorkers: 'block', viewport: { width: 390, height: 844 } });
      const external = [];
      await context.route('**/*', route => {
        if (new URL(route.request().url()).origin === base) return route.continue();
        external.push(route.request().url());
        return route.abort();
      });
      const page = await context.newPage();
      page.setDefaultTimeout(10000);
      const probe = await context.newPage();
      await probe.setContent('<button>Before</button><main tabindex="-1"><a href="#x" id="link">Link</a><button id="inside">Inside</button></main>');
      await probe.locator('main').focus();
      await probe.keyboard.press('Tab');
      const nativeTabDestination = await probe.evaluate(() => document.activeElement.id);
      await probe.close();
      if (nativeTabDestination !== 'link') report.limitations.push({ engine,
        coverage: 'Next-link Tab navigation NOT RUN: native browser Tab excludes anchors even in an isolated HTML fixture.' });
      const pageErrors = [];
      page.on('pageerror', error => pageErrors.push(error.message));
      for (const route of ['/', '/toolbox/01-discovered-careers/',
        '/toolbox/01-discovered-careers/01a-resume-builder/', '/search/?q=resume']) {
        await check('navigation ' + route, async () => {
          const before = pageErrors.length;
          const response = await page.goto(base + route, { waitUntil: 'load' });
          assert.equal(response.status(), 200);
          await page.locator('h1').waitFor({ state: 'visible' });
          const metrics = await page.evaluate(() => ({ title: document.title,
            overflow: document.documentElement.scrollWidth > innerWidth + 1 }));
          assert.equal(metrics.overflow, false);
          assert.equal(pageErrors.length, before, pageErrors.slice(before).join('; '));
          return metrics;
        });
      }
      await check('search query, keyboard, history and modal focus', async () => {
        await page.goto(base + '/search/?q=resume', { waitUntil: 'load' });
        const input = page.locator('[data-glee-search-inline-input]');
        await page.waitForFunction(() => document.querySelector('[data-glee-search-inline-results] a'));
        assert.equal(await input.inputValue(), 'resume');
        const first = await page.locator('[data-glee-search-inline-results] a').first().getAttribute('href');
        assert.match(first, /resume/);
        await input.fill('budget');
        await page.waitForFunction(() => new URL(location.href).searchParams.get('q') === 'budget');
        await page.goBack();
        assert.equal(await input.inputValue(), 'resume');
        await input.press('ArrowDown');
        const selected = await page.locator('[data-glee-search-inline-results] a[data-active="true"]').getAttribute('href');
        await input.press('Enter');
        await page.waitForURL(base + selected);
        const notice = page.locator('[data-wip-dismiss]');
        if (await notice.isVisible()) await notice.click();
        const trigger = page.locator('.okh-search-trigger');
        await trigger.click();
        assert.equal(await page.locator('.okh-search-overlay').getAttribute('aria-label'), 'Search Glee‑fully Tools');
        await page.waitForFunction(() => document.activeElement.classList.contains('okh-search-input'));
        await page.keyboard.press('Escape');
        const focus = await page.evaluate(() => ({ tag: document.activeElement.tagName,
          className: document.activeElement.className, text: document.activeElement.textContent.trim().slice(0, 100) }));
        assert.equal(await trigger.evaluate(element => element === document.activeElement), true,
          'Modal close did not return focus to the opener: ' + JSON.stringify(focus));
        return { firstResumeResult: first, keyboardDestination: selected };
      });
      for (const method of ['pointer', 'keyboard', 'shortcut', 'immediate-close']) {
        await check('modal focus return ' + method, async () => {
          await page.goto(base + '/', { waitUntil: 'load' });
          const trigger = page.locator('.okh-search-trigger');
          await trigger.waitFor({ state: 'visible' });
          if (method === 'pointer') {
            await trigger.click();
          } else {
            await trigger.focus();
            if (method === 'shortcut') await page.keyboard.press('Control+k');
            else if (method === 'immediate-close') {
              await trigger.evaluate(element => {
                element.click();
                document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
              });
            } else await page.keyboard.press('Enter');
          }
          if (method !== 'immediate-close') {
            await page.waitForFunction(() => document.activeElement.classList.contains('okh-search-input'));
            await page.keyboard.press('Escape');
          }
          // Wait beyond the deferred input focus so a hidden input cannot reclaim focus.
          await page.waitForTimeout(80);
          assert.equal(await page.locator('.okh-search-overlay').getAttribute('data-open'), 'false');
          assert.equal(await trigger.evaluate(element => element === document.activeElement), true);
          return { focused: '.okh-search-trigger' };
        });
      }
      await check('skip link moves focus and records native Tab behavior', async () => {
        await page.goto(base + '/', { waitUntil: 'load' });
        const skip = page.locator('.skip-to-content');
        await skip.focus();
        await page.keyboard.press('Enter');
        const focusedMain = await page.evaluate(() => document.activeElement === document.getElementById('main'));
        await page.keyboard.press('Tab');
        const nextFocus = await page.evaluate(() => ({ inside: document.getElementById('main').contains(document.activeElement),
          tag: document.activeElement.tagName, href: document.activeElement.getAttribute('href'), className: document.activeElement.className }));
        const nextInMain = nextFocus.inside;
        assert.ok(focusedMain, JSON.stringify({ focusedMain, nextFocus }));
        // When native Tab excludes links, this page has no eligible main form
        // controls. Record that boundary; do not alter source tab order to force it.
        if (nativeTabDestination === 'link') assert.ok(nextInMain, JSON.stringify(nextFocus));
        assert.equal(new URL(page.url()).hash, '#main');
        return { focusedMain, nextInMain, nativeTabDestination,
          nextLinkCoverage: nativeTabDestination === 'link' ? 'PASS' : 'NOT RUN: native browser Tab excludes links' };
      });
      await check('consent choice hydrates after reload', async () => {
        await page.goto(base + '/legal/', { waitUntil: 'load' });
        await page.waitForFunction(() => window.gleeAnalytics);
        assert.match(await page.locator('[data-analytics-status]').innerText(), /off/);
        await page.locator('[data-analytics-action="granted"]').click();
        await page.reload({ waitUntil: 'load' });
        await page.waitForFunction(() => window.gleeAnalytics?.status() === 'granted');
        assert.match(await page.locator('[data-analytics-status]').innerText(), /on/);
        await page.locator('[data-analytics-action="denied"]').click();
        return { optionalExternalRequestsBlocked: external.length };
      });
      await check('ordinary fragment focus, history and reduced motion', async () => {
        await page.emulateMedia({ reducedMotion: 'reduce' });
        await page.goto(base + '/', { waitUntil: 'load' });
        await page.evaluate(() => {
          const target = document.getElementById('why');
          const scroll = target.scrollIntoView.bind(target);
          target.scrollIntoView = options => { window.fragmentScroll = options; scroll(options); };
        });
        await page.locator('a[href="#why"]').click();
        assert.equal(await page.evaluate(() => document.activeElement.id), 'why');
        assert.equal(await page.evaluate(() => window.fragmentScroll.behavior), 'auto');
        assert.equal(new URL(page.url()).hash, '#why');
        await page.goBack();
        assert.equal(new URL(page.url()).hash, '');
        await page.emulateMedia({ reducedMotion: 'no-preference' });
        return { fragment: '#why', scrollBehavior: 'auto', historyRestored: true };
      });
      await check('Neighborly Bazaar image decodes', async () => {
        await page.goto(base + '/toolbox/05-organized-life/05f-neighborly-bazaar/', { waitUntil: 'load' });
        const image = page.locator('img[src*="05f-neighborly-bazaar-illustration"]');
        await image.scrollIntoViewIfNeeded();
        const dimensions = await image.evaluate(async element => {
          await element.decode(); return { width: element.naturalWidth, height: element.naturalHeight };
        });
        assert.ok(dimensions.width > 0 && dimensions.height > 0);
        return dimensions;
      });
      await context.close();
    } catch (error) { report.checks.push({ engine, name: 'engine setup', status: 'NOT RUN', error: error.message }); }
    finally { if (browser) await browser.close(); }
  }
  server.closeAllConnections();
  await new Promise(resolve => server.close(resolve));
  report.summary = Object.fromEntries(['PASS', 'FAIL', 'NOT RUN'].map(status =>
    [status, report.checks.filter(check => check.status === status).length]));
  if (output) { await fs.mkdir(path.dirname(output), { recursive: true }); await fs.writeFile(output, JSON.stringify(report, null, 2) + '\n'); }
  console.log(JSON.stringify({ ...report, servedSha256: Object.keys(served).length + ' source files fingerprinted' }, null, 2));
  if (report.summary.FAIL || report.summary['NOT RUN']) process.exitCode = 1;
})().catch(error => { console.error(error); process.exitCode = 1; server.closeAllConnections(); server.close(); });

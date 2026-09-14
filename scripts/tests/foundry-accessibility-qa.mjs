#!/usr/bin/env node

// Focused browser evidence for the public FoundRy feature page.
// This intentionally does not replace the site's full validation or viewport suites.
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { mkdir, readFile, stat, writeFile } from 'node:fs/promises';
import { dirname, extname, resolve, sep } from 'node:path';
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';

const ROOT = resolve(import.meta.dirname, '..', '..');
const require = createRequire(import.meta.url);
const ROUTE = '/foundry/';
const OUTPUT_PATH = (() => {
  const args = process.argv.slice(2);
  const outputIndex = args.indexOf('--output');
  if (outputIndex === -1) return null;
  const output = args[outputIndex + 1];
  if (!output || output.startsWith('--')) {
    throw new Error('Usage: foundry-accessibility-qa.mjs [--output <path>]');
  }
  return resolve(ROOT, output);
})();
const VIEWPORTS = [
  { name: 'narrow-320', width: 320, height: 780 },
  { name: 'narrow-390', width: 390, height: 844 },
];
const TYPES = {
  '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'application/javascript',
  '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png',
  '.webp': 'image/webp', '.ico': 'image/x-icon', '.webmanifest': 'application/manifest+json',
};

function sourceSha() {
  return execFileSync('git', ['rev-parse', 'HEAD'], { cwd: ROOT, encoding: 'utf8' }).trim();
}

async function serve(request, response) {
  const url = new URL(request.url, 'http://127.0.0.1');
  let file = resolve(ROOT, `.${decodeURIComponent(url.pathname)}`);
  if (file !== ROOT && !file.startsWith(`${ROOT}${sep}`)) {
    response.writeHead(403).end('Forbidden');
    return;
  }
  try {
    if ((await stat(file)).isDirectory()) file = resolve(file, 'index.html');
    let body = await readFile(file);
    if (extname(file) === '.html') {
      // The fixture is loopback-only. Keep production bytes unchanged while avoiding
      // a CSP upgrade-insecure-requests rewrite of the local test URL.
      body = body.toString('utf8').replace(/upgrade-insecure-requests;?\s*/g, '');
    }
    response.writeHead(200, {
      'Content-Type': TYPES[extname(file)] || 'application/octet-stream',
      'Cache-Control': 'no-store',
    }).end(body);
  } catch {
    response.writeHead(404).end('Not found');
  }
}

function result(name, status, evidence, error) {
  return { name, status, ...(evidence ? { evidence } : {}), ...(error ? { error } : {}) };
}

function summarize(report) {
  return Object.fromEntries(['PASS', 'FAIL', 'NOT RUN'].map(status => [
    status,
    report.checks.filter(check => check.status === status).length,
  ]));
}

async function writeReport(report) {
  if (!OUTPUT_PATH) return;
  await mkdir(dirname(OUTPUT_PATH), { recursive: true });
  await writeFile(OUTPUT_PATH, `${JSON.stringify(report, null, 2)}\n`);
}

async function notRun(report, reason) {
  report.runtime = { status: 'NOT RUN', reason };
  report.summary = summarize(report);
  await writeReport(report);
  console.log(JSON.stringify(report, null, 2));
  process.exitCode = 2;
  return report;
}

async function run() {
  const report = {
    generatedAt: new Date().toISOString(),
    sourceSha: sourceSha(),
    route: ROUTE,
    viewports: VIEWPORTS,
    checks: [],
    limitations: ['Human screen-reader testing was not run.'],
  };

  let playwright;
  try {
    playwright = require('playwright');
  } catch (error) {
    return await notRun(report, `Installed Playwright runtime unavailable: ${error.message}`);
  }

  const server = createServer(serve);
  try {
    await new Promise((resolveServer, rejectServer) => {
      server.once('error', rejectServer);
      server.listen(0, '127.0.0.1', resolveServer);
    });
  } catch (error) {
    return await notRun(report, `Loopback fixture unavailable: ${error.message}`);
  }
  const base = `http://127.0.0.1:${server.address().port}`;
  report.baseUrl = base;
  let browser;
  try {
    browser = await playwright.chromium.launch({ headless: true });
  } catch (error) {
    await new Promise(resolveServer => server.close(resolveServer));
    return await notRun(report, `Installed Chromium driver unavailable: ${error.message}`);
  }

  report.runtime = { status: 'RUN', driver: 'Playwright Chromium' };
  try {
    for (const viewport of VIEWPORTS) {
      const context = await browser.newContext({ viewport, serviceWorkers: 'block' });
      await context.route('**/*', route => {
        if (new URL(route.request().url()).origin === base) return route.continue();
        return route.abort();
      });
      const page = await context.newPage();
      page.setDefaultTimeout(5000);
      const pageErrors = [];
      page.on('pageerror', error => pageErrors.push(error.message));
      await page.goto(`${base}${ROUTE}`, { waitUntil: 'domcontentloaded', timeout: 10000 });

      const check = async (name, operation) => {
        try {
          report.checks.push(result(`${viewport.name}: ${name}`, 'PASS', await operation()));
        } catch (error) {
          report.checks.push(result(`${viewport.name}: ${name}`, 'FAIL', null, error.message));
        }
      };

      await check('page identity and landmarks', async () => {
        assert.equal(await page.title(), 'Glee‑fully FoundRy | Glee‑fully Personalizable Tools™');
        assert.equal(await page.locator('h1').count(), 1);
        assert.equal(await page.locator('main#main').count(), 1);
        assert.equal(await page.locator('header.site-header').count(), 1);
        assert.equal(await page.locator('nav[aria-label="Primary navigation"]').count(), 1);
        assert.equal(await page.locator('footer.site-footer').count(), 1);
        return { title: await page.title(), h1: await page.locator('h1').innerText() };
      });

      await check('heading order', async () => {
        const levels = await page.locator('h1,h2,h3,h4,h5,h6').evaluateAll(nodes => nodes.map(node => Number(node.tagName[1])));
        assert.equal(levels[0], 1);
        for (let i = 1; i < levels.length; i += 1) assert.ok(levels[i] <= levels[i - 1] + 1, `heading jump ${levels[i - 1]} to ${levels[i]}`);
        return { headingCount: levels.length, levels };
      });

      await check('CTA accessible names', async () => {
        const names = await page.locator('.hero-actions a').allTextContents();
        assert.deepEqual(names.map(name => name.trim()), ['Follow an idea through', 'Where things stand', 'Open the Toolbox', 'Share an idea']);
        for (const link of await page.locator('.hero-actions a').all()) assert.ok((await link.innerText()).trim());
        return { names };
      });

      await check('FAQ keyboard operation', async () => {
        const summary = page.locator('details summary').first();
        await summary.focus();
        assert.equal(await page.evaluate(() => document.activeElement?.tagName), 'SUMMARY');
        await page.keyboard.press('Enter');
        const details = summary.locator('xpath=..');
        assert.equal(await details.getAttribute('open'), '');
        await page.keyboard.press('Space');
        assert.equal(await details.getAttribute('open'), null);
        return { summaries: await page.locator('details summary').count(), toggled: true };
      });

      await check('focus visibility', async () => {
        const selector = 'a[href], button, summary';
        const inspect = async () => page.evaluate(selector => {
          const nodes = [...document.querySelectorAll(selector)];
          const node = document.activeElement;
          const style = getComputedStyle(node);
          return {
            key: nodes.indexOf(node),
            name: (node.textContent || node.getAttribute('aria-label') || node.tagName).trim().slice(0, 80),
            outlineStyle: style.outlineStyle, outlineWidth: style.outlineWidth,
            boxShadow: style.boxShadow,
          };
        }, selector);
        const assertIndicator = evidence => assert.ok(
          (evidence.outlineStyle !== 'none' && evidence.outlineWidth !== '0px') || evidence.boxShadow !== 'none',
          `no visible focus indicator for ${evidence.name}`,
        );
        const cycle = async state => {
          const expected = await page.locator(selector).evaluateAll(nodes => nodes.flatMap((node, key) => {
            const style = getComputedStyle(node);
            return node.tabIndex >= 0 && !node.disabled && !node.closest('[inert]') &&
              style.visibility === 'visible' && [...node.getClientRects()].some(rect => rect.width && rect.height) ? [key] : [];
          }));
          assert.ok(expected.length > 0, `${state}: no keyboard candidates`);
          const first = await inspect();
          assert.ok(expected.includes(first.key), `${state}: initial focus is not an eligible control`);
          const seen = new Set();
          let completed = false;
          // One document cycle, with room for the browser's own focus stop.
          for (let step = 0; step <= expected.length + 2; step += 1) {
            const current = await inspect();
            if (step > 0 && current.key === first.key) { completed = true; break; }
            if (current.key >= 0) {
              assert.ok(expected.includes(current.key), `${state}: reached an ineligible control`);
              assertIndicator(current);
              seen.add(current.key);
            }
            await page.keyboard.press('Tab');
          }
          assert.ok(completed, `${state}: keyboard navigation did not complete a cycle`);
          assert.deepEqual([...seen].sort((a, b) => a - b), expected.sort((a, b) => a - b), `${state}: keyboard controls were missed`);
          return { state, expected: expected.length, checked: seen.size };
        };

        await page.evaluate(() => { history.scrollRestoration = 'manual'; });
        await page.reload({ waitUntil: 'load' });
        await page.waitForFunction(() => [...document.styleSheets].every(sheet => {
          try {
            return sheet.cssRules !== null;
          } catch {
            return true;
          }
        }));
        await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
        await page.waitForFunction(() => scrollY === 0);
        await page.keyboard.press('Tab');
        const skip = page.locator('.skip-to-content');
        assert.equal(await skip.evaluate(node => node === document.activeElement), true, 'skip link is not the first keyboard target');
        assertIndicator(await inspect());
        await page.waitForFunction(() => {
          const rect = document.querySelector('.skip-to-content').getBoundingClientRect();
          return rect.y >= 0 && rect.y < innerHeight;
        });
        const box = await skip.boundingBox();
        assert.ok(box && box.x >= 0 && box.y >= 0 && box.x < viewport.width && box.y < viewport.height, 'focused skip link is off screen');

        // Negative control changes only the loopback browser fixture, never source.
        const priorStyle = await skip.getAttribute('style');
        try {
          await skip.evaluate(node => {
            node.style.setProperty('outline', 'none', 'important');
            node.style.setProperty('box-shadow', 'none', 'important');
          });
          const suppressed = await inspect();
          assert.throws(() => assertIndicator(suppressed), /no visible focus indicator/, 'negative fixture was not detected');
        } finally {
          await skip.evaluate((node, prior) => prior === null ? node.removeAttribute('style') : node.setAttribute('style', prior), priorStyle);
        }
        assertIndicator(await inspect());
        const navToggle = page.locator('.nav-toggle');
        assert.equal(await navToggle.getAttribute('aria-expanded'), 'false');
        const closed = await cycle('menu closed');
        await navToggle.click();
        await page.waitForFunction(() => document.querySelector('#navigation a') === document.activeElement);
        assert.equal(await navToggle.getAttribute('aria-expanded'), 'true');
        // Establish keyboard modality after the pointer opens the menu.
        await page.keyboard.press('Tab');
        const open = await cycle('menu open');
        assert.ok(open.checked > closed.checked, 'opening the menu added no keyboard targets');
        await page.keyboard.press('Escape');
        assert.equal(await navToggle.getAttribute('aria-expanded'), 'false');
        assert.equal(await navToggle.evaluate(node => node === document.activeElement), true, 'Escape did not restore focus');
        assertIndicator(await inspect());
        return { closed, open, negativeControl: 'detected missing indicator' };
      });

      await check('expanded mobile navigation keyboard focus', async () => {
        const navToggle = page.locator('.nav-toggle');
        const primaryNav = page.locator('#navigation');
        const primaryLinks = page.locator('#navigation > ul > li > a[href]');
        const submenuLinks = page.locator('#navigation .submenu a[href]');
        const navLinks = page.locator('#navigation a[href]');

        // Keep the collapsed-state contract explicit: the focus visibility
        // check above must continue to exclude this inert region.
        assert.equal(await navToggle.getAttribute('aria-expanded'), 'false');
        assert.equal(await primaryNav.getAttribute('aria-hidden'), 'true');
        assert.notEqual(await primaryNav.getAttribute('inert'), null);

        await navToggle.focus();
        await page.keyboard.press('Enter');
        await page.waitForFunction(() => document.activeElement?.matches('#navigation a[href]'));

        assert.equal(await navToggle.getAttribute('aria-expanded'), 'true');
        assert.equal(await primaryNav.getAttribute('aria-hidden'), 'false');
        assert.equal(await primaryNav.getAttribute('inert'), null);
        assert.ok(await primaryLinks.count() > 0, 'expanded navigation has no primary links');
        assert.ok(await submenuLinks.count() > 0, 'expanded navigation has no submenu links');

        const evidence = [];
        const count = await navLinks.count();
        for (let i = 0; i < count; i += 1) {
          const link = navLinks.nth(i);
          assert.equal(
            await link.evaluate(node => node === document.activeElement),
            true,
            `navigation link ${i + 1} is not keyboard-reachable`,
          );
          const style = await link.evaluate(node => {
            const computed = getComputedStyle(node);
            return {
              name: (node.innerText || node.getAttribute('aria-label') || '').trim().slice(0, 80),
              outlineStyle: computed.outlineStyle,
              outlineWidth: computed.outlineWidth,
              boxShadow: computed.boxShadow,
            };
          });
          assert.ok(
            style.outlineStyle !== 'none' && style.outlineWidth !== '0px' || style.boxShadow !== 'none',
            `no visible focus indicator for expanded navigation link ${style.name}`,
          );
          evidence.push(style);
          if (i < count - 1) await page.keyboard.press('Tab');
        }

        return {
          primaryLinks: await primaryLinks.count(),
          submenuLinks: await submenuLinks.count(),
          checked: evidence,
        };
      });

      await check('narrow viewport overflow and console health', async () => {
        const metrics = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, innerWidth: innerWidth }));
        assert.ok(metrics.scrollWidth <= metrics.innerWidth + 1, `${metrics.scrollWidth}px document exceeds ${metrics.innerWidth}px viewport`);
        assert.deepEqual(pageErrors, [], pageErrors.join('; '));
        return metrics;
      });
      await context.close();
    }
  } finally {
    await browser.close();
    server.closeAllConnections();
    await new Promise(resolveServer => server.close(resolveServer));
  }

  report.summary = summarize(report);
  await writeReport(report);
  console.log(JSON.stringify(report, null, 2));
  if (report.summary.FAIL > 0) process.exitCode = 1;
  return report;
}

run().catch(error => {
  console.error(error);
  process.exitCode = 1;
});

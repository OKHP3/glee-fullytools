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
        const interactive = page.locator('a, button, summary');
        const count = await interactive.count();
        const evidence = [];
        let skippedUnavailable = 0;
        for (let i = 0; i < count; i += 1) {
          const item = interactive.nth(i);
          const unavailable = await item.evaluate(node => {
            for (let current = node; current; current = current.parentElement) {
              const style = getComputedStyle(current);
              if (
                current.closest('[inert]') ||
                current.hidden ||
                current.getAttribute('aria-hidden') === 'true' ||
                style.display === 'none' ||
                style.visibility === 'hidden'
              ) return true;
            }
            return false;
          });
          if (unavailable) {
            skippedUnavailable += 1;
            continue;
          }
          // Request the keyboard-visible focus state explicitly. A generic
          // programmatic focus can leave Chromium's :focus-visible heuristic
          // false even when the keyboard focus style is present and usable.
          await item.evaluate(node => node.focus({ focusVisible: true }));
          const style = await item.evaluate(node => {
            const computed = getComputedStyle(node);
            return { name: (node.innerText || node.getAttribute('aria-label') || '').trim().slice(0, 80), outlineStyle: computed.outlineStyle, outlineWidth: computed.outlineWidth, boxShadow: computed.boxShadow };
          });
          assert.ok(style.outlineStyle !== 'none' && style.outlineWidth !== '0px' || style.boxShadow !== 'none', `no visible focus indicator for ${style.name}`);
          evidence.push(style);
        }
        return { interactiveCount: count, checked: evidence.length, skippedUnavailable };
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

/* Browser regressions for the September 2026 corrective release.
   Requires an existing Playwright installation and a local preview server. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const base = process.env.QA_BASE || 'http://127.0.0.1:5187';
const output = process.env.QA_OUTPUT;
const results = [];
function rgb(value) { return value.match(/[\d.]+/g).map(Number); }
function luminance(color) {
  const c = color.slice(0, 3).map(v => v / 255).map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4);
  return .2126 * c[0] + .7152 * c[1] + .0722 * c[2];
}
function contrast(foreground, background) {
  const fg = rgb(foreground), bg = rgb(background), alpha = fg[3] ?? 1;
  const a = luminance(fg.map((v, i) => i < 3 ? v * alpha + bg[i] * (1 - alpha) : v));
  const b = luminance(bg);
  return (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
}
(async () => {
  const browser = await chromium.launch({ headless: true });
  let failures = 0;
  async function check(name, fn) {
    try { const evidence = await fn(); results.push({ name, status: 'PASS', evidence }); }
    catch (error) { failures++; results.push({ name, status: 'FAIL', error: error.message }); }
  }
  try {
    for (const mode of ['light', 'dark', 'auto-light', 'auto-dark']) {
      const context = await browser.newContext({ colorScheme: mode.endsWith('dark') ? 'dark' : 'light', reducedMotion: 'reduce', serviceWorkers: 'block' });
      await context.route('**/*', route => new URL(route.request().url()).origin === new URL(base).origin ? route.continue() : route.abort());
      const page = await context.newPage();
      await page.goto(base, { waitUntil: 'domcontentloaded' });
      await page.evaluate(mode => { if (mode.startsWith('auto')) document.documentElement.removeAttribute('data-color-scheme'); else document.documentElement.setAttribute('data-color-scheme', mode); }, mode);
      await page.waitForTimeout(350);
      await check(`hero contrast ${mode}`, async () => {
        const colors = await page.evaluate(() => ({
          eyebrow: getComputedStyle(document.querySelector('.hero-eyebrow')).color,
          heading: getComputedStyle(document.querySelector('h1')).color,
          background: getComputedStyle(document.querySelector('.glee-hero-card'), '::before').backgroundColor,
        }));
        const eyebrowRatio = contrast(colors.eyebrow, colors.background), headingRatio = contrast(colors.heading, colors.background);
        assert(eyebrowRatio >= 4.5, `Eyebrow ${eyebrowRatio.toFixed(2)}:1`);
        assert(headingRatio >= 3, `Large heading ${headingRatio.toFixed(2)}:1`);
        return { ...colors, eyebrowRatio, headingRatio };
      });
      await context.close();
    }
    const context = await browser.newContext({ serviceWorkers: 'block' });
    await context.route('**/*', route => new URL(route.request().url()).origin === new URL(base).origin ? route.continue() : route.abort());
    const page = await context.newPage();
    await page.goto(base, { waitUntil: 'domcontentloaded' });
    await check('Neighborly illustration decodes', async () => {
      const size = await page.evaluate(async () => { const img = new Image(); img.src = '/assets/img/tool-ettes/05f-neighborly-bazaar-illustration.svg'; await img.decode(); return [img.naturalWidth, img.naturalHeight]; });
      assert(size.every(v => v > 0)); return size;
    });
    for (const width of [320, 375, 390, 414, 768, 1024, 1280, 1440]) {
      await check(`Resume Builder route and image recheck ${width}`, async () => {
        await page.setViewportSize({ width, height: 900 });
        const errors = [];
        const failed = request => { if (request.url().startsWith(base)) errors.push(request.url()); };
        const pageError = error => errors.push(error.message);
        page.on('requestfailed', failed); page.on('pageerror', pageError);
        try {
          const response = await page.goto(base + '/toolbox/01-discovered-careers/01a-resume-builder/', { waitUntil: 'load' });
          assert.equal(response.status(), 200);
          const sizes = await page.evaluate(async () => {
            const imgs = [...document.images];
            await Promise.all(imgs.map(img => { img.loading = 'eager'; return img.decode(); }));
            return imgs.map(img => [img.naturalWidth, img.naturalHeight]);
          });
          assert(sizes.every(size => size.every(v => v > 0)));
          assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
          assert.deepEqual(errors, []);
          return { width, decodedImages: sizes.length };
        } finally { page.off('requestfailed', failed); page.off('pageerror', pageError); }
      });
    }
    await context.close();
  } finally { await browser.close(); }
  const report = { checkedAt: new Date().toISOString(), base, browser: 'Chromium', results, failures };
  if (output) { fs.mkdirSync(path.dirname(output), { recursive: true }); fs.writeFileSync(output, JSON.stringify(report, null, 2) + '\n'); }
  console.log(JSON.stringify(report, null, 2));
  process.exitCode = failures ? 1 : 0;
})().catch(error => { console.error(error); process.exitCode = 1; });

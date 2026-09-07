// Existing Playwright only. Local lab observations are not field Core Web Vitals.
function createLayoutShiftAccumulator() {
  let cls = 0;
  let layoutShiftTotal = 0;
  let windowStart = null;
  let previousShift = null;
  let windowValue = 0;
  return {
    add(entry) {
      if (!entry.hadRecentInput) {
        layoutShiftTotal += entry.value;
        if (windowStart !== null && entry.startTime - previousShift < 1000 && entry.startTime - windowStart < 5000) {
          windowValue += entry.value;
        } else {
          windowStart = entry.startTime;
          windowValue = entry.value;
        }
        previousShift = entry.startTime;
        cls = Math.max(cls, windowValue);
      }
      return { cls, layoutShiftTotal };
    },
    snapshot() { return { cls, layoutShiftTotal }; },
  };
}
module.exports = { createLayoutShiftAccumulator };

if (require.main === module && process.argv[2] === '--reassess-cls') {
  const fs = require('node:fs');
  const path = require('node:path');
  const crypto = require('node:crypto');
  const directory = path.resolve(__dirname, '../../assets/audit/remaining-program-2026-09-05');
  const destination = process.argv[3];
  if (!destination || fs.existsSync(destination)) throw new Error('Supply a new evidence filename; existing evidence will not be overwritten.');
  const result = { assessedAt: new Date().toISOString(), method: 'Maximum non-input session-window sum; gap <1000ms and elapsed <5000ms. Originals are preserved and identified by SHA-256.',
    references: ['https://web.dev/articles/cls','https://web.dev/blog/evolving-cls'],
    note: 'Historical files overlap and include an initial duplicate; row counts are not independent sample counts.', sources: [], rows: [] };
  for (const filename of fs.readdirSync(directory).filter(name => name.startsWith('experience') && name.endsWith('.json')).sort()) {
    const bytes = fs.readFileSync(path.join(directory, filename));
    const report = JSON.parse(bytes);
    if (!report.performance?.length) continue;
    result.sources.push({ filename, sha256: crypto.createHash('sha256').update(bytes).digest('hex'), rows: report.performance.length });
    report.performance.forEach((row, index) => {
      const initial = row.initialViewport;
      const shifts = initial?.shifts;
      const legacyTotal = initial?.layoutShiftTotal ?? initial?.cls ?? null;
      const derived = { source: filename, row: index, profile: row.profile, route: row.route, repetition: row.repetition, cache: row.cache,
        originalFieldName: initial?.layoutShiftTotal === undefined ? 'cls (legacy lifetime total)' : 'layoutShiftTotal',
        layoutShiftTotal: legacyTotal, rawShiftsPointer: `/performance/${index}/initialViewport/shifts`, cls: null,
        interpretation: 'legacy-total-insufficient-timestamps' };
      if (Array.isArray(shifts) && shifts.every(s => Number.isFinite(s.startTime) && Number.isFinite(s.value))) {
        const accumulator = createLayoutShiftAccumulator();
        for (const shift of [...shifts].sort((a,b) => a.startTime-b.startTime)) accumulator.add(shift);
        const measured = accumulator.snapshot();
        if (legacyTotal !== null && Math.abs(measured.layoutShiftTotal - legacyTotal) < 1e-10) {
          derived.cls = measured.cls;
          derived.interpretation = shifts.length ? 'recomputed-from-timestamped-shifts' : 'confirmed-empty-shift-observation';
        } else derived.interpretation = 'incomplete-raw-shifts-total-mismatch';
      }
      result.rows.push(derived);
    });
  }
  result.summary = result.rows.reduce((counts,row) => {counts[row.interpretation]=(counts[row.interpretation]||0)+1;return counts;},{});
  fs.mkdirSync(path.dirname(path.resolve(destination)),{recursive:true});
  fs.writeFileSync(destination,JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify({destination,summary:result.summary}));
} else if (require.main === module) {
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const zlib = require('node:zlib');
const crypto = require('node:crypto');
const { execFileSync } = require('node:child_process');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '../..');
const output = path.resolve(process.env.EXPERIENCE_OUTPUT || path.join(root, `assets/audit/remaining-program-2026-09-05/experience-performance-session-${new Date().toISOString().replace(/[:.]/g,'-').toLowerCase()}.json`));
const screenshots = process.env.EXPERIENCE_SCREENSHOTS;
const repetitions = Number(process.env.EXPERIENCE_REPETITIONS || 2);
const selectedRoutes = process.env.EXPERIENCE_ROUTES?.split(',');
const candidateCss = process.env.EXPERIENCE_SEARCH_SPACE ? '\nbody.glee-main .glee-search-page__categories{min-height:4rem}body.glee-main .glee-search-page__results-wrap{min-height:22rem}@media(max-width:600px){body.glee-main .glee-search-page__categories{min-height:8rem}}\n' : '';
const routes = {
  home: '/', branch: '/toolbox/01-discovered-careers/',
  detail: '/toolbox/05-organized-life/05f-neighborly-bazaar/',
  search: '/search/?q=seniority', diagram: '/ecosystem/',
};
const profiles = [
  { name: 'desktop', viewport: { width: 1440, height: 1000 }, cpu: 1, latency: 0, download: -1, upload: -1 },
  { name: 'constrained-mobile', viewport: { width: 390, height: 844 }, cpu: 4, latency: 150, download: 200000, upload: 93750 },
];
const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.mjs': 'text/javascript',
  '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.webp': 'image/webp',
  '.ico': 'image/x-icon', '.webmanifest': 'application/manifest+json', '.woff2': 'font/woff2' };
const compressed = new Map();
const report = {
  startedAt: new Date().toISOString(), commit: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim(),
  browser: '', sourceRoot: root, repetitions,
  experimentalCssResponseAppend: candidateCss || null,
  policy: { kind: 'local lab, no live or field measurements', serviceWorkers: 'blocked to isolate HTTP cache',
    server: 'gzip text; max-age=600 assets and no-cache HTML; cold and same-context repeat navigation to identical URL',
    fonts: 'real Google Fonts network requests allowed for performance; blocked in isolated accessibility cases',
    analytics: 'all Google Analytics and Tag Manager requests blocked',
    constrained: '4x CPU slowdown, 150 ms request latency, 1.6 Mbps download, 0.75 Mbps upload',
    caveats: ['Localhost omits DNS/TLS/origin distance.', 'HTTP cache policy is an explicit lab policy, not verified production headers.',
      'Initial viewport LCP and CLS are observation-window values, not field p75.', 'Synthetic search latency is not INP.',
      'Two samples per condition identify candidates; they do not establish reliable percentile claims.'] },
  sourceAssets: {}, performance: [], accessibility: [], failures: [],
  layoutShiftMethod: { cls: 'maximum session-window sum; consecutive gap <1000ms and duration from window start <5000ms; excludes hadRecentInput',
    layoutShiftTotal: 'sum of all non-input shifts within this observation lifetime; not CLS',
    references: ['https://web.dev/articles/cls','https://web.dev/blog/evolving-cls'],
    boundary: 'Foreground local navigation observation only; not full page lifetime, field p75 or cross-frame aggregation.' },
};
for (const file of ['assets/css/theme.css', 'assets/js/app.js', 'assets/js/glee-site-enhancements.js', 'assets/data/search-index.json']) {
  const data = fs.readFileSync(path.join(root, file));
  report.sourceAssets[file] = { bytes: data.length, gzipBytes: zlib.gzipSync(data).length,
    sha256: crypto.createHash('sha256').update(data).digest('hex') };
}
function save() { fs.mkdirSync(path.dirname(output), { recursive: true }); fs.writeFileSync(output, JSON.stringify(report, null, 2) + '\n'); }
const server = http.createServer((request, response) => {
  const url = new URL(request.url, 'http://localhost');
  let file = path.resolve(root, '.' + decodeURIComponent(url.pathname));
  if (file !== root && !file.startsWith(root + path.sep)) { response.writeHead(403).end(); return; }
  try {
    if (fs.statSync(file).isDirectory()) file = path.join(file, 'index.html');
    let data = fs.readFileSync(file);
    if (candidateCss && file === path.join(root,'assets/css/theme.css')) data = Buffer.concat([data,Buffer.from(candidateCss)]);
    const type = types[path.extname(file)] || 'application/octet-stream';
    const gzip = /^(text\/|application\/(json|manifest))/.test(type) && String(request.headers['accept-encoding']).includes('gzip');
    let body = data;
    if (gzip) { const key = file + fs.statSync(file).mtimeMs; if (!compressed.has(key)) compressed.set(key, zlib.gzipSync(data)); body = compressed.get(key); }
    response.writeHead(200, { 'Content-Type': type, 'Content-Length': body.length, 'Vary': 'Accept-Encoding',
      'Cache-Control': type === 'text/html' ? 'no-cache' : 'public, max-age=600', ...(gzip ? { 'Content-Encoding': 'gzip' } : {}) }).end(body);
  } catch { response.writeHead(404, {'Content-Type': 'text/plain'}).end('Not found'); }
});
async function setup(context, page, profile, blockFonts = false) {
  const cdp = await context.newCDPSession(page);
  await cdp.send('Network.enable');
  await cdp.send('Network.setBlockedURLs', { urls: ['*googletagmanager.com*', '*google-analytics.com*', ...(blockFonts ? ['*fonts.googleapis.com*', '*fonts.gstatic.com*'] : [])] });
  await cdp.send('Emulation.setCPUThrottlingRate', { rate: profile.cpu || 1 });
  if (profile.latency) await cdp.send('Network.emulateNetworkConditions', { offline: false,
    latency: profile.latency, downloadThroughput: profile.download, uploadThroughput: profile.upload });
  return cdp;
}
async function readiness(page, includeAll = false) {
  return page.evaluate(async includeAll => {
    const images = [...document.images].filter(img => includeAll || img.getBoundingClientRect().top < innerHeight);
    const results = await Promise.all(images.map(async img => {
      if (includeAll) img.loading = 'eager';
      try { await img.decode(); const bounds = img.getBoundingClientRect(); return { src: img.currentSrc || img.src, width: img.naturalWidth, height: img.naturalHeight,
        renderedWidth: bounds.width, renderedHeight: bounds.height, top: bounds.top, loading: img.loading, fetchPriority: img.fetchPriority }; }
      catch (error) { return { src: img.currentSrc || img.src, error: error.message }; }
    }));
    return results;
  }, includeAll);
}
async function completeDiagrams(page) {
  const count = await page.locator('.mermaid').count();
  const states = [];
  for (let index = 0; index < count; index++) {
    const node = page.locator('.mermaid').nth(index);
    await node.scrollIntoViewIfNeeded();
    await page.waitForFunction(index => {
      const node = document.querySelectorAll('.mermaid')[index];
      return Boolean(node?.querySelector('svg')) && !node.querySelector('.error-icon, .error-text');
    }, index, { timeout: 20000 });
    states.push(await node.evaluate(el => ({ rendered: el.dataset.mermaidRendered, svg: Boolean(el.querySelector('svg')),
      accessibleName: el.getAttribute('aria-label'), width: el.getBoundingClientRect().width,
      svgWidth: el.querySelector('svg').getBoundingClientRect().width })));
  }
  return states;
}

(async () => {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = 'http://127.0.0.1:' + server.address().port;
  report.base = base;
  const browser = await chromium.launch({ headless: true });
  report.browser = await browser.version();
  if(process.env.EXPERIENCE_CONTRAST_ONLY) {
    report.contrast=[];
    try {
      for(const system of ['light','dark']) for(const pinned of ['auto','light','dark']) for(const route of ['/','/search/?q=zzzzunmatchablequeryzzzz']) {
        const context=await browser.newContext({viewport:{width:390,height:900},colorScheme:system,serviceWorkers:'block'});
        const page=await context.newPage();await setup(context,page,{},true);await page.goto(base+route);
        const toggle=page.locator('.glee-color-toggle');await toggle.waitFor();
        for(let n=0;n<3&&await toggle.getAttribute('data-state')!==pinned;n++)await toggle.click();
        await page.waitForTimeout(500);
        const measurements=await page.evaluate(()=>{
          const luminance=color=>{const c=color.match(/[\d.]+/g).slice(0,3).map(Number).map(v=>{v/=255;return v<=0.04045?v/12.92:((v+0.055)/1.055)**2.4;});return c[0]*.2126+c[1]*.7152+c[2]*.0722;};
          return ['.glee-search-page__lede','.glee-search-page__title','.site-footer','.footer-column h3','.footer-column a','.footer-bottom'].map(selector=>{
            const el=document.querySelector(selector);if(!el)return null;const s=getComputedStyle(el);let parent=el;let backgrounds=[];
            while(parent){const p=getComputedStyle(parent);backgrounds=p.backgroundImage.match(/rgba?\([^)]+\)/g)||[];if(!backgrounds.length && p.backgroundColor!=='rgba(0, 0, 0, 0)')backgrounds=[p.backgroundColor];if(backgrounds.length)break;parent=parent.parentElement;}
            if(!backgrounds.length)backgrounds=['rgb(255,255,255)'];const fg=luminance(s.color);const contrast=Math.min(...backgrounds.map(bg=>{const b=luminance(bg);return (Math.max(fg,b)+.05)/(Math.min(fg,b)+.05);}));
            return {selector,color:s.color,backgrounds,contrast,pass:contrast>=(/title|h3/.test(selector)?3:4.5)};
          }).filter(Boolean);
        });
        const row={system,pinned,route,measurements};report.contrast.push(row);for(const m of measurements)if(!m.pass)report.failures.push({...row,measurements:undefined,...m});
        if(screenshots && system==='light' && pinned==='dark' && route.startsWith('/search/')) {fs.mkdirSync(screenshots,{recursive:true});await page.screenshot({path:path.join(screenshots,'search-pinned-dark-final.png'),fullPage:true});}
        await context.close();save();
      }
    } finally {report.finishedAt=new Date().toISOString();save();await browser.close();await new Promise(resolve=>server.close(resolve));}
    console.log(JSON.stringify({output,contrastCases:report.contrast.length,failures:report.failures.length}));process.exitCode=report.failures.length?1:0;return;
  }
  if (process.env.EXPERIENCE_LAYOUT_ONLY) {
    report.layouts = [];
    try {
      for (const scale of (process.env.EXPERIENCE_IMAGES_ONLY ? [1,2] : [1])) for (const width of [320,390,820,980,1024,1440]) {
        const context = await browser.newContext({viewport:{width,height:900},deviceScaleFactor:scale,serviceWorkers:'block'});
        const page = await context.newPage(); await setup(context,page,{},true);
        await page.goto(base + '/'); await page.waitForTimeout(900);
        report.layouts.push({kind:'homepage-images',width,scale,images:await page.evaluate(()=>[...document.images].filter(i=>i.classList.contains('glee-hero-img') || /chai/i.test(i.currentSrc||i.src)).map(i=>{const r=i.getBoundingClientRect();return {src:i.currentSrc,width:r.width,top:r.top,viewportHeight:innerHeight,naturalWidth:i.naturalWidth,loading:i.loading,fetchPriority:i.fetchPriority,sizes:i.closest('picture')?.querySelector('source')?.sizes||i.sizes};}))});
        if(process.env.EXPERIENCE_IMAGES_ONLY) {await context.close();save();continue;}
        for (const theme of ['light','dark']) {
          await page.goto(base + '/search/');
          await page.waitForFunction(()=>document.querySelector('[data-glee-search-inline-categories] button'));
          const schemeToggle=page.locator('.glee-color-toggle');
          for(let attempt=0;attempt<3 && await schemeToggle.getAttribute('data-state')!==theme;attempt++) await schemeToggle.click();
          assert.equal(await schemeToggle.getAttribute('data-state'),theme);
          const input=page.locator('[data-glee-search-inline-input]');
          for (const state of ['empty','no-results','query','category','reset']) {
            if(state==='no-results') await input.fill('zzzzunmatchablequeryzzzz');
            if(state==='query') await input.fill('seniority');
            if(state==='category') await page.locator('[data-glee-search-inline-categories] button').nth(1).click();
            if(state==='reset') {await input.fill('');await page.locator('[data-cat="all"]').click();}
            await page.waitForTimeout(250);
            const row=await page.evaluate(()=>{
              const selectors=['.glee-search-page__categories','.glee-search-page__results-wrap','.glee-search-page__shortcuts','footer'];
              return {url:location.href,actualTheme:document.documentElement.dataset.theme,actualColorScheme:document.documentElement.dataset.colorScheme,overflow:document.documentElement.scrollWidth-innerWidth,status:document.querySelector('[data-glee-search-inline-status]').textContent,
                results:document.querySelector('[data-glee-search-inline-results]').children.length,
                boxes:selectors.map(selector=>{const r=document.querySelector(selector).getBoundingClientRect();return {selector,top:r.top,bottom:r.bottom,height:r.height};})};
            });
            row.kind='search-layout';row.width=width;row.theme=theme;row.state=state;
            row.pass=row.overflow<=1 && row.boxes.slice(1).every((b,i)=>b.top>=row.boxes[i].bottom-1);
            if(!row.pass) report.failures.push(row);
            report.layouts.push(row);
            if(screenshots && width===320 && state==='no-results') {fs.mkdirSync(screenshots,{recursive:true});await page.screenshot({path:path.join(screenshots,`search-${width}-${theme}-${state}.png`),fullPage:true});}
          }
        }
        await context.close();save();
      }
    } finally {report.finishedAt=new Date().toISOString();save();await browser.close();await new Promise(resolve=>server.close(resolve));}
    console.log(JSON.stringify({output,layoutCases:report.layouts.length,failures:report.failures.length}));process.exitCode=report.failures.length?1:0;return;
  }
  try {
    if (!process.env.EXPERIENCE_ACCESSIBILITY_ONLY) for (const profile of profiles) for (const [name, route] of Object.entries(routes)) {
      if (selectedRoutes && !selectedRoutes.includes(name)) continue;
      if (process.env.EXPERIENCE_PROFILES && !process.env.EXPERIENCE_PROFILES.split(',').includes(profile.name)) continue;
      for (let repetition = 1; repetition <= repetitions; repetition++) {
        const context = await browser.newContext({ viewport: profile.viewport, serviceWorkers: 'block' });
        await context.addInitScript({content: `(${(createAccumulator => {
          const accumulator = createAccumulator();
          window.__lab = { lcp: null, cls: 0, layoutShiftTotal: 0, shifts: [], longTasks: [] };
          new PerformanceObserver(list => { for (const entry of list.getEntries()) window.__lab.lcp = { ms: entry.startTime, element: entry.element?.tagName, url: entry.url }; }).observe({ type: 'largest-contentful-paint', buffered: true });
          new PerformanceObserver(list => { for (const entry of list.getEntries()) {
            Object.assign(window.__lab, accumulator.add(entry));
            window.__lab.shifts.push({value:entry.value,startTime:entry.startTime,hadRecentInput:entry.hadRecentInput,readyState:document.readyState,sources:entry.sources.map(s=>({tag:s.node?.tagName,class:s.node?.className,parent:s.node?.parentElement?.outerHTML.slice(0,700),previous:s.previousRect.toJSON(),current:s.currentRect.toJSON()})),heroPseudo:[...document.querySelectorAll('.glee-hero-card,.hero-eyebrow,body')].map(el=>{const style=getComputedStyle(el,'::before');return {class:el.className,bounds:el.getBoundingClientRect().toJSON(),content:style.content,width:style.width,height:style.height,position:style.position,transform:style.transform,animation:style.animationName};})});
          } }).observe({ type: 'layout-shift', buffered: true });
          new PerformanceObserver(list => { for (const entry of list.getEntries()) window.__lab.longTasks.push(entry.duration); }).observe({ type: 'longtask', buffered: true });
        }).toString()})(${createLayoutShiftAccumulator.toString()});`});
        const page = await context.newPage();
        const cdp = await setup(context, page, profile);
        let resources = new Map(), pageErrors = [], consoleErrors = [];
        cdp.on('Network.requestWillBeSent', e => resources.set(e.requestId, { url: e.request.url, type: e.type }));
        cdp.on('Network.responseReceived', e => { const row = resources.get(e.requestId); if (row) Object.assign(row, { status: e.response.status, mime: e.response.mimeType, fromDiskCache: Boolean(e.response.fromDiskCache), fromServiceWorker: Boolean(e.response.fromServiceWorker) }); });
        cdp.on('Network.requestServedFromCache', e => { const row = resources.get(e.requestId); if (row) row.servedFromCache = true; });
        cdp.on('Network.loadingFinished', e => { const row = resources.get(e.requestId); if (row) row.encodedDataLength = e.encodedDataLength; });
        cdp.on('Network.loadingFailed', e => { const row = resources.get(e.requestId); if (row) row.failure = { error: e.errorText, blockedReason: e.blockedReason }; });
        page.on('pageerror', e => pageErrors.push(e.message));
        page.on('console', e => { if (e.type() === 'error' || /mermaid.*error/i.test(e.text())) consoleErrors.push({ type: e.type(), text: e.text(), location: e.location() }); });
        for (const cache of ['cold', 'repeat']) {
          resources = new Map(); pageErrors = []; consoleErrors = [];
          const row = { profile: profile.name, name, route, repetition, cache, startedAt: new Date().toISOString() };
          const sourcePath = path.join(root, new URL(base + route).pathname, 'index.html');
          row.documentSha256 = crypto.createHash('sha256').update(fs.readFileSync(sourcePath)).digest('hex');
          row.runtimeSha256 = crypto.createHash('sha256').update(fs.readFileSync(path.join(root,'assets/js/app.js'))).digest('hex');
          try {
            // Search cost probes change URL state after each measurement. Always
            // navigate to the intended URL while retaining the context's cache.
            const response = await page.goto(base + route, { waitUntil: 'load', timeout: 45000 });
            row.actualUrl = page.url();
            row.status = response.status();
            row.initialImages = await readiness(page);
            await page.evaluate(() => Promise.race([document.fonts.ready, new Promise(resolve => setTimeout(resolve, 10000))]));
            if (name === 'search') await page.waitForFunction(() => document.querySelector('[data-glee-search-inline-results] a'), null, { timeout: 20000 });
            await page.waitForTimeout(1000);
            row.initialViewport = await page.evaluate(() => ({
              ...window.__lab,
              navigation: performance.getEntriesByType('navigation').map(n => ({ domContentLoaded: n.domContentLoadedEventEnd, load: n.loadEventEnd, transferSize: n.transferSize, encodedBodySize: n.encodedBodySize }))[0],
              paint: performance.getEntriesByType('paint').map(p => ({name: p.name, ms: p.startTime})),
              fontStatus: document.fonts.status,
              fonts: [...document.fonts].map(f => ({family: f.family, status: f.status})),
              headingFont: getComputedStyle(document.querySelector('h1')).fontFamily,
              bodyFont: getComputedStyle(document.body).fontFamily,
              overflow: Math.max(document.body.scrollWidth, document.documentElement.scrollWidth) - innerWidth,
            }));
            row.initialResources = [...resources.values()];
            if (screenshots && process.env.EXPERIENCE_PERFORMANCE_SCREENSHOTS) {
              fs.mkdirSync(screenshots, {recursive:true}); row.screenshot=path.join(screenshots, `${profile.name}-${name}-${cache}-${repetition}.png`);
              await page.screenshot({path:row.screenshot});
            }
            row.allImages = await readiness(page, true);
            if (name === 'diagram') row.diagrams = await completeDiagrams(page);
            row.finalResources = [...resources.values()];
            if (name === 'search') row.searchCost = await page.evaluate(async () => {
              const raw = await (await fetch('/assets/data/search-index.json')).text();
              const parse = [];
              for (let i = 0; i < 50; i++) { const before = performance.now(); JSON.parse(raw); parse.push(performance.now() - before); }
              const input = document.querySelector('[data-glee-search-inline-input]');
              const searches = [];
              for (const query of ['resume', 'budget', 'seniority', 'scheduling']) {
                input.value = query;
                const before = performance.now(); input.dispatchEvent(new Event('input', {bubbles: true}));
                const resultCount = document.querySelectorAll('[data-glee-search-inline-results] a').length;
                document.querySelector('[data-glee-search-inline-results]').getBoundingClientRect();
                searches.push({query, scriptAndLayoutMs: performance.now() - before, resultCount});
              }
              return { decodedCharacters: raw.length, parseMs: parse, searches };
            });
            assert.equal(row.status, 200);
            assert(row.allImages.every(img => !img.error && img.width > 0), 'all images must decode after eager request');
            assert.equal(pageErrors.length, 0, 'page errors');
            assert.equal(consoleErrors.filter(e => !/fonts\.(googleapis|gstatic)\.com/.test(e.location?.url || '')).length, 0, 'unexpected console errors');
            const failures = row.finalResources.filter(r => r.url.startsWith(base) && (r.failure || r.status >= 400));
            assert.equal(failures.length, 0, JSON.stringify(failures));
            row.result = 'PASS';
          } catch (error) { row.result = 'FAIL'; row.error = error.message; report.failures.push({ area: 'performance-readiness', profile: profile.name, name, repetition, cache, error: error.message }); }
          row.resources = [...resources.values()]; row.pageErrors = [...pageErrors]; row.consoleErrors = [...consoleErrors];
          report.performance.push(row); save(); console.log(`${row.result} ${profile.name} ${name} ${cache} sample ${repetition}`);
        }
        await context.close();
      }
    }
    if (!process.env.EXPERIENCE_PERFORMANCE_ONLY) for (const condition of [
      { name: 'reflow-320', viewport: {width: 320, height: 900} },
      { name: '200-percent-equivalent-640', viewport: {width: 640, height: 450}, deviceScaleFactor: 2 },
      { name: 'reduced-motion', viewport: {width: 1280, height: 900}, reducedMotion: 'reduce' },
      { name: 'forced-colors', viewport: {width: 1280, height: 900}, forcedColors: 'active' },
    ]) {
      for (const [name, route] of Object.entries({...routes, universe: '/universe/'})) {
        const { name: conditionName, ...options } = condition;
        const context = await browser.newContext({...options, serviceWorkers: 'block'});
        const page = await context.newPage();
        await setup(context, page, {}, true);
        const row = {condition: conditionName, name, route, checks: [], errors: []};
        page.on('pageerror', e => row.errors.push(e.message));
        const record = (check, pass, evidence) => { row.checks.push({check, pass, evidence}); if (!pass) report.failures.push({area: 'accessibility', condition: conditionName, name, check, evidence}); };
        try {
          const response = await page.goto(base + route, {waitUntil: 'load', timeout: 25000});
          record('page identity and content', response.status() === 200 && await page.locator('main h1').count() === 1, {status: response.status(), title: await page.title()});
          const images = await readiness(page, true);
          record('all images decode', images.every(i => !i.error && i.width > 0), images);
          if (await page.locator('.mermaid').count()) row.diagrams = await completeDiagrams(page);
          const overflow = await page.evaluate(() => ({ pixels: Math.max(document.body.scrollWidth, document.documentElement.scrollWidth) - innerWidth,
            offenders: [...document.querySelectorAll('main *')].filter(el => el.getBoundingClientRect().right > innerWidth + 1 && getComputedStyle(el).overflowX !== 'auto').slice(0, 10).map(el => ({tag: el.tagName, class: el.className?.baseVal || el.className, right: el.getBoundingClientRect().right})) }));
          record('reflow without document overflow', overflow.pixels <= 1, overflow);
          await page.evaluate(() => scrollTo(0, 0));
          await page.keyboard.press('Tab');
          const skip = page.locator('.skip-to-content');
          await skip.focus(); await page.keyboard.press('Enter');
          await page.waitForTimeout(400);
          const afterSkip = await page.evaluate(() => ({hash: location.hash, active: document.activeElement.tagName,
            activeId: document.activeElement.id, mainFocused: document.querySelector('main') === document.activeElement,
            focusInsideMain: document.querySelector('main').contains(document.activeElement)}));
          await page.keyboard.press('Tab');
          const nextFocus = await page.evaluate(() => ({tag: document.activeElement.tagName, href: document.activeElement.getAttribute('href'),
            insideMain: document.querySelector('main').contains(document.activeElement)}));
          record('skip link moves focus and next Tab into main', (afterSkip.mainFocused || afterSkip.focusInsideMain) && nextFocus.insideMain, {afterSkip, nextFocus});
          if (name === 'home') {
            const toggle = page.locator('.nav-toggle');
            if (await toggle.isVisible()) {
              await toggle.focus(); await page.keyboard.press('Enter');
              await page.waitForTimeout(400);
              record('keyboard opens navigation', await toggle.getAttribute('aria-expanded') === 'true');
              await page.keyboard.press('Escape');
              record('Escape closes navigation and returns focus', await toggle.getAttribute('aria-expanded') === 'false' && await toggle.evaluate(el => el === document.activeElement));
            }
            const search = page.locator('.okh-search-trigger');
            await search.focus(); await page.keyboard.press('Enter');
            await page.waitForTimeout(100);
            const input = page.locator('.okh-search-input');
            record('search receives focus', await input.evaluate(el => el === document.activeElement));
            await page.keyboard.press('Shift+Tab');
            record('search focus trap loops within dialog', await page.evaluate(() => document.querySelector('.okh-search-overlay').contains(document.activeElement)));
            await page.keyboard.press('Escape');
            record('search closes and returns focus', await search.evaluate(el => el === document.activeElement));
            const focus = await search.evaluate(el => { const s = getComputedStyle(el); return {outlineStyle: s.outlineStyle, outlineWidth: s.outlineWidth, outlineColor: s.outlineColor, color: s.color, background: s.backgroundColor}; });
            record('visible keyboard focus outline', focus.outlineStyle !== 'none' && parseFloat(focus.outlineWidth) > 0, focus);
          }
          if (conditionName === 'reduced-motion') {
            const running = await page.evaluate(() => document.getAnimations().filter(a => a.playState === 'running' && a.effect?.getTiming().duration > 1).map(a => ({target: a.effect.target.tagName, class: a.effect.target.className, duration: a.effect.getTiming().duration})));
            record('no long running animation under reduced motion', running.length === 0, running);
            const durations = await page.evaluate(() => [...document.querySelectorAll('h1,.brand-stripes,.reveal-on-scroll,.nav-toggle')].map(el => {
              const s=getComputedStyle(el); return {tag:el.tagName, animationName:s.animationName, animationDuration:s.animationDuration, transitionDuration:s.transitionDuration, scrollBehavior:s.scrollBehavior};
            }));
            record('reduced motion duration and scroll styles', durations.every(s => s.animationDuration.split(',').every(t=>parseFloat(t)<=0.001) && s.transitionDuration.split(',').every(t=>parseFloat(t)<=0.001) && s.scrollBehavior==='auto'), durations);
          }
          if (conditionName === 'forced-colors') {
            const states = await page.evaluate(() => ({ active: matchMedia('(forced-colors: active)').matches,
              buttons: [...document.querySelectorAll('button')].filter(b => b.getBoundingClientRect().width).slice(0,10).map(b => {const s=getComputedStyle(b); return {label:b.getAttribute('aria-label')||b.textContent, color:s.color, background:s.backgroundColor, border:s.borderColor};}) }));
            record('forced colors active with named controls', states.active && states.buttons.every(b => b.label.trim()), states);
          }
          record('no page errors', row.errors.length === 0, row.errors);
          if (screenshots && (name === 'home' || name === 'diagram')) {
            fs.mkdirSync(screenshots, {recursive: true});
            row.screenshot = path.join(screenshots, `${conditionName}-${name}.png`);
            await page.screenshot({path: row.screenshot});
          }
        } catch (error) { row.error = error.message; report.failures.push({area:'accessibility', condition:conditionName, name, error:error.message}); }
        report.accessibility.push(row); save(); console.log(`CHECKED ${conditionName} ${name}`); await context.close();
      }
    }
  } finally { report.finishedAt = new Date().toISOString(); save(); await browser.close(); await new Promise(resolve => server.close(resolve)); }
  console.log(JSON.stringify({ output, performanceCases: report.performance.length, accessibilityCases: report.accessibility.length, failures: report.failures.length }));
  process.exitCode = report.failures.length ? 1 : 0;
})().catch(error => { report.fatal = error.stack; save(); console.error(error); process.exitCode = 1; server.close(); });
}

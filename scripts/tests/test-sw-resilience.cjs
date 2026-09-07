// Deterministic production-worker regressions; no browser or dependencies needed.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');
const source = fs.readFileSync(path.join(__dirname, '../../sw.js'), 'utf8');
const origin = 'https://glee-fully.tools';
const enhancementUrl = source.match(/\/assets\/js\/glee-site-enhancements\.js(?:\?v=[^"']+)?/)[0];

function harness(options = {}) {
  const handlers = {};
  const entries = new Map();
  const deleted = [];
  const key = (request) => new URL(typeof request === 'string' ? request : request.url, origin).href;
  const response = (label) => ({ ok: true, type: 'basic', label,
    headers: { get: () => 'text/html; charset=utf-8' }, clone() { return response(label); } });
  entries.set(key('/offline.html'), response('offline'));
  const cache = {
    async match(request) {
      if (options.readFailure) throw new Error('Storage unavailable');
      return entries.get(key(request));
    },
    async put(request, value) {
      if (options.writeFailure) throw new Error('QuotaExceededError');
      entries.set(key(request), value);
    },
    async keys() { return [...entries.keys()].map(url => ({ url })); },
    async delete(request) { return entries.delete(key(request)); },
    async addAll(urls) { for (const url of urls) entries.set(key(url), response(url)); },
  };
  const context = {
    URL, Response,
    self: { location: { origin }, clients: { async claim() {} },
      addEventListener(name, handler) { handlers[name] = handler; } },
    caches: {
      async open() { if (options.openFailure) throw new Error('Storage unavailable'); return cache; },
      async match(request) { if (options.readFailure) throw new Error('Storage unavailable'); return cache.match(request); },
      async keys() { return ['glee-fully-shell-v1', 'other-app']; },
      async delete(name) { deleted.push(name); },
    },
    async fetch(request) { if (options.offline) throw new Error('Offline'); return response(request.url || request); },
  };
  vm.runInNewContext(source, context);
  return { entries, deleted, handlers, options,
    async request(route, mode = 'navigate') {
      const work = [];
      let result;
      handlers.fetch({ request: { url: key(route), mode, method: 'GET' },
        waitUntil(promise) { work.push(promise); }, respondWith(promise) { result = promise; } });
      const value = await result;
      await Promise.all(work);
      return value;
    },
    async lifecycle(name) {
      let work;
      handlers[name]({ waitUntil(promise) { work = promise; } });
      await work;
    },
  };
}

for (const failure of ['writeFailure', 'openFailure', 'readFailure']) {
  test(`online navigation survives ${failure}`, async () => {
    const worker = harness({ [failure]: true });
    const result = await worker.request('/toolbox/01-discovered-careers/');
    assert.equal(result.label, origin + '/toolbox/01-discovered-careers/');
  });
}

test('query variants share one cached shell and work offline with a new query', async () => {
  const worker = harness();
  for (let i = 0; i < 150; i++) await worker.request(`/search/?q=${i}&utm_source=test`);
  assert.equal(worker.entries.size, 2);
  assert.ok(worker.entries.has(origin + '/search/'));
  worker.options.offline = true;
  assert.notEqual((await worker.request('/search/?q=brand-new')).label, 'offline');
});

test('runtime cache growth is bounded while the offline shell survives', async () => {
  const worker = harness();
  await Promise.all(Array.from({ length: 150 }, (_, i) => worker.request(
    `/toolbox/01-discovered-careers/01a-example-${i}/`)));
  assert.ok(worker.entries.size <= 81, `unbounded entries: ${worker.entries.size}`);
  assert.ok(worker.entries.has(origin + '/offline.html'));
});

test('non-public paths are not retained and third-party requests are not intercepted', async () => {
  const worker = harness();
  await worker.request('/docs/private-notes.html?draft=yes');
  assert.equal(worker.entries.size, 1);
  assert.equal(await worker.request('https://example.com/'), undefined);
});

test('missing precached assets still use successful network when storage fails', async () => {
  const worker = harness({ openFailure: true, readFailure: true });
  assert.equal((await worker.request('/assets/data/search-index.json', 'cors')).label,
    origin + '/assets/data/search-index.json');
});

test('cold offline shell includes the dynamically loaded Glee adapter', async () => {
  const worker = harness();
  await worker.lifecycle('install');
  worker.options.offline = true;
  assert.ok(await worker.request(enhancementUrl, 'cors'));
});

test('activation deletes only stale Glee cache namespaces', async () => {
  const worker = harness();
  await worker.lifecycle('activate');
  assert.deepEqual(worker.deleted, ['glee-fully-shell-v1']);
});

for (const route of ['/foundry/', '/foundry/index.html']) {
  test(`visited FoundRy page is available offline: ${route}`, async () => {
    const worker = harness();
    await worker.request(route);
    assert.ok(worker.entries.has(origin + "/foundry/"));
    worker.options.offline = true;
    assert.equal((await worker.request(route)).label, origin + route);
  });
}

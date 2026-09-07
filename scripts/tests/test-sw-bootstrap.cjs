// Registration must work whether the dynamically imported adapter beats load or not.
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const vm = require('node:vm');
const source = readFileSync(resolve(__dirname, '../../assets/js/glee-site-enhancements.js'), 'utf8');
let failures = 0;
for (const readyState of ['loading', 'interactive', 'complete']) {
  let listener;
  const registrations = [];
  const context = {
    localStorage: { getItem: () => null },
    fetch: async () => ({ ok: false }),
    document: { readyState, querySelectorAll: () => [] },
    navigator: { serviceWorker: { register: (url, options) => {
      registrations.push({ url, scope: options.scope });
      return Promise.resolve({});
    } } },
    window: { addEventListener: (name, callback, options) => { listener = { name, callback, options }; } },
  };
  try {
    vm.runInNewContext(source, context);
    if (readyState === 'complete') {
      assert.equal(registrations.length, 1, 'late import must register without a second load event');
      assert.equal(listener, undefined);
    } else {
      assert.equal(registrations.length, 0);
      assert.equal(listener.name, 'load');
      assert.equal(listener.options?.once, true, 'early import needs one load handler');
      listener.callback();
    }
    assert.deepEqual(registrations, [{ url: '/sw.js', scope: '/' }]);
    console.log('PASS service-worker bootstrap at ' + readyState);
  } catch (error) { failures++; console.error('FAIL ' + readyState + ': ' + error.message); }
}
process.exitCode = failures ? 1 : 0;

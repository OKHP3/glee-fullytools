const assert = require('node:assert/strict');
const { test } = require('node:test');
const { pathToFileURL } = require('node:url');
const { resolve } = require('node:path');
const helper = import(pathToFileURL(resolve(__dirname, 'focus-geometry.mjs')));
const viewport = { width: 390, height: 844 };
const visibleBox = { x: 0, y: 0, width: 175, height: 47 };
const ready = { focused: true, settled: true, visible: true, rect: visibleBox };

function fixture(states, boxes) {
  let reads = 0;
  const link = {
    async evaluate() { return states[Math.min(reads, states.length - 1)]; },
    async boundingBox() { return boxes[Math.min(reads++, boxes.length - 1)]; },
  };
  return { page: { locator: () => link }, reads: () => reads };
}

test('waits for compositor geometry after DOM geometry reaches zero', async () => {
  const { waitForFocusedSkipLink } = await helper;
  const f = fixture([ready], [{ ...visibleBox, y: -0.0079 }, visibleBox]);
  const evidence = await waitForFocusedSkipLink(f.page, viewport);
  assert.deepEqual(evidence.box, visibleBox);
  assert.equal(f.reads(), 2);
});

test('waits for the slide transition to finish even with visible geometry', async () => {
  const { waitForFocusedSkipLink } = await helper;
  const f = fixture([{ ...ready, settled: false }, ready], [visibleBox]);
  await waitForFocusedSkipLink(f.page, viewport);
  assert.equal(f.reads(), 2);
});

for (const [name, state, box] of [
  ['off-screen link', ready, { ...visibleBox, y: -0.001 }],
  ['lost keyboard focus', { ...ready, focused: false }, visibleBox],
  ['hidden link', { ...ready, visible: false }, visibleBox],
  ['missing layout box', ready, null],
  ['unfinished transition', { ...ready, settled: false }, visibleBox],
]) {
  test(`rejects ${name} within its bounded deadline`, async () => {
    const { waitForFocusedSkipLink } = await helper;
    const f = fixture([state], [box]);
    await assert.rejects(waitForFocusedSkipLink(f.page, viewport, { timeout: 40 }),
                         /focused skip link did not settle on screen/);
  });
}

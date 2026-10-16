import { setTimeout as delay } from 'node:timers/promises';

// Firefox can round the DOM rect to zero while its compositor still reports a
// negative fractional position near the end of the skip-link slide transition.
// Keep strict bounds and wait for both the animation and actual box to settle.
export async function waitForFocusedSkipLink(page, viewport, { timeout = 2000 } = {}) {
  const skip = page.locator('.skip-to-content');
  const deadline = Date.now() + timeout;
  const onScreen = box => box && box.width > 0 && box.height > 0 &&
    box.x >= 0 && box.y >= 0 &&
    box.x + box.width <= viewport.width && box.y + box.height <= viewport.height;
  let evidence;
  do {
    const state = await skip.evaluate(node => {
      const style = getComputedStyle(node);
      const rect = node.getBoundingClientRect();
      return {
        focused: node === document.activeElement,
        settled: node.getAnimations().every(animation =>
          animation.playState === 'finished' || animation.playState === 'idle'),
        visible: style.visibility === 'visible' && style.display !== 'none',
        rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
      };
    });
    const box = await skip.boundingBox();
    evidence = { ...state, box };
    if (state.focused && state.settled && state.visible && onScreen(state.rect) && onScreen(box)) {
      return evidence;
    }
    // Poll actual state; elapsed time alone never makes a failed check pass.
    await delay(16);
  } while (Date.now() < deadline);
  throw new Error(`focused skip link did not settle on screen: ${JSON.stringify(evidence)}`);
}

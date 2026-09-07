const { test } = require('node:test');
const assert = require('node:assert/strict');
const { createLayoutShiftAccumulator } = require('./test-experience-performance.cjs');
function measure(entries) {
  const accumulator = createLayoutShiftAccumulator();
  for (const entry of entries) accumulator.add({ hadRecentInput: false, ...entry });
  return accumulator.snapshot();
}
function near(actual, expected) { assert(Math.abs(actual - expected) < 1e-10, `${actual} != ${expected}`); }
test('separated bursts select their maximum instead of lifetime total', () => {
  const result = measure([{startTime:0,value:.1},{startTime:500,value:.2},{startTime:2000,value:.25}]);
  near(result.cls,.3); near(result.layoutShiftTotal,.55);
});
test('a gap strictly below one second joins; exactly one second resets', () => {
  near(measure([{startTime:0,value:.1},{startTime:999,value:.2}]).cls,.3);
  near(measure([{startTime:0,value:.1},{startTime:1000,value:.2}]).cls,.2);
});
test('window duration strictly below five seconds joins; exactly five seconds resets', () => {
  const chain = [0,900,1800,2700,3600,4500].map(startTime=>({startTime,value:.1}));
  near(measure([...chain,{startTime:4999,value:.2}]).cls,.8);
  near(measure([...chain,{startTime:5000,value:.2}]).cls,.6);
});
test('recent input is excluded and cannot bridge two separate windows', () => {
  const result=measure([{startTime:0,value:.2},{startTime:900,value:5,hadRecentInput:true},{startTime:1800,value:.3}]);
  near(result.cls,.3); near(result.layoutShiftTotal,.5);
});
test('later smaller windows do not replace maximum; a larger one does', () => {
  const accumulator=createLayoutShiftAccumulator();
  accumulator.add({startTime:0,value:.4});
  accumulator.add({startTime:2000,value:.1});
  near(accumulator.snapshot().cls,.4);
  accumulator.add({startTime:2200,value:.5});
  near(accumulator.snapshot().cls,.6); near(accumulator.snapshot().layoutShiftTotal,1);
});
test('empty and entirely input-driven observations stay zero', () => {
  assert.deepEqual(measure([]),{cls:0,layoutShiftTotal:0});
  assert.deepEqual(measure([{startTime:0,value:1,hadRecentInput:true}]),{cls:0,layoutShiftTotal:0});
});

const assert = require('node:assert/strict');
const Timeline = require('./segments.js');

function valid(points, duration) {
  assert.equal(points[0], 0);
  assert.equal(points.at(-1), duration);
  const clips = Timeline.clips(points, []);
  assert.ok(clips.every(c => c.end > c.start));
  for (let i = 1; i < clips.length; i++) assert.equal(clips[i - 1].end, clips[i].start);
  assert.ok(Math.abs(clips.reduce((sum, c) => sum + c.end - c.start, 0) - duration) < 1e-8);
}

assert.deepEqual(Timeline.split(30, 10), [0, 10, 20, 30]);
assert.deepEqual(Timeline.split(32.5, 10), [0, 10, 20, 30, 32.5]);
assert.deepEqual(Timeline.split(3, 10), [0, 3]);
assert.equal(Timeline.split(.3, .1).length, 4);
assert.throws(() => Timeline.split(30, 0));
let points = Timeline.boundary([0, 10, 20, 30], 1, 8);
points = Timeline.boundary(points, 2, 23);
assert.deepEqual(points, [0, 8, 23, 30]);
assert.deepEqual(Timeline.move(points, 1, 2), [0, 10, 25, 30]);
assert.deepEqual(Timeline.move(points, 0, 3), points);
assert.deepEqual(Timeline.boundary(points, 0, 3), points);
assert.deepEqual(Timeline.boundary(points, 3, 25), points);
assert.deepEqual(Timeline.boundary([0, 10, 20, 30, 40], 2, 18), [0, 10, 18, 30, 40]);
let seed = 527;
const random = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 2 ** 32);
for (const duration of [.015, .3, 10, 30, 156.8135, 3600]) {
  let state = Timeline.split(duration, Math.min(10, duration / 3));
  for (let i = 0; i < 300; i++) {
    const index = 1 + Math.floor(random() * (state.length - 2));
    state = Timeline.boundary(state, index, (random() * 3 - 1) * duration);
    valid(state, duration);
    const block = Math.floor(random() * (state.length - 1));
    const before = state[block + 1] - state[block];
    state = Timeline.move(state, block, (random() - .5) * duration);
    valid(state, duration);
    assert.ok(Math.abs(state[block + 1] - state[block] - before) < 1e-8);
  }
}
console.log('PASS: tail segments, fractional split, boundary edits, fixed endpoints, block length and gap-free coverage through 3,600 edits');

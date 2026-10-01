'use strict';

const Timeline = {
  split(duration, seconds) {
    if (!Number.isFinite(duration) || duration <= 0 || !Number.isFinite(seconds) || seconds <= 0) {
      throw new Error('분할 길이는 0보다 큰 숫자로 입력해주세요.');
    }
    const points = [0];
    for (let i = 1; i * seconds < duration - 1e-8; i++) points.push(i * seconds);
    points.push(duration);
    return points;
  },
  boundary(points, index, time) {
    if (index <= 0 || index >= points.length - 1 || !Number.isFinite(time)) return points.slice();
    const out = points.slice();
    const gap = Math.min(.01, (points[index + 1] - points[index - 1]) / 3);
    out[index] = Math.max(points[index - 1] + gap, Math.min(time, points[index + 1] - gap));
    return out;
  },
  move(points, index, delta) {
    const out = points.slice();
    if (index <= 0 || index >= points.length - 2 || !Number.isFinite(delta)) return out;
    const gap = Math.min(.01, (points[index] - points[index - 1]) / 2, (points[index + 2] - points[index + 1]) / 2);
    const shift = Math.max(points[index - 1] + gap - points[index], Math.min(delta, points[index + 2] - gap - points[index + 1]));
    out[index] += shift;
    out[index + 1] += shift;
    return out;
  },
  clips(points, names) {
    return points.slice(0, -1).map((start, i) => ({start, end: points[i + 1], name: names[i] || '블록 ' + String(i + 1).padStart(2, '0')}));
  }
};
if (typeof module !== 'undefined') module.exports = Timeline;

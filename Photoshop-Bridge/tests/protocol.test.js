const {test} = require("node:test");
const assert = require("node:assert/strict");
const {padPixels, applyMask, makePrompt, resultNames} = require("../plugin/protocol.js");
const template = require("../plugin/pro-template.json");

test("trimmed RGBA layer returns to its original document coordinates", () => {
  const actual = padPixels(new Uint8Array([10, 20, 30, 128]), 1, 1, 4, {left: 2, top: 1}, 4, 3);
  assert.deepEqual([...actual.slice(24, 28)], [10, 20, 30, 128]);
  assert.equal(actual.filter(x => x !== 0).length, 4);
});
test("off-canvas pixels clip without shifting visible content", () => {
  const actual = padPixels(new Uint8Array([1, 2, 3, 4, 5, 6]), 2, 1, 3, {left: -1, top: 0}, 2, 1);
  assert.deepEqual([...actual], [4, 5, 6, 255, 0, 0, 0, 0]);
});
test("feathered selection multiplies alpha, preserving unselected transparency", () => {
  const rgba = new Uint8Array([1, 2, 3, 200, 4, 5, 6, 255, 7, 8, 9, 128]);
  assert.deepEqual([...applyMask(rgba, new Uint8Array([0, 128, 255]))], [1, 2, 3, 0, 4, 5, 6, 128, 7, 8, 9, 128]);
});
test("roundtrip carries opacity separately from selection", () => {
  const graph = makePrompt({}, {workflow: "roundtrip"}, {main: {name: "TooBusyPS/a.png", selection: "TooBusyPS/m.png"}});
  assert.deepEqual(graph["2"].inputs.alpha, ["1", 2]);
  assert.equal(graph["1"].inputs.selection, "TooBusyPS/m.png");
});
test("Pro adaptation keeps source immutable and does not silently invent reference inputs", () => {
  const before = JSON.stringify(template);
  const main = {name: "TooBusyPS/a.png"};
  assert.throws(() => makePrompt(template, {depth: true}, {main}), /참조/);
  assert.throws(() => makePrompt(template, {inpaint: true}, {main}), /선택/);
  const graph = makePrompt(template, {workflow: "pro", prompt: "한글 프롬프트", negative: "흐림", lineart: true, seed: 7, steps: 12, cfg: 5.5, denoise: 1}, {main});
  assert.equal(graph["4"].class_type, "TooBusyPhotoshopInput");
  assert.equal(graph["12"].class_type, "TooBusyPhotoshopOutput");
  assert.equal(graph["2"].inputs.text, "한글 프롬프트");
  assert.equal(graph["1"].inputs.ckpt_name, template["1"].inputs.ckpt_name);
  assert.equal(JSON.stringify(template), before);
});
test("only dedicated output images are offered for Photoshop import", () => {
  assert.deepEqual(resultNames({outputs: {"12": {images: [
    {type: "output", subfolder: "TooBusyPS", filename: "a.png"},
    {type: "output", subfolder: "TooBusyPS/test", filename: "b.png"},
    {type: "output", subfolder: "other", filename: "c.png"},
    {type: "temp", subfolder: "TooBusyPS", filename: "d.png"}
  ]}}}), ["a.png", "test/b.png"]);
});

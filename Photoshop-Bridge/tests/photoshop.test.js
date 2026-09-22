const {test} = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const protocol = require("../plugin/protocol.js");

function harness({selection = false, failPut = false} = {}) {
  const calls = [];
  const original = {id: 10, title: "원본.psd", width: 3, height: 2, activeLayers: [{id: 11, name: "선화"}], selection: {bounds: selection ? {left: 1, top: 0, right: 3, bottom: 1} : null}, createLayer: async () => ({id: 12})};
  const other = {...original, id: 20, title: "다른 문서"};
  const app = {documents: [original, other], activeDocument: original};
  app.documents.add = async (options) => { calls.push(["add", options]); return {...original, id: 30}; };
  const data = (bytes, width, height, components) => ({width, height, components, componentSize: 8, getData: async () => Uint8Array.from(bytes), dispose: () => calls.push(["dispose"])});
  const imaging = {
    getPixels: async () => ({imageData: data([11, 22, 33, 128], 1, 1, 4), sourceBounds: {left: 2, top: 1}}),
    getSelection: async () => ({imageData: data([0, 128], 2, 1, 1), sourceBounds: {left: 1, top: 0}}),
    createImageDataFromBuffer: async (bytes, options) => ({bytes, options, dispose: () => {}}),
    putPixels: async (options) => { calls.push(["put", options]); if (failPut) throw new Error("host failure"); }
  };
  const core = {executeAsModal: async (fn) => fn({hostControl: {suspendHistory: async () => 100, resumeHistory: async (id, commit) => calls.push(["history", commit])}})};
  const sandbox = {module: {exports: {}}, require: name => name === "photoshop" ? {app, core, imaging} : name === "uxp" ? {storage: {}} : protocol, Uint8Array};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../plugin/photoshop.js"), "utf8"), sandbox);
  return {adapter: sandbox.module.exports, app, original, other, calls};
}

test("Photoshop adapter pads cropped layer and selection into document space", async () => {
  const h = harness({selection: true});
  const snapshot = await h.adapter.capture("layer");
  assert.equal(snapshot.documentID, 10);
  assert.deepEqual([...snapshot.pixels.slice(20)], [11, 22, 33, 128]);
  assert.deepEqual([...snapshot.selection], [0, 0, 128, 0, 0, 0]);
  assert.equal(h.calls.filter(x => x[0] === "dispose").length, 2);
});
test("canvas result targets the synced document even after active document changes", async () => {
  const h = harness(); h.app.activeDocument = h.other;
  const result = {label: "test", input: {documentID: 10, canvasWidth: 3, canvasHeight: 2, width: 3, height: 2}};
  await h.adapter.applyResult("canvas", result, async () => ({width: 3, height: 2, data: new Uint8Array(24)}));
  assert.equal(h.calls.find(x => x[0] === "put")[1].documentID, 10);
  assert.deepEqual(h.calls.find(x => x[0] === "history"), ["history", true]);
});
test("canvas resize is rejected before result download or layer mutation", async () => {
  const h = harness();
  const result = {input: {documentID: 10, canvasWidth: 6, canvasHeight: 2}};
  await assert.rejects(() => h.adapter.applyResult("canvas", result, async () => { throw new Error("must not download"); }), /크기/);
  assert.equal(h.calls.length, 0);
});
test("selection application uses feather mask and original selection offset", async () => {
  const h = harness({selection: true});
  await h.adapter.applyResult("selection", {label: "test"}, async () => ({width: 2, height: 1, data: Uint8Array.from([1, 2, 3, 255, 4, 5, 6, 255])}));
  const put = h.calls.find(x => x[0] === "put")[1];
  assert.equal(put.targetBounds.left, 1);
  assert.equal(put.targetBounds.top, 0);
  assert.deepEqual([...put.imageData.bytes], [1, 2, 3, 0, 4, 5, 6, 128]);
});
test("host write failure rolls back the new layer history", async () => {
  const h = harness({failPut: true});
  const result = {label: "test", input: {documentID: 10, canvasWidth: 3, canvasHeight: 2, width: 3, height: 2}};
  await assert.rejects(() => h.adapter.applyResult("canvas", result, async () => ({width: 3, height: 2, data: new Uint8Array(24)})), /host failure/);
  assert.deepEqual(h.calls.find(x => x[0] === "history"), ["history", false]);
});

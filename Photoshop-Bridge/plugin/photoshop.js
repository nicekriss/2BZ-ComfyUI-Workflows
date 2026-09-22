const {app, core, imaging} = require("photoshop");
const {storage} = require("uxp");
const {padPixels, applyMask} = require("./protocol.js");
const MAX_PIXELS = 16777216;

function sizeCheck(width, height) {
  if (width < 1 || height < 1 || width * height > MAX_PIXELS) throw new Error("개발본은 최대 1,677만 픽셀까지 지원합니다. 입력 크기를 줄여주세요.");
}
function activeDocument() {
  if (!app.documents.length) throw new Error("포토샵 문서를 먼저 열어주세요.");
  return app.activeDocument;
}
function docMeta(doc) {
  return {documentID: doc.id, documentName: doc.title, canvasWidth: doc.width, canvasHeight: doc.height};
}
async function readData(image) {
  try {
    const data = await image.getData({chunky: true, fullRange: true});
    if (image.componentSize === 8) return new Uint8Array(data);
    const scale = image.componentSize === 16 ? 255 / 65535 : 255;
    return Uint8Array.from(data, (value) => Math.round(Math.max(0, Math.min(255, value * scale))));
  }
  finally { image.dispose(); }
}
async function capture(source) {
  if (source === "file") {
    const file = await storage.localFileSystem.getFileForOpening({types: ["png", "jpg", "jpeg", "webp"]});
    if (!file) return null;
    const meta = app.documents.length ? docMeta(app.activeDocument) : {};
    return {...meta, source, label: file.name, fileBytes: await file.read({format: storage.formats.binary})};
  }
  return core.executeAsModal(async () => {
    const doc = activeDocument();
    sizeCheck(doc.width, doc.height);
    const meta = docMeta(doc);
    const bounds = {left: 0, top: 0, right: doc.width, bottom: doc.height};
    const options = {documentID: doc.id, sourceBounds: bounds, colorSpace: "RGB", colorProfile: "sRGB IEC61966-2.1", componentSize: 8, applyAlpha: false};
    let label = doc.title;
    if (source === "layer") {
      if (doc.activeLayers.length !== 1) throw new Error("입력으로 보낼 레이어를 하나만 선택하세요.");
      options.layerID = doc.activeLayers[0].id;
      label += " / " + doc.activeLayers[0].name;
    }
    const captured = await imaging.getPixels(options);
    const image = captured.imageData;
    const width = image.width, height = image.height, components = image.components;
    const pixels = padPixels(await readData(image), width, height, components, captured.sourceBounds, doc.width, doc.height);
    let selection = null;
    if (doc.selection.bounds) {
      const selected = await imaging.getSelection({documentID: doc.id, sourceBounds: bounds});
      const mask = selected.imageData;
      const mw = mask.width, mh = mask.height;
      selection = padPixels(await readData(mask), mw, mh, 1, selected.sourceBounds, doc.width, doc.height);
    }
    return {...meta, source, label, width: doc.width, height: doc.height, pixels, selection};
  }, {commandName: "TooBusy 입력 싱크"});
}

async function selectionTarget() {
  return core.executeAsModal(async () => {
    const doc = activeDocument();
    const bounds = doc.selection.bounds;
    if (!bounds) throw new Error("결과를 넣을 선택 영역을 먼저 만드세요.");
    const box = {left: Math.floor(bounds.left), top: Math.floor(bounds.top), right: Math.ceil(bounds.right), bottom: Math.ceil(bounds.bottom)};
    const width = box.right - box.left, height = box.bottom - box.top;
    sizeCheck(width, height);
    const selected = await imaging.getSelection({documentID: doc.id, sourceBounds: box});
    const data = selected.imageData;
    const mw = data.width, mh = data.height;
    const offset = {left: selected.sourceBounds.left - box.left, top: selected.sourceBounds.top - box.top};
    const mask = padPixels(await readData(data), mw, mh, 1, offset, width, height);
    return {...docMeta(doc), bounds: box, width, height, mask};
  }, {commandName: "TooBusy 선택 영역 확인"});
}

function findDocument(id) {
  for (let i = 0; i < app.documents.length; i++) if (app.documents[i].id === id) return app.documents[i];
  throw new Error("입력 문서가 닫혔습니다. 새 이미지로 열거나 현재 선택 영역에 넣어주세요.");
}

async function applyResult(mode, result, fetchPixels) {
  let target = null;
  if (mode === "selection") target = await selectionTarget();
  else if (mode === "canvas") {
    const doc = findDocument(result.input.documentID);
    if (doc.width !== result.input.canvasWidth || doc.height !== result.input.canvasHeight) throw new Error("입력 문서 크기가 바뀌었습니다. 새 이미지로 열거나 다시 싱크하세요.");
    target = {...docMeta(doc), width: result.input.width, height: result.input.height, bounds: {left: 0, top: 0}};
  }
  const pixels = await fetchPixels(result, target && target.width, target && target.height);
  if (target && target.mask) applyMask(pixels.data, target.mask);
  await core.executeAsModal(async (context) => {
    let doc;
    if (mode === "new") {
      doc = await app.documents.add({width: pixels.width, height: pixels.height, resolution: 72, mode: "RGBColorMode", fill: "transparent", name: "TooBusy 결과"});
    } else {
      doc = findDocument(target.documentID);
      if (doc.width !== target.canvasWidth || doc.height !== target.canvasHeight) throw new Error("처리 중 문서 크기가 바뀌었습니다. 다시 적용하세요.");
    }
    const suspension = await context.hostControl.suspendHistory({documentID: doc.id, name: "TooBusy 결과 적용"});
    let image;
    let success = false;
    try {
      const layer = await doc.createLayer({name: "TooBusy · " + result.label});
      image = await imaging.createImageDataFromBuffer(pixels.data, {width: pixels.width, height: pixels.height, components: 4, colorSpace: "RGB", colorProfile: "sRGB IEC61966-2.1"});
      await imaging.putPixels({documentID: doc.id, layerID: layer.id, imageData: image, replace: true, targetBounds: target ? {left: target.bounds.left, top: target.bounds.top} : {left: 0, top: 0}});
      success = true;
    } finally {
      if (image) image.dispose();
      await context.hostControl.resumeHistory(suspension, success);
    }
  }, {commandName: "TooBusy 결과 적용"});
}

module.exports = {capture, applyResult};

/* Pure data operations; also run under Node's test runner. */
const {applyRecipe, migrateRecipe} = require("./model-settings.js");
const {applyInpaint} = require("./inpaint.js");
function padPixels(bytes, width, height, components, bounds, canvasWidth, canvasHeight) {
  if (bytes.length !== width * height * components) throw new Error("픽셀 길이가 맞지 않습니다.");
  if (![1, 3, 4].includes(components)) throw new Error("지원하지 않는 채널 수입니다.");
  const outComponents = components === 1 ? 1 : 4;
  const out = new Uint8Array(canvasWidth * canvasHeight * outComponents);
  const left = Math.round(bounds.left), top = Math.round(bounds.top);
  for (let y = 0; y < height; y++) {
    const dy = y + top;
    if (dy < 0 || dy >= canvasHeight) continue;
    for (let x = 0; x < width; x++) {
      const dx = x + left;
      if (dx < 0 || dx >= canvasWidth) continue;
      const src = (y * width + x) * components, dst = (dy * canvasWidth + dx) * outComponents;
      if (components === 1) out[dst] = bytes[src];
      else {
        out[dst] = bytes[src]; out[dst + 1] = bytes[src + 1]; out[dst + 2] = bytes[src + 2];
        out[dst + 3] = components === 4 ? bytes[src + 3] : 255;
      }
    }
  }
  return out;
}

function applyMask(rgba, mask) {
  if (rgba.length !== mask.length * 4) throw new Error("결과와 선택 영역 크기가 다릅니다.");
  for (let i = 0; i < mask.length; i++) rgba[i * 4 + 3] = Math.round(rgba[i * 4 + 3] * mask[i] / 255);
  return rgba;
}

function makePrompt(template, settings, inputs) {
  if (!inputs.main) throw new Error("먼저 입력 이미지를 싱크하세요.");
  const input = (item) => ({class_type: "TooBusyPhotoshopInput", inputs: {image: item.name, selection: item.selection || "", matte_white: settings.workflow !== "roundtrip"}});
  if (settings.workflow === "roundtrip") return {
    "1": input(inputs.main),
    "2": {class_type: "TooBusyPhotoshopOutput", inputs: {images: ["1", 0], alpha: ["1", 2]}}
  };
  if ((settings.depth || settings.pose) && !inputs.reference) throw new Error("뎁스·포즈용 참조 이미지를 싱크하세요.");
  if (settings.style && !inputs.style) throw new Error("스타일 참조 이미지를 싱크하세요.");
  if (settings.inpaint && !inputs.main.selection) throw new Error("포토샵에 선택 영역을 만든 뒤 입력을 다시 싱크하세요.");
  const g = JSON.parse(JSON.stringify(template));
  g["4"] = input(inputs.main);
  g["67"] = input(inputs.reference || inputs.main);
  g["56"] = input(inputs.style || inputs.main);
  g["12"] = {class_type: "TooBusyPhotoshopOutput", inputs: {images: ["66", 0]}};
  g["2"].inputs.text = settings.prompt;
  g["3"].inputs.text = settings.negative;
  for (const [id, key] of [["53", "lineart"], ["36", "depth"], ["45", "pose"], ["57", "style"], ["61", "inpaint"]]) g[id].inputs.value = !!settings[key];
  g["32"].inputs.switch = settings.img2img;
  for (const [id, key] of [["9", "lineartStrength"], ["42", "depthStrength"], ["50", "poseStrength"]]) g[id].inputs.strength = settings[key];
  g["59"].inputs.weight = settings.styleStrength;
  if (settings.maskExpand !== undefined) g["62"].inputs.expand = settings.maskExpand;
  if (settings.maskBlur !== undefined) g["62"].inputs.blur_radius = settings.maskBlur;
  Object.assign(g["10"].inputs, {seed: settings.seed, steps: settings.steps, cfg: settings.cfg, denoise: settings.denoise});
  return applyInpaint(applyRecipe(g, migrateRecipe(settings, template)), settings, inputs.main);
}

function resultNames(history) {
  const found = [];
  for (const output of Object.values(history.outputs || {})) {
    for (const image of output.images || []) {
      const subfolder = (image.subfolder || "").replace(/\\/g, "/");
      if (image.type === "output" && (subfolder === "TooBusyPS" || subfolder.startsWith("TooBusyPS/"))) {
        found.push(subfolder.slice("TooBusyPS".length).replace(/^\//, "") + (subfolder === "TooBusyPS" ? "" : "/") + image.filename);
      }
    }
  }
  return found;
}

module.exports = {padPixels, applyMask, makePrompt, resultNames};

/* Work in a padded selection crop, then composite at its original coordinates. */
function selectionBounds(mask, width, height) {
  if (mask.length !== width * height) throw new Error("선택 영역 픽셀 크기가 맞지 않습니다.");
  let left = width, top = height, right = 0, bottom = 0;
  for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
    if (!mask[y * width + x]) continue;
    left = Math.min(left, x); top = Math.min(top, y);
    right = Math.max(right, x + 1); bottom = Math.max(bottom, y + 1);
  }
  return right > left && bottom > top ? {left, top, right, bottom} : null;
}

function cropRegion(input, settings) {
  const {width, height, selectionBounds: b} = input;
  if (!b || ![width, height, b.left, b.top, b.right, b.bottom].every(Number.isInteger) ||
      width < 1 || height < 1 || b.left < 0 || b.top < 0 || b.right > width || b.bottom > height ||
      b.right <= b.left || b.bottom <= b.top) {
    throw new Error("선택 영역을 포함해 입력 이미지를 다시 싱크하세요.");
  }
  const padding = Math.max(160, Math.ceil(Math.max(0, settings.maskExpand || 0) + 3 * (settings.maskBlur || 0)));
  const w = Math.min(width, Math.ceil((Math.max(256, b.right - b.left) + padding * 2) / 16) * 16);
  const h = Math.min(height, Math.ceil((Math.max(256, b.bottom - b.top) + padding * 2) / 16) * 16);
  const x = Math.max(0, Math.min(width - w, Math.floor((b.left + b.right - w) / 2)));
  const y = Math.max(0, Math.min(height - h, Math.floor((b.top + b.bottom - h) / 2)));
  const scale = 1024 / Math.max(w, h);
  return {x, y, width: w, height: h, workWidth: Math.max(16, Math.ceil(w * scale / 16) * 16), workHeight: Math.max(16, Math.ceil(h * scale / 16) * 16)};
}

function applyInpaint(graph, settings, input) {
  if (!settings.inpaint) return graph;
  const {workWidth, workHeight, ...box} = cropRegion(input, settings);
  const add = (name, class_type, inputs, title) => {
    const id = "tb_inpaint_" + name;
    graph[id] = {class_type, inputs, _meta: {title}};
    return [id, 0];
  };
  const scale = image => ({image, upscale_method: "lanczos", width: workWidth, height: workHeight, crop: "disabled"});
  const crop = add("crop", "ImageCrop", {image: ["4", 0], ...box}, "인페인팅 · 주변 맥락 포함 자르기");
  const pixels = add("pixels", "ImageScale", scale(crop), "인페인팅 · 1024 작업 해상도");
  const mask = add("mask_crop", "CropMask", {mask: ["62", 0], ...box}, "인페인팅 · 원본 좌표 마스크");
  const maskImage = add("mask_image", "MaskToImage", {mask}, "인페인팅 · 마스크 크기 변환");
  const scaledMask = add("mask_scale", "ImageScale", {...scale(maskImage), upscale_method: "bilinear"}, "인페인팅 · 작업 마스크 크기");
  const noiseMask = add("noise_mask", "ImageToMask", {image: scaledMask, channel: "red"}, "인페인팅 · 부드러운 노이즈 마스크");
  graph["31"].inputs.pixels = pixels;
  graph["63"].inputs.mask = noiseMask;
  graph["10"].inputs.model = add("model", "DifferentialDiffusion", {model: graph["10"].inputs.model}, "인페인팅 · Differential Diffusion");
  graph["9"].inputs.image = pixels;
  if (settings.depth || settings.pose) {
    const reference = add("reference_crop", "ImageCrop", {image: ["35", 0], ...box}, "인페인팅 · 참조 이미지 동일 영역");
    const resized = add("reference_scale", "ImageScale", scale(reference), "인페인팅 · 참조 이미지 작업 크기");
    graph["38"].inputs.image = resized;
    graph["47"].inputs.image = resized;
  }
  const matched = add("color", "ColorMatch", {image_ref: pixels, image_target: ["11", 0], method: "mkl", strength: 1, multithread: false}, "인페인팅 · 원본 색감에 맞추기");
  const restored = add("restore", "ImageScale", {image: matched, upscale_method: "lanczos", width: box.width, height: box.height, crop: "disabled"}, "인페인팅 · 원본 크기로 복원");
  Object.assign(graph["65"].inputs, {source: restored, mask, x: box.x, y: box.y});
  return graph;
}

module.exports = {selectionBounds, cropRegion, applyInpaint};

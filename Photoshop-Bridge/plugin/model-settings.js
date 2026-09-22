/* Model recipes contain filenames and weights only; never executable graphs. */
const MAX_LORAS = 8;
const fileKey = name => String(name || "").replace(/\\/g, "/").toLowerCase();
const fileLabel = name => String(name || "").replace(/\\/g, "/").split("/").pop();
function defaultRecipe(template) {
  return {checkpoint: template["1"].inputs.ckpt_name, loras: [{name: template["17"].inputs.lora_name, enabled: true, strength: template["17"].inputs.strength_model}]};
}
function normalizeRecipe(value) {
  if (!value || typeof value.checkpoint !== "string" || !value.checkpoint.trim() || !Array.isArray(value.loras) || value.loras.length > MAX_LORAS) throw new Error("모델 조합을 읽을 수 없습니다.");
  const seen = new Set();
  return {checkpoint: value.checkpoint, loras: value.loras.map(row => {
    if (!row || typeof row.name !== "string" || typeof row.enabled !== "boolean" || typeof row.strength !== "number" || !Number.isFinite(row.strength) || row.strength < -2 || row.strength > 2) throw new Error("LoRA 강도는 -2~2 사이 숫자로 입력하세요.");
    if (row.enabled && row.strength !== 0) {
      if (!row.name) throw new Error("사용할 LoRA를 선택하세요.");
      if (seen.has(fileKey(row.name))) throw new Error("같은 LoRA가 중복되어 있어요. 하나만 남겨 주세요.");
      seen.add(fileKey(row.name));
    }
    return {name: row.name, enabled: row.enabled, strength: row.strength};
  })};
}
function migrateRecipe(saved, template) {
  if (saved && saved.modelRecipe) return normalizeRecipe(saved.modelRecipe);
  const value = defaultRecipe(template);
  if (saved && saved.lora !== undefined) value.loras[0].strength = Number(saved.lora);
  return normalizeRecipe(value);
}
function resolveFile(name, available) {
  const exact = available.filter(candidate => fileKey(candidate) === fileKey(name));
  if (exact.length === 1) return exact[0];
  const matches = available.filter(candidate => fileKey(fileLabel(candidate)) === fileKey(fileLabel(name)));
  if (matches.length === 1) return matches[0];
  if (matches.length > 1) throw new Error("같은 이름의 파일이 여러 개 있어요. 경로를 선택하세요: " + fileLabel(name));
  throw new Error("ComfyUI에 없는 파일이에요: " + fileLabel(name));
}
function resolveRecipe(recipe, available) {
  const value = normalizeRecipe(recipe);
  value.checkpoint = resolveFile(value.checkpoint, available.checkpoints);
  for (const row of value.loras) if (row.enabled && row.strength !== 0) {
    row.name = resolveFile(row.name, available.loras);
  }
  return value;
}
function applyRecipe(graph, recipe) {
  const value = normalizeRecipe(recipe);
  const rows = value.loras.filter(row => row.enabled && row.strength !== 0);
  graph["1"].inputs.ckpt_name = value.checkpoint;
  delete graph["17"];
  const last = rows.length === 0 ? "1" : rows.length === 1 ? "17" : "tb_lora_" + (rows.length - 1);
  for (const node of Object.values(graph)) for (const [key, input] of Object.entries(node.inputs)) {
    if (Array.isArray(input) && input[0] === "17") node.inputs[key] = [last, input[1]];
  }
  rows.forEach((row, index) => {
    const id = index === 0 ? "17" : "tb_lora_" + index;
    if (graph[id]) throw new Error("LoRA 노드 ID가 기존 그래프와 겹칩니다.");
    const previous = index === 0 ? "1" : index === 1 ? "17" : "tb_lora_" + (index - 1);
    graph[id] = {class_type: "LoraLoader", inputs: {model: [previous, 0], clip: [previous, 1], lora_name: row.name, strength_model: row.strength, strength_clip: row.strength}};
  });
  return graph;
}
function savePreset(presets, name, recipe) {
  const title = String(name || "").trim();
  if (!title || title.length > 40) throw new Error("조합 이름을 1~40자로 입력하세요.");
  if (presets.some(preset => preset.name === title)) throw new Error("이미 있는 조합 이름이에요. 다른 이름으로 저장하세요.");
  if (presets.length >= 30) throw new Error("조합은 최대 30개까지 저장할 수 있어요.");
  return presets.concat([{name: title, recipe: normalizeRecipe(recipe)}]);
}
module.exports = {MAX_LORAS, fileKey, fileLabel, defaultRecipe, normalizeRecipe, migrateRecipe, resolveFile, resolveRecipe, applyRecipe, savePreset};

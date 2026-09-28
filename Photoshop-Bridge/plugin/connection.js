const MODEL_FIELDS = {"1":"ckpt_name", "17":"lora_name", "7":"control_net_name", "40":"control_net_name", "37":"model_name", "46":"ckpt_name", "58":"ipadapter_file", "68":"clip_name"};
const MODEL_KINDS = {"1":"checkpoints", "17":"loras", "7":"controlnet", "40":"controlnet", "37":"geometry_estimation", "46":"checkpoints", "58":"ipadapter", "68":"clip_vision"};
const MODEL_LABELS = {"1":"체크포인트", "17":"LoRA", "7":"라인아트 ControlNet", "40":"뎁스·포즈 ControlNet", "37":"뎁스 모델", "46":"포즈 모델", "58":"IP-Adapter", "68":"CLIP Vision"};
function connection(value) {
  if (!value || !/^[a-f0-9]{64}$/i.test(value.token || "")) throw new Error("올바른 TooBusy 연결 파일을 선택하세요.");
  const server = value.server || "http://127.0.0.1:8188";
  if (!/^http:\/\/(127\.0\.0\.1|localhost):\d{1,5}$/.test(server) || Number(server.split(":").pop()) > 65535 || Number(server.split(":").pop()) < 1) throw new Error("연결 파일의 서버 주소가 올바르지 않아요.");
  const modelPaths = {};
  for (const [id,path] of Object.entries(value.modelPaths || {})) {
    if (!MODEL_FIELDS[id] || typeof path !== "string" || !path || path.startsWith("/") || /[:\x00-\x1f]/.test(path) || path.replace(/\\/g,"/").split("/").includes("..")) throw new Error("연결 파일의 모델 경로가 올바르지 않아요.");
    modelPaths[id] = path;
  }
  return {token:value.token,server,modelPaths};
}
function applyPaths(template, value) {
  for (const [id,path] of Object.entries(value.modelPaths)) template[id].inputs[MODEL_FIELDS[id]] = path;
}
// ComfyUI validates loader values by exact string. Lists use the host's separator
// (Windows: backslash) while the installer writes forward slashes before the
// first connection check, so match separator-insensitively, then by file name.
function normalize(path) { return String(path).replace(/\\/g, "/").toLowerCase(); }
function resolveModel(desired, options) {
  if (!Array.isArray(options) || typeof desired !== "string") return null;
  const names = options.filter((item) => typeof item === "string");
  if (names.includes(desired)) return desired;
  const wanted = normalize(desired);
  const same = names.filter((item) => normalize(item) === wanted);
  if (same.length === 1) return same[0];
  const file = wanted.split("/").pop();
  const byName = names.filter((item) => normalize(item).split("/").pop() === file);
  return byName.length === 1 ? byName[0] : null;
}
function loaderOptions(info, classType, field) {
  const node = info && info[classType];
  if (!node) return null;
  const schema = ((node.input || {}).required || {})[field];
  if (!Array.isArray(schema)) return [];
  if (Array.isArray(schema[0])) return schema[0];
  return (schema[1] && Array.isArray(schema[1].options)) ? schema[1].options : [];
}
// Rewrites graph loader values to the server's exact strings. Returns the nodes
// that could not be matched so the caller can explain which file is missing.
function resolvePaths(graph, info, ids = Object.keys(MODEL_FIELDS)) {
  const missing = [], missingNodes = [];
  for (const id of ids) {
    const node = graph[id];
    if (!node || !MODEL_FIELDS[id]) continue;
    const field = MODEL_FIELDS[id], desired = node.inputs[field];
    const options = loaderOptions(info, node.class_type, field);
    if (options === null) { if (!missingNodes.includes(node.class_type)) missingNodes.push(node.class_type); continue; }
    const found = resolveModel(desired, options);
    if (found === null) missing.push({id, field, desired, kind: MODEL_KINDS[id], label: MODEL_LABELS[id], classType: node.class_type});
    else node.inputs[field] = found;
  }
  return {missing, missingNodes};
}
function missingMessage({missing, missingNodes}, folders) {
  const lines = [];
  if (missingNodes.length) lines.push("ComfyUI에 필요한 노드가 없습니다: " + missingNodes.join(", ") + ". 설치기에서 ② 설치를 다시 실행하고 ComfyUI를 재시작하세요.");
  if (missing.length) {
    lines.push("ComfyUI가 다음 모델 파일을 찾지 못했습니다.");
    for (const item of missing) {
      const file = String(item.desired).replace(/\\/g, "/").split("/").pop();
      const known = folders && Array.isArray(folders[item.kind]) ? folders[item.kind].filter((p) => typeof p === "string") : [];
      lines.push("- " + item.label + ": " + file + (known.length ? " → 넣을 폴더: " + known.join(" 또는 ") : " → ComfyUI의 " + item.kind + " 모델 폴더"));
    }
    lines.push("파일을 해당 폴더에 넣고 ComfyUI를 재시작하거나, 최신 설치기에서 ② 설치 → ComfyUI 재실행 → ③ 연결 검사를 다시 진행하세요.");
  }
  return lines.join("\n");
}
module.exports = {connection,applyPaths,resolveModel,resolvePaths,loaderOptions,missingMessage,MODEL_FIELDS,MODEL_KINDS,MODEL_LABELS};

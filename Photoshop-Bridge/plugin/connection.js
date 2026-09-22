const MODEL_FIELDS = {"1":"ckpt_name", "17":"lora_name", "7":"control_net_name", "40":"control_net_name", "37":"model_name", "46":"ckpt_name", "58":"ipadapter_file", "68":"clip_name"};
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
module.exports = {connection,applyPaths};

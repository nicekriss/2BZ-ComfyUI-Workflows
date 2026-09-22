// ComfyUI opens API JSON as an editable, automatically arranged node graph.
// Export only execution data, never the job envelope (server/token/document info).
function executionGraph(graph) {
  if (!graph || typeof graph !== "object" || Array.isArray(graph) || !Object.keys(graph).length) throw new Error("저장할 실행 워크플로우가 없습니다.");
  const result = {};
  for (const [id, node] of Object.entries(graph)) {
    if (!node || typeof node.class_type !== "string" || !node.inputs || Array.isArray(node.inputs) || typeof node.inputs !== "object") throw new Error("실행 워크플로우 형식이 올바르지 않습니다.");
    result[id] = {class_type: node.class_type, inputs: JSON.parse(JSON.stringify(node.inputs))};
    if (node._meta && typeof node._meta.title === "string") result[id]._meta = {title: node._meta.title.replace(/선화/g, "라인아트")};
  }
  for (const node of Object.values(result)) for (const value of Object.values(node.inputs)) {
    if (Array.isArray(value) && (!result[String(value[0])] || !Number.isInteger(value[1]) || value[1] < 0)) throw new Error("워크플로우의 노드 연결을 확인할 수 없습니다.");
  }
  return result;
}
module.exports = {executionGraph};

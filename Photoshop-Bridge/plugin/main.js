const {capture, applyResult} = require("./photoshop.js");
const {makePrompt, resultNames} = require("./protocol.js");
const config = require("./config.json");
const template = require("./pro-template.json");
const manifest = require("./manifest.json");
const updater = require("./updater.js");
const {executionGraph} = require("./workflow-export.js");
let availableUpdate = null;
const {connection, applyPaths} = require("./connection.js");
try { const saved = localStorage.getItem("toobusy.connection"); if (saved) { const value = connection(JSON.parse(saved)); config.token = value.token; applyPaths(template,value); } } catch (_) { /* An invalid saved connection must be imported again. */ }
const {base64, inputPreviewPath} = require("./preview.js");
const {createModelControls} = require("./model-controls.js");
const {fileLabel} = require("./model-settings.js");
const {entrypoints, pluginManager} = require("uxp");
const panelRoots = ["app", "inputViewer", "resultViewer"].map((id) => document.getElementById(id));
const $ = (id) => panelRoots.find((root) => root.id === id) || panelRoots.map((root) => root.querySelector("#" + id)).find(Boolean);
const all = (selector) => panelRoots.reduce((items, root) => items.concat(Array.from(root.querySelectorAll(selector))), []);
const inputPreviews = {};
let inputPreviewVersion = 0;
const inputState = {};
const results = [];
let connected = false, busy = false, pending = null, stopWaiting = false;
const boolKeys = ["img2img", "lineart", "depth", "pose", "style", "inpaint"];
const numKeys = ["lineartStrength", "depthStrength", "poseStrength", "styleStrength", "maskExpand", "maskBlur", "denoise", "steps", "cfg", "seed"];

function status(message, error = false) {
  for (const id of ["status", "viewerStatus"]) {
    $(id).textContent = message; $(id).classList.toggle("error", error); $(id).setAttribute("title", message); $(id).scrollTop = 0;
  }
}

// Photoshop's native button chrome overrides background colors. These controls
// keep explicit keyboard and disabled behavior while using the panel's palette.
function actionControl(element) {
  element.classList.add("action");
  element.setAttribute("role", "button");
  element.setAttribute("data-action", "true");
  Object.defineProperty(element, "disabled", {
    get() { return element.getAttribute("aria-disabled") === "true"; },
    set(value) {
      element.setAttribute("aria-disabled", String(!!value));
      element.classList.toggle("disabled", !!value);
      element.setAttribute("tabindex", value ? "-1" : "0");
    }
  });
  element.disabled = false;
  element.addEventListener("click", (event) => {
    if (element.disabled) { event.preventDefault(); event.stopImmediatePropagation(); }
  }, true);
  element.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      if (!element.disabled && !event.repeat && element.onclick) element.onclick();
    }
  });
  return element;
}
for (const element of all("[data-action]")) actionControl(element);
for (const toolbar of all(".applyToolbar")) {
  const hint = toolbar.querySelector(".applyHint");
  for (const button of toolbar.querySelectorAll(".iconAction")) {
    const describe = () => { hint.textContent = button.getAttribute("aria-label"); };
    const reset = () => { hint.textContent = "결과 적용"; };
    button.addEventListener("mouseenter", describe);
    button.addEventListener("mouseleave", reset);
    button.addEventListener("focus", describe);
    button.addEventListener("blur", reset);
  }
}
function switchTab(name) {
  for (const tab of ["work", "results"]) {
    $(tab + "View").classList.toggle("hidden", tab !== name);
    $(tab + "Tab").classList.toggle("active", tab === name);
    $(tab + "Tab").setAttribute("aria-selected", String(tab === name));
  }
  $("content").scrollTop = 0;
}
function address() {
  const value = $("server").value.replace(/\/+$/, "");
  if (!/^http:\/\/(127\.0\.0\.1|localhost)(:\d{1,5})?$/.test(value)) throw new Error("같은 PC의 http://127.0.0.1:포트 주소를 입력하세요.");
  return value;
}
async function request(base, path, options = {}) {
  if (!config.token) throw new Error("연결 설정에서 설치기가 만든 연결 파일을 열어주세요.");
  // UXP's localhost domain allowlist rejects loopback on this host. Keep the
  // application boundary here, including restored pending jobs and results.
  if (!/^http:\/\/(127\.0\.0\.1|localhost)(:\d{1,5})?$/.test(base) || !path.startsWith("/") || path.startsWith("//")) throw new Error("이 PC의 ComfyUI 주소만 사용할 수 있습니다.");
  let timer;
  let response;
  try {
    response = await Promise.race([
      fetch(base + path, {...options, redirect: "error", headers: {...options.headers, "X-TooBusy-Token": config.token}}),
      new Promise((_, reject) => { timer = setTimeout(() => reject(new Error("서버 응답이 늦습니다. 연결을 확인하고 진행 중인 결과를 다시 조회하세요.")), 30000); })
    ]);
  } finally { clearTimeout(timer); }
  if (!response.ok) {
    const error = new Error("연결 오류 " + response.status + ": " + (await response.text()).slice(0, 600));
    error.httpStatus = response.status; throw error;
  }
  return response;
}
function updateButtons() {
  for (const element of all("input, textarea, select, [data-action]")) element.disabled = busy;
  for (const element of all("[data-tab], [data-fold]")) element.disabled = false;
  $("connectionToggle").disabled = false;
  $("openInputViewer").disabled = false;
  $("openResultViewer").disabled = false;
  $("viewerSync").disabled = busy || !connected;
  $("installUpdate").disabled = busy || !!pending;
  $("exportLastWorkflow").disabled = busy || !localStorage.getItem("toobusy.lastPrompt");
  $("generate").disabled = busy || !connected || !inputState.main || !!pending;
  $("generate").textContent = pending ? "생성 중…" : ($("workflow").value === "roundtrip" ? "이미지 왕복 검사" : "이미지 생성");
  $("resume").classList.toggle("hidden", !pending);
  $("forget").classList.toggle("hidden", !pending);
  $("stopWait").classList.toggle("hidden", !pending || !busy);
  $("stopWait").disabled = !pending || !busy;
  const selected = results[Number($("resultList").value)];
  for (const button of all("[data-export-result]")) button.disabled = busy || !selected;
  for (const id of ["applyNew", "applySelection", "viewerApplyNew", "viewerApplySelection"]) $(id).disabled = busy || !selected;
  for (const id of ["applyCanvas", "viewerApplyCanvas"]) $(id).disabled = busy || !selected || !selected.input.documentID;
  updateResultNavigation();
  modelControls.updateButtons(busy);
}
function updateResultNavigation() {
  const index = $("resultList").selectedIndex;
  const hasResult = !!results[index];
  for (const label of all(".resultPosition")) label.textContent = (hasResult ? index + 1 : 0) + " / " + results.length;
  for (const button of all("[data-result-nav]")) {
    const direction = button.getAttribute("data-result-nav");
    button.disabled = busy || !hasResult || (direction === "previous" ? index <= 0 : index >= results.length - 1);
  }
}
async function navigateResult(direction) {
  if (!results.length) return;
  const index = $("resultList").selectedIndex;
  const next = direction === "latest" ? results.length - 1 : index + (direction === "previous" ? -1 : 1);
  $("resultList").selectedIndex = Math.max(0, Math.min(results.length - 1, next));
  await showResult();
}
async function operation(fn) {
  if (busy) return;
  busy = true; updateButtons();
  try { await fn(); }
  catch (error) { console.error("TooBusy Bridge", error.stack || error); status(error.message || String(error), true); }
  finally { busy = false; updateButtons(); }
}
function settings(includeUnusedModels = true) {
  const s = {workflow: $("workflow").value, prompt: $("prompt").value, negative: $("negative").value};
  if (!["roundtrip", "pro"].includes(s.workflow)) throw new Error("작업 종류를 선택하세요.");
  for (const id of boolKeys) s[id] = $(id).checked;
  for (const id of numKeys) {
    const el = $(id), number = Number(el.value);
    if (!String(el.value).trim() || !Number.isFinite(number) || number < Number(el.getAttribute("min")) || number > Number(el.getAttribute("max"))) throw new Error("설정값을 확인하세요: " + id);
    if (["steps", "seed", "maskExpand"].includes(id) && !Number.isInteger(number)) throw new Error("단계·시드·선택 영역 확장은 정수여야 합니다.");
    s[id] = number;
  }
  if (includeUnusedModels || s.workflow === "pro") s.modelRecipe = modelControls.getRecipe();
  return s;
}
function persist() {
  try { localStorage.setItem("toobusy.settings", JSON.stringify({...settings(), server: $("server").value})); } catch (_) { /* An unfinished numeric edit is not saved. */ }
}
function persistPending() { localStorage.setItem("toobusy.pending", JSON.stringify(pending)); }

async function syncInput(role) {
  const base = address();
  if (!connected) throw new Error("먼저 ComfyUI 연결을 확인하세요.");
  status("입력 이미지를 읽고 있습니다…");
  const captured = await capture($(role + "Source").value);
  if (!captured) { status("파일 선택을 취소했습니다."); return; }
  let info;
  if (captured.fileBytes) info = await (await request(base, "/toobusy/ps/v1/input", {method: "POST", body: captured.fileBytes})).json();
  else info = await (await request(base, "/toobusy/ps/v1/input?format=raw&width=" + captured.width + "&height=" + captured.height + "&components=4", {method: "POST", body: captured.pixels.buffer})).json();
  let selection = "";
  if (captured.selection) {
    const mask = await (await request(base, "/toobusy/ps/v1/input?format=raw&width=" + captured.width + "&height=" + captured.height + "&components=1", {method: "POST", body: captured.selection.buffer})).json();
    selection = mask.name;
  }
  const {pixels, fileBytes, selection: ignoredMask, ...meta} = captured;
  inputState[role] = {...meta, ...info, selection, base};
  inputState[role].syncedAt = Date.now();
  delete inputPreviews[role];
  $(role + "Info").textContent = captured.label + " · " + info.width + " × " + info.height + (selection ? " · 선택 영역 포함" : "") + " · 싱크 완료";
  status("싱크 완료. 이제 이 이미지를 재료로 사용합니다.");
  $("inputViewerRole").value = role;
  await showInputPreview();
}

async function checkConnection() {
  connected = false;
  $("connectionStatus").textContent = "연결 확인 중…";
  $("connectionToggle").textContent = "연결 중…";
  $("connectionToggle").classList.remove("connected");
  let info;
  try { info = await (await request(address(), "/toobusy/ps/v1/info")).json(); }
  catch (error) { $("connectionStatus").textContent = "연결 실패: " + error.message; $("connectionToggle").textContent = "연결 설정"; $("connectionPanel").classList.remove("hidden"); $("connectionToggle").setAttribute("aria-expanded", "true"); throw error; }
  if (info.protocol !== 1) throw new Error("플러그인과 커스텀노드 버전이 다릅니다.");
  connected = true;
  $("connectionStatus").textContent = "연결됨 · Bridge " + info.version;
  $("connectionToggle").textContent = "● 연결됨";
  $("connectionToggle").classList.add("connected");
  await modelControls.refresh();
  status(inputState.main ? "연결 완료 · 생성할 준비가 됐어요." : "입력을 싱크하면 생성할 수 있어요.");
}

async function generate() {
  const base = address();
  for (const item of Object.values(inputState)) if (item.base !== base) throw new Error("연결 주소가 바뀌었습니다. 입력을 다시 싱크하세요.");
  const s = settings(false);
  if (s.workflow === "pro") {
    await modelControls.refresh();
    s.modelRecipe = modelControls.validate();
  }
  const graph = makePrompt(template, s, inputState);
  localStorage.setItem("toobusy.lastPrompt", JSON.stringify(executionGraph(graph)));
  const clientId = "toobusy-" + Date.now() + "-" + Math.random().toString(16).slice(2);
  status("ComfyUI에 작업을 제출합니다…");
  pending = {base, id: null, clientId, graph, input: {...inputState.main}, label: s.workflow === "roundtrip" ? "왕복 검사" : "라인아트 채색", modelRecipe: s.workflow === "pro" ? s.modelRecipe : null, started: Date.now()};
  persistPending();
  try {
    const response = await (await request(base, "/prompt", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({prompt: graph, client_id: clientId})})).json();
    pending.id = response.prompt_id; persistPending();
  } catch (error) {
    if (error.httpStatus >= 400 && error.httpStatus < 500) { pending = null; persistPending(); }
    throw error;
  }
  await watchPending();
}

async function watchPending() {
  if (!pending) return;
  stopWaiting = false;
  updateButtons();
  // Do not re-submit on network loss or panel reload; retain the exact prompt ID.
  const job = pending;
  if (!job.id) {
    const history = await (await request(job.base, "/history?max_items=200")).json();
    const completed = Object.entries(history).find(([, record]) => record.prompt && record.prompt[3] && record.prompt[3].client_id === job.clientId);
    if (completed) job.id = completed[0];
    else {
      const queue = await (await request(job.base, "/queue")).json();
      const queued = [...queue.queue_running, ...queue.queue_pending].find((entry) => entry[3] && entry[3].client_id === job.clientId);
      if (queued) job.id = queued[1];
    }
    if (!job.id) throw new Error("제출 결과를 확인할 수 없습니다. ComfyUI 대기열을 확인하세요. 작업을 찾지 못했을 때만 추적 종료 후 다시 실행하세요.");
    persistPending();
  }
  status("생성 중 · 완료되면 결과 미리보기가 갱신됩니다.");
  const until = Date.now() + 30 * 60 * 1000;
  while (Date.now() < until) {
    if (stopWaiting) { status("대기를 중지했습니다. 생성은 서버에서 계속됩니다. 결과 다시 확인으로 이어갈 수 있습니다."); return; }
    const history = await (await request(job.base, "/history/" + encodeURIComponent(job.id))).json();
    if (history[job.id]) {
      const record = history[job.id];
      if (record.status && record.status.status_str === "error") {
        pending = null; persistPending();
        const failure = (record.status.messages || []).find((entry) => entry[0] === "execution_error");
        throw new Error("생성 실패: " + (failure ? failure[1].exception_message : "ComfyUI 실행 로그를 확인하세요."));
      }
      const names = resultNames(record);
      if (!names.length) { pending = null; persistPending(); throw new Error("실행이 끝났지만 Bridge 출력이 없습니다. 워크플로우의 출력 노드를 확인하세요."); }
      for (const name of names) results.push({...job, name});
      if (results.length > 20) results.splice(0, results.length - 20);
      localStorage.setItem("toobusy.results", JSON.stringify(results));
      pending = null; persistPending();
      renderResultList();
      status("결과가 도착했습니다. 확인한 뒤 적용 방법을 고르세요.");
      await showResult();
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
  throw new Error("아직 완료되지 않았습니다. 진행 중인 결과 다시 확인을 눌러 같은 작업을 조회하세요.");
}

function renderResultList() {
  for (const id of ["resultList", "viewerResultList"]) {
  const select = $(id); select.innerHTML = "";
  results.forEach((item, index) => {
    const option = document.createElement("option"); option.setAttribute("value", String(index));
    option.textContent = (index + 1) + ". " + String(item.label).replace(/선화/g, "라인아트") + " · " + new Date(item.started).toLocaleTimeString();
    select.appendChild(option);
  });
  select.selectedIndex = results.length - 1;
  }
  $("resultsTab").textContent = "결과 · " + results.length;
}
async function showResult() {
  const item = results[Number($("resultList").value)];
  if (!item) return;
  $("viewerResultList").selectedIndex = $("resultList").selectedIndex;
  updateResultNavigation();
  $("preview").classList.add("hidden");
  $("viewerResultImage").classList.add("hidden");
  const preview = await (await request(item.base, "/toobusy/ps/v1/result?preview=1&name=" + encodeURIComponent(item.name))).json();
  $("preview").src = preview.data; $("preview").classList.remove("hidden");
  $("emptyResult").classList.add("hidden");
  $("viewerResultImage").src = preview.data; $("viewerResultImage").classList.remove("hidden");
  $("viewerEmptyResult").classList.add("hidden");
  $("resultInfo").textContent = item.input.documentName ? "캔버스 적용 대상: " + item.input.documentName : "새 이미지로 열거나 현재 선택 영역에 넣으세요.";
  if (item.modelRecipe) $("resultInfo").textContent += "\n모델: " + fileLabel(item.modelRecipe.checkpoint) + " · LoRA " + item.modelRecipe.loras.filter(row => row.enabled && row.strength !== 0).length + "개";
  $("resultInfo").setAttribute("title", $("resultInfo").textContent);
  $("viewerResultInfo").textContent = $("resultInfo").textContent;
}

async function showInputPreview() {
  const version = ++inputPreviewVersion;
  const role = $("inputViewerRole").value || "main";
  const item = inputState[role];
  $("inputViewerImage").classList.add("hidden");
  $("inputViewerEmpty").classList.remove("hidden");
  if (!item) {
    $("inputViewerEmpty").textContent = "먼저 이미지를 싱크하세요.";
    $("inputViewerMeta").textContent = "아직 싱크한 이미지가 없습니다.";
    return;
  }
  const sourceLabel = {canvas: "캔버스", layer: "레이어", file: "파일"}[item.source] || "이미지";
  $("inputViewerMeta").textContent = sourceLabel + " · " + item.width + " × " + item.height + " · " +
    new Date(item.syncedAt).toLocaleTimeString() + " 싱크\n" + item.label + (item.selection ? "\n선택 영역 포함" : "\n선택 영역 없음");
  $("inputViewerEmpty").textContent = "싱크 이미지 불러오는 중…";
  try {
    if (!inputPreviews[role]) {
      const bytes = new Uint8Array(await (await request(item.base, inputPreviewPath(item.name))).arrayBuffer());
      if (inputState[role] !== item) return;
      inputPreviews[role] = "data:image/jpeg;base64," + base64(bytes);
    }
    if (version !== inputPreviewVersion) return;
    $("inputViewerImage").src = inputPreviews[role];
    $("inputViewerImage").classList.remove("hidden");
    $("inputViewerEmpty").classList.add("hidden");
  } catch (error) {
    if (version === inputPreviewVersion) $("inputViewerEmpty").textContent = "미리보기 로드 실패 · 다시 싱크해 주세요.";
    console.error("Input preview", error);
  }
}
async function openViewer(id) {
  try {
    const me = Array.from(pluginManager.plugins).find((plugin) => plugin.id === manifest.id);
    if (!me) throw new Error("플러그인을 찾지 못했습니다.");
    await me.showPanel(id);
  } catch (error) { status("창을 열지 못했어요. 포토샵 플러그인 메뉴에서 미리보기를 열어주세요.", true); console.error(error); }
}
async function exportWorkflow(item) {
  let graph = item ? item.graph : JSON.parse(localStorage.getItem("toobusy.lastPrompt") || "null");
  if (!graph && item && item.id) {
    const history = await (await request(item.base, "/history/" + encodeURIComponent(item.id))).json();
    const record = history[item.id];
    graph = record && record.prompt && record.prompt[2];
  }
  if (!graph) throw new Error("이 결과의 실행 기록이 없습니다. 다시 생성한 결과부터 워크플로우를 저장할 수 있습니다.");
  const {storage} = require("uxp");
  const file = await storage.localFileSystem.getFileForSaving("TooBusy-execution-" + (item && item.started || Date.now()) + ".json", {types: ["json"]});
  if (!file) { status("워크플로우 저장을 취소했습니다."); return; }
  await file.write(JSON.stringify(executionGraph(graph), null, 2));
  status("워크플로우 저장 완료 · 같은 ComfyUI의 새 탭에 JSON을 끌어 놓으세요. 싱크 이미지와 마스크는 해당 ComfyUI에 보관되어 있습니다.");
}
async function fetchPixels(item, width, height) {
  let path = "/toobusy/ps/v1/result?name=" + encodeURIComponent(item.name);
  if (width && height) path += "&width=" + width + "&height=" + height;
  const response = await request(item.base, path);
  const result = {width: Number(response.headers.get("X-Width")), height: Number(response.headers.get("X-Height")), data: new Uint8Array(await response.arrayBuffer())};
  if (result.data.length !== result.width * result.height * 4) throw new Error("받은 이미지 데이터가 올바르지 않습니다.");
  return result;
}

for (const [role, title] of [["main", "입력 이미지"], ["reference", "뎁스·포즈 참조"], ["style", "스타일 참조"]]) {
  const parent = $(role === "main" ? "mainInput" : role + "Input");
  const label = document.createElement("label"); label.textContent = title; parent.appendChild(label);
  const row = document.createElement("div"); row.className = "row";
  const select = document.createElement("select"); select.id = role + "Source";
  select.innerHTML = '<option value="canvas"' + (role === "main" ? ' selected' : '') + '>캔버스</option><option value="file">파일</option><option value="layer"' + (role !== "main" ? ' selected' : '') + '>현재 레이어</option>';
  const button = actionControl(document.createElement("div")); button.classList.add("syncAction"); button.textContent = "싱크"; button.onclick = () => operation(() => syncInput(role));
  row.appendChild(select); row.appendChild(button); parent.appendChild(row);
  const info = document.createElement("p"); info.id = role + "Info"; info.className = "muted"; info.textContent = "소스를 고른 뒤 싱크하세요."; parent.appendChild(info);
  select.onchange = () => { delete inputState[role]; delete inputPreviews[role]; info.textContent = "입력 방식을 바꿨습니다. 싱크하세요."; updateButtons(); showInputPreview(); };
}
const modelControls = createModelControls({$, document, storage: localStorage, template, actionControl, request, address, operation, changed: () => { persist(); updateButtons(); }, status});
$("prompt").value = template["2"].inputs.text;
$("negative").value = template["3"].inputs.text;
try {
  const saved = JSON.parse(localStorage.getItem("toobusy.settings") || "null");
  if (saved) for (const [id, value] of Object.entries(saved)) if ($(id)) { if (boolKeys.includes(id)) $(id).checked = value; else $(id).value = value; }
  pending = JSON.parse(localStorage.getItem("toobusy.pending") || "null");
  const savedResults = JSON.parse(localStorage.getItem("toobusy.results") || "[]");
  results.push(...savedResults); if (results.length) renderResultList();
} catch (_) { status("저장된 설정을 읽지 못해 기본값을 사용합니다."); }
for (const button of all("[data-fold]")) {
  const target = $(button.getAttribute("data-fold"));
  const key = "toobusy.fold." + target.id;
  const saved = localStorage.getItem(key);
  if (saved !== null) target.classList.toggle("hidden", saved === "closed");
  button.setAttribute("aria-expanded", String(!target.classList.contains("hidden")));
  button.textContent = (target.classList.contains("hidden") ? "▸ " : "▾ ") + button.textContent.slice(2);
  button.onclick = () => { target.classList.toggle("hidden"); const closed = target.classList.contains("hidden"); button.textContent = (closed ? "▸ " : "▾ ") + button.textContent.slice(2); button.setAttribute("aria-expanded", String(!closed)); localStorage.setItem(key, closed ? "closed" : "open"); };
}
for (const element of all("input, textarea, select")) element.addEventListener("change", persist);
$("server").addEventListener("change", () => { connected = false; $("connectionStatus").textContent = "주소 변경됨 · 다시 연결하세요."; $("connectionToggle").textContent = "연결 설정"; $("connectionToggle").classList.remove("connected"); updateButtons(); });
for (const button of all("[data-tab]")) button.onclick = () => switchTab(button.getAttribute("data-tab"));
for (const element of all("[data-tab], [data-fold]")) element.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") { event.preventDefault(); element.onclick(); }
  if (element.getAttribute("data-tab") && (event.key === "ArrowLeft" || event.key === "ArrowRight")) {
    event.preventDefault(); const next = element.getAttribute("data-tab") === "work" ? "results" : "work"; switchTab(next); $(next + "Tab").focus();
  }
});
$("connectionToggle").onclick = () => { $("connectionPanel").classList.toggle("hidden"); $("connectionToggle").setAttribute("aria-expanded", String(!$("connectionPanel").classList.contains("hidden"))); };
$("img2img").addEventListener("change", () => { $("denoise").value = $("img2img").checked ? "0.75" : "1"; persist(); });
$("inpaint").addEventListener("change", () => { if ($("inpaint").checked) $("denoise").value = "0.75"; persist(); });
$("connect").onclick = () => operation(checkConnection);
$("exportLastWorkflow").onclick = () => operation(() => exportWorkflow(null));
for (const button of all("[data-export-result]")) button.onclick = () => operation(() => exportWorkflow(results[Number($("resultList").value)]));
$("pluginVersion").textContent = "TooBusy AI · v" + manifest.version;
$("checkUpdate").onclick = () => operation(async () => {
  availableUpdate = null;
  $("installUpdate").classList.add("hidden");
  $("updatePage").classList.add("hidden");
  $("updateStatus").textContent = "새 버전을 확인하고 있습니다…";
  try {
    availableUpdate = await updater.check(manifest.version);
    if (!availableUpdate) { $("updateStatus").textContent = "현재 v" + manifest.version + " · 최신 버전입니다."; return; }
    $("updateStatus").textContent = "v" + availableUpdate.version + " 업데이트가 있습니다. " + (availableUpdate.asset ? "Adobe 설치 화면에서 업데이트를 마치세요." : "이 버전은 배포 페이지에서 설치 파일을 받아주세요.");
    $("installUpdate").textContent = "v" + availableUpdate.version + " 업데이트 받기";
    $("installUpdate").classList.toggle("hidden", !availableUpdate.asset);
    $("updatePage").classList.remove("hidden");
  } catch (error) {
    $("updateStatus").textContent = error.message;
    $("updatePage").classList.remove("hidden");
  }
});
$("installUpdate").onclick = () => operation(async () => {
  if (pending) throw new Error("진행 중인 이미지 생성이 끝난 뒤 업데이트하세요.");
  try {
    $("updateStatus").textContent = "업데이트를 다운로드하고 검증하고 있습니다…";
    const bytes = await updater.download(availableUpdate);
    const {storage, shell} = require("uxp");
    const folder = await storage.localFileSystem.getDataFolder();
    const file = await folder.createFile("TooBusyAI-" + availableUpdate.version + ".ccx", {overwrite: true});
    await file.write(bytes, {format: storage.formats.binary});
    const error = await shell.openPath(file.nativePath, "TooBusy AI 업데이트를 Adobe 설치 화면에서 엽니다. 모델과 연결 설정은 유지됩니다.");
    if (error) throw new Error("Adobe 설치 화면을 열지 못했습니다. 배포 페이지에서 CCX 파일을 받아 열어주세요.");
    $("updateStatus").textContent = "Adobe 설치 화면을 열었습니다. 설치 후 플러그인을 다시 열어 버전을 확인하세요.";
  } catch (error) { $("updateStatus").textContent = error.message; throw error; }
});
$("updatePage").onclick = () => operation(async () => {
  const error = await require("uxp").shell.openExternal(availableUpdate ? availableUpdate.page : updater.RELEASES + "/tag/photoshop-bridge-v" + manifest.version, "TooBusy AI 공식 배포 페이지를 엽니다.");
  if (error) throw new Error("배포 페이지를 열지 못했습니다. 인터넷 연결을 확인하세요.");
});
$("importConnection").onclick = () => operation(async () => {
  if (pending) throw new Error("진행 중인 결과 확인을 마친 뒤 연결을 바꾸세요.");
  const fs = require("uxp").storage.localFileSystem;
  const file = await fs.getFileForOpening({types:["json"]});
  if (!file) return;
  const value = connection(JSON.parse(await file.read()));
  localStorage.setItem("toobusy.connection",JSON.stringify(value));
  config.token = value.token; applyPaths(template,value); $("server").value = value.server;
  connected = false;
  for (const role of Object.keys(inputState)) delete inputState[role];
  persist(); await checkConnection();
  status("설치 연결 완료. 입력 이미지를 싱크하세요.");
});
$("generate").onclick = () => operation(generate);
$("resume").onclick = () => operation(watchPending);
$("stopWait").onclick = () => { stopWaiting = true; status("현재 응답을 받은 뒤 대기를 중지합니다. 서버 생성은 계속됩니다."); };
$("forget").onclick = () => { pending = null; persistPending(); status("작업 추적을 종료했습니다. 서버에서 진행 중인 생성은 계속됩니다. 중복 실행 전 대기열을 확인하세요."); updateButtons(); };
$("resultList").onchange = () => operation(showResult);
$("viewerResultList").onchange = () => { $("resultList").selectedIndex = $("viewerResultList").selectedIndex; operation(showResult); };
for (const button of all("[data-result-nav]")) button.onclick = () => operation(() => navigateResult(button.getAttribute("data-result-nav")));
$("inputViewerRole").onchange = showInputPreview;
$("viewerSync").onclick = () => operation(() => syncInput($("inputViewerRole").value));
$("openInputViewer").onclick = () => openViewer("toobusyInput");
$("openResultViewer").onclick = () => openViewer("toobusyResults");
for (const [id, mode] of [["applyCanvas", "canvas"], ["applyNew", "new"], ["applySelection", "selection"], ["viewerApplyCanvas", "canvas"], ["viewerApplyNew", "new"], ["viewerApplySelection", "selection"]]) $(id).onclick = () => operation(async () => { const item = results[Number($("resultList").value)]; await applyResult(mode, item, fetchPixels); status(mode === "new" ? "새 이미지로 열었어요." : "새 레이어에 적용 완료 · Ctrl+Z로 되돌리기"); });

const panelHandlers = {};
for (const [index, id] of ["toobusyBridge", "toobusyInput", "toobusyResults"].entries()) {
  const element = panelRoots[index];
  if (element.parentNode) element.parentNode.removeChild(element);
  const attach = (root) => { root.appendChild(element); element.classList.remove("hidden"); };
  panelHandlers[id] = {create: attach, show: attach};
}
entrypoints.setup({panels: panelHandlers});
updateButtons();
operation(async () => { await checkConnection(); if (results.length) await showResult(); });


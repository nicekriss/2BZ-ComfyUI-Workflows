const M = require("./model-settings.js");
function createModelControls({$, document, storage, template, actionControl, request, address, operation, changed, status}) {
  let available = {checkpoints: [], loras: []}, loaded = false;
  let presets = [], initial;
  try {
    const saved = JSON.parse(storage.getItem("toobusy.settings") || "null");
    initial = M.migrateRecipe(saved, template);
    const savedPresets = JSON.parse(storage.getItem("toobusy.modelPresets") || "[]");
    if (Array.isArray(savedPresets)) presets = savedPresets.filter(p => p && typeof p.name === "string").slice(0, 30).map(p => ({name:p.name, recipe:M.normalizeRecipe(p.recipe)}));
  } catch (_) { status("저장된 모델 조합을 읽지 못했어요. 기본 조합을 확인하세요.", true); }
  initial = initial || M.defaultRecipe(template);
  const el = (tag, className, text) => { const e = document.createElement(tag); if (className) e.className = className; if (text !== undefined) e.textContent = text; return e; };
  // Use in-panel choices: native UXP popup menus can lose focus across floating panels.
  const pickers = [];
  function updatePicker(select) {
    const picker = select.modelPicker;
    if (!picker) return;
    const selected = Array.from(select.querySelectorAll("option")).find(option => option.value === select.value);
    picker.button.textContent = (selected ? selected.textContent : "선택") + " ▾";
    picker.button.setAttribute("title", select.value || picker.label);
    picker.list.innerHTML = "";
    for (const option of select.querySelectorAll("option")) {
      const choice = actionControl(el("div", "pickerOption" + (option.value === select.value ? " chosen" : ""), option.textContent));
      choice.setAttribute("title", option.value || option.textContent);
      choice.onclick = () => {
        select.value = option.value; picker.list.classList.add("hidden"); picker.button.setAttribute("aria-expanded", "false");
        updatePicker(select);
        if (select.onchange) select.onchange(); else changed();
      };
      picker.list.appendChild(choice);
    }
  }
  function installPicker(select) {
    if (select.modelPicker) return;
    const wrapper = el("div", "modelPicker"), button = actionControl(el("div", "secondary pickerButton")), list = el("div", "pickerOptions hidden");
    const label = select.getAttribute("aria-label") || "선택";
    button.setAttribute("aria-label", label); button.setAttribute("aria-expanded", "false");
    button.onclick = () => {
      const opening = list.classList.contains("hidden");
      for (const picker of pickers) { picker.list.classList.add("hidden"); picker.button.setAttribute("aria-expanded", "false"); }
      list.classList.toggle("hidden", !opening); button.setAttribute("aria-expanded", String(opening));
    };
    select.parentNode.insertBefore(wrapper, select); wrapper.appendChild(button); wrapper.appendChild(list); select.classList.add("hidden");
    select.modelPicker = {button,list,label}; pickers.push(select.modelPicker); updatePicker(select);
  }
  function options(select, files, value, placeholder) {
    select.innerHTML = "";
    const add = (file, label) => { const option = el("option", "", label); option.value = file; select.appendChild(option); };
    if (placeholder !== undefined) add("", placeholder);
    files.forEach(file => add(file, files.filter(other => M.fileKey(M.fileLabel(other)) === M.fileKey(M.fileLabel(file))).length > 1 ? file : M.fileLabel(file)));
    let selected = value;
    if (value) {
      try { selected = M.resolveFile(value, files); } catch (_) {
        if (!files.includes(value)) add(value, (loaded ? "[미설치] " : "") + M.fileLabel(value));
      }
    }
    select.value = selected || "";
    select.setAttribute("title", select.value);
    updatePicker(select);
  }
  const choices = key => available[key];
  function rows() { return Array.from($("loraRows").querySelectorAll(".loraRow")); }
  function getRecipe() {
    return M.normalizeRecipe({checkpoint: $("checkpointChoice").value, loras: rows().map(row => {
      const field = row.querySelector(".loraStrength");
      return {name: row.querySelector("select").value, enabled: row.querySelector("input[type=checkbox]").checked, strength: String(field.value).trim() ? Number(field.value) : NaN};
    })});
  }
  function addRow(value) {
    const row = el("div", "loraRow"), top = el("div", "loraTop"), bottom = el("div", "loraBottom");
    const enabled = el("input"); enabled.type = "checkbox"; enabled.checked = value.enabled; enabled.setAttribute("aria-label", "LoRA 사용");
    const select = el("select"); select.setAttribute("aria-label", "LoRA 파일"); options(select, choices("loras"), value.name, "LoRA 선택");
    const caption = el("span", "muted", "강도 · 모델/CLIP"), weight = el("input", "loraStrength");
    weight.type = "number"; weight.min = "-2"; weight.max = "2"; weight.step = "0.05"; weight.value = value.strength; weight.setAttribute("aria-label", "LoRA 강도");
    const remove = actionControl(el("div", "secondary loraRemove", "×")); remove.setAttribute("aria-label", "이 LoRA 제거"); remove.setAttribute("title", "이 LoRA 제거");
    remove.onclick = () => { releasePicker(select); row.parentNode.removeChild(row); changed(); };
    for (const field of [enabled, select, weight]) field.addEventListener("change", () => { select.setAttribute("title", select.value); changed(); });
    top.appendChild(enabled); top.appendChild(select); bottom.appendChild(caption); bottom.appendChild(weight); bottom.appendChild(remove);
    row.appendChild(top); row.appendChild(bottom); $("loraRows").appendChild(row); installPicker(select);
  }
  function setRecipe(recipe) {
    const value = M.normalizeRecipe(recipe);
    options($("checkpointChoice"), choices("checkpoints"), value.checkpoint);
    for (const row of rows()) releasePicker(row.querySelector("select"));
    $("loraRows").innerHTML = ""; value.loras.forEach(addRow);
  }
  function releasePicker(select) {
    const index = pickers.indexOf(select.modelPicker);
    if (index >= 0) pickers.splice(index, 1);
  }
  function renderPresets(selected = "") {
    $("modelPreset").innerHTML = "";
    const empty = el("option", "", "저장한 조합 선택"); empty.value = ""; $("modelPreset").appendChild(empty);
    presets.forEach((preset, index) => { const option = el("option", "", preset.name); option.value = String(index); $("modelPreset").appendChild(option); });
    $("modelPreset").value = selected;
    updatePicker($("modelPreset"));
  }
  async function refresh() {
    const base = address();
    $("modelLibraryStatus").textContent = "설치된 모델 확인 중…";
    try {
      const data = await Promise.all([request(base, "/object_info/" + encodeURIComponent(template["1"].class_type)).then(r => r.json()), request(base, "/object_info/LoraLoader").then(r => r.json())]);
      const checkpoints = data[0][template["1"].class_type].input.required.ckpt_name[0];
      const loras = data[1].LoraLoader.input.required.lora_name[0];
      if (!Array.isArray(checkpoints) || !Array.isArray(loras)) throw new Error("설치된 모델 목록 형식이 다릅니다.");
      available = {checkpoints, loras}; loaded = true;
      // Keep unfinished weights and selections intact when refreshing the inventory.
      options($("checkpointChoice"), choices("checkpoints"), $("checkpointChoice").value);
      for (const row of rows()) { const select = row.querySelector("select"); options(select, choices("loras"), select.value, "LoRA 선택"); }
      $("modelLibraryStatus").textContent = "설치된 모델 " + choices("checkpoints").length + "개 / LoRA " + choices("loras").length + "개";
    } catch (error) { loaded = false; $("modelLibraryStatus").textContent = "모델 목록을 읽지 못했어요. 새로고침하세요."; throw error; }
  }
  function validate() {
    if (!loaded) throw new Error("연결 후 모델 목록을 새로고침하세요.");
    return M.resolveRecipe(getRecipe(), available);
  }
  function updateButtons(busy) {
    $("addLora").disabled = busy || rows().length >= M.MAX_LORAS;
    $("loadModelPreset").disabled = busy || $("modelPreset").value === "";
  }
  setRecipe(initial); renderPresets();
  for (const id of ["checkpointChoice", "modelPreset"]) installPicker($(id));
  $("checkpointChoice").addEventListener("change", () => { $("checkpointChoice").setAttribute("title", $("checkpointChoice").value); changed(); });
  $("addLora").onclick = () => { if (rows().length >= M.MAX_LORAS) return; addRow({name:"",enabled:true,strength:0.5}); changed(); };
  $("refreshModels").onclick = () => operation(async () => { await refresh(); changed(); status("모델 목록을 갱신했어요."); });
  $("restoreModels").onclick = () => { setRecipe(M.defaultRecipe(template)); changed(); status("모델과 LoRA를 기본 조합으로 복원했어요."); };
  $("modelPreset").onchange = () => changed();
  $("loadModelPreset").onclick = () => operation(async () => {
    const preset = presets[Number($("modelPreset").value)];
    if (!preset || $("modelPreset").value === "") return;
    await refresh();
    const recipe = M.resolveRecipe(preset.recipe, available);
    setRecipe(recipe); changed(); status("조합 불러옴 · " + preset.name);
  });
  $("saveModelPreset").onclick = () => operation(async () => {
    const recipe = validate();
    const next = M.savePreset(presets, $("modelPresetName").value, recipe);
    storage.setItem("toobusy.modelPresets", JSON.stringify(next)); presets = next;
    renderPresets(String(presets.length - 1)); $("modelPresetName").value = "";
    changed(); status("모델·LoRA 조합을 저장했어요.");
  });
  return {getRecipe, refresh, validate, updateButtons};
}
module.exports = {createModelControls};

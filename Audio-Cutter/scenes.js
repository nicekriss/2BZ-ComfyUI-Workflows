'use strict';
let scenes = [], assets = {}, library = [], freeActive = -1, checkedScenes = new Set(), exportedScenes = [], savedSignature = '';
let autoSignature = '', autoSource = '', autoTimer = null, autoTask = null, videoShown = '', libraryRendered = '';
const blankScene = () => ({prompt: '', references: [], keyframeStart: null, keyframeEnd: null, status: 'draft', resultVideo: null});
const sceneStatusLabels = {draft: '준비 중', queued: '생성 대기', done: '생성 완료'};
function selectedScene() { return mode === 'split' ? scenes[active] : clips[freeActive]?.scene; }
function sceneList() { return mode === 'split' ? scenes : clips.map(x => x.scene); }
function sceneIndex() { return mode === 'split' ? active : freeActive; }
function projectState() { return {version: 2, project: $('project').value, mode, points, names, scenes, clips, library, view: {active, freeActive}}; }
function projectDirty() { return !!source && savedSignature !== JSON.stringify(projectState()); }
function assetLabel(id) { return library.find(x => x.id === id)?.label || assets[id]?.name || '이미지'; }
function assetUrl(id) { return '/asset?id=' + id + '&token=' + encodeURIComponent(config.token); }
function sceneControls() {
  const ready = !busy && !!source, selected = ready && !!selectedScene();
  $('save-project').disabled = !ready; $('load-project').disabled = busy;
  $('scene-fields').disabled = !selected; $('project').disabled = busy;
  $('scene-status').disabled = !selected; $('clone-scene').disabled = !selected;
  $('inherit-scene').disabled = !selected || sceneIndex() < 1;
  $('add-library').disabled = !ready; $('recover').disabled = busy;
  $('project-state').textContent = !source ? '노래를 넣고 시작하세요.' : projectDirty() ? '편집 중' : '프로젝트 저장됨';
  $('open-scene').disabled = !selected || !exportedScenes[sceneIndex()];
  if (ready) scheduleAutosave();
}
function scheduleAutosave() {
  clearTimeout(autoTimer);
  if (!source || !config || busy) return;
  if (autoSource === source.id && autoSignature === JSON.stringify(projectState())) return;
  $('autosave-state').textContent = '자동 저장 대기…';
  autoTimer = setTimeout(() => { if (!busy) flushAutoSave().catch(() => {}); }, 650);
}
async function flushAutoSave() {
  clearTimeout(autoTimer);
  if (autoTask) { await autoTask; return flushAutoSave(); }
  if (!source || !config) return;
  const signature = JSON.stringify(projectState()), id = source.id;
  if (autoSource === id && autoSignature === signature) return;
  $('autosave-state').classList.remove('error'); $('autosave-state').textContent = '자동 저장 중…';
  autoTask = api('/autosave', {id, state: JSON.parse(signature)}).then(result => {
    if (source?.id === id) { autoSignature = signature; autoSource = id; $('autosave-state').textContent = '✓ 자동 저장 ' + result.updated.slice(11); }
  }).catch(error => {
    $('autosave-state').textContent = '자동 저장 실패 · 프로젝트 저장 필요'; $('autosave-state').classList.add('error');
    status('자동 저장: ' + error.message, true); throw error;
  }).finally(() => { autoTask = null; });
  await autoTask;
}
async function prepareClose() {
  if (busy) { window.pywebview.api.close_cancel('파일 처리가 끝난 뒤 닫아주세요.'); return; }
  busy = true; controls();
  try { await flushAutoSave(); await window.pywebview.api.close_ready(); }
  catch (error) { busy = false; controls(); window.pywebview.api.close_failed(error.message); }
}
function addToLibrary(asset, label) {
  assets[asset.id] = asset;
  if (asset.kind !== 'video' && !library.some(x => x.id === asset.id)) library.push({id: asset.id, label: label || asset.name, category: '기타'});
}
function renderLibrary() {
  const signature = JSON.stringify([library, busy, !!selectedScene(), $('library-search').value]);
  if (signature === libraryRendered) return;
  libraryRendered = signature; const box = $('library-items'); box.replaceChildren();
  $('library-count').textContent = library.length;
  const query = $('library-search').value.trim().toLowerCase();
  const filtered = library.filter(item => (item.label + ' ' + item.category).toLowerCase().includes(query));
  if (!filtered.length) { const empty = document.createElement('p'); empty.className = 'queueempty'; empty.textContent = library.length ? '검색 결과가 없어요.' : '캐릭터·의상·배경을 한 번 등록해두세요.'; box.append(empty); }
  for (const item of filtered) {
    const card = document.createElement('div'); card.className = 'library-card';
    const img = document.createElement('img'); img.src = assetUrl(item.id); img.alt = item.label;
    const label = document.createElement('input'); label.value = item.label; label.disabled = busy; label.setAttribute('aria-label', item.label + ' 자료 이름');
    label.oninput = () => { item.label = label.value; scheduleAutosave(); };
    label.onchange = () => { libraryRendered = ''; renderClips(); };
    const row = document.createElement('div'); row.className = 'library-meta';
    const category = document.createElement('select'); category.setAttribute('aria-label', item.label + ' 분류'); category.disabled = busy;
    for (const name of ['캐릭터', '의상', '배경', '기타']) { const option = document.createElement('option'); option.value = name; option.textContent = name; category.append(option); }
    category.value = item.category; category.onchange = () => { item.category = category.value; renderLibrary(); scheduleAutosave(); };
    const remove = document.createElement('button'); remove.textContent = '×'; remove.disabled = busy; remove.setAttribute('aria-label', item.label + ' 자료함에서 빼기');
    remove.onclick = () => { library = library.filter(x => x.id !== item.id); renderClips(); status('자료함에서 뺐습니다. 이미 장면에 넣은 이미지는 유지됩니다.'); };
    row.append(category, remove);
    const actions = document.createElement('div'); actions.className = 'library-actions';
    for (const [text, role] of [['＋ 장면', 'references'], ['시작', 'keyframeStart'], ['끝', 'keyframeEnd']]) {
      const button = document.createElement('button'); button.textContent = text; button.disabled = busy || !selectedScene();
      button.setAttribute('aria-label', item.label + ' ' + text);
      button.onclick = () => { if (mode === 'split') remember(); const scene = selectedScene(); if (role === 'references') scene.references = [...new Set([...scene.references, item.id])]; else scene[role] = item.id; renderClips(); };
      actions.append(button);
    }
    card.append(img, label, row, actions); box.append(card);
  }
}
function renderScene() {
  if (workflow === 'audio') { sceneControls(); return; }
  const scene = selectedScene(), index = sceneIndex();
  $('scene-title').textContent = scene ? String(index + 1).padStart(2, '0') + ' · ' + (currentClips()[index]?.name || '장면 준비') : '선택한 장면을 준비하세요.';
  $('scene-help').textContent = scene ? '경계를 옮겨도 이 장면의 자료는 유지됩니다.' : '노래를 넣으세요. 자유 모드는 구간을 담은 뒤 선택합니다.';
  $('scene-count').textContent = '이미지 ' + (scene ? scene.references.length + Number(!!scene.keyframeStart) + Number(!!scene.keyframeEnd) : 0) + '개';
  if (document.activeElement !== $('scene-prompt')) $('scene-prompt').value = scene?.prompt || '';
  $('scene-status').value = scene?.status || 'draft';
  $('clone-scene').textContent = mode === 'split' ? '블록 나눠 복제' : '장면 복제';
  const box = $('references'); box.replaceChildren();
  scene?.references.forEach((id, i) => {
    const card = document.createElement('div'); card.className = 'ref-card';
    const img = document.createElement('img'); img.src = assetUrl(id); img.alt = assetLabel(id);
    const name = document.createElement('small'); name.textContent = img.alt; name.title = img.alt;
    const actions = document.createElement('div'); actions.className = 'ref-actions';
    const num = document.createElement('span'); num.textContent = String(i + 1).padStart(2, '0'); actions.append(num);
    for (const [label, step] of [['←', -1], ['→', 1], ['×', 0]]) {
      const button = document.createElement('button'); button.textContent = label;
      button.setAttribute('aria-label', '레퍼런스 ' + (i + 1) + (step === -1 ? ' 앞으로' : step === 1 ? ' 뒤로' : ' 삭제'));
      button.disabled = step !== 0 && (i + step < 0 || i + step >= scene.references.length);
      button.onclick = () => { if (busy) return; if (mode === 'split') remember(); if (!step) scene.references.splice(i, 1); else [scene.references[i], scene.references[i + step]] = [scene.references[i + step], scene.references[i]]; renderClips(); };
      actions.append(button);
    }
    card.append(img, name, actions); box.append(card);
  });
  for (const [edge, key] of [['start', 'keyframeStart'], ['end', 'keyframeEnd']]) {
    const pick = $('pick-' + edge); pick.replaceChildren();
    if (scene?.[key]) { const img = document.createElement('img'); img.src = assetUrl(scene[key]); img.alt = assetLabel(scene[key]); pick.append(img); }
    else pick.textContent = '＋ ' + (edge === 'start' ? '시작' : '끝') + ' 이미지';
    $('remove-' + edge).disabled = !scene?.[key];
  }
  const key = scene?.resultVideo || '', video = $('result-video');
  if (videoShown !== key) { video.pause(); if (key) video.src = assetUrl(key); else video.removeAttribute('src'); video.load(); videoShown = key; }
  video.hidden = !key; $('video-name').textContent = key ? assets[key]?.name || '결과 영상' : '결과 영상을 넣으면 생성 완료로 표시합니다.';
  $('remove-video').disabled = !key; $('next-frame').disabled = !key || index >= sceneList().length - 1;
  sceneControls(); renderLibrary();
}
async function uploadFiles(route, file) {
  const response = await fetch(route + '?name=' + encodeURIComponent(file.name), {method: 'POST', headers: {'X-Cutter-Token': config.token}, body: file});
  const result = await response.json(); if (!response.ok) throw Error(result.error); return result;
}
async function addImages(files, key = 'references') {
  const scene = selectedScene(); if (!source || busy || !files.length || (key !== 'library' && !scene)) return;
  if (!['references', 'library'].includes(key)) files = [files[0]];
  busy = true; renderClips(); status('이미지를 준비하고 있어요…');
  try {
    const added = []; for (const file of files) added.push(await uploadFiles('/asset-upload', file));
    if (mode === 'split' && key !== 'library') remember();
    for (const asset of added) addToLibrary(asset);
    if (key === 'references') scene.references = [...new Set([...scene.references, ...added.map(x => x.id)])];
    else if (key !== 'library') scene[key] = added[0].id;
    status(added.length + '개 이미지를 넣었습니다. 공통 자료함에서도 다시 쓸 수 있어요.');
  } catch (error) { status(error.message, true); }
  finally { busy = false; renderClips(); }
}
function bindDrop(element, action) {
  for (const event of ['dragenter', 'dragover']) element.addEventListener(event, e => { e.preventDefault(); if (!busy && source) element.classList.add('drag'); });
  element.addEventListener('dragleave', () => element.classList.remove('drag'));
  element.addEventListener('drop', e => { e.preventDefault(); element.classList.remove('drag'); action([...e.dataTransfer.files]); });
}
function selectFree(index, listen = false) {
  stop(); freeActive = index; const clip = clips[index]; fixedLength = 0;
  selection = {start: clip.start, end: clip.end}; $('clipname').value = clip.name;
  sync(); renderClips(); revealSelection(); if (listen) play(true);
}
function copyPreparation(scene) { return {...structuredClone(scene), status: 'draft', resultVideo: null}; }
async function addVideo(file) {
  const scene = selectedScene(); if (!file || busy || !scene) return;
  busy = true; stop(); renderClips(); status('결과 영상을 연결하고 재생용 미리보기를 만들고 있어요…');
  try { const asset = await uploadFiles('/video-upload', file); if (mode === 'split') remember(); assets[asset.id] = asset; scene.resultVideo = asset.id; scene.status = 'done'; status('결과 영상을 연결했습니다. 마지막 프레임을 다음 장면으로 이어갈 수 있어요.'); }
  catch (error) { status(error.message, true); } finally { busy = false; renderClips(); }
}
async function restoreState(result, recovered = false) {
  const info = result.source;
  const response = await fetch('/preview?id=' + info.id + '&token=' + encodeURIComponent(config.token));
  if (!response.ok) throw Error('프로젝트 음악을 읽을 수 없습니다.');
  audioContext ||= new AudioContext(); const decoded = await audioContext.decodeAudioData(await response.arrayBuffer());
  const value = result.state;
  source = info; buffer = decoded; points = value.points; names = value.names; scenes = value.scenes; clips = value.clips; mode = value.mode; library = [...new Map(value.library.map(x => [x.id, x])).values()];
  assets = Object.fromEntries(result.assets.map(x => [x.id, x]));
  active = value.view?.active || 0; freeActive = value.view?.freeActive ?? (clips.length ? 0 : -1); history = []; checkedScenes.clear(); exportedScenes = []; libraryRendered = '';
  freeSelection = clips[freeActive] ? {start: clips[freeActive].start, end: clips[freeActive].end} : {start: 0, end: Math.min(10, info.duration)};
  selection = {...freeSelection}; zoom = 1; offset = 0;
  $('project').value = value.project; $('filename').textContent = info.name; $('filemeta').textContent = format(info.duration) + ' · 복원 완료';
  $('empty').hidden = true; $('result').textContent = '';
  savedSignature = recovered ? '' : JSON.stringify(projectState());
  autoSignature = recovered ? JSON.stringify(projectState()) : ''; autoSource = info.id;
  $('autosave-state').textContent = recovered ? '✓ 이전 자동 저장 복원됨' : '자동 저장 대기…';
  modeUI(); panSetup(); sync(); renderClips();
  status(recovered ? '이전 작업을 복구했습니다. 이어서 편집하세요.' : '프로젝트의 자료와 결과 영상을 복원했습니다.');
}
async function recoverDraft(id, initial = false) {
  if (!id || (busy && !initial)) return;
  if (source) { try { await flushAutoSave(); } catch { return; } }
  busy = true; stop(); controls(); status('이전 작업을 복구하고 있어요…');
  try { await restoreState(await api('/recover', {id}), true); }
  catch (error) { status(error.message, true); }
  finally { busy = false; controls(); renderClips(); }
}
async function initRecovery(drafts) {
  if (!drafts.length) return;
  const box = $('recovery-choice'); box.replaceChildren();
  for (const draft of drafts) { const option = document.createElement('option'); option.value = draft.id; option.textContent = draft.project + ' · ' + draft.updated.replace('T', ' '); box.append(option); }
  $('recovery-bar').hidden = false;
  // Recover only when the user chooses to continue a recent task.
}
function initScenes() {
  $('add-refs').onclick = () => $('ref-files').click();
  $('ref-drop').onclick = () => { if (!busy && selectedScene()) $('ref-files').click(); };
  $('ref-drop').onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); $('ref-drop').click(); } };
  $('ref-files').onchange = e => { addImages([...e.target.files]); e.target.value = ''; };
  bindDrop($('ref-drop'), files => addImages(files));
  $('add-library').onclick = () => $('library-files').click();
  $('library-files').onchange = e => { addImages([...e.target.files], 'library'); e.target.value = ''; };
  bindDrop($('library-drop'), files => addImages(files, 'library'));
  $('library-search').oninput = renderLibrary;
  for (const [edge, key] of [['start', 'keyframeStart'], ['end', 'keyframeEnd']]) {
    $('pick-' + edge).onclick = () => $(edge + '-file').click();
    $(edge + '-file').onchange = e => { addImages([...e.target.files], key); e.target.value = ''; };
    $('remove-' + edge).onclick = () => { if (mode === 'split') remember(); selectedScene()[key] = null; renderClips(); };
    bindDrop($('pick-' + edge), files => addImages(files, key));
  }
  $('scene-prompt').onfocus = () => { if (mode === 'split') remember(); };
  $('scene-prompt').oninput = () => { if (selectedScene()) { selectedScene().prompt = $('scene-prompt').value; renderClips(); } };
  $('scene-status').onchange = () => { if (mode === 'split') remember(); selectedScene().status = $('scene-status').value; renderClips(); };
  $('project').oninput = sceneControls;
  $('copy-prompt').onclick = async () => {
    const value = selectedScene()?.prompt; if (!value) { status('복사할 프롬프트를 먼저 적어주세요.'); return; }
    try { if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(value); else { $('scene-prompt').focus(); $('scene-prompt').select(); if (!document.execCommand('copy')) throw Error(); } status('프롬프트를 복사했습니다.'); }
    catch { $('scene-prompt').focus(); $('scene-prompt').select(); status('선택된 프롬프트를 Ctrl+C로 복사해주세요.'); }
  };
  $('apply-refs').onclick = () => {
    const refs = selectedScene()?.references; if (!refs?.length) { status('현재 장면에 레퍼런스를 먼저 넣어주세요.'); return; }
    const targets = sceneList().filter((_, i) => $('apply-target').value === 'all' || checkedScenes.has(i));
    if (!targets.length) { status('목록에서 적용할 블록을 체크해주세요.'); return; }
    if (mode === 'split') remember();
    for (const item of targets) item.references = [...new Set([...item.references, ...refs])];
    renderClips(); status(targets.length + '개 장면에 공통 레퍼런스를 추가했습니다.');
  };
  $('clone-scene').onclick = () => {
    const scene = selectedScene(); if (!scene || busy) return;
    const copied = copyPreparation(scene), index = sceneIndex(), name = currentClips()[index].name;
    if (mode === 'split') { remember(); const midpoint = (points[active] + points[active + 1]) / 2; points.splice(active + 1, 0, midpoint); while (names.length < scenes.length) names.push(''); scenes.splice(active + 1, 0, copied); names.splice(active + 1, 0, name + ' 복제'); active++; }
    else { clips.splice(index + 1, 0, {...clips[index], name: name + ' 복제', scene: copied}); freeActive++; }
    checkedScenes.clear(); exportedScenes = []; stop(); sync(); renderClips();
    status(mode === 'split' ? '블록을 둘로 나누고 자료를 복제했습니다. 전체 음악 길이는 유지됩니다.' : '같은 구간의 장면을 복제했습니다.');
  };
  $('inherit-scene').onclick = () => {
    const index = sceneIndex(), current = selectedScene(); if (index < 1 || busy) return;
    if ((current.prompt || current.references.length || current.keyframeStart || current.keyframeEnd || current.resultVideo) && !confirm('현재 장면의 자료를 이전 장면의 이미지·프롬프트로 바꿀까요? 연결된 결과 영상은 해제됩니다.')) return;
    if (mode === 'split') remember();
    const copied = copyPreparation(sceneList()[index - 1]);
    if (mode === 'split') scenes[index] = copied; else clips[index].scene = copied;
    renderClips(); status('이전 장면의 이미지와 프롬프트를 가져왔습니다. 동작만 바꿔 이어가세요.');
  };
  $('add-video').onclick = () => $('video-file').click();
  $('video-file').onchange = e => { addVideo(e.target.files[0]); e.target.value = ''; };
  bindDrop($('video-drop'), files => addVideo(files[0]));
  $('remove-video').onclick = () => { if (mode === 'split') remember(); selectedScene().resultVideo = null; selectedScene().status = 'draft'; renderClips(); };
  $('next-frame').onclick = async () => {
    const index = sceneIndex(), scene = selectedScene(), next = sceneList()[index + 1]; if (!scene?.resultVideo || !next || busy) return;
    if (next.keyframeStart && !confirm('다음 장면의 시작 이미지를 이 영상의 마지막 프레임으로 바꿀까요?')) return;
    busy = true; renderClips(); status('영상의 마지막 프레임을 추출하고 있어요…');
    try { const asset = await api('/last-frame', {id: scene.resultVideo}); if (mode === 'split') remember(); addToLibrary(asset, currentClips()[index].name + ' · 마지막 프레임'); next.keyframeStart = asset.id; next.status = 'draft'; status('다음 장면의 시작 이미지로 연결했습니다.'); }
    catch (error) { status(error.message, true); } finally { busy = false; renderClips(); }
  };
  $('open-scene').onclick = async () => { try { await api('/open-scene', {id: exportedScenes[sceneIndex()]}); } catch (e) { status(e.message, true); } };
  $('save-project').onclick = async () => {
    if (!source || busy) return; const state = projectState(); busy = true; renderClips(); status('프로젝트를 저장하고 있어요…');
    try { const result = await api('/project-save', {id: source.id, state}); savedSignature = JSON.stringify(state); $('result').textContent = '프로젝트 저장 완료\n' + result.path; status('프로젝트를 저장하고 폴더를 열었습니다.'); }
    catch (e) { status(e.message, true); } finally { busy = false; renderClips(); }
  };
  $('load-project').onclick = () => $('project-file').click();
  $('project-file').onchange = async e => {
    const file = e.target.files[0]; e.target.value = ''; if (!file || busy) return;
    try { await flushAutoSave(); } catch { return; }
    busy = true; stop(); renderClips(); status('프로젝트를 복원하고 있어요…');
    try { await restoreState(await uploadFiles('/project-open', file)); }
    catch (error) { status(error.message, true); } finally { busy = false; renderClips(); }
  };
  $('recover').onclick = () => recoverDraft($('recovery-choice').value);
  $('hide-recovery').onclick = () => $('recovery-bar').hidden = true;
  setInterval(() => { if (source && !busy && !autoTask && autoSignature !== JSON.stringify(projectState())) flushAutoSave().catch(() => {}); }, 5000);
}

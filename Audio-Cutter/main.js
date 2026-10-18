'use strict';
const $ = id => document.getElementById(id);
const canvas = $('wave'), ctx = canvas.getContext('2d');
let config, source = null, buffer = null, audioContext = null, player = null, playbackTimer = null;
let selection = {start: 0, end: 10}, fixedLength = 10, clips = [], zoom = 1, offset = 0, drag = null;
let workflow = 'audio';
let mode = 'split', points = [], names = [], active = 0, history = [], freeSelection = {start: 0, end: 10};
let playing = false, playStarted = 0, playOffset = 0, selectionPlayback = true, busy = true, playVersion = 0;
const waveColors = {background: '#191b1f', accent: '#d5b366', muted: '#989da6', boundary: '#41454d', fill: '#b4b8bf', selection: '#302c23', waveform: '#757b85', playhead: '#e0e1df'};
const format = t => {
  const ms = Math.max(0, Math.round(t * 1000));
  return String(Math.floor(ms / 60000)).padStart(2, '0') + ':' + String(Math.floor(ms / 1000) % 60).padStart(2, '0') + '.' + String(ms % 1000).padStart(3, '0');
};
function status(text, error = false) { $('status').textContent = text; $('status').classList.toggle('error', error); }
function currentClips() { return mode === 'split' ? Timeline.clips(points, names).map((clip, i) => ({...clip, scene: scenes[i] || blankScene()})) : clips; }
function remember() {
  const snapshot = {points: points.slice(), names: names.slice(), scenes: structuredClone(scenes), active};
  if (JSON.stringify(history[history.length - 1]) !== JSON.stringify(snapshot)) history.push(snapshot);
  if (history.length > 50) history.shift();
  controls();
}
function undo() {
  if (busy || mode !== 'split' || !history.length) return;
  stop(); const previous = history.pop();
  points = previous.points; names = previous.names; scenes = previous.scenes; active = previous.active; checkedScenes.clear(); exportedScenes = [];
  sync(); renderClips(); status('이전 경계로 되돌렸습니다.');
}
async function api(route, body) {
  const r = await fetch(route, {method: 'POST', headers: {'X-Cutter-Token': config.token, 'Content-Type': 'application/json'}, body: JSON.stringify(body)});
  const result = await r.json(); if (!r.ok) throw Error(result.error || '요청에 실패했습니다.'); return result;
}
function setWorkflow(next) {
  if (busy || workflow === next) return;
  workflow = next; applyWorkflow(); sync(); renderClips();
}
function applyWorkflow() {
  const audio = workflow === 'audio';
  document.body.classList.toggle('audio-workspace', audio);
  for (const name of ['audio', 'mv']) {
    $('workflow-' + name).classList.toggle('selected', workflow === name);
    $('workflow-' + name).setAttribute('aria-pressed', String(workflow === name));
  }
  if (audio) $('audio-name').append($('clipname'));
  else $('scene-meta').prepend($('clipname'));
  $('clipname').setAttribute('aria-label', audio ? '선택 구간 이름' : '장면 이름');
  if (mode === 'free') $('clipname').value = clips[freeActive]?.name || '';
  $('workflow-help').textContent = audio ? '노래 넣고, 원하는 길이로 자르고, MP3로 저장.' : '구간마다 이미지·프롬프트를 담아 장면 꾸러미로 저장.';
  $('export').textContent = audio ? 'MP3 저장' : '장면 꾸러미 저장';
  $('list-title').textContent = mode === 'split' ? '전체 블록' : audio ? '담은 구간' : '장면 바구니';
  if (audio) $('result-video').pause();
}
function controls() {
  sceneControls();
  const ready = !!buffer && !busy;
  for (const id of ['play', 'whole', 'start', 'end', 'previous', 'next', 'add', 'split', 'clipname']) $(id).disabled = !ready;
  $('export').disabled = !ready || !currentClips().length;
  $('clear').disabled = busy || !clips.length; $('file').disabled = busy;
  $('split-seconds').disabled = busy; $('undo').disabled = busy || !history.length;
  for (const id of ['mode-split', 'mode-free', 'workflow-audio', 'workflow-mv']) $(id).disabled = busy;
  for (const b of $('presets').children) b.disabled = busy;
  if (mode === 'split') {
    $('start').disabled = !ready || active === 0;
    $('end').disabled = !ready || active === points.length - 2;
    $('previous').disabled = !ready || active === 0;
    $('next').disabled = !ready || active >= points.length - 2;
  }
}
function sync(editing) {
  if (mode === 'split' && points.length) selection = {start: points[active], end: points[active + 1]};
  if (!playing) $('playtime').textContent = format(selection.start);
  if (editing !== 'start') $('start').value = selection.start.toFixed(3);
  if (editing !== 'end') $('end').value = selection.end.toFixed(3);
  $('duration').replaceChildren(document.createTextNode((selection.end - selection.start).toFixed(2)));
  const unit = document.createElement('span'); unit.textContent = '초'; $('duration').append(unit);
  for (const b of $('presets').children) b.classList.toggle('selected', Number(b.dataset.seconds) === fixedLength);
  if (mode === 'split') {
    if (editing !== 'name') $('clipname').value = names[active] || '';
    $('clipname').placeholder = '선택한 블록 이름 (예: 도입부, 후렴)';
    $('editor-title').textContent = points.length ? '블록 ' + String(active + 1).padStart(2, '0') + ' · 경계를 다듬어요.' : '쫙 나누고, 딱 맞추고.';
    $('split-summary').textContent = points.length ? (points.length - 1) + '개 블록 · 전체 ' + format(source.duration) + ' · 빈틈 없이 연결' : '마지막 남는 구간까지 모두 담습니다.';
  }
  controls(); draw();
}
function setMode(next) {
  if (mode === next || busy) return;
  stop();
  if (mode === 'free') freeSelection = {...selection};
  mode = next; selection = {...freeSelection}; checkedScenes.clear(); exportedScenes = [];
  modeUI(); sync(); renderClips();
}
function modeUI() {
  const split = mode === 'split';
  $('split-tools').hidden = !split; $('free-length').hidden = split; $('add').hidden = split; $('clear').hidden = split;
  $('workspace').classList.toggle('split-mode', split);
  for (const name of ['split', 'free']) { $('mode-' + name).classList.toggle('selected', mode === name); $('mode-' + name).setAttribute('aria-pressed', String(mode === name)); }
  $('list-title').textContent = split ? '전체 블록' : workflow === 'audio' ? '담은 구간' : '장면 바구니';
  $('editor-title').textContent = split ? '쫙 나누고, 딱 맞추고.' : '딱, 이 부분만.';
  $('clipname').value = ''; $('clipname').placeholder = split ? '선택한 블록 이름' : '장면 이름 (예: 도입부, 솔로, 후렴)';
  $('edit-help').textContent = split ? '클릭: 반복 듣기 · 경계 드래그: 이웃과 조정 · 내부 드래그: 블록 이동' : '고정 길이: 통째로 이동 · 자유: 양끝 조절';
  $('keyboard-help').textContent = split ? '곡의 처음·끝은 고정 · 경계는 이웃을 넘지 않음 · Space 재생 · ← → 이동 · Ctrl+Z 되돌리기' : 'Space 재생 / 정지 · ← → 0.1초 이동 · Shift + ← → 1초 이동';
}
function splitAll(initial = false) {
  if (!source) return;
  const seconds = Number($('split-seconds').value);
  let next;
  try { next = Timeline.split(source.duration, seconds); } catch (e) { status(e.message, true); return; }
  if (!initial && scenes.some(x => x.prompt || x.references.length || x.keyframeStart || x.keyframeEnd) && !confirm('전체를 다시 나누면 새 장면 목록이 됩니다. 이미지·프롬프트를 유지하려면 취소하고 경계만 조절하세요. 다시 나눌까요? (되돌리기 가능)')) return;
  if (!initial) remember();
  stop(); points = next; names = []; scenes = points.slice(1).map(blankScene); active = 0; checkedScenes.clear(); exportedScenes = [];
  sync(); renderClips(); status((points.length - 1) + '개로 나눴어요. 블록을 눌러 듣고 경계를 드래그하세요.');
}
function setStart(value, editing) {
  if (!source) return; stop();
  if (mode === 'split') { points = Timeline.move(points, active, value - selection.start); }
  else {
    const length = Math.min(fixedLength || selection.end - selection.start, source.duration);
    selection.start = Math.max(0, Math.min(value, source.duration - length)); selection.end = selection.start + length;
  }
  sync(editing); if (mode === 'split') renderClips();
}
function viewSpan() { return source ? source.duration / zoom : 1; }
function panSetup() {
  const max = source ? Math.max(0, source.duration - viewSpan()) : 0;
  offset = Math.max(0, Math.min(offset, max)); $('pan').max = max; $('pan').value = offset; $('pan').disabled = !max; $('zoomvalue').textContent = zoom === 1 ? '전체' : zoom + '×';
}
function revealSelection() {
  if (selection.start < offset || selection.end > offset + viewSpan()) offset = Math.max(0, (selection.start + selection.end) / 2 - viewSpan() / 2);
  panSetup(); draw();
}
function choose(index, listen = true) {
  stop(); active = index; sync(); renderClips(); revealSelection(); if (listen) play(true);
}
function draw() {
  const rect = canvas.getBoundingClientRect(), ratio = window.devicePixelRatio || 1;
  canvas.width = Math.round(rect.width * ratio); canvas.height = Math.round(rect.height * ratio); ctx.scale(ratio, ratio);
  const w = rect.width, h = rect.height;
  ctx.fillStyle = waveColors.background; ctx.fillRect(0, 0, w, h); if (!buffer || !w) return;
  const span = viewSpan(), x = t => (t - offset) / span * w, a = x(selection.start), b = x(selection.end);
  if (mode === 'split') {
    for (let i = 0; i < points.length - 1; i++) {
      const left = x(points[i]), right = x(points[i + 1]);
      if (right < 0 || left > w) continue;
      ctx.globalAlpha = i === active ? .12 : (i % 2 ? .025 : 0); ctx.fillStyle = i === active ? waveColors.accent : waveColors.fill; ctx.fillRect(left, 24, right - left, h - 24); ctx.globalAlpha = 1;
      ctx.fillStyle = i === active ? waveColors.accent : waveColors.muted; ctx.font = '12px Segoe UI';
      if (right - Math.max(left, 0) > 22) ctx.fillText(String(i + 1).padStart(2, '0'), Math.max(left + 5, 5), 40);
      ctx.fillStyle = waveColors.boundary; ctx.fillRect(left, 25, 1, h - 25);
    }
  } else { ctx.fillStyle = waveColors.selection; ctx.fillRect(a, 0, b - a, h); }
  ctx.strokeStyle = waveColors.boundary; ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const px = i * w / 4; ctx.fillStyle = waveColors.muted; ctx.font = '11px Segoe UI';
    ctx.fillText(format(offset + i * span / 4).slice(0, zoom > 8 ? 9 : 5), Math.min(px + 4, w - 58), 16);
  }
  const samples = buffer.getChannelData(0), rate = buffer.sampleRate, middle = h * .59, amp = h * .30;
  for (let px = 0; px < w; px++) {
    const start = Math.floor((offset + px / w * span) * rate), end = Math.min(samples.length, Math.ceil((offset + (px + 1) / w * span) * rate));
    let min = 0, max = 0; const step = Math.max(1, Math.floor((end - start) / 100));
    for (let i = start; i < end; i += step) { min = Math.min(min, samples[i]); max = Math.max(max, samples[i]); }
    ctx.strokeStyle = px >= a && px <= b ? waveColors.accent : waveColors.waveform; ctx.beginPath(); ctx.moveTo(px, middle + min * amp); ctx.lineTo(px, middle + max * amp); ctx.stroke();
  }
  ctx.fillStyle = waveColors.accent;
  for (const px of [a, b]) if (px >= 0 && px <= w) { ctx.fillRect(px - 1, 25, 2, h - 25); ctx.fillRect(px - 4, h * .5, 8, 30); }
  if (playing) { ctx.fillStyle = waveColors.playhead; ctx.fillRect(x(currentPosition()), 23, 2, h - 23); }
}
function currentPosition() {
  if (!playing) return selection.start;
  const elapsed = audioContext.currentTime - playStarted;
  return selectionPlayback && $('loop').checked ? selection.start + (elapsed % (selection.end - selection.start)) : Math.min(playOffset + elapsed, buffer.duration);
}
function stop() {
  playVersion++;
  if (player) { player.onended = null; player.stop(); player.disconnect(); player = null; }
  playing = false; clearInterval(playbackTimer); $('play').textContent = '▶ 선택 구간 듣기'; $('whole').textContent = '처음부터 듣기'; $('playtime').textContent = format(selection.start); draw();
}
async function play(selected = true) {
  if (!buffer || busy) return; if (playing) { stop(); return; }
  const version = ++playVersion; await audioContext.resume(); if (version !== playVersion) return;
  selectionPlayback = selected; player = audioContext.createBufferSource(); player.buffer = buffer; player.connect(audioContext.destination);
  playOffset = selected ? selection.start : 0; playStarted = audioContext.currentTime; player.loop = selected && $('loop').checked;
  player.loopStart = selection.start; player.loopEnd = selection.end; player.onended = stop; playing = true;
  if (player.loop) player.start(0, playOffset); else player.start(0, playOffset, selected ? selection.end - selection.start : buffer.duration);
  $('play').textContent = '■ 정지'; $('whole').textContent = selected ? '처음부터 듣기' : '■ 정지';
  playbackTimer = setInterval(() => { $('playtime').textContent = format(currentPosition()); draw(); }, 40); draw();
}
async function load(file) {
  if (!file || busy) return;
  if (source) { try { await flushAutoSave(); } catch { return; } }
  busy = true; controls(); stop(); status('음악을 읽고 파형을 준비하고 있어요…');
  try {
    const r = await fetch('/upload?name=' + encodeURIComponent(file.name), {method: 'POST', headers: {'X-Cutter-Token': config.token}, body: file});
    const info = await r.json(); if (!r.ok) throw Error(info.error);
    const response = await fetch('/preview?id=' + info.id + '&token=' + encodeURIComponent(config.token));
    if (!response.ok) throw Error('미리듣기 파일을 읽지 못했습니다.');
    audioContext ||= new AudioContext(); const decoded = await audioContext.decodeAudioData(await response.arrayBuffer());
    source = info; buffer = decoded; source.duration = Math.min(source.duration, buffer.duration);
    clips = []; scenes = []; assets = {}; library = []; libraryRendered = ''; autoSignature = ''; autoSource = ''; freeActive = -1; checkedScenes.clear(); exportedScenes = []; savedSignature = ''; history = []; names = []; points = []; zoom = 1; offset = 0; active = 0;
    freeSelection = {start: 0, end: Math.min(fixedLength || 10, source.duration)}; selection = {...freeSelection};
    $('filename').textContent = info.name; $('filemeta').textContent = format(source.duration) + ' · ' + buffer.numberOfChannels + '채널 · 원본은 수정하지 않습니다';
    $('project').value = file.name.replace(/\.[^.]+$/, ''); $('empty').hidden = true; $('result').textContent = '';
    if (!(Number($('split-seconds').value) > 0)) $('split-seconds').value = '10';
    points = Timeline.split(source.duration, Number($('split-seconds').value)); scenes = points.slice(1).map(blankScene);
    panSetup(); sync(); renderClips(); status(mode === 'split' ? (points.length - 1) + '개로 나눴어요. 경계를 다듬거나 바로 저장하세요.' : '파형을 드래그해서 원하는 구간을 고르세요.');
  } catch (e) { status(e.message, true); }
  finally { busy = false; renderClips(); controls(); $('file').value = ''; }
}
$('file').addEventListener('change', e => load(e.target.files[0]));
for (const event of ['dragenter', 'dragover']) $('drop').addEventListener(event, e => { e.preventDefault(); $('drop').classList.add('drag'); });
$('drop').addEventListener('dragleave', () => $('drop').classList.remove('drag'));
$('drop').addEventListener('drop', e => { e.preventDefault(); $('drop').classList.remove('drag'); load(e.dataTransfer.files[0]); });
$('drop').addEventListener('keydown', e => { if (e.code === 'Enter' || e.code === 'Space') { e.preventDefault(); e.stopPropagation(); if (!busy) $('file').click(); } });
$('mode-split').onclick = () => setMode('split'); $('mode-free').onclick = () => setMode('free');
$('split').onclick = () => splitAll(); $('undo').onclick = undo;
$('presets').onclick = e => { if (!e.target.dataset.seconds) return; fixedLength = Number(e.target.dataset.seconds); if (source) setStart(selection.start); else sync(); };
for (const edge of ['start', 'end']) {
  $(edge).addEventListener('focus', () => { if (mode === 'split' && source) remember(); });
  $(edge).addEventListener('input', () => {
    const n = Number($(edge).value); if (!source || !Number.isFinite(n) || $(edge).value === '') return; stop();
    if (mode === 'split') { points = Timeline.boundary(points, active + (edge === 'end' ? 1 : 0), n); sync(edge); renderClips(); }
    else if (fixedLength) setStart(edge === 'start' ? n : n - Math.min(fixedLength, source.duration), edge);
    else { if (edge === 'start') selection.start = Math.max(0, Math.min(n, selection.end - .01)); else selection.end = Math.min(source.duration, Math.max(n, selection.start + .01)); sync(edge); }
  });
  $(edge).addEventListener('blur', () => sync());
}
$('clipname').addEventListener('focus', () => { if (mode === 'split' && source) remember(); });
$('clipname').addEventListener('input', () => { if (mode === 'split') names[active] = $('clipname').value.trim(); else if (clips[freeActive]) clips[freeActive].name = $('clipname').value.trim() || '장면'; renderClips(); });
function timeAt(e) { const r = canvas.getBoundingClientRect(); return Math.max(0, Math.min(source.duration, offset + (e.clientX - r.left) / r.width * viewSpan())); }
canvas.addEventListener('pointerdown', e => {
  if (!source || busy) return; stop(); canvas.focus(); canvas.setPointerCapture(e.pointerId);
  const t = timeAt(e), tol = viewSpan() * 7 / canvas.clientWidth;
  if (mode === 'split') {
    let edge = -1, distance = Infinity;
    for (let i = 1; i < points.length - 1; i++) if (Math.abs(points[i] - t) < Math.min(tol, distance)) { edge = i; distance = Math.abs(points[i] - t); }
    if (edge < 0) active = Math.min(points.length - 2, points.findIndex((value, i) => i > 0 && value > t) - 1);
    if (active < 0) active = points.length - 2;
    remember(); drag = {kind: edge >= 0 ? 'boundary' : 'block', edge, t, x: e.clientX, points: points.slice(), moved: false};
    sync(); renderClips(); return;
  }
  let kind;
  if (fixedLength) { kind = 'move'; if (t < selection.start || t > selection.end) setStart(t); }
  else if (Math.abs(t - selection.start) < tol) kind = 'start';
  else if (Math.abs(t - selection.end) < tol) kind = 'end';
  else if (t > selection.start && t < selection.end) kind = 'move';
  else { kind = 'new'; selection = {start: Math.min(t, Math.max(0, source.duration - .01)), end: Math.min(source.duration, t + .01)}; }
  drag = {kind, t, start: selection.start, end: selection.end}; sync();
});
canvas.addEventListener('pointermove', e => {
  if (!drag) return; const t = timeAt(e);
  if (mode === 'split') {
    if (Math.abs(e.clientX - drag.x) < 3 && !drag.moved) return; drag.moved = true;
    points = drag.kind === 'boundary' ? Timeline.boundary(drag.points, drag.edge, t) : Timeline.move(drag.points, active, t - drag.t);
    sync(); renderClips(); return;
  }
  if (drag.kind === 'move') { const len = drag.end - drag.start; selection.start = Math.max(0, Math.min(source.duration - len, drag.start + t - drag.t)); selection.end = selection.start + len; }
  else if (drag.kind === 'start') selection.start = Math.max(0, Math.min(t, selection.end - .01));
  else if (drag.kind === 'end') selection.end = Math.min(source.duration, Math.max(t, selection.start + .01));
  else { selection.start = Math.min(t, drag.t); selection.end = Math.max(t, drag.t); if (selection.end - selection.start < .01) { selection.start = Math.max(0, selection.end - .01); selection.end = Math.min(source.duration, selection.start + .01); } }
  sync();
});
canvas.addEventListener('pointerup', () => { const click = drag && mode === 'split' && drag.kind === 'block' && !drag.moved; drag = null; if (click) play(true); });
for (const event of ['pointercancel', 'lostpointercapture']) canvas.addEventListener(event, () => drag = null);
function changeZoom(mult) { if (!source) return; zoom = Math.max(1, Math.min(64, zoom * mult)); offset = Math.max(0, (selection.start + selection.end) / 2 - viewSpan() / 2); panSetup(); draw(); }
$('zoomin').onclick = () => changeZoom(2); $('zoomout').onclick = () => changeZoom(.5);
$('pan').oninput = () => { offset = Number($('pan').value); draw(); };
$('play').onclick = () => play(true); $('whole').onclick = () => play(false); $('loop').onchange = () => { if (playing) stop(); };
$('previous').onclick = () => mode === 'split' ? choose(active - 1) : setStart(selection.start - (selection.end - selection.start));
$('next').onclick = () => mode === 'split' ? choose(active + 1) : setStart(selection.end);
$('add').onclick = () => {
  if (!source || selection.end <= selection.start) return;
  clips.push({...selection, name: $('clipname').value.trim() || '장면 ' + String(clips.length + 1).padStart(2, '0'), scene: blankScene()});
  freeActive = clips.length - 1; $('clipname').value = ''; renderClips(); status('구간을 담았습니다. 다음 구간을 고르거나 MP3로 저장하세요.');
};
function renderClips() {
  const box = $('clips'), scrollTop = box.scrollTop, list = currentClips(); box.replaceChildren(); $('count').textContent = list.length;
  if (!list.length) { const empty = document.createElement('div'); empty.className = 'queueempty'; empty.textContent = mode === 'split' ? '노래를 넣으면 전체가 블록으로 나뉩니다.' : '좋아하는 구간을 담아보세요.'; box.append(empty); }
  list.forEach((clip, i) => {
    const row = document.createElement('div'); row.className = 'clip' + (i === (mode === 'split' ? active : freeActive) ? ' active' : '');
    const num = document.createElement('span'); num.className = 'num'; num.textContent = String(i + 1).padStart(2, '0');
    const info = document.createElement('button'); info.className = 'info';
    info.disabled = busy; info.setAttribute('aria-label', (i + 1) + '번 블록 선택'); info.onclick = () => mode === 'split' ? choose(i, false) : selectFree(i);
    const title = document.createElement('strong'); title.textContent = clip.name;
    const time = document.createElement('small'); time.textContent = format(clip.start) + ' → ' + format(clip.end) + ' / ' + (clip.end - clip.start).toFixed(2) + '초'; info.append(title, time);
    const badge = document.createElement('span'); badge.className = 'scene-badge'; const scene = clip.scene || blankScene(); badge.textContent = sceneStatusLabels[scene.status || 'draft'] + (scene.resultVideo ? ' · 영상 ✓' : '') + ' · 레퍼런스 ' + scene.references.length + ' · 키프레임 ' + (Number(!!scene.keyframeStart) + Number(!!scene.keyframeEnd)) + (scene.prompt ? ' · 프롬프트 ✓' : ''); info.append(badge);
    const preview = document.createElement('button'); preview.textContent = '▶'; preview.setAttribute('aria-label', clip.name + ' 듣기'); preview.disabled = busy;
    preview.onclick = () => { if (mode === 'split') choose(i); else selectFree(i, true); };
    const check = document.createElement('input'); check.type = 'checkbox'; check.checked = checkedScenes.has(i); check.disabled = busy; check.setAttribute('aria-label', (i + 1) + '번 공통 레퍼런스 적용'); check.onchange = () => check.checked ? checkedScenes.add(i) : checkedScenes.delete(i);
    row.append(check, num, info, preview);
    if (mode === 'free') { const remove = document.createElement('button'); remove.className = 'remove'; remove.textContent = '×'; remove.setAttribute('aria-label', clip.name + ' 삭제'); remove.disabled = busy; remove.onclick = () => { clips.splice(i, 1); freeActive = Math.min(freeActive, clips.length - 1); checkedScenes.clear(); exportedScenes = []; renderClips(); }; row.append(remove); }
    box.append(row);
  });
  box.scrollTop = scrollTop; controls(); renderScene();
}
$('clear').onclick = () => { if (confirm('담아둔 구간 목록을 비울까요? 원본 음악은 그대로입니다.')) { clips = []; freeActive = -1; checkedScenes.clear(); exportedScenes = []; renderClips(); } };
$('export').onclick = async () => {
  const list = currentClips(); if (!list.length || busy) return;
  busy = true; stop(); renderClips(); $('export').textContent = '저장 중…'; $('result').textContent = ''; status(list.length + '개 구간을 원본에서 저장하고 있어요…');
  try {
    const result = await api('/export', {id: source.id, clips: list, project: $('project').value, state: projectState(), audioOnly: workflow === 'audio'});
    if (workflow === 'mv') { exportedScenes = result.files.map(x => x.folderId); savedSignature = JSON.stringify(projectState()); }
    $('result').textContent = result.files.length + '개 저장 완료\n' + result.folder;
    status(result.folderOpened ? '저장 완료! 파일 탐색기에서 폴더를 열었습니다.' : '저장 완료. 아래 경로에서 파일을 확인해주세요.');
  } catch (e) { status(e.message, true); }
  finally { busy = false; $('export').textContent = workflow === 'audio' ? 'MP3 저장' : '장면 꾸러미 저장'; renderClips(); }
};
$('open').onclick = async () => { try { await api('/open-output', {}); } catch (e) { status(e.message, true); } };
document.addEventListener('keydown', e => {
  if (['INPUT', 'TEXTAREA', 'BUTTON', 'SELECT', 'VIDEO'].includes(document.activeElement.tagName) || !buffer || busy) return;
  if ((e.ctrlKey || e.metaKey) && e.code === 'KeyZ') { e.preventDefault(); undo(); return; }
  if (e.code === 'Space') { e.preventDefault(); play(true); }
  if (['ArrowLeft', 'ArrowRight'].includes(e.code)) { e.preventDefault(); if (mode === 'split') remember(); setStart(selection.start + (e.code === 'ArrowLeft' ? -1 : 1) * (e.shiftKey ? 1 : .1)); }
});
$('workflow-audio').onclick = () => setWorkflow('audio');
$('workflow-mv').onclick = () => setWorkflow('mv');
initScenes(); applyWorkflow(); modeUI(); controls(); renderClips(); new ResizeObserver(draw).observe(canvas);
window.addEventListener('beforeunload', e => { stop(); if (source && (autoSource !== source.id || autoSignature !== JSON.stringify(projectState()))) { e.preventDefault(); e.returnValue = ''; } });
fetch('/config').then(r => r.json()).then(async c => { config = c; busy = !c.ready; controls(); $('output').textContent = c.output; if (!c.ready) status('FFmpeg를 찾지 못했습니다. 실행 안내를 확인해주세요.', true); else await initRecovery(c.drafts || []); }).catch(() => { busy = true; controls(); status('실행 프로그램과 연결되지 않았습니다. 실행.cmd로 다시 열어주세요.', true); });

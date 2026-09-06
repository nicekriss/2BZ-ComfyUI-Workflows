"""Build the reviewed package from a saved workflow, without touching the live canvas."""
import argparse
import copy
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile
import uuid

BASE = Path(__file__).resolve().parent
PACKAGE = BASE / 'FastH3-USDU'
REVIEWED = {
    'comfy/model_detection.py': '39b51a18b5853839b72dc2173426dde33c15c107d4044a3ec3ac1b85c05d98d0',
    'comfy/ldm/minimax/model.py': 'f0f615a58a90401ef0e5dac397eee0b56eaac47835a33b0896b8e5808b532dbf',
}


def build(root, workflow, output):
    patch = []
    for name in ('comfy/model_detection.py', 'comfy/ldm/minimax/model.py'):
        before = subprocess.check_output(['git', '-C', str(root), 'show',
            '7fd919f0caff66a52289ea5b19cb6eaca0da04ef:' + name]).decode('utf-8').replace('\r\n', '\n')
        after = (root / name).read_text(encoding='utf-8')
        if hashlib.sha256(after.encode()).hexdigest() != REVIEWED[name]:
            raise RuntimeError('Source changed since patch review; refusing to package: ' + name)
        old_lines, new_lines = before.splitlines(keepends=True), after.splitlines(keepends=True)
        offsets = [0]
        for line in old_lines:
            offsets.append(offsets[-1] + len(line))
        edits = [{'start': offsets[i], 'end': offsets[j], 'replacement': ''.join(new_lines[k:l])}
                 for tag, i, j, k, l in difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False).get_opcodes()
                 if tag != 'equal']
        patch.append({'path': name, 'before_sha256': hashlib.sha256(before.encode()).hexdigest(),
                      'after_sha256': hashlib.sha256(after.encode()).hexdigest(), 'edits': edits})
    (PACKAGE / 'h3-gate-patch.json').write_text(json.dumps(patch, indent=2), encoding='utf-8')
    graph = json.loads(workflow.read_text(encoding='utf-8'))
    nodes = {n['id']: n for n in graph['nodes']}
    assert len(nodes) == 27 and len(graph['links']) == 29
    assert not any(i in nodes for i in range(34, 42))
    assert any(l[1:5] == [24, 0, 16, 0] for l in graph['links'])
    def widget(node_id, name, index, value):
        node = nodes[node_id]
        node['widgets_values'][index] = value
        if 'widgets_values_named' in node:
            node['widgets_values_named'][name] = value
    widget(31, 'model_name', 0, 'RealESRGAN_x2plus.pth')
    widget(24, 'upscale_by', 0, 2.0)
    widget(12, 'denoise', 2, 0.20)
    nodes[12]['title'] = '8 · Simple · 2 steps / Denoise 0.20'
    nodes[31]['title'] = '10 · RealESRGAN x2plus (공식 파일)'
    nodes[26]['title'] = '📦 모델 4개 · 다운로드 링크'
    widget(2, 'file', 0, '')
    widget(17, 'filename_prefix', 0, 'video/FastH3_USDU')
    for node_id, filename in ((1, 'canvas-start.md'), (27, 'canvas-install.md'),
                              (26, 'canvas-models.md'), (18, 'canvas-settings.md'),
                              (42, 'canvas-results.md')):
        widget(node_id, 'text', 0, (PACKAGE / filename).read_text(encoding='utf-8'))
    nodes[42]['title'] = '최종 비교 · FastH3 USDU 채택 / 2026-09-07'
    # Keep the download and results notes visible in the main canvas lanes.
    nodes[26]['size'] = [700, 710]
    nodes[31]['pos'] = [1640, 544]
    nodes[42]['pos'] = [2145, 1040]
    nodes[42]['size'] = [760, 1100]
    groups = {g['id']: g for g in graph['groups']}
    groups[2]['title'] = '① 모델 다운로드 · 필수 4개'
    groups[2]['bounding'] = [860, 0, 1110, 860]
    groups[7]['title'] = '⑦ 설정 도움말 · 제작 / 출처'
    results_group = {'id': 8, 'title': '⑥ 최신 테스트 결과 · 최종 선택',
                     'bounding': [2105, 960, 840, 1250], 'color': '#286878', 'flags': {}}
    if 8 in groups:
        groups[8].update(results_group)
    else:
        graph['groups'].append(results_group)
    assert '1w0xkpb' in nodes[28]['widgets_values'][0] and '1vwgoy2' in nodes[28]['widgets_values'][0]
    graph.get('extra', {}).pop('comfyui_mcp', None)
    # Remove local execution previews/paths, retaining only graph content.
    for node in graph['nodes']:
        node.pop('imgs', None)
        node.pop('images', None)
    (PACKAGE / '2BZ_FastH3_USDU.json').write_text(json.dumps(graph, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    english = copy.deepcopy(graph)
    english['id'] = str(uuid.uuid5(uuid.NAMESPACE_URL, 'https://github.com/nicekriss/2BZ-ComfyUI-Workflows/FastH3-USDU/EN'))
    translation = json.loads((PACKAGE / 'canvas-en.json').read_text(encoding='utf-8'))
    for node in english['nodes']:
        node['title'] = translation['titles'][str(node['id'])]
        if node['type'] == 'MarkdownNote':
            value = translation['notes'][str(node['id'])]
            node['widgets_values'][0] = value
            if 'widgets_values_named' in node:
                node['widgets_values_named']['text'] = value
    for group in english['groups']:
        group['title'] = translation['groups'][str(group['id'])]
    (PACKAGE / '2BZ_FastH3_USDU_EN.json').write_text(json.dumps(english, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    files = ['2BZ_FastH3_USDU.json', '2BZ_FastH3_USDU_EN.json', 'START-HERE-en.md',
             'check_solattn.py', 'install_solattn.py', 'h3_compat.py',
             'h3-gate-patch.json', 'Install-SolAttn-MiniMax.bat', 'Install-SolAttn-MiniMax.ps1',
             'Restore-SolAttn-MiniMax.bat', 'Check-Setup.bat', 'README.md', 'START-HERE-ko.md',
             'BENCHMARK.md', 'RECORDING-ko.md', 'install_usdu.py', 'Install-USDU-H3.bat',
             'Check-ComfyUI.bat', 'Check-ComfyUI.ps1', 'REPORT-PROBLEM-ko.md', 'MEMORY-ko.md']
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            archive.write(PACKAGE / name, name)
        archive.write(BASE / 'LICENSE', 'LICENSE')
        archive.write(root / 'LICENSE', 'LICENSE-ComfyUI.txt')
    print(output)
    print('SHA256:', hashlib.sha256(output.read_bytes()).hexdigest())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--workflow', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    build(args.root, args.workflow, args.output)

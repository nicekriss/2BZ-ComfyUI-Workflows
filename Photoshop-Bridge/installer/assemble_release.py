"""Assemble the release ZIP and .sha256 sidecar after package_ccx.py and build.py.

Layout matches photoshop-bridge-v0.2.4: checksums.json, dependencies.json, LICENSE, licenses/,
qa/illustrious-inpaint/, THIRD_PARTY_NOTICES.md, the CCX, TooBusyAI-Setup.exe, workflows/,
설치안내.md (START-HERE-ko.md) and 검증기록.md (VALIDATION.md).
Usage: python installer/assemble_release.py [output_dir]   (default: release/)
"""
import hashlib, json, shutil, sys, zipfile
from pathlib import Path
bridge = Path(__file__).resolve().parents[1]
root = bridge.parent
release = bridge / 'release'
build_data = root.parent / 'work/installer-build/data'  # created by build.py
version = json.loads((bridge / 'plugin/manifest.json').read_text('utf-8'))['version']
out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else release
stage = out_dir / f'stage-{version}'
if stage.exists(): shutil.rmtree(stage)
stage.mkdir(parents=True)
def put(src, rel):
    dst = stage / rel; dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, dst)
put(bridge / 'installer/dependencies.json', 'dependencies.json')
put(root / 'LICENSE', 'LICENSE')
put(root / 'THIRD_PARTY_NOTICES.md', 'THIRD_PARTY_NOTICES.md')
put(bridge / 'START-HERE-ko.md', '설치안내.md')
put(bridge / 'VALIDATION.md', '검증기록.md')
put(release / 'toobusy.photoshop.bridge_PS.ccx', 'toobusy.photoshop.bridge_PS.ccx')
put(release / 'TooBusyAI-Setup.exe', 'TooBusyAI-Setup.exe')
for p in (bridge / 'workflows').iterdir():
    if p.is_file(): put(p, 'workflows/' + p.name)
for p in (bridge / 'qa/illustrious-inpaint').iterdir():
    if p.is_file(): put(p, 'qa/illustrious-inpaint/' + p.name)
for p in (build_data / 'licenses').rglob('*'):
    if p.is_file(): put(p, 'licenses/' + p.relative_to(build_data / 'licenses').as_posix())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
entries = sorted(p for p in stage.rglob('*') if p.is_file())
checks = [{'file': p.relative_to(stage).as_posix(), 'sha256': sha(p), 'bytes': p.stat().st_size} for p in entries]
(stage / 'checksums.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2) + '\n', 'utf-8')
name = f'2BZ-TooBusyAI-Photoshop-Bridge-v{version}'
out = out_dir / f'{name}.zip'
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as archive:
    for p in sorted(stage.rglob('*')):
        if p.is_file(): archive.write(p, p.relative_to(stage).as_posix())
shutil.rmtree(stage)
ccx = release / 'toobusy.photoshop.bridge_PS.ccx'
sidecar = out_dir / f'{name}.sha256'
sidecar.write_text(f'{sha(out)}  {out.name}\n{sha(ccx)}  {ccx.name}\n', 'utf-8')
print(out, out.stat().st_size, 'bytes,', len(checks), 'files')
print(sidecar.read_text('utf-8'))

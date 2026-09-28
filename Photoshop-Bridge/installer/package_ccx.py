"""Package plugin/ as the distributable CCX (a ZIP with manifest.json at the root, as Adobe UDT produces)."""
from pathlib import Path
import json, sys, zipfile
root = Path(__file__).resolve().parents[1]
plugin = root / 'plugin'
target = Path(sys.argv[1]) if len(sys.argv) > 1 else root / 'release' / 'toobusy.photoshop.bridge_PS.ccx'
manifest = json.loads((plugin / 'manifest.json').read_text('utf-8'))
if json.loads((plugin / 'config.json').read_text('utf-8')).get('token'):
    raise SystemExit('plugin/config.json의 token이 비어 있어야 합니다. 개발 PC 연결 키를 배포하지 마세요.')
files = sorted(p for p in plugin.rglob('*') if p.is_file() and not p.name.startswith('.') and '__pycache__' not in p.parts)
target.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
    archive.write(plugin / 'manifest.json', 'manifest.json')
    for path in files:
        if path.name != 'manifest.json' or path.parent != plugin:
            archive.write(path, path.relative_to(plugin).as_posix())
print(f"{target} · {manifest['id']} v{manifest['version']} · {len(files)} files · {target.stat().st_size} bytes")

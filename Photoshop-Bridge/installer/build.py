"""Run in a build venv after packaging the sanitized release plugin using Adobe UDT."""
from pathlib import Path
import json,shutil,subprocess,sys
root=Path(__file__).resolve().parents[1]
work=root.parent.parent/'work/installer-build'
data=work/'data';data.mkdir(parents=True,exist_ok=True)
ccx=root/'release/toobusy.photoshop.bridge_PS.ccx'
if not ccx.is_file():raise SystemExit('먼저 Adobe UDT에서 배포용 CCX를 release 폴더에 만드세요.')
import zipfile
import importlib.metadata
licenses=data/'licenses';licenses.mkdir(exist_ok=True)
for name in ['requests','urllib3','certifi','charset-normalizer','idna','psutil','PyYAML','pyinstaller']:
    dist=importlib.metadata.distribution(name)
    for file in dist.files or []:
        if any(word in file.name.lower() for word in ['license','copying','notice']) and '.dist-info' in str(file):
            source=Path(dist.locate_file(file))
            if source.is_file():
                destination=licenses/name/file.name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,destination)
for name,path in [('Python',Path(sys.base_prefix)/'LICENSE.txt'),('TclTk',Path(sys.base_prefix)/'tcl/tk8.6/license.terms')]:
    if path.is_file():shutil.copy2(path,licenses/(name+'.txt'))
with zipfile.ZipFile(ccx) as archive:
    config=json.loads(archive.read('config.json'))
    if config.get('token'):raise SystemExit('배포 CCX에 개발 PC 토큰이 들어 있습니다. config.json의 token을 비워 다시 패키징하세요.')
shutil.copy2(ccx,data/'TooBusyAI.ccx')
for name in ['dependencies.json','convert_model.py']:shutil.copy2(root/'installer'/name,data/name)
shutil.copy2(root/'plugin/pro-template.json',data/'pro-template.json')
shutil.copytree(root/'workflows',data/'workflows',dirs_exist_ok=True)
(data/'comfy_node').mkdir(exist_ok=True)
for name in ['__init__.py','pixels.py']:shutil.copy2(root/'comfy_node'/name,data/'comfy_node'/name)
subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--onefile','--windowed','--name','TooBusyAI-Setup','--distpath',str(root/'release'),'--workpath',str(work/'pyinstaller'),'--specpath',str(work),'--add-data',str(data)+';data','--collect-all','requests','--collect-all','certifi','--collect-all','psutil','--collect-all','yaml',str(root/'installer/setup.py')],check=True)

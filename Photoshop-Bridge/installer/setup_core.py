"""Installer engine. Never starts/stops an existing server or overwrites user models."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import subprocess
import tempfile
import time
import zipfile
from urllib.parse import urlsplit, urljoin

import requests

FIELDS = {'1':('ckpt_name','checkpoints'), '17':('lora_name','loras'), '7':('control_net_name','controlnet'), '40':('control_net_name','controlnet'), '37':('model_name','geometry_estimation'), '46':('ckpt_name','checkpoints'), '58':('ipadapter_file','ipadapter'), '68':('clip_name','clip_vision')}
class SetupError(RuntimeError): pass
class Cancelled(SetupError): pass

def civitai_endpoint(url):
    parsed=urlsplit(url)
    return parsed.scheme=='https' and parsed.netloc=='civitai.com' and parsed.path.startswith('/api/')

def api_token(value):
    value=str(value or '').strip()
    if value and (len(value)>4096 or not all(33<=ord(c)<=126 for c in value)):
        raise SetupError('Civitai API 키만 붙여넣으세요. 공백이나 줄바꿈은 포함할 수 없습니다.')
    return value

def read_json(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write_json(path, value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    os.replace(temporary,path)
def sha(path, cancel=lambda:False):
    digest=hashlib.sha256()
    with Path(path).open('rb') as f:
        while block:=f.read(8*1024*1024):
            if cancel(): raise Cancelled('중지했습니다. 다시 실행하면 이어서 진행합니다.')
            digest.update(block)
    return digest.hexdigest()
def inside(root, relative):
    root=Path(root).resolve(); relative=str(relative).replace('\\','/')
    if ':' in relative or PurePosixPath(relative).is_absolute() or '..' in PurePosixPath(relative).parts: raise SetupError('잘못된 설치 경로')
    target=(root/relative).resolve()
    if not target.is_relative_to(root): raise SetupError('설치 폴더 밖을 가리키는 경로')
    return target
def server_url(value):
    if not re.fullmatch(r'http://(?:127\.0\.0\.1|localhost):[0-9]{1,5}',value) or not 1<=int(value.rsplit(':',1)[1])<=65535: raise SetupError('같은 PC의 주소를 입력하세요. 예: http://127.0.0.1:8188')
    return value
def resolve_root(path):
    path=Path(path).expanduser().resolve()
    for root in [path,path/'ComfyUI',path/'ComfyUI_windows_portable'/'ComfyUI']:
        if (root/'main.py').is_file() and (root/'custom_nodes').is_dir(): return root
    raise SetupError('ComfyUI의 main.py와 custom_nodes가 있는 폴더를 선택하세요.')
def runtime(root):
    for p in [root/'.venv/Scripts/python.exe',root/'venv/Scripts/python.exe',root.parent/'python_embeded/python.exe',root.parent/'python_embedded/python.exe']:
        if p.is_file(): return p.resolve()
    raise SetupError('ComfyUI 전용 Python을 찾지 못했습니다. .venv 또는 Windows Portable 환경이 필요합니다.')
def run(args, log=print, cwd=None, timeout=1200):
    result=subprocess.run([str(x) for x in args],cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),timeout=timeout)
    if result.returncode: raise SetupError('설치 명령 실패:\n'+result.stdout[-3000:])
    if result.stdout.strip(): log(result.stdout[-1500:].strip())
    return result.stdout
def active_processes(root):
    import psutil
    matches=[]
    root=str(Path(root).resolve()).lower()
    for p in psutil.process_iter(['pid','exe','cmdline','cwd']):
        try:
            info=p.info; args=info.get('cmdline') or []
            if not any(Path(a).name.lower()=='main.py' for a in args): continue
            cwd=info.get('cwd') or ''
            scripts=[Path(a) if Path(a).is_absolute() else Path(cwd)/a for a in args if Path(a).name.lower()=='main.py']
            script_match=any(str(a.resolve()).lower()==str(Path(root)/'main.py').lower() for a in scripts)
            env_match=bool(args) and str(Path(args[0]).resolve()).lower() in [str(Path(root)/'.venv/Scripts/python.exe').lower(),str(Path(root)/'venv/Scripts/python.exe').lower()]
            if script_match or env_match: matches.append(info)
        except (psutil.Error,OSError): pass
    return matches
def model_roots(root, extra=None):
    import yaml
    result={kind:[root/'models'/kind] for _,kind in FIELDS.values()}
    files=[root/'extra_model_paths.yaml']
    for proc in active_processes(root):
        args=proc['cmdline']
        for i,arg in enumerate(args[:-1]):
            if arg=='--extra-model-paths-config':
                for v in args[i+1:]:
                    if v.startswith('--'): break
                    files.append(Path(v) if Path(v).is_absolute() else root/v)
    if extra:
        extra=Path(extra).resolve()
        for kind in result: result[kind].append(extra/kind)
        result['ipadapter'].append(extra/'IpAdapter')
    for file in files:
        if not file.is_file(): continue
        data=yaml.safe_load(file.read_text(encoding='utf-8-sig')) or {}
        for section in data.values():
            if not isinstance(section,dict): continue
            base=Path(os.path.expandvars(str(section.get('base_path',file.parent)))).expanduser()
            if not base.is_absolute(): base=file.parent/base
            for kind in result:
                for relative in str(section.get(kind,'')).splitlines():
                    if relative.strip(): result[kind].append((base/relative.strip()).resolve())
    return result
def existing_model(root, model, roots):
    kind,relative=model['path'].split('/',1)
    expected=inside(root/'models',model['path'])
    if expected.is_file(): return expected
    candidates=[]
    for folder in roots.get(kind,[]):
        if folder.is_dir():
            for file in folder.rglob(Path(relative).name):
                if file.is_file() and file.resolve() not in candidates: candidates.append(file.resolve())
    if len(candidates)>1:
        exact=[p for p in candidates if str(p).replace('\\','/').endswith('/'+relative)]
        if len(exact)==1:return exact[0]
        raise SetupError('동명 모델이 여러 개입니다. 사용할 모델 폴더를 지정하세요: '+Path(relative).name)
    return candidates[0] if candidates else None

class Engine:
    def __init__(self,data,state,log=print,cancel=lambda:False,civitai_token='',request_token=None):
        self.data=Path(data); self.state=Path(state); self.state.mkdir(parents=True,exist_ok=True)
        self.manifest=read_json(self.data/'dependencies.json');self.cancel=cancel
        self.civitai_token=api_token(civitai_token);self.request_token=request_token
        def record(message):
            with (self.state/'setup.log').open('a',encoding='utf-8') as f:f.write(time.strftime('%Y-%m-%d %H:%M:%S')+' '+message+'\n')
            log(message)
        self.log=record
    def check_cancel(self):
        if self.cancel():raise Cancelled('중지했습니다. 다운로드는 다음 실행에서 이어받습니다.')
    def download_response(self,url,headers):
        # Credentials belong only to Civitai's HTTPS API, never a redirected CDN.
        origin=url;redirects=0
        while True:
            self.check_cancel()
            parsed=urlsplit(url)
            if parsed.scheme!='https' or parsed.username or parsed.password:
                raise SetupError('안전한 HTTPS 다운로드 주소가 아닙니다.')
            current=dict(headers)
            if civitai_endpoint(origin) and civitai_endpoint(url) and self.civitai_token:
                current['Authorization']='Bearer '+self.civitai_token
            try:response=requests.get(url,headers=current,stream=True,timeout=(30,90),allow_redirects=False)
            except requests.RequestException:
                raise SetupError('다운로드 서버에 연결하지 못했습니다. 인터넷 연결을 확인하고 설치를 다시 누르세요. 받은 부분은 이어받습니다.') from None
            if response.status_code in (301,302,303,307,308):
                location=response.headers.get('Location');response.close()
                if not location:raise SetupError('다운로드 서버의 이동 주소가 비어 있습니다.')
                redirects+=1
                if redirects>10:raise SetupError('다운로드 주소 이동이 너무 많습니다. 잠시 후 다시 시도하세요.')
                url=urljoin(url,location);continue
            if response.status_code in (401,403) and civitai_endpoint(origin) and civitai_endpoint(url):
                response.close()
                if not self.request_token:
                    raise SetupError('Civitai 인증이 필요합니다. 설치 창의 Civitai API 키를 입력하고 설치를 다시 누르세요.')
                self.log('Civitai 인증을 기다립니다. 키를 입력하면 이 모델부터 자동으로 이어갑니다.')
                token=self.request_token(bool(self.civitai_token))
                self.check_cancel()
                if not token:raise Cancelled('Civitai 인증을 취소했습니다. 받은 파일은 보존되며 다음 설치에서 이어받습니다.')
                self.civitai_token=api_token(token)
                url=origin;redirects=0;continue
            if response.status_code not in (200,206):
                status=response.status_code;response.close()
                raise SetupError(f'다운로드 서버가 HTTP {status}를 반환했습니다. 잠시 후 설치를 다시 눌러주세요. 받은 부분은 보존됩니다.')
            return response
    def inspect(self,root,extra=None):
        root=resolve_root(root);python=runtime(root);roots=model_roots(root,extra)
        write_json(self.state/'model-roots.json',{'root':str(root),'extra':str(extra or ''),'paths':{k:[str(p) for p in v] for k,v in roots.items()}})
        missing=[]
        for item in self.manifest['models']:
            found=existing_model(root,item,roots)
            self.log(('재사용 후보: ' if found else '다운로드 필요: ')+Path(item['path']).name)
            if not found:missing.append(item)
        self.log(f'필요한 모델 {len(self.manifest["models"])}개 / 새 다운로드 {len(missing)}개, 약 {sum(x["size"] for x in missing)/1024**3:.1f} GiB')
        running=bool(active_processes(root))
        if running:self.log('ComfyUI가 실행 중입니다. 설치 전 작업을 저장하고 종료하세요. 점검은 가능합니다.')
        return {'root':str(root),'runtime':str(python),'download_bytes':sum(x['size'] for x in missing),'running':running}
    def download(self,item,destination):
        self.check_cancel(); destination=Path(destination); destination.parent.mkdir(parents=True,exist_ok=True)
        if destination.is_file():
            if sha(destination,self.cancel)==item['sha256']: return destination
            raise SetupError('기존 파일의 해시가 다릅니다. 덮어쓰지 않았습니다: '+str(destination))
        partial=destination.with_name(destination.name+'.part')
        offset=partial.stat().st_size if partial.exists() else 0
        if offset>item['size']:raise SetupError('불완전 다운로드 크기가 예상보다 큽니다: '+str(partial))
        if offset==item['size'] and sha(partial,self.cancel)==item['sha256']:
            os.replace(partial,destination);return destination
        if offset==item['size']:
            partial.rename(partial.with_name(partial.name+'.failed-'+secrets.token_hex(4)));offset=0
        if shutil.disk_usage(destination.parent).free < item['size']-offset+256*1024*1024: raise SetupError('다운로드 공간이 부족합니다: '+str(destination.parent))
        headers={'User-Agent':'TooBusySetup/0.2'}
        if offset:headers['Range']=f'bytes={offset}-'
        self.log('다운로드: '+destination.name)
        with self.download_response(item['url'],headers) as response:
            if response.status_code==206:
                content_range=response.headers.get('Content-Range','')
                if not content_range.startswith(f'bytes {offset}-') or not content_range.endswith('/'+str(item['size'])): raise SetupError('다운로드 이어받기 응답이 올바르지 않습니다.')
            else:offset=0
            last=0;done=offset
            with partial.open('ab' if offset else 'wb') as out:
                try:
                    for block in response.iter_content(4*1024*1024):
                        self.check_cancel()
                        if not block:continue
                        out.write(block);done+=len(block)
                        if done>item['size']:raise SetupError('다운로드가 예상 크기를 초과했습니다.')
                        if time.monotonic()-last>3:
                            self.log(f'{destination.name}: {done/item["size"]:.0%}');last=time.monotonic()
                except requests.RequestException:
                    raise SetupError('다운로드 연결이 끊겼습니다. 설치를 다시 누르면 받은 부분부터 이어갑니다.') from None
        if partial.stat().st_size!=item['size'] or sha(partial,self.cancel)!=item['sha256']:
            partial.rename(partial.with_name(partial.name+'.failed-'+secrets.token_hex(4)))
            raise SetupError('다운로드 무결성 검사 실패. 모델로 설치하지 않았습니다. 다시 설치하면 새로 받습니다: '+destination.name)
        os.replace(partial,destination);return destination
    def install_nodes(self,root,python):
        for node in self.manifest['nodes']:
            self.check_cancel();target=inside(root/'custom_nodes',node['name'])
            if target.exists():
                if not (target/'__init__.py').is_file():raise SetupError('노드 폴더가 불완전합니다: '+str(target))
                self.log('기존 노드 유지: '+node['name']);continue
            archive=self.download(node,self.state/'cache'/(node['name']+'.zip'))
            staging=Path(tempfile.mkdtemp(prefix='.toobusy-node-',dir=self.state))
            with zipfile.ZipFile(archive) as z:
                for entry in z.infolist():
                    inside(staging,entry.filename)
                    if (entry.external_attr>>16)&0o170000==0o120000:raise SetupError('노드 압축에 심볼릭 링크가 있습니다.')
                z.extractall(staging)
            candidates=[p for p in staging.iterdir() if p.is_dir()]
            if len(candidates)!=1 or not (candidates[0]/'__init__.py').is_file():raise SetupError('노드 압축 구조 오류')
            package=candidates[0];req=package/'requirements.txt'
            if req.exists():
                self.log('노드 Python 의존성 설치: '+node['name'])
                freeze=run([python,'-m','pip','freeze'],log=lambda _:None,cwd=root)
                constraints=staging/'constraints.txt'
                constraints.write_text('\n'.join(line for line in freeze.splitlines() if re.fullmatch(r'[\w.-]+==[^\s]+',line)),encoding='utf-8')
                run([python,'-m','pip','install','-r',req,'-c',constraints],self.log,cwd=root)
            # Copy into a sibling then rename: incomplete dependencies never look installed.
            sibling=target.with_name('.'+target.name+'.toobusy-'+secrets.token_hex(4))
            shutil.copytree(package,sibling);sibling.rename(target)
            self.log('노드 설치 완료: '+node['name'])
    def bridge(self,root):
        target=inside(root/'custom_nodes','toobusy_photoshop_bridge');source=self.data/'comfy_node'
        if target.exists():
            for name in ['__init__.py','pixels.py']:
                if not (target/name).is_file() or sha(target/name)!=sha(source/name):raise SetupError('기존 Bridge 버전이 다릅니다. 기존 설치를 유지했으며 별도 업데이트가 필요합니다.')
            token=read_json(target/'pairing.json')['token']
            if not re.fullmatch('[a-fA-F0-9]{64}',token):raise SetupError('기존 Bridge 연결 정보가 올바르지 않습니다.')
        else:
            token=secrets.token_hex(32)
            staging=target.with_name('.toobusy-bridge-'+secrets.token_hex(4));staging.mkdir()
            for name in ['__init__.py','pixels.py']:shutil.copy2(source/name,staging/name)
            write_json(staging/'pairing.json',{'token':token});staging.rename(target)
        return token
    def models(self,root,python,roots):
        for item in self.manifest['models']:
            self.check_cancel();target=inside(root/'models',item['path']);existing=existing_model(root,item,roots)
            expected=item.get('installed_sha256',item['sha256'])
            if existing:
                self.log('기존 모델 확인: '+existing.name)
                if sha(existing,self.cancel) not in item.get('accepted_installed_sha256',[expected]):raise SetupError('기존 모델 해시가 다릅니다. 덮어쓰지 않았습니다: '+str(existing))
                if existing!=target:
                    target.parent.mkdir(parents=True,exist_ok=True)
                    try:os.link(existing,target)
                    except OSError:
                        if shutil.disk_usage(target.parent).free<existing.stat().st_size+256*1024**2:raise SetupError('모델 복사 공간 부족')
                        temporary=target.with_name(target.name+'.copying');shutil.copy2(existing,temporary);os.replace(temporary,target)
                self.log('모델 재사용: '+target.name);continue
            if item.get('convert_fp16'):
                original=self.download(item,self.state/'cache/CN-anytest4-original.safetensors')
                target.parent.mkdir(parents=True,exist_ok=True);temporary=target.with_name(target.name+'.converting')
                self.log('라인아트 모델 FP16 변환 중…')
                run([python,self.data/'convert_model.py',original,temporary],self.log,cwd=root)
                if sha(temporary,self.cancel)!=expected:raise SetupError('FP16 변환 파일 검증 실패')
                os.replace(temporary,target)
            else:self.download(item,target)
    def install(self,root,url,extra=None):
        root=resolve_root(root);python=runtime(root);server_url(url)
        if active_processes(root):raise SetupError('작업을 저장하고 이 ComfyUI를 종료한 뒤 설치를 다시 눌러주세요. 실행 중인 환경은 수정하지 않습니다.')
        roots=model_roots(root,extra)
        remembered=self.state/'model-roots.json'
        if remembered.is_file():
            cached=read_json(remembered)
            if cached.get('root')==str(root) and cached.get('extra')==str(extra or ''):
                for kind,paths in cached['paths'].items():roots.setdefault(kind,[]).extend(Path(p) for p in paths)
        # Persist resolved external paths before Desktop closes them on the next run.
        self.log('설치 대상: '+str(root))
        run([python,'-c','import torch, safetensors; print("ComfyUI Python 확인 완료")'],self.log,cwd=root)
        needed=sum(item['size'] for item in self.manifest['models'] if not existing_model(root,item,roots))
        if shutil.disk_usage(root).free<needed+3*1024**3:raise SetupError(f'설치 공간이 부족합니다. 추가 여유 공간 약 {(needed+3*1024**3)/1024**3:.1f} GiB가 필요합니다.')
        self.install_nodes(root,python);self.models(root,python,roots);token=self.bridge(root)
        paths={}
        template=read_json(self.data/'pro-template.json')
        for id,(field,category) in FIELDS.items():paths[id]=template[id]['inputs'][field].replace('\\','/')
        connection=self.state/'TooBusy-connection.json'
        write_json(connection,{'token':token,'server':url,'modelPaths':paths})
        write_json(self.state/'installation.json',{'root':str(root),'server':url,'connection':str(connection),'prepared':True,'verified':False})
        self.log('파일 설치 완료. ComfyUI를 시작한 뒤 연결 검사를 진행하세요.')
        return connection
    def verify(self,root,url):
        root=resolve_root(root);server_url(url)
        import psutil
        port=int(url.rsplit(':',1)[1]);pids={p['pid'] for p in active_processes(root)}
        listeners={c.pid for c in psutil.net_connections(kind='tcp') if c.status=='LISTEN' and c.laddr.port==port}
        if not pids.intersection(listeners):raise SetupError('입력한 주소가 선택한 ComfyUI 프로세스인지 확인하지 못했습니다. 폴더와 포트를 확인하세요.')
        token=read_json(root/'custom_nodes/toobusy_photoshop_bridge/pairing.json')['token']
        session=requests.Session();session.trust_env=False
        response=session.get(url+'/object_info',timeout=30,allow_redirects=False);response.raise_for_status();info=response.json()
        template=read_json(self.data/'pro-template.json');types={v['class_type'] for v in template.values()}|{'TooBusyPhotoshopInput','TooBusyPhotoshopOutput'}
        missing=sorted(types-set(info))
        if missing:raise SetupError('필요한 노드가 로드되지 않았습니다. ComfyUI 업데이트/노드 오류 확인: '+', '.join(missing))
        paths={}
        for id,(field,_) in FIELDS.items():
            node=template[id];schema=info[node['class_type']]['input']['required'][field]
            files=schema[0] if isinstance(schema[0],list) else schema[1].get('options',[])
            desired=node['inputs'][field].replace('\\','/')
            exact=[f for f in files if f.replace('\\','/')==desired]
            matches=exact or [f for f in files if f.replace('\\','/').split('/')[-1]==desired.split('/')[-1]]
            if len(matches)!=1:raise SetupError('모델 경로를 하나로 확인하지 못했습니다: '+desired)
            paths[id]=matches[0]
        response=session.get(url+'/toobusy/ps/v1/info',headers={'X-TooBusy-Token':token},timeout=30,allow_redirects=False);response.raise_for_status()
        write_json(self.state/'TooBusy-connection.json',{'token':token,'server':url,'modelPaths':paths})
        write_json(self.state/'installation.json',{'root':str(root),'server':url,'prepared':True,'verified':True,'checked_at':time.strftime('%Y-%m-%d %H:%M:%S')})
        self.log('Bridge 인증, 필요한 노드와 모델 경로 검사 통과. 포토샵에서 연결 파일을 열고 이미지를 싱크하세요.')
    def export_plugin(self):
        source=self.data/'TooBusyAI.ccx'
        if not source.is_file():raise SetupError('CCX 패키지가 포함되지 않았습니다.')
        target=self.state/'TooBusyAI.ccx';shutil.copy2(source,target)
        return target

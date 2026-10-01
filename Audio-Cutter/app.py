import hashlib
import argparse
import atexit
import json
import math
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request
import uuid
import webbrowser

import projects
from recovery import RecoveryStore
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = (Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else ROOT) / 'exports'
APP_ID = 'toobusy-mv-audio-cutter'
TOKEN = secrets.token_urlsafe(32)
FFMPEG = str(ROOT / 'media' / 'ffmpeg.exe') if (ROOT / 'media' / 'ffmpeg.exe').exists() else shutil.which('ffmpeg')
FFPROBE = str(ROOT / 'media' / 'ffprobe.exe') if (ROOT / 'media' / 'ffprobe.exe').exists() else shutil.which('ffprobe')
SOURCES = {}
ASSETS = {}
EXPORTED_FOLDERS = {}
RECOVERY = RecoveryStore(Path(os.environ.get('LOCALAPPDATA', Path.home())) / '2BZ-Audio-Cutter' / 'recovery')
SOURCE_LOCK = threading.Lock()
EXPORT_LOCK = threading.Lock()
CACHE = Path(tempfile.mkdtemp(prefix='toobusy-audio-'))
atexit.register(shutil.rmtree, CACHE, ignore_errors=True)
NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0


def run_media(args):
    result = subprocess.run(args, capture_output=True, text=True, encoding='utf-8',
                            errors='replace', creationflags=NO_WINDOW, timeout=300)
    if result.returncode:
        raise ValueError('오디오를 처리하지 못했습니다. 파일 형식이나 손상 여부를 확인해주세요.')
    return result.stdout


def inspect_audio(path):
    info = json.loads(run_media([FFPROBE, '-v', 'error', '-select_streams', 'a:0',
                                '-show_entries', 'stream=codec_name:format=duration',
                                '-of', 'json', str(path)]))
    if not info.get('streams'):
        raise ValueError('이 파일에는 오디오 트랙이 없습니다.')
    duration = float(info.get('format', {}).get('duration', 0))
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('오디오 길이를 읽을 수 없습니다.')
    return duration


def safe_name(name):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', str(name)).strip(' .')[:70]
    if not name or name.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL',
                                                 *['COM' + str(i) for i in range(1, 10)],
                                                 *['LPT' + str(i) for i in range(1, 10)]}:
        return '장면'
    return name


def stamp(seconds):
    millis = round(seconds * 1000)
    return f'{millis // 60000:02d}m{millis // 1000 % 60:02d}s{millis % 1000:03d}'


def validate_clips(clips, duration):
    if not isinstance(clips, list) or not clips:
        raise ValueError('저장할 구간을 먼저 담아주세요.')
    clean = []
    for index, clip in enumerate(clips):
        if not isinstance(clip, dict):
            raise ValueError('구간 목록 형식을 확인해주세요.')
        start, end = float(clip['start']), float(clip['end'])
        if not (math.isfinite(start) and math.isfinite(end) and 0 <= start < end <= duration + .001):
            raise ValueError(f'{index + 1}번째 구간의 시작과 끝을 확인해주세요.')
        clean.append({'name': safe_name(clip.get('name', f'장면{index + 1:02d}')),
                      'start': start, 'end': min(end, duration)})
    return clean


def register_source(path, name):
    identifier = uuid.uuid4().hex
    duration = inspect_audio(path)
    preview = CACHE / (identifier + '.mp3')
    run_media([FFMPEG, '-v', 'error', '-nostdin', '-i', str(path), '-map', '0:a:0',
               '-vn', '-map_metadata', '-1', '-c:a', 'libmp3lame', '-b:a', '128k', str(preview)])
    SOURCES[identifier] = {'path': path, 'preview': preview, 'name': name, 'duration': duration, 'recoveryId': identifier}
    return {'id': identifier, 'name': name, 'duration': duration, 'recoveryId': identifier}


def register_asset(data, name):
    extension, mime = projects.image_kind(data)
    identifier = hashlib.sha256(data).hexdigest()[:32]
    path = CACHE / (identifier + extension)
    if identifier not in ASSETS:
        path.write_bytes(data)
        ASSETS[identifier] = {'path': path, 'name': name, 'mime': mime, 'kind': 'image'}
    return {'id': identifier, 'name': ASSETS[identifier]['name'], 'kind': 'image'}


def register_video(path, name):
    with path.open('rb') as file:
        identifier = hashlib.file_digest(file, 'sha256').hexdigest()[:32]
    if identifier in ASSETS:
        return {'id': identifier, 'name': ASSETS[identifier]['name'], 'kind': 'video'}
    info = json.loads(run_media([FFPROBE, '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=codec_name:format=duration', '-of', 'json', str(path)]))
    duration = float(info.get('format', {}).get('duration', 0))
    if not info.get('streams') or not math.isfinite(duration) or duration <= 0:
        raise ValueError('재생할 수 있는 영상 파일을 넣어주세요.')
    extension = Path(name).suffix.lower()
    if extension not in {'.mp4', '.mov', '.webm', '.mkv', '.avi', '.m4v'}:
        extension = '.video'
    original = CACHE / (identifier + extension)
    shutil.copyfile(path, original)
    preview = CACHE / (identifier + '.preview.mp4')
    run_media([FFMPEG, '-v', 'error', '-nostdin', '-i', str(original), '-map', '0:v:0', '-map', '0:a:0?',
               '-vf', "scale='min(1280,iw)':-2", '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
               '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-movflags', '+faststart', str(preview)])
    ASSETS[identifier] = {'path': original, 'preview': preview, 'name': name, 'mime': 'video/mp4', 'kind': 'video', 'duration': duration}
    return {'id': identifier, 'name': name, 'kind': 'video'}


def final_frame(identifier):
    asset = ASSETS.get(identifier)
    if not asset or asset.get('kind') != 'video':
        raise ValueError('이 장면에 결과 영상을 먼저 넣어주세요.')
    target = CACHE / (uuid.uuid4().hex + '.png')
    try:
        run_media([FFMPEG, '-v', 'error', '-nostdin', '-sseof', str(-min(3, asset['duration'])),
                   '-i', str(asset['path']), '-map', '0:v:0', '-an', '-fps_mode', 'passthrough', '-update', '1', str(target)])
        if not target.exists():
            raise ValueError('영상의 마지막 프레임을 읽을 수 없습니다.')
        return register_asset(target.read_bytes(), Path(asset['name']).stem + '_마지막프레임.png')
    finally:
        target.unlink(missing_ok=True)


def restore_project(info, audio_path, media, recovery_id=None):
    source = register_source(audio_path, str(info['audioName']))
    mapped = {}
    for key, asset in media.items():
        if asset.get('kind') == 'video':
            path = asset.get('path')
            if path is None:
                path = CACHE / (uuid.uuid4().hex + '.video')
                path.write_bytes(asset['data'])
            mapped[key] = register_video(path, asset['name'])
        else:
            data = asset['path'].read_bytes() if 'path' in asset else asset['data']
            mapped[key] = register_asset(data, asset['name'])
    value = projects.state(info['state'], source['duration'], {key: ASSETS[item['id']] for key, item in mapped.items()})
    for scene in value['scenes'] + [clip['scene'] for clip in value['clips']]:
        scene['references'] = [mapped[key]['id'] for key in scene['references']]
        for field in ('keyframeStart', 'keyframeEnd', 'resultVideo'):
            if scene[field]:
                scene[field] = mapped[scene[field]]['id']
    for item in value['library']:
        item['id'] = mapped[item['id']]['id']
    value = projects.state(value, source['duration'], ASSETS)
    if recovery_id:
        SOURCES[source['id']]['recoveryId'] = recovery_id
        source['recoveryId'] = recovery_id
    return {'source': source, 'state': value, 'assets': list(mapped.values())}


def export_clips(source, clips, project, open_folder=True, state=None, audio_only=False):
    validated = validate_clips(clips, source['duration'])
    scenes = [] if audio_only else [projects.scene(clip.get('scene', {}), ASSETS) for clip in clips]
    clips = validated
    destination = OUTPUT_ROOT / (datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + safe_name(project) + '_' + uuid.uuid4().hex[:4])
    destination.mkdir(parents=True)
    exported = []
    try:
        for index, clip in enumerate(clips, 1):
            name = f'{index:02d}_{clip["name"]}_{stamp(clip["start"])}-{stamp(clip["end"])}.mp3'
            folder_name = f'{index:02d}_{clip["name"]}'
            if audio_only:
                target = destination / name
            else:
                scene_folder = destination / folder_name
                media_folder = scene_folder / '업로드'
                media_folder.mkdir(parents=True)
                target = media_folder / name
                scene = scenes[index - 1]
                media_files = []
                roles = [('keyframe_start', scene['keyframeStart']), ('keyframe_end', scene['keyframeEnd'])]
                roles += [(f'reference_{i:02d}', asset) for i, asset in enumerate(scene['references'], 1)]
                for role, identifier in roles:
                    if not identifier:
                        continue
                    asset = ASSETS[identifier]
                    filename = role + asset['path'].suffix
                    shutil.copy2(asset['path'], media_folder / filename)
                    media_files.append({'role': role, 'file': '업로드/' + filename, 'originalName': asset['name']})
                if scene.get('resultVideo'):
                    video = ASSETS[scene['resultVideo']]
                    shutil.copy2(video['path'], scene_folder / ('결과영상' + video['path'].suffix))
                (scene_folder / '프롬프트.txt').write_text(scene['prompt'], encoding='utf-8-sig')
                (scene_folder / '장면정보.json').write_text(json.dumps({**clip, 'status': scene['status'], 'images': media_files,
                    'note': '파일명은 구분용입니다. 생성 사이트에서 시작·끝 프레임 역할과 레퍼런스 순서를 확인해주세요.'}, ensure_ascii=False, indent=2), encoding='utf-8')
            run_media([FFMPEG, '-v', 'error', '-nostdin', '-i', str(source['path']),
                       '-ss', f'{clip["start"]:.6f}', '-t', f'{clip["end"] - clip["start"]:.6f}',
                       '-map', '0:a:0', '-vn', '-map_metadata', '-1', '-c:a', 'libmp3lame', '-q:a', '2', str(target)])
            exported.append({**clip, 'duration': clip['end'] - clip['start'], 'file': name if audio_only else folder_name + '/업로드/' + name, 'folder': '' if audio_only else folder_name})
        if state is not None and not audio_only:
            projects.write_project(destination / (safe_name(project) + '.2bz'), source, state, ASSETS)
        manifest = {'source': source['name'], 'project': project, 'clips': exported,
                    'note': '원곡의 start~end 초 구간. 속도 변경·자동 페이드 없음. MP3 고품질 재인코딩.'}
        if not audio_only:
            (destination / '구간목록.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        # This newly-created directory only contains this failed export batch.
        if not destination.resolve().is_relative_to(OUTPUT_ROOT.resolve()):
            raise ValueError('저장 경로를 확인해주세요.')
        shutil.rmtree(destination)
        raise
    for item in exported:
        key = uuid.uuid4().hex
        EXPORTED_FOLDERS[key] = destination / item['folder']
        item['folderId'] = key
    opened = False
    if open_folder and os.name == 'nt':
        try:
            os.startfile(destination)
            opened = True
        except OSError:
            pass
    return {'folder': str(destination), 'files': exported, 'folderOpened': opened}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, value, status=200):
        self.send_bytes(json.dumps(value, ensure_ascii=False).encode(), 'application/json; charset=utf-8', status)

    def send_bytes(self, data, kind, status=200):
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; media-src 'self' blob:; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(data)

    def send_file(self, path, kind):
        size = path.stat().st_size
        start, end = 0, size - 1
        header = self.headers.get('Range')
        if header:
            match = re.fullmatch(r'bytes=(\d*)-(\d*)', header)
            if not match or not any(match.groups()):
                self.send_error(416)
                return
            left, right = match.groups()
            if left:
                start = int(left)
                end = min(int(right), end) if right else end
            else:
                start = max(0, size - int(right))
            if start > end or start >= size:
                self.send_error(416)
                return
        self.send_response(206 if header else 200)
        self.send_header('Content-Type', kind)
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Length', str(end - start + 1))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        if header:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.end_headers()
        with path.open('rb') as file:
            file.seek(start)
            remaining = end - start + 1
            try:
                while remaining:
                    chunk = file.read(min(1024 * 1024, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

    def local_request(self):
        allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
        host = self.headers.get('Host', '')
        origin = self.headers.get('Origin')
        return host in allowed and (not origin or origin in {'http://' + h for h in allowed})

    def do_GET(self):
        if not self.local_request():
            self.reply({'error': '허용되지 않은 요청입니다.'}, 403)
            return
        parsed = urlsplit(self.path)
        if parsed.path == '/health':
            self.reply({'app': APP_ID})
        elif parsed.path == '/config':
            self.reply({'token': TOKEN, 'output': str(OUTPUT_ROOT), 'ready': bool(FFMPEG and FFPROBE), 'drafts': RECOVERY.list()})
        elif parsed.path in {'/', '/index.html', '/style.css', '/segments.js', '/main.js', '/scenes.js'}:
            name = 'index.html' if parsed.path == '/' else parsed.path[1:]
            kind = {'html': 'text/html', 'css': 'text/css', 'js': 'text/javascript'}[name.rsplit('.', 1)[1]]
            self.send_bytes((ROOT / name).read_bytes(), kind + '; charset=utf-8')
        elif parsed.path == '/asset':
            query = parse_qs(parsed.query)
            asset = ASSETS.get(query.get('id', [''])[0])
            if query.get('token', [''])[0] != TOKEN or not asset:
                self.reply({'error': '이미지를 찾을 수 없습니다.'}, 404)
                return
            self.send_file(asset.get('preview', asset['path']), asset['mime'])
        elif parsed.path == '/preview':
            query = parse_qs(parsed.query)
            if query.get('token', [''])[0] != TOKEN:
                self.reply({'error': '허용되지 않은 요청입니다.'}, 403)
                return
            with SOURCE_LOCK:
                source = SOURCES.get(query.get('id', [''])[0])
            if not source:
                self.reply({'error': '음악을 다시 열어주세요.'}, 404)
                return
            self.send_bytes(source['preview'].read_bytes(), 'audio/mpeg')
        else:
            self.reply({'error': '페이지를 찾을 수 없습니다.'}, 404)

    def do_POST(self):
        if not self.local_request() or self.headers.get('X-Cutter-Token') != TOKEN:
            self.reply({'error': '허용되지 않은 요청입니다.'}, 403)
            return
        try:
            if not FFMPEG or not FFPROBE:
                raise ValueError('이 PC에서 FFmpeg를 찾지 못했습니다. 실행 안내를 확인해주세요.')
            parsed = urlsplit(self.path)
            length = int(self.headers.get('Content-Length', 0))
            limit = 1024 if parsed.path == '/project-open' else 32 if parsed.path == '/asset-upload' else 512 if parsed.path in {'/upload', '/video-upload'} else 4
            if not 0 < length <= limit * 1024 * 1024:
                raise ValueError(f'이 요청은 {limit} MB 이하로 열어주세요.')
            if parsed.path in {'/upload', '/asset-upload', '/video-upload', '/project-open'}:
                identifier = uuid.uuid4().hex
                path = CACHE / (identifier + '.source')
                remaining = length
                with path.open('wb') as output:
                    while remaining:
                        chunk = self.rfile.read(min(1024 * 1024, remaining))
                        if not chunk:
                            raise ValueError('파일 전송이 끊겼습니다. 다시 열어주세요.')
                        output.write(chunk)
                        remaining -= len(chunk)
                name = parse_qs(parsed.query).get('name', ['파일'])[0][:240]
                if parsed.path == '/asset-upload':
                    if length > 32 * 1024 * 1024:
                        raise ValueError('이미지는 32 MB 이하로 넣어주세요.')
                    result = register_asset(path.read_bytes(), name)
                    path.unlink()
                    self.reply(result)
                elif parsed.path == '/video-upload':
                    result = register_video(path, name)
                    path.unlink()
                    self.reply(result)
                elif parsed.path == '/project-open':
                    info, audio, media = projects.read_project(path)
                    audio_path = CACHE / (uuid.uuid4().hex + '.source')
                    audio_path.write_bytes(audio)
                    result = restore_project(info, audio_path, media)
                    path.unlink()
                    self.reply(result)
                else:
                    self.reply(register_source(path, name))
            elif parsed.path == '/autosave':
                data = json.loads(self.rfile.read(length))
                source = SOURCES.get(data.get('id'))
                if not source:
                    raise ValueError('음악을 먼저 열어주세요.')
                value = projects.state(data['state'], source['duration'], ASSETS)
                updated = RECOVERY.save(source['recoveryId'], source, value, ASSETS)
                self.reply({'updated': updated})
            elif parsed.path == '/recover':
                data = json.loads(self.rfile.read(length))
                info, audio_path, media = RECOVERY.load(data.get('id'))
                self.reply(restore_project(info, audio_path, media, data['id']))
            elif parsed.path == '/last-frame':
                data = json.loads(self.rfile.read(length))
                self.reply(final_frame(data.get('id')))
            elif parsed.path in {'/export', '/project-save'}:
                if length > 4 * 1024 * 1024:
                    raise ValueError('구간 목록이 너무 큽니다.')
                data = json.loads(self.rfile.read(length))
                with SOURCE_LOCK:
                    source = SOURCES.get(data.get('id'))
                if source is None:
                    raise ValueError('음악을 먼저 열어주세요.')
                if not EXPORT_LOCK.acquire(blocking=False):
                    raise ValueError('이전 저장이 끝난 뒤 다시 눌러주세요.')
                try:
                    state = projects.state(data['state'], source['duration'], ASSETS)
                    if parsed.path == '/project-save':
                        folder = OUTPUT_ROOT.parent / 'projects'
                        folder.mkdir(parents=True, exist_ok=True)
                        target = folder / (safe_name(state['project']) + '_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:4] + '.2bz')
                        try:
                            projects.write_project(target, source, state, ASSETS)
                        except Exception:
                            target.unlink(missing_ok=True)
                            raise
                        os.startfile(folder)
                        self.reply({'path': str(target)})
                    else:
                        self.reply(export_clips(source, data.get('clips'), state['project'], state=state, audio_only=data.get('audioOnly') is True))
                finally:
                    EXPORT_LOCK.release()
            elif parsed.path == '/open-scene':
                data = json.loads(self.rfile.read(length))
                folder = EXPORTED_FOLDERS.get(data.get('id'))
                if folder is None:
                    raise ValueError('장면 꾸러미를 먼저 저장해주세요.')
                os.startfile(folder)
                self.reply({'ok': True})
            elif parsed.path == '/open-output':
                self.rfile.read(length)
                output = OUTPUT_ROOT
                output.mkdir(exist_ok=True)
                os.startfile(output)
                self.reply({'ok': True})
            else:
                self.reply({'error': '요청을 찾을 수 없습니다.'}, 404)
        except (ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
            self.reply({'error': str(error)}, 400)
        except OSError:
            self.reply({'error': '파일을 읽거나 저장하지 못했습니다. 공용폴더 연결과 디스크 공간을 확인해주세요.'}, 500)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8791)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    address = f'http://127.0.0.1:{args.port}'
    try:
        server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    except OSError:
        try:
            existing = json.load(urllib.request.urlopen(address + '/health', timeout=2))
            if existing.get('app') == APP_ID:
                if not args.no_browser:
                    webbrowser.open(address)
                return
        except (OSError, ValueError):
            pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        address = f'http://127.0.0.1:{server.server_port}'
    if not args.no_browser:
        webbrowser.open(address)
    server.serve_forever()


if __name__ == '__main__':
    main()

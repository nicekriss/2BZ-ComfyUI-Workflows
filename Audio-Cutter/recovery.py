import json
import os
from pathlib import Path
import re
import shutil
import threading
import uuid
from datetime import datetime

import projects


class RecoveryStore:
    def __init__(self, root):
        self.root = Path(root)
        self.lock = threading.Lock()

    def folder(self, identifier):
        if not isinstance(identifier, str) or not re.fullmatch(r'[0-9a-f]{32}', identifier):
            raise ValueError('복구 작업을 다시 선택해주세요.')
        return self.root / identifier

    def save(self, identifier, source, state, assets):
        folder = self.folder(identifier)
        with self.lock:
            folder.mkdir(parents=True, exist_ok=True)
            info = projects.manifest(source, state, assets)
            files = {'audio': source['path'], **{key: assets[key]['path'] for key in info['assets']}}
            for name, path in files.items():
                target = folder / name
                if not target.exists():
                    temporary = folder / (uuid.uuid4().hex + '.tmp')
                    try:
                        shutil.copyfile(path, temporary)
                        os.replace(temporary, target)
                    finally:
                        temporary.unlink(missing_ok=True)
            info['updated'] = datetime.now().isoformat(timespec='seconds')
            temporary = folder / (uuid.uuid4().hex + '.tmp')
            try:
                with temporary.open('w', encoding='utf-8') as output:
                    json.dump(info, output, ensure_ascii=False)
                    output.flush()
                    os.fsync(output.fileno())
                os.replace(temporary, folder / 'draft.json')
            finally:
                temporary.unlink(missing_ok=True)
            return info['updated']

    def list(self):
        drafts = []
        for path in self.root.glob('*/draft.json'):
            try:
                info = json.loads(path.read_text(encoding='utf-8'))
                drafts.append({'id': path.parent.name, 'project': info['state']['project'], 'updated': info['updated']})
            except (OSError, ValueError, KeyError, TypeError):
                continue
        return sorted(drafts, key=lambda x: x['updated'], reverse=True)

    def load(self, identifier):
        folder = self.folder(identifier)
        with self.lock:
            info = json.loads((folder / 'draft.json').read_text(encoding='utf-8'))
            media = {}
            for key, metadata in info['assets'].items():
                if not re.fullmatch(r'[0-9a-f]{32}', key):
                    raise ValueError('복구 자료 경로를 확인해주세요.')
                media[key] = {**metadata, 'path': folder / key}
            return info, folder / 'audio', media

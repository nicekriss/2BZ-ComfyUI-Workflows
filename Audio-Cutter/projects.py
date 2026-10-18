import json
import math
import zipfile


def image_kind(data):
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return '.png', 'image/png'
    if data.startswith(b'\xff\xd8\xff'):
        return '.jpg', 'image/jpeg'
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return '.webp', 'image/webp'
    raise ValueError('이미지는 PNG, JPG, WebP로 넣어주세요.')


def scene(value, assets):
    if not isinstance(value, dict):
        raise ValueError('장면 정보를 읽을 수 없습니다.')
    refs = value.get('references', [])
    if not isinstance(refs, list) or not all(isinstance(x, str) and x in assets and assets[x].get('kind', 'image') == 'image' for x in refs):
        raise ValueError('장면의 레퍼런스 이미지를 다시 넣어주세요.')
    result = {'prompt': str(value.get('prompt', '')), 'references': list(dict.fromkeys(refs))}
    for key in ('keyframeStart', 'keyframeEnd', 'resultVideo'):
        identifier = value.get(key)
        kind = 'video' if key == 'resultVideo' else 'image'
        if identifier is not None and (not isinstance(identifier, str) or identifier not in assets or assets[identifier].get('kind', 'image') != kind):
            raise ValueError('장면의 이미지 또는 결과 영상을 다시 넣어주세요.')
        result[key] = identifier
    result['status'] = value.get('status', 'draft')
    if result['status'] not in ('draft', 'queued', 'done'):
        raise ValueError('장면 상태를 확인해주세요.')
    return result


def state(value, duration, assets):
    if not isinstance(value, dict) or value.get('version') not in (1, 2):
        raise ValueError('지원하지 않는 프로젝트 형식입니다.')
    points = value.get('points')
    if not isinstance(points, list) or len(points) < 2 or not all(type(x) in (int, float) and math.isfinite(x) for x in points):
        raise ValueError('프로젝트의 구간 경계를 확인해주세요.')
    if points[0] != 0 or abs(points[-1] - duration) > .001 or any(a >= b for a, b in zip(points, points[1:])):
        raise ValueError('프로젝트 구간과 음악 길이가 맞지 않습니다.')
    scenes, names = value.get('scenes', []), value.get('names', [])
    if not isinstance(scenes, list) or len(scenes) != len(points) - 1 or not isinstance(names, list):
        raise ValueError('프로젝트 장면 수가 맞지 않습니다.')
    clips, raw_clips = [], value.get('clips', [])
    if not isinstance(raw_clips, list):
        raise ValueError('장면 바구니 형식을 확인해주세요.')
    for item in raw_clips:
        if not isinstance(item, dict):
            raise ValueError('장면 바구니 형식을 확인해주세요.')
        start, end = float(item['start']), float(item['end'])
        if not (math.isfinite(start) and math.isfinite(end) and 0 <= start < end <= duration + .001):
            raise ValueError('장면 바구니의 구간을 확인해주세요.')
        clips.append({'name': str(item.get('name', '장면')), 'start': start, 'end': end, 'scene': scene(item.get('scene', {}), assets)})
    library = value.get('library')
    if library is None:
        library = [{'id': key, 'label': asset['name'], 'category': '기타'} for key, asset in assets.items() if asset.get('kind', 'image') == 'image']
    if not isinstance(library, list):
        raise ValueError('공통 자료함 형식을 확인해주세요.')
    clean_library, seen = [], set()
    for item in library:
        if not isinstance(item, dict) or not isinstance(item.get('id'), str) or item['id'] not in assets or assets[item['id']].get('kind', 'image') != 'image':
            raise ValueError('공통 자료함 이미지를 확인해주세요.')
        if item['id'] in seen:
            continue
        seen.add(item['id'])
        category = item.get('category', '기타')
        clean_library.append({'id': item['id'], 'label': str(item.get('label', assets[item['id']]['name'])), 'category': category if category in ('캐릭터', '의상', '배경', '기타') else '기타'})
    view = value.get('view', {})
    if not isinstance(view, dict):
        raise ValueError('프로젝트 선택 위치를 확인해주세요.')
    active, free_active = view.get('active', 0), view.get('freeActive', -1)
    if type(active) is not int or type(free_active) is not int:
        raise ValueError('프로젝트 선택 위치를 확인해주세요.')
    return {'version': 2, 'project': str(value.get('project', '뮤비_장면')), 'mode': 'free' if value.get('mode') == 'free' else 'split',
            'points': points, 'names': [str(x or '') for x in names[:len(scenes)]], 'library': clean_library,
            'view': {'active': max(0, min(active, len(scenes) - 1)), 'freeActive': max(-1, min(free_active, len(clips) - 1))},
            'scenes': [scene(x, assets) for x in scenes], 'clips': clips}


def used_assets(value):
    identifiers = {item['id'] for item in value.get('library', [])}
    for item in value['scenes'] + [clip['scene'] for clip in value['clips']]:
        identifiers.update(item['references'])
        identifiers.update(item.get(key) for key in ('keyframeStart', 'keyframeEnd', 'resultVideo') if item.get(key))
    return identifiers


def manifest(source, value, assets):
    return {'state': value, 'audioName': source['name'], 'assets': {
        key: {'name': assets[key]['name'], 'kind': assets[key].get('kind', 'image'), 'extension': assets[key]['path'].suffix}
        for key in sorted(used_assets(value))}}


def write_project(path, source, value, assets):
    info = manifest(source, value, assets)
    encoded = json.dumps(info, ensure_ascii=False).encode('utf-8')
    total = len(encoded) + source['path'].stat().st_size + sum(assets[key]['path'].stat().st_size for key in info['assets'])
    if total > 1024 * 1024 * 1024 - 1024 * 1024 or len(encoded) > 4 * 1024 * 1024:
        raise ValueError('프로젝트는 1 GB 이내로 저장해주세요. 큰 결과 영상을 줄여주세요.')
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_STORED) as archive:
        archive.writestr('project.json', encoded)
        archive.write(source['path'], 'audio')
        for key in info['assets']:
            archive.write(assets[key]['path'], 'assets/' + key)


def read_project(path):
    # Read exact archive members only; never extract archive paths.
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            names = [x.filename for x in entries]
            if len(names) != len(set(names)) or sum(x.file_size for x in entries) > 1024 * 1024 * 1024:
                raise ValueError('프로젝트가 너무 크거나 중복 파일이 있습니다.')
            if archive.getinfo('project.json').file_size > 4 * 1024 * 1024:
                raise ValueError('프로젝트 정보가 너무 큽니다.')
            info = json.loads(archive.read('project.json'))
            if not isinstance(info, dict) or not isinstance(info.get('assets'), dict):
                raise ValueError('프로젝트 정보를 읽을 수 없습니다.')
            assets = info['assets']
            if any(len(k) != 32 or any(c not in '0123456789abcdef' for c in k) for k in assets):
                raise ValueError('프로젝트 자료 목록을 확인해주세요.')
            if set(names) != {'project.json', 'audio', *('assets/' + k for k in assets)}:
                raise ValueError('프로젝트에 허용되지 않은 파일이 있습니다.')
            media = {}
            for key, metadata in assets.items():
                if isinstance(metadata, str):
                    metadata = {'name': metadata, 'kind': 'image'}
                if not isinstance(metadata, dict) or metadata.get('kind') not in ('image', 'video'):
                    raise ValueError('프로젝트 자료 형식을 확인해주세요.')
                limit = 512 if metadata['kind'] == 'video' else 32
                if archive.getinfo('assets/' + key).file_size > limit * 1024 * 1024:
                    raise ValueError(f'자료 파일은 {limit} MB 이하로 넣어주세요.')
                data = archive.read('assets/' + key)
                if metadata['kind'] == 'image':
                    image_kind(data)
                media[key] = {**metadata, 'data': data}
            return info, archive.read('audio'), media
    except (zipfile.BadZipFile, KeyError, UnicodeDecodeError, RuntimeError) as error:
        raise ValueError('프로젝트 파일이 손상되었거나 2BZ 프로젝트가 아닙니다.') from error

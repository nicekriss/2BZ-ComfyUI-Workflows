"""Apply only the fingerprinted H3 gate-loading patch; never guess at newer code."""
import argparse
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def plan(root):
    changes = []
    for item in json.loads((HERE / 'h3-gate-patch.json').read_text(encoding='utf-8')):
        if item['path'] not in ('comfy/model_detection.py', 'comfy/ldm/minimax/model.py'):
            raise RuntimeError('Invalid patch target.')
        path = root / item['path']
        if path.resolve() != root.resolve() / item['path']:
            raise RuntimeError('Linked H3 source is not supported: ' + str(path))
        current = path.read_text(encoding='utf-8')
        if digest(current) == item['after_sha256']:
            continue
        if digest(current) != item['before_sha256']:
            raise RuntimeError('Unverified H3 source version; preserved: ' + str(path) +
                               '. See START-HERE-ko.md compatibility section. Do not downgrade blindly.')
        result = current
        for edit in reversed(item['edits']):
            result = result[:edit['start']] + edit['replacement'] + result[edit['end']:]
        if digest(result) != item['after_sha256']:
            raise RuntimeError('Patch fingerprint mismatch; nothing changed.')
        compile(result, str(path), 'exec')
        changes.append((path, result))
    return changes


def apply(root):
    changes = plan(root)
    if not changes:
        print('H3 gate source: verified patched version already present.')
        return
    backup = root / 'user' / '2bz-solattn-installer' / ('h3-backup-' + str(time.time_ns()))
    backup.mkdir(parents=True)
    records = []
    for index, (path, result) in enumerate(changes):
        data = path.read_bytes()
        (backup / str(index)).write_bytes(data)
        records.append({'path': path.relative_to(root).as_posix(), 'backup': str(index),
                        'backup_sha256': hashlib.sha256(data).hexdigest(),
                        'after_sha256': digest(result)})
    (backup / 'manifest.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
    try:
        for path, result in changes:
            path.write_text(result, encoding='utf-8', newline='')
    except BaseException:
        for record in records:
            (root / record['path']).write_bytes((backup / record['backup']).read_bytes())
        raise
    print('H3 gate patch applied. Backup:', backup)


def restore(root):
    state = root / 'user' / '2bz-solattn-installer'
    backups = sorted(state.glob('h3-backup-*'))
    if not backups:
        print('No H3 patch backup; nothing to restore.')
        return
    backup = backups[-1]
    records = json.loads((backup / 'manifest.json').read_text(encoding='utf-8'))
    for record in records:
        path = root / record['path']
        if record['path'] not in ('comfy/model_detection.py', 'comfy/ldm/minimax/model.py'):
            raise RuntimeError('Invalid backup path.')
        if path.resolve() != root.resolve() / record['path'] or Path(record['backup']).name != record['backup']:
            raise RuntimeError('Invalid backup location.')
        if digest(path.read_text(encoding='utf-8')) != record['after_sha256']:
            raise RuntimeError('H3 source changed since patch; manual review required. Preserved: ' + str(path))
        if not (backup / record['backup']).is_file():
            raise RuntimeError('Incomplete H3 backup.')
        if hashlib.sha256((backup / record['backup']).read_bytes()).hexdigest() != record['backup_sha256']:
            raise RuntimeError('H3 backup checksum mismatch; nothing restored.')
    for record in records:
        (root / record['path']).write_bytes((backup / record['backup']).read_bytes())
    print('H3 source restored from:', backup)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--restore', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    if args.restore:
        restore(root)
    elif args.apply:
        apply(root)
    else:
        changes = plan(root)
        print('H3 gate source:', 'known version; patch required' if changes else 'verified patched version')

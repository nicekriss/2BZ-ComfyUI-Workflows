"""Install the pinned VSA dependency with a local, exact-file rollback."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import time
import urllib.request

VERSION = '0.2.32'
NODE_URL = 'https://github.com/user-attachments/files/31576773/sol_attn_minimax_v5.py'
NODE_SHA = '97c9d56fdc7c9a102e59bff9ac8d79503299514d061892088a03d99dcf415b0c'
HERE = Path(__file__).resolve().parent


def package_paths(site):
    return [p for p in site.iterdir() if p.name == 'comfy_kitchen' or
            (p.name.startswith('comfy_kitchen-') and p.name.endswith('.dist-info'))]


def snapshot(site, backup):
    backup.mkdir(parents=True, exist_ok=False)
    names = []
    for path in package_paths(site):
        if path.is_symlink() or path.resolve().parent != site:
            raise RuntimeError('Linked package layout is not supported; nothing changed.')
        shutil.copytree(path, backup / path.name)
        names.append(path.name)
    (backup / 'manifest.json').write_text(json.dumps({
        'site': str(site), 'python': sys.executable, 'names': names
    }), encoding='utf-8')


def restore(site, backup):
    manifest = json.loads((backup / 'manifest.json').read_text(encoding='utf-8'))
    if Path(manifest['site']).resolve() != site:
        raise RuntimeError('Backup belongs to a different Python environment.')
    for name in manifest['names']:
        if Path(name).name != name or not (backup / name).is_dir():
            raise RuntimeError('Invalid or incomplete backup.')
        if name != 'comfy_kitchen' and not (name.startswith('comfy_kitchen-') and name.endswith('.dist-info')):
            raise RuntimeError('Invalid backup entry.')
    displaced = backup / ('displaced-' + str(time.time_ns()))
    displaced.mkdir()
    for path in package_paths(site):
        if path.resolve().parent != site or path.is_symlink():
            raise RuntimeError('Refusing to move a linked package.')
        shutil.move(str(path), str(displaced / path.name))
    for name in manifest['names']:
        shutil.copytree(backup / name, site / name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--restore', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    if not (root / 'main.py').is_file():
        raise RuntimeError('Not a ComfyUI root.')
    site = Path(sysconfig.get_path('purelib')).resolve()
    state = root / 'user' / '2bz-solattn-installer'
    state.mkdir(parents=True, exist_ok=True)
    log_path = state / ('install-' + str(time.time_ns()) + '.log')
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    env['PYTHONUTF8'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'
    with log_path.open('w', encoding='utf-8') as log:
        def say(message):
            print(message, flush=True)
            log.write(message + '\n')
            log.flush()

        def run(arguments, checked=True):
            result = subprocess.run([sys.executable, '-s', *arguments], cwd=root,
                                    env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    encoding='utf-8', errors='replace')
            say(result.stdout)
            if checked and result.returncode:
                raise RuntimeError('Command failed; see log: ' + str(log_path))
            return result.returncode

        say('Python: ' + sys.executable)
        say('Log: ' + str(log_path))
        pointer = state / 'last-backup.txt'
        if args.restore:
            run([str(HERE / 'h3_compat.py'), '--root', str(root), '--restore'])
            if not pointer.exists():
                say('No Kitchen backup; Kitchen unchanged. SolAttn and USDU are retained.')
                return
            backup = Path(pointer.read_text(encoding='utf-8')).resolve()
            if not backup.is_relative_to(state.resolve()):
                raise RuntimeError('Backup is outside installer state directory.')
            restore(site, backup)
            say('RESTORED previous comfy-kitchen files. Restart ComfyUI. SolAttn node is retained.')
            return
        check = [str(HERE / 'check_solattn.py')]
        if args.check_only:
            run([str(HERE / 'h3_compat.py'), '--root', str(root)])
            run(check)
            return
        # Reject unknown core source before changing any installed package.
        run([str(HERE / 'h3_compat.py'), '--root', str(root)])
        # Reject unsupported GPUs and outdated frontend API before changing packages.
        run(['-c', 'import torch; from comfy_api.latest import io; '
             'assert torch.cuda.is_available(), "CUDA unavailable"; '
             'assert torch.cuda.get_device_capability()[0]>=8, "SM80+ required"; '
             'assert torch.cuda.is_bf16_supported(), "BF16 required"; '
             'assert hasattr(io,"DynamicCombo"), "Update ComfyUI first"'])
        node = root / 'custom_nodes' / 'ComfyUI-SolAttn-MiniMax' / '__init__.py'
        if node.exists() and hashlib.sha256(node.read_bytes()).hexdigest() != NODE_SHA:
            raise RuntimeError('Existing SolAttn node differs from verified v5. Preserved; no packages changed.')
        try:
            version = importlib.metadata.version('comfy-kitchen')
        except importlib.metadata.PackageNotFoundError:
            version = 'not installed'
        say('Current comfy-kitchen: ' + version)
        backup = None
        changed = False
        try:
            if run(check, checked=False):
                run(['-m', 'pip', '--version'])
                with tempfile.TemporaryDirectory(prefix='2bz-kitchen-wheel-') as temp:
                    run(['-m', 'pip', 'download', '--disable-pip-version-check', '--no-deps',
                         '--only-binary=:all:', '--dest', temp, 'comfy-kitchen==' + VERSION])
                    wheels = list(Path(temp).glob('*.whl'))
                    if len(wheels) != 1:
                        raise RuntimeError('Expected one compatible wheel; no packages changed.')
                    backup = state / ('backup-' + str(time.time_ns()))
                    snapshot(site, backup)
                    pointer.write_text(str(backup), encoding='utf-8')
                    changed = True
                    run(['-m', 'pip', 'install', '--disable-pip-version-check', '--no-deps',
                         '--force-reinstall', str(wheels[0])])
                run(check)
            if not node.exists():
                with urllib.request.urlopen(NODE_URL, timeout=60) as response:
                    data = response.read()
                if hashlib.sha256(data).hexdigest() != NODE_SHA:
                    raise RuntimeError('Original SolAttn v5 SHA-256 mismatch.')
                node.parent.mkdir(parents=True, exist_ok=True)
                # Exclusive creation preserves any file created by another installer.
                with node.open('xb') as output:
                    output.write(data)
            run([str(HERE / 'h3_compat.py'), '--root', str(root), '--apply'])
            say('DEPENDENCIES READY: VSA CUDA passed, SolAttn v5 and H3 gate source verified.')
            say('USDU and models are separate steps. This does NOT mean the workflow is ready to render.')
            say('Restart ComfyUI; use VSA (FastVideo). Check actual H3 log for VSA tiles and no fallback.')
            say('This is a kernel test, not a full H3 speed/quality benchmark.')
            if backup:
                say('Restore-SolAttn-MiniMax.bat can restore: ' + str(backup))
        except BaseException:
            if changed:
                say('Installation failed. Restoring exact previous package files...')
                restore(site, backup)
                say('ROLLBACK COMPLETE. Prior package files restored; details: ' + str(log_path))
            raise


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('FAILED:', error, flush=True)
        sys.exit(1)

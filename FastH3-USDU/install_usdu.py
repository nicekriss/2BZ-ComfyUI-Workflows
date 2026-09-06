"""Install the tested H3 fork and pinned submodule without importing the node."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

URL = 'https://github.com/lisitskyaa/ComfyUI_UltimateSDUpscaleGuider_H3'
COMMIT = '6836cf365d1b84ef2cb605a8e92a0901a6d2c81f'
SUBMODULE = '2322caa480535b1011a1f9c18126d85ea444f146'


def install(root):
    if not (root / 'main.py').is_file():
        raise RuntimeError('Choose the ComfyUI folder containing main.py.')
    git = shutil.which('git')
    if not git:
        raise RuntimeError('Git is required. Install Git for Windows, then reopen this installer.')
    target = root / 'custom_nodes' / 'ComfyUI_UltimateSDUpscaleGuider_H3'
    for directory in (root / 'custom_nodes').iterdir():
        if directory.name.endswith('.disabled'):
            continue
        source = directory / 'usdu_nodes.py'
        if directory != target and source.is_file() and 'UltimateSDUpscaleGuider' in source.read_text(encoding='utf-8'):
            raise RuntimeError('Another USDU Guider pack may register the same node: ' + str(directory) +
                               '. Disable it in Manager before retrying; nothing deleted.')
    def run(*args, cwd=None):
        return subprocess.check_output([git, *args], cwd=cwd, text=True).strip()
    def verify(path):
        if run('rev-parse', 'HEAD', cwd=path) != COMMIT:
            raise RuntimeError('Existing USDU revision differs; preserved for manual review.')
        sub = path / 'repositories' / 'ultimate_sd_upscale'
        if not (sub / 'scripts' / 'ultimate-upscale.py').is_file():
            raise RuntimeError('USDU submodule is incomplete. See START-HERE-ko.md.')
        if run('rev-parse', 'HEAD', cwd=sub) != SUBMODULE:
            raise RuntimeError('USDU submodule revision differs; preserved.')
        if run('status', '--porcelain', '--untracked-files=no', cwd=path):
            raise RuntimeError('Existing USDU has local edits; preserved for manual review.')
    if target.exists():
        verify(target)
        print('USDU pinned revision and submodule already installed.')
        return
    state = root / 'user' / '2bz-solattn-installer'
    state.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='usdu-stage-', dir=state)) / 'repo'
    print('Download staging (retained on failure):', stage)
    run('clone', '--no-checkout', URL, str(stage))
    run('checkout', '--detach', COMMIT, cwd=stage)
    run('submodule', 'update', '--init', '--recursive', cwd=stage)
    verify(stage)
    if target.exists():
        raise RuntimeError('Destination appeared during installation; preserved.')
    stage.rename(target)
    # Git stores submodule worktree paths relative to this tree; verify after moving it.
    verify(target)
    print('USDU INSTALLED. Restart ComfyUI after completing model setup. No model downloads performed.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    install(args.root.resolve())

"""Explicit isolated download test. Does not start ComfyUI or import downloaded code."""
import importlib.util
from pathlib import Path
import tempfile

base = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('install_usdu', base / 'FastH3-USDU/install_usdu.py')
usdu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(usdu)

with tempfile.TemporaryDirectory(prefix='2bz-usdu-download-test-') as temporary:
    root = Path(temporary)
    (root / 'main.py').touch()
    (root / 'custom_nodes').mkdir()
    usdu.install(root)
    usdu.install(root)
    other = root / 'custom_nodes' / 'OtherUSDU'
    other.mkdir()
    (other / 'usdu_nodes.py').write_text('UltimateSDUpscaleGuider', encoding='utf-8')
    try:
        usdu.install(root)
    except RuntimeError as error:
        assert 'Another USDU' in str(error)
    else:
        raise AssertionError('Duplicate pack was not rejected')
    print('PASS: isolated download, pinned submodule, post-move verification, repeat install, duplicate refusal.')

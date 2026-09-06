"""Offline installer contract tests; no live install or model execution."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('h3_compat', BASE / 'FastH3-USDU/h3_compat.py')
compat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compat)
SOURCE = Path('C:/mini/minimax/ComfyUI')


class GatePatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='2bz-patch-test-')
        self.root = Path(self.temp.name)
        self.original = {}
        for name in ('comfy/model_detection.py', 'comfy/ldm/minimax/model.py'):
            data = subprocess.check_output(['git', '-C', str(SOURCE), 'show',
                '7fd919f0caff66a52289ea5b19cb6eaca0da04ef:' + name])
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            self.original[name] = data

    def tearDown(self):
        self.temp.cleanup()

    def test_apply_idempotent_restore(self):
        self.assertEqual(len(compat.plan(self.root)), 2)
        compat.apply(self.root)
        self.assertEqual(compat.plan(self.root), [])
        compat.apply(self.root)
        compat.restore(self.root)
        for name, data in self.original.items():
            self.assertEqual((self.root / name).read_bytes(), data)

    def test_unknown_source_preserved_before_any_write(self):
        path = self.root / 'comfy/ldm/minimax/model.py'
        path.write_bytes(path.read_bytes() + b'\n# user edit\n')
        with self.assertRaisesRegex(RuntimeError, 'Unverified'):
            compat.apply(self.root)
        self.assertEqual((self.root / 'comfy/model_detection.py').read_bytes(), self.original['comfy/model_detection.py'])
        self.assertFalse((self.root / 'user').exists())

    def test_restore_preserves_newer_user_edit(self):
        compat.apply(self.root)
        path = self.root / 'comfy/ldm/minimax/model.py'
        edited = path.read_bytes() + b'\n# later edit\n'
        path.write_bytes(edited)
        with self.assertRaisesRegex(RuntimeError, 'changed since patch'):
            compat.restore(self.root)
        self.assertEqual(path.read_bytes(), edited)
        self.assertNotEqual((self.root / 'comfy/model_detection.py').read_bytes(), self.original['comfy/model_detection.py'])

    def test_crlf_source(self):
        for name in self.original:
            path = self.root / name
            path.write_bytes(path.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
        compat.apply(self.root)
        self.assertEqual(compat.plan(self.root), [])

    def test_workflow_contract(self):
        graph = json.loads((BASE / 'FastH3-USDU/2BZ_FastH3_USDU.json').read_text(encoding='utf-8'))
        nodes = {n['id']: n for n in graph['nodes']}
        self.assertEqual(len(nodes), 27)
        self.assertFalse(set(nodes) & set(range(34, 42)))
        self.assertEqual(nodes[31]['widgets_values'][0], 'RealESRGAN_x2plus.pth')
        self.assertEqual(nodes[2]['widgets_values'][0], '')
        self.assertEqual(nodes[3]['mode'], 4)
        self.assertEqual(nodes[24]['widgets_values'][0], 2.0)
        self.assertEqual(nodes[12]['widgets_values'], ['simple', 2, .20])
        self.assertTrue(any(link[1:5] == [24, 0, 16, 0] for link in graph['links']))
        self.assertIn('96분 37초', nodes[42]['widgets_values'][0])
        self.assertIn('48분 40초', nodes[42]['widgets_values'][0])
        self.assertIn('47분 36초', nodes[42]['widgets_values'][0])
        self.assertIn('1w0xkpb', nodes[28]['widgets_values'][0])
        self.assertIn('1vwgoy2', nodes[28]['widgets_values'][0])
        self.assertFalse(any('Latent' in n['type'] for n in nodes.values()))
        self.assertFalse(any(n['type'] == 'ModelMemoryUsageFactorOverride' for n in nodes.values()))
        for node in nodes.values():
            if 'widgets_values_named' in node:
                for inp in node.get('inputs', []):
                    if inp.get('widget', {}).get('name') == 'denoise':
                        self.assertEqual(node['widgets_values_named']['denoise'], .20)
        for target, slot in ((24, 10), (24, 11), (10, 5), (10, 6)):
            self.assertTrue(any(link[1] == 19 and link[3:5] == [target, slot] for link in graph['links']))


if __name__ == '__main__':
    unittest.main()

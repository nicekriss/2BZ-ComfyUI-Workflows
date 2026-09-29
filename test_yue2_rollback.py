"""Failure injection for the complete installer; no packages or models are installed."""
from contextlib import ExitStack, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from test_yue2_installer import BASE, Response, installer

REAL_RUN = installer.run


class RollbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = (Path(self.temp.name) / 'ComfyUI').resolve()
        self.root.mkdir()
        (self.root / 'main.py').touch()
        (self.root / 'custom_nodes').mkdir()
        self.state = self.root / 'user/2bz-yue2'
        self.state.mkdir(parents=True)
        self.abc_state = self.root / 'user/abc-studio'
        self.here = Path(self.temp.name) / 'installer'
        shutil.copytree(BASE, self.here, ignore=shutil.ignore_patterns('__pycache__'))
        self.node = self.root / 'custom_nodes/ComfyUI-YuE2'
        self.abc = self.root / 'custom_nodes/toobusy-abc-studio'
        self.model = self.root / 'models/audio_encoders/YuE2-3B/model.safetensors'
        self.old_abc = {'abc_studio_node/abc_studio.py': '# old ABC\n'}
        self.new_abc = {'abc_studio_node/abc_studio.py': '# new ABC\n', 'install_sheetsage2.py': '# fixture\n'}
        fingerprints = lambda files: {name: hashlib.sha256(text.encode()).hexdigest() for name, text in files.items()}
        (self.here / 'abc-studio-versions.json').write_text(json.dumps({
            'old': fingerprints(self.old_abc), installer.ABC_STUDIO_REF: fingerprints(self.new_abc)}))
        abc_archive = self.state / f'toobusy-abc-studio-{installer.ABC_STUDIO_REF}.zip'
        with zipfile.ZipFile(abc_archive, 'w') as archive:
            for name, text in self.new_abc.items():
                archive.writestr('studio/' + name, text)
        source_archive = self.state / 'yue2-source.zip'
        with zipfile.ZipFile(source_archive, 'w') as archive:
            archive.writestr('YuE/src/yue2/__init__.py', '# fixture')
        manifest = json.loads((self.here / 'downloads.json').read_text())
        manifest['source_sha256'] = installer.digest(source_archive)
        manifest['abc_studio']['sha256'] = installer.digest(abc_archive)
        manifest['models'] = [{'kind': 'model', 'name': 'model.safetensors', 'bytes': 5,
                               'sha256': hashlib.sha256(b'model').hexdigest(), 'url': 'https://example.invalid/model'}]
        (self.here / 'downloads.json').write_text(json.dumps(manifest))
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for name, value in [('HERE', self.here), ('_running_comfyui', lambda root: []),
                            ('environment', lambda: 'fixture-site'), ('package_state', lambda: {}),
                            ('prepare_runtime', self.prepare_runtime), ('smoke_runtime', lambda *args: None),
                            ('run', self.install_sheetsage)]:
            self.stack.enter_context(patch.object(installer, name, value))
        self.stack.enter_context(patch('sys.argv', ['installer', '--root', str(self.root)]))
        self.stack.enter_context(patch.object(installer.urllib.request, 'urlopen', side_effect=lambda *a, **k: Response(b'model')))

    def prepare_runtime(self, state, shared):
        runtime = state / 'runtime'
        site = runtime / 'Lib/site-packages'
        site.mkdir(parents=True)
        (runtime / 'Scripts').mkdir()
        python = runtime / 'Scripts/python.exe'
        python.write_bytes(b'new runtime')
        return python, site

    def install_sheetsage(self, command, **kwargs):
        if '--check-only' in command:
            raise subprocess.CalledProcessError(1, command)
        runtime = self.abc_state / 'runtime'
        runtime.mkdir(parents=True)
        (runtime / 'new-torch.txt').write_text('new torch')
        (self.abc_state / 'python311').mkdir(exist_ok=True)
        (self.abc_state / 'setup.json').write_text('{"new": true}')

    def fail_sheetsage(self, command, **kwargs):
        self.install_sheetsage(command, **kwargs)
        raise subprocess.CalledProcessError(1, command)

    def upgrade_fixture(self):
        for name, text in self.old_abc.items():
            path = self.abc / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        self.node.mkdir()
        (self.node / 'nodes.py').write_text('# old bridge\n')
        (self.here / 'bridge-versions.json').write_text(json.dumps({'old': {'nodes.py': installer._code_digest(self.node / 'nodes.py')}}))
        config = {'runtime': str(self.state / 'runtime/Scripts/python.exe'),
                  'model': str(self.model.parent), 'vae': str(self.root / 'models/vae')}
        (self.node / 'setup.json').write_text(json.dumps(config))
        (self.state / 'runtime').mkdir()
        (self.state / 'runtime/user-package.txt').write_text('original Yue runtime')
        (self.abc_state / 'runtime').mkdir(parents=True)
        (self.abc_state / 'runtime/original.txt').write_text('original ABC runtime')
        (self.abc_state / 'setup.json').write_text('{"old": true}')
        (self.abc_state / 'scores').mkdir()
        (self.abc_state / 'scores/user.abc').write_text('user score')

    def journal(self):
        files = list((self.state / 'audits').glob('*/rollback.json'))
        self.assertEqual(len(files), 1)
        return json.loads(files[0].read_text())

    def test_late_failure_removes_new_nodes_runtimes_but_keeps_models(self):
        with patch.object(installer, 'run', side_effect=self.fail_sheetsage):
            with self.assertRaises(subprocess.CalledProcessError):
                installer.main()
        for path in (self.node, self.abc, self.state / 'runtime', self.abc_state / 'runtime',
                     self.abc_state / 'python311', self.abc_state / 'setup.json'):
            self.assertFalse(path.exists(), path)
        self.assertEqual(self.model.read_bytes(), b'model')
        self.assertTrue((self.state / 'yue2-source.zip').exists())
        self.assertEqual(self.journal()['status'], 'rolled-back')
        installer.main()
        self.assertTrue(self.node.is_dir())
        self.assertTrue((self.abc_state / 'setup.json').is_file())

    def test_late_failure_restores_both_nodes_and_original_runtime_and_scores(self):
        self.upgrade_fixture()
        old_setup = (self.node / 'setup.json').read_bytes()
        with patch.object(installer, 'run', side_effect=self.fail_sheetsage):
            with self.assertRaises(subprocess.CalledProcessError):
                installer.main()
        self.assertEqual((self.abc / 'abc_studio_node/abc_studio.py').read_text(), '# old ABC\n')
        self.assertEqual((self.node / 'nodes.py').read_text(), '# old bridge\n')
        self.assertEqual((self.node / 'setup.json').read_bytes(), old_setup)
        self.assertEqual((self.abc_state / 'runtime/original.txt').read_text(), 'original ABC runtime')
        self.assertFalse((self.abc_state / 'runtime/new-torch.txt').exists())
        self.assertEqual((self.abc_state / 'setup.json').read_text(), '{"old": true}')
        self.assertEqual((self.abc_state / 'scores/user.abc').read_text(), 'user score')
        self.assertEqual((self.state / 'runtime/user-package.txt').read_text(), 'original Yue runtime')

    def test_success_keeps_node_backups_and_removes_old_runtime_backup(self):
        self.upgrade_fixture()
        installer.main()
        journal = self.journal()
        self.assertEqual(journal['status'], 'committed')
        self.assertTrue((self.abc_state / 'runtime/new-torch.txt').exists())
        for entry in journal['entries']:
            if entry['backup']:
                self.assertEqual(Path(entry['backup']).exists(), not entry['discard_backup'])

    def test_final_environment_audit_failure_rolls_back_without_success_message(self):
        output = io.StringIO()
        with patch.object(installer, 'report_preservation', side_effect=RuntimeError('audit failed')), redirect_stdout(output):
            with self.assertRaisesRegex(RuntimeError, 'audit failed'):
                installer.main()
        self.assertNotIn('INSTALLED', output.getvalue())
        self.assertFalse(self.node.exists())
        self.assertFalse((self.root / 'user/default/workflows/2BZ_YuE2_Music.json').exists())
        self.assertEqual(self.journal()['status'], 'rolled-back')

    def test_install_error_is_not_hidden_by_audit_error(self):
        with patch.object(installer, 'prepare_runtime', side_effect=RuntimeError('original failure')), \
             patch.object(installer, 'report_preservation', side_effect=RuntimeError('audit failed')):
            with self.assertRaisesRegex(RuntimeError, 'original failure'):
                installer.main()
        self.assertFalse(self.abc.exists())

    def test_healthy_sheetsage_reuses_runtime_without_installing(self):
        self.upgrade_fixture()
        (self.abc_state / 'setup.json').write_text(json.dumps({'model': str(self.root / 'models/abc_studio/SheetSage2')}))
        with patch.object(installer, 'run') as run:
            installer.main()
        run.assert_called_once()
        self.assertIn('--check-only', run.call_args.args[0])
        self.assertEqual((self.abc_state / 'runtime/original.txt').read_text(), 'original ABC runtime')

    def test_partial_runtime_creation_is_removed_and_next_install_works(self):
        def broken_runtime(state, shared):
            (state / 'runtime').mkdir()
            (state / 'runtime/partial.txt').touch()
            raise RuntimeError('venv failed')
        with patch.object(installer, 'prepare_runtime', side_effect=broken_runtime):
            with self.assertRaisesRegex(RuntimeError, 'venv failed'):
                installer.main()
        self.assertFalse((self.state / 'runtime').exists())
        installer.main()
        self.assertTrue(self.node.exists())

    def test_failed_node_copy_cleans_temporary_folder_and_can_retry(self):
        destination = self.root / 'custom_nodes/test-node'
        source = self.here / 'custom_nodes/ComfyUI-YuE2'
        rename = Path.rename
        def fail_promotion(path, target):
            if Path(target) == destination:
                raise PermissionError('injected lock')
            return rename(path, target)
        with patch.object(Path, 'rename', fail_promotion):
            with self.assertRaises(PermissionError):
                installer._copy_node_package(source, destination)
        self.assertEqual(list(destination.parent.glob('.test-node.installing-*')), [])
        installer._copy_node_package(source, destination)
        self.assertTrue((destination / 'nodes.py').exists())

    def test_invalid_model_partial_is_removed(self):
        with self.assertRaisesRegex(RuntimeError, 'checksum failed'):
            installer.download('https://example.invalid', self.model, '0' * 64)
        self.assertFalse(self.model.with_name('model.safetensors.part').exists())

    def test_network_interruption_keeps_partial_for_resume(self):
        class BrokenResponse(Response):
            def read(self, size=-1):
                if self.tell():
                    raise OSError('network interrupted')
                return super().read(size)
        with patch.object(installer.urllib.request, 'urlopen', return_value=BrokenResponse(b'partial')):
            with self.assertRaisesRegex(OSError, 'network interrupted'):
                installer.download('https://example.invalid', self.model, '0' * 64)
        self.assertEqual(self.model.with_name('model.safetensors.part').read_bytes(), b'partial')

    def test_recovery_failure_preserves_backup_and_blocks_next_install(self):
        audit = self.state / 'audits/test'
        audit.mkdir(parents=True)
        tx = installer.InstallTransaction(self.root, audit)
        runtime = self.state / 'runtime'
        runtime.mkdir()
        (runtime / 'old.txt').write_text('old')
        tx.replace(runtime)
        runtime.mkdir()
        (runtime / 'new.txt').write_text('new')
        with patch.object(tx, 'remove', side_effect=PermissionError('locked')):
            with self.assertRaisesRegex(RuntimeError, '자동 복구'):
                tx.rollback()
        self.assertEqual((Path(tx.entries[0]['backup']) / 'old.txt').read_text(), 'old')
        self.assertEqual(self.journal()['status'], 'recovery-required')
        with self.assertRaisesRegex(RuntimeError, '이전 설치의 복구'):
            installer.main()

    def test_paths_outside_root_are_rejected_without_changes(self):
        audit = self.state / 'audits/test'
        audit.mkdir(parents=True)
        tx = installer.InstallTransaction(self.root, audit)
        outside = Path(self.temp.name) / 'user.txt'
        outside.write_text('keep')
        with self.assertRaisesRegex(RuntimeError, 'outside ComfyUI'):
            tx.replace(outside)
        with self.assertRaisesRegex(RuntimeError, 'outside ComfyUI'):
            tx.replace(self.root / 'user/../../user.txt')
        self.assertEqual(outside.read_text(), 'keep')

    def test_real_child_process_failure_removes_its_runtime(self):
        installer.main()
        (self.abc / 'install_sheetsage2.py').write_text(
            'import pathlib,sys\n'
            'if "--check-only" in sys.argv: sys.exit(1)\n'
            'root=pathlib.Path(sys.argv[sys.argv.index("--comfyui")+1])\n'
            'runtime=root/"user/abc-studio/runtime"\n'
            'runtime.mkdir(parents=True,exist_ok=True)\n'
            '(runtime/"child-created.txt").write_text("partial pip installation")\n'
            'sys.exit(7)\n')
        audit = self.state / 'audits/child-test'
        audit.mkdir()
        tx = installer.InstallTransaction(self.root, audit)
        with patch.object(installer, 'run', REAL_RUN):
            with self.assertRaises(subprocess.CalledProcessError) as caught:
                installer._setup_sheetsage(self.abc, self.root, self.root / 'models', transaction=tx)
        self.assertEqual(caught.exception.returncode, 7)
        self.assertTrue((self.abc_state / 'runtime/child-created.txt').exists())
        tx.rollback()
        self.assertTrue((self.abc_state / 'runtime/new-torch.txt').exists())

    def test_commit_journal_failure_rolls_back(self):
        save = installer.InstallTransaction.save
        def failing_save(transaction, status):
            if status == 'committed':
                raise OSError('cannot save commit')
            return save(transaction, status)
        with patch.object(installer.InstallTransaction, 'save', failing_save):
            with self.assertRaisesRegex(OSError, 'cannot save commit'):
                installer.main()
        self.assertFalse(self.node.exists())
        self.assertEqual(self.journal()['status'], 'rolled-back')

    def test_successful_check_does_not_ignore_a_new_model_directory(self):
        self.upgrade_fixture()
        (self.abc_state / 'setup.json').write_text(json.dumps({'model': str(self.root / 'old-models/abc_studio/SheetSage2')}))
        with patch.object(installer, 'run') as run:
            installer.main()
        self.assertEqual(run.call_count, 2)
        self.assertNotIn('--check-only', run.call_args.args[0])

    def test_failed_abc_promotion_restores_original_in_transaction(self):
        self.upgrade_fixture()
        rename = Path.rename
        def fail_promotion(path, target):
            if path.name == 'studio' and Path(target) == self.abc:
                raise PermissionError('promotion locked')
            return rename(path, target)
        with patch.object(Path, 'rename', fail_promotion):
            with self.assertRaisesRegex(PermissionError, 'promotion locked'):
                installer.main()
        self.assertEqual((self.abc / 'abc_studio_node/abc_studio.py').read_text(), '# old ABC\n')
        self.assertEqual(self.journal()['status'], 'rolled-back')

    def test_sheetsage_ignores_pip_target_and_uses_local_cache(self):
        with patch.dict(installer.os.environ, {'PIP_TARGET': 'outside-site', 'PIP_PREFIX': 'outside-prefix'}), \
             patch.object(installer, 'run') as run:
            installer._setup_sheetsage(self.abc, self.root, self.root / 'models')
        env = run.call_args.kwargs['env']
        self.assertNotIn('PIP_TARGET', env)
        self.assertNotIn('PIP_PREFIX', env)
        self.assertEqual(env['PIP_CONFIG_FILE'], installer.os.devnull)
        self.assertEqual(Path(env['PIP_CACHE_DIR']), self.state / 'pip-cache')

    @unittest.skipUnless(installer.sys.platform == 'win32', 'Windows file lock')
    def test_real_locked_file_keeps_recovery_backup(self):
        audit = self.state / 'audits/locked-test'
        audit.mkdir(parents=True)
        tx = installer.InstallTransaction(self.root, audit)
        target = self.state / 'runtime'
        target.mkdir()
        (target / 'old.txt').write_text('original')
        tx.replace(target)
        target.mkdir()
        locked = target / 'locked.txt'
        locked.write_text('new')
        with locked.open('rb'):
            with self.assertRaisesRegex(RuntimeError, '자동 복구'):
                tx.rollback()
        self.assertTrue((Path(tx.entries[0]['backup']) / 'old.txt').exists())

    def test_keyboard_interrupt_also_rolls_back(self):
        with patch.object(installer, '_install_model_weights', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                installer.main()
        self.assertFalse(self.node.exists())
        self.assertFalse(self.abc.exists())
        self.assertFalse((self.state / 'runtime').exists())


if __name__ == '__main__':
    unittest.main()

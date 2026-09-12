import json
import hashlib
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from test_yue2_installer import installer


class ABCUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.here = self.root / 'installer'
        self.here.mkdir()
        self.state = self.root / 'user/2bz-yue2'
        self.state.mkdir(parents=True)
        self.dest = self.root / 'custom_nodes/toobusy-abc-studio'
        self.dest.parent.mkdir()
        self.old = {'abc_studio_node/test.py': '# old\n'}
        self.new = {'abc_studio_node/test.py': '# new\n', 'js/microphone.js': '// roles\n'}
        fingerprints = lambda files: {k: hashlib.sha256(v.encode()).hexdigest() for k,v in files.items()}
        (self.here / 'abc-studio-versions.json').write_text(json.dumps({
            'v0.2.0': fingerprints(self.old), installer.ABC_STUDIO_REF: fingerprints(self.new)}))
        self.archive = self.state / f'toobusy-abc-studio-{installer.ABC_STUDIO_REF}.zip'
        with zipfile.ZipFile(self.archive, 'w') as archive:
            for name, value in self.new.items():
                archive.writestr('studio/' + name, value)
        self.manifest = {'abc_studio': {'sha256': installer.digest(self.archive)}}
        self.patcher = patch.object(installer, 'HERE', self.here)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def write_old(self):
        for name, value in self.old.items():
            p = self.dest / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(value)

    def test_clean_install_and_reinstall(self):
        installer._install_abc(self.dest, self.state, self.manifest)
        self.assertEqual(installer._abc_status(self.dest), 'current')
        with patch.object(installer, 'download_file', side_effect=AssertionError('download')):
            installer._install_abc(self.dest, self.state, self.manifest)

    def test_official_upgrade_backs_up_outside_custom_nodes(self):
        self.write_old()
        installer._install_abc(self.dest, self.state, self.manifest)
        self.assertEqual(installer._abc_status(self.dest), 'current')
        backups = list((self.state / 'backups').iterdir())
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / 'abc_studio_node/test.py').read_text(), '# old\n')
        self.assertEqual(len(list(self.dest.parent.iterdir())), 1)

    def test_failed_swap_restores_old_version(self):
        self.write_old()
        rename = Path.rename
        def fail_staged(path, target):
            if path.name == 'studio':
                raise OSError('locked')
            return rename(path, target)
        with patch.object(Path, 'rename', fail_staged):
            with self.assertRaisesRegex(OSError, 'locked'):
                installer._install_abc(self.dest, self.state, self.manifest)
        self.assertEqual(installer._abc_status(self.dest), 'upgrade')

    def test_modified_and_git_old_installations_are_not_overwritten(self):
        self.write_old()
        (self.dest / 'user.abc').write_text('my score')
        with self.assertRaisesRegex(RuntimeError, 'customized'):
            installer._install_abc(self.dest, self.state, self.manifest)
        (self.dest / 'user.abc').unlink()
        (self.dest / '.git').mkdir()
        with self.assertRaisesRegex(RuntimeError, 'customized'):
            installer._install_abc(self.dest, self.state, self.manifest)

    def test_damaged_archive_leaves_old_code_in_place(self):
        self.write_old()
        with patch.object(installer, 'download_file', side_effect=RuntimeError('bad archive')):
            with self.assertRaisesRegex(RuntimeError, 'bad archive'):
                installer._install_abc(self.dest, self.state, self.manifest)
        self.assertEqual(installer._abc_status(self.dest), 'upgrade')

    def test_audio_plan_rejects_replacement_protected_packages_and_sources(self):
        def report(name, url='https://files.pythonhosted.org/package.whl'):
            return {'install':[{'metadata':{'name':name,'version':'1.0'},'download_info':{'url':url}}]}
        for name, before, url in [('torch',{},'x.whl'), ('numpy',{'numpy':{}},'x.whl'), ('librosa',{},'x.tar.gz')]:
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                installer._audio_plan_packages(report(name,url),before)
        self.assertEqual(installer._audio_plan_packages(report('lazy_loader'),{}), ['lazy-loader==1.0'])

    def test_preservation_allows_only_planned_additions(self):
        before = {'torch':{'version':'2.12'}, 'numpy':{'version':'2.2'}}
        after = {**before, 'librosa':{'version':'0.11'}}
        with patch.object(installer, 'package_state', return_value=after):
            installer.report_preservation(before,self.state,{'librosa'})
            with self.assertRaises(RuntimeError):
                installer.report_preservation(before,self.state)
        after['numpy'] = {'version':'2.1'}
        with patch.object(installer, 'package_state', return_value=after):
            with self.assertRaises(RuntimeError):
                installer.report_preservation(before,self.state,{'librosa','numpy'})

    def test_resolver_constrains_all_existing_versions_and_install_has_no_resolver(self):
        before = {'torch':{'version':'2.12.1+cu130'}, 'numpy':{'version':'2.2.6'}}
        calls=[]
        def run(args, **kwargs):
            args=list(map(str,args)); calls.append(args)
            if '--report' in args:
                Path(args[args.index('--report')+1]).write_text(json.dumps({'install':[{
                    'metadata':{'name':'librosa','version':'0.11.0'},
                    'download_info':{'url':'https://files.pythonhosted.org/librosa.whl'}}]}))
        allowed=set()
        with patch.object(installer,'package_state',return_value=before), patch.object(installer,'run',side_effect=run):
            installer._prepare_abc_audio(self.state,self.state,allowed)
        self.assertEqual(allowed,{'librosa'})
        self.assertIn('torch==2.12.1+cu130', (self.state/'audio-constraints.txt').read_text())
        installs=[c for c in calls if 'install' in c and '--dry-run' not in c]
        self.assertEqual(len(installs),1)
        for flag in ['--no-deps','--no-index','--only-binary=:all:']:
            self.assertIn(flag,installs[0])


if __name__ == '__main__':
    unittest.main()

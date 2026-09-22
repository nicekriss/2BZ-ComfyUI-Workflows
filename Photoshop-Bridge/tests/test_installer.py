import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'installer'))
from setup_core import Engine,SetupError,Cancelled,inside,existing_model,server_url,resolve_root,read_json

class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name);self.data=self.base/'data';self.data.mkdir()
        (self.data/'dependencies.json').write_text('{"models":[],"nodes":[]}',encoding='utf-8')
        (self.data/'comfy_node').mkdir()
        for name in ['__init__.py','pixels.py']:(self.data/'comfy_node'/name).write_text('# fixture',encoding='utf-8')
        self.root=self.base/'client Comfy';self.root.mkdir();(self.root/'main.py').touch();(self.root/'custom_nodes').mkdir()
        self.e=Engine(self.data,self.base/'state',lambda _:None)
    def tearDown(self):self.temp.cleanup()
    def test_path_boundary_and_endpoint(self):
        for path in ['../user-data','C:/Windows','/absolute','a/../../b']:
            with self.assertRaises(SetupError):inside(self.root,path)
        for url in ['http://example.com:8188','http://127.0.0.1:99999','http://localhost:0']:
            with self.assertRaises(SetupError):server_url(url)
        self.assertEqual(resolve_root(self.root),self.root)
    def test_pairing_survives_reinstall_and_other_nodes_untouched(self):
        other=self.root/'custom_nodes/other';other.mkdir();(other/'work.txt').write_text('preserve')
        token=self.e.bridge(self.root);self.assertEqual(len(token),64);self.assertEqual(token,self.e.bridge(self.root))
        self.assertEqual((other/'work.txt').read_text(),'preserve')
        installed=self.root/'custom_nodes/toobusy_photoshop_bridge/__init__.py';installed.write_text('user edit')
        with self.assertRaises(SetupError):self.e.bridge(self.root)
        self.assertEqual(installed.read_text(),'user edit')
    def test_reuse_and_ambiguous_external_models(self):
        a=self.base/'shared/a';b=self.base/'shared/b';a.mkdir(parents=True);b.mkdir()
        (a/'model.safetensors').write_bytes(b'a');model={'path':'checkpoints/model.safetensors'}
        self.assertEqual(existing_model(self.root,model,{'checkpoints':[a]}),a/'model.safetensors')
        (b/'model.safetensors').write_bytes(b'b')
        with self.assertRaises(SetupError):existing_model(self.root,model,{'checkpoints':[a,b]})
    def test_resume_checks_range_and_hash(self):
        data=b'abcdef';target=self.base/'model';target.with_name('model.part').write_bytes(data[:3])
        class Response:
            status_code=206;headers={'Content-Range':'bytes 3-5/6'}
            def __enter__(self):return self
            def __exit__(self,*_):pass
            def raise_for_status(self):pass
            def iter_content(self,*_):yield data[3:]
        item={'url':'https://example.test/model','size':6,'sha256':hashlib.sha256(data).hexdigest()}
        with patch('setup_core.requests.get',return_value=Response()) as request:self.e.download(item,target)
        self.assertEqual(request.call_args.kwargs['headers']['Range'],'bytes=3-');self.assertEqual(target.read_bytes(),data)
        target.write_bytes(b'own model')
        with self.assertRaises(SetupError):self.e.download(item,target)
        self.assertEqual(target.read_bytes(),b'own model')
    def test_wrong_hash_never_promoted(self):
        class Response:
            status_code=200;headers={}
            def __enter__(self):return self
            def __exit__(self,*_):pass
            def raise_for_status(self):pass
            def iter_content(self,*_):yield b'bad'
        target=self.base/'bad-model'
        with patch('setup_core.requests.get',return_value=Response()):
            with self.assertRaises(SetupError):self.e.download({'url':'https://example.test','size':3,'sha256':'0'*64},target)
        self.assertFalse(target.exists())
    def test_cancel_prevents_new_download(self):
        self.e.cancel=lambda:True
        with self.assertRaises(Cancelled):self.e.download({},self.base/'no-file')
        self.assertFalse((self.base/'no-file').exists())
    def test_fresh_install_and_rerun_with_existing_comfy_fixture(self):
        (self.root/'.venv/Scripts').mkdir(parents=True);(self.root/'.venv/Scripts/python.exe').touch()
        template=Path(__file__).resolve().parents[1]/'plugin/pro-template.json'
        (self.data/'pro-template.json').write_bytes(template.read_bytes())
        with patch('setup_core.active_processes',return_value=[]),patch('setup_core.run',return_value=''):
            output=self.e.install(self.root,'http://127.0.0.1:8188')
            connection=read_json(output)
            self.assertEqual(connection['modelPaths']['7'],'test_controlnet2/CN-anytest4_illustrious2_B_fp16.safetensors')
            self.e.install(self.root,'http://127.0.0.1:8188')
            self.assertEqual(read_json(output)['token'],connection['token'])
        with patch('setup_core.active_processes',return_value=[{'pid':123}]):
            with self.assertRaisesRegex(SetupError,'종료'):self.e.install(self.root,'http://127.0.0.1:8188')

if __name__=='__main__':unittest.main()

import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'installer'))
from setup_core import Engine,SetupError,Cancelled,inside,existing_model,server_url,resolve_root,read_json

class DownloadResponse:
    def __init__(self,status=200,headers=None,data=b'abcdef'):
        self.status_code=status;self.headers=headers or {};self.data=data;self.closed=False
    def close(self):self.closed=True
    def __enter__(self):return self
    def __exit__(self,*_):self.close()
    def iter_content(self,*_):yield self.data

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
    def test_civitai_prompt_retries_partial_and_reuses_key_without_persisting(self):
        from unittest.mock import Mock
        target=self.base/'authenticated-model';target.with_name(target.name+'.part').write_bytes(b'abc')
        item={'url':'https://civitai.com/api/download/models/1?fileId=2','size':6,'sha256':hashlib.sha256(b'abcdef').hexdigest()}
        self.e.request_token=Mock(return_value='fixture-private-key')
        replies=[DownloadResponse(401),DownloadResponse(206,{'Content-Range':'bytes 3-5/6'},b'def'),DownloadResponse()]
        with patch('setup_core.requests.get',side_effect=replies) as request:
            self.e.download(item,target)
            self.e.download(item,self.base/'next-model')
        self.assertEqual(target.read_bytes(),b'abcdef');self.e.request_token.assert_called_once_with(False)
        calls=request.call_args_list
        self.assertNotIn('Authorization',calls[0].kwargs['headers'])
        self.assertEqual(calls[1].kwargs['headers']['Range'],'bytes=3-')
        for call in calls[1:]:self.assertEqual(call.kwargs['headers']['Authorization'],'Bearer fixture-private-key')
        for p in self.e.state.rglob('*'):
            if p.is_file():self.assertNotIn(b'fixture-private-key',p.read_bytes())
    def test_civitai_key_is_not_forwarded_to_cdn_or_other_providers(self):
        self.e.civitai_token='fixture-private-key'
        for origin in ['https://civitai.com/api/download/models/1','https://huggingface.co/model','https://civitai.com.evil.test/api/download','https://civitai.com:443/api/download']:
            with patch('setup_core.requests.get',side_effect=[DownloadResponse(302,{'Location':'https://cdn.example.test/file?signature=signed'}),DownloadResponse()]) as request:
                response=self.e.download_response(origin,{'Range':'bytes=3-'});response.close()
            first,second=request.call_args_list
            self.assertEqual('Authorization' in first.kwargs['headers'],origin=='https://civitai.com/api/download/models/1')
            self.assertNotIn('Authorization',second.kwargs['headers']);self.assertEqual(second.kwargs['headers']['Range'],'bytes=3-')
            self.assertFalse(first.kwargs['allow_redirects'])
    def test_invalid_civitai_key_can_be_replaced_and_auth_cancel_keeps_partial(self):
        from unittest.mock import Mock
        self.e.civitai_token='wrong-key';self.e.request_token=Mock(side_effect=['second-key',None])
        partial=self.base/'model.part';partial.write_bytes(b'abc')
        item={'url':'https://civitai.com/api/download/models/1','size':6,'sha256':hashlib.sha256(b'abcdef').hexdigest()}
        with patch('setup_core.requests.get',side_effect=[DownloadResponse(403),DownloadResponse(401)]) as request:
            with self.assertRaises(Cancelled):self.e.download(item,self.base/'model')
        self.assertEqual([c.args for c in self.e.request_token.call_args_list],[(True,),(True,)])
        self.assertEqual(request.call_args.kwargs['headers']['Authorization'],'Bearer second-key')
        self.assertEqual(partial.read_bytes(),b'abc');self.assertFalse((self.base/'model').exists())
    def test_cdn_denial_does_not_ask_for_civitai_key_and_errors_hide_signed_urls(self):
        from unittest.mock import Mock
        import requests
        self.e.request_token=Mock();self.e.civitai_token='fixture-private-key'
        with patch('setup_core.requests.get',side_effect=[DownloadResponse(302,{'Location':'https://cdn.example.test/file?secret=private-signature'}),DownloadResponse(403)]):
            with self.assertRaises(SetupError) as error:self.e.download_response('https://civitai.com/api/download/models/1',{})
        self.e.request_token.assert_not_called();self.assertNotIn('private-signature',str(error.exception))
        with patch('setup_core.requests.get',side_effect=requests.ConnectionError('sensitive URL fixture-private-key')):
            with self.assertRaises(SetupError) as error:self.e.download_response('https://civitai.com/api/download/models/1',{})
        self.assertNotIn('fixture-private-key',str(error.exception))
    def test_download_rejects_insecure_redirect_before_sending_key(self):
        self.e.civitai_token='fixture-private-key'
        with patch('setup_core.requests.get',return_value=DownloadResponse(302,{'Location':'http://civitai.com/api/download/models/1'})) as request:
            with self.assertRaises(SetupError):self.e.download_response('https://civitai.com/api/download/models/1',{})
        request.assert_called_once()
    def test_civitai_token_validation_rejects_header_injection(self):
        from setup_core import api_token
        self.assertEqual(api_token('  sample-key  '),'sample-key')
        for value in ['key\r\nX-Header: secret','key with space','한글','x'*4097]:
            with self.assertRaises(SetupError):api_token(value)
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

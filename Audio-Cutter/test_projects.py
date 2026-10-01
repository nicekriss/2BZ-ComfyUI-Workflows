import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from recovery import RecoveryStore
import subprocess
import zipfile
import app
import projects

class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.audio = self.root / 'source.wav'
        app.run_media([app.FFMPEG, '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=2.5', str(self.audio)])
        self.source = {'path': self.audio, 'name': 'test.wav', 'duration': 2.5}
        self.image = self.root / 'ref.png'
        app.run_media([app.FFMPEG, '-v', 'error', '-f', 'lavfi', '-i', 'color=c=yellow:s=32x32', '-frames:v', '1', str(self.image)])
        self.asset = app.register_asset(self.image.read_bytes(), '레퍼런스.png')['id']
        self.scene = {'prompt': '천천히 걸으며 카메라를 본다.\n카메라는 뒤로 이동.', 'references': [self.asset], 'keyframeStart': self.asset, 'keyframeEnd': None}
        self.value = {'version': 1, 'project': '검증', 'mode': 'split', 'points': [0, 1, 2.5], 'names': ['도입', '후렴'], 'scenes': [copy.deepcopy(self.scene), projects.scene({}, {})], 'clips': [{'name': '바구니', 'start': .2, 'end': .9, 'scene': copy.deepcopy(self.scene)}]}
    def tearDown(self):
        self.tmp.cleanup()
    def test_portable_round_trip_and_boundaries(self):
        self.value['points'][1] = .8
        value = projects.state(self.value, 2.5, app.ASSETS)
        archive = self.root / 'test.2bz'
        projects.write_project(archive, self.source, value, app.ASSETS)
        manifest, audio, images = projects.read_project(archive)
        self.assertEqual(audio, self.audio.read_bytes())
        self.assertEqual(images[self.asset]['data'], self.image.read_bytes())
        self.assertEqual(manifest['state'], value)
        self.assertEqual(value['scenes'][0]['prompt'], self.scene['prompt'])
        self.assertEqual(value['points'][1], .8)
    def test_export_media_and_prompt(self):
        original = app.OUTPUT_ROOT
        app.OUTPUT_ROOT = self.root / 'exports'
        try:
            result = app.export_clips(self.source, [{'name': '../도입', 'start': 0, 'end': 1, 'scene': self.scene}, {'name': '후렴', 'start': 1, 'end': 2.5}], '검증', open_folder=False, state=self.value)
            folder = Path(result['folder'])
            first = folder / result['files'][0]['folder']
            self.assertEqual((first / '프롬프트.txt').read_text(encoding='utf-8-sig'), self.scene['prompt'])
            self.assertEqual((first / '업로드/reference_01.png').read_bytes(), self.image.read_bytes())
            self.assertEqual((first / '업로드/keyframe_start.png').read_bytes(), self.image.read_bytes())
            self.assertTrue((folder / '검증.2bz').exists())
            for item in result['files']:
                target = folder / item['file']
                self.assertTrue(target.resolve().is_relative_to(folder.resolve()))
                # Decoded PCM duration, excluding MP3 encoder padding.
                pcm = self.root / (item['folder'] + '.wav')
                app.run_media([app.FFMPEG, '-v', 'error', '-i', str(target), str(pcm)])
                self.assertAlmostEqual(app.inspect_audio(pcm), item['duration'], places=3)
        finally:
            app.OUTPUT_ROOT = original
    def test_audio_only_export_keeps_scene_data_out(self):
        original = app.OUTPUT_ROOT
        app.OUTPUT_ROOT = self.root / 'audio_exports'
        before = copy.deepcopy(self.value)
        try:
            result = app.export_clips(self.source, [
                {'name': '도입', 'start': 0, 'end': 1, 'scene': self.scene},
                {'name': '후렴', 'start': 1, 'end': 2.5, 'scene': self.scene}
            ], '음악', open_folder=False, state=self.value, audio_only=True)
            folder = Path(result['folder'])
            self.assertEqual(sorted(p.name for p in folder.iterdir()), sorted(x['file'] for x in result['files']))
            self.assertEqual(len(result['files']), 2)
            for index, item in enumerate(result['files']):
                target = folder / item['file']
                self.assertEqual(target.suffix, '.mp3')
                self.assertEqual(target.parent, folder)
                pcm = self.root / f'audio_only_{index}.wav'
                app.run_media([app.FFMPEG, '-v', 'error', '-i', str(target), str(pcm)])
                self.assertAlmostEqual(app.inspect_audio(pcm), item['duration'], places=3)
            self.assertEqual(self.value, before)
        finally:
            app.OUTPUT_ROOT = original

    def test_unsafe_archive_and_missing_asset_rejected(self):
        archive = self.root / 'bad.2bz'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('project.json', json.dumps({'assets': {}}))
            z.writestr('audio', b'x')
            z.writestr('../escape', b'x')
        with self.assertRaises(ValueError): projects.read_project(archive)
        with self.assertRaises(ValueError): projects.scene(self.scene, {})
        with self.assertRaises(ValueError): projects.image_kind(b'<svg/>')
        bad = copy.deepcopy(self.value); bad['points'] = [0, 2, 1]
        with self.assertRaises(ValueError): projects.state(bad, 2.5, app.ASSETS)


class StudioTests(ProjectTests):
    def make_video(self):
        video = self.root / 'red_then_blue.mp4'
        app.run_media([app.FFMPEG, '-v', 'error', '-f', 'lavfi', '-i', 'color=red:s=64x64:d=3:r=10',
                       '-f', 'lavfi', '-i', 'color=blue:s=64x64:d=1:r=10',
                       '-filter_complex', '[0:v][1:v]concat=n=2:v=1:a=0[v]', '-map', '[v]', '-c:v', 'libx264', str(video)])
        return app.register_video(video, '빨강_파랑.mp4')['id']

    def test_last_frame_and_result_portability(self):
        video_id = self.make_video()
        result = app.final_frame(video_id)
        pixels = subprocess.check_output([app.FFMPEG, '-v', 'error', '-i', str(app.ASSETS[result['id']]['path']), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], creationflags=app.NO_WINDOW)
        red, green, blue = pixels[:3]
        self.assertGreater(blue, 200)
        self.assertLess(red, 20)
        self.value['scenes'][0].update({'resultVideo': video_id, 'status': 'done'})
        self.value['scenes'][1]['keyframeStart'] = result['id']
        self.value['library'] = [{'id': self.asset, 'label': '세라', 'category': '캐릭터'}, {'id': result['id'], 'label': '마지막', 'category': '배경'}]
        value = projects.state(self.value, 2.5, app.ASSETS)
        archive = self.root / 'movie.2bz'
        projects.write_project(archive, self.source, value, app.ASSETS)
        info, audio, media = projects.read_project(archive)
        self.assertEqual(media[video_id]['data'], app.ASSETS[video_id]['path'].read_bytes())
        self.assertEqual(info['state']['library'][0]['label'], '세라')
        self.assertEqual(info['state']['scenes'][0]['status'], 'done')
        restored = app.restore_project(info, self.audio, media)
        self.assertEqual(restored['state'], value)
        original = app.OUTPUT_ROOT
        app.OUTPUT_ROOT = self.root / 'studio-export'
        try:
            result = app.export_clips(self.source, [{'name': '완료', 'start': 0, 'end': 1, 'scene': value['scenes'][0]}], '영상', open_folder=False, state=value)
            folder = Path(result['folder']) / result['files'][0]['folder']
            self.assertEqual((folder / '결과영상.mp4').read_bytes(), media[video_id]['data'])
            self.assertFalse(any(x.suffix == '.mp4' for x in (folder / '업로드').iterdir()))
        finally:
            app.OUTPUT_ROOT = original

    def test_recovery_survives_restart_and_interrupted_commit(self):
        store = RecoveryStore(self.root / 'recovery')
        key = 'a' * 32
        value = projects.state(self.value, 2.5, app.ASSETS)
        store.save(key, self.source, value, app.ASSETS)
        updated = copy.deepcopy(value); updated['scenes'][0]['prompt'] = '새 내용'
        with patch('recovery.os.replace', side_effect=OSError('test interruption')):
            with self.assertRaises(OSError): store.save(key, self.source, updated, app.ASSETS)
        reopened = RecoveryStore(self.root / 'recovery')
        info, audio, media = reopened.load(key)
        self.assertEqual(info['state'], value)
        self.assertEqual(audio.read_bytes(), self.audio.read_bytes())
        self.assertEqual(media[self.asset]['path'].read_bytes(), self.image.read_bytes())
        store.save(key, self.source, updated, app.ASSETS)
        self.assertEqual(reopened.load(key)[0]['state'], updated)
        self.assertEqual(len(reopened.list()), 1)
        with self.assertRaises(ValueError): reopened.load('../outside')

    def test_unused_library_asset_and_legacy_archive(self):
        self.value['scenes'] = [projects.scene({}, {}), projects.scene({}, {})]
        self.value['clips'] = []
        self.value['library'] = [{'id': self.asset, 'label': '공통 배경', 'category': '배경'}]
        value = projects.state(self.value, 2.5, app.ASSETS)
        archive = self.root / 'library.2bz'
        projects.write_project(archive, self.source, value, app.ASSETS)
        self.assertIn(self.asset, projects.read_project(archive)[2])
        legacy = self.root / 'legacy.2bz'
        with zipfile.ZipFile(legacy, 'w') as z:
            z.writestr('project.json', json.dumps({'state': self.value, 'audioName': 'source.wav', 'assets': {self.asset: 'old.png'}}))
            z.write(self.audio, 'audio'); z.write(self.image, 'assets/' + self.asset)
        info, audio, media = projects.read_project(legacy)
        self.assertEqual(media[self.asset]['kind'], 'image')
        self.assertEqual(app.restore_project(info, self.audio, media)['state']['version'], 2)

if __name__ == '__main__': unittest.main()

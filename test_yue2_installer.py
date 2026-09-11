import importlib.util
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

BASE = Path(__file__).parent / "YuE2"
spec = importlib.util.spec_from_file_location("installer", BASE / "install_yue2.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class Response(io.BytesIO):
    status = 200
    headers = {}


class InstallerTests(unittest.TestCase):
    def test_verified_file_never_downloaded(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "model"
            p.write_bytes(b"verified")
            with patch.object(installer.urllib.request, "urlopen", side_effect=AssertionError("network")):
                installer.download("https://example.invalid", p, hashlib.sha256(b"verified").hexdigest())

    def test_mismatched_existing_file_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "model"
            p.write_bytes(b"user data")
            with self.assertRaisesRegex(RuntimeError, "Existing file differs"):
                installer.download("https://example.invalid", p, "wrong")
            self.assertEqual(p.read_bytes(), b"user data")

    def test_bad_download_never_promoted(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "model"
            with patch.object(installer.urllib.request, "urlopen", return_value=Response(b"bad")):
                with self.assertRaisesRegex(RuntimeError, "checksum"):
                    installer.download("https://example.invalid", p, "wrong")
            self.assertFalse(p.exists())

    def test_server_ignoring_range_restarts_download(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "model"
            p.with_name("model.part").write_bytes(b"old")
            with patch.object(installer.urllib.request, "urlopen", return_value=Response(b"complete")):
                installer.download("https://example.invalid", p, hashlib.sha256(b"complete").hexdigest())
            self.assertEqual(p.read_bytes(), b"complete")

    def test_resume(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "model"
            p.with_name("model.part").write_bytes(b"abc")
            response = Response(b"def")
            response.status = 206
            response.headers = {"Content-Range": "bytes 3-5/6"}
            with patch.object(installer.urllib.request, "urlopen", return_value=response):
                installer.download("https://example.invalid", p, hashlib.sha256(b"abcdef").hexdigest(), 6)
            self.assertEqual(p.read_bytes(), b"abcdef")

    def test_existing_pack_stops_before_install(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "main.py").touch()
            node = root / "custom_nodes" / "ComfyUI-YuE2"
            node.mkdir(parents=True)
            with patch("sys.argv", ["install", "--root", str(root)]), patch.object(installer, "environment", return_value="site"), patch.object(installer, "run", side_effect=AssertionError("mutation")):
                with self.assertRaisesRegex(RuntimeError, "Existing node pack preserved"):
                    installer.main()

    def test_workflow_is_portable_and_links_resolve(self):
        text = (BASE / "YuE2_Music.json").read_text(encoding="utf-8")
        self.assertNotIn("C:/mini", text)
        self.assertNotIn("D:/SM", text)
        workflow = json.loads(text)
        nodes = {n["id"]: n for n in workflow["nodes"]}
        self.assertNotIn("LoadAudio", [n["type"] for n in nodes.values()])
        for link in workflow["links"]:
            self.assertIn(link[1], nodes)
            self.assertIn(link[3], nodes)


if __name__ == "__main__":
    unittest.main()

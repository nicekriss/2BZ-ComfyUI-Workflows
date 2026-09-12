import importlib.util
import hashlib
import io
import json
import zipfile
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

BASE = Path(__file__).parent / "YuE2"
spec = importlib.util.spec_from_file_location("installer", BASE / "install_yue2.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class Response(io.BytesIO):
    status = 200
    headers = {}


class InstallerTests(unittest.TestCase):
    def test_newer_torch_warns_and_continues(self):
        torch = SimpleNamespace(__version__="2.12.1+cu130", __file__="site/torch/__init__.py",
            cuda=SimpleNamespace(is_available=lambda: True, is_bf16_supported=lambda: True,
                                 get_device_name=lambda: "Test GPU"))
        with patch.dict("sys.modules", {"torch": torch}), patch.object(installer.sys, "platform", "win32"), \
                patch.object(installer.sys, "version_info", (3, 13)), patch("sys.stdout", new_callable=io.StringIO) as out:
            installer.environment()
        self.assertIn("Continuing without modifying", out.getvalue())

    def test_non_cuda_still_rejected(self):
        torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False))
        with patch.dict("sys.modules", {"torch": torch}), patch.object(installer.sys, "platform", "win32"), \
                patch.object(installer.sys, "version_info", (3, 13)):
            with self.assertRaisesRegex(RuntimeError, "CUDA is unavailable"):
                installer.environment()

    def test_protected_packages_and_direct_urls_never_reach_pip(self):
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "state"
            dist = SimpleNamespace(locate_file=lambda _: Path(temp) / "comfy-site")
            with patch.object(installer.metadata, "distribution", return_value=dist), patch.object(installer, "run") as run:
                for package in ["torch==2.10.0", "torchvision", "torchaudio", "xformers", "triton",
                                "triton_windows", "nvidia-cublas-cu13", "cuda-bindings", "torch-cuda",
                                "example @ https://example.invalid/package.whl", "yue2-infer[fast]"]:
                    with self.subTest(package=package), self.assertRaisesRegex(RuntimeError, "Refusing"):
                        installer.install_wheels(state / "site", [package], state)
                run.assert_not_called()

    def test_dependency_install_disables_resolver_and_builds(self):
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "state"
            dist = SimpleNamespace(locate_file=lambda _: Path(temp) / "comfy-site")
            with patch.object(installer.metadata, "distribution", return_value=dist), patch.object(installer, "run") as run:
                installer.install_wheels(state / "site", ["tiktoken==0.12.0"], state)
                args = run.call_args.args[0]
                self.assertIn("--no-deps", args)
                self.assertIn("--only-binary=:all:", args)
                self.assertNotIn("--upgrade", args)
                self.assertEqual(args[args.index("--target") + 1], (state / "site").resolve())

    def test_pip_target_cannot_escape_into_comfy(self):
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "state"
            with patch.object(installer, "run") as run:
                with self.assertRaisesRegex(RuntimeError, "outside YuE2"):
                    installer.install_wheels(state / ".." / "comfy-site", ["numpy"], state)
                run.assert_not_called()

    def test_environment_change_is_reported_and_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            before = {"torch": {"version": "2.12.1+cu130"}}
            with patch.object(installer, "package_state", return_value={"torch": {"version": "2.10.0"}}):
                with self.assertRaisesRegex(RuntimeError, "ComfyUI packages changed: torch"):
                    installer.report_preservation(before, Path(temp))
            result = json.loads((Path(temp) / "environment-comparison.json").read_text())
            self.assertEqual(result["changed"], ["torch"])

    def test_existing_compatible_dependencies_not_installed(self):
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp)
            runtime = state / "runtime"
            (runtime / "Scripts").mkdir(parents=True)
            (runtime / "Scripts" / "python.exe").touch()
            (runtime / "Lib" / "site-packages").mkdir(parents=True)
            with patch.object(installer, "ADDITIONAL", {"numpy>=1.26,<3": "numpy==2.2.6", "tiktoken==0.12.0": "tiktoken==0.12.0"}), \
                    patch.object(installer, "package_state", return_value={"numpy": {"version": "2.4.4"}}), \
                    patch.object(installer, "install_wheels") as install:
                installer.prepare_runtime(state, "comfy-site")
                self.assertEqual(install.call_args.args[1], ["tiktoken==0.12.0"])

    def test_audit_runs_when_installation_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "main.py").touch()
            (root / "custom_nodes").mkdir()
            with patch("sys.argv", ["install", "--root", str(root)]), \
                    patch.object(installer, "environment", return_value="site"), \
                    patch.object(installer, "prepare_runtime", side_effect=RuntimeError("install failed")), \
                    patch.object(installer, "report_preservation") as audit:
                with self.assertRaisesRegex(RuntimeError, "install failed"):
                    installer.main()
                audit.assert_called_once()

    def test_clean_install_uses_src_package_and_bundled_bridge(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "main.py").touch()
            (root / "custom_nodes").mkdir()
            state = root / "user" / "2bz-yue2"
            site = state / "runtime" / "Lib" / "site-packages"
            site.mkdir(parents=True)
            with zipfile.ZipFile(state / "yue2-source.zip", "w") as archive:
                archive.writestr("YuE-pinned/src/yue2/__init__.py", "# model source")
            with zipfile.ZipFile(state / "toobusy-abc-studio.zip", "w") as archive:
                archive.writestr("studio/abc_studio_node/abc_studio.py", "# ABC node")
            with patch("sys.argv", ["install", "--root", str(root)]), \
                    patch.object(installer, "environment", return_value="shared"), \
                    patch.object(installer, "prepare_runtime", return_value=(state / "runtime/Scripts/python.exe", site)), \
                    patch.object(installer, "download_file"), patch.object(installer, "smoke_runtime"), \
                    patch.object(installer, "_install_model_weights"):
                installer.main()
            self.assertTrue((site / "yue2/__init__.py").is_file())
            node = root / "custom_nodes/ComfyUI-YuE2"
            self.assertEqual((node / "nodes.py").read_bytes(), (BASE / "custom_nodes/ComfyUI-YuE2/nodes.py").read_bytes())
            self.assertTrue((node / "setup.json").is_file())

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

    def test_installer_keeps_existing_node_packs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "main.py").touch()
            node = root / "custom_nodes" / "ComfyUI-YuE2"
            node.mkdir(parents=True)
            (node / "setup.json").write_text(json.dumps({
                "runtime": str(root / "runtime" / "bin" / "python.exe"),
                "model": str(root / "models" / "audio_encoders" / "YuE2-3B"),
                "vae": str(root / "models" / "vae" / "YuE2-Vae"),
            }, ensure_ascii=False), encoding="utf-8")
            abc = root / "custom_nodes" / "toobusy-abc-studio"
            abc.mkdir(parents=True)
            (abc / "abc_studio_node").mkdir(parents=True)
            (abc / "abc_studio_node" / "abc_studio.py").write_text(
                "\"\"\"marker\"\"\"\nclass YuE2LocalGenerateWithABCUnavailable: pass\n"
                "class YuE2LocalGenerateWithABC: pass\n\"YuE2LocalGenerateWithABC\"\n"
                "\"2BZ YuE2 Generate + ABC\"",
                encoding="utf-8",
            )
            with patch("sys.argv", ["install", "--root", str(root)]), \
                    patch.object(installer, "environment", return_value="site"), \
                    patch.object(installer, "run", return_value=None), \
                    patch.object(installer, "_install_model_weights", return_value=None), \
                    patch.object(installer, "download_file", return_value=None):
                installer.main()

    def test_stale_abc_studio_reinstalled_safely(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "main.py").touch()
            node = root / "custom_nodes" / "ComfyUI-YuE2"
            node.mkdir(parents=True)
            (node / "setup.json").write_text(json.dumps({
                "runtime": str(root / "runtime" / "bin" / "python.exe"),
                "model": str(root / "models" / "audio_encoders" / "YuE2-3B"),
                "vae": str(root / "models" / "vae" / "YuE2-Vae"),
            }, ensure_ascii=False), encoding="utf-8")

            abc = root / "custom_nodes" / "toobusy-abc-studio"
            abc.mkdir(parents=True)
            (abc / "abc_studio_node").mkdir(parents=True)
            (abc / "abc_studio_node" / "abc_studio.py").write_text("class LegacyOnly: pass", encoding="utf-8")

            state = root / "user" / "2bz-yue2"
            state.mkdir(parents=True)
            zip_path = state / "toobusy-abc-studio.zip"
            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(
                    "toobusy-abc-studio-main/abc_studio_node/abc_studio.py",
                    "class YuE2LocalGenerateWithABC: pass",
                )

            with patch("sys.argv", ["install", "--root", str(root)]), \
                    patch.object(installer, "environment", return_value="site"), \
                    patch.object(installer, "run", return_value=None), \
                    patch.object(installer, "_install_model_weights", return_value=None), \
                    patch.object(installer, "download_file", side_effect=lambda *_a, **_k: None):
                installer.main()

            self.assertTrue((root / "custom_nodes" / "toobusy-abc-studio.old").exists())
            self.assertTrue((root / "custom_nodes" / "toobusy-abc-studio").is_dir())

    def test_missing_pack_detected_in_check_mode(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "main.py").touch()
            (root / "custom_nodes").mkdir()
            yue2 = root / "custom_nodes" / "ComfyUI-YuE2"
            yue2.mkdir(parents=True)
            with patch("sys.argv", ["install", "--root", str(root), "--check-only"]), \
                    patch.object(installer, "environment", return_value="site"):
                with self.assertRaisesRegex(RuntimeError, "Missing toobusy-abc-studio"):
                    installer.main()

    def test_stale_toobusy_pack_detected_in_check_mode(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "main.py").touch()
            yue2 = root / "custom_nodes" / "ComfyUI-YuE2"
            yue2.mkdir(parents=True)
            (yue2 / "setup.json").write_text(json.dumps({
                "runtime": str(root / "runtime" / "bin" / "python.exe"),
                "model": str(root / "models" / "audio_encoders" / "YuE2-3B"),
                "vae": str(root / "models" / "vae" / "YuE2-Vae"),
            }, ensure_ascii=False), encoding="utf-8")
            abc = root / "custom_nodes" / "toobusy-abc-studio"
            abc.mkdir(parents=True)
            (abc / "abc_studio_node").mkdir(parents=True)
            (abc / "abc_studio_node" / "abc_studio.py").write_text("class LegacyOnly: pass", encoding="utf-8")
            with patch("sys.argv", ["install", "--root", str(root), "--check-only"]), \
                    patch.object(installer, "environment", return_value="site"):
                with self.assertRaisesRegex(RuntimeError, "missing required node class"):
                    installer.main()

    def test_release_package_includes_the_installed_bridge(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "builder", Path(__file__).parent / "build_yue2_release.py")
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        names = {name for _, name in builder.members()}
        self.assertIn("YuE2/install_yue2.py", names)
        self.assertIn("YuE2/YuE2_Music.json", names)
        self.assertIn("YuE2/custom_nodes/ComfyUI-YuE2/nodes.py", names)
        self.assertIn("YuE2/smoke_yue2.py", names)
        self.assertFalse([n for n in names if "__pycache__" in n])
        self.assertEqual(builder.check(), len(names))

    def test_source_archive_is_verified_before_use(self):
        # 이름만 같고 내용이 다른 zip 이 남아 있으면 버리고 다시 받아야 한다.
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "source.zip"
            p.write_bytes(b"half written wreckage")
            good = b"real archive"
            digest = hashlib.sha256(good).hexdigest()
            with patch.object(installer.urllib.request, "urlopen", return_value=Response(good)):
                installer.download_file("https://example.invalid", p, digest)
            self.assertEqual(p.read_bytes(), good)

    def test_matching_archive_skips_the_network(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "source.zip"
            p.write_bytes(b"real archive")
            digest = hashlib.sha256(b"real archive").hexdigest()
            with patch.object(installer.urllib.request, "urlopen", side_effect=AssertionError("network")):
                installer.download_file("https://example.invalid", p, digest)

    def test_corrupt_download_is_deleted_and_raises(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "source.zip"
            with patch.object(installer.urllib.request, "urlopen", return_value=Response(b"tampered")):
                with self.assertRaisesRegex(RuntimeError, "pinned checksum"):
                    installer.download_file("https://example.invalid", p, "0" * 64)
            self.assertFalse(p.exists(), "검증에 실패한 파일을 남겨 두면 다음 실행이 그걸 믿는다")

    def test_abc_studio_is_pinned_to_a_release_not_a_moving_branch(self):
        self.assertIn("refs/tags/", installer.ABC_STUDIO_ZIP_URL)
        self.assertNotIn("refs/heads/", installer.ABC_STUDIO_ZIP_URL)
        manifest = json.loads((BASE / "downloads.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["abc_studio"]["ref"], installer.ABC_STUDIO_REF)
        self.assertEqual(len(manifest["abc_studio"]["sha256"]), 64)

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

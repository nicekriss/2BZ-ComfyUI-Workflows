"""Install YuE2 beside an existing Windows ComfyUI while preserving existing packages."""

import argparse
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent

# The Korean guidance has to survive a console that is not UTF-8. On an
# English Windows the console encodes cp1252, which has no Hangul, and a
# single Korean line raises UnicodeEncodeError and kills the install
# rather than printing the advice it was trying to give. The launcher
# passes -X utf8, but nothing guarantees the launcher is what ran us.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError, ValueError):
        pass
SOURCE_COMMIT = "92a73cc7652fcc1f937855e4b765e0a0edd7ff2e"
SOURCE_ZIP_URL = f"https://codeload.github.com/multimodal-art-projection/YuE/zip/{SOURCE_COMMIT}"
ABC_STUDIO_REF = "v0.4.5"
ABC_STUDIO_ZIP_URL = f"https://codeload.github.com/nicekriss/toobusy-abc-studio/zip/refs/tags/{ABC_STUDIO_REF}"
VERSION = "0.1.0-rc14"
PROTECTED = {"torch", "torchvision", "torchaudio", "xformers", "triton", "triton-windows"}
AUDITED = sorted(PROTECTED | {"transformers", "numpy"})
# Reuse compatible shared packages. Conflicts are overlaid ONLY in the subprocess.
# Missing dependencies are installed with no resolver or source builds.
ADDITIONAL = {
    "transformers==4.57.6": "transformers==4.57.6",
    "huggingface-hub==0.36.2": "huggingface-hub==0.36.2",
    "safetensors>=0.7": "safetensors==0.7.0",
    "tiktoken>=0.12,<0.13": "tiktoken==0.12.0",
    "numpy>=1.26,<3": "numpy==2.2.6",
    "soundfile>=0.13,<0.14": "soundfile==0.13.1",
    "accelerate>=1.13,<2": "accelerate==1.13.0",
    "tokenizers>=0.22,<=0.23": "tokenizers==0.22.2",
    "filelock": "filelock==3.20.3", "packaging>=20": "packaging==26.0",
    "pyyaml>=5.1": "pyyaml==6.0.3", "regex": "regex==2026.1.15",
    "requests>=2.26": "requests==2.32.5", "tqdm>=4.42.1": "tqdm==4.67.3",
    "fsspec>=2023.5": "fsspec==2025.12.0", "typing-extensions>=3.7.4.3": "typing-extensions==4.15.0",
    "psutil": "psutil==7.2.2", "cffi>=1.0": "cffi==2.0.0",
    "pycparser": "pycparser==3.0", "charset-normalizer>=2,<4": "charset-normalizer==3.4.4",
    "idna>=2.5,<4": "idna==3.11", "urllib3>=1.21.1,<3": "urllib3==2.6.3",
    "certifi>=2017.4.17": "certifi==2026.1.4", "colorama": "colorama==0.4.6",
}
OPTIONAL = ("vllm", "triton", "hf-xet", "pynvml")  # Never installed automatically.


class InstallTransaction:
    """Keep completed changes reversible until the final environment audit passes."""

    def __init__(self, root, audit):
        self.root = root.resolve()
        self.audit = audit
        self.entries = []
        self.journal = audit / "rollback.json"

    def check_path(self, path):
        path = Path(os.path.abspath(path))
        if path == self.root or not path.is_relative_to(self.root):
            raise RuntimeError(f"Refusing installation path outside ComfyUI: {path}")
        for parent in (path, *path.parents):
            if parent == self.root:
                break
            if parent.is_symlink() or (parent.exists() and getattr(parent.lstat(), "st_file_attributes", 0) & 0x400):
                raise RuntimeError(f"Refusing linked installation path: {parent}")
        return path

    def save(self, status):
        temporary = self.journal.with_suffix(".tmp")
        temporary.write_text(json.dumps({"status": status, "entries": self.entries}, indent=2), encoding="utf-8")
        temporary.replace(self.journal)

    def remember(self, path, backup=None, discard_backup=False):
        path = self.check_path(path)
        if backup is not None:
            backup = self.check_path(backup)
        self.entries.append({"path": str(path), "backup": str(backup) if backup else None,
                             "discard_backup": discard_backup})
        self.save("pending")

    def replace(self, path):
        path = self.check_path(path)
        backup = None
        if path.exists():
            backup = self.audit / "recovery" / str(len(self.entries))
            self.check_path(backup)
            backup.parent.mkdir(parents=True, exist_ok=True)
            path.rename(backup)
        self.remember(path, backup, discard_backup=True)

    def remove(self, path):
        path = self.check_path(path)
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()

    def rollback(self):
        failures = []
        for entry in reversed(self.entries):
            path = Path(entry["path"])
            backup = Path(entry["backup"]) if entry["backup"] else None
            try:
                if backup is not None and not backup.exists():
                    raise RuntimeError(f"Recovery backup is missing: {backup}")
                self.remove(path)
                if backup is not None:
                    self.check_path(backup).rename(path)
                entry["restored"] = True
            except OSError as exc:
                failures.append(f"{path}: {exc}")
            except RuntimeError as exc:
                failures.append(str(exc))
        self.save("recovery-required" if failures else "rolled-back")
        if failures:
            raise RuntimeError("자동 복구를 완료하지 못했습니다. ComfyUI와 관련 창을 닫고 복구 기록을 확인하세요: "
                               + str(self.journal) + "\n" + "\n".join(failures))
        print("설치 실패: 이번 실행의 노드·런타임 변경을 되돌렸습니다. 모델 다운로드와 진단 기록은 유지합니다.", flush=True)

    def commit(self):
        self.save("committed")

    def cleanup_backups(self):
        for entry in self.entries:
            if entry["discard_backup"] and entry["backup"]:
                try:
                    self.remove(Path(entry["backup"]))
                except (OSError, RuntimeError) as exc:
                    print(f"설치는 완료됐지만 이전 런타임 백업을 지우지 못했습니다: {entry['backup']} ({exc})", flush=True)


def package_state():
    result = {}
    for dist in metadata.distributions():
        name = dist.metadata.get("Name", "").lower().replace("_", "-").replace(".", "-")
        if name:
            record = dist.read_text("RECORD") or ""
            result[name] = {"version": dist.version, "location": str(dist.locate_file("").resolve()),
                            "record_sha256": hashlib.sha256(record.encode()).hexdigest()}
    return result


def report_preservation(before, state, allowed_additions=()):
    after = package_state()
    changed = sorted(name for name in before.keys() | after.keys() if before.get(name) != after.get(name))
    (state / "environment-after.json").write_text(json.dumps(after, indent=2), encoding="utf-8")
    (state / "environment-comparison.json").write_text(json.dumps({"changed": changed}, indent=2), encoding="utf-8")
    for name in AUDITED:
        old = before.get(name, {}).get("version", "not installed")
        new = after.get(name, {}).get("version", "not installed")
        print(f"{name:14}: {old} -> {'unchanged' if name not in changed else new}", flush=True)
    unexpected = [name for name in changed if name in before or name not in allowed_additions]
    if unexpected:
        raise RuntimeError("WARNING: ComfyUI packages changed: " + ", ".join(unexpected)
                           + ". Stop and inspect the environment snapshots; no automatic Torch rollback is attempted.")
    print("Existing ComfyUI environment preserved. Approved audio additions: "
          + ", ".join(name for name in changed if name not in before), flush=True)


def protected(name):
    name = name.lower().replace("_", "-").replace(".", "-")
    return name in PROTECTED or name.startswith(("torch-", "nvidia-", "cuda-", "pytorch-"))


def install_wheels(target, packages, state):
    from pip._vendor.packaging.requirements import Requirement
    target = Path(target).resolve()
    if not target.is_relative_to(state.resolve()) or target == state.resolve():
        raise RuntimeError(f"Refusing pip target outside YuE2 state: {target}")
    shared = Path(metadata.distribution("torch").locate_file("")).resolve()
    if target == shared or target.is_relative_to(shared) or shared.is_relative_to(target):
        raise RuntimeError("Refusing pip target overlapping ComfyUI packages")
    for package in packages:
        req = Requirement(package)
        if protected(req.name) or req.url or req.extras:
            raise RuntimeError(f"Refusing protected or unapproved dependency: {package}")
    if packages:
        env = {k: v for k, v in os.environ.items() if not k.startswith("PIP_")}
        env.update(PIP_CONFIG_FILE=os.devnull, PYTHONNOUSERSITE="1")
        run([sys.executable, "-m", "pip", "--isolated", "install", "--no-deps", "--only-binary=:all:",
             "--disable-pip-version-check", "--cache-dir", state / "pip-cache", "--target", target, *packages], env=env)


def prepare_runtime(state, shared_site):
    from pip._vendor.packaging.requirements import Requirement
    runtime = state / "runtime"
    python = runtime / "Scripts" / "python.exe"
    if not python.exists():
        try:
            import venv
        except ImportError:
            bootstrap = state / "bootstrap"
            install_wheels(bootstrap, ["virtualenv==20.36.1", "distlib==0.4.0",
                                      "filelock==3.20.3", "platformdirs==4.5.1"], state)
            run([sys.executable, "-c", "import sys,runpy; sys.path.insert(0,sys.argv.pop(1)); runpy.run_module('virtualenv',run_name='__main__')",
                 bootstrap, "--no-download", "--no-seed", runtime])
        else:
            venv.EnvBuilder(with_pip=False).create(runtime)
    site = runtime / "Lib" / "site-packages"
    local = {d.metadata["Name"].lower().replace("_", "-").replace(".", "-"): d.version for d in metadata.distributions(path=[str(site)])}
    if any(protected(name) for name in local):
        raise RuntimeError("YuE2 runtime contains a private Torch/CUDA package; move the runtime aside and retry.")
    (site / "comfy_cuda.pth").write_text(shared_site + "\n", encoding="utf-8")
    shared = package_state()
    missing = []
    for requirement, wheel in ADDITIONAL.items():
        req = Requirement(requirement)
        name = req.name.lower().replace("_", "-").replace(".", "-")
        version = local.get(name) or shared.get(name, {}).get("version")
        if version and req.specifier.contains(version):
            print(f"REUSE: {name} {version}", flush=True)
        elif name in local:
            raise RuntimeError(f"Incompatible YuE2-only package {name} {version}; move {runtime} aside and retry.")
        else:
            missing.append(wheel)
    install_wheels(site, missing, state)
    return python, site


def smoke_runtime(python, shared_site, config=None):
    command = [python, "-I", "-X", "utf8", HERE / "smoke_yue2.py", "--shared-site", shared_site]
    if config:
        command.extend(["--model", config["model"], "--vae", config["vae"]])
    run(command)


def run(args, **kwargs):
    subprocess.run([str(x) for x in args], check=True, **kwargs)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest() if hasattr(hashlib, "file_digest") else hash_stream(stream)


def hash_stream(stream):
    result = hashlib.sha256()
    for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
        result.update(block)
    return result.hexdigest()


def download(url, target, sha256, size=None):
    if target.is_file():
        if digest(target) == sha256:
            print(f"VERIFIED: {target}", flush=True)
            return
        raise RuntimeError(f"Existing file differs; move it aside and retry: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_name(target.name + ".part")
    offset = part.stat().st_size if part.exists() else 0
    if offset and digest(part) == sha256:
        part.replace(target)
        return
    request = urllib.request.Request(url, headers={"Range": f"bytes={offset}-"} if offset else {})
    with urllib.request.urlopen(request, timeout=120) as response:
        resume = offset > 0 and response.status == 206
        if resume and not response.headers.get("Content-Range", "").startswith(f"bytes {offset}-"):
            raise RuntimeError("Unexpected download resume offset")
        received = offset if resume else 0
        mark = received // (100 * 1024 * 1024)
        with part.open("ab" if resume else "wb") as output:
            while block := response.read(4 * 1024 * 1024):
                output.write(block)
                received += len(block)
                if received // (100 * 1024 * 1024) > mark:
                    mark = received // (100 * 1024 * 1024)
                    print(f"{target.name}: {received / 1e9:.2f} GB" + (f" / {size / 1e9:.2f} GB" if size else ""), flush=True)
    if (size is not None and part.stat().st_size != size) or digest(part) != sha256:
        part.unlink()
        raise RuntimeError(f"Download checksum failed; damaged partial file removed. Retry: {target}")
    part.replace(target)


def download_file(url, target, sha256):
    """Fetch a source archive and refuse to use it unless the hash matches.

    A half-written archive from an interrupted run has the right name and the
    wrong bytes. Trusting the name alone installs that wreckage silently, so
    every call checks the digest, both for a file already on disk and for one
    just downloaded.
    """
    if target.is_file():
        if digest(target) == sha256:
            print(f"VERIFIED: {target}", flush=True)
            return
        print(f"Discarding damaged archive and fetching again: {target}", flush=True)
        target.unlink()
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading: {target.name}", flush=True)
    with urllib.request.urlopen(url, timeout=120) as response, target.open("wb") as output:
        while block := response.read(4 * 1024 * 1024):
            output.write(block)
    actual = digest(target)
    if actual != sha256:
        target.unlink()
        raise RuntimeError(
            "Download does not match the pinned checksum and was deleted: " + url
            + " | expected " + sha256 + " | got " + actual
        )
    print(f"VERIFIED: {target}", flush=True)


def environment():
    # Importing Torch reads a multi-gigabyte install and can sit for a
    # minute or more on a cold cache, with nothing else printing. Say so
    # first, or the window looks frozen right after the folder pickers.
    print("ComfyUI의 Torch를 확인하는 중입니다. 처음 한 번은 1분 넘게 걸릴 수 있습니다.", flush=True)
    import torch
    if sys.platform != "win32" or not (3, 10) <= sys.version_info[:2] <= (3, 13):
        raise RuntimeError("This installer supports Windows Python 3.10-3.13.")
    if not torch.cuda.is_available():
        raise RuntimeError("Select ComfyUI's NVIDIA CUDA Python; CUDA is unavailable here.")
    if not torch.__version__.startswith("2.10."):
        print(f"Detected Torch: {torch.__version__}\nYuE2 was originally tested with Torch 2.10.x.\n"
              "Continuing without modifying the existing ComfyUI Torch installation.", flush=True)
    if not torch.cuda.is_bf16_supported():
        raise RuntimeError("YuE2 requires an NVIDIA GPU with BF16 support.")
    print(f"Python: {sys.executable}\nTorch: {torch.__version__}\nGPU: {torch.cuda.get_device_name()}", flush=True)
    return str(Path(torch.__file__).resolve().parent.parent)


def _find_root_with_child(parent, marker):
    candidates = [p for p in Path(parent).iterdir() if p.is_dir() and marker(p)]
    if not candidates:
        raise RuntimeError(f"Expected source root not found under {parent}.")
    if len(candidates) > 1:
        raise RuntimeError(f"Multiple source roots found under {parent}; expected one.")
    return candidates[0]


def _copy_node_package(source_root, destination, setup_payload=None):
    if destination.exists():
        print(f"SKIP: existing package kept: {destination}")
        return
    with tempfile.TemporaryDirectory(prefix=f".{destination.name}.installing-", dir=destination.parent) as temp:
        staging = Path(temp) / destination.name
        shutil.copytree(source_root, staging)
        if setup_payload is not None:
            (staging / "setup.json").write_text(json.dumps(setup_payload, indent=2), encoding="utf-8")
        staging.rename(destination)


def _update_bridge(destination, state, transaction=None):
    """Upgrade only a recognized installer bridge; preserve custom code and setup."""
    source = HERE / "custom_nodes" / "ComfyUI-YuE2"
    current = {p.name: _code_digest(p) for p in source.glob("*.py")}
    known = json.loads((HERE / "bridge-versions.json").read_text(encoding="utf-8"))
    actual = {p.name: _code_digest(p) for p in destination.glob("*.py")}
    if actual == current:
        print("YuE2 bridge is already current.", flush=True)
        return True
    if (destination / ".git").exists() or actual not in known.values():
        print("WARNING: YuE2 bridge update SKIPPED: unrecognized/customized code was preserved. "
              "Live progress may be unavailable. Back up your custom node before replacing it.", flush=True)
        return False
    if destination.is_symlink() or any(p.is_symlink() for p in destination.glob("*.py")):
        raise RuntimeError("Refusing to update a linked YuE2 bridge.")
    backups = state / "backups"
    backups.mkdir(parents=True, exist_ok=True)
    backup = backups / ("ComfyUI-YuE2-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ"))
    with tempfile.TemporaryDirectory(prefix="bridge-update-", dir=state) as temp:
        staged = Path(temp) / destination.name
        shutil.copytree(destination, staged, symlinks=True, ignore=shutil.ignore_patterns("__pycache__"))
        for name in current:
            shutil.copy2(source / name, staged / name)
        try:
            destination.rename(backup)
        except PermissionError as exc:
            raise _folder_in_use(destination, exc) from exc
        if transaction is not None:
            transaction.remember(destination, backup)
        try:
            staged.rename(destination)
        except BaseException:
            if transaction is None:
                backup.rename(destination)
            raise
    print(f"UPDATED: YuE2 bridge {VERSION}. Previous files: {backup}", flush=True)
    return True


def _code_digest(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _folder_in_use(path, exc):
    """Windows refuses to move a folder while any file or working directory inside it is open."""
    return RuntimeError(
        f"기존 폴더를 교체하지 못했습니다. 다른 프로그램이 이 폴더를 사용 중입니다: {path}\n"
        "기존 폴더는 바뀌지 않았습니다. ComfyUI를 종료하고, 이 폴더를 열어 둔 탐색기·명령 프롬프트·편집기도 "
        "닫은 뒤 Install-YuE2.bat을 다시 실행하세요.\n"
        f"원래 오류: {exc}")


def _running_comfyui(root):
    """Processes running this ComfyUI's main.py. Empty when psutil is unavailable."""
    try:
        import psutil
    except ImportError:
        return []
    target = os.path.normcase(os.path.realpath(root / "main.py"))
    found = []
    for proc in psutil.process_iter(["pid", "exe", "cmdline", "cwd"]):
        info = proc.info
        for arg in info.get("cmdline") or []:
            if not arg.lower().endswith("main.py") or not (os.path.isabs(arg) or info.get("cwd")):
                continue
            if os.path.normcase(os.path.realpath(os.path.join(info.get("cwd") or "", arg))) == target:
                found.append((info["pid"], info.get("exe") or ""))
                break
    return found


def _install_model_weights(model_root, manifest):
    for item in manifest["models"]:
        target = Path(model_root[item["kind"]]) / item["name"]
        download(item["url"], target, item["sha256"], item["bytes"])


def _verify_node_setup(config, manifest):
    for item in manifest["models"]:
        target = Path(config[item["kind"]]) / item["name"]
        if not target.is_file() or digest(target) != item["sha256"]:
            raise RuntimeError(f"Missing or damaged: {target}")


def _abc_studio_has_required_generate_node(abc_destination):
    if not abc_destination.is_dir():
        return False
    source_file = abc_destination / "abc_studio_node" / "abc_studio.py"
    if not source_file.is_file():
        return False
    try:
        text = source_file.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    return (
        "class YuE2LocalGenerateWithABC" in text
        and "YuE2LocalGenerateWithABCUnavailable" in text
        and '"YuE2LocalGenerateWithABC"' in text
        and "2BZ YuE2 Generate + ABC" in text
    )


def _abc_tree(directory):
    result = {}
    for current, dirs, files in os.walk(directory, followlinks=False):
        for name in dirs + files:
            path = Path(current) / name
            if path.is_symlink() or getattr(path.lstat(), "st_file_attributes", 0) & 0x400:
                raise RuntimeError(f"Linked ABC Studio files cannot be updated: {path}")
        dirs[:] = [name for name in dirs if name not in {".git", "__pycache__", ".pytest_cache"}]
        for name in files:
            if name.endswith((".pyc", ".pyo")):
                continue
            path = Path(current) / name
            result[path.relative_to(directory).as_posix()] = _code_digest(path)
    return result


def _abc_status(destination):
    if destination.is_symlink() or (destination.exists() and getattr(destination.lstat(), "st_file_attributes", 0) & 0x400):
        raise RuntimeError(f"Linked ABC Studio folder cannot be updated: {destination}")
    if not destination.exists():
        return "missing"
    known = json.loads((HERE / "abc-studio-versions.json").read_text(encoding="utf-8"))
    actual = _abc_tree(destination)
    if actual == known[ABC_STUDIO_REF]:
        return "current"
    if (destination / ".git").exists() or actual not in known.values():
        raise RuntimeError("ABC Studio contains customized, newer or unrecognized files; kept unchanged. "
                           "Back up this folder and update it separately before rerunning: " + str(destination))
    return "upgrade"


def _install_abc(destination, state, manifest, transaction=None):
    status = _abc_status(destination)
    if status == "current":
        print(f"ABC Studio {ABC_STUDIO_REF} is already current.", flush=True)
        return
    archive = state / f"toobusy-abc-studio-{ABC_STUDIO_REF}.zip"
    download_file(ABC_STUDIO_ZIP_URL, archive, manifest["abc_studio"]["sha256"])
    known = json.loads((HERE / "abc-studio-versions.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="abc-update-", dir=state) as temp:
        with zipfile.ZipFile(archive) as source:
            source.extractall(temp)
        staged = _find_root_with_child(Path(temp), lambda p: (p / "abc_studio_node").is_dir())
        if _abc_tree(staged) != known[ABC_STUDIO_REF]:
            raise RuntimeError("ABC Studio archive content differs from the pinned release.")
        # Recheck immediately before the swap; do not overwrite intervening user edits.
        if _abc_status(destination) != status:
            raise RuntimeError("ABC Studio changed during installation. Please retry.")
        backup = None
        if status == "upgrade":
            backups = state / "backups"
            backups.mkdir(parents=True, exist_ok=True)
            backup = backups / ("toobusy-abc-studio-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ"))
            try:
                destination.rename(backup)
            except PermissionError as exc:
                raise _folder_in_use(destination, exc) from exc
        if transaction is not None:
            transaction.remember(destination, backup)
        try:
            staged.rename(destination)
        except BaseException:
            if backup is not None and transaction is None:
                backup.rename(destination)
            raise
    print(f"ABC Studio {ABC_STUDIO_REF} installed. Previous version: {backup or 'none'}", flush=True)


def _audio_plan_packages(report, before):
    from pip._vendor.packaging.utils import canonicalize_name
    from pip._vendor.packaging.version import Version
    packages = []
    for item in report.get("install", []):
        name = canonicalize_name(item["metadata"]["name"])
        version = str(Version(item["metadata"]["version"]))
        if protected(name) or name in before:
            raise RuntimeError(f"Audio installation would change existing/protected package: {name}")
        if not item.get("download_info", {}).get("url", "").split("?", 1)[0].endswith(".whl"):
            raise RuntimeError(f"Audio dependency is not a binary wheel: {name}")
        packages.append(f"{name}=={version}")
    return packages


def _prepare_abc_audio(state, audit, allowed_additions):
    # ABC v0.3.0 runs its analysis worker with ComfyUI's Python. Add only absent
    # wheels there; every installed distribution is constrained to its current version.
    before = package_state()
    constraints = audit / "audio-constraints.txt"
    constraints.write_text("".join(f"{name}=={dist['version']}\n" for name, dist in sorted(before.items())), encoding="utf-8")
    report = audit / "audio-pip-plan.json"
    env = {k: v for k, v in os.environ.items() if not k.startswith("PIP_")}
    env.update(PIP_CONFIG_FILE=os.devnull, PYTHONNOUSERSITE="1")
    base = [sys.executable, "-m", "pip", "--isolated"]
    try:
        run([*base, "install", "--dry-run", "--report", report, "--only-binary=:all:",
             "--index-url", "https://pypi.org/simple", "--constraint", constraints,
             "librosa>=0.11,<0.12", "soundfile>=0.13,<0.14"], env=env)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("Audio dependencies cannot be added without changing existing ComfyUI packages. "
                           "No package upgrade was attempted; inspect audio-constraints.txt and the pip error.") from exc
    packages = _audio_plan_packages(json.loads(report.read_text(encoding="utf-8")), before)
    if packages:
        wheels = audit / "audio-wheels"
        wheels.mkdir()
        run([*base, "download", "--no-deps", "--only-binary=:all:", "--index-url", "https://pypi.org/simple",
             "--dest", wheels, *packages], env=env)
        if package_state() != before:
            raise RuntimeError("ComfyUI packages changed during preparation. Close other installers and retry.")
        allowed_additions.update(package.split("==", 1)[0] for package in packages)
        run([*base, "install", "--no-deps", "--no-index", "--only-binary=:all:",
             "--find-links", wheels, *packages], env=env)
    _smoke_abc_audio()


def _smoke_abc_audio():
    run([sys.executable, "-I", "-X", "utf8", HERE / "smoke_abc.py"])


def _setup_sheetsage(abc, root, models, check_only=False, transaction=None):
    command = [sys.executable, "-I", "-X", "utf8", abc / "install_sheetsage2.py",
               "--comfyui", root, "--models", models]
    if check_only:
        command.append("--check-only")
    elif transaction is not None:
        state = root / "user" / "abc-studio"
        for path in (state / "runtime", state / "setup.json", state / "setup.tmp", state / "python311"):
            transaction.check_path(path)
        if (state / "setup.json").is_file():
            try:
                run([*command, "--check-only"])
            except subprocess.CalledProcessError:
                print("SheetSage2 환경을 다시 준비합니다. 실패하면 기존 런타임을 복원합니다.", flush=True)
            else:
                config = json.loads((state / "setup.json").read_text(encoding="utf-8"))
                if Path(config["model"]).parent.resolve() == (models / "abc_studio").resolve():
                    print("SheetSage2 설치 검사를 통과해 기존 환경을 재사용합니다.", flush=True)
                    return
        transaction.replace(state / "runtime")
        transaction.replace(state / "setup.json")
        transaction.replace(state / "setup.tmp")
        if not (state / "python311").exists():
            transaction.remember(state / "python311")
    env = {key: value for key, value in os.environ.items() if not key.startswith("PIP_")}
    env.update(PIP_CONFIG_FILE=os.devnull, PYTHONNOUSERSITE="1", PIP_CACHE_DIR=str(root / "user/2bz-yue2/pip-cache"))
    run(command, env=env)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--models", type=Path)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    if not (root / "main.py").is_file() or not (root / "custom_nodes").is_dir():
        raise RuntimeError("Select the real ComfyUI folder containing main.py and custom_nodes.")

    manifest = json.loads((HERE / "downloads.json").read_text(encoding="utf-8"))
    yue2_destination = root / "custom_nodes" / "ComfyUI-YuE2"
    abc_destination = root / "custom_nodes" / "toobusy-abc-studio"
    models = (args.models or root / "models").resolve()

    if args.check_only:
        if not yue2_destination.is_dir():
            raise RuntimeError(f"Missing ComfyUI-YuE2: {yue2_destination}")
        if not abc_destination.is_dir():
            raise RuntimeError(f"Missing toobusy-abc-studio: {abc_destination}")
        if not _abc_studio_has_required_generate_node(abc_destination):
            raise RuntimeError(f"toobusy-abc-studio installed but missing required node class: {abc_destination}")
        if _abc_status(abc_destination) != "current":
            raise RuntimeError("ABC Studio needs an update. Run Install-YuE2.bat first.")
        _setup_sheetsage(abc_destination, root, models, check_only=True)
        config = json.loads((yue2_destination / "setup.json").read_text(encoding="utf-8"))
        _verify_node_setup(config, manifest)
        smoke_runtime(config["runtime"], environment(), config)
        workflow = root / "user" / "default" / "workflows" / "2BZ_YuE2_Music.json"
        if not workflow.is_file():
            raise RuntimeError(f"Missing workflow: {workflow}")
        print("SETUP VERIFIED. Restart ComfyUI, open YuE2_Music.json, and run a short song.")
        return

    print(f"YuE2 Installer {VERSION}", flush=True)
    running = _running_comfyui(root)
    if running:
        raise RuntimeError(
            "ComfyUI가 실행 중이라 설치를 시작하지 않았습니다. 아무것도 변경하지 않았습니다.\n"
            "ComfyUI(Desktop 앱 포함)를 완전히 종료한 뒤 Install-YuE2.bat을 다시 실행하세요.\n"
            + "\n".join(f"실행 중: PID {pid} {exe}" for pid, exe in running))
    shared_site = environment()
    state = root / "user" / "2bz-yue2"
    audit = state / "audits" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    transaction = InstallTransaction(root, audit)
    for path in (state, audit, state / "backups", yue2_destination, abc_destination,
                 root / "user" / "abc-studio", root / "user" / "default" / "workflows"):
        transaction.check_path(path)
    for journal in (state / "audits").glob("*/rollback.json"):
        if json.loads(journal.read_text(encoding="utf-8"))["status"] in {"pending", "recovery-required"}:
            raise RuntimeError(f"이전 설치의 복구가 완료되지 않았습니다. 백업을 보존했으니 복구 기록을 확인하세요: {journal}")
    audit.mkdir(parents=True)
    print("설치 전 패키지 목록을 기록하는 중입니다.", flush=True)
    before = package_state()
    (audit / "environment-before.json").write_text(json.dumps(before, indent=2), encoding="utf-8")
    allowed_additions = set()
    try:
        # Swap ABC Studio first: a folder held open fails in seconds, not after hashing 7.8GB of weights.
        _install_abc(abc_destination, state, manifest, transaction=transaction)
        if yue2_destination.exists():
            config = json.loads((yue2_destination / "setup.json").read_text(encoding="utf-8"))
            _update_bridge(yue2_destination, state, transaction=transaction)
        else:
            transaction.replace(state / "runtime")
            transaction.replace(state / "bootstrap")
            python, site = prepare_runtime(state, shared_site)
            source_archive = state / "yue2-source.zip"
            download_file(SOURCE_ZIP_URL, source_archive, manifest["source_sha256"])
            with tempfile.TemporaryDirectory(prefix="yue2-source-", dir=state) as temp:
                with zipfile.ZipFile(source_archive) as source:
                    source.extractall(temp)
                source_root = _find_root_with_child(Path(temp), lambda p: (p / "src" / "yue2").is_dir())
                # Install the pinned pure-Python package directly: no build backend or resolver.
                _copy_node_package(source_root / "src" / "yue2", site / "yue2")
                smoke_runtime(python, shared_site)
                source_node_root = HERE / "custom_nodes" / "ComfyUI-YuE2"
                config = {
                    "runtime": str(python),
                    "model": str(models / "audio_encoders" / "YuE2-3B"),
                    "vae": str(models / "vae" / "YuE2-Vae"),
                }
                transaction.remember(yue2_destination)
                _copy_node_package(source_node_root, yue2_destination, config)

        _install_model_weights(config, manifest)
        smoke_runtime(config["runtime"], shared_site, config)

        _setup_sheetsage(abc_destination, root, models, transaction=transaction)

        workflows = root / "user" / "default" / "workflows"
        workflows.mkdir(parents=True, exist_ok=True)
        workflow = workflows / "2BZ_YuE2_Music.json"
        if not workflow.exists():
            transaction.remember(workflow)
            shutil.copy2(HERE / "YuE2_Music.json", workflow)
    except BaseException:
        try:
            report_preservation(before, audit, allowed_additions)
        except Exception as exc:
            print(f"설치 후 패키지 검사도 실패했습니다: {exc}", flush=True)
        transaction.rollback()
        raise
    try:
        report_preservation(before, audit, allowed_additions)
        transaction.commit()
    except BaseException:
        transaction.rollback()
        raise
    transaction.cleanup_backups()
    print(f"INSTALLED\nWorkflow: {workflow}\nRestart ComfyUI, then open the workflow.", flush=True)


if __name__ == "__main__":
    os.environ.update(PYTHONUTF8="1", HF_HUB_DISABLE_TELEMETRY="1", PIP_DISABLE_PIP_VERSION_CHECK="1")
    main()

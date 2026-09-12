"""Install YuE2 beside an existing Windows ComfyUI without changing its packages."""

import argparse
import hashlib
import json
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

HERE = Path(__file__).resolve().parent
SOURCE_COMMIT = "92a73cc7652fcc1f937855e4b765e0a0edd7ff2e"
SOURCE_ZIP_URL = f"https://codeload.github.com/multimodal-art-projection/YuE/zip/{SOURCE_COMMIT}"
ABC_STUDIO_REF = "v0.2.0"
ABC_STUDIO_ZIP_URL = f"https://codeload.github.com/nicekriss/toobusy-abc-studio/zip/refs/tags/{ABC_STUDIO_REF}"
PACKAGES = ["transformers==4.57.6", "huggingface-hub==0.36.2", "safetensors==0.7.0",
            "tiktoken==0.12.0", "numpy==2.2.6", "soundfile==0.13.1", "accelerate==1.13.0", "tokenizers==0.22.2"]


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
        raise RuntimeError(f"Download checksum failed; delete this partial file and retry: {part}")
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
    import torch
    if sys.platform != "win32" or not (3, 10) <= sys.version_info[:2] <= (3, 13):
        raise RuntimeError("This installer supports Windows Python 3.10-3.13.")
    if not torch.cuda.is_available():
        raise RuntimeError("Select ComfyUI's NVIDIA CUDA Python; CUDA is unavailable here.")
    if not torch.__version__.startswith("2.10."):
        raise RuntimeError(f"This release is tested with Torch 2.10.x; found {torch.__version__}. No Torch packages were changed.")
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
    staging = destination.parent / f".{destination.name}.installing"
    if staging.exists():
        raise RuntimeError(f"Previous incomplete staging folder retained; move it aside: {staging}")
    shutil.copytree(source_root, staging)
    if setup_payload is not None:
        (staging / "setup.json").write_text(json.dumps(setup_payload, indent=2), encoding="utf-8")
    staging.rename(destination)


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


def _backup_existing_path(path):
    counter = 0
    while True:
        suffix = ".old" if counter == 0 else f".old.{counter}"
        backup = path.with_name(path.name + suffix)
        if not backup.exists():
            return path.replace(backup)
        counter += 1


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
        config = json.loads((yue2_destination / "setup.json").read_text(encoding="utf-8"))
        _verify_node_setup(config, manifest)
        run([config["runtime"], "-X", "utf8", "-c", "import torch, yue2, transformers, soundfile; assert torch.cuda.is_available(); print('RUNTIME READY')"])
        workflow = root / "user" / "default" / "workflows" / "2BZ_YuE2_Music.json"
        if not workflow.is_file():
            raise RuntimeError(f"Missing workflow: {workflow}")
        print("SETUP VERIFIED. Restart ComfyUI, open YuE2_Music.json, and run a short song.")
        return

    shared_site = environment()
    state = root / "user" / "2bz-yue2"
    state.mkdir(parents=True, exist_ok=True)

    if yue2_destination.exists():
        config = json.loads((yue2_destination / "setup.json").read_text(encoding="utf-8"))
        print(f"Existing ComfyUI-YuE2 detected and preserved: {yue2_destination}")
    else:
        runtime = state / "runtime"
        python = runtime / "Scripts" / "python.exe"
        if not python.exists():
            # virtualenv supports portable interpreters that do not ship the venv module.
            bootstrap = state / "bootstrap"
            run([sys.executable, "-m", "pip", "install", "--target", bootstrap, "virtualenv==20.36.1"])
            run([sys.executable, "-c", "import sys,runpy; sys.path.insert(0,sys.argv.pop(1)); runpy.run_module('virtualenv',run_name='__main__')", bootstrap, "--no-download", runtime])
        site = runtime / "Lib" / "site-packages"
        (site / "comfy_cuda.pth").write_text(shared_site + "\n", encoding="utf-8")
        # --target always writes only into the dedicated environment, never ComfyUI.
        run([python, "-m", "pip", "install", "--upgrade", "--target", site, "--no-deps", *PACKAGES])
        source_archive = state / "yue2-source.zip"
        download_file(SOURCE_ZIP_URL, source_archive, manifest["source_sha256"])
        with tempfile.TemporaryDirectory(prefix="yue2-source-", dir=state) as temp:
            with zipfile.ZipFile(source_archive) as source:
                source.extractall(temp)
            source_root = _find_root_with_child(Path(temp), lambda p: (p / "ComfyUI-YuE2").is_dir())
            source_node_root = source_root / "ComfyUI-YuE2"
            run([python, "-m", "pip", "install", "--no-deps", "--upgrade", "--target", site, source_root])
            config = {
                "runtime": str(python),
                "model": str(models / "audio_encoders" / "YuE2-3B"),
                "vae": str(models / "vae" / "YuE2-Vae"),
            }
            _copy_node_package(source_node_root, yue2_destination, config)

    _install_model_weights(config, manifest)

    if abc_destination.exists() and _abc_studio_has_required_generate_node(abc_destination):
        print(f"Existing toobusy-abc-studio detected and preserved: {abc_destination}")
    else:
        stale = abc_destination.exists()
        backup = None
        if stale:
            print(f"Existing toobusy-abc-studio detected but required node class is missing or outdated: {abc_destination}")
            backup = _backup_existing_path(abc_destination)
            print(f"Old toobusy-abc-studio moved to: {backup}")
        abc_archive = state / "toobusy-abc-studio.zip"
        download_file(ABC_STUDIO_ZIP_URL, abc_archive, manifest["abc_studio"]["sha256"])
        try:
            with tempfile.TemporaryDirectory(prefix="toobusy-abc-studio-", dir=state) as temp:
                with zipfile.ZipFile(abc_archive) as source:
                    source.extractall(temp)
                package_root = _find_root_with_child(Path(temp), lambda p: (p / "abc_studio_node").is_dir())
                _copy_node_package(package_root, abc_destination)
        except Exception:
            if backup is not None and backup.is_dir():
                if abc_destination.exists():
                    shutil.rmtree(abc_destination)
                backup.rename(abc_destination)
                print(f"Restored previous toobusy-abc-studio package: {abc_destination}")
            raise

    workflows = root / "user" / "default" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    workflow = workflows / "2BZ_YuE2_Music.json"
    if not workflow.exists():
        shutil.copy2(HERE / "YuE2_Music.json", workflow)
    print(f"INSTALLED\nWorkflow: {workflow}\nRestart ComfyUI, then open the workflow.", flush=True)


if __name__ == "__main__":
    os.environ.update(PYTHONUTF8="1", HF_HUB_DISABLE_TELEMETRY="1", PIP_DISABLE_PIP_VERSION_CHECK="1")
    main()

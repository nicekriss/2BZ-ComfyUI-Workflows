"""Install YuE2 beside an existing Windows ComfyUI without changing its packages."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

HERE = Path(__file__).resolve().parent
SOURCE_COMMIT = "92a73cc7652fcc1f937855e4b765e0a0edd7ff2e"
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--models", type=Path)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    if not (root / "main.py").is_file() or not (root / "custom_nodes").is_dir():
        raise RuntimeError("Select the real ComfyUI folder containing main.py and custom_nodes.")
    shared_site = environment()
    destination = root / "custom_nodes" / "ComfyUI-YuE2"
    manifest = json.loads((HERE / "downloads.json").read_text(encoding="utf-8"))
    if args.check_only:
        config = json.loads((destination / "setup.json").read_text(encoding="utf-8"))
        for item in manifest["models"]:
            target = Path(config[item["kind"]]) / item["name"]
            if not target.is_file() or digest(target) != item["sha256"]:
                raise RuntimeError(f"Missing or damaged: {target}")
        run([config["runtime"], "-X", "utf8", "-c", "import torch, yue2, transformers, soundfile; assert torch.cuda.is_available(); print('RUNTIME READY')"])
        print("SETUP VERIFIED. Restart ComfyUI, open YuE2_Music.json, and run a short song.")
        return
    if destination.exists():
        raise RuntimeError(f"Existing node pack preserved. Move it outside custom_nodes before installing: {destination}")
    models = (args.models or root / "models").resolve()
    state = root / "user" / "2bz-yue2"
    state.mkdir(parents=True, exist_ok=True)
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
    archive = state / "yue2-source.zip"
    download(f"https://codeload.github.com/multimodal-art-projection/YuE/zip/{SOURCE_COMMIT}", archive, manifest["source_sha256"])
    with tempfile.TemporaryDirectory(prefix="yue2-source-", dir=state) as temp:
        with zipfile.ZipFile(archive) as source:
            source.extractall(temp)
        run([python, "-m", "pip", "install", "--no-deps", "--upgrade", "--target", site, Path(temp) / f"YuE-{SOURCE_COMMIT}"])
    run([python, "-X", "utf8", "-c", "import torch, yue2, transformers, soundfile; assert torch.cuda.is_available(); print('RUNTIME READY')"])
    paths = {"model": models / "audio_encoders" / "YuE2-3B", "vae": models / "vae" / "YuE2-Vae"}
    for item in manifest["models"]:
        download(item["url"], paths[item["kind"]] / item["name"], item["sha256"], item["bytes"])
    config = {"runtime": str(python), **{k: str(v) for k, v in paths.items()}}
    staging = state / "node-staging"
    if staging.exists():
        raise RuntimeError(f"Previous incomplete staging folder retained; move it aside: {staging}")
    shutil.copytree(HERE / "custom_nodes" / "ComfyUI-YuE2", staging)
    (staging / "setup.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    staging.rename(destination)
    workflows = root / "user" / "default" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    workflow = workflows / "2BZ_YuE2_Music.json"
    if not workflow.exists():
        shutil.copy2(HERE / "YuE2_Music.json", workflow)
    print(f"INSTALLED\nWorkflow: {workflow}\nRestart ComfyUI, then open the workflow.", flush=True)


if __name__ == "__main__":
    os.environ.update(PYTHONUTF8="1", HF_HUB_DISABLE_TELEMETRY="1", PIP_DISABLE_PIP_VERSION_CHECK="1")
    main()

"""Install YuE2 beside an existing Windows ComfyUI without changing its packages."""

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
SOURCE_COMMIT = "92a73cc7652fcc1f937855e4b765e0a0edd7ff2e"
SOURCE_ZIP_URL = f"https://codeload.github.com/multimodal-art-projection/YuE/zip/{SOURCE_COMMIT}"
ABC_STUDIO_REF = "v0.2.0"
ABC_STUDIO_ZIP_URL = f"https://codeload.github.com/nicekriss/toobusy-abc-studio/zip/refs/tags/{ABC_STUDIO_REF}"
VERSION = "0.1.0-rc5"
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


def package_state():
    result = {}
    for dist in metadata.distributions():
        name = dist.metadata.get("Name", "").lower().replace("_", "-")
        if name:
            record = dist.read_text("RECORD") or ""
            result[name] = {"version": dist.version, "location": str(dist.locate_file("").resolve()),
                            "record_sha256": hashlib.sha256(record.encode()).hexdigest()}
    return result


def report_preservation(before, state):
    after = package_state()
    changed = sorted(name for name in before.keys() | after.keys() if before.get(name) != after.get(name))
    (state / "environment-after.json").write_text(json.dumps(after, indent=2), encoding="utf-8")
    (state / "environment-comparison.json").write_text(json.dumps({"changed": changed}, indent=2), encoding="utf-8")
    for name in AUDITED:
        old = before.get(name, {}).get("version", "not installed")
        new = after.get(name, {}).get("version", "not installed")
        print(f"{name:14}: {old} -> {'unchanged' if name not in changed else new}", flush=True)
    if changed:
        raise RuntimeError("WARNING: ComfyUI packages changed: " + ", ".join(changed)
                           + ". Stop and inspect the environment snapshots; no automatic Torch rollback is attempted.")
    print("Existing ComfyUI environment preserved.", flush=True)


def protected(name):
    name = name.lower().replace("_", "-")
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
             "--disable-pip-version-check", "--target", target, *packages], env=env)


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
    local = {d.metadata["Name"].lower().replace("_", "-"): d.version for d in metadata.distributions(path=[str(site)])}
    if any(protected(name) for name in local):
        raise RuntimeError("YuE2 runtime contains a private Torch/CUDA package; move the runtime aside and retry.")
    (site / "comfy_cuda.pth").write_text(shared_site + "\n", encoding="utf-8")
    shared = package_state()
    missing = []
    for requirement, wheel in ADDITIONAL.items():
        req = Requirement(requirement)
        name = req.name.lower().replace("_", "-")
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
    staging = destination.parent / f".{destination.name}.installing"
    if staging.exists():
        raise RuntimeError(f"Previous incomplete staging folder retained; move it aside: {staging}")
    shutil.copytree(source_root, staging)
    if setup_payload is not None:
        (staging / "setup.json").write_text(json.dumps(setup_payload, indent=2), encoding="utf-8")
    staging.rename(destination)


def _update_bridge(destination, state):
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
        destination.rename(backup)
        try:
            staged.rename(destination)
        except BaseException:
            backup.rename(destination)
            raise
    print(f"UPDATED: YuE2 bridge {VERSION}. Previous files: {backup}", flush=True)
    return True


def _code_digest(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


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
        smoke_runtime(config["runtime"], environment(), config)
        workflow = root / "user" / "default" / "workflows" / "2BZ_YuE2_Music.json"
        if not workflow.is_file():
            raise RuntimeError(f"Missing workflow: {workflow}")
        print("SETUP VERIFIED. Restart ComfyUI, open YuE2_Music.json, and run a short song.")
        return

    print(f"YuE2 Installer {VERSION}", flush=True)
    shared_site = environment()
    state = root / "user" / "2bz-yue2"
    state.mkdir(parents=True, exist_ok=True)

    audit = state / "audits" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    audit.mkdir(parents=True)
    before = package_state()
    (audit / "environment-before.json").write_text(json.dumps(before, indent=2), encoding="utf-8")
    try:
        if yue2_destination.exists():
            config = json.loads((yue2_destination / "setup.json").read_text(encoding="utf-8"))
            _update_bridge(yue2_destination, state)
        else:
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
                _copy_node_package(source_node_root, yue2_destination, config)

        _install_model_weights(config, manifest)
        smoke_runtime(config["runtime"], shared_site, config)

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
    finally:
        report_preservation(before, audit)


if __name__ == "__main__":
    os.environ.update(PYTHONUTF8="1", HF_HUB_DISABLE_TELEMETRY="1", PIP_DISABLE_PIP_VERSION_CHECK="1")
    main()

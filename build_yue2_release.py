"""Build the YuE2 installer ZIP that users download from the release page.

The installer ships the local subprocess bridge and downloads pinned YuE2 model code.

The archive is written with fixed timestamps and sorted names, so the same
inputs always produce the same bytes and the checksum means something.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

BASE = Path(__file__).resolve().parent
PACKAGE = BASE / "YuE2"
SKIP_DIRS = {"__pycache__"}
REQUIRED = [
    "Install-YuE2.bat",
    "Install-YuE2.ps1",
    "Check-YuE2.bat",
    "install_yue2.py",
    "downloads.json",
    "smoke_yue2.py",
    "bridge-versions.json",
    "custom_nodes/ComfyUI-YuE2/live_progress.py",
    "custom_nodes/ComfyUI-YuE2/nodes.py",
    "custom_nodes/ComfyUI-YuE2/worker.py",
    "custom_nodes/ComfyUI-YuE2/__init__.py",
    "YuE2_Music.json",
    "START-HERE-ko.md",
]


def members():
    yield BASE / "LICENSE", "LICENSE"
    for path in sorted(PACKAGE.rglob("*")):
        if not path.is_file():
            continue
        if SKIP_DIRS & set(path.relative_to(PACKAGE).parts):
            continue
        yield path, "YuE2/" + path.relative_to(PACKAGE).as_posix()


def check():
    """Refuse to ship a package the installer cannot actually use."""
    names = {name for _, name in members()}
    for required in REQUIRED:
        if "YuE2/" + required not in names:
            raise RuntimeError("Missing from package: " + required)

    manifest = json.loads((PACKAGE / "downloads.json").read_text(encoding="utf-8"))
    studio = manifest.get("abc_studio") or {}
    if len(studio.get("sha256", "")) != 64 or not studio.get("ref"):
        raise RuntimeError("downloads.json must pin toobusy-abc-studio to a ref with a sha256.")
    if len(manifest.get("source_sha256", "")) != 64:
        raise RuntimeError("downloads.json must pin the upstream YuE2 source checksum.")

    installer = (PACKAGE / "install_yue2.py").read_text(encoding="utf-8")
    if "refs/heads/" in installer:
        raise RuntimeError("Installer must pin releases, not track a moving branch.")

    workflow = (PACKAGE / "YuE2_Music.json").read_text(encoding="utf-8")
    if "YuE2LocalGenerateWithABC" not in workflow:
        raise RuntimeError("Packaged workflow must use the ABC-aware generate node.")
    return len(names)


def build(output):
    count = check()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, name in members():
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    data = output.read_bytes()
    print(f"{output.name}  {len(data):,} bytes  {count} files")
    print("sha256", hashlib.sha256(data).hexdigest())
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=BASE / "dist" / "2BZ-YuE2-installer.zip")
    build(parser.parse_args().output)

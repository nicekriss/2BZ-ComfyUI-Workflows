"""Maintain the permanent YuE2 download independently of other product releases."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

REPO = "nicekriss/2BZ-ComfyUI-Workflows"
ALIAS = "yue2-latest"
ASSET = "2BZ-YuE2-installer.zip"


def gh(*args, data=None):
    return subprocess.run(["gh", *args], input=json.dumps(data) if data is not None else None,
                          check=True, capture_output=True, text=True, encoding="utf-8").stdout


def sync(check_only=False):
    pages = json.loads(gh("api", f"repos/{REPO}/releases?per_page=100", "--paginate", "--slurp"))
    releases = [release for page in pages for release in page]
    source = max((release for release in releases if release["tag_name"].startswith("yue2-v")
                  and not release["draft"] and not release["prerelease"]), key=lambda release: release["published_at"])
    tag = source["tag_name"]
    commit = json.loads(gh("api", f"repos/{REPO}/commits/{tag}"))["sha"]
    alias = next((release for release in releases if release["tag_name"] == ALIAS), None)
    with tempfile.TemporaryDirectory(prefix="yue2-latest-") as temporary:
        directory = Path(temporary)
        gh("release", "download", tag, "--repo", REPO, "--pattern", ASSET,
           "--pattern", ASSET + ".sha256", "--dir", str(directory))
        archive = directory / ASSET
        checksum = directory / (ASSET + ".sha256")
        expected, name = checksum.read_text(encoding="utf-8").split()
        actual = hashlib.sha256(archive.read_bytes()).hexdigest()
        if name != ASSET or expected.lower() != actual:
            raise RuntimeError("Release ZIP does not match its SHA256 file")
        print(f"Verified {tag}: {actual}", flush=True)
        if check_only:
            return
        notes = directory / "notes.md"
        notes.write_text(
            "YuE2 전용 고정 다운로드입니다. 새 Yue2 정식 배포마다 자동으로 갱신됩니다.\n\n"
            f"현재 버전: [{tag}]({source['html_url']})\n\n"
            f"[최신 설치 ZIP 다운로드](https://github.com/{REPO}/releases/download/{ALIAS}/{ASSET})\n\n"
            "다른 제품 릴리스와 구분하기 위해 이 고정 링크용 릴리스는 Pre-release로 표시합니다. "
            "ZIP은 위 버전의 공개 배포본과 동일합니다. 자세한 변경·복구·제거 안내는 버전 링크를 확인하세요.\n\n"
            f"SHA256: `{actual}`\n", encoding="utf-8")
        if alias is None:
            gh("release", "create", ALIAS, str(archive), str(checksum), "--repo", REPO,
               "--target", commit, "--title", "YuE2 · 항상 최신 설치기", "--notes-file", str(notes),
               "--prerelease", "--latest=false")
        else:
            gh("release", "upload", ALIAS, str(archive), str(checksum), "--repo", REPO, "--clobber")
            gh("api", f"repos/{REPO}/git/refs/tags/{ALIAS}", "--method", "PATCH", "--input", "-",
               data={"sha": commit, "force": True})
            gh("release", "edit", ALIAS, "--repo", REPO, "--title", "YuE2 · 항상 최신 설치기",
               "--notes-file", str(notes), "--prerelease", "--latest=false")
        with tempfile.TemporaryDirectory(prefix="yue2-verify-") as verified:
            gh("release", "download", ALIAS, "--repo", REPO, "--pattern", ASSET, "--dir", verified)
            if hashlib.sha256((Path(verified) / ASSET).read_bytes()).hexdigest() != actual:
                raise RuntimeError("Permanent download verification failed")
        print(f"Published and verified {ALIAS} -> {tag}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    sync(parser.parse_args().check_only)

import argparse
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--work-dir', required=True)
    parser.add_argument('--dist-dir', default=str(ROOT / 'desktop-v0.5'))
    args = parser.parse_args()
    work = Path(args.work_dir).resolve()
    work.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which('ffmpeg')
    ffprobe = shutil.which('ffprobe')
    if not ffmpeg or not ffprobe:
        raise SystemExit('ffmpeg and ffprobe must be on PATH when building.')
    media = Path(ffmpeg).parent
    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--onedir', '--windowed',
               '--name', '2BZ Audio Cutter', '--icon', str(ROOT / 'app.ico'),
               '--distpath', args.dist_dir, '--workpath', str(work / 'build'), '--specpath', str(work)]
    for name in ('index.html', 'style.css', 'segments.js', 'scenes.js', 'main.js'):
        command += ['--add-data', f'{ROOT / name};.']
    for binary in [Path(ffmpeg), Path(ffprobe), *media.glob('*.dll')]:
        command += ['--add-binary', f'{binary};media']
    command += [str(ROOT / 'desktop.py')]
    subprocess.run(command, check=True)
    destination = Path(args.dist_dir) / '2BZ Audio Cutter'
    shutil.copy2(ROOT / 'DESKTOP-README.txt', destination / '사용안내.txt')
    licenses = destination / 'licenses'
    licenses.mkdir(exist_ok=True)
    ffmpeg_license = media.parent / 'LICENSE.txt'
    if ffmpeg_license.exists():
        shutil.copy2(ffmpeg_license, licenses / 'FFmpeg-LICENSE.txt')
    print(destination)


if __name__ == '__main__':
    main()

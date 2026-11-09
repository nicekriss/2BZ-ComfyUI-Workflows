# -*- coding: utf-8 -*-
"""8K 360 파노라마 PNG → 편집기가 360으로 알아보는 mp4 (20초 정지 영상 + 360 표시).
사용: python make_360_video.py 파노라마.png [초]   (또는 360영상만들기.bat 에 PNG 끌어다 놓기)
- 가로가 4096보다 크면 HEVC(H.265), 아니면 H.264. 같은 폴더에 <이름>_360.mp4 로 저장.
- 그래픽카드 인코더(NVIDIA → AMD → 인텔) 순서로 시도하고, 다 안 되면 CPU로 만듭니다(8K는 몇 분 걸림).
- ffmpeg 찾는 순서: 이 폴더의 ffmpeg.exe → PC에 깔린 ffmpeg → 컴피UI에 들어 있는 imageio-ffmpeg
- 인코더를 직접 고르려면 환경변수 PANO360_ENCODER (예: libx265)
"""
import os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"


def stop(msg):
    print("\n [멈춤] " + msg + "\n")
    sys.exit(1)


def find_ffmpeg():
    local = os.path.join(HERE, "ffmpeg.exe")
    if os.path.exists(local):
        return local
    if shutil.which("ffmpeg"):
        return shutil.which("ffmpeg")
    try:
        import imageio_ffmpeg  # 컴피UI에 VideoHelperSuite 등이 깔려 있으면 같이 들어 있음
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


src = os.path.abspath(sys.argv[1])
sec = sys.argv[2] if len(sys.argv) > 2 else "20"
try:
    from PIL import Image
except ImportError:
    stop("이 파이썬에 Pillow가 없어요. 컴피UI에 들어 있는 파이썬으로 실행해 주세요.")
Image.MAX_IMAGE_PIXELS = None
try:
    w, h = Image.open(src).size
except Exception:
    stop(f"그림 파일을 열 수 없어요: {src}")
if w != 2 * h:
    stop(f"가로:세로가 2:1인 360 파노라마가 아니에요 ({w}x{h})")

FF = find_ffmpeg()
if not FF:
    stop("ffmpeg를 찾지 못했어요.\n   아래에서 받아 압축을 풀고, bin 폴더 안의 ffmpeg.exe 를 이 bat 파일과 같은 폴더에 넣어 주세요.\n   " + FFMPEG_URL)

big = w > 4096
if big:  # 8K는 H.264 한계를 넘어서 HEVC로
    cands = [("hevc_nvenc", ["-preset", "p5", "-b:v", "120M"]), ("hevc_amf", ["-quality", "quality", "-b:v", "120M"]),
             ("hevc_qsv", ["-preset", "medium", "-b:v", "120M"]), ("libx265", ["-preset", "fast", "-crf", "18"])]
    tag = ["-tag:v", "hvc1"]
else:
    cands = [("h264_nvenc", ["-preset", "p5", "-b:v", "60M"]), ("h264_amf", ["-quality", "quality", "-b:v", "60M"]),
             ("h264_qsv", ["-preset", "medium", "-b:v", "60M"]), ("libx264", ["-preset", "medium", "-crf", "16"])]
    tag = []
force = os.environ.get("PANO360_ENCODER")
if force:
    cands = [c for c in cands if c[0] == force] or [(force, [])]

base = os.path.splitext(src)[0]
raw, out = base + "_raw.mp4", base + "_360.mp4"
print(f" {w}x{h} → {sec}초 360 영상 만드는 중...")
for enc, opts in cands:
    if enc.startswith("lib") and not force:
        print(" 그래픽카드 인코더를 못 써서 CPU로 만들어요. 8K는 몇 분 걸려요...")
    r =subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-framerate", "25", "-i", src, "-t", sec,
                        "-c:v", enc, *opts, *tag, "-pix_fmt", "yuv420p", raw], capture_output=True, text=True, errors="replace")
    if r.returncode == 0 and os.path.exists(raw) and os.path.getsize(raw) > 0:
        print(f" 인코더: {enc}")
        break
    if os.path.exists(raw):
        os.remove(raw)
else:
    stop("영상 만들기에 실패했어요. ffmpeg 메시지:\n" + (r.stderr or "").strip()[-800:])

subprocess.run([sys.executable, os.path.join(HERE, "inject360.py"), raw, out], check=True)
os.remove(raw)
print(" 완료:", out)
print(" 필모라 같은 편집기에 넣으면 360 영상으로 인식돼요.")

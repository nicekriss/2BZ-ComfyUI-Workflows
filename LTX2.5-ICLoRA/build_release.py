"""작업본(D:\\working\\watersim) → 배포본 변환. 로컬 값만 바꾸고 그래프 구조·링크는 그대로 둔다.

  python build_release.py
"""
import json
import re
from pathlib import Path

SRC = Path(r"D:\working\watersim\LTX25_ICLoRA_3FX_Water_Night_CleanPlate_FHD.json")
DST = Path(__file__).parent / "2BZ_LTX25_ICLoRA_3FX_Water_Night_CleanPlate.json"

wf = json.loads(SRC.read_text(encoding="utf-8"))
for n in wf["nodes"]:
    wv = n.get("widgets_values")
    if n["type"] == "VHS_LoadVideo":  # 내 테스트 영상 이름 → 자리표시
        wv["video"] = "your_video.mp4"
        wv["videopreview"]["params"]["filename"] = "your_video.mp4"
    if n["type"] == "LTXICLoRALoaderModelOnly":  # 내 PC 하위폴더(LTX25\) 제거 — 안내대로 models/loras 에 바로 넣으면 맞게
        wv[0] = wv[0].split("\\")[-1]
    if n["type"] == "MarkdownNote":
        wv[0] = wv[0].replace("(ComfyUI 본체는 최신 버전으로)", "(ComfyUI 본체 **0.37.0 이상** — 코어 노드 TextGenerate·ComfyMathExpression 사용)")
        wv[0] = wv[0].replace(
            "- **프롬프트가 엉뚱함(⑦)** → ③ 을 조금 더 구체적으로.",
            "- **프롬프트가 엉뚱함(⑦)** → ③ 을 조금 더 구체적으로.\n"
            "- **결과 색이 바램** → 폰으로 찍은 **HDR 영상**입니다. 코어 노드 `Convert Image Color Space`(source HDR → destination sRGB)를 "
            "「타일 디코드」와 「영상 합치기」 사이에 끼우세요. 일반(SDR) 영상에는 쓰지 마세요.")

s = json.dumps(wf, ensure_ascii=False, indent=1)
leaks = re.findall(r"[A-Za-z]:\\\\[^\"]{0,40}|kriss|watersim_[a-z_]+\.mp4|LTX25\\\\|hf_[A-Za-z0-9]{12,}", s)
assert not leaks, leaks
assert "0.37.0 이상" in s and "HDR 영상" in s
DST.write_text(s, encoding="utf-8")
types = sorted({n["type"] for n in wf["nodes"]})
print(DST.name, len(wf["nodes"]), "nodes", len(wf["links"]), "links")
print("custom:", [t for t in types if t.startswith(("LTX", "VHS_")) or "rgthree" in t])

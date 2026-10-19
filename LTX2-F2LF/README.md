# LTX2 시작 → 끝 프레임 (Frame to Last Frame) — 코어 노드판

1월 영상 「LTX2 영상 생성, 이제 더 쉬워짐… Frame to Last Frame 드디어 추가됨! (PainterLTXv2)」에서 시연한 흐름을 **커스텀 노드 없이 ComfyUI 기본 노드만**으로 다시 만든 워크플로입니다.

영상에서 쓴 PainterLTXv2 노드는 ComfyUI 2026-04-21 업데이트 이후 `'VAE' object has no attribute 'latent_frequency_bins'` 에러가 납니다(노드가 1월 이후 업데이트되지 않음). 이 판은 그 노드를 걷어내고 같은 2단계 구조를 코어 노드로 짰습니다.

**[워크플로 다운로드 (JSON)](https://raw.githubusercontent.com/nicekriss/2BZ-ComfyUI-Workflows/main/LTX2-F2LF/2BZ_LTX2_F2LF_core.json)** — 링크에서 우클릭 → 다른 이름으로 저장 후 ComfyUI 화면에 끌어다 놓으세요.

## 흐름

시작 프레임 + 마지막 프레임 → ③ 1단계 768×512, distilled 8스텝 → ④ 잠재 2배 업스케일 + 디테일러 LoRA 3스텝 (1536×1024) → ⑤ 영상+소리 mp4

## 필요한 것

**ComfyUI 0.41 이상**, 커스텀 노드 없음.

모델 4개 — 워크플로 안 「⓪ 먼저 읽기」 메모에 클릭하면 바로 받아지는 링크와 넣을 폴더가 있습니다.

| 파일 | 폴더 | 크기 |
|---|---|---|
| `ltx-2-19b-distilled-fp8.safetensors` (영상 VAE·오디오 VAE 포함) | `models/checkpoints/` | 27GB |
| `gemma_3_12B_it_fp4_mixed.safetensors` | `models/text_encoders/` | 약 8GB |
| `ltx-2-spatial-upscaler-x2-1.0.safetensors` | `models/latent_upscale_models/` | 1GB |
| `ltx-2-19b-ic-lora-detailer.safetensors` (선택) | `models/loras/LTX2/` | 2.6GB |

영상 설명란의 Kijai 모델(텍스트 인코더·디테일러 LoRA)을 이미 받았다면 체크포인트와 업스케일러만 추가하면 됩니다.

## 쓰는 법

1. ② 시작 프레임·마지막 프레임 넣기 (같은 장면의 두 순간이 좋습니다)
2. ② 프롬프트에 장면·동작·소리를 영어로. 가로·세로는 64배수, 프레임 수는 8n+1 (121 = 25fps 4.8초)
3. 실행 → `output/video/` 에 저장

## 확인한 환경

| GPU | 설정 | 시간 | VRAM 최고 |
|---|---|---|---|
| RTX 3090 24GB · ComfyUI 0.42.1 | 768×512 → 1536×1024 · 121프레임(4.8초) · 소리 포함 | 154초 | 22.8GB |
| RTX 3090 24GB · ComfyUI 0.42.1 | 768×768 → 1536×1536 · 73프레임(2.9초) · 소리 포함 | 162초 | 22.6GB |

결과 확인: 첫 프레임과 시작 이미지의 평균 픽셀 차이 2.3, 마지막 프레임과 끝 이미지 4.1 — 시작·끝이 입력대로 박히고 그 사이가 일정하게 움직입니다(프레임 간 변화 0.5~2.0, 점프 없음). 소리(AAC, 24kHz) 포함.

16GB 카드는 확인하지 못했습니다. 2단계에서 VRAM 이 모자라면 ④ 노드들을 Ctrl+B 로 끄고 ③ 결과를 바로 디코드하세요(768×512).

## 알아둘 것

- 1단계 시드는 매번 바뀌고 2단계 시드는 0 고정입니다. 1단계가 마음에 들면 2단계는 그대로 다듬기만 합니다.
- 「마지막 프레임 심기」 strength 는 0.7 이 기본입니다. 1.0 으로 올리면 끝 프레임은 더 정확하지만 중간이 멈췄다가 점프하거나 자세가 무너집니다(같은 시드 비교로 확인). 끝이 덜 맞으면 0.85 까지만.
- VRAM 이 부족하면 ⑤ 디코드 tile_size 를 512 로 줄이거나 ② 가로·세로를 줄이세요.
- 1단계만 보려면 ④ 노드들을 Ctrl+B 로 끄고 ③ 「심은 프레임 잘라내기」 잠재를 ⑤ 디코드에 직접 연결하세요.

## 라이선스

워크플로 파일은 이 저장소 라이선스를 따릅니다. 모델은 **LTX-2 Community License** 입니다 — 연매출 1천만 달러 미만은 상업 이용 포함 무료. 모델은 이 저장소에 포함하지 않으며 Hugging Face 에서 직접 받습니다.

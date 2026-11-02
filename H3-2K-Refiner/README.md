# MiniMax H3 로컬 2K 리파이너 — Deno 8+2

영상 「MiniMax H3 로컬 드디어 2K 생성 가능? 하지만.. 요구사양이..」에서 쓴 워크플로입니다.

MiniMax H3 레퍼런스→영상(R2V)에 NVIDIA [Open-H3-Regenerate-2K](https://huggingface.co/Efficient-Large-Model/Open-H3-Regenerate-2K) 리파이너를 붙였어요. 리파이너는 [Kijai](https://huggingface.co/Kijai/MiniMax-H3-experimental) 경량 LoRA(rank16, 150MB)를 씁니다. 방식은 [Deno님](https://www.youtube.com/@DenoPictures)이 먼저 찾아 공개한 8+2 조합 그대로입니다([원본 워크플로](https://huggingface.co/Deno2026/MiniMax-H3-DenoMix/blob/main/workflows/Deno_MiniMax_H3_R2V_Turbo_8plus2.json)). 이 판은 순정 ref2va 모델을 쓰고, 한국어 프롬프트 번역·해상도 선택·초 단위 길이·메모리 절약 노드를 더했습니다.

**[워크플로 다운로드 (JSON)](https://raw.githubusercontent.com/nicekriss/2BZ-ComfyUI-Workflows/main/H3-2K-Refiner/2BZ_H3_2K_Refiner_Deno8plus2.json)** — 링크에서 우클릭 → 다른 이름으로 저장 후 ComfyUI 화면에 끌어다 놓으세요.

## 흐름

레퍼런스 사진 1·2 + 한국어 프롬프트(Gemma 4가 영어로 번역) → 초안 Acc-8Step LoRA 8스텝 → 잠재 업스케일 ×2 → DMD LoRA + 2K 리파이너로 8스텝 스케줄의 **마지막 2스텝** → 최종 = 초안 ×2 크기

## 먼저 알아둘 것 — 요구사양

**2K는 지금은 24GB 이상 카드용입니다.**

| RTX 3090 24GB | 결과 | 시간 | VRAM 최고 |
|---|---|---|---|
| 2K(2560x1440) 5초 | 성공 | 8분 40초 | 96% |
| 2K 10초 | 실패 (98% 넘침) | — | — |
| FHD(1920x1088) 10초 | 성공 | 9분 35초 | 90% |
| FHD 15초 · 메모리 절약 노드 켬 | 성공 | 16분 42초 | 22.3GB |
| FHD 15초 · 절약 노드 끔 | 실패 | — | — |

VRAM 98% 이상이 이어지면 실패로 봤습니다. 16GB 이하 카드에서 2K가 됐다는 사례는 아직 찾지 못했습니다. 작은 카드는 FHD 이하로 쓰세요.

작은 카드라도 크게 손해 보는 건 아닙니다. 멀리 있는 인물이나 특정 앵글에서 디테일이 무너지는 건 H3 모델 자체의 한계라 공식 2K에서도 같습니다. 디테일이 확실히 좋아지는 건 **2K만큼 크게 뽑을 때**입니다. 초안을 낮춰 FHD로 끝내면 기존 FHD 방식과 디테일 차이는 크지 않습니다.

## 필요한 것

**ComfyUI 0.42 이상.** 모델 9개(합계 약 66GB)와 커스텀 노드 5개가 필요합니다. 워크플로 안 「⓪ 준비」 메모에 클릭하면 바로 받아지는 링크와 넣을 폴더가 있습니다. 로더 노드에 다운로드 정보를 넣어 두어서, 빠진 모델이 있으면 ComfyUI가 열 때 목록과 받기 버튼을 띄웁니다.

| 파일 | 폴더 | 크기 |
|---|---|---|
| [minimax_h3_ref2va_pruned_int8_convrot.safetensors](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors?download=true) | `models/diffusion_models/` | 21GB |
| [qwen3vl_32b_minimax_h3_int8_convrot.safetensors](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors?download=true) | `models/text_encoders/` | 27GB |
| [gemma4_e4b_it_fp8_scaled.safetensors](https://huggingface.co/Comfy-Org/gemma-4/resolve/main/text_encoders/gemma4_e4b_it_fp8_scaled.safetensors?download=true) (번역) | `models/text_encoders/` | 9GB |
| [minimax_h3_video_vae_int8_convrot.safetensors](https://huggingface.co/Kijai/MiniMax-H3-experimental/resolve/main/minimax_h3_video_vae_int8_convrot.safetensors?download=true) | `models/vae/` | 3.2GB |
| [minimax_h3_audio_vae_fp32.safetensors](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/vae/minimax_h3_audio_vae_fp32.safetensors?download=true) | `models/vae/` | 0.6GB |
| [MiniMax-H3-Ref2VA-Acc-8Step_pruned_comfy.safetensors](https://huggingface.co/Kijai/MiniMax-H3-experimental/resolve/main/loras/MiniMax-H3-Ref2VA-Acc-8Step_pruned_comfy.safetensors?download=true) | `models/loras/` | 1.7GB |
| [minimax_h3_dmd_ref2va_8step_turbo_pruned.safetensors](https://huggingface.co/drbaph/MiniMax-H3-Turbo-Lora-ComfyUI/resolve/main/experimental/minimax_h3_dmd_ref2va_8step_turbo_pruned.safetensors?download=true) | `models/loras/` | 2.3GB |
| [minimax_h3_open_regenerate_2k_refiner_rank_16_bf16.safetensors](https://huggingface.co/Kijai/MiniMax-H3-experimental/resolve/main/loras/minimax_h3_open_regenerate_2k_refiner_rank_16_bf16.safetensors?download=true) | `models/loras/` | 0.16GB |
| [minimax_h3_latent_upscaler_3d_conv_v1_bf16.safetensors](https://huggingface.co/Efficient-Large-Model/Open-H3-Regenerate-2K/resolve/main/latent_upsampler/minimax_h3_latent_upscaler_3d_conv_v1_bf16.safetensors?download=true) | `models/latent_upscale_models/` | 0.7GB |

커스텀 노드:

| 노드팩 | 쓰는 곳 | 설치 |
|---|---|---|
| [Comfyui_Minimax_h3_latent_Upscaler](https://github.com/LBH-123-AI/Comfyui_Minimax_h3_latent_Upscaler) | 잠재 업스케일 | Manager에 같은 이름의 다른 포크가 있으니 git 주소로 |
| [ComfyUI-OpenH3-Regenerate2K](https://github.com/Songssx/ComfyUI-OpenH3-Regenerate2K) | 리파인 때 소리 유지 | 레지스트리 미등록 → git 주소로 |
| [comfyui-deno-custom-nodes](https://github.com/Deno2026/comfyui-deno-custom-nodes) | 해상도 선택 · 텍스트 인코더 내리기 | Manager 검색: Deno |
| [H3-Optimizations](https://github.com/Zironic/H3-Optimizations) | 리파인 메모리 절약 (15초 FHD) | Manager 검색: H3 Optimizations |
| [ComfyUI-KJNodes](https://github.com/kijai/ComfyUI-KJNodes) | 번역 앞뒤·디코드 전 메모리 정리 | Manager 검색: KJNodes |

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/LBH-123-AI/Comfyui_Minimax_h3_latent_Upscaler.git
git clone https://github.com/Songssx/ComfyUI-OpenH3-Regenerate2K.git
```

## 쓰는 법

1. **레퍼런스 사진 1·2**에 인물·의상 사진을 넣으세요(기본 이름 `picture1.png`·`picture2.png`는 자리만 잡아 둔 것).
2. ⓪ 노란 칸에 **한국어 프롬프트**. 사진1·사진2라고 쓰면 `<Picture 1>`·`<Picture 2>`로 바뀌고, 대사는 `<d>안녕하세요</d>`처럼 감싸면 한국어 그대로 갑니다. 기본 프롬프트는 영상의 15초 판타지 액션 예시입니다.
3. **해상도 선택** — 최종 = 초안 ×2
   - FHD(기본): Preset Ratio · 16:9 · 0.51MP → 960x544 → **1920x1088**
   - 2K: Manual Input · 1280 x 720 · divisible_by **16** → **2560x1440**, 길이는 **5초**까지
4. **길이 (초)** 최대 15. 프레임 수는 17k+5로 자동 보정.
5. 실행 → `output/H3_Deno8plus2/` 에 초안(draft)과 최종(final) 저장.

## 확인한 환경

RTX 3090 24GB · RAM 64GB · ComfyUI 0.42.0. 위 표의 시간은 같은 그래프로 잰 값입니다.

배포 직전(2026-11-02) 이 JSON 그대로 다시 돌린 결과: FHD 1920x1088 · 5초(124프레임) · 소리 포함 — **6분 21초**(모델 로드 포함), VRAM 최고 22.2GB, 98% 이상 0초.

## 라이선스

워크플로 파일은 이 저장소 라이선스를 따릅니다. 모델은 이 저장소에 포함하지 않으며 각 Hugging Face 페이지의 라이선스를 따릅니다. 쓰기 전에 원문을 확인하세요. H3 출력물로 다른 모델을 학습하는 건 금지입니다.

# FastH3 + USDU Video Restore v1.1.0

MiniMax H3 Fast VSA 모델을 USDU의 타일 복원 경로에 연결해, 기존 영상을 빠르게 복원·확대하는 ComfyUI 워크플로우입니다.

## 설치

1. [Releases](https://github.com/nicekriss/2BZ-ComfyUI-Workflows/releases/latest)에서 ZIP을 다운로드해 압축을 풉니다.
2. ComfyUI를 완전히 종료합니다.
3. `Install-SolAttn-MiniMax.bat`을 더블클릭합니다.
4. 창이 뜨면 `main.py`가 들어 있는 ComfyUI 폴더를 선택합니다.
5. ComfyUI Manager에서 [Ultimate SD Upscale Guider H3](https://github.com/lisitskyaa/ComfyUI_UltimateSDUpscaleGuider_H3)를 설치합니다.
6. 아래 모델을 지정된 폴더에 넣고 ComfyUI를 재시작합니다.
7. `2BZ_FastH3_USDU.json`을 ComfyUI로 드래그합니다.

## 필수 모델

| 파일 | 설치 폴더 |
|---|---|
| [FastH3 VSA 본체](https://huggingface.co/Kijai/MiniMax-H3-experimental/resolve/main/minimax_h3_fastvideo_vsa_datafree_1300step_4step_int8_convrot.safetensors) | `ComfyUI/models/diffusion_models/` |
| [Qwen3-VL 텍스트 인코더](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors) | `ComfyUI/models/text_encoders/` |
| [MiniMax H3 Video VAE](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/vae/minimax_h3_video_vae_fp16.safetensors) | `ComfyUI/models/vae/` |
| [RealESRGAN x2](https://github.com/xinntao/Real-ESRGAN) | `ComfyUI/models/upscale_models/` |

모델 용량은 합계 약 41GB입니다.

## Sol-Attn 설치기가 하는 일

설치기는 kijai가 [Comfy-Kitchen PR #117](https://github.com/Comfy-Org/comfy-kitchen/pull/117)에 공개한 원본 파일을 직접 내려받습니다. 기존 설치 파일이 다르면 먼저 백업하며, 필요한 `comfy-kitchen` Sol-Attn 커널도 검사합니다.

Sol-Attn은 NVIDIA CUDA 및 SM 8.0 이상 GPU를 대상으로 합니다. 지원 조건이 맞지 않으면 일반 어텐션으로 폴백되어 속도 이득이 없을 수 있습니다.

## 기본 사용법

1. `1 · Load Input Video`에 영상을 넣습니다.
2. 인물이 있으면 `6 · 타일 조건부여` 프롬프트에 인종과 핵심 얼굴 특징을 긍정형 문장으로 적습니다.
3. Queue를 실행합니다.

해상도와 타일 크기는 입력 영상에 맞춰 자동 계산됩니다. 기본값은 약 1MP 정규화, `1.4x` 출력, `denoise 0.25`입니다.

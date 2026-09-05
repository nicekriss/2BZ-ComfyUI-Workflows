# FastH3 + USDU · 설치기 v1.2.0-rc1 (메인컴 테스트용)

먼저 [START-HERE-ko.md](START-HERE-ko.md)를 읽으세요. 워크플로우는 v1.1.1이며 이번 테스트 대상은 자동 설치·복구 기능입니다.

MiniMax H3 Fast VSA 모델을 USDU의 타일 복원 경로에 연결해, 기존 영상을 빠르게 복원·확대하는 ComfyUI 워크플로우입니다.

## 설치

1. [테스트 Release v1.2.0-rc1](https://github.com/nicekriss/2BZ-ComfyUI-Workflows/releases/tag/v1.2.0-rc1)에서 ZIP을 다운로드해 압축을 풉니다.
2. ComfyUI를 완전히 종료합니다.
3. `Install-SolAttn-MiniMax.bat`을 더블클릭합니다.
4. 창이 뜨면 `main.py`가 들어 있는 ComfyUI 폴더를 선택합니다.
5. [Ultimate SD Upscale Guider H3](https://github.com/lisitskyaa/ComfyUI_UltimateSDUpscaleGuider_H3) 포크를 설치합니다. Manager에서 해당 URL로 확인하거나 `custom_nodes`에서 저장소를 clone합니다. 같은 노드명을 등록하는 다른 USDU Guider 팩과 중복 설치하지 마세요.
6. 아래 모델을 지정된 폴더에 넣고 ComfyUI를 재시작합니다.
7. `2BZ_FastH3_USDU.json`을 ComfyUI로 드래그합니다.

## 필수 모델

| 파일 | 설치 폴더 |
|---|---|
| [FastH3 VSA 본체](https://huggingface.co/Kijai/MiniMax-H3-experimental/resolve/main/minimax_h3_fastvideo_vsa_datafree_1300step_4step_int8_convrot.safetensors) | `ComfyUI/models/diffusion_models/` |
| [Qwen3-VL 텍스트 인코더](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors) | `ComfyUI/models/text_encoders/` |
| [MiniMax H3 Video VAE](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/vae/minimax_h3_video_vae_fp16.safetensors) | `ComfyUI/models/vae/` |
| [RealESRGAN x2plus](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth) | `ComfyUI/models/upscale_models/` |

모델 용량은 합계 약 41GB입니다.

업스케일 로더의 기존 선택은 로컬 파일명 `RealESRGAN_x2.pth`입니다. 파일이 없다면 위 공식 모델을 받고 로더에서 `RealESRGAN_x2plus.pth`를 직접 선택하세요. 로컬 파일과 공식 파일의 동일성은 검증하지 않았으므로 기존 비교 영상과 동일 모델이라고 단정하지 않습니다.

## Sol-Attn 설치기가 하는 일

설치기는 kijai가 [Comfy-Kitchen PR #117](https://github.com/Comfy-Org/comfy-kitchen/pull/117)에 공개한 v5 파일을 원본 URL에서 직접 내려받고 SHA-256을 확인합니다. 기존 설치 파일이 다르면 덮어쓰지 않고 중단합니다. 다운로드한 노드는 재배포 ZIP에 포함하지 않습니다.

`sol_attn` import만으로는 부족합니다. 현재 VSA 경로는 CUDA `sol_attn_chunked`와 `tail`, `block_len`, `coarse_gate`, `topk_ratio` 인자를 요구합니다. 설치 전 GPU/BF16 지원과 128-token CUDA 커널 실행을 검사합니다. 이 검사는 전체 H3 모델 호환성이나 속도·화질을 보장하지 않습니다.

현재 CUDA 검사가 실패하면 기존 comfy-kitchen 파일을 백업한 뒤 공식 `0.2.32` wheel을 `--no-deps`로 설치합니다. Torch와 다른 패키지는 변경하지 않습니다. 설치 또는 CUDA 재검사에 실패하면 백업으로 복구합니다. 성공 후에도 `Restore-SolAttn-MiniMax.bat`으로 수동 복구할 수 있습니다. 실행 중인 ComfyUI를 먼저 종료해야 합니다.

격리된 테스트 환경에서 0.2.31 → 0.2.32 설치와 VSA CUDA 실행을 검증했습니다. 메인컴 전체 H3 실행은 아직 미검증이며, 이 파일은 테스트 배포본입니다.

진단만 실행: `powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-SolAttn-MiniMax.ps1 -ComfyUIRoot "C:\path\ComfyUI" -CheckOnly`. Python 자동 탐색이 모호하면 `-PythonExe "C:\path\python.exe"`를 추가하세요. Linux/macOS용 원클릭 설치기는 제공하지 않습니다.

Sol-Attn은 NVIDIA CUDA 및 SM 8.0 이상 GPU를 대상으로 합니다. 지원 조건이 맞지 않으면 일반 어텐션으로 폴백되어 속도 이득이 없을 수 있습니다.

## 기본 사용법

1. `1 · Load Input Video`에 영상을 넣습니다.
2. 추가 프롬프트는 평소 비워 둡니다. 필요할 때만 `선택 · 추가 상황·인물 표현`에 원본에 실제로 있는 특징을 적습니다. 인종 지정은 필수가 아닙니다.
3. Queue를 실행합니다.

기본값은 약 1MP·32배수 정규화, `2.0x` 출력, 2스텝, `denoise 0.25`입니다. 정규화된 크기를 USDU 타일과 조건부여에 함께 연결합니다. 예: 1376×768 → 2752×1536. FHD 근처는 배율 1.4~1.5를 비교할 수 있지만, 정확한 1920×1080은 별도 리사이즈가 필요합니다.

어텐션 선택은 `VSA (FastVideo)`, keep 10%, `exact_kv_and_rows`를 유지합니다. 일반 Sol-Attn 모드와 동일하지 않습니다. 실행 로그의 `VSA tiles`와 fallback/커널 오류 여부를 확인하세요. 새 범용 프롬프트의 영상 품질 재검증은 아직 하지 않았습니다.

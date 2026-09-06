# FastH3 + USDU · v1.2.1

**[처음 시작하기](START-HERE-ko.md)**. 기존 영상을 약 1MP로 정규화하고 ESRGAN + FastH3 USDU로 2배 확대합니다. 빠른 처리나 원본 완전 보존을 보장하지 않습니다. 실패한 latent 경로는 제거했습니다.

이 ZIP은 보완한 설치 패키지입니다. [v1.2.1 다운로드](https://github.com/nicekriss/2BZ-ComfyUI-Workflows/releases/tag/v1.2.1). **새 설치기로 깨끗한 PC에서 전체 설치·렌더 검증은 미완료**입니다.
기존 환경에서는 RTX 3090 24GB / RAM 64GB로 실행했고, 사용자는 메인 RTX 4070 Ti SUPER 16GB / RAM 32GB에서도 업스케일 성공을 확인했습니다. 녹화 동시 실행이나 모든 길이·해상도 보장은 아닙니다.

## 워크플로우에서 바로 받기

한국어 `2BZ_FastH3_USDU.json` / English `2BZ_FastH3_USDU_EN.json` 중 하나를 먼저 여세요. **① 모델 다운로드** 노트에 모델 4개의 직접 다운로드 링크와 저장 위치가 있습니다. **⑥ 최신 테스트 결과**에서 비교표를 볼 수 있습니다. 영문판은 노트·노드 제목·그룹 제목을 번역했고 계산은 같습니다. [English setup guide](START-HERE-en.md).

## 필수 모델 4개 — 약 41GB, 별도 다운로드

| 파일 | ComfyUI 기준 폴더 |
|---|---|
| [FastH3 VSA 본체](https://huggingface.co/Kijai/MiniMax-H3-experimental/resolve/main/minimax_h3_fastvideo_vsa_datafree_1300step_4step_int8_convrot.safetensors) | `models/diffusion_models/` |
| [Qwen3-VL 인코더](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors) | `models/text_encoders/` |
| [H3 Video VAE](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/vae/minimax_h3_video_vae_fp16.safetensors) | `models/vae/` |
| [RealESRGAN_x2plus.pth](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth) | `models/upscale_models/` |

파일명을 변경하지 마세요. 기존 로컬 x2 파일과 공식 x2plus가 동일하다고 주장하지 않습니다. 공식 다운로드와 로더 선택을 일치시킨 것입니다.

## 설치 도구

- `Install-SolAttn-MiniMax.bat`: [kijai SolAttn v5](https://github.com/user-attachments/files/31576773/sol_attn_minimax_v5.py) 다운로드/해시 검증, Kitchen 0.2.32 CUDA 검사/필요 시 설치, 검증된 H3 코어 2파일 게이트 패치. [원본 출처](https://github.com/Comfy-Org/comfy-kitchen/pull/117).
- `Install-USDU-H3.bat`: [H3 USDU 포크](https://github.com/lisitskyaa/ComfyUI_UltimateSDUpscaleGuider_H3) commit `6836cf365d1b84ef2cb605a8e92a0901a6d2c81f`와 하위 저장소 `2322caa480535b1011a1f9c18126d85ea444f146` 설치. Git for Windows 필요.
- `Check-Setup.bat`: H3 소스/작은 CUDA 검사. 전체 준비 완료 검사가 아닙니다.
- `Restore-SolAttn-MiniMax.bat`: 백업된 H3/Kitchen 복구. 노드·모델은 남습니다.

실행 중인 ComfyUI에 설치하지 마세요. 미확인 코어 버전이나 수정된 노드는 덮어쓰지 않습니다. **호환성 제한과 복구 방법은 START-HERE-ko.md 필독**.
Windows / NVIDIA SM80+ 및 BF16 환경용이며 Linux/macOS 설치기는 없습니다.

## 기본값

전체 영상 / 1MP·32배수 / 2배 / Euler·simple / 2스텝 / denoise 0.20 / VSA keep 10% / 빈 추가 프롬프트 / 원본 오디오 연결.
정확한 FHD 또는 가로 2048 출력은 아닙니다. 기본 프롬프트는 특정 인종·성별을 지정하지 않습니다.
얼굴·의상·배경이 달라질 수 있습니다. 같은 15초 비교에서 일반 H3+Turbo 96분37초, FastH3 USDU 48분40초, 단일 노드47분36초였습니다. 단일 노드는 사용자 검토에서 더 변형되어 USDU를 최종 채택했습니다. VSA만의 전체 가속 효과와 구분하세요. OOM 선택 대응은 [MEMORY-ko.md](MEMORY-ko.md). [측정 기록](BENCHMARK.md).

## 출처·라이선스

- [FastH3 레딧 공개 글](https://www.reddit.com/r/StableDiffusion/comments/1w0xkpb/weve_open_sourced_minimax_h3_that_generates_15s/)
- [H3 + USDU 레딧 활용 글](https://www.reddit.com/r/StableDiffusion/comments/1vwgoy2/minimax_h3_ultimate_sd_upscale_can_actually_fix/)

두 링크는 워크플로우 제작자/출처 메모에도 있습니다. 원문 성능 주장과 본 배포 실측은 별개입니다.
설치 스크립트·문서는 저장소 LICENSE를 따릅니다. H3 게이트 패치의 ComfyUI 파생 부분은 GPL-3.0이며 동봉 LICENSE-ComfyUI.txt를 참고하세요. [대상 원본 소스](https://github.com/Comfy-Org/ComfyUI/tree/7fd919f0caff66a52289ea5b19cb6eaca0da04ef). 패치 변경분은 h3-gate-patch.json, 적용·복구 소스는 h3_compat.py에 모두 포함합니다. 타사 모델·커스텀 노드는 각각 원저작자의 조건을 따릅니다.

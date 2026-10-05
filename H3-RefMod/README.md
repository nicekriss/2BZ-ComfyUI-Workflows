# MiniMax H3 RefMod — 만들기 + 영상 생성

너무바쁜베짱이 RefMod 리뷰에서 사용하는 두 워크플로우입니다. 모델·사진·음성·개인 RefMod는 포함하지 않습니다.

1. **[RefMod 제작 JSON 다운로드](https://raw.githubusercontent.com/nicekriss/2BZ-ComfyUI-Workflows/main/H3-RefMod/2BZ_H3_RefMod_01_Create.json)**
2. **[영상 생성 JSON 다운로드](https://raw.githubusercontent.com/nicekriss/2BZ-ComfyUI-Workflows/main/H3-RefMod/2BZ_H3_RefMod_02_Video_Gemma4.json)**

링크가 텍스트로 열리면 파일로 저장한 뒤 ComfyUI 캔버스로 끌어다 놓으세요. 워크플로우 사용에 익숙한 사용자를 위한 배포입니다.

## 먼저 RefMod 만들기

- 제작 JSON을 열고 `input/RefMod_images/my_character`에 같은 캐릭터의 사진을 넣습니다. 폴더 노드에서 본인 폴더로 바꿔도 됩니다.
- 저장 이름 `my_character`를 원하는 이름으로 바꿉니다. 같은 이름은 덮어씁니다.
- H3 비디오 VAE를 선택하고 실행합니다. 제작에는 RefMod 노드팩과 비디오 VAE가 필요합니다.
- 결과는 `models/refmods/characters/`에 저장됩니다. 영상 생성 JSON에서 RefMod 목록을 새로고침하고 선택하세요.
- 사진 여러 장을 하나로 묶은 RefMod는 Video 타입으로 표시될 수 있습니다. 파일명이나 슬롯 번호가 아닌 실제 Picture/Video/Audio 참조 미리보기를 기준으로 프롬프트를 작성하세요.

## 영상 만들기

H3 Singularity + DMD 8-step을 사용합니다. 저해상도 7스텝 → 잠재 업스케일 → 마지막 1스텝 구조입니다. 한국어 번역은 ComfyUI 기본 TextGenerate와 Gemma 4 E4B로 처리합니다.

기본은 세로 3초 입력, 24fps, 1080×1920입니다. H3 프레임 제약으로 실제 길이는 입력 초와 조금 다를 수 있습니다. 본인 RefMod를 선택한 뒤 예제 프롬프트의 인물·의상·상황을 바꾸세요. 가로 영상은 비율을 16:9로 변경합니다.

메모리 부족 시 워크플로우의 VRAM 그룹에서 길이 → 업스케일 배율 → 시작 MP → 마지막 단계 chunk_rows 순서로 하나씩 조절하세요. 8/12/16GB별 성공 보장 프리셋은 아닙니다.

## 호환성과 확인 범위

MiniMax H3·Gemma 4·TextGenerate·BlockSparseAttention을 지원하는 ComfyUI가 필요합니다. 최신 ComfyUI라는 조건만으로 모델·커스텀 노드·어텐션 커널 설치까지 완료되는 것은 아닙니다.

로컬에서 사용한 그래프를 바탕으로 개인 경로와 참조 선택값을 제거했습니다. 공개본은 JSON/연결/필수 노드를 검사했고, 번역 분기의 참조 표기와 한국어 대사 보호는 기존 로컬 테스트를 통과했습니다. 배포 직전 깨끗한 새 환경에서 전체 설치·영상 생성을 다시 수행한 것은 아닙니다.

개인적으로 확장한 Text Encode의 미사용 source_image 입력을 제거해 공개 노드 정의에 맞췄습니다. 타사 노드는 각 원본 저장소에서 설치하세요.

# 필요한 커스텀 노드 · Manager 검색 이름

**Registry 등록 표시명 (2026-10-05 확인)**

- [MiniMax H3 RefMod](https://github.com/Luisacaotica/ComfyUI-MiniMaxH3Mod) — 제작자 `luisacaotica`, ID `ComfyUI-MiniMaxH3Mod`
- [Deno Custom Nodes](https://github.com/Deno2026/comfyui-deno-custom-nodes) — 제작자 `deno2026`, ID `deno-custom-nodes`
- [H3 Optimizations](https://github.com/Zironic/H3-Optimizations) — 제작자 `zironic`, ID `h3-optimizations`
- [ComfyUI-KJNodes](https://github.com/kijai/ComfyUI-KJNodes) — 제작자 `kijai`, ID `comfyui-kjnodes`. 구형 Manager 목록 이름: **KJNodes for ComfyUI**.

**잠재 업스케일러: 검색 설치로 안내하지 않습니다.**

[Comfyui_Minimax_h3_latent_Upscaler](https://github.com/LBH-123-AI/Comfyui_Minimax_h3_latent_Upscaler) — 현재 조사에서 Manager 등록을 확인하지 못했습니다. Git URL 설치 기능이 있는 환경에서는 이 저장소 주소를 사용하거나, `ComfyUI/custom_nodes` 폴더에서 실행하세요.

```bash
git clone https://github.com/LBH-123-AI/Comfyui_Minimax_h3_latent_Upscaler.git
```

설치 후 ComfyUI를 재시작하세요. 각 저장소의 의존성 설치 안내도 확인하세요.

번역용 CLIPLoader·TextGenerate, Sol Attention을 선택하는 BlockSparseAttention은 이 환경의 ComfyUI 기본 노드입니다. 이 그래프에 별도 SolAttn 노드팩이나 LM Studio 번역 노드는 필요하지 않습니다.

# 모델 준비

ComfyUI와 프런트엔드에 H3 / Gemma 4 / TextGenerate 지원이 필요합니다. 아래 경로는 ComfyUI/models 기준입니다.

**확산 모델** — [Minimax-h3_Singularity_ref2va_Pruned_v1.3_int8.safetensors](https://huggingface.co/WarmBloodAban/Minimax-h3_Singularity/resolve/main/Minimax-h3_Singularity_ref2va_Pruned_v1.3_int8.safetensors?download=true)

저장: `models/diffusion_models/H3SING/`

**8스텝 LoRA** — [minimax_h3_dmd_ref2va_8step_turbo_pruned.safetensors](https://huggingface.co/drbaph/MiniMax-H3-Turbo-Lora-ComfyUI/resolve/main/experimental/minimax_h3_dmd_ref2va_8step_turbo_pruned.safetensors?download=true)

저장: `models/loras/H3_DMD/experimental/`

**H3 텍스트 인코더** — [qwen3vl_32b_minimax_h3_int8_convrot.safetensors](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors?download=true)

저장: `models/text_encoders/H3/`

**번역 Gemma 4** — [gemma4_e4b_it_fp8_scaled.safetensors](https://huggingface.co/Comfy-Org/gemma-4/resolve/main/text_encoders/gemma4_e4b_it_fp8_scaled.safetensors?download=true)

저장: `models/text_encoders/`

**비디오 VAE** — [minimax_h3_video_vae_fp16.safetensors](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/vae/minimax_h3_video_vae_fp16.safetensors?download=true)

저장: `models/vae/`

**오디오 VAE** — [minimax_h3_audio_vae_fp32.safetensors](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/vae/minimax_h3_audio_vae_fp32.safetensors?download=true)

저장: `models/vae/`

**잠재 업스케일러** — [minimax_h3_latent_upscaler_3d_bf16.safetensors](https://huggingface.co/LBH-123-AI/Minimax_h3_latent_Upscaler/resolve/13ccf95d85d120bdbc92c05b1247a6e147bf54bf/minimax_h3_latent_upscaler_3d_bf16.safetensors?download=true)

저장: `models/latent_upscale_models/`

업스케일러는 기존 엔진과 같은 파일을 받도록 이전 공개 리비전 링크를 고정했습니다.

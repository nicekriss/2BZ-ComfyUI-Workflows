# MiniMax H3 Image — 사진 4장 참조 생성·편집

영상 「MiniMax H3 Image로 사진 4장 합성하기」에서 쓴 워크플로입니다.

**[워크플로 다운로드 (JSON)](https://raw.githubusercontent.com/nicekriss/2BZ-ComfyUI-Workflows/main/H3-Image/2BZ_H3Image_01_Edit_4Ref.json)** — 링크에서 우클릭 → 다른 이름으로 저장 후 ComfyUI 화면에 끌어다 놓으세요.

## 무엇을 하나

- 사진 칸 4개. 켠 칸만 위에서부터 `사진1`, `사진2`…로 불러서 편집·합성합니다.
- 칸을 전부 끄면 글로만 생성(t2i)합니다.
- 한국어로 쓰면 Gemma 4가 영어로 번역하고, 증강을 켜면 긴 프롬프트로 살을 붙입니다.
- 크기는 메가픽셀(4~20, 공식 권장 16)과 비율로 정합니다.

쓰는 순서와 주의할 점은 워크플로 안 「⓪ 먼저 읽기」 메모에 있습니다.

## 필요한 것

**ComfyUI 0.45.1 이상.** 모델 4개(합계 약 44GB)와 커스텀 노드 1개.
Comfy Desktop 앱에서 열면 Issues 패널의 **Download all** 한 번으로 알맞은 폴더에 들어갑니다.

| 파일 | 폴더 | 크기 |
|---|---|---|
| [minimax_h3_image_pruned_int8_convrot.safetensors](https://huggingface.co/Comfy-Org/MiniMax-H3-Image/resolve/main/diffusion_models/minimax_h3_image_pruned_int8_convrot.safetensors) | `models/diffusion_models/` | 19.5GB |
| [qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors](https://huggingface.co/Comfy-Org/MiniMax-H3-Image/resolve/main/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors) | `models/text_encoders/` | 14.6GB |
| [minimax_h3_image_vae_fp16.safetensors](https://huggingface.co/Comfy-Org/MiniMax-H3-Image/resolve/main/vae/minimax_h3_image_vae_fp16.safetensors) | `models/vae/` | 1.1GB |
| [gemma4_e4b_it_fp8_scaled.safetensors](https://huggingface.co/Comfy-Org/gemma-4/resolve/main/text_encoders/gemma4_e4b_it_fp8_scaled.safetensors) (번역) | `models/text_encoders/` | 8.4GB |

커스텀 노드: **ComfyUI-KJNodes** (`VRAM_Debug`) — Manager에서 `ComfyUI-KJNodes` 검색.

사진 칸에 들어 있는 `vintage_yellow_taxi.png`는 예시 파일명이라 빨갛게 뜹니다. 본인 사진을 올리면 됩니다.

## 실측 (VRAM 16GB + 램 32GB)

- 9~16MP 한 장 70~90초, VRAM 약 14GB
- 20MP도 되지만 남는 램이 2GB 아래로 내려갑니다. 다른 프로그램을 닫고 쓰세요.
- 4MP로 전신을 뽑으면 얼굴이 뭉개집니다. 인물 장면은 9~16MP로.

## 써 보고 알게 된 것

- 사진 네 장을 한 번에 합치라고 하면 잘 안 섞일 때가 있습니다. 옷 먼저 입혀 캐릭터를 만들고, 그 결과를 배경에 세우는 식으로 두 번에 나누면 훨씬 잘 됩니다.
- 옷 참조 사진에 얼굴이 있으면 그 얼굴까지 따라올 수 있습니다. 얼굴을 가리고 넣으세요.
- 따옴표로 지정한 큰 글자는 정확하고, 지정하지 않은 작은 글자는 깨집니다.

## 라이선스

MiniMax-H3-Image Community License. 한국은 제외 지역이라 [MiniMax 콘솔](https://platform.minimax.io/console/license)에서 신청해 승인을 받아야 씁니다. 결과물로 다른 AI 모델을 학습시키는 것은 금지입니다. 쓰기 전에 원문을 직접 확인하세요.

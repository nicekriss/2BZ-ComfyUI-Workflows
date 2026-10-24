# MOSS-Image 텍스트 → 이미지 + 박스 레이아웃 (코어 노드판)

푸단대 OpenMOSS 팀의 5B 이미지 모델 **MOSS-Image**용 워크플로입니다. 프롬프트만으로 생성하거나, 캔버스에 박스를 그려 글자·물체 자리를 지정해 생성합니다. 한글 간판·메뉴판처럼 **글자가 들어간 이미지**가 강점입니다.

**[워크플로 다운로드 (JSON)](https://raw.githubusercontent.com/nicekriss/2BZ-ComfyUI-Workflows/main/MOSS-Image/2BZ_MOSS_01_T2I_Layout.json)** — 링크에서 우클릭 → 다른 이름으로 저장 후 ComfyUI 화면에 끌어다 놓으세요.

## 필요한 것

**ComfyUI 0.42.0 이상**, 커스텀 노드 없음(MOSS-Image 지원이 0.42.0에 들어옴). 박스 그리기 노드는 **노드 2.0(Vue) 화면**에서 씁니다.

모델 4개, 합계 약 14GB — 워크플로 안 「① 모델 다운로드」 메모에도 같은 링크가 있습니다.

| 파일 | 폴더 | 크기 |
|---|---|---|
| [moss_image_sft_int8_convrot.safetensors](https://huggingface.co/Comfy-Org/MOSS-Image/resolve/main/diffusion_models/moss_image_sft_int8_convrot.safetensors) | `models/diffusion_models/` | 5.4GB |
| [qwen3.5_9b_w4a8_gptq.safetensors](https://huggingface.co/Comfy-Org/MOSS-Image/resolve/main/text_encoders/qwen3.5_9b_w4a8_gptq.safetensors) | `models/text_encoders/` | 7.3GB |
| [flux2-vae_small.safetensors](https://huggingface.co/Comfy-Org/MOSS-Image/resolve/main/vae/flux2-vae_small.safetensors) | `models/vae/` | 0.25GB |
| [lora.safetensors](https://huggingface.co/lodestones/MOSS-Image-SFT-8-steps-dmd/resolve/main/lora.safetensors) → 이름을 **moss_sft_8step_dmd_lora.safetensors** 로 | `models/loras/` | 1.2GB |

- 하위 폴더 없이 위 폴더에 바로 넣으면 됩니다. 다른 폴더에 두었다면 「MOSS 엔진」 서브그래프 안 로더 노드에서 다시 골라 주세요.
- 8스텝 가속을 안 써도 LoRA 파일은 필요합니다(없으면 저장 노드가 조용히 빠지고 아무것도 안 나옴).
- 라이선스: 모델·LoRA 모두 Apache-2.0.

## 쓰는 법

**① 조작판만 만지면 됩니다.** 복잡한 부분은 「MOSS 엔진」 서브그래프로 접어 두었습니다.

1. **비율** 드롭다운에서 고르기. **4MP로 크게** 를 켜면 네이티브 4MP(2K), 끄면 1MP(권장).
2. **하이레즈 픽스**: 1MP로 뽑고 2배로 키워 다듬기(약 4MP). 강도 0.3~0.5 권장. 네이티브 2K보다 자연스럽습니다.
3. **프롬프트** 칸에 장면을 씁니다. 그림 속 글자는 "큰따옴표"로 감싸면 한글도 그대로 나옵니다.
4. 스위치
   - **프롬프트 증강**: 한 줄 아이디어(한국어 OK)를 Qwen3.5 9B가 자세한 영어 캡션으로 불려 줍니다.
   - **박스 레이아웃 사용**: 박스 그리기 노드에서 영역을 그리고 종류(text/obj)·글자·설명을 적습니다. 배경 쪽부터 먼저. 켜면 프롬프트 증강은 자동으로 꺼집니다.
     - 박스 캔버스는 고정 크기(기본 1024×1024)라 크기·4MP·하이레즈를 바꿔도 박스가 비율대로 따라옵니다. **비율을 바꾸면 박스 그리기 노드의 width·height도 같은 비율로** 맞춰 주세요(예: 3:4 → 768×1024, 16:9 → 1024×576).
   - **박스 설명 영어로 번역**(기본 ON): 박스 설명을 한글로 써도 영어로 바꿔 넣습니다. 그림에 쓸 글자는 그대로 둡니다.
   - **8스텝 가속**: LoRA·스텝 8·CFG 1로 한 번에 바뀝니다(약 2.5배 빠름).
   - **SLG 디테일 보정**: 가속을 끄고 CFG를 쓸 때만 효과가 있습니다.
5. 결과는 `output/MOSS/날짜/` 에 저장됩니다.

## 3090 실측 (int8)

1MP 약 20초 · 8스텝 가속 8~11초 · 네이티브 4MP 약 100초 · 하이레즈 픽스 약 125초 · 증강/번역 +4~6초.
편집(인페인팅) 모델은 아닙니다 — 텍스트 → 이미지 전용.

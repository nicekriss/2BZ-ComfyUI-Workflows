# 2BZ · Qwen-Image 2.1 워크플로

너무바쁜베짱이(2BZ) Qwen-Image 2.1 리뷰 배포본. 2026-09-23. ComfyUI **0.37.0 이상**.

| 파일 | 하는 일 | 커스텀 노드 |
|---|---|---|
| `2BZ_Qwen21_01_T2I.json` | 텍스트 → 이미지 (1MP·2K 네이티브·투명 PNG) | 없음 |
| `2BZ_Qwen21_02_ImageEdit.json` | 이미지 편집, 레퍼런스 최대 10장 | 없음 |
| `2BZ_Qwen21_03_Upscale2K.json` | Qwen 2.1을 업스케일러로 (0.3MP → 2K) | 없음 |
| 04 AutoDetail | 텍스트로 검출 → 박스마다 2K 리터치 → 제자리 복귀 | 다음 편 공개 예정 |

01~03은 Comfy 공식 템플릿 그래프에 2BZ 색상·메모·테스트 기록만 얹은 것이라 계산은 공식과 같습니다. 커스텀 노드 없이 코어만으로 돌아갑니다.

## 모델 (3개, 약 16GB)
`<ComfyUI>/models/` 아래에 넣습니다. 각 워크플로 왼쪽 **⓪ 먼저 읽기** 메모에도 같은 링크와 저장 경로가 있습니다.

클릭하면 바로 다운로드됩니다.

- `diffusion_models/` ← [qwen_image_2.1_int8_convrot.safetensors (6.8GB)](https://huggingface.co/Comfy-Org/Qwen-Image-2.1/resolve/main/diffusion_models/qwen_image_2.1_int8_convrot.safetensors)
- `text_encoders/` ← [qwen3vl_8b_int8_convrot.safetensors (8.7GB)](https://huggingface.co/Comfy-Org/Qwen-Image-2.1/resolve/main/text_encoders/qwen3vl_8b_int8_convrot.safetensors)
- `vae/` ← [qwen_image_2.1_vae_bf16.safetensors (0.6GB)](https://huggingface.co/Comfy-Org/Qwen-Image-2.1/resolve/main/vae/qwen_image_2.1_vae_bf16.safetensors)
- 저장소: https://huggingface.co/Comfy-Org/Qwen-Image-2.1

## 색상 규칙 (모든 파일 공통)
- **검정** = 건드리지 않는 엔진(로더·샘플러·VAE)
- **노랑** = 프롬프트, 사용자가 쓰는 글
- **빨강** = 필수 입력 이미지 · **갈색** = 두 번째 레퍼런스
- **파랑** = 숫자·토글(크기, denoise)
- **보라** = 이 워크플로를 특별하게 만드는 노드
- **초록** = 미리보기·저장·비교
- **하늘색** = 읽기용 메모

## 테스트 기록
[TEST-RECORD-ko.md](TEST-RECORD-ko.md) — RTX 3090 / RTX 4070 Ti SUPER 속도, 스텝 수, 편집 시드 실패 모드, shift 검증, 업스케일, 캐릭터 시트 결과.

## 폴더
- `src/` 장식 전 원본 그래프 (Comfy 공식 템플릿)
- `notes/` ⓪ 먼저 읽기 메모 원문
- `samples/q21u_h3frame_03mp.png` 03 업스케일 샘플 입력 (720×400 영상 프레임)

## 배포 전 확인한 것
- LoadImage 기본값: 01은 없음, 02는 공식 템플릿 샘플명(템플릿 브라우저에 포함), 03은 동봉 샘플. 자기 파일로 바꿔서 쓰세요.
- 켜둔 디버그 스위치 없음. seed는 777 고정(fixed). 편집 결과가 과포화로 타면 seed만 바꿔 보세요(테스트 기록 3절).
- 모델 링크 HEAD 200 확인(2026-09-23).

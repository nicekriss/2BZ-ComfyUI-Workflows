# ③ 사용 순서 — Qwen 2.1을 업스케일러로 쓰기

전용 업스케일 노드·LoRA 없이, **편집 모드 + custom_size ON + 2K 라텐트 + 강화 프롬프트**로 저해상도(0.3~1MP)를 2K로 올립니다.
출처: r/StableDiffusion "qwen 2.1 is very good upscaler" (H3 영상 프레임 0.3MP를 6GB VRAM에서 테스트).

1. **Load Image** 에 저해상도 원본. 샘플 `q21u_h3frame_03mp.png`(720×400)가 같이 들어 있습니다.
2. **Resolution Selector** 비율을 **원본과 같은 비율**로. 4.2MP ≈ 2K 예산(16:9면 2752×1536).
3. **prompt** 는 기본 문장(Enhance this image to high resolution…) 그대로. 그레인이 심하면 문장을 짧게. 얼굴·글자를 지켜야 하면 `Keep the face/text exactly the same.` 추가.
4. Queue. 3090 기준 2K 한 장 약 2분(124~131s), 1MP는 36s.

## 실행 전 확인
- 결과는 프롬프트에 크게 좌우됩니다. 첫 결과가 이상하면 시드보다 프롬프트를 먼저 바꾸세요.
- 이 방식은 '다시 그리기'라 원본과 100% 같지 않습니다. 원본 보존이 우선이면 denoise가 있는 img2img 쪽(04 자동 리터치 워크플로, denoise 0.3)을 쓰세요.

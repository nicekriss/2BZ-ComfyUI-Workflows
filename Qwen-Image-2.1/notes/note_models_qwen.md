# ① 모델 다운로드 · 저장 경로

`<ComfyUI>/models/` 아래 경로. **3개 필수, 합계 약 16GB.** 파일명을 클릭하면 바로 다운로드됩니다. ComfyUI 코어 **0.37.0 이상** 필요(TextEncodeQwenImage21 노드).

**diffusion_models/**

- [qwen_image_2.1_int8_convrot.safetensors](https://huggingface.co/Comfy-Org/Qwen-Image-2.1/resolve/main/diffusion_models/qwen_image_2.1_int8_convrot.safetensors) (6.8GB)

**text_encoders/**

- [qwen3vl_8b_int8_convrot.safetensors](https://huggingface.co/Comfy-Org/Qwen-Image-2.1/resolve/main/text_encoders/qwen3vl_8b_int8_convrot.safetensors) (8.7GB)

**vae/**

- [qwen_image_2.1_vae_bf16.safetensors](https://huggingface.co/Comfy-Org/Qwen-Image-2.1/resolve/main/vae/qwen_image_2.1_vae_bf16.safetensors) (0.6GB)

저장소: [Hugging Face: Comfy-Org/Qwen-Image-2.1](https://huggingface.co/Comfy-Org/Qwen-Image-2.1)

## 선택
- bf16 확산 모델(13.3GB)은 24GB 이상에서만. 화질 차이는 미미해서 이 배포본은 int8 세트만 씁니다.
- 16GB(4070 Ti SUPER)에서도 int8 세트로 2K 네이티브까지 OOM 없이 동작했습니다.

## SHA256 (받은 뒤 확인용)
- 확산 모델 `cb74113c…eaa57d`
- 텍스트 인코더 `8bfd0f6e…452e8f`
- VAE `bb21f747…6b7c9`

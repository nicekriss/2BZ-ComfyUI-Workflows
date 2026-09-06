# 모델 다운로드 · 여기서 바로 클릭

워크플로우를 먼저 연 뒤 아래 링크로 받으세요. **받은 파일명 그대로** 표시된 폴더에 넣습니다. 모델이 아직 없으면 로더의 MISSING 표시는 정상입니다.

### ① FastH3 VSA 본체
[FastH3 체크포인트 다운로드](https://huggingface.co/Kijai/MiniMax-H3-experimental/resolve/main/minimax_h3_fastvideo_vsa_datafree_1300step_4step_int8_convrot.safetensors)
→ `ComfyUI/models/diffusion_models/`

### ② H3 Qwen 텍스트 인코더
[Qwen3-VL NVFP4 인코더 다운로드](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors)
→ `ComfyUI/models/text_encoders/`

### ③ H3 비디오 VAE
[H3 Video VAE FP16 다운로드](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/vae/minimax_h3_video_vae_fp16.safetensors)
→ `ComfyUI/models/vae/`

### ④ 픽셀 업스케일러
[RealESRGAN_x2plus.pth 다운로드](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth)
→ `ComfyUI/models/upscale_models/`

합계 약 41GB. 링크는 2026-09-07 응답 확인. 등록한 공유 모델 폴더도 가능합니다.
모델 목록을 새로고침하고 로더에서 선택하세요. 인식되지 않을 때 ComfyUI를 재시작합니다.
실측의 로컬 x2 파일과 배포용 공식 x2plus의 동일성은 미검증입니다.

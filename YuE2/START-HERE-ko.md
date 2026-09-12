# YuE2 음악 생성 설치기 · yue2-v0.1.0-rc4

가사와 음악 스타일을 입력해 보컬과 반주가 있는 곡을 만드는 ComfyUI 워크플로입니다.

## 다운로드와 설치

1. **[2BZ-YuE2-installer-v0.1.0-rc4.zip 다운로드](https://github.com/nicekriss/2BZ-ComfyUI-Workflows/releases/download/yue2-v0.1.0-rc4/2BZ-YuE2-installer-v0.1.0-rc4.zip)**를 받아 압축을 풉니다. `Source code (zip)`이나 BAT 파일 하나만 받지 마세요.
2. **Install-YuE2.bat**을 더블클릭합니다.
3. **ComfyUI 폴더**를 선택합니다. `main.py`와 `custom_nodes`가 있는 폴더입니다. 포터블은 그 위 폴더도 가능합니다. Desktop 앱의 EXE 설치 폴더가 아니라 실제 ComfyUI 인스턴스 폴더를 선택하세요.
4. **모델 저장 폴더**를 선택합니다. 기본 `ComfyUI/models` 또는 이미 사용하는 공유 모델 폴더를 선택하면 됩니다.
5. `INSTALLED`가 나오면 ComfyUI를 재시작하고 **YuE2_Music.json**을 캔버스로 드래그합니다. 워크플로 메뉴에도 `2BZ_YuE2_Music`으로 복사됩니다.

Python은 `.venv`, `venv`, 포터블 `python_embeded`/`python_embedded`에서 찾습니다. 여러 개이거나 찾지 못하면 그 ComfyUI가 실제 사용하는 `python.exe`를 선택합니다.

## 지원 환경

- Windows, NVIDIA BF16 지원 GPU, Python 3.10–3.13. 기존 ComfyUI의 CUDA Torch를 공유합니다.
- 24GB VRAM 권장. 확인한 생성 환경은 RTX 3090 24GB / RAM 64GB / Python 3.13 / Torch 2.10.0+cu130입니다.
- Torch 2.10.x 이외 버전은 경고 후 실제 import로 검증합니다. Torch 2.12.1+cu130 검증 결과는 `VALIDATION.md`를 참고하세요. Torch를 낮추거나 교체하지 않습니다.
- 폴더 탐색은 일반·Desktop·포터블 구조를 처리하지만 모든 배포판의 새 PC 설치 검증을 완료한 것은 아닙니다. 첫 공개는 시험 배포입니다.
- 모델 약 7.8GB와 별도 Python 패키지 공간이 필요합니다. 여유 공간 12GB 이상을 권장합니다.

## 설치기가 하는 일

- 공식 YuE2 런타임을 준비하고, `custom_nodes/ComfyUI-YuE2`(이 저장소의 subprocess 노드 3개)와
  `custom_nodes/toobusy-abc-studio`(ABC Studio 연동 노드 1개)를 함께 설치합니다.
- `user/2bz-yue2/runtime`에 별도 환경을 만들고, ComfyUI의 CUDA Torch와 기본 의존성을 참조합니다. ComfyUI 본체와 기존 Python 패키지는 수정하지 않습니다.
- 공식 YuE 소스를 고정 commit으로 받고, 필요한 모델·설정·토크나이저·라이선스를 공식 Hugging Face에서 다운로드합니다.
- SHA256을 확인합니다. 기존 파일이 정확하면 재사용하고, 다른 파일은 덮어쓰지 않습니다. 중단된 다운로드는 `.part`에서 이어받습니다.
- 이미 설치된 패키지는 덮어쓰지 않고 유지합니다.
  - `custom_nodes/ComfyUI-YuE2`가 이미 있으면 기존 환경을 보존하고 건너뜁니다.
  - `custom_nodes/toobusy-abc-studio`가 이미 있으면 기존 스튜디오를 보존하고 건너뜁니다.
- 실행 시에는 인터넷을 사용하지 않습니다. 설치 단계에는 GitHub·Hugging Face·PyPI 접속이 필요합니다.

## dependency 보존 원칙

- **ComfyUI shared dependencies**: Torch, torchvision, torchaudio, xformers, triton, CUDA 관련 패키지는 설치·업데이트·다운그레이드하지 않습니다. 기존 numpy, safetensors 등도 호환 범위면 재사용합니다.
- **YuE2 additional dependencies**: `install_yue2.py`의 `ADDITIONAL` 목록을 확인하고 부족한 것만 `user/2bz-yue2/runtime`에 설치합니다. Transformers 5.x처럼 YuE2 요구 버전과 다른 경우에만 subprocess 안에서 전용 버전을 사용합니다. ComfyUI의 버전은 유지합니다.
- 모든 pip 호출은 YuE2 하위 경로만 허용하고 `--no-deps --only-binary=:all:`을 사용합니다. upstream `requirements.txt` / `pip install .` / 빌드 의존성 resolver는 실행하지 않습니다. SHA256 검증한 순수 Python `src/yue2`를 전용 runtime에 복사합니다.
- **YuE2 optional dependencies**: vLLM/fast backend, triton, hf-xet은 자동 설치하지 않습니다. `pynvml`도 설치·교체하지 않습니다. 기존 pynvml 경고는 별개이며, nvidia-ml-py가 이미 있어도 본 설치기는 양쪽을 보존합니다.
- 설치 전후 전체 패키지 버전·위치·RECORD 해시를 `user/2bz-yue2/audits/<UTC 시각>/`에 기록합니다. 설치 실패 때도 비교하며, 변경이 감지되면 경고와 오류로 종료합니다. Torch를 다시 설치하는 자동 rollback은 하지 않습니다.
- `Check-YuE2.bat`은 모델 해시와 실제 모델/VAE loader·tokenizer import 및 가중치 loading 직전까지 확인합니다. 곡 생성은 별도 실행 검증입니다.

## 처음 곡 만들기

1. **② 장르·가사**에서 가사를 입력합니다. `[Verse]`, `[Chorus]`, `[Outro]`처럼 구간을 나누면 편합니다.
2. 장르를 고릅니다. `style_override`에 직접 스타일을 쓰면 선택한 장르보다 우선합니다. 기본 예제는 한국어 붐뱁 홍보 랩입니다. 팝·록·재즈·댄스 프리셋을 쓰려면 이 칸을 비우세요.
3. **③ 생성**의 `planning`을 선택합니다. `full`은 멜로디+코드 계획, `melody`는 멜로디, `off`는 악보 계획 없이 생성합니다.
4. **Run**을 누르고 완료 후 저장 노드 플레이어로 듣습니다. `seed`를 바꾸면 다른 곡을 만들 수 있습니다.

길이는 모델이 결정하며 프롬프트의 초 단위 지시는 보장되지 않습니다. 처음에는 짧은 가사로 실행하세요. `memory_gib`는 실행 메모리 예산이며 곡 길이 설정이 아닙니다.

FLAC은 ComfyUI의 `output/YuE2/`에 저장됩니다. Desktop에서는 앱의 공유 output 폴더입니다. 생성별 하위 폴더에 오디오, 생성 기록, `generation.log`, `metrics.json`이 남습니다. 큐 중지는 ComfyUI 상단 중지 버튼을 사용합니다.

공식 모델의 편집 가능한 악보·외부 ABC·커버 관련 기능 전체를 구현한 노드는 아닙니다. 이 패키지의 연결 범위는 **텍스트 스타일+가사 → 곡 생성**입니다.

## 모델 수동 다운로드

설치기를 쓰면 수동 다운로드는 필요 없습니다. 직접 받는 경우 아래 폴더를 구분하세요. 두 모델 모두 큰 파일 이름이 `model.safetensors`입니다.

```text
선택한 모델 폴더/
  audio_encoders/YuE2-3B/
    model.safetensors
    config.json
    generation_config.json
    yue2_generation_config.json
    qwen.tiktoken
    weights_manifest.json
    LICENSE
  vae/YuE2-Vae/
    model.safetensors
    config.json
    weights_manifest.json
    LICENSE
```

- [YuE2-3B 파일 목록](https://huggingface.co/m-a-p/YuE2-3B/tree/main) · 약 7.26GB 가중치
- [YuE2-VAE 파일 목록](https://huggingface.co/m-a-p/YuE2-Vae/tree/main) · 약 531MB 가중치
- [공식 사용법](https://github.com/multimodal-art-projection/YuE) · [공식 데모](https://map-yue2.github.io/)

설치기에 사용하는 정확한 revision·파일 URL·해시는 `downloads.json`에 있습니다. 모델 가중치에는 **CC BY-NC 4.0**이 적용됩니다. 이 저장소의 MIT 라이선스가 모델 라이선스를 대체하지 않습니다.

## 확인과 오류 해결

`Check-YuE2.bat`에서 같은 ComfyUI 폴더를 선택합니다. 모델 전체 해시 확인으로 잠시 걸릴 수 있습니다. `SETUP VERIFIED`는 파일과 실행 환경 검사 통과이며, 실제 곡 생성 성공은 Run 후 새 오디오로 확인하세요.

- Python/CUDA 오류: 시스템 Python이 아니라 ComfyUI의 Python을 선택했는지 확인합니다.
- 기존 노드가 있다는 오류: 기존 팩을 덮어쓰지 않은 것입니다. ComfyUI를 종료하고 해당 팩을 `custom_nodes` 밖에 보관하세요.
- 다운로드 중단: 동일한 BAT를 다시 실행합니다. 체크섬 오류가 명시된 경우에만 표시된 `.part` 파일을 지우고 다시 받습니다.
- 기존 모델 파일 불일치: 표시된 파일을 별도 보관한 뒤 재실행합니다. 다른 모델을 같은 폴더에 섞지 마세요.
- 빨간 Unknown 노드: ComfyUI 재시작 후 시작 로그의 YuE2 import 오류를 확인합니다.
- 생성 실패: 해당 곡의 `generation.log` 마지막 오류를 확인합니다. 지원 환경에서도 다른 작업이 GPU 메모리를 점유하면 실패할 수 있습니다.
- ComfyUI/Python/모델 폴더 이동: `custom_nodes/ComfyUI-YuE2/setup.json`의 경로와 `user/2bz-yue2/runtime/Lib/site-packages/comfy_cuda.pth` 참조가 달라집니다. 새 위치에서 재설치하세요.

제거하려면 ComfyUI 종료 후 `custom_nodes/ComfyUI-YuE2`와 `user/2bz-yue2`를 삭제합니다. 모델과 생성 결과, 저장한 워크플로는 별도로 유지됩니다. 설치기는 기존 노드 제거·코어 패치·모델 업로드를 수행하지 않습니다.

## 영상 설명란 문구

> 설치 ZIP을 받아 압축을 푼 뒤 Install-YuE2.bat을 실행하세요. ComfyUI 폴더와 모델 저장 폴더를 선택하면 필요한 파일을 자동으로 받습니다. 설치 완료 후 ComfyUI를 재시작하고 YuE2_Music.json을 열면 됩니다. Windows·NVIDIA 대상 시험 배포이며, 자세한 조건은 설치 안내서를 확인해주세요.

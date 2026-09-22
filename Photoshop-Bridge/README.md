# TooBusy AI Photoshop Bridge · v0.2.3

캔버스·파일·레이어를 입력으로 동기화하고 ComfyUI 생성 결과를 Photoshop에 적용하는 자체 제작 UXP 플러그인입니다.

**[설치 ZIP 다운로드](https://github.com/nicekriss/2BZ-ComfyUI-Workflows/releases/tag/photoshop-bridge-v0.2.3)** → `2BZ-TooBusyAI-Photoshop-Bridge-v0.2.3.zip`을 받아 압축을 풀고 `TooBusyAI-Setup.exe`를 실행하세요. Windows용 기존 ComfyUI 환경에 필요한 구성을 추가합니다.

[설치 순서](START-HERE-ko.md) · [검증 범위](VALIDATION.md)

0.2.3은 선택 영역 확대 처리와 원본 색감 보정으로 인페인팅을 개선했습니다. 플러그인 안의 업데이트 확인과 실제 실행 워크플로우 저장을 지원합니다. 기존 사용자는 같은 릴리스의 CCX만 열어 업데이트하세요. 설치기는 Civitai API 키 인증과 이어받기를 지원합니다.

## 두 가지 Photoshop 연동 제품

기존 **[Photoshop AI (SD-PPP)](../Photoshop-SDPPP/START-HERE-ko.md)**도 계속 제공합니다. Bridge는 별도 설치기·플러그인 ID·커스텀노드 폴더를 사용합니다. 기존 SD-PPP를 제거하거나 교체하지 않습니다.

Bridge에는 별도 입력·결과 창, 결과 이력 이동, 캔버스·새 문서·선택 영역 적용, 설치된 모델 목록, Illustrious 계열 체크포인트 변경과 최대 8개 LoRA 배합, 라인아트·뎁스·포즈·참조 이미지 제어가 있습니다. 제어 기능의 실행 여부와 결과 품질은 다르며, 포즈·부분 수정 품질 및 의뢰인 PC의 전체 설치·생성 검수는 남아 있습니다.

## 소스와 빌드

`plugin/`은 개인 연결 키가 비어 있는 배포 ID의 플러그인 소스입니다. `comfy_node/`는 자체 Bridge, `installer/`는 설치기와 고정 다운로드 명세입니다. 모델 가중치와 타사 노드 소스는 포함하지 않습니다.

1. Adobe UXP Developer Tools에서 `plugin/manifest.json`을 패키징하여 `release/toobusy.photoshop.bridge_PS.ccx`에 저장합니다.
2. Python 가상환경에 `installer/requirements-build.txt`를 설치합니다.
3. 해당 Python으로 `installer/build.py`를 실행합니다. `release/TooBusyAI-Setup.exe`가 생성됩니다.

빌드 산출물과 실제 PC의 연결 파일은 커밋하지 않습니다. 자체 소스에는 저장소의 MIT 라이선스가 적용됩니다. 실행 파일의 Python·Tcl/Tk 및 라이브러리 고지는 배포 ZIP의 `licenses/`에 포함됩니다. 다운로드 구성의 원저자 링크·SHA-256은 `installer/dependencies.json`에 있습니다.

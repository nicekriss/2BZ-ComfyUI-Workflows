# 2BZ ComfyUI Workflows

너무바쁜베짱이(2BZ)가 실제 제작과 비교 테스트에 사용한 ComfyUI 워크플로우를 배포합니다.

English users: open **2BZ_FastH3_USDU_EN.json** from the ZIP, then use its clickable model-download note. [English setup guide](FastH3-USDU/START-HERE-en.md).

## YuE2 Music

가사와 스타일로 보컬·반주가 있는 곡을 생성합니다. **[설치 ZIP 다운로드](https://github.com/nicekriss/2BZ-ComfyUI-Workflows/releases/latest/download/2BZ-YuE2-installer.zip)**는 기존 ComfyUI Torch를 보존하며, Torch 2.12.1+cu130에서 설치·43.48초 생성 검증을 완료했습니다. 모델 약 7.8GB 자동 다운로드, 별도 subprocess 실행 환경과 한국어 예제 워크플로를 포함합니다.

ZIP 압축을 풀고 ComfyUI를 종료한 뒤 `YuE2/Install-YuE2.bat`을 실행하세요. YuE2와 ABC Studio v0.4.4을 함께 설치합니다. [릴리스 안내](https://github.com/nicekriss/2BZ-ComfyUI-Workflows/releases/latest). [설치·사용 가이드](YuE2/START-HERE-ko.md) · [검증 범위와 남은 한계](YuE2/VALIDATION.md). Windows·NVIDIA 대상 시험 배포이며 모델 가중치는 CC BY-NC 4.0입니다.

## FastH3 + USDU Video Restore

기존 영상을 약 1MP로 정규화한 뒤 MiniMax H3 Fast 모델과 USDU 타일 복원으로 확대합니다. v1.2.1은 2배이며, 타일 크기는 정규화된 입력에 자동으로 맞춥니다. FHD 고정 출력은 아닙니다.

**[설치 ZIP 다운로드 · v1.2.1](https://github.com/nicekriss/2BZ-ComfyUI-Workflows/releases/tag/v1.2.1)** → Assets의 `2BZ-FastH3-USDU-installer-v1.2.1.zip`을 받으세요. `Source code (zip)`이 아닙니다. [처음 시작하기](FastH3-USDU/START-HERE-ko.md).

- 기본 복원 강도: `denoise 0.20`
- v1.2.1 기본 출력 배율: `2x`
- 기본 프롬프트: 인종·성별을 지정하지 않는 범용 복원 지시 + 선택 추가 묘사
- 권장 입력 길이: 약 5초
- 기존 실행 환경: RTX 3090 24GB. 메인 RTX 4070 Ti SUPER 16GB / RAM 32GB도 업스케일 성공(사용자 확인). 새 v1.2.1 설치기로 깨끗한 환경 전체 설치·렌더 검증은 미완료.
- 최종 선택: FastH3 USDU. 같은 15초·2스텝·denoise 0.20 비교에서 일반 H3+Turbo 96분37초 → FastH3 USDU 48분40초. 단일 노드는47분36초였으나 사용자 검토에서 더 변형되어 미채택. [조건·한계](FastH3-USDU/BENCHMARK.md).
- OOM 때만 [선택적 메모리 보완](FastH3-USDU/MEMORY-ko.md). 기본 그래프는 추가 KJNodes 없이 유지합니다.
- 상세 설치법: [FastH3-USDU/README.md](FastH3-USDU/README.md)

## TooBusy AI Photoshop Bridge

자체 제작 Photoshop 패널에서 이미지 싱크, 별도 결과 창, 모델 교체·LoRA 배합과 라인아트·뎁스·포즈 제어를 사용합니다. **기존 SD-PPP 제품도 계속 제공하며, 서로 별도 제품입니다.**

**[Bridge 설치 ZIP · v0.2.4](https://github.com/nicekriss/2BZ-ComfyUI-Workflows/releases/tag/photoshop-bridge-v0.2.4)** · [설치 안내](Photoshop-Bridge/START-HERE-ko.md) · [기능과 검증 범위](Photoshop-Bridge/README.md)

Windows용 기존 ComfyUI에 필요한 노드·모델·플러그인을 추가하는 시험 배포입니다. 새 ComfyUI를 설치하지 않습니다. 의뢰인 PC의 전체 설치·최종 생성은 추가 검수 대상입니다.

## Photoshop AI (SD-PPP)

포토샵에서 그린 선화를 ComfyUI로 채색하고 결과를 포토샵 레이어로 되돌려받습니다. 설치 도우미가 노드·모델·플러그인·워크플로우를 한 번에 잡아줍니다.

[SD-PPP 설치 ZIP · v0.1.4](https://github.com/nicekriss/2BZ-ComfyUI-Workflows/releases/tag/photoshop-sdppp-v0.1.4) · [처음 시작하기](Photoshop-SDPPP/START-HERE-ko.md) · [상세 설명](Photoshop-SDPPP/README.md)

- 선화 구조 유지 강도 조절, t2i / i2i 전환, 붓터치 LoRA 켜고 끄기
- 플러그인 입력창 포커스 문제 자동 패치 (해시 일치 시에만, 복원 가능)
- 확인한 환경: Windows 11 + RTX 3090 + Photoshop 2026. 8GB 환경은 미검증

## 주의

이 저장소는 워크플로우, 설치 도우미와 자체 제작 Photoshop Bridge 플러그인을 제공합니다. 모델, ComfyUI, 타사 커스텀 노드와 CUDA 커널은 포함하거나 재배포하지 않습니다. 각 파일은 안내된 원본 배포처에서 직접 받습니다.

## 제작

- 기획·테스트: [너무바쁜베짱이](https://www.youtube.com/@toobusyAI)
- GitHub: [nicekriss](https://github.com/nicekriss)

이 저장소의 자체 제작 워크플로우·문서·설치 스크립트는 [MIT License](LICENSE)로 배포합니다. 타사 구성요소에는 각 원저작자의 라이선스가 적용됩니다.

# 2BZ ComfyUI Workflows

너무바쁜베짱이(2BZ)가 실제 제작과 비교 테스트에 사용한 ComfyUI 워크플로우를 배포합니다.

English users: open **2BZ_FastH3_USDU_EN.json** from the ZIP, then use its clickable model-download note. [English setup guide](FastH3-USDU/START-HERE-en.md).

## 2BZ 오디오 커터 — 음악 자르기 / 뮤비 장면 준비

**[Windows ZIP 다운로드 · v0.6](https://github.com/nicekriss/2BZ-ComfyUI-Workflows/releases/download/audio-cutter-v0.6.0/2BZ-Audio-Cutter-v0.6.0-Windows-x64.zip)** · [사용 안내](Audio-Cutter/README.md)

노래를 몇 초씩 나누거나 원하는 구간만 MP3로 저장합니다. 처음에는 음악 자르기만 표시하고, **뮤비 프로젝트**를 선택하면 구간별 이미지·키프레임·프롬프트·결과 영상을 함께 관리합니다. Windows 단독 프로그램이며 ComfyUI가 필요하지 않습니다.

## LTX 2.5 IC-LoRA — 물 · 밤 · 사람 지우기

찍어둔 영상에 사람·카메라·배경은 그대로 두고 효과만 입힙니다. 한 워크플로에 물 채우기 / 낮→밤 / 사람 지우기 3종, 스위치 딸깍으로 전환. 세로·가로 영상 자동, 한 줄 한국어 요청을 AI가 영어 프롬프트로 써줍니다.

**[워크플로 다운로드 (JSON)](https://raw.githubusercontent.com/nicekriss/2BZ-ComfyUI-Workflows/main/LTX2.5-ICLoRA/2BZ_LTX25_ICLoRA_3FX_Water_Night_CleanPlate.json)** · [사용 안내](LTX2.5-ICLoRA/README.md)

- 필요: ComfyUI 0.37.0 이상 + `ComfyUI-LTXVideo` · `ComfyUI-VideoHelperSuite` · `rgthree-comfy`
- 확인한 환경: RTX 3090 24GB, RTX 4070 Ti SUPER 16GB (FHD 121프레임 436초, 시스템 RAM 32GB 중 30.2GB 사용)
- 모델: LTX-2.x Community License (연매출 1천만 달러 미만 상업 이용 무료)

## Qwen-Image 2.1

Qwen-Image 2.1 리뷰에서 쓴 워크플로 3종입니다. 커스텀 노드 없이 ComfyUI 0.37.0 이상 코어만으로 돌아갑니다. 모델 다운로드 링크와 저장 경로가 워크플로 안 메모에 들어 있습니다.

[Qwen-Image-2.1 폴더](Qwen-Image-2.1/) · [사용 안내](Qwen-Image-2.1/README.md) · [테스트 기록](Qwen-Image-2.1/TEST-RECORD-ko.md)

- 01 T2I: 텍스트 → 이미지, 1MP·2K 네이티브·투명 PNG
- 02 Image Edit: 이미지 편집, 레퍼런스 최대 10장
- 03 Upscale 2K: 편집 모드를 업스케일러로 써서 0.3MP → 2K
- 확인한 환경: RTX 3090 24GB, RTX 4070 Ti SUPER 16GB (int8 convrot 모델 세트)
- ⚠ 모델은 Qwen Research License(연구·평가용)입니다. 협찬·외주·판매용 등 상업 작업에는 아직 쓰지 마세요. [자세히](Qwen-Image-2.1/README.md#-라이선스-상업-이용-주의)

## YuE2 Music

가사와 스타일로 보컬·반주가 있는 곡을 생성합니다. **[설치 ZIP 다운로드](https://github.com/nicekriss/2BZ-ComfyUI-Workflows/releases/download/yue2-latest/2BZ-YuE2-installer.zip)**는 기존 ComfyUI Torch를 보존하며, Torch 2.12.1+cu130에서 설치·43.48초 생성 검증을 완료했습니다. 모델 약 7.8GB 자동 다운로드, 별도 subprocess 실행 환경과 한국어 예제 워크플로를 포함합니다.

ZIP 압축을 풀고 ComfyUI를 종료한 뒤 `YuE2/Install-YuE2.bat`을 실행하세요. YuE2와 ABC Studio v0.4.5을 함께 설치합니다. [릴리스 안내](https://github.com/nicekriss/2BZ-ComfyUI-Workflows/releases/latest). [설치·사용 가이드](YuE2/START-HERE-ko.md) · [검증 범위와 남은 한계](YuE2/VALIDATION.md). Windows·NVIDIA 대상 시험 배포이며 모델 가중치는 CC BY-NC 4.0입니다.

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

이 저장소는 워크플로우, 설치 도우미, 자체 제작 Photoshop Bridge와 오디오 커터를 제공합니다. 오디오 커터 Windows ZIP에는 Python·FFmpeg 등 실행 구성요소가 포함되며 [별도 고지](Audio-Cutter/THIRD_PARTY_NOTICES.md)를 따릅니다. 모델, ComfyUI, 타사 커스텀 노드와 CUDA 커널은 포함하거나 재배포하지 않습니다. 각 파일은 안내된 원본 배포처에서 직접 받습니다.

## 제작

- 기획·테스트: [너무바쁜베짱이](https://www.youtube.com/@toobusyAI)
- GitHub: [nicekriss](https://github.com/nicekriss)

이 저장소의 자체 제작 워크플로우·문서·설치 스크립트는 [MIT License](LICENSE)로 배포합니다. 타사 구성요소에는 각 원저작자의 라이선스가 적용됩니다.

# 2BZ ComfyUI Workflows

너무바쁜베짱이(2BZ)가 실제 제작과 비교 테스트에 사용한 ComfyUI 워크플로우를 배포합니다.

## FastH3 + USDU Video Restore

기존 영상을 약 1MP로 정규화한 뒤 MiniMax H3 Fast 모델과 USDU 타일 복원으로 2배 확대하는 워크플로우입니다. 타일 크기는 정규화된 입력 크기에 자동으로 맞춥니다. FHD 고정 출력은 아닙니다.

**[최신 배포 ZIP 다운로드](https://github.com/nicekriss/2BZ-ComfyUI-Workflows/releases/latest)**

- 기본 복원 강도: `denoise 0.25`
- 기본 출력 배율: `2.0x` (1376×768 정규화 시 2752×1536)
- 기본 프롬프트: 인종·성별을 지정하지 않는 범용 복원 지시 + 선택 추가 묘사
- 권장 입력 길이: 약 5초
- 기존 영상 실측 환경: RTX 3090 24GB. v1.1.1 범용 프롬프트의 새 영상 품질 비교는 미실시.
- 상세 설치법: [FastH3-USDU/README.md](FastH3-USDU/README.md)

## 주의

이 저장소는 워크플로우와 설치 보조 스크립트만 제공합니다. 모델, ComfyUI, 타사 커스텀 노드와 CUDA 커널은 포함하거나 재배포하지 않습니다. 각 파일은 안내된 원본 배포처에서 직접 받습니다.

## 제작

- 기획·테스트: [너무바쁜베짱이](https://www.youtube.com/@toobusyAI)
- GitHub: [nicekriss](https://github.com/nicekriss)

이 저장소의 자체 제작 워크플로우·문서·설치 스크립트는 [MIT License](LICENSE)로 배포합니다. 타사 구성요소에는 각 원저작자의 라이선스가 적용됩니다.

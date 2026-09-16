# 2BZ Photoshop AI (SD-PPP)

포토샵에서 그린 선화를 ComfyUI로 채색하고 결과를 포토샵 레이어로 되돌려받는 구성과, 그 환경을 잡아주는 설치 도우미입니다.
설치 안내는 [START-HERE-ko.md](START-HERE-ko.md)를 보세요.

## 구성

| 파일 | 역할 |
|---|---|
| `설치하기.bat` / `install.ps1` | 설치 도우미 (PC 점검 → 노드 → 모델 → 워크플로우 → 플러그인 → 연결 확인) |
| `manifest.json` | 설치할 노드 커밋·모델 URL·SHA256·패치 해시를 고정한 목록 |
| `tools\patch-sdppp-focus.ps1` | SD-PPP 입력창 포커스 패치 (해시가 일치할 때만 적용, `-Restore`로 복원) |
| `tools\build-pack.ps1` | 워크플로우를 배포용으로 정리·검사 (제작자용) |
| `workflows\2BZ_Photoshop_Sketch_Color.json` | 선화 채색 워크플로우 (t2i / i2i 전환, LoRA 강도 조절) |

옵션: `install.ps1 -CheckOnly`(점검만), `-ComfyPath`, `-ModelsPath`.

## 설치되는 것

- 커스텀 노드: [sd-ppp](https://github.com/zombieyang/sd-ppp) (BSD-3-Clause), [KJNodes](https://github.com/kijai/ComfyUI-KJNodes) (GPL-3.0) — 각 저장소에서 검증된 커밋으로 받습니다
- 모델: Illustrious 계열 체크포인트, anytest v4 ControlNet, 붓터치 LoRA — 원본 배포처에서 직접 받고 SHA256을 확인합니다
- Photoshop 플러그인: sd-ppp 노드에 포함된 CCX를 Creative Cloud로 설치합니다

이 저장소는 플러그인·노드·모델 파일을 포함하거나 재배포하지 않습니다.

## 입력창 포커스 패치에 대해

SD-PPP 2.0.0에서 패널 입력창의 글자가 유지되지 않는 문제가 있습니다.
설치 도우미는 설치된 플러그인 파일이 **검증한 해시와 정확히 일치할 때만** 해당 호출을 제거하고, 원본을 백업한 뒤 결과 해시까지 확인합니다.
다른 버전에는 손대지 않습니다. `-Restore`로 언제든 원래대로 되돌릴 수 있습니다.

## 버전 고정

노드와 플러그인은 `manifest.json`에 적힌 커밋으로 고정해 설치합니다. 플러그인은 파일로 직접 설치하므로 Adobe 쪽에서 자동 갱신되지 않습니다.
사용자가 ComfyUI Manager로 sd-ppp를 업데이트하면 고정이 풀리고 포커스 패치도 무효가 됩니다. 이 경우 설치 도우미를 다시 실행하면 복구됩니다.

## 검증 범위

- 확인한 환경: Windows 11, RTX 3090 24GB, Photoshop 2026, ComfyUI v0.35.1 (Comfy Desktop)
- **8GB 그래픽카드에서 Photoshop을 켠 채 사용하는 조건은 아직 검증하지 않았습니다.**
- 손·얼굴 보정, 타일 업스케일은 이 배포에 포함되지 않습니다.

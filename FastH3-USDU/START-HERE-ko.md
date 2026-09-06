# 처음 시작하기 · v1.2.1

**Windows / NVIDIA용 설치 패키지. 깨끗한 PC에서 새 설치기로 전체 설치·렌더 검증은 아직 미완료입니다.**

## 0. 어디서 받고, 어디에 풀까요?

**[설치기 다운로드 페이지 · v1.2.1](https://github.com/nicekriss/2BZ-ComfyUI-Workflows/releases/tag/v1.2.1)**를 엽니다. Assets에서 `2BZ-FastH3-USDU-installer-v1.2.1.zip`을 받으세요.
검색으로 찾는다면 GitHub에서 `nicekriss/2BZ-ComfyUI-Workflows` → README의 설치 ZIP 링크를 누릅니다. 촬영은 위 버전 지정 링크, 항상 최신 안내는 https://github.com/nicekriss/2BZ-ComfyUI-Workflows/releases/latest 를 사용하세요. `Source code (zip)`은 설치 패키지가 아닙니다.
다운로드한 ZIP 우클릭 → 모두 압축 풀기 → 예: `C:\AI-Setup\FastH3-USDU\`에 풉니다. **custom_nodes에 ZIP 전체를 넣지 않습니다.**
압축 푼 폴더에 이 문서, `Install-SolAttn-MiniMax.bat`, `Install-USDU-H3.bat`, `2BZ_FastH3_USDU.json`이 함께 보여야 합니다. BAT만 따로 옮기지 마세요.
Windows가 실행을 차단하면 배포 출처·파일명이 맞는지 먼저 확인하세요. 보안 기능을 일괄 해제하지 말고 경고 화면을 오류 제보에 첨부하세요.

## 네 단계 완료 기준

| 단계 | 정상으로 볼 수 있는 표시 | 실패 시 |
|---|---|---|
| 다운로드·압축 해제 | 지정 ZIP 이름, BAT·PS1·PY·JSON·문서가 같은 폴더에 있음 | Source code ZIP이나 BAT 단독 다운로드인지 확인 |
| 설치기 실행 | 어텐션 `DEPENDENCIES READY`, USDU `USDU INSTALLED` 또는 `already installed`, 끝에 오류 없음 | 창의 마지막 오류와 설치 로그 보관 |
| ComfyUI 재실행 | 아래 Check-ComfyUI 검사와 로더/노드 확인 통과 | 누락 노드는 단계 3, 모델은 단계 4, 서버 연결 오류는 URL 확인 |
| 짧은 실제 실행 | 오류 없이 저장 노드에 새 결과, mp4 재생·길이·음성 확인 | 워크플로우·전체 traceback·로그로 제보 |

위 네 단계가 모두 성공해야 **그 환경에서 설치부터 첫 실행까지 성공**한 것입니다. 화질과 VSA 가속 성공은 별도 판정입니다.

## 1. 준비

ZIP을 완전히 압축 해제하세요. ComfyUI와 Git for Windows가 필요합니다. 모델은 별도 다운로드(약 41GB)이며 백업·영상 출력 공간도 필요합니다.
워크플로우를 저장하고 ComfyUI를 종료하세요. Desktop은 해당 인스턴스를 Stop합니다.
선택할 폴더는 앱 프로그램 폴더가 아니라 `main.py`가 있는 실제 ComfyUI 폴더입니다. 포터블 최상위 폴더도 선택 가능합니다.

## 2. 어텐션 준비

`Install-SolAttn-MiniMax.bat` → ComfyUI 폴더 선택 → 경로·변경 내용 확인 후 OK.

- 검증한 SolAttn v5 파일을 원본에서 다운로드하고 해시를 확인합니다.
- 작은 CUDA 검사가 실패하면 Kitchen 0.2.32만 백업 후 설치합니다. Torch는 변경하지 않습니다.
- **H3 코어 파일 2개에 게이트 로딩 패치를 적용할 수 있습니다.** 아래 호환성 제한을 읽으세요.
- `DEPENDENCIES READY`는 어텐션 준비 완료이지 USDU·모델·전체 렌더 준비 완료가 아닙니다.

Python은 .venv, venv, 포터블 python_embeded에서 찾으며 모호하면 직접 선택합니다. 일반 시스템 Python이 아니라 해당 ComfyUI 실행 Python이어야 합니다.

## 3. USDU 준비

`Install-USDU-H3.bat` → 같은 ComfyUI 폴더 선택 → 확인.

검증한 H3 포크와 하위 저장소를 고정 commit으로 설치합니다. Git이 필요하며 모델이나 pip 패키지는 받지 않습니다. 기존 다른 USDU Guider 또는 수정된 설치본과 충돌하면 덮어쓰지 않고 중단합니다. Manager에서 기존 팩 상태를 확인하고 사용자 폴더를 임의로 삭제하지 마세요.
하위 저장소가 비었다면 기존 USDU 설치 폴더에서 `git submodule update --init --recursive` 후 재검사하세요. import 시 자동 다운로드에 의존하지 않습니다.

## 4. 모델과 영상

[README.md](README.md)의 모델 4개를 표의 폴더에 넣으세요. 이미 등록된 공유 모델 폴더를 사용해도 되며 중복 다운로드할 필요는 없습니다.
ComfyUI 재시작 → `2BZ_FastH3_USDU.json` 드래그 → 로더 4개 확인 → 입력 영상 선택.
개인 샘플 영상은 포함하지 않았으므로 **입력 영상은 반드시 직접 선택**합니다. 업스케일 모델은 공식 `RealESRGAN_x2plus.pth`로 통일했습니다.

### ComfyUI 실행 후 무엇을 확인하나요?

1. ComfyUI가 열린 뒤 `Check-ComfyUI.bat`을 실행하고 **지금 사용하는 ComfyUI 주소**를 입력합니다. 예: `http://127.0.0.1:8188`. Desktop의 실제 포트는 8189 등으로 다를 수 있으니 추측하지 마세요. 주소를 모르면 Desktop의 해당 서버 연결/로그에서 확인하세요.
2. `SERVER READY`와 모델 4개 `MODEL LISTED`가 나와야 서버가 필요한 노드명·모델명을 인식한 상태입니다. 파일 무결성이나 전체 모델 로딩 완료를 뜻하지는 않습니다.
3. 캔버스에서 Unknown/Missing Node 경고가 없어야 하고, 모델 로더 4개가 위 파일을 가리켜야 합니다. **붉은색 노드 자체는 오류가 아닙니다.** 커스텀 노드임을 표시한 색입니다.
4. 입력 영상 선택 후 미리보기가 나오는지 확인합니다. 추가 프롬프트는 비워도 됩니다.
5. 짧은 영상 실행 성공을 확인합니다. 화면에 남은 과거 결과가 아니라 이번 실행의 새 파일인지 확인하세요.

모델을 하위 폴더에 넣었다면 자동 검사가 기본 경로를 못 찾을 수 있습니다. 로더에서 실제 하위 경로를 직접 선택하고 확인하세요.

## 5. 첫 실행

기본: 전체 영상 / 약 1MP·32배수 정규화 / 2배 / Euler·simple / 2스텝 / denoise 0.20.
정규화된 크기를 USDU 타일과 조건부여에 자동 연결합니다. FHD·2048 고정 출력이 아닙니다.
처음에는 1초 안팎 별도 영상으로 확인하세요. 또는 '선택 · 구간 자르기'를 활성화하면 처음 22프레임만 처리합니다(기본 바이패스). 이후 바이패스로 복원해야 전체 영상이 처리됩니다.
예: 1376×768로 정규화된 입력은 2752×1536으로 출력됩니다. 1.5/1.8배로 바꾸면 크기와 속도도 달라져 이번 실측과 직접 비교하지 않습니다.
출력: `output/video/FastH3_USDU…mp4`. 얼굴·의상·움직임 변형을 직접 확인하세요.

## 호환성 제한

H3 코어 패치는 ComfyUI commit `7fd919f0caff66a52289ea5b19cb6eaca0da04ef`의 **변경 전/후 2파일 전체 해시**가 일치할 때만 지원합니다. 이미 확인된 패치는 재적용하지 않습니다.
`Unverified H3 source version`은 새 버전이 고장이라는 뜻이 아니라 이 설치기의 수정 대상으로 검증되지 않았다는 뜻입니다.
**무작정 최신/nightly 설치나 다운그레이드를 하지 마세요.** ComfyUI 버전과 설치 로그로 호환성 확인을 요청하세요. 모든 버전에 통하는 원클릭 설치기는 아닙니다.

`Check-Setup.bat`은 H3 소스 상태와 작은 CUDA 연산만 검사합니다. 전체 모델 로딩·VSA 실행·속도·화질 검사가 아닙니다.
실제 로그의 `VSA tiles`, gate 누락·커널 오류를 확인해야 합니다. USDU가 샘플링 로그를 숨기는 버전에서는 로그 부재만으로 미작동이라고 단정하지 마세요.

## 메모리 오류가 날 때

정상 실행되면 설정을 바꾸지 마세요. 이번 15초 비교의 FastH3 USDU는 OOM 두 번 후 선택적 메모리 추정 계수1.0으로 완료했습니다. 기본 그래프에는 추가 노드가 없으며 [MEMORY-ko.md](MEMORY-ko.md)에 정확한 연결과 원복을 설명했습니다. 길이만이 원인이라는 뜻은 아닙니다. 이전 30초 성공 사례도 있습니다.

## 복구·오류 보고

ComfyUI 종료 → `Restore-SolAttn-MiniMax.bat` → 같은 폴더/Python 선택. 백업된 H3 코어·Kitchen을 복구합니다. 설치 후 코어가 다시 수정됐으면 덮어쓰지 않고 중단합니다. SolAttn·USDU·모델은 남습니다.
로그·백업: `ComfyUI/user/2bz-solattn-installer/`.
설치 오류 시 변경한 Kitchen은 백업으로 복구를 시도합니다. 파일 잠금 등으로 실패하면 백업을 유지하고 종료 후 재시도하세요.
오류 마지막 줄·로그·ComfyUI/Python 경로를 함께 보내주세요.
제보 항목과 복사할 양식은 [REPORT-PROBLEM-ko.md](REPORT-PROBLEM-ko.md)에 있습니다. 파일은 검토 후 직접 전달하며 자동 업로드하지 않습니다.
촬영은 [RECORDING-ko.md](RECORDING-ko.md), 실측은 [BENCHMARK.md](BENCHMARK.md)를 참고하세요.

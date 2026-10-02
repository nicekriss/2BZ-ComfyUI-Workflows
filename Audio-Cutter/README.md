# 2BZ 오디오 커터 v0.6 · Night Session

노래를 원하는 길이로 나누고, 필요한 구간을 MP3로 저장하는 Windows 프로그램입니다. ComfyUI 없이 단독으로 실행합니다.

**[Windows ZIP 다운로드](https://github.com/nicekriss/2BZ-ComfyUI-Workflows/releases/download/audio-cutter-v0.6.0/2BZ-Audio-Cutter-v0.6.0-Windows-x64.zip)** · [릴리스 안내](https://github.com/nicekriss/2BZ-ComfyUI-Workflows/releases/tag/audio-cutter-v0.6.0)

## v0.6 디자인 업데이트

차콜 배경과 부드러운 글자색, 앰버 강조로 화면을 정리했습니다. 음악 화면의 구간 목록은 가로로 넓히고 작은 창의 배치를 개선했습니다. 경계 조정·되돌리기·프로젝트 복구와 음악/뮤비 화면 전환을 확인했습니다.

## 시작하기

1. ZIP을 내려받아 쓰기 가능한 폴더에 **전체 압축 해제**합니다.
2. `2BZ Audio Cutter/2BZ Audio Cutter.exe`를 실행합니다. `_internal` 폴더도 함께 있어야 합니다.
3. 노래를 넣고 **전체 분할** 또는 **원하는 구간만**을 선택합니다.
4. 파형에서 경계를 조절하고 들어본 뒤 **MP3 저장**을 누릅니다. 저장 폴더가 열립니다.

Windows 10/11 64비트와 [Microsoft Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/)이 필요합니다. Python과 FFmpeg는 ZIP에 포함되어 있습니다. Windows 11에서 실행·저장을 검증했습니다. 실행파일은 코드 서명이 되어 있지 않습니다.

## 음악 자르기

- 매번 간단한 음악 화면으로 시작합니다.
- 전체 곡을 지정한 초 단위로 분할합니다. 경계를 조절하면 이웃 구간도 맞춰집니다.
- 원하는 구간만 골라 담거나 반복해서 들어볼 수 있습니다.
- MP3 저장은 한 폴더에 음악 파일만 모읍니다. 원본 파일은 변경하지 않습니다.
- MP3는 고품질 재인코딩합니다. 속도·볼륨·페이드를 자동으로 바꾸지 않습니다.

## 뮤비 프로젝트 (선택 기능)

상단 **뮤비 프로젝트**를 누르면 현재 구간을 그대로 이어서 장면별 레퍼런스 이미지·시작/끝 키프레임·프롬프트를 준비합니다.

- 공통 자료함: 이미지 이름·캐릭터/의상/배경 분류·검색·재사용
- 블록 나눠 복제, 이전 장면 자료 가져오기
- 준비 중/생성 대기/생성 완료 상태와 결과 영상 미리보기
- 결과 영상의 마지막 프레임을 다음 장면 시작 이미지로 연결
- 장면 꾸러미 저장: 장면별 `업로드` 폴더에 음악·이미지, 그 옆에 프롬프트·결과 영상

음악 화면으로 돌아가도 장면 자료는 유지됩니다. 외부 생성 사이트의 업로드·생성·상태 동기화는 수행하지 않습니다.

## 저장과 복구

- 편집은 자동 저장됩니다. 상단 저장 완료 표시를 확인하세요.
- 재실행 후 최근 작업의 **이어 작업하기**를 눌러 복구합니다.
- 자동 저장 위치: `%LOCALAPPDATA%/2BZ-Audio-Cutter/recovery`
- 다른 PC 이동·백업: 뮤비 프로젝트 화면에서 **프로젝트 저장**. `.2bz` 하나에 음악·이미지·결과 영상·구간·프롬프트를 담습니다.
- 프로젝트는 EXE 옆 `projects`, 음악/꾸러미는 `exports`에 새 파일로 저장됩니다.
- 이미지 장당 32 MB, 음악·영상 파일당 512 MB, 프로젝트 총 1 GB까지 지원합니다.

## 개발·검증

Python 3.13 + `requirements-desktop.txt`, PATH에 FFmpeg/ffprobe가 필요합니다.

```powershell
python -m pip install -r requirements-desktop.txt
python desktop.py
python -m unittest test_projects
node test_segments.cjs
python build_desktop.py --work-dir C:\build\2bz-audio-cutter
```

음악 전용 내보내기, 장면 꾸러미, 프로젝트 저장·복구, 경계 계산, 마지막 프레임 추출을 검사했습니다. 실제 곡의 17개 MP3 저장과 Windows EXE 시작 화면을 확인했습니다. 모든 Windows 환경에서 검증된 것은 아닙니다.

자체 제작 코드는 저장소의 [MIT License](../LICENSE)를 따릅니다. 포함된 구성요소의 고지와 소스 위치는 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 및 ZIP의 `licenses`를 확인하세요.

제작: [너무바쁜베짱이](https://www.youtube.com/@toobusyAI)

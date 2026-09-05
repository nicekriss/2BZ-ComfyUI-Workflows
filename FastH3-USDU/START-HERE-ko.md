# 메인컴 테스트용 설치기 v1.2.0-rc1

1. ZIP을 완전히 압축 해제합니다. ZIP 안에서 바로 실행하지 마세요.
2. 설치 대상 ComfyUI를 종료합니다. Desktop은 해당 인스턴스의 Stop을 누르세요.
3. `Install-SolAttn-MiniMax.bat`을 더블클릭합니다.
4. 메인컴 ComfyUI 폴더를 선택합니다. `main.py`가 있는 폴더 또는 포터블 최상위 폴더를 선택할 수 있습니다.
5. 표시되는 ComfyUI와 Python 경로가 맞으면 OK를 누릅니다.
6. `SUCCESS`가 나오면 ComfyUI를 다시 실행하고 워크플로우 JSON을 불러옵니다.

Python은 `.venv`, `venv`, 포터블 `python_embeded`에서 찾습니다. 하나로 결정되지 않으면 파일 선택 창이 뜹니다. 설치 폴더에 Python이 없는 특수 환경은 실제 실행에 쓰는 python.exe를 선택해야 합니다.

## 자동으로 처리하는 것

- GPU/BF16/ComfyUI API 사전 검사
- 현재 VSA CUDA 실행이 성공하면 설치된 comfy-kitchen 유지
- 실패하면 기존 comfy-kitchen 파일 전체를 백업하고 공식 `0.2.32` wheel만 설치
- Torch나 다른 패키지는 변경하지 않음 (`--no-deps`)
- VSA CUDA 재검사, SolAttn v5 원본 다운로드 및 고정 SHA-256 확인
- 변경 후 오류 발생 시 기존 comfy-kitchen 파일 자동 복구

패키지 백업과 로그는 선택한 `ComfyUI/user/2bz-solattn-installer/`에 남습니다. 인터넷 연결이 필요하며, 휠 다운로드는 약 49MB입니다. 기존 패키지 백업 공간도 필요합니다.

## 되돌리기

ComfyUI를 종료하고 `Restore-SolAttn-MiniMax.bat` 실행 → 같은 ComfyUI 폴더와 Python 선택. 마지막 백업의 comfy-kitchen을 복구합니다. SolAttn 노드 파일은 남겨두며 자동 삭제하지 않습니다. 복구 후 ComfyUI를 재시작하세요.

기존 SolAttn 파일이 검증된 v5와 다르면 덮어쓰지 않고 중단합니다. 실패 로그를 확인하세요. 파일이 잠겨 복구가 실패한 경우에도 백업은 남습니다. ComfyUI를 완전히 종료한 뒤 Restore를 다시 실행하세요.

## 영상 실행 전

이 설치기는 어텐션 의존성만 준비합니다. USDU H3 포크와 모델은 README대로 별도 설치해야 합니다. 업스케일 모델은 로더에서 실제 설치 파일을 선택하세요.

`VSA (FastVideo)` 모드를 유지하고 실제 실행 로그에서 `VSA tiles` 및 fallback/커널 오류 여부를 확인하세요. `SUCCESS`는 작은 CUDA 테스트 통과이며 전체 H3 모델 속도·화질 검증을 뜻하지 않습니다.

이 버전은 메인컴 검증 전 테스트 배포본입니다. 격리된 RTX 3090 환경에서 설치 성공 경로, 수동 복구, 의도적 오류 발생 후 자동 복구를 검증했습니다. 메인컴 환경의 결과는 아직 확인하지 않았습니다.

동봉 워크플로우의 버전은 v1.1.1입니다. 캔버스 설치 메모의 ‘자동 업그레이드 없음’은 이전 설치기 설명이며, 이 테스트 설치기의 동작은 이 문서를 기준으로 확인하세요.

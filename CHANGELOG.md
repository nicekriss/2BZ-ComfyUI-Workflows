# Changelog

## v1.2.1 — 2026-09-07

- Added four direct model download links and destination folders to the workflow's MarkdownNote.
- Added an English workflow and English installation/support guide; Korean and English graphs have identical execution settings and connections.
- Moved the latest three-way result table into a visible, dedicated group. Final choice remains FastH3 + USDU.
- Updated the recording sequence to load the workflow before downloading models. Installer logic and render settings are unchanged from v1.2.0.
- Verified both graphs, layout, live-canvas note contents and download URL responses. Clean-PC end-to-end rendering remains unverified.

## v1.2.0 — 2026-09-07

- Latest download now points to the installer package, not the older v1.1.1 release.
- Defaults aligned to the latest comparison: 2x / 2 steps / denoise0.20; same automatic source-normalized tile sizing.
- Updated three-way timings and user's final selection: FastH3 USDU; corrected single-node path completes but showed more distortion in user review.
- Optional OOM memory-estimate instructions, failures and unverified causal claims disclosed; no new mandatory node or installer behavior change.
- Beginner installation, success checks, recording and error-report instructions refreshed. Clean-PC end-to-end installation and simultaneous recording remain unverified.

## v1.2.0-rc2 — 2026-09-06 · public candidate

- Failed latent path removed; 27-node USDU graph, 1.8x / 2 steps / .25 and summary included.
- Official x2plus filename; private input selection cleared.
- Fingerprinted H3 gate patch, backups and guarded restore; unknown versions refused.
- Pinned USDU/submodule installer, beginner and recording guides.
- Clean-PC end-to-end install remains unverified; published as a release candidate for the documented installation walkthrough.

## v1.1.1 — 2026-09-05

- 현재 캔버스 26노드·29링크를 반영하고 범용 기본 프롬프트 + 선택 추가 묘사로 수정
- 실제 2배 출력·2스텝과 맞지 않던 설명 및 인종 지정 필수 안내 정정
- VSA CUDA chunked 경로 검사, 작은 커널 실행 테스트, 원본 SHA-256 확인 추가
- 패키지 자동 업데이트 및 기존 다른 노드 파일 덮어쓰기 제거
- 로컬 0.2.31 실패/격리된 공식 0.2.32 CUDA 검사 통과 기록. 새 프롬프트 영상 품질 비교 미실시

## v1.1.0 — 2026-09-04

- FastH3 + USDU 영상 복원 워크플로우 공개
- 입력 비율 및 타일 해상도 자동 연결
- 약 1MP 정규화와 1.4배 출력 기본값
- Sol-Attn 원클릭 설치기 및 커널 검사 추가

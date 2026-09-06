# 최종 선택: FastH3 + USDU

동일 소스 앞 15초 / 2752×1536 / 24fps / 2 steps / denoise 0.20.

| 방식 | 성공 실행 시간 |
|---|---:|
| 일반 H3 + 4-step Turbo LoRA / USDU | 96분 37초 |
| FastH3 / USDU | 48분 40초 |
| FastH3 / MMH3 단일 노드 | 47분 36초 |

이번 테스트에서 FastH3 구성이 약 2배 빨랐습니다. 각 1회 성공 실행이며 VSA 단독 효과를 분리한 값은 아닙니다.
단일 노드는 약 1분 빨랐지만 사용자 검토에서 더 망가지는 부분이 있어, 기존 USDU를 최종 채택했습니다.
초기 bilinear latent 실패와 후속 픽셀 SR 기반 단일 노드 비교를 혼동하지 마세요.

FastH3 USDU는 OOM 두 번 후 memory factor 1.0으로 보완한 실행입니다.
실패 시간은 위 표에서 제외했습니다. 길이만이 원인이라고 확정하지 않았습니다.
배포 기본에는 그 선택 노드가 없습니다. OOM 대응은 MEMORY-ko.md 참고.

실측은 로컬 RealESRGAN_x2.pth, 배포는 공식 x2plus 파일을 사용합니다. 동일성 미검증으로 그대로 재현되는 시간을 보장하지 않습니다.
4070 Ti SUPER 16GB / RAM 32GB에서도 기존 USDU 성공(사용자 확인). 이번 15초 표는 RTX 3090 24GB / RAM 64GB입니다.
신규 PC 전체 설치·렌더와 녹화 동시 실행은 별도 미검증. 자세한 조건은 BENCHMARK.md.

# OOM일 때만: 선택적 메모리 추정 보완

정상 실행되면 변경하지 마세요. 이 노드는 기본 배포 그래프의 필수 의존성이 아닙니다.

## 이번에 확인한 것

RTX 3090 24GB에서 같은 15초·2배 FastH3 USDU를 두 번 실행하다 추가 6.75GiB 할당에 실패했습니다. 이후 기존 KJNodes의 `ModelMemoryUsageFactorOverride`를 사용한 실행은 완료했습니다.
H3 기본 추정 계수 0.114 대신 1.0을 사용했습니다. 실제 메모리를 9배 쓰거나 화질을 낮추는 옵션이 아니라, ComfyUI의 샘플링 메모리 추정과 오프로딩 판단에 영향을 주는 값입니다. 검사한 구현은 준비 단계 이후 기본값을 복구합니다.
소스·출력 크기·프레임·모델·steps·denoise는 바꾸지 않았습니다.

**긴 영상만이 원인이라고 확정하지 않았습니다.** 사용자는 이전에 30초도 성공했습니다. 실행 당시 VRAM/RAM, 타일·출력 크기, 모델 상주 상태가 다를 수 있으며 이 보완이 유일한 성공 원인이었는지도 통제 검증하지 않았습니다.

## 적용 방법

1. 먼저 워크플로우를 별도 저장하고, 실행 중 작업을 끝냅니다. 모델을 내릴 때는 ComfyUI의 정상 메모리 해제 기능을 사용하세요. 다른 프로그램을 강제 종료하지 마세요.
2. [ComfyUI-KJNodes](https://github.com/kijai/ComfyUI-KJNodes)가 없다면 Manager에서 정확한 팩을 확인해 설치하고 ComfyUI를 재시작합니다. 이 ZIP은 KJNodes를 자동 설치하지 않습니다.
3. 노드 검색에서 `ModelMemoryUsageFactorOverride`를 추가하고 `memory_usage_factor`를 **1.0**으로 설정합니다.
4. `SolAttnMiniMax`의 MODEL 출력을 새 노드의 MODEL 입력에 연결합니다.
5. 새 노드의 MODEL 출력을 **BasicGuider.model과 BasicScheduler.model 두 곳 모두**에 연결합니다. 기존 SolAttn 직결 두 선은 새 연결로 교체합니다.
6. 나머지 조건은 그대로 두고 짧은 테스트부터 실행합니다. 기본 모델 로더나 VAE에 연결하는 노드가 아닙니다.

이렇게 해도 실패하면 반복 실행만 하지 말고 REPORT-PROBLEM-ko.md의 정보와 전체 OOM 로그를 보내주세요. 긴 영상에는 타일의 시간축 부담도 있으며, 특정 길이·GPU 용량의 성공을 보장하지 않습니다.

원복은 새 노드를 제거하고 SolAttn의 MODEL 출력을 BasicGuider와 BasicScheduler로 다시 직결합니다.

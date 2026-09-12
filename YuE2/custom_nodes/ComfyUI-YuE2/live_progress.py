"""Read worker output without blocking the node's cancellation checks."""
import re
import time


LABELS = {
    "Resolving model files": "모델 경로 확인",
    "Verifying model files": "모델 파일 검증",
    "Loading model": "모델 로딩",
    "Planning score": "악보 계획",
    "Generating song": "음악 생성",
    "Synthesizing audio": "오디오 합성",
    "Loading audio decoder": "오디오 디코더 로딩",
    "Decoding audio": "오디오 디코딩",
    "Saving audio": "오디오 저장",
}
STAGE = re.compile(r"^\[YuE2\] (Starting|Running|Completed|Failed|Cancelled|Finished \(generation limit reached\)) ([^:]+): (.*)$")
COUNT = re.compile(r"(\d+)/(\d+) (steps|chunks)")


def display_status(phase, detail):
    label = LABELS.get(phase, phase)
    elapsed = re.search(r"elapsed ([\d.]+)s", detail)
    heading = label + (f" · {float(elapsed[1]):.0f}초" if elapsed else "")
    tokens = re.search(r"(\d+) tokens", detail)
    if tokens:
        rate = re.search(r"([\d.]+) tokens/s", detail)
        return heading + f"\n{int(tokens[1]):,} 토큰" + (f" · {rate[1]}/s" if rate else "")
    count = COUNT.search(detail)
    if count:
        value, total, unit = count.groups()
        label = "단계" if unit == "steps" else "구간"
        return heading + f"\n{value}/{total} {label}"
    return heading


class LiveProgress:
    def __init__(self, reader, log, status, clock=time.monotonic):
        self.reader, self.log, self.status = reader, log, status
        self.clock = clock
        self.started = self.last_update = clock()
        self.pending = ""
        self.current = "실행 환경 준비 중"
        self.phase = None
        self.progress = None
        self.log("[YuE2] 실행 환경 준비 중 — 모델을 불러오는 동안에도 진행 상태를 표시합니다.")
        self.status(self.current, None, True)

    def poll(self, final=False):
        self.pending += self.reader.read()
        lines = self.pending.split("\n")
        self.pending = lines.pop()
        if final and self.pending:
            lines.append(self.pending)
            self.pending = ""
        for line in lines:
            line = line.rstrip("\r")
            if not line:
                continue
            self.log(line)
            match = STAGE.match(line)
            if match:
                state, phase, detail = match.groups()
                changed = phase != self.phase
                self.phase = phase
                self.current = display_status(phase, detail)
                if state == "Failed":
                    self.current = "실패 · " + self.current
                elif state == "Cancelled":
                    self.current = "취소 · " + self.current
                elif state.startswith("Finished"):
                    self.current = "생성 제한 도달 · " + self.current
                count = COUNT.search(detail)
                self.progress = tuple(map(int, count.groups()[:2])) if count else None
                self.status(self.current, self.progress, changed)
                self.last_update = self.clock()
        if not final and self.clock() - self.last_update >= 5:
            message = f"{self.current.splitlines()[0]}\n전체 경과 {self.clock() - self.started:.0f}초"
            self.log("[YuE2] " + message)
            self.status(message, self.progress, False)
            self.last_update = self.clock()

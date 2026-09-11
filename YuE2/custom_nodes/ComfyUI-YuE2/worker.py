import json
from pathlib import Path
import sys

import torch
from yue2 import YuE2Pipeline


def main():
    job = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    model = job["model"]
    pipeline = YuE2Pipeline.from_pretrained(model["model"], vae=model["vae"], device="cuda", backend="torch-eager", memory_budget_gib=model["memory_gib"], local_files_only=True)
    song = pipeline(**job["song"])
    song.save_artifacts(job["output"])
    metrics = {"duration_seconds": len(song.audio) / song.sample_rate, "truncated": song.truncated, "timing": song.timing, "peak_vram_gib": torch.cuda.max_memory_allocated() / 2**30}
    (Path(job["output"]) / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics), flush=True)


if __name__ == "__main__":
    main()

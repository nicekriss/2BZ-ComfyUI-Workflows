"""Import the actual loaders and optionally initialize a pipeline without weights."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--shared-site", required=True, type=Path)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--vae", type=Path)
    args = parser.parse_args()
    import torch
    import transformers
    import tokenizers
    import soundfile
    import numpy
    import yue2
    from yue2 import YuE2Pipeline, YuE2ForCausalLM, YuE2VAE
    from yue2.tokenization_yue2 import YuE2TextTokenizer
    expected = args.shared_site.resolve() / "torch"
    if Path(torch.__file__).resolve().parent != expected:
        raise RuntimeError(f"Torch is not shared from ComfyUI: {torch.__file__}")
    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
        raise RuntimeError("CUDA BF16 is unavailable")
    report = {"torch": torch.__version__, "torch_file": torch.__file__,
              "transformers": transformers.__version__, "numpy": numpy.__version__,
              "imports": ["yue2", "YuE2Pipeline", "YuE2ForCausalLM", "YuE2VAE",
                          "YuE2TextTokenizer", "tokenizers", "soundfile"]}
    if args.model:
        pipeline = YuE2Pipeline.from_pretrained(str(args.model), vae=str(args.vae), device="cuda",
                    backend="torch-eager", memory_budget_gib=12, local_files_only=True)
        assert pipeline._model is None and pipeline._vae is None
        report["preload"] = "tokenizer and model integrity verified; weights not loaded"
    print("RUNTIME READY " + json.dumps(report), flush=True)


if __name__ == "__main__":
    main()

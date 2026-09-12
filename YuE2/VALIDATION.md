# Validation · yue2-v0.1.0-rc4 (local candidate)

Tested on 2026-09-12 against `D:\ComfyUI (1)\ComfyUI`, Python 3.13.12,
RTX 4070 Ti SUPER 16GB, Torch 2.12.1+cu130. This candidate is not published yet.

## Current results

- Clean installation completed, including downloading and SHA256-checking all 11 model/config/tokenizer/license files (about 7.8GB).
- Actual imports passed: `yue2`, `YuE2Pipeline`, `YuE2ForCausalLM`, `YuE2VAE`, tokenizer, Transformers and soundfile. `torch.__file__` resolved to the existing ComfyUI `.venv`.
- Pipeline initialization passed with local tokenizer and model integrity verification, before weight loading. The packaged `--check-only` path passed too.
- 10.239s bounded inference passed with the shared Torch: 48kHz stereo, finite/non-silent, 65.07s including file verification, 6.852GiB peak allocated VRAM. This intentionally stopped at 256 semantic tokens; it is a smoke test, not a complete song.
- The installed `YuE2LocalGenerateWithABC` class then ran a default full-planning song through the real subprocess bridge and returned ComfyUI AUDIO `[1, 2, 2086976]`. Duration 43.479s, 48kHz stereo, no ABC or semantic truncation. Node call 137.70s; model pipeline 124.89s; peak allocated VRAM 7.851GiB. Host-side soundfile was not imported.
- Both FLAC files passed ffprobe and full `ffmpeg -v error` decode. Signal validity is verified; listening quality and every sung word have not been reviewed.
- ComfyUI core imports and KSampler, CheckpointLoaderSimple, CLIPTextEncode, VAEDecode, SaveImage passed. `comfy_extras.nodes_audio` also imported with the existing torchaudio.
- The actual ComfyUI `main.py --quick-test-for-ci` startup passed (exit 0) with installed custom nodes, including YuE2 and ABC Studio. This initializes the application and nodes then exits before serving HTTP.
- The actual Desktop-managed instance subsequently started on port 8188 using the requested ComfyUI `.venv`, ComfyUI 0.35.1 and Torch 2.12.1+cu130. Live object_info confirmed YuE2, ABC Studio, SaveAudio and the five basic image nodes listed above.
- Real queued workflow `YuE2LocalModel -> YuE2LocalGenerateWithABC -> SaveAudio` succeeded: prompt `d229e989-68b1-4de8-ae86-613477a94764`, history `success/completed`, 166.40s queue execution. Saved `YuE2/rc4-smoke_00001.flac`: 43.479s, 48kHz stereo, finite/non-silent, full decode passed, no truncation. Pipeline 145.19s; peak allocated VRAM 7.849GiB. All 186 host package records remained unchanged after this run.
- The final ZIP was extracted and its installer rerun successfully; existing packages/model files were reused without pip installation or host changes. Packaged bridge files exactly match the live installed files.
- Existing ComfyUI-LTXVideo fails to import `interleaved_freqs_cis` from the current ComfyUI core. The same failure was independently reproduced with only LTXVideo enabled and both YuE2 packages disabled. No LTX/core patch was made.
- All 186 original ComfyUI distributions retained their versions, locations and RECORD hashes after installation and runtime tests; `pip check` reports no broken requirements.
- 24 installer regression tests, Python compilation and PowerShell parsing passed. Fresh-install source layout, resolver restrictions, protected packages, target containment, failure auditing and dependency reuse are covered.

## Dependency result on this PC

| Package | ComfyUI before / after | YuE2 subprocess |
| --- | --- | --- |
| torch | 2.12.1+cu130 / unchanged | Same ComfyUI files |
| torchvision | 0.27.1+cu130 / unchanged | Shared |
| torchaudio | 2.11.0+cu130 / unchanged | Shared |
| xformers, triton | Not installed / unchanged | Not installed |
| transformers | 5.8.0 / unchanged | Private 4.57.6 |
| huggingface-hub | 1.14.0 / unchanged | Private 0.36.2 |
| numpy | 2.4.4 / unchanged | Shared 2.4.4 |
| safetensors | 0.8.0 / unchanged | Shared 0.8.0 |
| tokenizers | 0.22.2 / unchanged | Shared 0.22.2 |
| tiktoken, soundfile, accelerate | Not installed / unchanged | Added 0.12.0 / 0.13.1 / 1.13.0 |
| pynvml, nvidia-ml-py | 13.0.1 / 13.610.43, unchanged | Not installed by YuE2 |

No Torch API incompatibility was found in these runs, so no Torch version branch or model compatibility patch was needed. Optional fast/vLLM/triton backends were not tested. Portable Python, Python 3.10–3.12 and arbitrary other host dependency combinations remain unverified. The runtime shares ComfyUI Torch; it does not contain a separate Torch 2.10 environment.

## Historical rc1 results (previously documented, not rerun here)


Validated on 2026-09-11, Windows / RTX 3090 24GB / RAM 64GB / Python 3.13.12 / Torch 2.10.0+cu130.

- Created a fresh isolated runtime in a path containing Korean characters and a space, using the installed ComfyUI interpreter.
- Installed pinned YuE2 source and runtime packages; CUDA and imports passed.
- Installed `toobusy-abc-studio` alongside the official ComfyUI-YuE2 package for ABC workflow.
- Reused all 11 existing model/config/license files only after checking their SHA256 hashes.
- Downloaded pinned upstream source and a model config into new files; verified their hashes.
- Setup checker passed all model hashes and runtime CUDA imports.
- Seven focused tests passed: existing-file reuse, mismatch preservation, failed-download handling, range fallback, resume, package-preservation behavior, portable workflow links.
- PowerShell parser and Python compilation passed. Existing ComfyUI `pip check` remained clean.

The existing ComfyUI Desktop server was restarted with the packaged node code. `/object_info/YuE2LocalModel` confirmed registration. A Korean full-planning generation using the newly installed runtime completed successfully:

- Prompt ID: `cd5f0194-103a-4f5b-9a4e-c4708f23e561`; ComfyUI history reported success.
- Output: 39.999 seconds, 48kHz stereo FLAC, finite and non-silent.
- Model end-to-end time: 113.02 seconds; peak allocated VRAM: 7.852 GiB.
- Planning: 26.52s; semantic generation: 58.62s; NAR: 12.81s; VAE: 4.76s.
- Neither score nor semantic output was truncated.
- GitHub Windows CI passed the installer tests and PowerShell parser check.
- Workflow import sanity confirmed: `YuE2LocalModel`, `YuE2Song`, `YuE2LocalGenerateWithABC`, and `SaveAudio` appeared in `YuE2_Music.json` and were installed by workflow packaging.

## Scope limits

This is a release candidate, not a claim of universal one-click installation. A clean second PC, portable Python end-to-end installation, Python 3.10–3.12, other GPU models and interrupted multi-GB downloads against Hugging Face have not been tested. Resume behavior was tested with controlled HTTP responses. The 7.8GB weights were reused and verified instead of downloaded again. The runtime inherits ComfyUI's CUDA Torch and basic dependencies; arbitrary third-party package combinations are not covered.

The earlier local integration generated piano pop (67.72s), indie rock (142.72s), and Korean promotional rap (64.20s). These support the model-generation path; they are not substitutes for installer verification on other PCs. Audio signal checks do not verify every sung word or artistic quality.

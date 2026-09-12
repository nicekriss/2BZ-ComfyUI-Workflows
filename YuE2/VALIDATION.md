# Validation · yue2-v0.1.0-rc7

## rc7 SheetSage2 integration verification (2026-09-13)

- ABC Studio v0.4.0 uses official SheetSage2 and MERT2 pinned models in an isolated Python 3.11 / Torch 2.8.0 environment. The real ComfyUI runtime remains Python 3.13.12 / Torch 2.12.1+cu130.
- A 30.02-second source produced 52 vocal and 55 instrumental notes. A repeated 330.26-second input exercised two overlapping windows and produced both parts across the entire input.
- Actual browser import/application retained the original ABC; connected input/generation nodes showed a single editor shortcut. Resize, note placement, graph reload and clone were checked.
- Actual YuE2 score-conditioned generation completed twice; the reported failing excerpt rerun with the same style/lyrics/seed produced a 31.479-second result, no truncation. This is execution and a limited melody comparison, not a universal cover-quality guarantee.
- Standalone transcription installer succeeded on the real PC. The portable Python fallback was independently downloaded, hash checked, extracted and run (Python 3.11.16).
- The combined rc7 installer completed on the actual ComfyUI instance. All existing shared package versions, locations and RECORD hashes were unchanged; no host packages were added. Existing model files and both private runtimes were reused.
- The official v0.3.0 archive upgraded to v0.4.0 in a separate fixture, with an exact v0.3.0 backup outside custom_nodes. The live development tree was first checked against the union of known v0.3/v0.4 fingerprints, backed up and synchronized to the complete official release.
- 39 installer regression tests passed. ABC v0.4.0 archive: 87,305 bytes, SHA256 `28c8f548a688ff67930ca85ddbe9b406a9850866952b822d0370f922916688e5`.


## rc6 ABC Studio update verification (2026-09-12)

- ABC Studio v0.3.0 source archive: 71,278 bytes, SHA256 `697c53cee3810125fc5ec182d60dead3b77a46d55c2aa041fc536d835bc347ca`. Old v0.2.0 archive and normalized file fingerprints independently verified.
- 39 regression tests passed: official ABC upgrade/backup/rollback, clean install/reuse, custom-code preservation, corrupt download preservation, dependency-plan rejection and existing-package constraints.
- Ran the installer with the actual ComfyUI Python 3.13.12 / Torch 2.12.1+cu130: existing YuE2 bridge/runtime/model files and current ABC Studio reused; WAV roundtrip and 440Hz pYIN smoke test passed. All existing shared package records were unchanged, with no new packages needed on this PC.
- A separate clean Python 3.13 environment had no librosa/soundfile. The actual resolver/download/install path added 31 absent audio distributions, preserved all preexisting distributions, and passed 440Hz pYIN. This is a clean audio-dependency test, not a fresh GPU/ComfyUI installation.
- Actual running ComfyUI on port 8188 reported ABC audio available with no missing dependencies and an existing separation model. ABCScoreInput registered. This release changes installer behavior, not the already-tested generation bridge or ABC v0.3.0 runtime; no new full-song generation was performed for rc6.
- Extracted the installer ZIP and ran its complete entrypoint against a separate installation fixture containing the official v0.2.0 ABC archive, an existing rc5 bridge and references to the already-verified models/runtime. It installed v0.3.0, kept an intact v0.2.0 backup outside custom_nodes, and preserved the saved workflow byte-for-byte. No fixture ComfyUI server was started.
- The earlier manual live ABC deployment lacked test/CI files. Only those release metadata files were synchronized with the official v0.3.0 archive before installation, with the previous CI file backed up. Runtime code did not change.


## rc5 live progress verification (2026-09-12)

Same Windows / RTX 4070 Ti SUPER / Torch 2.12.1+cu130 environment below.

- Ran the installer against the existing rc4 installation: recognized bridge upgraded with a backup outside custom_nodes; setup, runtime, models, saved workflow and all 186 shared package records preserved.
- ComfyUI Desktop restarted with the same launch arguments. YuE2, ABC wrapper and basic ComfyUI nodes registered.
- Prompt `b8771d4b-3dcf-4800-8468-3bb158de22b0` completed successfully: 43.479s, 48kHz stereo FLAC, full ffmpeg decode passed.
- Captured 48 native progress text events. First status arrived at 0.014s; generated tokens, 32-step synthesis, chunk decoding and completion were received. Numeric synthesis progress was also received.
- ComfyUI console contained the same worker progress lines while inference was running.
- Separate browser test showed Korean preparation immediately after Run, then a compact two-line stage/tokens/speed display (for example music generation 25s, 415 tokens, 16.6/s). The user's existing canvas was not edited.
- 31 regression tests passed, including partial log lines, silent-worker heartbeats, truthful step totals, customized-code preservation and failed-upgrade rollback.

A later runtime audit detected 13 newly added audio-analysis distributions from concurrent ABC Studio development (an explicit librosa/soundfile installation). All original 186 distribution versions, locations and RECORD hashes remained unchanged. The rc5 installer itself added or changed no shared packages.

## rc4 installation and inference verification

Tested on 2026-09-12 against `D:\ComfyUI (1)\ComfyUI`, Python 3.13.12,
RTX 4070 Ti SUPER 16GB, Torch 2.12.1+cu130. This is a public release candidate; the tested scope is listed below.

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

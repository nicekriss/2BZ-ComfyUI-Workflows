# Validation · yue2-v0.1.0-rc11

## rc11 silent stretches and non-Korean consoles (2026-09-16)

- A viewer reported the window showing no progress after picking the ComfyUI and models folders. The cause of that report is not established. What is established is that rc10 printed one line there and then imported ComfyUI's Torch with nothing else on screen.
- Measured on this bench with a warm cache and an NVMe disk, `import torch` against the ComfyUI environment took 8.8 seconds. A cold cache or an antivirus scan makes it longer. Recording the installed package list and fetching a source archive were silent for the same reason.
- rc11 prints what it is doing at all three points. Verified by running `environment()` under the ComfyUI interpreter with timestamps: the notice appears at 09:08:33.086 and the Torch and GPU lines at 09:08:34.956, so the message precedes the work rather than following it.
- CI on the English Windows runner then exposed a real defect: on a cp1252 console every Korean line raised `UnicodeEncodeError` and killed the install, so the guidance meant to help was itself the crash. A Korean console encodes cp949 and handles Hangul, which is why this never appeared here. Reproduced locally with `PYTHONIOENCODING=cp1252` before fixing, and the same command passes afterwards.
- The installer now reconfigures its own stdout and stderr to UTF-8 rather than trusting the launcher's `-X utf8`. This also covers the Korean planning guard shipped in rc9, which carried the same exposure. Confirmed that Korean still renders through the launcher path and that a run with no UTF-8 mode and `PYTHONIOENCODING=cp1252` no longer dies.
- Installer tests: 39 pass, under both cp949 and cp1252.
- No functional change to installation itself. Existing runtimes, model weights and saved workflows remain reusable.



## rc10 RTX 50 field confirmation and key picker (2026-09-14)

- The rc9 fix is reported working by both commenters who hit the failure, on RTX 5060 Ti 16GB and RTX 5070 Ti 16GB. This confirmation arrived through YouTube comments; no RTX 50 card was exercised here, so it is user-reported rather than measured on this bench.
- ABC Studio v0.4.4 adds the key picker. Verified in a browser against a served copy, not a static file, because module imports do not run from a file snapshot. Opening a score sets the picker from its `K:` field; changing the key updates the status line, the `K:` header and the ABC body together.
- Pitch safety: a real 69-note two-voice score was cycled through `C`, `Eb`, `F#`, `C#m`, `none` and `Am`, reparsing after each change. Every pitch was unchanged each time. Changing the key relabels the signature and never transposes.
- The piano roll shading follows the chosen key while note positions stay put, confirmed on screen.
- ABC Studio tests: 5 JavaScript files and 5 Python files pass, including 5 new key tests. The module script inside `index.html` is not covered by that CI and was syntax-checked separately.


## rc10 installed package size (2026-09-14)

- ABC Studio v0.4.2 shipped four Aegukga demo MP3s under `docs/audio/`, assets for the GitHub Pages comparison player with no role in the node. `_install_abc` copies the whole tag archive into `custom_nodes`, so every installation carried about 20MB of documentation audio.
- v0.4.3 excludes `docs` from release archives with `/docs export-ignore`. The archive downloaded from codeload went from 18,242,956 bytes to 90,182 bytes, back to the 39 files v0.4.1 had, with no `docs` entries. Verified by downloading the published tag archive, not by inference.
- The Pages player is unaffected: `export-ignore` applies to `git archive` only, and Pages serves the `docs` path of `main` directly. Both the site and `audio/aegukga-original.mp3` still answer with HTTP 206 to a range request, so seeking still works.
- `git clone` and ComfyUI-Manager Git URL installs are unaffected.
- No functional change to the node or the installer beyond the pin.


## rc9 RTX 50 transcription fix (2026-09-14)

- Cause confirmed on the live installation. The SheetSage2 runtime carried `torch 2.8.0+cu126` whose architectures are `sm_61 sm_70 sm_75 sm_80 sm_86 sm_90`, while RTX 50 cards are `sm_120`. The same machine's ComfyUI already ran `torch 2.10.0+cu130` including `sm_120`, so the isolated runtime was installing an older CUDA than the host it sits beside.
- `torch 2.8.0+cu128` installed into a scratch Python 3.11 runtime reports `sm_61 sm_70 sm_75 sm_80 sm_86 sm_90 sm_100 sm_120`. It adds `sm_120` and keeps every architecture cu126 covered, so no currently supported card loses support.
- RTX 3090 (sm_86) executed a real CUDA kernel on that build: `matmul(64x64).sum() = 262144.0`.
- The new runtime check passed against that build and printed `{"torch": "2.8.0+cu128", "gpu": "NVIDIA GeForce RTX 3090", "arch": "sm_86"}`. The same check refused the existing cu126 runtime by name. Neither test modified the live installation.
- Console encoding: under a forced code page 949 console the Korean guidance rendered as mojibake; with the launcher's UTF-8 console setting it renders correctly.
- Not verified: no RTX 50 card was available. That `cu128` contains `sm_120` kernels is established; execution on an actual RTX 50 card is not.

## rc8 Windows status-file regression (2026-09-13)

- Reproduced WinError 5 using a real Windows reader holding status.json open. The worker now retries transient replacement failures and still reports persistent access failures.
- Four regression tests cover the Windows reader collision, complete JSON replacement, bounded retries and unrelated I/O errors.
- Live ComfyUI 0.35.1 / RTX 3090 / Torch 2.10.0+cu130: 30-second range analysis completed while status was polled every 200ms; returned ABC, 73 instrumental notes and audio previews. Vocal notes were zero for this sample; this test establishes execution success, not transcription fidelity.
- All 39 installer regression tests passed. A real official v0.4.0 archive upgraded to v0.4.1 with an exact v0.4.0 backup.
- No host dependency or model change. The worker fix applies to new jobs without restarting ComfyUI.


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

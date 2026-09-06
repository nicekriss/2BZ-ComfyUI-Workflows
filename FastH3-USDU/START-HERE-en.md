# FastH3 + USDU installer · v1.2.1

English workflow: **2BZ_FastH3_USDU_EN.json**. Korean: **2BZ_FastH3_USDU.json**. They have identical computation, model choices, prompts and settings; only the notes, node titles and group titles are translated.

## Download and extract

[Download v1.2.1](https://github.com/nicekriss/2BZ-ComfyUI-Workflows/releases/tag/v1.2.1) → Assets → **2BZ-FastH3-USDU-installer-v1.2.1.zip**. Do not choose Source code(zip).
Extract the entire ZIP into a writable local folder, for example `C:\AI-Setup\FastH3-USDU`. Do not put the whole ZIP folder into custom_nodes or move BAT files away from their PS1/Python companions.
Windows/NVIDIA SM80+ and BF16 are required. Git for Windows, ComfyUI and about41GB of models are separate. Keep room for backups and video outputs. Do not disable security protections globally if Windows warns; verify the release source and report the warning.

## Install the two node packs

1. Save work and stop your ComfyUI instance in Desktop or its normal launcher.
2. Run **Install-SolAttn-MiniMax.bat** and choose the actual ComfyUI folder containing main.py (or its portable parent). Confirm the displayed root and Python belong to that instance.
3. Run **Install-USDU-H3.bat**, choosing the same root. Git is required. This installs the pinned H3 USDU fork and submodule; conflicting or modified existing packs are preserved and installation stops.
4. Restart ComfyUI and drag **2BZ_FastH3_USDU_EN.json** onto its canvas. Do not queue it yet.

The attention installer verifies the original SolAttn v5 download and a small CUDA operation. If necessary it backs up Kitchen and installs0.2.32 without updating Torch. It may patch two H3 core files ONLY when their known before/after fingerprints match ComfyUI commit7fd919f0caff66a52289ea5b19cb6eaca0da04ef. Unknown or edited versions are refused. **Do not blindly upgrade/nightly/downgrade when this happens.** Report your version and installer log.

## Download models from the workflow

Use the **Download all4models here** Markdown note. Each link names a download and its destination under ComfyUI:

| Model | Folder |
|---|---|
| FastH3 VSA checkpoint | models/diffusion_models |
| Qwen3-VL H3 NVFP4 encoder | models/text_encoders |
| H3 Video VAE FP16 | models/vae |
| RealESRGAN_x2plus.pth | models/upscale_models |

Keep original filenames. Missing-model labels are expected until this step is complete. Configured shared-model directories also work. Refresh the model lists, select the downloaded files, and restart only if still not found. If using a subfolder, choose its actual path in the loader; the automatic check expects the default names. Use the video VAE, not an image VAE.

## How to know it worked

| Stage | Expected evidence |
|---|---|
| Extracted package | Both JSONs, BAT/PS1/Python files and this guide are present together |
| Attention install | DEPENDENCIES READY, no final error |
| USDU install | USDU INSTALLED or pinned revision already installed |
| Running backend | Check-ComfyUI.bat → actual localhost URL → SERVER READY and four MODEL LISTED messages |
| Canvas | No Unknown/Missing Node warning; four correct model selections; your input video selected |
| Real execution | A newly saved MP4 opens with expected duration, picture and original audio |

Desktop may use8189 instead of8188. Read the actual server address; do not guess. Red-colored nodes intentionally mark custom nodes and are not errors by themselves.
Check-Setup.bat only checks known H3 source and a small CUDA operation. Check-ComfyUI checks registered names, not file integrity, full model loading, speed or quality. DEPENDENCIES READY alone does not mean the whole workflow is ready.

## First render

Select your own video. Defaults: about1MP normalization,2x,2steps,Euler/simple,denoise0.20,VSA keep10%, full video with original audio. Output is not fixed FHD. A1376×768 normalized input produces2752×1536.
Try a separate short clip first. The optional trim node is bypassed; enable it to process the first22frames, then bypass it again for the whole input. Extra prompt can stay blank.
Output: `ComfyUI/output/video/FastH3_USDU…mp4`. Check the new output rather than an old preview. Faces, clothing and scene details can be regenerated, not merely sharpened.

## Results and limits

Same15seconds/2752×1536/24fps/2steps/.20 on RTX3090 24GB/RAM64GB: baseH3+TurboUSDU96m37s,FastH3USDU48m40s,FastH3single-node47m36s. One successful run each, with different cache states and implementations; not a VSA-only ablation. The user selected USDU because the single-node result showed more distortion for only about1minute saved.
FastH3USDU had two failed OOM attempts(2143.691s and2542.020s) before the reported successful2920.586s run with the optional memory override below. Including those failed full attempts totals126m46s(excluding setup/smoke/waiting). Duration alone was not established as the cause; the user previously completed30-second clips.
The benchmark used a local RealESRGAN_x2.pth, while this package selects officialx2plus; file identity is unverified. The default package does NOT include the optional override and is not an exact copy of that successful benchmark graph.
Existing4070 Ti SUPER16GB/RAM32GB upscaling success is user-reported. **Clean-PC end-to-end installation using this ZIP and simultaneous screen recording are unverified.** No universal time, memory or fidelity guarantee.

## Optional OOM recovery (not required by default)

If the workflow already works, leave it alone. Save a copy before changing wiring.
If needed, install [ComfyUI-KJNodes](https://github.com/kijai/ComfyUI-KJNodes) through Manager and restart normally. Add **ModelMemoryUsageFactorOverride**, set **memory_usage_factor=1.0**.
Connect **SolAttnMiniMax.MODEL → override.MODEL input → BOTH BasicGuider.model and BasicScheduler.model**. Replace both original direct connections. Do not connect it to the VAE.
This changes sampling memory estimation/offloading, not model weights or image quality settings. The inspected implementation restores the original factor after sampling preparation. It is not proof that this change alone caused success or fixes every OOM.
To undo, remove the override and reconnect SolAttn directly to both consumers. Do not repeatedly retry unchanged failed full renders or kill unrelated processes.

## Restore and report

Stop ComfyUI → Restore-SolAttn-MiniMax.bat → same root/Python. This restores backed-up H3/Kitchen files; later user edits are protected. SolAttn, USDU and models remain. Logs/backups: `ComfyUI/user/2bz-solattn-installer/`.
Report through [GitHub Issues](https://github.com/nicekriss/2BZ-ComfyUI-Workflows/issues). Review JSON/logs before sharing; redact credentials, private paths and footage. No automatic upload occurs.

```text
ZIP filename/version and release URL:
Windows / NVIDIA driver:
GPU / VRAM / system RAM:
ComfyUI Desktop, Portable or manual; BACKEND version:
Python / Torch / CUDA / comfy-kitchen versions (unknown is OK):
Failed stage and exact error:
Last successful step; previous success and subsequent changes:
Recording/other GPU workloads running:
Input width/height/fps/duration/frame count:
Normalization MP / scale / steps / denoise / seed:
VSA mode/keep/bypass; USDU batch/anchor/tiled decode:
Memory override used? Factor / KJNodes version:
First or repeated run; time; failed node:
Output size/duration/audio; problem timestamp:
```

Attach actual execution workflowJSON, complete traceback and nearby server log, readiness-check output and installer log. For OOM include VRAM/RAM usage at failure and settings of any longer clip that previously succeeded. For quality issues provide matching source/output crops and a public-safe short moving clip. Do not upload models or private footage.

For recording, capture installation and queue submission, then stop recording while waiting for inference; record results separately. Do not present an already-prepared PC as a verified clean install.
Repository scripts/docs are MIT; the bundled H3 core patch derives from GPL-3.0 ComfyUI (LICENSE-ComfyUI.txt). Third-party components keep their original licenses.

# Changes

## yue2-v0.1.0-rc8

- Pin ABC Studio v0.4.1: retry transient Windows status-file replacement failures during transcription.
- Preserve recognition and backup upgrades for official v0.4.0 installations.
- Existing runtimes, model weights and saved workflows remain reusable.

## yue2-v0.1.0-rc7

- Pin ABC Studio v0.4.0 with official SheetSage2/MERT2 transcription of instrumental and vocal melodies.
- Install a separate Python 3.11 / Torch 2.8.0 runtime; do not add audio packages to ComfyUI Python.
- Support whole-song analysis with overlapping windows, per-part previews, lossless unedited ABC transfer, and responsive editor fixes.
- Recognize and back up official ABC v0.2.0 and v0.3.0 installations during upgrade.

## yue2-v0.1.0-rc6

- Pin ABC Studio v0.3.0 and its verified archive hash; include song transcription and explicit instrument/vocal microphone routing.
- Upgrade recognized v0.2.0 installations with backup outside custom_nodes and rollback. Preserve current versions; stop on customized or unknown ABC files.
- Plan audio dependencies with every existing ComfyUI package constrained, reject replacements, download wheels first and add only absent packages without dependency resolution during installation.
- Verify host audio imports, WAV I/O and pYIN before reporting installation success. Keep YuE2 model/runtime and existing workflow settings.

## yue2-v0.1.0-rc5

- Relay worker output to the ComfyUI console while retaining each job's generation.log.
- Show native node progress text immediately, including five-second heartbeats during silent preparation.
- Report generated tokens for open-ended music generation and actual step/chunk progress for synthesis/decoding.
- Upgrade recognized rc4 bridges with backup and rollback; preserve customized code, setup, models, runtime and shared Torch.
- Fix the packaged workflow's stale rc3 download link and Torch 2.10-only label.

## yue2-v0.1.0-rc4

- Warn on Torch versions other than 2.10 and test real loader imports instead of refusing installation.
- Share ComfyUI CUDA Torch. Install only missing/incompatible additional packages into the subprocess runtime with resolver and source builds disabled; reject Torch/CUDA package targets.
- Record all ComfyUI package versions, locations and RECORD hashes before/after, including failed installations; fail with a warning on changes.
- Fix clean installation: pinned upstream source contains `src/yue2`, not a `ComfyUI-YuE2` node pack. Ship and install the repository subprocess bridge.
- Remove the bridge's host-side soundfile dependency, transfer audio through NumPy, and accept the ABC argument supplied by ABC Studio v0.2.0.
- Check actual model/VAE loader imports, shared Torch path, tokenizer and pipeline initialization before reporting readiness.
- Leave pynvml and nvidia-ml-py untouched. No separate Torch installation or Torch downgrade.

## yue2-v0.1.0-rc3

- `toobusy-abc-studio` is now pinned to release `v0.2.0` instead of tracking `main`, so two machines installing on different days get the same package.
- Every source archive download is checked against a pinned sha256. A half-written zip left by an interrupted run used to be reported as `VERIFIED` on its filename alone and installed as-is; it is now discarded and fetched again.
- Install flow now keeps pre-installed `ComfyUI-YuE2` and `toobusy-abc-studio` packages and installs only missing components.
- `YuE2_Music.json` now uses `YuE2LocalGenerateWithABC` with optional `abc` input for ABC Studio integration.
- Installer now installs official upstream ComfyUI-YuE2 source and `toobusy-abc-studio` package (separate node package) instead of local patched node copy.
- Check flow now validates YuE2, ABC Studio package, and new workflow file presence.

## yue2-v0.1.0-rc2

- Synchronize the packaged workflow notes with the current canvas installer guide.
- Link installation steps, folder selection, setup checks and troubleshooting directly from the workflow.
- Generation code and settings are unchanged; omit the author-PC installed status from the public copy.

## yue2-v0.1.0-rc1

- Add Windows folder-picker installer and isolated YuE2 runtime using existing ComfyUI CUDA Torch.
- Download pinned official source and model files with SHA256 verification and resumable partial downloads.
- Add three local music nodes, Korean promo-rap workflow, setup checker and Korean guide.
- Preserve existing node installations and mismatched model files instead of overwriting them.
- Scope first release to Torch 2.10.x; clean-machine and portable end-to-end coverage remains incomplete.

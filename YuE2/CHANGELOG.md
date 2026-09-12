# Changes

## yue2-v0.1.0-rc2

- `toobusy-abc-studio` is now pinned to release `v0.2.0` instead of tracking `main`, so two machines installing on different days get the same package.
- Every source archive download is checked against a pinned sha256. A half-written zip left by an interrupted run used to be reported as `VERIFIED` on its filename alone and installed as-is; it is now discarded and fetched again.
- Install flow now keeps pre-installed `ComfyUI-YuE2` and `toobusy-abc-studio` packages and installs only missing components.
- `YuE2_Music.json` now uses `YuE2LocalGenerateWithABC` with optional `abc` input for ABC Studio integration.
- Installer now installs official upstream ComfyUI-YuE2 source and `toobusy-abc-studio` package (separate node package) instead of local patched node copy.
- Check flow now validates YuE2, ABC Studio package, and new workflow file presence.

- Synchronize the packaged workflow notes with the current canvas installer guide.
- Link installation steps, folder selection, setup checks and troubleshooting directly from the workflow.
- Generation code and settings are unchanged; omit the author-PC installed status from the public copy.

## yue2-v0.1.0-rc1

- Add Windows folder-picker installer and isolated YuE2 runtime using existing ComfyUI CUDA Torch.
- Download pinned official source and model files with SHA256 verification and resumable partial downloads.
- Add three local music nodes, Korean promo-rap workflow, setup checker and Korean guide.
- Preserve existing node installations and mismatched model files instead of overwriting them.
- Scope first release to Torch 2.10.x; clean-machine and portable end-to-end coverage remains incomplete.

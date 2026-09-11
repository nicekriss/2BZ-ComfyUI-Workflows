# Validation · yue2-v0.1.0-rc1

Validated on 2026-09-11, Windows / RTX 3090 24GB / RAM 64GB / Python 3.13.12 / Torch 2.10.0+cu130.

- Created a fresh isolated runtime in a path containing Korean characters and a space, using the installed ComfyUI interpreter.
- Installed pinned YuE2 source and runtime packages; CUDA and imports passed.
- Reused all 11 existing model/config/license files only after checking their SHA256 hashes.
- Downloaded pinned upstream source and a model config into new files; verified their hashes.
- Setup checker passed all model hashes and runtime CUDA imports.
- Seven focused tests passed: existing-file reuse, mismatch preservation, failed-download handling, range fallback, resume, existing-node protection, portable workflow links.
- PowerShell parser and Python compilation passed. Existing ComfyUI `pip check` remained clean.

The existing ComfyUI Desktop server was restarted with the packaged node code. `/object_info/YuE2LocalModel` confirmed registration. A short Korean full-planning generation was queued against the newly installed runtime; final measurements are recorded below after completion.

## Scope limits

This is a release candidate, not a claim of universal one-click installation. A clean second PC, portable Python end-to-end installation, Python 3.10–3.12, other GPU models and interrupted multi-GB downloads against Hugging Face have not been tested. Resume behavior was tested with controlled HTTP responses. The 7.8GB weights were reused and verified instead of downloaded again. The runtime inherits ComfyUI's CUDA Torch and basic dependencies; arbitrary third-party package combinations are not covered.

The earlier local integration generated piano pop (67.72s), indie rock (142.72s), and Korean promotional rap (64.20s). These support the model-generation path; they are not substitutes for installer verification on other PCs. Audio signal checks do not verify every sung word or artistic quality.

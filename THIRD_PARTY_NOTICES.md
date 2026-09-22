# Third-Party Notices

This repository does not redistribute the following third-party models or custom-node source files. Its documentation and installer link to their original distribution locations.

- ComfyUI: https://github.com/Comfy-Org/ComfyUI
- Comfy-Kitchen and Sol-Attn contribution: https://github.com/Comfy-Org/comfy-kitchen/pull/117
- MiniMax H3 experimental model: https://huggingface.co/Kijai/MiniMax-H3-experimental
- MiniMax H3 text encoder and video VAE: https://huggingface.co/Comfy-Org/MiniMax-H3
- Ultimate SD Upscale Guider H3: https://github.com/lisitskyaa/ComfyUI_UltimateSDUpscaleGuider_H3
- Real-ESRGAN: https://github.com/xinntao/Real-ESRGAN

All trademarks, model weights, source code, and other third-party materials remain subject to their respective owners' terms and licenses.


## TooBusy AI Photoshop Bridge installer

The installer executable bundles Python, Tcl/Tk, requests, urllib3, certifi, charset-normalizer, idna, psutil and PyYAML using PyInstaller. The release ZIP includes their license notices in `licenses/`; the executable also embeds the collected notices. Model weights and third-party ComfyUI node packages are downloaded from upstream, not bundled. See `Photoshop-Bridge/installer/dependencies.json` for pinned sources and hashes. Photoshop, Creative Cloud and ComfyUI are separately installed products. This independently developed Bridge does not bundle SD-PPP.

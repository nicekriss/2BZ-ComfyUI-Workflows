# Third-party notices — 2BZ Audio Cutter v0.5

The application invokes FFmpeg/ffprobe as separate local processes. It also bundles the Python runtime and packages listed below using PyInstaller. No user songs, reference images, generated videos, saved projects, credentials, or recovery data are included in this release.

- Python 3.13.5: PSF License; https://www.python.org/downloads/release/python-3135/
- pywebview 6.2.1: BSD-3-Clause; https://github.com/r0x0r/pywebview
- pythonnet 3.2.0: MIT; https://github.com/pythonnet/pythonnet
- clr_loader 0.3.1: MIT; https://github.com/pythonnet/clr-loader
- PyInstaller 6.22.3: GPL with bootloader exception; https://github.com/pyinstaller/pyinstaller
- Supporting package licenses are copied from the build environment into the release ZIP's `licenses` directory.
- Microsoft WebView2 SDK loader/managed assemblies are included by pywebview. WebView2 Runtime is separately installed: https://developer.microsoft.com/microsoft-edge/webview2/

## FFmpeg

Bundled FFmpeg and ffprobe: `N-120970-g9ee7796c54-20250904`, Windows x64 GPL shared build from BtbN. FFmpeg has not been modified by this project. Its GPLv3 license and complete version/configuration output are included under `licenses/`.

- FFmpeg source matching the bundled revision: https://github.com/FFmpeg/FFmpeg/tree/9ee7796c540ce9cec3fdff0dd246de842228707b
- Source archive: https://github.com/FFmpeg/FFmpeg/archive/9ee7796c540ce9cec3fdff0dd246de842228707b.tar.gz
- Upstream build system, dependency recipes and source locations: https://github.com/BtbN/FFmpeg-Builds
- Build recipes as of 2025-09-03 (historical reference): https://github.com/BtbN/FFmpeg-Builds/tree/cbf8564182070dec8f8125127373c5fb3539a100

Each third-party component remains subject to its own license; the repository's MIT license does not replace those licenses.

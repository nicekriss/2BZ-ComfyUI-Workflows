import ctypes
import os
from pathlib import Path
import threading
import traceback

import webview

import app


class DesktopBridge:
    def __init__(self):
        self._window = None
        self._closing = False
        self._ready = False

    def close_ready(self):
        self._ready = True
        self._window.destroy()

    def close_cancel(self, message):
        self._closing = False
        ctypes.windll.user32.MessageBoxW(None, str(message), '2BZ 오디오 커터', 0x40)

    def close_failed(self, message):
        self._closing = False
        answer = ctypes.windll.user32.MessageBoxW(None, '자동 저장에 실패했습니다. 저장하지 않고 닫을까요?\n\n' + str(message), '2BZ 오디오 커터', 0x34)
        if answer == 6:
            self.close_ready()

    def _request_flush(self):
        try:
            self._window.run_js('if (typeof prepareClose === "function") { void prepareClose(); } else { void window.pywebview.api.close_ready(); }')
        except Exception:
            self.close_failed('종료 전 저장을 요청하지 못했습니다. 프로젝트 저장을 이용해주세요.')

    def on_closing(self):
        if self._ready:
            return True
        if app.EXPORT_LOCK.locked():
            self.close_cancel('프로젝트·꾸러미 저장이 끝난 뒤 닫아주세요.')
            return False
        if not self._closing:
            self._closing = True
            # Return from the UI closing event before evaluating JavaScript.
            threading.Thread(target=self._request_flush, daemon=True).start()
        return False


def main():
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('TooBusyAI.AudioCutter')
    server = app.ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    bridge = DesktopBridge()
    window = webview.create_window(
        '2BZ 오디오 커터 v0.5 · 뮤비 작업실',
        f'http://127.0.0.1:{server.server_port}', js_api=bridge,
        width=1380, height=960, min_size=(820, 650), background_color='#10131a',
    )
    bridge._window = window
    window.events.closing += bridge.on_closing
    try:
        webview.start(gui='edgechromium', private_mode=True)
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        log = Path(os.environ.get('LOCALAPPDATA', Path.home())) / '2BZ-Audio-Cutter' / 'startup-error.txt'
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(traceback.format_exc(), encoding='utf-8')
        ctypes.windll.user32.MessageBoxW(None,
            f'프로그램을 열지 못했습니다. Microsoft Edge WebView2 Runtime 설치 여부를 확인해주세요.\n\n오류 기록: {log}',
            '2BZ 오디오 커터', 0x10)

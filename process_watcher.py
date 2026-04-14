import time

from PyQt6.QtCore import QThread, pyqtSignal


class ProcessWatcher(QThread):
    """
    Watches a subprocess.Popen process in a background thread.
    Emits `finished` with (wad_id, elapsed_seconds) when the process exits.
    """
    finished = pyqtSignal(int, int)  # wad_id, elapsed_seconds

    def __init__(self, process, wad_id, parent=None):
        super().__init__(parent)
        self._process = process
        self._wad_id = wad_id

    def run(self):
        start = time.monotonic()
        self._process.wait()
        elapsed = int(time.monotonic() - start)
        self.finished.emit(self._wad_id, elapsed)

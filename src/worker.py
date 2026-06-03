from __future__ import annotations
from PyQt5.QtCore import QThread, pyqtSignal


class Worker(QThread):
    """Ejecuta una función bloqueante en un hilo separado y notifica al hilo de la UI via señales."""
    finished = pyqtSignal(object)
    error    = pyqtSignal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn     = fn
        self._args   = args
        self._kwargs = kwargs

    def run(self):
        try:
            self.finished.emit(self._fn(*self._args, **self._kwargs))
        except Exception as exc:
            self.error.emit(str(exc))

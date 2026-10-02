"""Small usage labels; native-statistics reads stay off the GUI thread."""

from PyQt6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QLabel

from espansr.core.usage import UsageSnapshot, refresh_usage


class _Result(QObject):
    ready = pyqtSignal(object)


class _Read(QRunnable):
    def __init__(self, entries):
        super().__init__()
        self.entries = entries
        self.result = _Result()
        self.reader = refresh_usage

    def run(self):
        try:
            snapshot = self.reader(self.entries, reconcile=False)
        except Exception:
            snapshot = UsageSnapshot(reason="Local usage is temporarily unavailable.")
        self.result.ready.emit(snapshot)


class UsageMonitor(QObject):
    updated = pyqtSignal(object)

    def __init__(self, provider, parent):
        super().__init__(parent)
        self.provider = provider
        self.snapshot = UsageSnapshot(reason="Reading local Espanso usage…")
        self._running = False
        self._timer = QTimer(self)
        self._timer.setInterval(10000)
        self._timer.timeout.connect(self._start)
        self._timer.start()
        QTimer.singleShot(0, self._start)

    def _start(self):
        if self._running:
            return
        try:
            worker = _Read(list(self.provider()))
        except Exception:
            return
        self._running = True
        worker.result.ready.connect(self._receive)
        self._worker = worker
        QThreadPool.globalInstance().start(worker)

    @pyqtSlot(object)
    def _receive(self, snapshot):
        self._running = False
        self.snapshot = snapshot
        self.updated.emit(snapshot)


class UsageLabel(QLabel):
    def __init__(self, monitor: UsageMonitor, key: str = "", parent=None):
        super().__init__(parent)
        self._key = key
        self._monitor = monitor
        self.setObjectName("usageCounter")
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.setStyleSheet("font-size: 10pt; color: #808080;")
        monitor.updated.connect(self._update)
        self._update(monitor.snapshot)

    def set_key(self, key: str):
        self._key = key
        self._update(self._monitor.snapshot)

    @pyqtSlot(object)
    def _update(self, snapshot):
        self.setVisible(bool(self._key))
        self.setText(
            f"Runs: {snapshot.counts.get(self._key, 0):,}"
            if snapshot.available
            else "Runs: unavailable"
        )
        self.setToolTip(snapshot.reason)

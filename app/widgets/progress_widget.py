"""Progress Widget — styled progress bar with percentage label."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QProgressBar, QLabel


class ProgressWidget(QWidget):
    """Compact progress bar with percentage label."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setFixedHeight(20)
        layout.addWidget(self._bar, 1)

        self._label = QLabel("0%")
        self._label.setFixedWidth(40)
        layout.addWidget(self._label)

    def set_progress(self, value: int):
        value = max(0, min(100, value))
        self._bar.setValue(value)
        self._label.setText(f"{value}%")

    def reset(self):
        self._bar.setValue(0)
        self._label.setText("0%")

    def set_format(self, fmt: str):
        self._bar.setFormat(fmt)

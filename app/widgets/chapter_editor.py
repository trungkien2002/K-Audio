"""Chapter Editor widget — text editor with auto-save and debounce."""

import os
from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtCore import QTimer


class ChapterEditor(QPlainTextEdit):
    """Text editor for chapter content with debounced auto-save."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._file_path: str | None = None
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(500)
        self._save_timer.timeout.connect(self._do_save)
        self.textChanged.connect(self._on_text_changed)

    def load_file(self, file_path: str):
        """Load a file into the editor."""
        self._file_path = file_path
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                self.blockSignals(True)
                self.setPlainText(f.read())
                self.blockSignals(False)

    def _on_text_changed(self):
        if self._file_path and os.path.exists(self._file_path):
            self._save_timer.start()

    def _do_save(self):
        if self._file_path:
            try:
                with open(self._file_path, "w", encoding="utf-8") as f:
                    f.write(self.toPlainText())
            except Exception:
                pass

    @property
    def file_path(self) -> str | None:
        return self._file_path

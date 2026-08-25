"""Path Picker widget — file/folder selection with text display."""

import os
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QFileDialog
)


class PathPicker(QWidget):
    """A compact widget for picking a file or directory path."""

    def __init__(
        self,
        label: str = "Chọn...",
        is_directory: bool = False,
        file_filter: str = "All (*.*)",
        parent=None,
    ):
        super().__init__(parent)
        self._is_directory = is_directory
        self._file_filter = file_filter
        self._label = label

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._line_edit = QLineEdit()
        self._line_edit.setPlaceholderText(label)
        self._line_edit.setReadOnly(False)
        layout.addWidget(self._line_edit, 1)

        self._browse_btn = QPushButton("Chọn")
        self._browse_btn.setMinimumWidth(84)
        self._browse_btn.clicked.connect(self._browse)
        layout.addWidget(self._browse_btn)

    def _browse(self):
        if self._is_directory:
            path = QFileDialog.getExistingDirectory(
                self, self._label, self._line_edit.text()
            )
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, self._label, "", self._file_filter
            )
        if path:
            self._line_edit.setText(path)

    def text(self) -> str:
        return self._line_edit.text().strip()

    def setText(self, value: str):
        self._line_edit.setText(value)

    def set_text(self, value: str):
        self._line_edit.setText(value)

    def setPlaceholderText(self, text: str):
        self._line_edit.setPlaceholderText(text)

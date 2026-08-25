"""Log Viewer widget — scrollable, colored log output."""

from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtGui import QTextCharFormat, QColor
from app.theme import THEME_COLORS


class LogViewer(QPlainTextEdit):
    """Read-only log viewer with colored message support."""

    TAG_COLORS = {
        "info": THEME_COLORS["info"],
        "success": THEME_COLORS["success"],
        "warning": THEME_COLORS["warning"],
        "error": THEME_COLORS["error"],
        "progress": THEME_COLORS["accent"],
        "default": THEME_COLORS["text_primary"],
    }

    def __init__(self, height: int = 200, parent=None):
        super().__init__(parent)
        self.setObjectName("processLog")
        self.setReadOnly(True)
        self.setMinimumHeight(height)
        self.setMaximumBlockCount(5000)
        self.setPlaceholderText("Nhật ký tiến trình, cảnh báo và lỗi sẽ hiển thị tại đây.")

    def append(self, message: str, tag: str = "default"):
        """Append a colored message to the log."""
        color = self.TAG_COLORS.get(tag, self.TAG_COLORS["default"])
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))

        cursor = self.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(message + "\n", fmt)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def append_info(self, msg: str):
        self.append(msg, "info")

    def append_success(self, msg: str):
        self.append(msg, "success")

    def append_warning(self, msg: str):
        self.append(msg, "warning")

    def append_error(self, msg: str):
        self.append(msg, "error")

    def clear(self):
        super().clear()

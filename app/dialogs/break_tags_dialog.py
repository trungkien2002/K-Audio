"""Break Tags Dialog — configure break tags and insert into text."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QGroupBox,
)
from PySide6.QtCore import Qt, Signal


BREAK_TIME_OPTIONS = [
    "100ms", "200ms", "300ms", "400ms", "500ms",
    "600ms", "700ms", "800ms", "900ms",
    "1s", "1.25s", "1.5s", "1.75s",
    "2s", "2.25s", "2.5s", "2.75s", "3s",
]


class BreakTagsDialog(QDialog):
    """Dialog for configuring break tags."""

    break_insert = Signal(str)  # Emitted when user wants to insert a break tag

    def __init__(self, enabled: bool = True, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⏸️ Break Tags — Thẻ tạm dừng")
        self.setMinimumSize(400, 300)
        self._build_ui(enabled)

    def _build_ui(self, enabled: bool):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(QLabel(
            "Chèn thẻ tạm dừng <break time=Xms/> vào text.\n"
            "Hỗ trợ cả Gemini-style tags: [pause], [sigh], [laugh]..."
        ))

        # Quick insert
        insert_group = QGroupBox("Chèn nhanh")
        ig_layout = QVBoxLayout(insert_group)

        row = QHBoxLayout()
        self.cmb_time = QComboBox()
        self.cmb_time.addItems(BREAK_TIME_OPTIONS)
        self.cmb_time.setCurrentText("500ms")
        row.addWidget(QLabel("Thời gian:"))
        row.addWidget(self.cmb_time, 1)

        btn_insert = QPushButton("Chèn vào văn bản")
        btn_insert.setStyleSheet("background: #00e5ff; color: #111; font-weight: bold; padding: 6px 16px; border-radius: 6px;")
        btn_insert.clicked.connect(self._on_insert)
        row.addWidget(btn_insert)
        ig_layout.addLayout(row)

        # Audio tags reference
        ig_layout.addWidget(QLabel("\nAudio Tags (tự động xử lý khi Generate):"))
        tags_text = (
            "⏸ [pause], [short pause], [long pause]\n"
            "😮‍💨 [breath], [sigh], [gasp]\n"
            "😂 [laugh], [giggles]\n"
            "🗣️ [whisper], [shouting] (bị loại bỏ)"
        )
        lbl_tags = QLabel(tags_text)
        lbl_tags.setStyleSheet("color: #888; font-size: 12px;")
        ig_layout.addWidget(lbl_tags)

        layout.addWidget(insert_group)

        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton("Đóng")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _on_insert(self):
        time_val = self.cmb_time.currentText()
        tag = f"<break time={time_val}/>"
        self.break_insert.emit(tag)

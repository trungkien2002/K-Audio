"""Punctuation Pauses Dialog — configure pause after each punctuation type."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCheckBox, QGroupBox, QGridLayout,
    QDoubleSpinBox,
)
from PySide6.QtCore import Qt


PUNCTUATION_TYPES = [
    ("period", ". 。", "Dấu chấm"),
    ("comma", ", ，", "Dấu phẩy"),
    ("semicolon", "; ；", "Chấm phẩy"),
    ("colon", ": ：", "Dấu hai chấm"),
    ("question", "? ？", "Dấu hỏi"),
    ("exclamation", "! ！", "Dấu chấm than"),
    ("newline", "\\n", "Xuống dòng"),
]


class PunctuationDialog(QDialog):
    """Dialog for configuring punctuation pause durations."""

    def __init__(self, config=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📝 Punctuation Pauses — Ngắt dấu câu")
        self.setMinimumSize(450, 380)
        self._spinners = {}
        self._build_ui(config)

    def _build_ui(self, config):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(QLabel(
            "Tự động thêm khoảng lặng sau mỗi loại dấu câu.\n"
            "Đặt 0.00 để không ngắt."
        ))

        self.chk_enabled = QCheckBox("Bật Punctuation Pauses")
        self.chk_enabled.setChecked(config.enabled if config else False)
        layout.addWidget(self.chk_enabled)

        # Grid of spinners
        group = QGroupBox("Thời gian ngắt (giây)")
        grid = QGridLayout(group)
        grid.setSpacing(8)

        for i, (key, symbol, label) in enumerate(PUNCTUATION_TYPES):
            grid.addWidget(QLabel(f"{symbol}"), i, 0)
            grid.addWidget(QLabel(label), i, 1)

            spin = QDoubleSpinBox()
            spin.setRange(0.0, 5.0)
            spin.setSingleStep(0.05)
            spin.setDecimals(2)
            spin.setSuffix("s")
            if config:
                spin.setValue(getattr(config, key, 0.0))
            self._spinners[key] = spin
            grid.addWidget(spin, i, 2)

        layout.addWidget(group)

        # Presets
        preset_row = QHBoxLayout()
        btn_reset = QPushButton("Reset (0s)")
        btn_reset.clicked.connect(self._reset_all)
        btn_recommended = QPushButton("Khuyến nghị")
        btn_recommended.clicked.connect(self._set_recommended)
        preset_row.addWidget(btn_reset)
        preset_row.addWidget(btn_recommended)
        preset_row.addStretch()
        layout.addLayout(preset_row)

        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("Hủy")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Lưu")
        btn_save.setStyleSheet("background: #00e5ff; color: #111; font-weight: bold; padding: 8px 20px; border-radius: 6px;")
        btn_save.clicked.connect(self.accept)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

    def _reset_all(self):
        for spin in self._spinners.values():
            spin.setValue(0.0)

    def _set_recommended(self):
        recommended = {
            "period": 0.40,
            "comma": 0.15,
            "semicolon": 0.25,
            "colon": 0.20,
            "question": 0.45,
            "exclamation": 0.40,
            "newline": 0.30,
        }
        for key, val in recommended.items():
            if key in self._spinners:
                self._spinners[key].setValue(val)

    def get_config(self):
        from process.tts.punctuation import PunctuationConfig
        return PunctuationConfig(
            enabled=self.chk_enabled.isChecked(),
            **{key: spin.value() for key, spin in self._spinners.items()},
        )

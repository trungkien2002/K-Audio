"""Dictionary Dialog — pronunciation dictionary editor."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox,
)
from PySide6.QtCore import Qt


class DictionaryDialog(QDialog):
    """Dialog for editing the pronunciation dictionary."""

    def __init__(self, entries: list[dict] | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📚 Từ điển phát âm")
        self.setMinimumSize(500, 400)
        self._entries = entries or []
        self._build_ui()
        self._load_entries()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        layout.addWidget(QLabel(
            "Thêm từ và cách phát âm. Ví dụ: AI → Ay Ai, TTS → Ti Ti Ét"
        ))

        # Add row
        add_row = QHBoxLayout()
        self.txt_word = QLineEdit()
        self.txt_word.setPlaceholderText("Từ gốc...")
        self.txt_pron = QLineEdit()
        self.txt_pron.setPlaceholderText("Phát âm...")
        btn_add = QPushButton("Thêm")
        btn_add.clicked.connect(self._add_entry)
        add_row.addWidget(self.txt_word, 1)
        add_row.addWidget(QLabel("→"))
        add_row.addWidget(self.txt_pron, 1)
        add_row.addWidget(btn_add)
        layout.addLayout(add_row)

        # Table
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Từ gốc", "Phát âm", "Xóa"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(2, 60)
        layout.addWidget(self.table, 1)

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

    def _load_entries(self):
        for entry in self._entries:
            self._add_row(entry.get("word", ""), entry.get("pronunciation", ""))

    def _add_entry(self):
        word = self.txt_word.text().strip()
        pron = self.txt_pron.text().strip()
        if word and pron:
            self._add_row(word, pron)
            self.txt_word.clear()
            self.txt_pron.clear()
            self.txt_word.setFocus()

    def _add_row(self, word: str, pron: str):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(word))
        self.table.setItem(row, 1, QTableWidgetItem(pron))
        btn_del = QPushButton("Xóa")
        btn_del.clicked.connect(lambda: self._delete_row(row))
        self.table.setCellWidget(row, 2, btn_del)

    def _delete_row(self, row):
        self.table.removeRow(row)
        # Reconnect delete buttons
        for r in range(self.table.rowCount()):
            btn = self.table.cellWidget(r, 2)
            if btn:
                try:
                    btn.clicked.disconnect()
                except RuntimeError:
                    pass
                btn.clicked.connect(lambda checked=False, r=r: self._delete_row(r))

    def get_entries(self) -> list[dict]:
        entries = []
        for row in range(self.table.rowCount()):
            word_item = self.table.item(row, 0)
            pron_item = self.table.item(row, 1)
            if word_item and pron_item:
                w = word_item.text().strip()
                p = pron_item.text().strip()
                if w and p:
                    entries.append({"word": w, "pronunciation": p})
        return entries

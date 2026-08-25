"""Voice Clone Dialog — upload audio, enter transcript, metadata → create new voice."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QComboBox, QPushButton, QFileDialog, QGroupBox,
    QFormLayout, QMessageBox,
)
from PySide6.QtCore import Qt


class VoiceCloneDialog(QDialog):
    """Dialog for cloning a new voice from an audio sample."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎤 Clone Voice — Tạo giọng mới")
        self.setMinimumSize(550, 500)
        self._audio_path = ""
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Audio file
        audio_group = QGroupBox("File audio mẫu")
        ag_layout = QHBoxLayout(audio_group)
        self.lbl_audio = QLabel("Chưa chọn file")
        self.lbl_audio.setStyleSheet("color: #888;")
        btn_browse = QPushButton("Chọn file")
        btn_browse.clicked.connect(self._browse_audio)
        ag_layout.addWidget(self.lbl_audio, 1)
        ag_layout.addWidget(btn_browse)
        layout.addWidget(audio_group)

        # Transcript
        layout.addWidget(QLabel("Transcript (nội dung chính xác của đoạn audio):"))
        self.txt_transcript = QTextEdit()
        self.txt_transcript.setPlaceholderText("Nhập chính xác nội dung người nói trong file audio...")
        self.txt_transcript.setMaximumHeight(100)
        layout.addWidget(self.txt_transcript)

        # Metadata
        meta_group = QGroupBox("Thông tin giọng nói")
        form = QFormLayout(meta_group)

        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("Ví dụ: Trâm Anh, Lê Hoàng...")
        form.addRow("Tên giọng:", self.txt_name)

        self.cmb_gender = QComboBox()
        self.cmb_gender.addItems(["", "Male", "Female", "Other"])
        form.addRow("Giới tính:", self.cmb_gender)

        self.cmb_language = QComboBox()
        self.cmb_language.addItems([
            "Vietnamese", "English", "Chinese", "Japanese", "Korean",
            "Thai", "Indonesian", "French", "Spanish", "German",
        ])
        form.addRow("Ngôn ngữ:", self.cmb_language)

        self.txt_location = QLineEdit()
        self.txt_location.setPlaceholderText("Northern Vietnam, Southern Vietnam...")
        form.addRow("Vùng miền:", self.txt_location)

        self.cmb_style = QComboBox()
        self.cmb_style.addItems([
            "", "Storytelling", "Conversational", "News",
            "Emotional", "Whisper", "Dramatic",
        ])
        self.cmb_style.setEditable(True)
        form.addRow("Phong cách:", self.cmb_style)

        layout.addWidget(meta_group)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("Hủy")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Lưu giọng")
        btn_save.setStyleSheet("background: #00e5ff; color: #111; font-weight: bold; padding: 8px 24px; border-radius: 6px;")
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

    def _browse_audio(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file audio mẫu", "",
            "Audio Files (*.wav *.mp3 *.flac *.ogg *.m4a *.aac *.webm);;All Files (*)"
        )
        if path:
            self._audio_path = path
            self.lbl_audio.setText(path.split("/")[-1].split("\\")[-1])
            self.lbl_audio.setStyleSheet("color: #00e5ff;")

    def _save(self):
        if not self._audio_path:
            QMessageBox.warning(self, "Lỗi", "Chưa chọn file audio mẫu!")
            return
        if not self.txt_name.text().strip():
            QMessageBox.warning(self, "Lỗi", "Chưa nhập tên giọng!")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "audio_path": self._audio_path,
            "name": self.txt_name.text().strip(),
            "transcript": self.txt_transcript.toPlainText().strip(),
            "gender": self.cmb_gender.currentText(),
            "language": self.cmb_language.currentText(),
            "location": self.txt_location.text().strip(),
            "style": self.cmb_style.currentText(),
        }

"""Tab Voice Clone — Clone giọng nói từ audio mẫu (tool độc lập)."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QComboBox, QGroupBox, QFormLayout,
    QFileDialog, QMessageBox, QListWidget, QListWidgetItem,
    QSplitter, QFrame,
)
from PySide6.QtCore import Qt

from app.theme import THEME_COLORS
from app.widgets.log_viewer import LogViewer


class TabVoiceClone(QWidget):
    """Voice cloning management — upload audio + transcript → create voice."""

    def __init__(self):
        super().__init__()
        self._audio_path = ""
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        header = QLabel("Voice Clone — Tạo giọng mới")
        header.setStyleSheet(f"color: {THEME_COLORS['accent']}; font-size: 18px; font-weight: bold;")
        layout.addWidget(header)

        splitter = QSplitter(Qt.Horizontal)

        # ═══ LEFT: Voice List ═══
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 8, 0)

        ll.addWidget(QLabel("Danh sách giọng nói"))

        self.lst_voices = QListWidget()
        ll.addWidget(self.lst_voices, 1)

        btn_row = QHBoxLayout()
        btn_scan = QPushButton("Quét lại")
        btn_scan.clicked.connect(self._scan_voices)
        btn_row.addWidget(btn_scan)
        btn_row.addStretch()
        ll.addLayout(btn_row)

        splitter.addWidget(left)

        # ═══ RIGHT: Clone Form ═══
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(8, 0, 0, 0)

        clone_group = QGroupBox("Clone Voice Mới")
        form = QVBoxLayout(clone_group)

        # Audio file
        audio_row = QHBoxLayout()
        self.lbl_audio = QLabel("Chưa chọn file audio")
        self.lbl_audio.setStyleSheet(f"color: {THEME_COLORS['text_muted']};")
        btn_browse = QPushButton("Chọn audio mẫu")
        btn_browse.clicked.connect(self._browse_audio)
        audio_row.addWidget(self.lbl_audio, 1)
        audio_row.addWidget(btn_browse)
        form.addLayout(audio_row)

        form.addWidget(QLabel("Transcript (nội dung audio):"))
        self.txt_transcript = QTextEdit()
        self.txt_transcript.setPlaceholderText("Nhập chính xác nội dung người nói trong file audio...")
        self.txt_transcript.setMaximumHeight(80)
        form.addWidget(self.txt_transcript)

        # Metadata
        meta = QFormLayout()
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("Trâm Anh, Lê Hoàng...")
        meta.addRow("Tên giọng:", self.txt_name)

        self.cmb_gender = QComboBox()
        self.cmb_gender.addItems(["", "Male", "Female", "Other"])
        meta.addRow("Giới tính:", self.cmb_gender)

        self.cmb_language = QComboBox()
        self.cmb_language.addItems(["Vietnamese", "English", "Chinese", "Japanese", "Korean",
                                     "Thai", "Indonesian", "French", "Spanish", "German"])
        meta.addRow("Ngôn ngữ:", self.cmb_language)

        self.txt_location = QLineEdit()
        self.txt_location.setPlaceholderText("Northern Vietnam, Southern Vietnam...")
        meta.addRow("Vùng miền:", self.txt_location)

        self.cmb_style = QComboBox()
        self.cmb_style.addItems(["", "Storytelling", "Conversational", "News",
                                  "Emotional", "Whisper", "Dramatic"])
        self.cmb_style.setEditable(True)
        meta.addRow("Phong cách:", self.cmb_style)

        form.addLayout(meta)

        btn_clone = QPushButton("Tạo giọng clone")
        btn_clone.setObjectName("primaryBtn")
        btn_clone.clicked.connect(self._do_clone)
        form.addWidget(btn_clone)

        rl.addWidget(clone_group)

        self.log = LogViewer()
        rl.addWidget(self.log, 1)

        splitter.addWidget(right)
        splitter.setSizes([350, 550])

        layout.addWidget(splitter, 1)
        self._scan_voices()

    def _browse_audio(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file audio mẫu", "",
            "Audio Files (*.wav *.mp3 *.flac *.ogg *.m4a *.aac *.webm);;All Files (*)"
        )
        if path:
            self._audio_path = path
            import os
            self.lbl_audio.setText(os.path.basename(path))
            self.lbl_audio.setStyleSheet(f"color: {THEME_COLORS['accent']};")

    def _scan_voices(self):
        try:
            from process.tts.voice_manager import scan_voices
            voices = scan_voices()
            self.lst_voices.clear()
            for v in voices:
                label = f"{v.name}"
                if v.gender:
                    label += f" ({v.gender})"
                if v.language:
                    label += f" [{v.language}]"
                if v.duration > 0:
                    label += f" {v.duration:.1f}s"
                self.lst_voices.addItem(QListWidgetItem(label))
        except Exception as exc:
            self.log.append(f"Không quét được danh sách giọng: {exc}")

    def _do_clone(self):
        if not self._audio_path:
            QMessageBox.warning(self, "Lỗi", "Chưa chọn file audio mẫu!")
            return
        name = self.txt_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Lỗi", "Chưa nhập tên giọng!")
            return

        try:
            from process.tts.voice_manager import clone_voice
            voice = clone_voice(
                source_audio_path=self._audio_path,
                name=name,
                transcript=self.txt_transcript.toPlainText().strip(),
                gender=self.cmb_gender.currentText(),
                language=self.cmb_language.currentText(),
                location=self.txt_location.text().strip(),
                style=self.cmb_style.currentText(),
            )
            self.log.append(f"Cloned: {voice.name} → {voice.path}")
            self._scan_voices()

            # Reset form
            self._audio_path = ""
            self.lbl_audio.setText("Chưa chọn file audio")
            self.lbl_audio.setStyleSheet(f"color: {THEME_COLORS['text_muted']};")
            self.txt_name.clear()
            self.txt_transcript.clear()
        except Exception as e:
            self.log.append(f"Error: {e}")

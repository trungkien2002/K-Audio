"""Multi-Speaker Dialog — analyze media, assign voices, generate audio."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QFileDialog, QProgressBar,
    QTextEdit, QSpinBox,
)
from PySide6.QtCore import Qt, QThread, Signal


class AnalyzeWorker(QThread):
    """Worker thread for media analysis."""
    progress = Signal(str)
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, media_path, stt_model, num_speakers, speech_enhance):
        super().__init__()
        self.media_path = media_path
        self.stt_model = stt_model
        self.num_speakers = num_speakers
        self.speech_enhance = speech_enhance

    def run(self):
        try:
            from process.multispeaker.analyzer import analyze_multispeaker_media
            entries = analyze_multispeaker_media(
                self.media_path,
                stt_model=self.stt_model,
                num_speakers=self.num_speakers,
                speech_enhance=self.speech_enhance,
                log_callback=lambda msg: self.progress.emit(msg),
            )
            self.finished.emit([e.to_dict() for e in entries])
        except Exception as e:
            self.error.emit(str(e))


class MultiSpeakerDialog(QDialog):
    """Dialog for multi-speaker analysis and generation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Multi-Speaker — Đa người nói")
        self.setMinimumSize(750, 600)
        self._segments = []
        self._worker = None
        self._generate_worker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Input
        input_group = QGroupBox("Phân tích media")
        ig = QVBoxLayout(input_group)

        row1 = QHBoxLayout()
        self.txt_media = QLineEdit()
        self.txt_media.setPlaceholderText("Đường dẫn file video/audio...")
        btn_browse = QPushButton("Chọn file")
        btn_browse.clicked.connect(self._browse_media)
        row1.addWidget(QLabel("File:"))
        row1.addWidget(self.txt_media, 1)
        row1.addWidget(btn_browse)
        ig.addLayout(row1)

        row2 = QHBoxLayout()
        self.cmb_stt = QComboBox()
        self.cmb_stt.addItems([
            "small", "medium", "large-v3-turbo", "large-v3",
            "online-gemini-fast", "online-gemini-flash-lite-3.1",
            "online-whisper",
        ])
        row2.addWidget(QLabel("STT Model:"))
        row2.addWidget(self.cmb_stt)

        self.spn_speakers = QSpinBox()
        self.spn_speakers.setRange(0, 20)
        self.spn_speakers.setSpecialValueText("Auto")
        row2.addWidget(QLabel("Speakers:"))
        row2.addWidget(self.spn_speakers)

        self.cmb_enhance = QComboBox()
        self.cmb_enhance.addItems(["off", "demucs_vocals", "fast_clean"])
        row2.addWidget(QLabel("Enhance:"))
        row2.addWidget(self.cmb_enhance)

        btn_analyze = QPushButton("Phân tích")
        btn_analyze.setObjectName("primaryBtn")
        btn_analyze.clicked.connect(self._start_analyze)
        row2.addWidget(btn_analyze)
        ig.addLayout(row2)

        layout.addWidget(input_group)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximum(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Log
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumHeight(80)
        self.txt_log.setPlaceholderText("Log phân tích...")
        layout.addWidget(self.txt_log)

        # Segments table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Start", "End", "Speaker", "Text", "Voice"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 80)
        self.table.setColumnWidth(1, 80)
        self.table.setColumnWidth(2, 100)
        self.table.setColumnWidth(4, 150)
        layout.addWidget(self.table, 1)

        # Bottom buttons
        btn_row = QHBoxLayout()
        btn_export_srt = QPushButton("Xuất SRT")
        btn_export_srt.clicked.connect(lambda: self._export_subtitle("srt"))
        btn_export_vtt = QPushButton("Xuất VTT")
        btn_export_vtt.clicked.connect(lambda: self._export_subtitle("vtt"))
        btn_row.addWidget(btn_export_srt)
        btn_row.addWidget(btn_export_vtt)
        btn_row.addStretch()

        btn_cancel = QPushButton("Đóng")
        btn_cancel.clicked.connect(self.reject)
        btn_generate = QPushButton("Tạo audio")
        btn_generate.setObjectName("primaryBtn")
        btn_generate.clicked.connect(self._generate)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_generate)
        layout.addLayout(btn_row)

    def _browse_media(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file media", "",
            "Media Files (*.mp4 *.mkv *.avi *.mov *.mp3 *.wav *.flac);;All Files (*)"
        )
        if path:
            self.txt_media.setText(path)

    def _start_analyze(self):
        media = self.txt_media.text().strip()
        if not media:
            return

        self.txt_log.clear()
        self.progress_bar.setVisible(True)
        self.table.setRowCount(0)

        self._worker = AnalyzeWorker(
            media, self.cmb_stt.currentText(),
            self.spn_speakers.value(), self.cmb_enhance.currentText(),
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, msg):
        self.txt_log.append(msg)

    def _on_finished(self, segments):
        self.progress_bar.setVisible(False)
        self._segments = segments
        self._populate_table(segments)
        self.txt_log.append(f"✅ Hoàn tất: {len(segments)} segments")

    def _on_error(self, msg):
        self.progress_bar.setVisible(False)
        self.txt_log.append(f"❌ Lỗi: {msg}")

    def _populate_table(self, segments):
        self.table.setRowCount(len(segments))
        try:
            from process.tts.voice_manager import scan_voices
            voices = scan_voices()
        except Exception as exc:
            voices = []
            self.txt_log.append(f"Không quét được danh sách giọng: {exc}")

        for i, seg in enumerate(segments):
            self.table.setItem(i, 0, QTableWidgetItem(f"{seg['start']:.1f}s"))
            self.table.setItem(i, 1, QTableWidgetItem(f"{seg['end']:.1f}s"))
            self.table.setItem(i, 2, QTableWidgetItem(seg.get("speaker", "?")))
            self.table.setItem(i, 3, QTableWidgetItem(seg.get("text", "")))

            cmb = QComboBox()
            cmb.addItem("(mặc định)")
            for voice in voices:
                cmb.addItem(voice.name, voice.id)
            self.table.setCellWidget(i, 4, cmb)

    def _export_subtitle(self, fmt):
        if not self._segments:
            return
        folder = QFileDialog.getExistingDirectory(self, "Chọn folder output")
        if folder:
            import os
            path = os.path.join(folder, f"multispeaker_export.{fmt}")
            from process.multispeaker.analyzer import MultiSpeakerEntry
            from process.multispeaker.generator import export_multispeaker_subtitle
            entries = [MultiSpeakerEntry(**s) for s in self._segments]
            export_multispeaker_subtitle(entries, path, fmt)
            self.txt_log.append(f"Exported: {path}")

    def _generate(self):
        if not self._segments:
            self.txt_log.append("Chưa có segment để tạo audio.")
            return
        output_path, _ = QFileDialog.getSaveFileName(
            self, "Lưu audio", "multispeaker.wav", "WAV Audio (*.wav)"
        )
        if not output_path:
            return
        if not output_path.lower().endswith(".wav"):
            output_path += ".wav"

        from process.multispeaker.analyzer import MultiSpeakerEntry
        entries = []
        for row, original in enumerate(self._segments):
            voice_combo = self.table.cellWidget(row, 4)
            text_item = self.table.item(row, 3)
            speaker_item = self.table.item(row, 2)
            entries.append(MultiSpeakerEntry(
                start=float(original["start"]),
                end=float(original["end"]),
                speaker=speaker_item.text().strip() if speaker_item else original.get("speaker", "SPEAKER_00"),
                text=text_item.text().strip() if text_item else original.get("text", ""),
                voice_id=(voice_combo.currentData() or "") if voice_combo else "",
            ))

        from app.tabs.tab_multispeaker import GenerateAudioWorker
        self._generate_worker = GenerateAudioWorker(entries, output_path)
        self._generate_worker.progress.connect(self.txt_log.append)
        self._generate_worker.finished_ok.connect(
            lambda path: self.txt_log.append(f"Đã tạo audio: {path}")
        )
        self._generate_worker.error.connect(
            lambda message: self.txt_log.append(f"Lỗi: {message}")
        )
        self._generate_worker.start()

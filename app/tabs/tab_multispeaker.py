"""Tab Multi-Speaker — Đa người nói + diarization (tool độc lập)."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QGroupBox, QFileDialog, QSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QSplitter,
)
from PySide6.QtCore import Qt, QThread, Signal
import os

from app.theme import THEME_COLORS
from app.widgets.log_viewer import LogViewer


class AnalyzeWorker(QThread):
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


class GenerateAudioWorker(QThread):
    progress = Signal(str)
    finished_ok = Signal(str)
    error = Signal(str)

    def __init__(self, segments, output_path):
        super().__init__()
        self.segments = segments
        self.output_path = output_path

    def run(self):
        try:
            from process.multispeaker.generator import generate_multispeaker_audio
            voice_map = {
                segment.speaker: segment.voice_id
                for segment in self.segments
                if segment.voice_id
            }
            for message in generate_multispeaker_audio(
                self.segments,
                voice_map,
                self.output_path,
            ):
                self.progress.emit(message)
            if os.path.isfile(self.output_path) and os.path.getsize(self.output_path) > 0:
                self.finished_ok.emit(self.output_path)
            else:
                self.error.emit("Không tạo được file audio.")
        except Exception as e:
            self.error.emit(str(e))


class TabMultiSpeaker(QWidget):
    """Multi-speaker analysis and generation — independent tool."""

    def __init__(self):
        super().__init__()
        self._segments = []
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        header = QLabel("Multi-Speaker — Đa người nói")
        header.setStyleSheet(f"color: {THEME_COLORS['accent']}; font-size: 18px; font-weight: bold;")
        layout.addWidget(header)

        # Input section
        input_group = QGroupBox("Phân tích media")
        ig = QVBoxLayout(input_group)

        row1 = QHBoxLayout()
        self.txt_media = QLineEdit()
        self.txt_media.setPlaceholderText("Đường dẫn file video/audio...")
        btn_browse = QPushButton("Chọn file")
        btn_browse.clicked.connect(self._browse_media)
        row1.addWidget(self.txt_media, 1)
        row1.addWidget(btn_browse)
        ig.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("STT:"))
        self.cmb_stt = QComboBox()
        self.cmb_stt.addItems(["small", "medium", "large-v3-turbo", "large-v3",
                                "online-gemini-fast", "online-whisper"])
        row2.addWidget(self.cmb_stt)

        row2.addWidget(QLabel("Speakers:"))
        self.spn_speakers = QSpinBox()
        self.spn_speakers.setRange(0, 20)
        self.spn_speakers.setSpecialValueText("Auto")
        row2.addWidget(self.spn_speakers)

        row2.addWidget(QLabel("Enhance:"))
        self.cmb_enhance = QComboBox()
        self.cmb_enhance.addItems(["off", "demucs_vocals", "fast_clean"])
        row2.addWidget(self.cmb_enhance)

        self.btn_analyze = QPushButton("Phân tích")
        self.btn_analyze.setObjectName("primaryBtn")
        self.btn_analyze.clicked.connect(self._start_analyze)
        row2.addWidget(self.btn_analyze)
        ig.addLayout(row2)
        layout.addWidget(input_group)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximum(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Results table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Start", "End", "Speaker", "Text", "Voice"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 80)
        self.table.setColumnWidth(1, 80)
        self.table.setColumnWidth(2, 100)
        self.table.setColumnWidth(4, 150)
        layout.addWidget(self.table, 1)

        # Bottom actions
        btn_row = QHBoxLayout()
        btn_export_srt = QPushButton("Xuất SRT")
        btn_export_srt.clicked.connect(lambda: self._export("srt"))
        btn_export_vtt = QPushButton("Xuất VTT")
        btn_export_vtt.clicked.connect(lambda: self._export("vtt"))
        btn_row.addWidget(btn_export_srt)
        btn_row.addWidget(btn_export_vtt)
        btn_row.addStretch()
        btn_gen = QPushButton("Tạo audio")
        btn_gen.setObjectName("primaryBtn")
        btn_gen.clicked.connect(self._generate_audio)
        btn_row.addWidget(btn_gen)
        layout.addLayout(btn_row)

        # Log
        self.log = LogViewer()
        self.log.setMaximumHeight(100)
        layout.addWidget(self.log)

    def _browse_media(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file media", "",
            "Media Files (*.mp4 *.mkv *.avi *.mov *.mp3 *.wav *.flac);;All Files (*)"
        )
        if path:
            self.txt_media.setText(path)

    def _start_analyze(self):
        media = self.txt_media.text().strip()
        if not media or not os.path.isfile(media):
            self.log.append("Error: File media không tồn tại.")
            return
        self.log.clear()
        self.progress_bar.setVisible(True)
        self.btn_analyze.setEnabled(False)
        self.table.setRowCount(0)

        self._worker = AnalyzeWorker(
            media, self.cmb_stt.currentText(),
            self.spn_speakers.value(), self.cmb_enhance.currentText(),
        )
        self._worker.progress.connect(self.log.append)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_analyze_error)
        self._worker.start()

    def _on_finished(self, segments):
        self.progress_bar.setVisible(False)
        self.btn_analyze.setEnabled(True)
        self._segments = segments
        self.table.setRowCount(len(segments))

        try:
            from process.tts.voice_manager import scan_voices
            voices = scan_voices()
        except Exception as e:
            voices = []
            self.log.append(f"Không quét được voice: {e}")

        for i, seg in enumerate(segments):
            self.table.setItem(i, 0, QTableWidgetItem(f"{seg['start']:.1f}s"))
            self.table.setItem(i, 1, QTableWidgetItem(f"{seg['end']:.1f}s"))
            self.table.setItem(i, 2, QTableWidgetItem(seg.get("speaker", "?")))
            self.table.setItem(i, 3, QTableWidgetItem(seg.get("text", "")))
            cmb = QComboBox()
            cmb.addItem("(default)")
            for voice in voices:
                cmb.addItem(voice.name, voice.id)
            self.table.setCellWidget(i, 4, cmb)

        self.log.append(f"Done: {len(segments)} segments")

    def _export(self, fmt):
        if not self._segments:
            return
        folder = QFileDialog.getExistingDirectory(self, "Chọn folder output")
        if folder:
            import os
            path = os.path.join(folder, f"multispeaker_export.{fmt}")
            from process.multispeaker.analyzer import MultiSpeakerEntry
            from process.multispeaker.generator import export_multispeaker_subtitle
            entries = self._table_segments()
            export_multispeaker_subtitle(entries, path, fmt)
            self.log.append(f"Exported: {path}")

    def _on_analyze_error(self, message):
        self.log.append(f"Error: {message}")
        self.progress_bar.setVisible(False)
        self.btn_analyze.setEnabled(True)

    def _table_segments(self):
        from process.multispeaker.analyzer import MultiSpeakerEntry

        entries = []
        for row, original in enumerate(self._segments):
            speaker_item = self.table.item(row, 2)
            text_item = self.table.item(row, 3)
            voice_combo = self.table.cellWidget(row, 4)
            entries.append(MultiSpeakerEntry(
                start=float(original["start"]),
                end=float(original["end"]),
                speaker=speaker_item.text().strip() if speaker_item else original.get("speaker", "SPEAKER_00"),
                text=text_item.text().strip() if text_item else original.get("text", ""),
                voice_id=(voice_combo.currentData() or "") if voice_combo else "",
            ))
        return entries

    def _generate_audio(self):
        if not self._segments:
            self.log.append("Chưa có segment để sinh audio.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Lưu audio", "multispeaker.wav", "WAV Audio (*.wav)")
        if not path:
            return
        if not path.lower().endswith(".wav"):
            path += ".wav"
        self._generate_worker = GenerateAudioWorker(self._table_segments(), path)
        self._generate_worker.progress.connect(self.log.append)
        self._generate_worker.finished_ok.connect(lambda p: self.log.append(f"Generated: {p}"))
        self._generate_worker.error.connect(lambda msg: self.log.append(f"Error: {msg}"))
        self._generate_worker.start()

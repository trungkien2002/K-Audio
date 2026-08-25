"""Tab OmniVoice — Full OmniVoice TTS UI with all 13 features from AndyLe.

This is the main OmniVoice tab with:
- Text input (textarea or load file)
- Voice selector (70+ voices, filter by gender/language/location/style)
- Quick controls (num_steps, speed, pitch, volume, guidance, temperature, postprocess)
- Output format (WAV/MP3/FLAC/OGG)
- Toolbar (Break Tags, Punctuation, Dictionary, Load SRT/VTT/ASS)
- Generate button + audio player
- Device selector (GPU/CPU)
- Model status indicator
- Output folder picker
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QComboBox, QSlider, QDoubleSpinBox, QSpinBox,
    QGroupBox, QGridLayout, QFileDialog, QCheckBox, QLineEdit,
    QFrame, QSplitter, QMessageBox, QListWidget, QListWidgetItem,
    QTabWidget,
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont
import os

from app.theme import THEME_COLORS
from app.widgets.path_picker import PathPicker
from app.widgets.log_viewer import LogViewer
from app.widgets.progress_widget import ProgressWidget


class GenerateWorker(QThread):
    """Worker thread for TTS generation."""
    progress = Signal(str)
    work_completed = Signal()
    error = Signal(str)

    def __init__(self, text, output_path, config, srt_path=None):
        super().__init__()
        self.text = text
        self.output_path = output_path
        self.config = config
        self.srt_path = srt_path
        self._stop = False
        self._stop_event = None

    def run(self):
        try:
            import threading
            self._stop_event = threading.Event()

            from process.tts.omnivoice_engine import tts_omnivoice
            for msg in tts_omnivoice(self.text, self.output_path, self.config, self._stop_event, srt_path=self.srt_path):
                if self._stop:
                    self._stop_event.set()
                    self.progress.emit("[OmniVoice] Đã hủy bởi người dùng")
                    return
                self.progress.emit(msg)
            self.work_completed.emit()
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.error.emit(f"{e}\n{tb}")

    def stop(self):
        self._stop = True
        if self._stop_event:
            self._stop_event.set()


class TabOmniVoice(QWidget):
    """Full OmniVoice TTS tab — mirrors TTS_Voice_AndyLe-001."""

    def __init__(self):
        super().__init__()
        self._worker = None
        self._active_workers = []  # Lưu các luồng đang chạy để tránh bị Garbage Collector thu hồi gây crash
        self._all_voices = []  # Cached voice list
        self._chapter_files = []  # For batch chapter mode
        self._batch_stopped = False  # Track batch cancellation
        self._build_ui()
        self._model_status_timer = QTimer(self)
        self._model_status_timer.setInterval(500)
        self._model_status_timer.timeout.connect(self._refresh_model_status)
        self._model_status_timer.start()
        self._refresh_model_status()
        # Auto-load voices on startup
        QTimer.singleShot(100, self._scan_voices)

        # Connect signals for auto-saving session
        self.lst_voices.itemSelectionChanged.connect(self.save_session)
        self.cmb_device.currentTextChanged.connect(lambda: self.save_session())
        self.cmb_format.currentTextChanged.connect(lambda: self.save_session())
        self.cmb_gender_filter.currentTextChanged.connect(lambda: self.save_session())
        self.cmb_lang_filter.currentTextChanged.connect(lambda: self.save_session())
        self.chk_postprocess.toggled.connect(lambda: self.save_session())
        self.chk_skip_existing.toggled.connect(lambda: self.save_session())
        self.spn_speed.valueChanged.connect(lambda: self.save_session())
        self.spn_pitch.valueChanged.connect(lambda: self.save_session())
        self.spn_volume.valueChanged.connect(lambda: self.save_session())
        self.spn_temp.valueChanged.connect(lambda: self.save_session())
        self.cmb_steps.currentTextChanged.connect(lambda: self.save_session())
        self.cmb_guidance.currentTextChanged.connect(lambda: self.save_session())
        self.chk_export_srt.toggled.connect(lambda: self.save_session())
        self.chk_merge_files.toggled.connect(lambda: self.save_session())
        self.spn_merge_start.valueChanged.connect(lambda: self.save_session())
        self.spn_merge_end.valueChanged.connect(lambda: self.save_session())
        self.spn_group_size.valueChanged.connect(lambda: self.save_session())

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # ── Header ──
        header = QLabel("OmniVoice TTS")
        header.setStyleSheet(f"color: {THEME_COLORS['accent']}; font-size: 18px; font-weight: bold;")
        layout.addWidget(header)

        # ── Main splitter: left (text+controls) | right (voice+log) ──
        splitter = QSplitter(Qt.Horizontal)

        # ═══════ LEFT PANEL ═══════
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(8)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)

        btn_load_text = QPushButton("Nạp văn bản")
        btn_load_text.setToolTip("Load file TXT")
        btn_load_text.clicked.connect(self._load_text_file)
        toolbar.addWidget(btn_load_text)

        btn_load_folder = QPushButton("Nạp thư mục chương")
        btn_load_folder.setToolTip("Chọn folder chứa các file chương → TTS từng file")
        btn_load_folder.clicked.connect(self._load_chapter_folder)
        toolbar.addWidget(btn_load_folder)

        btn_load_sub = QPushButton("Nạp SRT/VTT")
        btn_load_sub.setToolTip("Import subtitle → auto break tags")
        btn_load_sub.clicked.connect(self._load_subtitle)
        toolbar.addWidget(btn_load_sub)

        btn_break = QPushButton("Ngắt nghỉ")
        btn_break.setToolTip("Cài đặt Break Tags")
        btn_break.clicked.connect(self._open_break_dialog)
        toolbar.addWidget(btn_break)

        btn_punct = QPushButton("Dấu câu")
        btn_punct.setToolTip("Cài đặt Punctuation Pauses")
        btn_punct.clicked.connect(self._open_punctuation_dialog)
        toolbar.addWidget(btn_punct)

        btn_dict = QPushButton("Từ điển")
        btn_dict.setToolTip("Từ điển phát âm")
        btn_dict.clicked.connect(self._open_dictionary_dialog)
        toolbar.addWidget(btn_dict)

        toolbar.addStretch()
        left_layout.addLayout(toolbar)

        # ── Mode: Single text vs Batch chapters ──
        mode_row = QHBoxLayout()
        self.lbl_mode = QLabel("Mode: Single Text")
        self.lbl_mode.setStyleSheet(f"color: {THEME_COLORS['text_muted']}; font-size: 12px;")
        mode_row.addWidget(self.lbl_mode)

        self.lbl_chapters = QLabel("")
        self.lbl_chapters.setStyleSheet(f"color: {THEME_COLORS['accent']}; font-size: 12px;")
        mode_row.addWidget(self.lbl_chapters)

        # Checkbox to skip existing audio files
        self.chk_skip_existing = QCheckBox("Bỏ qua chương đã có file audio")
        self.chk_skip_existing.setChecked(True)
        mode_row.addWidget(self.chk_skip_existing)
        mode_row.addStretch()

        btn_clear_chapters = QPushButton("Xóa danh sách")
        btn_clear_chapters.setToolTip("Xóa danh sách chương, quay lại Single Text")
        btn_clear_chapters.clicked.connect(self._clear_chapters)
        mode_row.addWidget(btn_clear_chapters)
        left_layout.addLayout(mode_row)

        # Text input
        self.txt_input = QTextEdit()
        self.txt_input.setPlaceholderText(
            "Nhập văn bản cần chuyển thành giọng nói...\n\n"
            "Hỗ trợ:\n"
            "• <break time=500ms/> — tạm dừng\n"
            "• [pause 1s], [sigh], [laugh] — audio tags\n"
            "• [whisper], [shouting] — style tags (bị loại bỏ)\n"
            "• Import SRT/VTT/ASS → auto break tags"
        )
        self.txt_input.setMinimumHeight(200)
        left_layout.addWidget(self.txt_input, 1)

        # ── Quick Controls ──
        controls_group = QGroupBox("Điều khiển")
        cg = QGridLayout(controls_group)
        cg.setSpacing(6)

        # Row 0: Device + Output Format
        cg.addWidget(QLabel("Device:"), 0, 0)
        self.cmb_device = QComboBox()
        self.cmb_device.addItems(["GPU (auto)", "CPU"])
        cg.addWidget(self.cmb_device, 0, 1)

        cg.addWidget(QLabel("Format:"), 0, 2)
        self.cmb_format = QComboBox()
        self.cmb_format.addItems(["wav", "mp3", "flac", "ogg"])
        cg.addWidget(self.cmb_format, 0, 3)

        # Row 1: Speed + Pitch
        cg.addWidget(QLabel("Speed:"), 1, 0)
        self.spn_speed = QDoubleSpinBox()
        self.spn_speed.setRange(0.5, 2.0)
        self.spn_speed.setSingleStep(0.05)
        self.spn_speed.setValue(1.0)
        self.spn_speed.setSuffix("x")
        cg.addWidget(self.spn_speed, 1, 1)

        cg.addWidget(QLabel("Pitch:"), 1, 2)
        self.spn_pitch = QDoubleSpinBox()
        self.spn_pitch.setRange(0.5, 2.0)
        self.spn_pitch.setSingleStep(0.05)
        self.spn_pitch.setValue(1.0)
        self.spn_pitch.setSuffix("x")
        cg.addWidget(self.spn_pitch, 1, 3)

        # Row 2: Volume + Num Steps
        cg.addWidget(QLabel("Volume:"), 2, 0)
        self.spn_volume = QDoubleSpinBox()
        self.spn_volume.setRange(0.1, 2.0)
        self.spn_volume.setSingleStep(0.05)
        self.spn_volume.setValue(1.0)
        self.spn_volume.setSuffix("x")
        cg.addWidget(self.spn_volume, 2, 1)

        cg.addWidget(QLabel("Steps:"), 2, 2)
        self.cmb_steps = QComboBox()
        self.cmb_steps.addItems(["1", "2", "4", "8", "16", "32", "64"])
        self.cmb_steps.setCurrentText("32")
        cg.addWidget(self.cmb_steps, 2, 3)

        # Row 3: Guidance + Temperature
        cg.addWidget(QLabel("Guidance:"), 3, 0)
        self.cmb_guidance = QComboBox()
        self.cmb_guidance.addItems(["1.0", "1.5", "2.0", "2.5", "3.0", "3.5", "4.0"])
        self.cmb_guidance.setCurrentText("3.0")
        cg.addWidget(self.cmb_guidance, 3, 1)

        cg.addWidget(QLabel("Temp:"), 3, 2)
        self.spn_temp = QDoubleSpinBox()
        self.spn_temp.setRange(0.1, 1.0)
        self.spn_temp.setSingleStep(0.1)
        self.spn_temp.setValue(0.1)
        cg.addWidget(self.spn_temp, 3, 3)

        # Row 4: Postprocess
        self.chk_postprocess = QCheckBox("Postprocess output")
        self.chk_postprocess.setChecked(True)
        cg.addWidget(self.chk_postprocess, 4, 0, 1, 2)

        left_layout.addWidget(controls_group)

        # ── Cấu hình Batch & Gộp file ──
        sub_group = QGroupBox("Cấu hình Batch & Gộp file")
        sub_grid = QGridLayout(sub_group)
        sub_grid.setSpacing(6)

        self.chk_export_srt = QCheckBox("Xuất phụ đề (SRT)")
        self.chk_export_srt.setChecked(True)
        sub_grid.addWidget(self.chk_export_srt, 0, 0, 1, 2)

        self.chk_merge_files = QCheckBox("Tự động gộp file")
        self.chk_merge_files.setChecked(False)
        sub_grid.addWidget(self.chk_merge_files, 0, 2, 1, 2)

        sub_grid.addWidget(QLabel("Chạy từ chương:"), 1, 0)
        self.spn_merge_start = QSpinBox()
        self.spn_merge_start.setRange(1, 9999)
        self.spn_merge_start.setValue(1)
        sub_grid.addWidget(self.spn_merge_start, 1, 1)

        sub_grid.addWidget(QLabel("Đến:"), 1, 2)
        self.spn_merge_end = QSpinBox()
        self.spn_merge_end.setRange(1, 9999)
        self.spn_merge_end.setValue(1)
        sub_grid.addWidget(self.spn_merge_end, 1, 3)

        sub_grid.addWidget(QLabel("Gộp mỗi file:"), 2, 0)
        self.spn_group_size = QSpinBox()
        self.spn_group_size.setRange(0, 9999)
        self.spn_group_size.setValue(10)
        self.spn_group_size.setSpecialValueText("Tất cả")
        self.spn_group_size.setSuffix(" chương")
        sub_grid.addWidget(self.spn_group_size, 2, 1, 1, 3)

        left_layout.addWidget(sub_group)

        # ── Output ──
        output_row = QHBoxLayout()
        output_row.addWidget(QLabel("Output:"))
        self.txt_output = QLineEdit()
        self.txt_output.setPlaceholderText("Chọn đường dẫn output...")
        output_row.addWidget(self.txt_output, 1)
        btn_browse_out = QPushButton("Chọn thư mục")
        btn_browse_out.clicked.connect(self._browse_output)
        output_row.addWidget(btn_browse_out)
        left_layout.addLayout(output_row)

        # ── Generate ──
        gen_row = QHBoxLayout()
        self.btn_generate = QPushButton("Tạo audio")
        self.btn_generate.setStyleSheet(
            f"background: {THEME_COLORS['accent']}; color: #111; "
            f"font-weight: bold; font-size: 14px; padding: 10px 32px; border-radius: 8px;"
        )
        self.btn_generate.clicked.connect(self._generate)
        gen_row.addStretch()
        gen_row.addWidget(self.btn_generate)

        self.btn_stop = QPushButton("Dừng")
        self.btn_stop.setStyleSheet("padding: 10px 16px;")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop_generate)
        gen_row.addWidget(self.btn_stop)
        gen_row.addStretch()
        left_layout.addLayout(gen_row)

        splitter.addWidget(left)

        # ═══════ RIGHT PANEL ═══════
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(8)

        # Voice selector
        voice_group = QGroupBox("Giọng nói")
        vg = QVBoxLayout(voice_group)

        # Filters
        filter_row = QHBoxLayout()
        self.cmb_gender_filter = QComboBox()
        self.cmb_gender_filter.addItems(["All", "Male", "Female"])
        self.cmb_gender_filter.currentTextChanged.connect(self._filter_voices)
        filter_row.addWidget(QLabel("Giới:"))
        filter_row.addWidget(self.cmb_gender_filter)

        self.cmb_lang_filter = QComboBox()
        self.cmb_lang_filter.addItems(["All", "Vietnamese", "English", "Chinese", "Japanese", "Korean", "French", "Thai"])
        self.cmb_lang_filter.currentTextChanged.connect(self._filter_voices)
        filter_row.addWidget(QLabel("Ngôn ngữ:"))
        filter_row.addWidget(self.cmb_lang_filter)
        vg.addLayout(filter_row)

        # Voice list
        self.lst_voices = QListWidget()
        self.lst_voices.setMaximumHeight(180)
        vg.addWidget(self.lst_voices)

        # Scan and Play buttons
        btn_row = QHBoxLayout()
        btn_scan = QPushButton("Quét danh sách giọng")
        btn_scan.clicked.connect(self._scan_voices)
        btn_row.addWidget(btn_scan)

        self.btn_play_voice = QPushButton("Nghe thử")
        self.btn_play_voice.clicked.connect(self._play_selected_voice)
        btn_row.addWidget(self.btn_play_voice)

        self.btn_stop_voice = QPushButton("Dừng nghe")
        self.btn_stop_voice.setToolTip("Dừng nghe thử")
        self.btn_stop_voice.clicked.connect(self._stop_voice_play)
        btn_row.addWidget(self.btn_stop_voice)

        vg.addLayout(btn_row)

        right_layout.addWidget(voice_group)

        # Model status
        status_group = QGroupBox("Model Status")
        sg = QVBoxLayout(status_group)
        self.lbl_model_status = QLabel("Chưa kiểm tra model")
        self.lbl_model_status.setStyleSheet(f"color: {THEME_COLORS['text_muted']};")
        sg.addWidget(self.lbl_model_status)
        self.progress_model = ProgressWidget()
        sg.addWidget(self.progress_model)
        right_layout.addWidget(status_group)

        # Log
        self.log = LogViewer()
        right_layout.addWidget(self.log, 1)

        splitter.addWidget(right)
        splitter.setSizes([600, 400])

        layout.addWidget(splitter, 1)

    def _refresh_model_status(self):
        """Reflect the model manager's real state in the status panel."""
        try:
            from process.tts.model_manager import get_model_status, model_folder_ready
            status = get_model_status()
            phase = status.get("phase", "idle")
            progress = int(status.get("progress", 0) or 0)
            message = status.get("message", "").strip()

            if phase == "idle":
                if model_folder_ready():
                    message = "Model đã có trên máy, sẵn sàng nạp khi tạo audio"
                    progress = 100
                else:
                    message = "Chưa có model; model sẽ được tải khi tạo audio"
                    progress = 0
            elif not message:
                message = {
                    "downloading": "Đang tải model",
                    "extracting": "Đang giải nén model",
                    "loading": "Đang nạp model vào bộ nhớ",
                    "ready": "Model đã sẵn sàng",
                    "error": "Không thể chuẩn bị model",
                }.get(phase, "Đang kiểm tra model")

            self.lbl_model_status.setText(message)
            self.progress_model.set_progress(progress)
            color = THEME_COLORS["error"] if phase == "error" else (
                THEME_COLORS["success"] if phase == "ready" else THEME_COLORS["text_secondary"]
            )
            self.lbl_model_status.setStyleSheet(f"color: {color};")
        except Exception as exc:
            self.lbl_model_status.setText(f"Không đọc được trạng thái model: {exc}")
            self.lbl_model_status.setStyleSheet(f"color: {THEME_COLORS['error']};")

    # ─────────────────────────── Actions ─────────────────────────

    def _load_text_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file text", "",
            "Text Files (*.txt);;All Files (*)"
        )
        if path:
            try:
                from process.reader.reader import read_txt
                content = read_txt(path)
                self.txt_input.setPlainText(content)
                self.log.append(f"Loaded: {path} ({len(content)} chars)")
            except Exception as e:
                self.log.append(f"Error: {e}")

    def _load_subtitle(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn subtitle", "",
            "Subtitle Files (*.srt *.vtt *.ass);;All Files (*)"
        )
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                from process.tts.subtitle_parser import maybe_convert_subtitle_text
                converted = maybe_convert_subtitle_text(content)
                self.txt_input.setPlainText(converted)
                self.log.append(f"Imported subtitle: {path}")
            except Exception as e:
                self.log.append(f"Error: {e}")

    def _open_break_dialog(self):
        from app.dialogs.break_tags_dialog import BreakTagsDialog
        dlg = BreakTagsDialog(parent=self)
        dlg.break_insert.connect(self._insert_break_tag)
        dlg.exec()

    def _insert_break_tag(self, tag: str):
        cursor = self.txt_input.textCursor()
        cursor.insertText(tag)

    def _open_punctuation_dialog(self):
        from app.dialogs.punctuation_dialog import PunctuationDialog
        from process.tts.punctuation import get_punctuation_config, set_punctuation_config
        config = get_punctuation_config()
        dlg = PunctuationDialog(config=config, parent=self)
        if dlg.exec():
            new_config = dlg.get_config()
            set_punctuation_config(new_config)
            self.log.append(f"Punctuation: {'ON' if new_config.enabled else 'OFF'}")

    def _open_dictionary_dialog(self):
        from app.dialogs.dictionary_dialog import DictionaryDialog
        from process.tts.pronunciation import get_dictionary, set_dictionary
        entries = get_dictionary()
        dlg = DictionaryDialog(entries=entries, parent=self)
        if dlg.exec():
            new_entries = dlg.get_entries()
            set_dictionary(new_entries)
            self.log.append(f"Dictionary: {len(new_entries)} entries")

    def _browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn folder output")
        if folder:
            self.txt_output.setText(folder)

    def _scan_voices(self):
        try:
            from process.tts.voice_manager import scan_voices
            self._all_voices = scan_voices()
            self._display_voices(self._all_voices)
            self.log.append(f"Found {len(self._all_voices)} voices")
            # Restore settings after voice list is populated
            self.load_session()
        except Exception as e:
            self.log.append(f"Scan error: {e}")

    def _display_voices(self, voices):
        """Display voices in the list widget."""
        self.lst_voices.clear()
        for v in voices:
            label = v.name
            if v.gender:
                label += f" ({v.gender})"
            if v.language:
                label += f" [{v.language}]"
            if v.style:
                label += f" • {v.style[:30]}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, v.id)
            item.setData(Qt.UserRole + 1, v.path)  # Store path too
            self.lst_voices.addItem(item)

    def _play_selected_voice(self):
        """Preview the selected voice using native winsound API."""
        sel = self.lst_voices.currentItem()
        if not sel:
            QMessageBox.warning(self, "Nghe thử", "Vui lòng chọn một giọng đọc trong danh sách!")
            return

        import os
        voice_path = sel.data(Qt.UserRole + 1)
        if not voice_path or not os.path.isfile(voice_path):
            QMessageBox.warning(self, "Nghe thử", "Không tìm thấy file âm thanh mẫu của giọng này!")
            return

        try:
            import winsound
            # Stop any currently playing sound first
            winsound.PlaySound(None, winsound.SND_ASYNC)
            # Play the sound asynchronously
            winsound.PlaySound(voice_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            self.log.append(f"Đang nghe thử giọng: {sel.text()}")
        except Exception as e:
            self.log.append(f"Lỗi nghe thử: {e}")

    def _stop_voice_play(self):
        """Stop any playing preview sound."""
        try:
            import winsound
            winsound.PlaySound(None, winsound.SND_ASYNC)
            self.log.append("Đã dừng nghe thử giọng")
        except Exception:
            pass

    def _filter_voices(self):
        """Filter cached voices by gender and language."""
        gender = self.cmb_gender_filter.currentText()
        lang = self.cmb_lang_filter.currentText()

        filtered = self._all_voices
        if gender != "All":
            filtered = [v for v in filtered if v.gender.lower() == gender.lower()]
        if lang != "All":
            filtered = [v for v in filtered if v.language.lower() == lang.lower()]

        self._display_voices(filtered)

    def _load_chapter_folder(self):
        """Load a folder of chapter TXT files for batch TTS."""
        folder = QFileDialog.getExistingDirectory(self, "Chọn folder chứa các chương")
        if not folder:
            return
        self._load_chapters_from_path(folder)

    def _load_chapters_from_path(self, folder):
        import os
        import re
        if not os.path.isdir(folder):
            return

        files = sorted([
            os.path.join(folder, f) for f in os.listdir(folder)
            if f.lower().endswith('.txt') and os.path.isfile(os.path.join(folder, f))
        ], key=lambda x: [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', x)])

        if not files:
            QMessageBox.warning(self, "Lỗi", "Không tìm thấy file .txt trong folder!")
            return

        self._chapters_folder_path = folder
        self._chapter_files = files
        self.lbl_mode.setText("Mode: Batch Chapters")
        self.lbl_chapters.setText(f"{len(files)} chương từ {os.path.basename(folder)}")
        
        self.spn_merge_start.setRange(1, len(files))
        self.spn_merge_start.setValue(1)
        self.spn_merge_end.setRange(1, len(files))
        self.spn_merge_end.setValue(len(files))

        self.txt_input.setPlainText(
            f"[BATCH MODE] {len(files)} chương sẽ được chuyển TTS\n"
            + "\n".join(f"  • {os.path.basename(f)}" for f in files[:20])
            + (f"\n  ... và {len(files) - 20} file nữa" if len(files) > 20 else "")
        )
        self.log.append(f"Loaded {len(files)} chapters from {folder}")
        self.save_session()

    def _clear_chapters(self):
        """Clear batch chapters, return to single text mode."""
        self._chapter_files = []
        self._chapters_folder_path = ""
        self.lbl_mode.setText("Mode: Single Text")
        self.lbl_chapters.setText("")
        self.txt_input.clear()
        self.save_session()

    def _build_config(self):
        """Build OmniVoice config from current controls."""
        from process.tts.omnivoice_engine import OmniVoiceConfig
        config = OmniVoiceConfig(
            speed=self.spn_speed.value(),
            pitch=self.spn_pitch.value(),
            volume=self.spn_volume.value(),
            num_steps=int(self.cmb_steps.currentText()),
            guidance_scale=float(self.cmb_guidance.currentText()),
            temperature=self.spn_temp.value(),
            postprocess=self.chk_postprocess.isChecked(),
            output_format=self.cmb_format.currentText(),
            device="cpu" if self.cmb_device.currentText() == "CPU" else "auto",
        )

        # Get selected voice
        sel = self.lst_voices.currentItem()
        if sel:
            config.voice_id = sel.data(Qt.UserRole)
            voice_path = sel.data(Qt.UserRole + 1)
            if voice_path:
                config.voice_path = voice_path

        return config

    def _generate(self):
        # Batch chapter mode
        if self._chapter_files:
            self._generate_batch()
            return

        # Single text mode
        text = self.txt_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Lỗi", "Chưa nhập text!")
            return

        output_dir = self.txt_output.text().strip()
        if not output_dir:
            output_dir = QFileDialog.getExistingDirectory(self, "Chọn folder output")
            if not output_dir:
                return
            self.txt_output.setText(output_dir)

        import os
        os.makedirs(output_dir, exist_ok=True)
        fmt = self.cmb_format.currentText()
        output = os.path.join(output_dir, f"output.{fmt}")
        
        srt_path = None
        if self.chk_export_srt.isChecked():
            srt_path = os.path.join(output_dir, "output.srt")

        config = self._build_config()
        self.save_session()

        self.log.clear()
        self.log.append("Starting OmniVoice generation...")
        self.btn_generate.setEnabled(False)
        self.btn_stop.setEnabled(True)

        worker = GenerateWorker(text, output, config, srt_path=srt_path)
        self._worker = worker
        self._active_workers.append(worker)
        worker.progress.connect(self.log.append)
        worker.work_completed.connect(self._on_generate_done)
        worker.error.connect(self._on_generate_error)
        worker.finished.connect(lambda: self._on_worker_finished(worker))
        worker.start()

    def _generate_batch(self):
        """Generate TTS for each chapter file."""
        output_dir = self.txt_output.text().strip()
        if not output_dir:
            output_dir = QFileDialog.getExistingDirectory(self, "Chọn folder output cho audio")
            if not output_dir:
                return
            self.txt_output.setText(output_dir)

        import os
        os.makedirs(output_dir, exist_ok=True)
        fmt = self.cmb_format.currentText()
        config = self._build_config()
        self.save_session()

        self.log.clear()
        
        # Xác định phạm vi chương cần xử lý
        start_idx = self.spn_merge_start.value() - 1
        end_idx = self.spn_merge_end.value()
        start_idx = max(0, min(start_idx, len(self._chapter_files) - 1))
        end_idx = max(start_idx + 1, min(end_idx, len(self._chapter_files)))
        
        self._batch_files_to_process = self._chapter_files[start_idx:end_idx]
        self._batch_results = []
        self._current_group_results = [] # Danh sách của nhóm cuốn chiếu hiện tại
        
        # Tải danh sách chương đã hoàn thành trước đó
        self._completed_chapters = self._load_completed_manifest(output_dir)
        
        total = len(self._batch_files_to_process)
        self.log.append(f"Batch TTS: {total} chương (từ chương {start_idx + 1} đến {end_idx}) → {output_dir}")
        self.btn_generate.setEnabled(False)
        self.btn_stop.setEnabled(True)

        self._batch_stopped = False
        # Use first chapter to start, then chain
        self._batch_index = 0
        self._batch_output_dir = output_dir
        self._batch_config = config
        self._batch_fmt = fmt
        self._process_next_chapter()

    def _process_next_chapter(self):
        """Process the next chapter in batch mode."""
        import os
        if self._batch_stopped:
            self.log.append("\nĐã dừng tiến trình Batch TTS!")
            self.btn_generate.setEnabled(True)
            self.btn_stop.setEnabled(False)
            return

        if self._batch_index >= len(self._batch_files_to_process):
            self.log.append(f"\nBatch TTS hoàn tất! {self._batch_index} chương")
            
            # Gộp nốt các chương còn sót lại ở cuối đợt chạy
            if self.chk_merge_files.isChecked():
                group_size = self.spn_group_size.value()
                if group_size > 0 and self._current_group_results:
                    self._merge_current_group()
                elif group_size == 0 and self._batch_results:
                    self._current_group_results = self._batch_results
                    self._merge_current_group()
                    
            self.btn_generate.setEnabled(True)
            self.btn_stop.setEnabled(False)
            return

        chapter_path = self._batch_files_to_process[self._batch_index]
        chapter_name = os.path.splitext(os.path.basename(chapter_path))[0]
        output_path = os.path.join(self._batch_output_dir, f"{chapter_name}.{self._batch_fmt}")
        srt_path = os.path.join(self._batch_output_dir, f"{chapter_name}.srt") if self.chk_export_srt.isChecked() else None

        # Kiểm tra chương đã hoàn thành (trong manifest hoặc file thực tế vẫn còn tồn tại)
        is_completed = (hasattr(self, "_completed_chapters") and chapter_name in self._completed_chapters) or \
                       (os.path.isfile(output_path) and os.path.getsize(output_path) > 1024)

        # Check if already exists and is non-empty
        if self.chk_skip_existing.isChecked() and is_completed:
            self.log.append(f"  ⏭ Đã hoàn thành: {chapter_name} - Bỏ qua")
            
            # Đảm bảo ghi nhận vào nhật ký
            self._mark_chapter_completed(self._batch_output_dir, chapter_name)
            
            item = {"audio_path": output_path, "srt_path": srt_path}
            self._batch_results.append(item)
            self._current_group_results.append(item)
            
            # Kiểm tra gộp cuốn chiếu ngay khi skip
            self._check_and_trigger_merge()
            
            self._batch_index += 1
            from PySide6.QtCore import QTimer
            QTimer.singleShot(30, self._process_next_chapter)
            return

        self.log.append(f"\n[{self._batch_index + 1}/{len(self._batch_files_to_process)}] {chapter_name}")

        try:
            with open(chapter_path, "r", encoding="utf-8") as f:
                text = f.read().strip()
        except Exception:
            try:
                import chardet
                with open(chapter_path, "rb") as f:
                    raw = f.read()
                detected = chardet.detect(raw)
                text = raw.decode(detected.get("encoding", "utf-8"), errors="replace").strip()
            except Exception as e:
                self.log.append(f"  Skip (read error): {e}")
                self._batch_index += 1
                self._process_next_chapter()
                return

        if not text:
            self.log.append("  Skip (empty file)")
            self._batch_index += 1
            self._process_next_chapter()
            return

        worker = GenerateWorker(text, output_path, self._batch_config, srt_path=srt_path)
        self._worker = worker
        self._active_workers.append(worker)
        worker.progress.connect(self.log.append)
        worker.work_completed.connect(self._on_batch_chapter_done)
        worker.error.connect(self._on_batch_chapter_error)
        worker.finished.connect(lambda: self._on_worker_finished(worker))
        worker.start()

    def _on_batch_chapter_done(self):
        chapter_path = self._batch_files_to_process[self._batch_index]
        chapter_name = os.path.splitext(os.path.basename(chapter_path))[0]
        output_path = os.path.join(self._batch_output_dir, f"{chapter_name}.{self._batch_fmt}")
        srt_path = os.path.join(self._batch_output_dir, f"{chapter_name}.srt") if self.chk_export_srt.isChecked() else None
        
        # Đánh dấu đã hoàn thành vào manifest
        self._mark_chapter_completed(self._batch_output_dir, chapter_name)

        item = {"audio_path": output_path, "srt_path": srt_path}
        self._batch_results.append(item)
        self._current_group_results.append(item)
        
        # Kiểm tra gộp cuốn chiếu ngay khi tạo xong file
        self._check_and_trigger_merge()

        self._batch_index += 1
        self._process_next_chapter()

    def _on_batch_chapter_error(self, msg):
        self.log.append(f"  Error: {msg}")
        
        # Clean up incomplete/failed audio file
        try:
            if self._batch_files_to_process and 0 <= self._batch_index < len(self._batch_files_to_process):
                chapter_path = self._batch_files_to_process[self._batch_index]
                import os
                chapter_name = os.path.splitext(os.path.basename(chapter_path))[0]
                output_path = os.path.join(self._batch_output_dir, f"{chapter_name}.{self._batch_fmt}")
                if os.path.isfile(output_path):
                    os.remove(output_path)
                    self.log.append(f"Đã xóa file lỗi: {os.path.basename(output_path)}")
        except Exception:
            pass

        self._batch_index += 1
        self._process_next_chapter()

    def _check_and_trigger_merge(self):
        if not self.chk_merge_files.isChecked():
            return
        group_size = self.spn_group_size.value()
        if group_size > 0 and len(self._current_group_results) >= group_size:
            self._merge_current_group()

    def _merge_current_group(self):
        grp = self._current_group_results
        self._current_group_results = [] # Xóa ngay lập tức để tránh trùng lặp
        if not grp:
            return
            
        self.log.append("\n🔗 Tiến hành gộp nhóm chương cuốn chiếu...")
        first_file = grp[0]["audio_path"]
        last_file = grp[-1]["audio_path"]
        
        def get_chap_num(path):
            import re
            basename = os.path.basename(path)
            match = re.search(r'\d+', basename)
            if match:
                return int(match.group())
            for idx, orig_path in enumerate(self._chapter_files):
                if os.path.basename(orig_path).split('.')[0] in basename:
                    return idx + 1
            return 1
            
        start_num = get_chap_num(first_file)
        end_num = get_chap_num(last_file)
        
        if start_num == end_num:
            name_str = f"Chương {start_num}"
        else:
            name_str = f"Chương {start_num} - {end_num}"
            
        merged_audio = os.path.join(self._batch_output_dir, f"{name_str}.{self._batch_fmt}")
        merged_srt = os.path.join(self._batch_output_dir, f"{name_str}.srt")
        
        export_srt = self.chk_export_srt.isChecked()
        
        # Nếu file gộp đích đã tồn tại hợp lệ, ta chỉ cần bỏ qua việc gộp
        if os.path.isfile(merged_audio) and (not export_srt or os.path.isfile(merged_srt)):
            self.log.append(f"  ⏭️ Nhóm {name_str} đã có sẵn file gộp - Bỏ qua gộp")
            return
            
        from process.tts.audio_merger import merge_chapters_pipeline
        
        ok = merge_chapters_pipeline(grp, merged_audio, merged_srt, export_srt)
        if ok:
            self.log.append(f"✅ Gộp thành công: {name_str}\n  - Audio: {os.path.basename(merged_audio)}\n  - Phụ đề: {os.path.basename(merged_srt) if export_srt else 'Không xuất'}")
            self.log.append("  ℹ️ Đã giữ lại các file chương gốc.")
        else:
            self.log.append(f"❌ Gộp thất bại nhóm: {name_str}")

    def _load_completed_manifest(self, output_dir):
        import json
        manifest_path = os.path.join(output_dir, ".completed_chapters.json")
        if os.path.isfile(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return set(data.get("completed_chapters", []))
            except Exception:
                pass
        return set()

    def _mark_chapter_completed(self, output_dir, chapter_name):
        import json
        if not hasattr(self, "_completed_chapters"):
            self._completed_chapters = set()
        self._completed_chapters.add(chapter_name)
        manifest_path = os.path.join(output_dir, ".completed_chapters.json")
        try:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump({"completed_chapters": list(self._completed_chapters)}, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _stop_generate(self):
        self._batch_stopped = True
        if self._worker:
            self._worker.stop()
            self._worker.wait(3000)  # Wait up to 3s for thread to finish
        
        # Clean up incomplete file of the current batch index
        try:
            if self._chapter_files and 0 <= self._batch_index < len(self._chapter_files):
                chapter_path = self._chapter_files[self._batch_index]
                import os
                chapter_name = os.path.splitext(os.path.basename(chapter_path))[0]
                output_path = os.path.join(self._batch_output_dir, f"{chapter_name}.{self._batch_fmt}")
                if os.path.isfile(output_path):
                    os.remove(output_path)
                    self.log.append(f"Đã dọn dẹp file dở dang: {os.path.basename(output_path)}")
        except Exception:
            pass

        self.btn_generate.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def _on_generate_done(self):
        self.log.append("✅ Generate hoàn tất!")
        self.btn_generate.setEnabled(True)
        self.btn_stop.setEnabled(False)
        if self._worker:
            self._worker.wait(1000)

    def _on_generate_error(self, msg):
        self.log.append(f"❌ Error: {msg}")
        
        # Clean up incomplete single output if exists
        try:
            output_dir = self.txt_output.text().strip()
            if output_dir and not self._chapter_files:
                import os
                fmt = self.cmb_format.currentText()
                output = os.path.join(output_dir, f"output.{fmt}")
                if os.path.isfile(output):
                    os.remove(output)
                    self.log.append("Đã dọn dẹp file lỗi.")
        except Exception:
            pass

        self.btn_generate.setEnabled(True)
        self.btn_stop.setEnabled(False)
        if self._worker:
            self._worker.wait(1000)

    # ─────────────────────────── Session Management ────────────────
    
    def save_session(self):
        """Save current workspace/session to JSON."""
        try:
            import json, os
            session = {
                "output_dir": self.txt_output.text().strip(),
                "chapters_folder": getattr(self, "_chapters_folder_path", ""),
                "speed": self.spn_speed.value(),
                "pitch": self.spn_pitch.value(),
                "volume": self.spn_volume.value(),
                "steps": self.cmb_steps.currentText(),
                "guidance": self.cmb_guidance.currentText(),
                "temperature": self.spn_temp.value(),
                "postprocess": self.chk_postprocess.isChecked(),
                "format": self.cmb_format.currentText(),
                "device": self.cmb_device.currentText(),
                "gender_filter": self.cmb_gender_filter.currentText(),
                "lang_filter": self.cmb_lang_filter.currentText(),
                "chk_skip_existing": self.chk_skip_existing.isChecked(),
                "chk_export_srt": self.chk_export_srt.isChecked(),
                "chk_merge_files": self.chk_merge_files.isChecked(),
                "spn_merge_start": self.spn_merge_start.value(),
                "spn_merge_end": self.spn_merge_end.value(),
                "spn_group_size": self.spn_group_size.value(),
                "text_content": self.txt_input.toPlainText() if not self._chapter_files else "",
            }
            # Get selected voice
            sel = self.lst_voices.currentItem()
            if sel:
                session["selected_voice_id"] = sel.data(Qt.UserRole)

            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_dir = os.path.join(project_root, "config")
            os.makedirs(config_dir, exist_ok=True)
            session_path = os.path.join(config_dir, "omnivoice_session.json")
            with open(session_path, "w", encoding="utf-8") as f:
                json.dump(session, f, indent=2, ensure_ascii=False)
        except Exception as e:
            LOGGER.warning(f"Failed to save session: {e}")

    def load_session(self):
        """Load session and restore widget states."""
        try:
            import json, os
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            session_path = os.path.join(project_root, "config", "omnivoice_session.json")
            if not os.path.isfile(session_path):
                return
            with open(session_path, "r", encoding="utf-8") as f:
                session = json.load(f)

            if "output_dir" in session:
                self.txt_output.setText(session["output_dir"])
            if "speed" in session:
                self.spn_speed.setValue(session["speed"])
            if "pitch" in session:
                self.spn_pitch.setValue(session["pitch"])
            if "volume" in session:
                self.spn_volume.setValue(session["volume"])
            if "steps" in session:
                self.cmb_steps.setCurrentText(str(session["steps"]))
            if "guidance" in session:
                self.cmb_guidance.setCurrentText(str(session["guidance"]))
            if "temperature" in session:
                self.spn_temp.setValue(session["temperature"])
            if "postprocess" in session:
                self.chk_postprocess.setChecked(session["postprocess"])
            if "format" in session:
                self.cmb_format.setCurrentText(session["format"])
            if "device" in session:
                self.cmb_device.setCurrentText(session["device"])
            if "gender_filter" in session:
                self.cmb_gender_filter.setCurrentText(session["gender_filter"])
            if "lang_filter" in session:
                self.cmb_lang_filter.setCurrentText(session["lang_filter"])
            if "chk_skip_existing" in session:
                self.chk_skip_existing.setChecked(session["chk_skip_existing"])
            if "chk_export_srt" in session:
                self.chk_export_srt.setChecked(session["chk_export_srt"])
            if "chk_merge_files" in session:
                self.chk_merge_files.setChecked(session["chk_merge_files"])
            if "spn_merge_start" in session:
                self.spn_merge_start.setValue(session["spn_merge_start"])
            if "spn_merge_end" in session:
                self.spn_merge_end.setValue(session["spn_merge_end"])
            if "spn_group_size" in session:
                self.spn_group_size.setValue(session["spn_group_size"])
            if "text_content" in session and session["text_content"]:
                self.txt_input.setPlainText(session["text_content"])

            if "chapters_folder" in session and session["chapters_folder"]:
                self._load_chapters_from_path(session["chapters_folder"])

            self._restore_selected_voice(session.get("selected_voice_id", ""))
        except Exception as e:
            LOGGER.warning(f"Failed to load session: {e}")

    def _restore_selected_voice(self, voice_id):
        if not voice_id:
            return
        for i in range(self.lst_voices.count()):
            item = self.lst_voices.item(i)
            if item.data(Qt.UserRole) == voice_id:
                self.lst_voices.setCurrentItem(item)
                break

    def _on_worker_finished(self, worker):
        """Dọn dẹp luồng chạy ngầm sau khi đã dừng hoàn toàn để tránh crash ứng dụng."""
        if worker in self._active_workers:
            self._active_workers.remove(worker)
        worker.deleteLater()

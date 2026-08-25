"""Tab TTS — Chuyển văn bản thành giọng nói (Edge-TTS, gTTS, OmniVoice)."""

import os
import re
import chardet
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QGridLayout, QComboBox, QSlider, QPushButton, QSplitter,
    QLineEdit, QMessageBox, QCheckBox, QSpinBox, QFileDialog
)
from PySide6.QtCore import Qt, Signal, QObject, QThread
from app.widgets import PathPicker, LogViewer, ProgressWidget
from process.tts.engine import TTSConfig, convert_tts


class TTSWorker(QThread):
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

            from process.tts.engine import convert_tts
            for msg in convert_tts(self.text, self.output_path, self.config, self._stop_event, srt_path=self.srt_path):
                if self._stop:
                    self._stop_event.set()
                    self.progress.emit("Đã hủy bởi người dùng")
                    return
                self.progress.emit(msg)
            self.work_completed.emit()
        except Exception as e:
            import traceback
            self.error.emit(f"{e}\n{traceback.format_exc()}")

    def stop(self):
        self._stop = True
        if self._stop_event:
            self._stop_event.set()


class TabTTS(QWidget):
    """Chuyển TTS với Edge-TTS, gTTS và OmniVoice."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._active_workers = []
        self._chapter_files = []
        self._batch_files_to_process = []
        self._batch_results = []
        self._batch_index = 0
        self._batch_stopped = False
        self._batch_active = False

        self._build_ui()
        self.load_session()
        self._connect_session_signals()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        header = QLabel("Chuyển Text-to-Speech")
        header.setProperty("heading", True)
        layout.addWidget(header)

        main_splitter = QSplitter(Qt.Horizontal)

        # Left: config
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        self.chapters_picker = PathPicker("Thư mục chương đã tách", is_directory=True)
        left_layout.addWidget(self.chapters_picker)

        self.output_picker = PathPicker("Thư mục xuất audio", is_directory=True)
        left_layout.addWidget(self.output_picker)

        # TTS Config
        config_group = QGroupBox("Cấu hình TTS")
        grid = QGridLayout(config_group)
        grid.setSpacing(8)

        grid.addWidget(QLabel("Engine:"), 0, 0)
        self.engine_combo = QComboBox()
        self.engine_combo.addItems([
            "Edge-TTS (Microsoft)",
            "gTTS (Google)",
            "OmniVoice (Local)",
        ])
        self.engine_combo.currentTextChanged.connect(self._on_engine_changed)
        grid.addWidget(self.engine_combo, 0, 1)

        grid.addWidget(QLabel("Giọng đọc:"), 1, 0)
        self.voice_combo = QComboBox()
        grid.addWidget(self.voice_combo, 1, 1)

        grid.addWidget(QLabel("Tốc độ:"), 2, 0)
        speed_w = QWidget()
        speed_row = QHBoxLayout(speed_w)
        speed_row.setContentsMargins(0, 0, 0, 0)
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(50, 200)
        self.speed_slider.setValue(100)
        self.speed_label = QLabel("1.0x")
        self.speed_label.setFixedWidth(32)
        self.speed_slider.valueChanged.connect(
            lambda v: self.speed_label.setText(f"{v / 100:.1f}x")
        )
        speed_row.addWidget(self.speed_slider)
        speed_row.addWidget(self.speed_label)
        grid.addWidget(speed_w, 2, 1)

        grid.addWidget(QLabel("Cao độ:"), 3, 0)
        pitch_w = QWidget()
        pitch_row = QHBoxLayout(pitch_w)
        pitch_row.setContentsMargins(0, 0, 0, 0)
        self.pitch_slider = QSlider(Qt.Horizontal)
        self.pitch_slider.setRange(-10, 10)
        self.pitch_slider.setValue(0)
        self.pitch_label = QLabel("0")
        self.pitch_label.setFixedWidth(24)
        self.pitch_slider.valueChanged.connect(
            lambda v: self.pitch_label.setText(str(v))
        )
        pitch_row.addWidget(self.pitch_slider)
        pitch_row.addWidget(self.pitch_label)
        grid.addWidget(pitch_w, 3, 1)

        left_layout.addWidget(config_group)

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

        self.chk_skip_existing = QCheckBox("Bỏ qua chương đã có audio")
        self.chk_skip_existing.setChecked(True)
        sub_grid.addWidget(self.chk_skip_existing, 1, 0, 1, 4)

        sub_grid.addWidget(QLabel("Chạy từ chương:"), 2, 0)
        self.spn_merge_start = QSpinBox()
        self.spn_merge_start.setRange(1, 9999)
        self.spn_merge_start.setValue(1)
        sub_grid.addWidget(self.spn_merge_start, 2, 1)

        sub_grid.addWidget(QLabel("Đến:"), 2, 2)
        self.spn_merge_end = QSpinBox()
        self.spn_merge_end.setRange(1, 9999)
        self.spn_merge_end.setValue(1)
        sub_grid.addWidget(self.spn_merge_end, 2, 3)

        sub_grid.addWidget(QLabel("Gộp mỗi file:"), 3, 0)
        self.spn_group_size = QSpinBox()
        self.spn_group_size.setRange(0, 9999)
        self.spn_group_size.setValue(10)
        self.spn_group_size.setSpecialValueText("Tất cả")
        self.spn_group_size.setSuffix(" chương")
        sub_grid.addWidget(self.spn_group_size, 3, 1, 1, 3)

        left_layout.addWidget(sub_group)

        # TTS Button
        self.tts_btn = QPushButton("Bắt đầu TTS")
        self.tts_btn.setObjectName("primaryBtn")
        self.tts_btn.setFixedHeight(36)
        self.tts_btn.clicked.connect(self._toggle_tts)
        left_layout.addWidget(self.tts_btn)

        self.progress = ProgressWidget()
        left_layout.addWidget(self.progress)

        left_layout.addStretch()
        main_splitter.addWidget(left)

        # Right: log
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_layout.addWidget(QLabel("Log TTS"))
        self.log = LogViewer(height=300)
        right_layout.addWidget(self.log, 1)

        main_splitter.addWidget(right)
        main_splitter.setSizes([400, 600])

        layout.addWidget(main_splitter, 1)
        self._on_engine_changed(self.engine_combo.currentText())

    def _on_engine_changed(self, engine_text):
        """Update voice options based on selected engine."""
        self.voice_combo.clear()
        if "Edge-TTS" in engine_text:
            self.voice_combo.addItems([
                "vi-VN-HoaiMyNeural", 
                "vi-VN-NamMinhNeural",
                "en-US-AriaNeural",
                "en-US-GuyNeural"
            ])
            self.pitch_slider.setEnabled(True)
            self.chk_export_srt.setEnabled(True)
        elif "gTTS" in engine_text:
            self.voice_combo.addItems(["vi", "en", "zh", "ja"])
            self.pitch_slider.setEnabled(False)
            self.chk_export_srt.setEnabled(False) # gTTS không có WordBoundary
        else:
            self.voice_combo.addItem("default")
            self.pitch_slider.setEnabled(True)
            self.chk_export_srt.setEnabled(True)

    def _toggle_tts(self):
        if self._batch_active:
            self._stop_tts()
        else:
            self._start_tts()

    def _stop_tts(self):
        self._batch_stopped = True
        self._batch_active = False
        if self._worker:
            self._worker.stop()
            self._worker.wait(3000)
        self.tts_btn.setText("Bắt đầu TTS")
        self.log.append("Đã dừng tiến trình TTS.")

    def _start_tts(self):
        import os
        import re

        chapters_dir = self.chapters_picker.text().strip()
        output_dir = self.output_picker.text().strip()

        if not chapters_dir or not os.path.isdir(chapters_dir):
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn thư mục chương hợp lệ!")
            return
        if not output_dir:
            output_dir = QFileDialog.getExistingDirectory(self, "Chọn thư mục xuất audio")
            if not output_dir:
                return
            self.output_picker.setText(output_dir)

        files = sorted([
            os.path.join(chapters_dir, f) for f in os.listdir(chapters_dir)
            if f.lower().endswith('.txt') and os.path.isfile(os.path.join(chapters_dir, f))
        ], key=lambda x: [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', x)])

        if not files:
            QMessageBox.warning(self, "Lỗi", "Không tìm thấy file .txt nào trong thư mục chương!")
            return

        self._chapter_files = files
        self.spn_merge_start.setRange(1, len(files))
        self.spn_merge_end.setRange(1, len(files))

        # Lấy phạm vi chương cần chạy
        start_idx = self.spn_merge_start.value() - 1
        end_idx = self.spn_merge_end.value()
        start_idx = max(0, min(start_idx, len(files) - 1))
        end_idx = max(start_idx + 1, min(end_idx, len(files)))

        self._batch_files_to_process = files[start_idx:end_idx]
        self._batch_results = []
        self._current_group_results = [] # Danh sách của nhóm cuốn chiếu hiện tại
        
        # Tải danh sách chương đã hoàn thành trước đó
        self._completed_chapters = self._load_completed_manifest(output_dir)
        
        self._batch_index = 0
        self._batch_stopped = False
        self._batch_active = True

        self.log.clear()
        self.log.append(f"Khởi động Batch TTS: {len(self._batch_files_to_process)} chương...")
        self.tts_btn.setText("Dừng TTS")
        self.progress.reset()
        self._process_next_chapter()

    def _process_next_chapter(self):
        if self._batch_stopped:
            self._batch_active = False
            self.tts_btn.setText("Bắt đầu TTS")
            return

        if self._batch_index >= len(self._batch_files_to_process):
            self.log.append("\n🎉 Batch TTS hoàn tất!")
            self._batch_active = False
            self.tts_btn.setText("Bắt đầu TTS")
            self.progress.set_progress(100)

            # Gộp nốt các chương còn sót lại ở cuối đợt chạy
            if self.chk_merge_files.isChecked():
                group_size = self.spn_group_size.value()
                if group_size > 0 and self._current_group_results:
                    self._merge_current_group()
                elif group_size == 0 and self._batch_results:
                    self._current_group_results = self._batch_results
                    self._merge_current_group()
            return

        chapter_path = self._batch_files_to_process[self._batch_index]
        chapter_name = os.path.splitext(os.path.basename(chapter_path))[0]
        
        engine_name = self.engine_combo.currentText()
        fmt = "mp3" if "Edge-TTS" in engine_name or "gTTS" in engine_name else "wav"
        
        output_path = os.path.join(self.output_picker.text().strip(), f"{chapter_name}.{fmt}")
        srt_path = os.path.join(self.output_picker.text().strip(), f"{chapter_name}.srt") if self.chk_export_srt.isChecked() and self.chk_export_srt.isEnabled() else None

        # Kiểm tra chương đã hoàn thành (trong manifest hoặc file thực tế vẫn còn tồn tại)
        is_completed = (hasattr(self, "_completed_chapters") and chapter_name in self._completed_chapters) or \
                       (os.path.isfile(output_path) and os.path.getsize(output_path) > 1024)

        # Check if already exists and is non-empty
        if self.chk_skip_existing.isChecked() and is_completed:
            self.log.append(f"  ⏭ Đã hoàn thành: {chapter_name} - Bỏ qua")
            
            # Đảm bảo ghi nhận vào nhật ký
            self._mark_chapter_completed(self.output_picker.text().strip(), chapter_name)
            
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

        engine_map = {
            "Edge-TTS (Microsoft)": "edge-tts",
            "gTTS (Google)": "gtts",
            "OmniVoice (Local)": "omnivoice",
        }
        config = TTSConfig(
            engine=engine_map.get(self.engine_combo.currentText(), "edge-tts"),
            voice=self.voice_combo.currentText(),
            speed=self.speed_slider.value() / 100.0,
            pitch=self.pitch_slider.value(),
        )

        pct = int(self._batch_index / len(self._batch_files_to_process) * 100)
        self.progress.set_progress(pct)

        self._worker = TTSWorker(text, output_path, config, srt_path=srt_path)
        self._active_workers.append(self._worker)
        self._worker.progress.connect(self.log.append)
        self._worker.work_completed.connect(self._on_chapter_done)
        self._worker.error.connect(self._on_chapter_error)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_chapter_done(self):
        chapter_path = self._batch_files_to_process[self._batch_index]
        chapter_name = os.path.splitext(os.path.basename(chapter_path))[0]
        
        engine_name = self.engine_combo.currentText()
        fmt = "mp3" if "Edge-TTS" in engine_name or "gTTS" in engine_name else "wav"
        
        output_path = os.path.join(self.output_picker.text().strip(), f"{chapter_name}.{fmt}")
        srt_path = os.path.join(self.output_picker.text().strip(), f"{chapter_name}.srt") if self.chk_export_srt.isChecked() and self.chk_export_srt.isEnabled() else None
        
        # Đánh dấu đã hoàn thành vào manifest
        self._mark_chapter_completed(self.output_picker.text().strip(), chapter_name)

        item = {"audio_path": output_path, "srt_path": srt_path}
        self._batch_results.append(item)
        self._current_group_results.append(item)
        
        # Kiểm tra gộp cuốn chiếu ngay khi tạo xong file
        self._check_and_trigger_merge()

        self._batch_index += 1
        self._process_next_chapter()

    def _on_chapter_error(self, msg):
        self.log.append(f"  Error: {msg}")
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
            
        engine_name = self.engine_combo.currentText()
        fmt = "mp3" if "Edge-TTS" in engine_name or "gTTS" in engine_name else "wav"
        
        merged_audio = os.path.join(self.output_picker.text().strip(), f"{name_str}.{fmt}")
        merged_srt = os.path.join(self.output_picker.text().strip(), f"{name_str}.srt")
        
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

    def _on_worker_finished(self):
        sender = self.sender()
        if sender in self._active_workers:
            self._active_workers.remove(sender)
        sender.deleteLater()
        if self._worker == sender:
            self._worker = None

    def save_session(self):
        """Save TTS session settings."""
        import json
        import os
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_dir = os.path.join(project_root, "config")
            os.makedirs(config_dir, exist_ok=True)
            session_path = os.path.join(config_dir, "tts_session.json")
            
            session = {
                "chapters_dir": self.chapters_picker.text(),
                "output_dir": self.output_picker.text(),
                "engine": self.engine_combo.currentText(),
                "voice": self.voice_combo.currentText(),
                "speed": self.speed_slider.value(),
                "pitch": self.pitch_slider.value(),
                "chk_skip_existing": self.chk_skip_existing.isChecked(),
                "chk_export_srt": self.chk_export_srt.isChecked(),
                "chk_merge_files": self.chk_merge_files.isChecked(),
                "spn_merge_start": self.spn_merge_start.value(),
                "spn_merge_end": self.spn_merge_end.value(),
                "spn_group_size": self.spn_group_size.value()
            }
            with open(session_path, "w", encoding="utf-8") as f:
                json.dump(session, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def load_session(self):
        """Load TTS session settings."""
        import json
        import os
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            session_path = os.path.join(project_root, "config", "tts_session.json")
            if not os.path.isfile(session_path):
                return
            with open(session_path, "r", encoding="utf-8") as f:
                session = json.load(f)
            
            self.chapters_picker.setText(session.get("chapters_dir", ""))
            self.output_picker.setText(session.get("output_dir", ""))
            saved_engine = session.get("engine", "")
            if self.engine_combo.findText(saved_engine) >= 0:
                self.engine_combo.setCurrentText(saved_engine)
            self.voice_combo.setCurrentText(session.get("voice", ""))
            self.speed_slider.setValue(session.get("speed", 100))
            self.pitch_slider.setValue(session.get("pitch", 0))
            self.chk_skip_existing.setChecked(session.get("chk_skip_existing", True))
            
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
        except Exception:
            pass

    def _connect_session_signals(self):
        self.chapters_picker._line_edit.textChanged.connect(lambda: self.save_session())
        self.output_picker._line_edit.textChanged.connect(lambda: self.save_session())
        self.engine_combo.currentTextChanged.connect(lambda: self.save_session())
        self.voice_combo.currentTextChanged.connect(lambda: self.save_session())
        self.speed_slider.valueChanged.connect(lambda: self.save_session())
        self.pitch_slider.valueChanged.connect(lambda: self.save_session())
        self.chk_skip_existing.toggled.connect(lambda: self.save_session())
        self.chk_export_srt.toggled.connect(lambda: self.save_session())
        self.chk_merge_files.toggled.connect(lambda: self.save_session())
        self.spn_merge_start.valueChanged.connect(lambda: self.save_session())
        self.spn_merge_end.valueChanged.connect(lambda: self.save_session())
        self.spn_group_size.valueChanged.connect(lambda: self.save_session())

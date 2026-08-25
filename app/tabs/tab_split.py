"""Tab Split — Tách truyện thành từng chương."""

import os
import glob
import threading

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QGridLayout, QComboBox, QSpinBox, QPushButton,
    QSplitter, QListWidget, QLineEdit, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QObject
from app.widgets import PathPicker, LogViewer, ProgressWidget, ChapterEditor


class SplitSignals(QObject):
    log_msg = Signal(str)
    chapters_loaded = Signal(list)
    done = Signal()


class TabSplit(QWidget):
    """Tách file truyện thành từng chương riêng biệt."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sig = SplitSignals()
        self.chapter_files = []
        self.stop_event = None
        self._build_ui()
        self._connect()
        self.load_session()
        self._connect_session_signals()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        header = QLabel("Tách Chương")
        header.setProperty("heading", True)
        layout.addWidget(header)

        # File + Output
        self.file_picker = PathPicker(
            "Chọn file truyện",
            file_filter="Hỗ trợ (*.txt *.epub *.docx *.pdf);;All (*.*)"
        )
        layout.addWidget(self.file_picker)

        self.output_picker = PathPicker("Thư mục xuất chương", is_directory=True)
        layout.addWidget(self.output_picker)

        # Pattern config
        config_row = QHBoxLayout()
        config_row.addWidget(QLabel("Pattern:"))
        self.pattern_combo = QComboBox()
        self.pattern_combo.addItems([
            r"Chương\s+\d+", r"Chapter\s+\d+", r"Hồi\s+\d+",
            r"Quyển\s+\d+", r"Phần\s+\d+", r"Part\s+\d+",
            r"Volume\s+\d+", r"Book\s+\d+", r"第.+章",
            r"\d+\.\s+",
        ])
        config_row.addWidget(self.pattern_combo, 1)

        config_row.addWidget(QLabel("Min từ:"))
        self.min_words_spin = QSpinBox()
        self.min_words_spin.setRange(10, 500)
        self.min_words_spin.setValue(50)
        config_row.addWidget(self.min_words_spin)

        self.auto_detect_btn = QPushButton("Tự phát hiện")
        self.auto_detect_btn.clicked.connect(self._handle_auto_detect)
        config_row.addWidget(self.auto_detect_btn)

        layout.addLayout(config_row)

        # Split button
        btn_row = QHBoxLayout()
        self.split_btn = QPushButton("Tách chương")
        self.split_btn.setObjectName("primaryBtn")
        self.split_btn.setFixedHeight(36)
        self.split_btn.clicked.connect(self._handle_split)
        btn_row.addWidget(self.split_btn)

        self.load_folder_btn = QPushButton("Nạp thư mục chương")
        self.load_folder_btn.setFixedHeight(36)
        self.load_folder_btn.clicked.connect(self._handle_load_folder)
        btn_row.addWidget(self.load_folder_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.progress = ProgressWidget()
        layout.addWidget(self.progress)

        # Main content: chapter list + editor
        main_splitter = QSplitter(Qt.Horizontal)

        # Left: chapter list + find
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_layout.addWidget(QLabel("Danh sách chương"))

        self.chapter_list = QListWidget()
        self.chapter_list.currentRowChanged.connect(self._on_chapter_selected)
        left_layout.addWidget(self.chapter_list, 1)

        # Find & mass delete
        find_row = QHBoxLayout()
        self.find_entry = QLineEdit()
        self.find_entry.setPlaceholderText("Tìm từ cần xóa hàng loạt...")
        find_row.addWidget(self.find_entry, 1)
        self.delete_btn = QPushButton("Xóa hàng loạt")
        self.delete_btn.clicked.connect(self._handle_mass_delete)
        find_row.addWidget(self.delete_btn)
        left_layout.addLayout(find_row)

        main_splitter.addWidget(left)

        # Right: editor + log
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_layout.addWidget(QLabel("Nội dung chương (auto-save)"))
        self.editor = ChapterEditor()
        right_layout.addWidget(self.editor, 1)

        self.log = LogViewer(height=120)
        right_layout.addWidget(self.log)

        main_splitter.addWidget(right)
        main_splitter.setSizes([300, 700])

        layout.addWidget(main_splitter, 1)

    def _connect(self):
        self.sig.log_msg.connect(lambda msg: self.log.append(msg, "info"))
        self.sig.chapters_loaded.connect(self._populate_chapters)
        self.sig.done.connect(self._on_done)

    def _handle_auto_detect(self):
        file_path = self.file_picker.text()
        if not file_path:
            return
        try:
            from process.reader.reader import read_file
            from process.splitter.splitter import auto_detect_pattern
            text = read_file(file_path)
            pattern, count = auto_detect_pattern(text)
            idx = self.pattern_combo.findText(pattern)
            if idx >= 0:
                self.pattern_combo.setCurrentIndex(idx)
            self.log.append(f"Phát hiện pattern: {pattern} ({count} chương)", "success")
        except Exception as e:
            self.log.append(f"Lỗi: {e}", "error")

    def _handle_split(self):
        file_path = self.file_picker.text()
        output_dir = self.output_picker.text()
        if not file_path or not output_dir:
            QMessageBox.warning(self, "Lỗi", "Chọn file và thư mục xuất!")
            return

        pattern = self.pattern_combo.currentText()
        min_words = self.min_words_spin.value()
        self.split_btn.setEnabled(False)
        self.log.clear()
        self.progress.reset()

        def task():
            try:
                from process.reader.reader import read_file
                from process.splitter.splitter import split_chapters
                import re
                self.sig.log_msg.emit(f"Đang đọc file: {file_path}")
                text = read_file(file_path)
                self.sig.log_msg.emit(f"Đọc xong: {len(text):,} ký tự")

                result = split_chapters(text, pattern=pattern, min_words=min_words)
                total = result.chapter_count
                self.sig.log_msg.emit(f"Tìm thấy {total} chương (pattern: {pattern})")

                os.makedirs(output_dir, exist_ok=True)
                width = len(str(total))

                for i, ch in enumerate(result.chapters):
                    safe_title = re.sub(r'[\\/:*?"<>|]', '_', ch.title)[:50]
                    filename = f"{ch.id:0{width}d}_{safe_title}.txt"
                    filepath = os.path.join(output_dir, filename)

                    if not os.path.exists(filepath):
                        with open(filepath, "w", encoding="utf-8") as f:
                            f.write(ch.content)
                        self.sig.log_msg.emit(f"Saved: {filename} ({ch.word_count} từ)")
                    else:
                        self.sig.log_msg.emit(f"Bỏ qua: {filename} (đã có)")

                import re
                files = sorted(glob.glob(os.path.join(output_dir, "*.txt")), key=lambda x: [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', x)])
                self.sig.chapters_loaded.emit(files)
                self.sig.log_msg.emit(f"Hoàn tất! {total} chương")
            except Exception as e:
                self.sig.log_msg.emit(f"Lỗi: {e}")
            self.sig.done.emit()

        threading.Thread(target=task, daemon=True).start()

    def _populate_chapters(self, files):
        self.chapter_files = files
        self.chapter_list.blockSignals(True)
        self.chapter_list.clear()
        for f in files:
            name = os.path.splitext(os.path.basename(f))[0]
            self.chapter_list.addItem(name)
        self.chapter_list.blockSignals(False)
        if files:
            self.chapter_list.setCurrentRow(0)

    def _on_chapter_selected(self, row):
        if 0 <= row < len(self.chapter_files):
            self.editor.load_file(self.chapter_files[row])

    def _handle_mass_delete(self):
        search = self.find_entry.text().strip()
        if not search or not self.chapter_files:
            return

        count = 0
        for path in self.chapter_files:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                new_content = content.replace(search, "")
                if new_content != content:
                    count += 1
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(new_content)
            except Exception:
                pass
        self.log.append(f"Đã xóa '{search}' khỏi {count} chương", "success")
        # Reload current chapter
        row = self.chapter_list.currentRow()
        if 0 <= row < len(self.chapter_files):
            self.editor.load_file(self.chapter_files[row])

    def _handle_load_folder(self):
        from PySide6.QtWidgets import QFileDialog
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục chứa các chương truyện")
        if not folder:
            return
        
        self.output_picker.set_text(folder)
        
        import glob
        import re
        files = sorted(glob.glob(os.path.join(folder, "*.txt")), key=lambda x: [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', x)])
        if not files:
            QMessageBox.warning(self, "Lỗi", "Không tìm thấy file .txt nào trong thư mục này!")
            return
            
        self._populate_chapters(files)
        self.log.append(f"Đã nạp {len(files)} chương từ thư mục: {folder}", "success")

    def _on_done(self):
        self.split_btn.setEnabled(True)

    def save_session(self):
        """Save split session settings."""
        import json
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_dir = os.path.join(project_root, "config")
            os.makedirs(config_dir, exist_ok=True)
            session_path = os.path.join(config_dir, "split_session.json")
            
            session = {
                "file_path": self.file_picker.text(),
                "output_dir": self.output_picker.text(),
                "pattern": self.pattern_combo.currentText(),
                "min_words": self.min_words_spin.value()
            }
            with open(session_path, "w", encoding="utf-8") as f:
                json.dump(session, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def load_session(self):
        """Load split session settings."""
        import json
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            session_path = os.path.join(project_root, "config", "split_session.json")
            if not os.path.isfile(session_path):
                return
            with open(session_path, "r", encoding="utf-8") as f:
                session = json.load(f)
            
            self.file_picker.setText(session.get("file_path", ""))
            self.output_picker.setText(session.get("output_dir", ""))
            self.pattern_combo.setCurrentText(session.get("pattern", ""))
            self.min_words_spin.setValue(session.get("min_words", 50))
            
            # Automatically load chapters list if output dir contains txt files
            out_dir = self.output_picker.text()
            if out_dir and os.path.isdir(out_dir):
                import glob
                import re
                files = sorted(glob.glob(os.path.join(out_dir, "*.txt")), key=lambda x: [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', x)])
                if files:
                    self._populate_chapters(files)
        except Exception:
            pass

    def _connect_session_signals(self):
        self.file_picker._line_edit.textChanged.connect(lambda: self.save_session())
        self.output_picker._line_edit.textChanged.connect(lambda: self.save_session())
        self.pattern_combo.currentTextChanged.connect(lambda: self.save_session())
        self.min_words_spin.valueChanged.connect(lambda: self.save_session())

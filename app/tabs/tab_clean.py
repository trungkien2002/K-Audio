"""Tab Clean — Làm sạch nội dung truyện nâng cao.

Tích hợp Hệ thống AI Lai (Hybrid AI) tự sinh quy tắc Regex từ 20 chương mẫu rải rác,
lưu trữ bộ quy tắc theo dự án riêng biệt, kiểm tra dị biệt và tạo luật AI 1-Click.
"""

import os
import re
import json
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QListWidget, QListWidgetItem,
    QPushButton, QPlainTextEdit, QCheckBox, QSplitter, QMessageBox, QMenu,
    QLineEdit, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QTextCharFormat, QColor, QTextCursor, QAction
from app.theme import THEME_COLORS

LOGGER = logging.getLogger(__name__)


# ═══════════════ AI SCANNING WORKERS (THREADS) ═══════════════

class AIScanWorker(QThread):
    """Luồng xử lý quét AI mẫu chương rải rác."""
    progress = Signal(str)
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, sample_paths, gemini_key):
        super().__init__()
        self.sample_paths = sample_paths
        self.gemini_key = gemini_key

    def run(self):
        try:
            self.progress.emit("[AI] Bắt đầu phân tích mẫu thử đa điểm...")
            from process.cleaner.ai_cleaner import analyze_samples_with_ai
            rules = analyze_samples_with_ai(self.sample_paths, self.gemini_key)
            self.finished.emit(rules)
        except Exception as e:
            self.error.emit(str(e))


class AISingleRuleWorker(QThread):
    """Luồng xử lý sinh quy tắc đơn từ text người dùng bôi đen."""
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, text, gemini_key):
        super().__init__()
        self.text = text
        self.gemini_key = gemini_key

    def run(self):
        try:
            from process.cleaner.ai_cleaner import generate_rule_from_text
            rule = generate_rule_from_text(self.text, self.gemini_key)
            self.finished.emit(rule)
        except Exception as e:
            self.error.emit(str(e))


# ═══════════════ MAIN TAB WIDGET ═══════════════

class TabClean(QWidget):
    """Làm sạch văn bản nâng cao theo file/folder chương truyện."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._chapter_files = []
        self._scanned_issues = []  # List of dict: {file_path, line_num, pattern, pattern_regex, content}
        self._search_results = []  # List of dict: {file_path, occurrences}
        self._ai_worker = None
        self._single_worker = None
        self._build_ui()
        self.load_session()
        self._connect_session_signals()

    def _build_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(10)

        # Splitter chính: Bảng điều khiển (Trái) & Diff/Preview (Phải)
        main_splitter = QSplitter(Qt.Horizontal)

        # ═══════════════ LEFT PANEL: CONTROLS ═══════════════
        from PySide6.QtWidgets import QScrollArea
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 5, 0)
        left_layout.setSpacing(10)

        header = QLabel("Làm Sạch & Quét Watermark")
        header.setProperty("heading", True)
        left_layout.addWidget(header)

        # 1. Folder Chooser Group
        folder_group = QGroupBox("Chọn đường dẫn thư mục")
        fg_layout = QVBoxLayout(folder_group)
        fg_layout.setSpacing(6)

        in_row = QHBoxLayout()
        in_row.addWidget(QLabel("Folder chương:"))
        self.txt_input_folder = QLineEdit()
        self.txt_input_folder.setPlaceholderText("Chọn folder chứa các chương truyện .txt...")
        in_row.addWidget(self.txt_input_folder, 1)
        btn_browse_in = QPushButton("Chọn folder")
        btn_browse_in.clicked.connect(self._browse_input_folder)
        in_row.addWidget(btn_browse_in)
        fg_layout.addLayout(in_row)

        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Folder lưu:"))
        self.txt_output_folder = QLineEdit()
        self.txt_output_folder.setPlaceholderText("Chọn folder lưu truyện sau khi dọn sạch...")
        out_row.addWidget(self.txt_output_folder, 1)
        btn_browse_out = QPushButton("Chọn folder")
        btn_browse_out.clicked.connect(self._browse_output_folder)
        out_row.addWidget(btn_browse_out)
        fg_layout.addLayout(out_row)

        left_layout.addWidget(folder_group)

        # 2. Project Custom AI Rules Group [NEW]
        ai_rules_group = QGroupBox("Quy tắc dự án (AI sinh)")
        ai_rules_lay = QVBoxLayout(ai_rules_group)
        
        self.lst_project_rules = QListWidget()
        self.lst_project_rules.setFixedHeight(95)
        self.lst_project_rules.itemChanged.connect(self._save_project_rules)
        ai_rules_lay.addWidget(self.lst_project_rules)
        
        ai_btn_row = QHBoxLayout()
        self.btn_ai_scan = QPushButton("Quét thông minh bằng AI")
        self.btn_ai_scan.setObjectName("primaryBtn")
        self.btn_ai_scan.clicked.connect(self._start_ai_scan)
        ai_btn_row.addWidget(self.btn_ai_scan, 1)
        
        self.btn_anomaly = QPushButton("Tìm dị biệt mới")
        self.btn_anomaly.clicked.connect(self._scan_anomalies)
        ai_btn_row.addWidget(self.btn_anomaly, 1)
        ai_rules_lay.addLayout(ai_btn_row)
        
        left_layout.addWidget(ai_rules_group)

        # 3. Filter Rules Checkbox Group
        rules_group = QGroupBox("Quy tắc mặc định")
        rg_layout = QVBoxLayout(rules_group)
        self.checkboxes = {}
        patterns = [
            ("url", "Xóa liên kết mạng (http/www/domain)"),
            ("credit", "Xóa nguồn dịch / sưu tầm / credits"),
            ("copyright", "Xóa dòng chống copy / bản quyền"),
            ("spam", "Xóa quảng cáo vote / bình luận / đánh giá"),
            ("separator", "Xóa dòng phân cách rác (***, ===)"),
            ("zero_width", "Xóa toàn bộ ký tự zero-width ẩn"),
            ("normalize", "Chuẩn hóa bảng mã Unicode (NFC)"),
        ]
        for key, label in patterns:
            cb = QCheckBox(label)
            cb.setChecked(True)
            self.checkboxes[key] = cb
            rg_layout.addWidget(cb)
        left_layout.addWidget(rules_group)

        # 4. Custom Regex Patterns Manual
        custom_group = QGroupBox("Regex tự gõ")
        cg_layout = QVBoxLayout(custom_group)
        self.txt_custom_regex = QPlainTextEdit()
        self.txt_custom_regex.setMinimumHeight(130)
        self.txt_custom_regex.setPlaceholderText("Nhập Regex tại đây — mỗi dòng là một quy tắc riêng...")
        self.txt_custom_regex.setToolTip("Mỗi dòng là một biểu thức Regex. Có thể nhập hoặc dán nhiều dòng.")
        cg_layout.addWidget(self.txt_custom_regex)
        left_layout.addWidget(custom_group)

        # 5. Action Buttons
        btn_row = QHBoxLayout()
        self.btn_scan = QPushButton("Quét phát hiện")
        self.btn_scan.setObjectName("primaryBtn")
        self.btn_scan.setFixedHeight(36)
        self.btn_scan.clicked.connect(self._scan_chapters)
        btn_row.addWidget(self.btn_scan, 1)

        self.btn_apply = QPushButton("Áp dụng dọn sạch")
        self.btn_apply.setFixedHeight(36)
        self.btn_apply.clicked.connect(self._apply_cleaning)
        btn_row.addWidget(self.btn_apply, 1)
        left_layout.addLayout(btn_row)

        # 6. Search & Destroy Group
        search_group = QGroupBox("Tìm kiếm & Xóa nhanh từ khóa")
        sg_layout = QVBoxLayout(search_group)

        search_row = QHBoxLayout()
        self.txt_search_kw = QLineEdit()
        self.txt_search_kw.setPlaceholderText("Nhập từ khóa hoặc câu cần xóa nhanh...")
        self.txt_search_kw.returnPressed.connect(self._search_keyword)
        search_row.addWidget(self.txt_search_kw, 1)
        btn_search = QPushButton("Tìm kiếm")
        btn_search.clicked.connect(self._search_keyword)
        search_row.addWidget(btn_search)
        sg_layout.addLayout(search_row)

        # Search results table
        self.table_search = QTableWidget()
        self.table_search.setColumnCount(2)
        self.table_search.setHorizontalHeaderLabels(["Chương", "Số lần xuất hiện"])
        self.table_search.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_search.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_search.verticalHeader().setVisible(False)
        self.table_search.setFixedHeight(90)
        self.table_search.itemSelectionChanged.connect(self._on_search_row_changed)
        sg_layout.addWidget(self.table_search)

        self.btn_delete_kw = QPushButton("Xác nhận xóa từ khóa khỏi các file đã chọn")
        self.btn_delete_kw.setStyleSheet(f"background-color: {THEME_COLORS['error']}; color: black; font-weight: bold;")
        self.btn_delete_kw.clicked.connect(self._delete_keyword_confirmed)
        sg_layout.addWidget(self.btn_delete_kw)

        left_layout.addWidget(search_group)

        # Stats Label
        self.lbl_stats = QLabel("Chưa quét thư mục chương.")
        self.lbl_stats.setStyleSheet(f"color: {THEME_COLORS['text_secondary']}; font-size: 11px;")
        left_layout.addWidget(self.lbl_stats)

        scroll_area.setWidget(left_widget)
        main_splitter.addWidget(scroll_area)

        # ═══════════════ RIGHT PANEL: ISSUES & PREVIEW ═══════════════
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # Table showing scanned issues
        issues_group = QGroupBox("Vấn đề phát hiện")
        ig_layout = QVBoxLayout(issues_group)
        self.table_issues = QTableWidget()
        self.table_issues.setColumnCount(3)
        self.table_issues.setHorizontalHeaderLabels(["Chương file", "Quy tắc / Loại", "Dòng vi phạm"])
        self.table_issues.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.table_issues.setColumnWidth(0, 200)
        self.table_issues.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_issues.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_issues.verticalHeader().setVisible(False)
        self.table_issues.itemSelectionChanged.connect(self._on_issue_selected)
        ig_layout.addWidget(self.table_issues)
        right_layout.addWidget(issues_group, 2)

        # Before & After side-by-side comparison (Diff)
        diff_group = QGroupBox("Xem trước so sánh (Diff Preview)")
        dg_layout = QVBoxLayout(diff_group)

        diff_splitter = QSplitter(Qt.Horizontal)

        # Left Diff Pane (Before)
        before_pane = QWidget()
        before_lay = QVBoxLayout(before_pane)
        before_lay.setContentsMargins(0, 0, 0, 0)
        before_lay.addWidget(QLabel("Trước (Original):"))
        self.txt_before = QPlainTextEdit()
        self.txt_before.setReadOnly(True)
        # Bật Context menu tùy chỉnh để bôi đen -> sinh quy tắc AI 1-Click
        self.txt_before.setContextMenuPolicy(Qt.CustomContextMenu)
        self.txt_before.customContextMenuRequested.connect(self._show_before_context_menu)
        before_lay.addWidget(self.txt_before)
        diff_splitter.addWidget(before_pane)

        # Right Diff Pane (After)
        after_pane = QWidget()
        after_lay = QVBoxLayout(after_pane)
        after_lay.setContentsMargins(0, 0, 0, 0)
        after_lay.addWidget(QLabel("Sau (Cleaned):"))
        self.txt_after = QPlainTextEdit()
        self.txt_after.setReadOnly(True)
        after_lay.addWidget(self.txt_after)
        diff_splitter.addWidget(after_pane)

        dg_layout.addWidget(diff_splitter)
        right_layout.addWidget(diff_group, 3)

        main_splitter.addWidget(right_widget)

        # Set ratio to Splitter
        main_splitter.setSizes([380, 620])
        main_layout.addWidget(main_splitter)

    # ═══════════════ PATH DIRECTORY SELECTORS ═══════════════

    def _browse_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục chứa các chương truyện")
        if folder:
            self.txt_input_folder.setText(folder)
            if not self.txt_output_folder.text():
                self.txt_output_folder.setText(f"{folder}_cleaned")
            self._load_chapter_files(folder)

    def _load_chapter_files(self, folder):
        try:
            import re
            self._chapter_files = sorted([
                os.path.join(folder, f) for f in os.listdir(folder)
                if f.lower().endswith('.txt') and os.path.isfile(os.path.join(folder, f))
            ], key=lambda x: [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', x)])
            self.lbl_stats.setText(f"Đã load {len(self._chapter_files)} file chương.")
            # Tự động tải quy tắc riêng của truyện này
            self._load_project_rules()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể đọc danh sách file: {e}")

    def _browse_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu file đã làm sạch")
        if folder:
            self.txt_output_folder.setText(folder)

    # ═══════════════ SETTINGS LOADING ═══════════════

    def _get_gemini_key(self):
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            settings_path = os.path.join(project_root, "config", "settings.json")
            if os.path.isfile(settings_path):
                with open(settings_path, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                return settings.get("gemini_key", "")
        except Exception:
            pass
        return ""

    # ═══════════════ PROJECT RULES LOADING & SAVING ═══════════════

    def _get_project_name(self):
        folder = self.txt_input_folder.text().strip()
        if not folder:
            return "default"
        normalized = os.path.normpath(folder)
        parts = normalized.split(os.sep)
        generic_names = {"chapter", "chapters", "txt", "raw", "audio", "output", "cleaned"}
        for part in reversed(parts):
            if part and part.lower() not in generic_names:
                return re.sub(r'[\\/:*?"<>| ]', '_', part)
        return "default"

    def _get_rules_filepath(self):
        project_name = self._get_project_name()
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_dir = os.path.join(project_root, "config")
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, f"clean_rules_{project_name}.json")

    def _save_project_rules(self):
        filepath = self._get_rules_filepath()
        rules = []
        for i in range(self.lst_project_rules.count()):
            item = self.lst_project_rules.item(i)
            # Item text is stored as "Name - Pattern", data(Qt.UserRole) is pattern
            parts = item.text().split(" - ", 1)
            name = parts[0] if parts else "Quy tắc"
            rules.append({
                "pattern": item.data(Qt.UserRole),
                "name": name,
                "reason": item.toolTip(),
                "checked": item.checkState() == Qt.Checked
            })
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(rules, f, indent=2, ensure_ascii=False)
        except Exception as e:
            LOGGER.warning(f"Failed to save project rules: {e}")

    def _load_project_rules(self):
        self.lst_project_rules.blockSignals(True)
        self.lst_project_rules.clear()
        filepath = self._get_rules_filepath()
        if os.path.isfile(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    rules = json.load(f)
                for r in rules:
                    self._add_project_rule(r["pattern"], r["name"], r["reason"], r.get("checked", True))
            except Exception as e:
                LOGGER.warning(f"Failed to load project rules: {e}")
        self.lst_project_rules.blockSignals(False)

    def _add_project_rule(self, pattern, name, reason, checked=True):
        # Tránh trùng lặp
        for i in range(self.lst_project_rules.count()):
            item = self.lst_project_rules.item(i)
            if item.data(Qt.UserRole) == pattern:
                item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
                return

        item = QListWidgetItem(f"{name} - {pattern}")
        item.setData(Qt.UserRole, pattern)
        item.setToolTip(reason)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        self.lst_project_rules.addItem(item)

    # ═══════════════ ACTION: HYBRID AI SAMPLING SCAN ═══════════════

    def _update_status(self, msg):
        """Cập nhật thông tin trạng thái lên cả giao diện tab và QStatusBar của cửa sổ chính."""
        self.lbl_stats.setText(msg)
        main_win = self.window()
        if main_win and hasattr(main_win, "statusBar"):
            sb = main_win.statusBar()
            if sb:
                sb.showMessage(f"Làm Sạch: {msg}")

    def _start_ai_scan(self):
        if not self._chapter_files:
            QMessageBox.warning(self, "AI Quét", "Vui lòng tải thư mục chương trước!")
            return

        gemini_key = self._get_gemini_key()
        if not gemini_key:
            QMessageBox.warning(self, "Lỗi", "Chưa cấu hình Gemini API Key trong tab Settings!")
            return

        from process.cleaner.ai_cleaner import sample_chapter_paths
        samples = sample_chapter_paths(self._chapter_files, count=10)

        self.btn_ai_scan.setEnabled(False)
        self._update_status("Đang lấy mẫu đa điểm và phân tích AI...")

        self._ai_worker = AIScanWorker(samples, gemini_key)
        self._ai_worker.progress.connect(self._update_status)
        self._ai_worker.finished.connect(self._on_ai_scan_finished)
        self._ai_worker.error.connect(self._on_ai_scan_error)
        self._ai_worker.start()

    def _on_ai_scan_finished(self, rules):
        self.btn_ai_scan.setEnabled(True)
        self._update_status(f"AI đã hoàn tất phân tích! Tìm thấy {len(rules)} quy tắc.")

        if not rules:
            QMessageBox.information(self, "AI Quét", "AI không phát hiện bất kỳ watermark lặp lại nào trong các mẫu chương thử.")
            return

        # Nạp các quy tắc mới vào giao diện
        self.lst_project_rules.blockSignals(True)
        added_count = 0
        for r in rules:
            pattern = r.get("pattern")
            if pattern:
                self._add_project_rule(pattern, r.get("name", "AI Rule"), r.get("reason", ""))
                added_count += 1
        self.lst_project_rules.blockSignals(False)

        # Lưu lại quy tắc
        self._save_project_rules()

        # Tự động chạy lại chức năng Quét Phát Hiện để người dùng thấy ngay kết quả lỗi quảng cáo đã lọc
        self._scan_chapters()

        QMessageBox.information(self, "AI Quét thành công", f"Đã sinh và lưu {added_count} quy tắc Regex AI vào tệp cấu hình của truyện này. Hệ thống đã tự động chạy quét phát hiện lỗi.")

    def _on_ai_scan_error(self, err_msg):
        self.btn_ai_scan.setEnabled(True)
        self._update_status("Lỗi quét AI.")
        QMessageBox.critical(self, "Lỗi AI Lai", f"Không thể quét AI mẫu thử:\n{err_msg}")

    # ═══════════════ ACTION: ANOMALY CHECKER (DỊ BIỆT ĐỘNG) ═══════════════

    def _scan_anomalies(self):
        """Quét tìm các dòng chứa từ khóa rủi ro cao mà bộ lọc Regex hiện tại chưa xử lý được."""
        if not self._chapter_files:
            QMessageBox.warning(self, "Dị biệt", "Vui lòng chọn folder chương trước!")
            return

        self._scanned_issues.clear()
        self.table_issues.setRowCount(0)

        high_risk_words = ["truyenfull", "khotruyenchu", "ăn cắp", "reup", "đọc tại", "chuyển ngữ", ".com", ".vn", "tải tại", "chấm cơm", "truyenyy"]
        anomaly_count = 0

        for fpath in self._chapter_files:
            content = self._read_file_content(fpath)
            if not content:
                continue

            # Run clean pipeline
            cleaned, _ = self._clean_text_with_ui_options(content)

            # Check for anomalies on cleaned text line-by-line
            lines = cleaned.split("\n")
            for i, line in enumerate(lines):
                # Search high risk words in cleaned line
                matched_words = [w for w in high_risk_words if w in line.lower()]
                if matched_words:
                    self._scanned_issues.append({
                        "file_path": fpath,
                        "line_num": i + 1,
                        "pattern": "Cảnh báo Dị biệt",
                        "pattern_regex": "|".join([re.escape(w) for w in matched_words]),
                        "content": line.strip(),
                    })
                    
                    row = self.table_issues.rowCount()
                    self.table_issues.insertRow(row)
                    
                    filename_item = QTableWidgetItem(os.path.basename(fpath))
                    filename_item.setData(Qt.UserRole, fpath)
                    
                    self.table_issues.setItem(row, 0, filename_item)
                    self.table_issues.setItem(row, 1, QTableWidgetItem("Dị biệt"))
                    self.table_issues.setItem(row, 2, QTableWidgetItem(line.strip()))
                    
                    anomaly_count += 1

        self.lbl_stats.setText(f"Tìm thấy {anomaly_count} dị biệt chưa được lọc bằng các quy tắc hiện tại.")
        if anomaly_count == 0:
            QMessageBox.information(self, "Không phát hiện dị biệt", "Tuyệt vời! Không phát hiện watermark rò rỉ nào.")

    # ═══════════════ ACTION: SCAN WATERMARKS (REGULAR ENGINE) ═══════════════

    def _build_active_patterns(self):
        """Tổng hợp các Regex mặc định được check + Regex tự gõ + Quy tắc AI."""
        active_patterns = []
        
        # 1. Thêm các quy tắc mặc định nếu checkbox tương ứng được chọn
        from process.cleaner.filter_engine import DEFAULT_PATTERNS
        
        # Ánh xạ từ checkbox key sang các nhóm pattern_name tương ứng
        mapping = {
            "url": ["URL", "Domain spam"],
            "credit": ["Source credit"],
            "copyright": ["Copyright"],
            "spam": ["Spam", "Spam vote", "Anti-piracy"],
            "separator": ["Separator"]
        }
        
        for key, cb in self.checkboxes.items():
            if cb.isChecked() and key in mapping:
                allowed_names = mapping[key]
                # Lấy các pattern từ DEFAULT_PATTERNS thỏa mãn
                for pat, name in DEFAULT_PATTERNS:
                    if name in allowed_names:
                        active_patterns.append(pat)

        # 2. Quy tắc tự gõ
        custom = self.txt_custom_regex.toPlainText().strip()
        if custom:
            active_patterns.extend([p.strip() for p in custom.split("\n") if p.strip()])
            
        # 3. Quy tắc AI của dự án
        for i in range(self.lst_project_rules.count()):
            item = self.lst_project_rules.item(i)
            if item.checkState() == Qt.Checked:
                pattern = item.data(Qt.UserRole)
                if pattern:
                    active_patterns.append(pattern)
                    
        return active_patterns

    def _clean_text_with_ui_options(self, content):
        """Làm sạch văn bản sử dụng toàn bộ tùy chọn trên giao diện UI."""
        from process.cleaner.filter_engine import clean_text
        custom_patterns = self._build_active_patterns()
        remove_zw = self.checkboxes["zero_width"].isChecked()
        norm_unicode = self.checkboxes["normalize"].isChecked()
        return clean_text(
            content,
            custom_patterns=custom_patterns,
            remove_zw=remove_zw,
            norm_unicode=norm_unicode
        )

    def _scan_chapters(self):
        if not self._chapter_files:
            folder = self.txt_input_folder.text().strip()
            if folder and os.path.isdir(folder):
                self._load_chapter_files(folder)
            else:
                QMessageBox.warning(self, "Quét", "Vui lòng chọn thư mục chứa chương trước!")
                return

        self._scanned_issues.clear()
        self.table_issues.setRowCount(0)

        scan_count = 0
        issue_total = 0

        for fpath in self._chapter_files:
            try:
                content = self._read_file_content(fpath)
                if not content:
                    continue
                
                # Dry clean to find issues
                _, issues = self._clean_text_with_ui_options(content)
                
                # Append to table
                for issue in issues:
                    self._scanned_issues.append({
                        "file_path": fpath,
                        "line_num": issue.line_num,
                        "pattern": issue.pattern_name,
                        "pattern_regex": issue.pattern_regex,
                        "content": issue.original_line,
                    })
                    
                    row = self.table_issues.rowCount()
                    self.table_issues.insertRow(row)
                    
                    filename_item = QTableWidgetItem(os.path.basename(fpath))
                    filename_item.setData(Qt.UserRole, fpath)
                    
                    self.table_issues.setItem(row, 0, filename_item)
                    self.table_issues.setItem(row, 1, QTableWidgetItem(issue.pattern_name))
                    self.table_issues.setItem(row, 2, QTableWidgetItem(issue.original_line))
                    
                    issue_total += 1
                
                scan_count += 1
            except Exception as e:
                self._update_status(f"Lỗi quét file {os.path.basename(fpath)}: {e}")

        self._update_status(f"Đã quét {scan_count}/{len(self._chapter_files)} file. Phát hiện {issue_total} lỗi quảng cáo.")
        if issue_total == 0:
            QMessageBox.information(self, "Hoàn tất quét", "Không phát hiện quảng cáo hay watermark nào!")

    # ═══════════════ ACTION: APPLY CLEANING ═══════════════

    def _apply_cleaning(self):
        if not self._chapter_files:
            QMessageBox.warning(self, "Làm sạch", "Không có chương nào để làm sạch.")
            return

        out_dir = self.txt_output_folder.text().strip()
        if not out_dir:
            out_dir = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu kết quả")
            if not out_dir:
                return
            self.txt_output_folder.setText(out_dir)

        os.makedirs(out_dir, exist_ok=True)

        success_count = 0
        for fpath in self._chapter_files:
            try:
                content = self._read_file_content(fpath)
                if not content:
                    continue

                cleaned, _ = self._clean_text_with_ui_options(content)

                out_path = os.path.join(out_dir, os.path.basename(fpath))
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(cleaned)
                success_count += 1
            except Exception as e:
                self.lbl_stats.setText(f"Lỗi lưu file {os.path.basename(fpath)}: {e}")

        self.lbl_stats.setText(f"Đã lưu thành công {success_count} chương đã làm sạch vào: {out_dir}")
        QMessageBox.information(self, "Thành công", f"Đã dọn dẹp và xuất {success_count} file sang {out_dir}!")

    # ═══════════════ INTERACTIVE SEARCH & DESTROY ═══════════════

    def _search_keyword(self):
        kw = self.txt_search_kw.text().strip()
        if not kw:
            QMessageBox.warning(self, "Tìm kiếm", "Vui lòng nhập từ khóa cần tìm!")
            return

        if not self._chapter_files:
            QMessageBox.warning(self, "Tìm kiếm", "Chưa tải danh sách file chương!")
            return

        self._search_results.clear()
        self.table_search.setRowCount(0)

        for fpath in self._chapter_files:
            try:
                content = self._read_file_content(fpath)
                if not content:
                    continue

                count = len(re.findall(re.escape(kw), content, re.IGNORECASE))
                if count > 0:
                    self._search_results.append({
                        "file_path": fpath,
                        "occurrences": count
                    })
                    row = self.table_search.rowCount()
                    self.table_search.insertRow(row)

                    item_name = QTableWidgetItem(os.path.basename(fpath))
                    item_name.setData(Qt.UserRole, fpath)
                    
                    self.table_search.setItem(row, 0, item_name)
                    self.table_search.setItem(row, 1, QTableWidgetItem(str(count)))
            except Exception as e:
                self.lbl_stats.setText(f"Lỗi đọc file tìm kiếm: {e}")

        self.lbl_stats.setText(f"Tìm thấy từ khóa '{kw}' xuất hiện tại {len(self._search_results)} chương.")
        if not self._search_results:
            QMessageBox.information(self, "Tìm kiếm", f"Không tìm thấy cụm từ '{kw}' trong bất kỳ chương nào.")

    def _delete_keyword_confirmed(self):
        kw = self.txt_search_kw.text().strip()
        if not kw:
            QMessageBox.warning(self, "Xóa từ khóa", "Không có từ khóa nào được chỉ định!")
            return

        selected_rows = self.table_search.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Xóa từ khóa", "Vui lòng chọn các chương muốn xóa từ danh sách tìm thấy!")
            return

        ret = QMessageBox.question(
            self, "Xác nhận xóa",
            f"Bạn có chắc muốn xóa cụm từ '{kw}' khỏi {len(selected_rows)} chương đã chọn?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ret != QMessageBox.Yes:
            return

        deleted_total = 0
        for index in selected_rows:
            row = index.row()
            fpath = self.table_search.item(row, 0).data(Qt.UserRole)
            try:
                content = self._read_file_content(fpath)
                if not content:
                    continue

                cleaned = re.sub(re.escape(kw), "", content, flags=re.IGNORECASE)
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(cleaned)
                
                deleted_total += 1
            except Exception as e:
                LOGGER.warning(f"Không thể xóa từ ở file {os.path.basename(fpath)}: {e}")

        QMessageBox.information(self, "Hoàn tất", f"Đã xóa hoàn thành cụm từ '{kw}' tại {deleted_total} chương!")
        self._search_keyword()

    # ═══════════════ CONTEXT MENU: BÔI ĐEN -> TẠO QUY TẮC AI ═══════════════

    def _show_before_context_menu(self, pos):
        menu = self.txt_before.createStandardContextMenu()
        cursor = self.txt_before.textCursor()
        selected_text = cursor.selectedText().strip()

        if selected_text:
            menu.addSeparator()
            action = QAction("Tạo quy tắc lọc bằng AI", menu)
            action.triggered.connect(lambda: self._generate_rule_for_selected(selected_text))
            menu.addAction(action)

        menu.exec_(self.txt_before.mapToGlobal(pos))

    def _generate_rule_for_selected(self, text):
        gemini_key = self._get_gemini_key()
        if not gemini_key:
            QMessageBox.warning(self, "Lỗi", "Chưa cấu hình Gemini API Key trong tab Settings!")
            return

        self.lbl_stats.setText("Đang sinh quy tắc Regex AI từ văn bản đã chọn...")
        
        self._single_worker = AISingleRuleWorker(text, gemini_key)
        self._single_worker.finished.connect(self._on_single_rule_generated)
        self._single_worker.error.connect(lambda err: QMessageBox.warning(self, "Lỗi sinh luật AI", err))
        self._single_worker.start()

    def _on_single_rule_generated(self, rule):
        pattern = rule.get("pattern")
        if not pattern:
            return

        self.lst_project_rules.blockSignals(True)
        self._add_project_rule(pattern, rule.get("name", "Tùy chỉnh"), rule.get("reason", ""))
        self.lst_project_rules.blockSignals(False)
        
        self._save_project_rules()
        self.lbl_stats.setText("Đã lưu quy tắc lọc mới do AI sinh.")
        QMessageBox.information(
            self, "AI Sinh Luật 1-Click",
            f"Đã tạo thành công quy tắc lọc:\n"
            f"Pattern: {pattern}\n"
            f"Tên: {rule.get('name')}\n"
            f"Giải thích: {rule.get('reason')}"
        )

    # ═══════════════ EVENT SELECTION HANDLERS (PREVIEW/DIFF) ═══════════════

    def _on_issue_selected(self):
        selected = self.table_issues.currentRow()
        if selected < 0:
            return

        fpath = self.table_issues.item(selected, 0).data(Qt.UserRole)
        if not fpath or not os.path.isfile(fpath):
            return

        try:
            content = self._read_file_content(fpath)
            if not content:
                return

            cleaned, _ = self._clean_text_with_ui_options(content)

            # Display Diff
            self.txt_before.setPlainText(content)
            self.txt_after.setPlainText(cleaned)

            # Scroll both panes to the line containing the issue
            line_num = 1
            pattern_regex = None
            if selected < len(self._scanned_issues):
                line_num = self._scanned_issues[selected].get("line_num", 1)
                pattern_regex = self._scanned_issues[selected].get("pattern_regex")

            # Scroll Before
            doc_before = self.txt_before.document()
            block_before = doc_before.findBlockByLineNumber(line_num - 1)
            cursor_before = self.txt_before.textCursor()
            cursor_before.setPosition(block_before.position())
            self.txt_before.setTextCursor(cursor_before)
            self.txt_before.ensureCursorVisible()

            # Scroll After (approximate line sync)
            doc_after = self.txt_after.document()
            target_line = min(line_num - 1, doc_after.blockCount() - 1)
            if target_line >= 0:
                block_after = doc_after.findBlockByLineNumber(target_line)
                cursor_after = self.txt_after.textCursor()
                cursor_after.setPosition(block_after.position())
                self.txt_after.setTextCursor(cursor_after)
                self.txt_after.ensureCursorVisible()

            # Highlight ONLY the matching pattern, not the entire line
            if pattern_regex:
                self._highlight_regex_in_pane(self.txt_before, pattern_regex)
            else:
                issue_content = self.table_issues.item(selected, 2).text().strip()
                self._highlight_literal_in_pane(self.txt_before, issue_content)

        except Exception as e:
            self.lbl_stats.setText(f"Lỗi tải xem trước: {e}")

    def _on_search_row_changed(self):
        selected = self.table_search.currentRow()
        if selected < 0:
            return

        fpath = self.table_search.item(selected, 0).data(Qt.UserRole)
        if not fpath or not os.path.isfile(fpath):
            return

        try:
            content = self._read_file_content(fpath)
            if not content:
                return

            self.txt_before.setPlainText(content)
            self.txt_after.setPlainText("Chế độ Xem trước Tìm kiếm & Xóa")

            kw = self.txt_search_kw.text().strip()
            if kw:
                self._highlight_literal_in_pane(self.txt_before, kw)
        except Exception as e:
            self.lbl_stats.setText(f"Lỗi tải xem trước tìm kiếm: {e}")

    # ═══════════════ UTILITIES ═══════════════

    def _read_file_content(self, fpath):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            try:
                import chardet
                with open(fpath, "rb") as f:
                    raw = f.read()
                detected = chardet.detect(raw)
                return raw.decode(detected.get("encoding", "utf-8"), errors="replace")
            except Exception:
                return ""

    def _highlight_regex_in_pane(self, text_edit, pattern_str):
        if not pattern_str:
            return
        
        # Reset format
        cursor = text_edit.textCursor()
        cursor.select(QTextCursor.Document)
        cursor.setCharFormat(QTextCharFormat())

        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QColor("#ef4444")) # Red background for deletion
        highlight_format.setForeground(QColor("#ffffff"))

        text = text_edit.toPlainText()
        cursor = text_edit.textCursor()
        
        try:
            import re
            first_pos = -1
            for m in re.finditer(pattern_str, text, re.IGNORECASE):
                if first_pos == -1:
                    first_pos = m.start()
                cursor.setPosition(m.start())
                cursor.setPosition(m.end(), QTextCursor.KeepAnchor)
                cursor.setCharFormat(highlight_format)
            
            if first_pos != -1:
                cursor.setPosition(first_pos)
                text_edit.setTextCursor(cursor)
                text_edit.ensureCursorVisible()
        except Exception:
            pass

    def _highlight_literal_in_pane(self, text_edit, search_str):
        if not search_str:
            return
        
        # Reset format
        cursor = text_edit.textCursor()
        cursor.select(QTextCursor.Document)
        cursor.setCharFormat(QTextCharFormat())

        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QColor("#fbbf24")) # Gold background
        highlight_format.setForeground(QColor("#000000"))

        text = text_edit.toPlainText()
        cursor = text_edit.textCursor()
        
        try:
            import re
            first_pos = -1
            for m in re.finditer(re.escape(search_str), text, re.IGNORECASE):
                if first_pos == -1:
                    first_pos = m.start()
                cursor.setPosition(m.start())
                cursor.setPosition(m.end(), QTextCursor.KeepAnchor)
                cursor.setCharFormat(highlight_format)
            
            if first_pos != -1:
                cursor.setPosition(first_pos)
                text_edit.setTextCursor(cursor)
                text_edit.ensureCursorVisible()
        except Exception:
            pass

    def save_session(self):
        """Save clean settings to clean_session.json."""
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_dir = os.path.join(project_root, "config")
            os.makedirs(config_dir, exist_ok=True)
            session_path = os.path.join(config_dir, "clean_session.json")
            
            checkbox_states = {k: cb.isChecked() for k, cb in self.checkboxes.items()}
            
            session = {
                "input_folder": self.txt_input_folder.text().strip(),
                "output_folder": self.txt_output_folder.text().strip(),
                "custom_regex": self.txt_custom_regex.toPlainText().strip(),
                "checkbox_states": checkbox_states
            }
            with open(session_path, "w", encoding="utf-8") as f:
                json.dump(session, f, indent=2, ensure_ascii=False)
        except Exception as e:
            LOGGER.warning(f"Failed to save clean session: {e}")

    def load_session(self):
        """Load clean settings from clean_session.json."""
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            session_path = os.path.join(project_root, "config", "clean_session.json")
            if not os.path.isfile(session_path):
                return
            with open(session_path, "r", encoding="utf-8") as f:
                session = json.load(f)
            
            self.txt_input_folder.setText(session.get("input_folder", ""))
            self.txt_output_folder.setText(session.get("output_folder", ""))
            self.txt_custom_regex.setPlainText(session.get("custom_regex", ""))
            
            checkbox_states = session.get("checkbox_states", {})
            for k, val in checkbox_states.items():
                if k in self.checkboxes:
                    self.checkboxes[k].setChecked(val)
                    
            # Automatically load files if path exists
            in_folder = self.txt_input_folder.text().strip()
            if in_folder and os.path.isdir(in_folder):
                self._load_chapter_files(in_folder)
        except Exception as e:
            LOGGER.warning(f"Failed to load clean session: {e}")

    def _connect_session_signals(self):
        self.txt_input_folder.textChanged.connect(lambda: self.save_session())
        self.txt_output_folder.textChanged.connect(lambda: self.save_session())
        self.txt_custom_regex.textChanged.connect(lambda: self.save_session())
        for cb in self.checkboxes.values():
            cb.toggled.connect(lambda: self.save_session())

"""Tab Crawl — Crawl truyện từ các website."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QGridLayout, QTabWidget, QMessageBox, QPushButton
)
from PySide6.QtCore import Signal, QObject
import threading

from app.widgets import PathPicker, LogViewer, ProgressWidget


class CrawlSignals(QObject):
    log_msg = Signal(str, str)
    spam_msg = Signal(str)
    progress = Signal(int, int)
    done = Signal()


class TabCrawl(QWidget):
    """Crawl truyện từ truyenfull, khotruyenchu, truyendichmienphi, xtruyen, truyenmoi."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sig = CrawlSignals()
        self.stop_event = None
        self.crawl_thread = None
        self._build_ui()
        self._connect()
        self.load_session()
        self._connect_session_signals()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # Header
        header = QLabel("Crawl Truyện")
        header.setProperty("heading", True)
        layout.addWidget(header)

        # Input section
        input_group = QGroupBox("Thông tin")
        input_layout = QGridLayout(input_group)
        input_layout.setSpacing(8)

        input_layout.addWidget(QLabel("Link truyện:"), 0, 0)
        from PySide6.QtWidgets import QLineEdit
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://truyenmoiss.org/ten-truyen/ hoặc https://metruyenchuvn.com/ten-truyen/")
        input_layout.addWidget(self.url_input, 0, 1)

        input_layout.addWidget(QLabel("Thư mục lưu:"), 1, 0)
        self.folder_picker = PathPicker("Chọn thư mục lưu truyện", is_directory=True)
        input_layout.addWidget(self.folder_picker, 1, 1)

        layout.addWidget(input_group)

        # Controls
        ctrl_row = QHBoxLayout()
        self.start_btn = QPushButton("Bắt đầu Crawl")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.setFixedHeight(36)
        self.start_btn.clicked.connect(self._start_crawl)
        ctrl_row.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Dừng")
        self.stop_btn.setFixedHeight(36)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_crawl)
        ctrl_row.addWidget(self.stop_btn)
        ctrl_row.addStretch()
        layout.addLayout(ctrl_row)

        # Progress
        self.progress = ProgressWidget()
        layout.addWidget(self.progress)

        # Log tabs
        log_tabs = QTabWidget()

        self.crawl_log = LogViewer(height=250)
        log_tabs.addTab(self.crawl_log, "Crawl Log")

        self.spam_log = LogViewer(height=250)
        log_tabs.addTab(self.spam_log, "🚫 Spam Log")

        layout.addWidget(log_tabs, 1)

        # Supported sites info
        info = QLabel("Hỗ trợ: truyenmoiss.org • metruyenchuvn.com • truyenfull.today • khotruyenchu.space • truyendichmienphi.com • xtruyen.vn • mtruyen.net")
        info.setStyleSheet("color: #5a6a84; font-size: 11px; padding: 4px;")
        layout.addWidget(info)

    def _connect(self):
        self.sig.log_msg.connect(lambda msg, tag: self.crawl_log.append(msg, tag))
        self.sig.spam_msg.connect(lambda msg: self.spam_log.append(msg, "error"))
        self.sig.progress.connect(self._on_progress)
        self.sig.done.connect(self._on_done)

    def _on_progress(self, current, total):
        if total > 0:
            pct = int(current / total * 100)
            self.progress.set_progress(pct)

    def _start_crawl(self):
        url = self.url_input.text().strip()
        folder = self.folder_picker.text()
        if not url:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập link truyện!")
            return
        if not folder:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn thư mục lưu!")
            return

        self.stop_event = threading.Event()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.crawl_log.clear()
        self.spam_log.clear()
        self.progress.reset()

        def task():
            try:
                from process.crawler import get_crawler
                crawler = get_crawler(url)
                if crawler is None:
                    self.sig.log_msg.emit(f"[!] Website chưa được hỗ trợ: {url}", "error")
                    self.sig.done.emit()
                    return

                crawler.set_log_callback(lambda msg: self.sig.log_msg.emit(msg, "info"))
                crawler.set_spam_log_callback(lambda msg: self.sig.spam_msg.emit(msg))
                crawler.set_progress_callback(lambda c, t: self.sig.progress.emit(c, t))
                crawler.crawl(folder, stop_event=self.stop_event)

                if not self.stop_event.is_set():
                    self.sig.log_msg.emit("🎉 Crawl hoàn tất!", "success")
            except Exception as e:
                self.sig.log_msg.emit(f"[!] Lỗi: {e}", "error")
            self.sig.done.emit()

        self.crawl_thread = threading.Thread(target=task, daemon=True)
        self.crawl_thread.start()

    def _stop_crawl(self):
        if self.stop_event:
            self.stop_event.set()
        self.crawl_log.append("Đang dừng...", "warning")

    def _on_done(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def save_session(self):
        """Save crawl session settings."""
        import json
        import os
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_dir = os.path.join(project_root, "config")
            os.makedirs(config_dir, exist_ok=True)
            session_path = os.path.join(config_dir, "crawl_session.json")
            
            session = {
                "url": self.url_input.text().strip(),
                "folder": self.folder_picker.text()
            }
            with open(session_path, "w", encoding="utf-8") as f:
                json.dump(session, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def load_session(self):
        """Load crawl session settings."""
        import json
        import os
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            session_path = os.path.join(project_root, "config", "crawl_session.json")
            if not os.path.isfile(session_path):
                return
            with open(session_path, "r", encoding="utf-8") as f:
                session = json.load(f)
            
            self.url_input.setText(session.get("url", ""))
            self.folder_picker.setText(session.get("folder", ""))
        except Exception:
            pass

    def _connect_session_signals(self):
        self.url_input.textChanged.connect(lambda: self.save_session())
        self.folder_picker._line_edit.textChanged.connect(lambda: self.save_session())

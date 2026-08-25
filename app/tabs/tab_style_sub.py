"""Tab Style Subtitle — Phụ đề nghệ thuật (tool độc lập)."""

import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QGroupBox, QFileDialog, QGridLayout,
    QSpinBox, QCheckBox, QSplitter,
)
from PySide6.QtCore import Qt, QThread, Signal

from app.theme import THEME_COLORS
from app.widgets.log_viewer import LogViewer


class RenderWorker(QThread):
    progress = Signal(str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, video_path, sub_path, output_path, style, template):
        super().__init__()
        self.video_path = video_path
        self.sub_path = sub_path
        self.output_path = output_path
        self.style = style
        self.template = template

    def run(self):
        try:
            from process.style_subtitles.renderer import render_style_subtitles
            ok = render_style_subtitles(
                self.video_path, self.sub_path, self.output_path,
                style=self.style, template_name=self.template,
                log_callback=lambda msg: self.progress.emit(msg),
            )
            if ok:
                self.finished.emit()
            else:
                self.error.emit("Render failed")
        except Exception as e:
            self.error.emit(str(e))


class TabStyleSub(QWidget):
    """Style subtitles — render phụ đề nghệ thuật lên video."""

    def __init__(self):
        super().__init__()
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        header = QLabel("Style Subtitles — Phụ đề nghệ thuật")
        header.setStyleSheet(f"color: {THEME_COLORS['accent']}; font-size: 18px; font-weight: bold;")
        layout.addWidget(header)

        splitter = QSplitter(Qt.Horizontal)

        # ═══ LEFT: Input ═══
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 8, 0)

        # Video input
        input_group = QGroupBox("Input")
        ig = QVBoxLayout(input_group)

        vid_row = QHBoxLayout()
        self.txt_video = QLineEdit()
        self.txt_video.setPlaceholderText("File video...")
        btn_vid = QPushButton("Chọn video")
        btn_vid.clicked.connect(self._browse_video)
        vid_row.addWidget(QLabel("Video:"))
        vid_row.addWidget(self.txt_video, 1)
        vid_row.addWidget(btn_vid)
        ig.addLayout(vid_row)

        sub_row = QHBoxLayout()
        self.txt_sub = QLineEdit()
        self.txt_sub.setPlaceholderText("File subtitle (SRT/VTT/ASS)...")
        btn_sub = QPushButton("Chọn phụ đề")
        btn_sub.clicked.connect(self._browse_sub)
        sub_row.addWidget(QLabel("Sub:"))
        sub_row.addWidget(self.txt_sub, 1)
        sub_row.addWidget(btn_sub)
        ig.addLayout(sub_row)

        out_row = QHBoxLayout()
        self.txt_output = QLineEdit()
        self.txt_output.setPlaceholderText("Chọn đường dẫn output...")
        btn_out = QPushButton("Chọn nơi lưu")
        btn_out.clicked.connect(self._browse_output)
        out_row.addWidget(QLabel("Output:"))
        out_row.addWidget(self.txt_output, 1)
        out_row.addWidget(btn_out)
        ig.addLayout(out_row)

        ll.addWidget(input_group)

        # Template selector
        tmpl_group = QGroupBox("Template")
        tg = QVBoxLayout(tmpl_group)
        self.cmb_template = QComboBox()
        self.cmb_template.addItems(["classic", "default", "modern", "neo-minimal", "tiktok3w", "custom"])
        tg.addWidget(self.cmb_template)
        ll.addWidget(tmpl_group)

        # Custom style controls
        custom_group = QGroupBox("Custom Style")
        cg = QGridLayout(custom_group)

        cg.addWidget(QLabel("Font:"), 0, 0)
        self.cmb_font = QComboBox()
        self.cmb_font.addItems(["Noto Sans", "Be Vietnam Pro", "Inter", "Montserrat", "Roboto"])
        self.cmb_font.setEditable(True)
        cg.addWidget(self.cmb_font, 0, 1)

        cg.addWidget(QLabel("Size:"), 0, 2)
        self.spn_size = QSpinBox()
        self.spn_size.setRange(24, 120)
        self.spn_size.setValue(48)
        cg.addWidget(self.spn_size, 0, 3)

        cg.addWidget(QLabel("Outline:"), 1, 0)
        self.spn_outline = QSpinBox()
        self.spn_outline.setRange(0, 8)
        self.spn_outline.setValue(3)
        cg.addWidget(self.spn_outline, 1, 1)

        cg.addWidget(QLabel("Shadow:"), 2, 0)
        self.spn_shadow = QSpinBox()
        self.spn_shadow.setRange(0, 8)
        self.spn_shadow.setValue(2)
        cg.addWidget(self.spn_shadow, 2, 1)

        cg.addWidget(QLabel("Position:"), 2, 2)
        self.cmb_pos = QComboBox()
        self.cmb_pos.addItems(["bottom", "center", "top"])
        cg.addWidget(self.cmb_pos, 2, 3)

        self.chk_bold = QCheckBox("Bold")
        self.chk_bold.setChecked(True)
        cg.addWidget(self.chk_bold, 3, 0)

        self.chk_opaque = QCheckBox("Opaque BG")
        cg.addWidget(self.chk_opaque, 3, 1)

        ll.addWidget(custom_group)

        # Render button
        self.btn_render = QPushButton("Render video")
        self.btn_render.setObjectName("primaryBtn")
        self.btn_render.clicked.connect(self._render)
        ll.addWidget(self.btn_render)

        splitter.addWidget(left)

        # ═══ RIGHT: Log ═══
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(8, 0, 0, 0)
        self.log = LogViewer()
        rl.addWidget(self.log, 1)
        splitter.addWidget(right)

        splitter.setSizes([500, 400])
        layout.addWidget(splitter, 1)

    def _browse_video(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn video", "", "Video (*.mp4 *.mkv *.avi *.mov);;All (*)")
        if path:
            self.txt_video.setText(path)

    def _browse_sub(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn subtitle", "", "Subtitle (*.srt *.vtt *.ass);;All (*)")
        if path:
            self.txt_sub.setText(path)

    def _browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn folder output")
        if folder:
            self.txt_output.setText(folder)

    def _render(self):
        video = self.txt_video.text().strip()
        sub = self.txt_sub.text().strip()
        output_dir = self.txt_output.text().strip()

        if not video or not sub or not output_dir:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Lỗi", "Chưa chọn đủ file input/output!")
            return
        if not os.path.isfile(video) or not os.path.isfile(sub):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Lỗi", "File video hoặc subtitle không tồn tại!")
            return

        os.makedirs(output_dir, exist_ok=True)
        video_name = os.path.splitext(os.path.basename(video))[0]
        output = os.path.join(output_dir, f"{video_name}_styled.mp4")

        template = self.cmb_template.currentText()
        style = None

        if template == "custom":
            from process.style_subtitles.templates import SubtitleStyle
            style = SubtitleStyle(
                name="custom",
                font_family=self.cmb_font.currentText(),
                font_size=self.spn_size.value(),
                outline_width=self.spn_outline.value(),
                shadow=self.spn_shadow.value(),
                position=self.cmb_pos.currentText(),
                bold=self.chk_bold.isChecked(),
                opaque_background=self.chk_opaque.isChecked(),
            )

        self.log.clear()
        self.btn_render.setEnabled(False)
        self._worker = RenderWorker(video, sub, output, style, template)
        self._worker.progress.connect(self.log.append)
        self._worker.finished.connect(self._on_render_done)
        self._worker.error.connect(self._on_render_error)
        self._worker.start()

    def _on_render_done(self):
        self.log.append("Done!")
        self.btn_render.setEnabled(True)

    def _on_render_error(self, message):
        self.log.append(f"Error: {message}")
        self.btn_render.setEnabled(True)

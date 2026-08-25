"""Tab Story Maker — AI tạo truyện + video (tool độc lập)."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QComboBox, QGroupBox, QGridLayout,
    QSpinBox, QFileDialog, QSplitter, QTabWidget,
)
from PySide6.QtCore import Qt, QThread, Signal
import os
import threading

from app.theme import THEME_COLORS
from app.widgets.log_viewer import LogViewer


class StoryWorker(QThread):
    progress = Signal(str)
    result = Signal(object)
    error = Signal(str)

    def __init__(self, config, api_key):
        super().__init__()
        self.config = config
        self.api_key = api_key
        self.stop_event = threading.Event()

    def run(self):
        try:
            from process.ai.story_maker import generate_text_story
            gen = generate_text_story(self.config, self.api_key, self.stop_event)
            while True:
                try:
                    self.progress.emit(next(gen))
                except StopIteration as e:
                    result = e.value
                    self.result.emit(result)
                    break
        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        self.stop_event.set()


class VideoWorker(QThread):
    progress = Signal(str)
    completed = Signal(str)
    error = Signal(str)

    def __init__(self, scenes, audio_path, output_path, transition, overlay, resolution):
        super().__init__()
        self.scenes = scenes
        self.audio_path = audio_path
        self.output_path = output_path
        self.transition = transition
        self.overlay = overlay
        self.resolution = resolution
        self.stop_event = threading.Event()

    def run(self):
        try:
            from process.video.composer import compose_story_video
            for message in compose_story_video(
                self.scenes,
                self.audio_path,
                self.output_path,
                transition=self.transition,
                overlay_effect="" if self.overlay == "(none)" else self.overlay,
                resolution=self.resolution,
                stop_event=self.stop_event,
            ):
                self.progress.emit(message)
            if os.path.isfile(self.output_path) and os.path.getsize(self.output_path) > 0:
                self.completed.emit(self.output_path)
            else:
                self.error.emit("Không tạo được file video đầu ra.")
        except Exception as exc:
            self.error.emit(str(exc))

    def stop(self):
        self.stop_event.set()


class TabStory(QWidget):
    """AI Story Maker — generate stories using AI models."""

    def __init__(self):
        super().__init__()
        self._worker = None
        self._video_worker = None
        self._story_result = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        header = QLabel("Story Maker — AI tạo truyện")
        header.setStyleSheet(f"color: {THEME_COLORS['accent']}; font-size: 18px; font-weight: bold;")
        layout.addWidget(header)

        splitter = QSplitter(Qt.Horizontal)

        # ═══ LEFT: Config ═══
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 8, 0)

        config_group = QGroupBox("Cấu hình truyện")
        cg = QGridLayout(config_group)

        cg.addWidget(QLabel("Tiêu đề:"), 0, 0)
        self.txt_title = QLineEdit()
        self.txt_title.setPlaceholderText("Để trống = AI tự đặt")
        cg.addWidget(self.txt_title, 0, 1, 1, 3)

        cg.addWidget(QLabel("Chủ đề:"), 1, 0)
        self.cmb_topic = QComboBox()
        self.cmb_topic.addItems([
            "Phiêu lưu", "Tình yêu", "Kinh dị", "Hài hước", "Trinh thám",
            "Khoa học viễn tưởng", "Tiên hiệp", "Võ hiệp", "Lịch sử",
            "Đời thường", "Fantasy", "Truyện cổ tích",
        ])
        self.cmb_topic.setEditable(True)
        cg.addWidget(self.cmb_topic, 1, 1)

        cg.addWidget(QLabel("Model:"), 1, 2)
        self.cmb_model = QComboBox()
        self.cmb_model.addItems([
            "mistral-4", "mistral", "free-mistral",
            "gemini-fast", "gemini-flash-lite-3.1",
            "llama", "llama-scout", "openai",
        ])
        cg.addWidget(self.cmb_model, 1, 3)

        cg.addWidget(QLabel("Ngôn ngữ:"), 2, 0)
        self.cmb_lang = QComboBox()
        self.cmb_lang.addItems([
            "Vietnamese", "English", "Chinese", "Japanese", "Korean",
            "Thai", "French", "Spanish", "German",
        ])
        cg.addWidget(self.cmb_lang, 2, 1)

        cg.addWidget(QLabel("Độ dài:"), 2, 2)
        self.cmb_length = QComboBox()
        self.cmb_length.addItems(["short", "medium", "long"])
        self.cmb_length.setCurrentText("medium")
        cg.addWidget(self.cmb_length, 2, 3)

        cg.addWidget(QLabel("Số chương:"), 3, 0)
        self.spn_chapters = QSpinBox()
        self.spn_chapters.setRange(1, 20)
        self.spn_chapters.setValue(1)
        cg.addWidget(self.spn_chapters, 3, 1)

        cg.addWidget(QLabel("API Key:"), 3, 2)
        self.txt_api_key = QLineEdit()
        self.txt_api_key.setPlaceholderText("API key...")
        self.txt_api_key.setEchoMode(QLineEdit.Password)
        cg.addWidget(self.txt_api_key, 3, 3)

        ll.addWidget(config_group)

        # Generate button
        self.btn_gen = QPushButton("Tạo truyện")
        self.btn_gen.setObjectName("primaryBtn")
        self.btn_gen.clicked.connect(self._generate_story)
        ll.addWidget(self.btn_gen)

        self.btn_stop = QPushButton("Dừng")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop_story)
        ll.addWidget(self.btn_stop)

        # Video options
        video_group = QGroupBox("Video Story (tùy chọn)")
        vg = QGridLayout(video_group)

        vg.addWidget(QLabel("Audio truyện:"), 0, 0)
        self.txt_video_audio = QLineEdit()
        self.txt_video_audio.setPlaceholderText("Chọn file audio narration...")
        vg.addWidget(self.txt_video_audio, 0, 1, 1, 2)
        btn_audio = QPushButton("Chọn audio")
        btn_audio.clicked.connect(self._browse_video_audio)
        vg.addWidget(btn_audio, 0, 3)

        vg.addWidget(QLabel("Thư mục media:"), 1, 0)
        self.txt_media_folder = QLineEdit()
        self.txt_media_folder.setPlaceholderText("Tùy chọn; để trống sẽ dùng nền đen")
        vg.addWidget(self.txt_media_folder, 1, 1, 1, 2)
        btn_media = QPushButton("Chọn thư mục")
        btn_media.clicked.connect(self._browse_media_folder)
        vg.addWidget(btn_media, 1, 3)

        vg.addWidget(QLabel("File video:"), 2, 0)
        self.txt_video_output = QLineEdit()
        self.txt_video_output.setPlaceholderText("Đường dẫn file MP4 đầu ra...")
        vg.addWidget(self.txt_video_output, 2, 1, 1, 2)
        btn_output = QPushButton("Chọn nơi lưu")
        btn_output.clicked.connect(self._browse_video_output)
        vg.addWidget(btn_output, 2, 3)

        vg.addWidget(QLabel("Transition:"), 3, 0)
        self.cmb_transition = QComboBox()
        from process.video.effects import TRANSITIONS
        self.cmb_transition.addItems(TRANSITIONS[:15])  # Show first 15
        vg.addWidget(self.cmb_transition, 3, 1)

        vg.addWidget(QLabel("Overlay:"), 3, 2)
        self.cmb_overlay = QComboBox()
        self.cmb_overlay.addItem("(none)")
        from process.video.effects import OVERLAY_EFFECTS
        self.cmb_overlay.addItems(list(OVERLAY_EFFECTS.keys()))
        vg.addWidget(self.cmb_overlay, 3, 3)

        vg.addWidget(QLabel("Resolution:"), 4, 0)
        self.cmb_res = QComboBox()
        self.cmb_res.addItems(["720p", "1080p", "2K", "4K"])
        self.cmb_res.setCurrentText("1080p")
        vg.addWidget(self.cmb_res, 4, 1)

        vg.addWidget(QLabel("Ken Burns:"), 4, 2)
        self.cmb_ken = QComboBox()
        self.cmb_ken.addItems(["(none)", "zoom_in", "zoom_out", "pan_left", "pan_right"])
        vg.addWidget(self.cmb_ken, 4, 3)

        self.btn_video = QPushButton("Dựng video")
        self.btn_video.setObjectName("primaryBtn")
        self.btn_video.setEnabled(False)
        self.btn_video.setToolTip("Hãy tạo truyện trước, sau đó chọn audio narration")
        self.btn_video.clicked.connect(self._build_video)
        vg.addWidget(self.btn_video, 5, 0, 1, 4)

        ll.addWidget(video_group)
        ll.addStretch()

        splitter.addWidget(left)

        # ═══ RIGHT: Result ═══
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(8, 0, 0, 0)

        rl.addWidget(QLabel("Kết quả:"))
        self.txt_result = QTextEdit()
        self.txt_result.setPlaceholderText("Truyện sẽ hiển thị ở đây...")
        rl.addWidget(self.txt_result, 1)

        self.log = LogViewer()
        self.log.setMaximumHeight(120)
        rl.addWidget(self.log)

        splitter.addWidget(right)
        splitter.setSizes([450, 500])

        layout.addWidget(splitter, 1)

    def _generate_story(self):
        from process.ai.story_maker import StoryConfig
        config = StoryConfig(
            title=self.txt_title.text().strip(),
            topic=self.cmb_topic.currentText(),
            model=self.cmb_model.currentText(),
            language=self.cmb_lang.currentText(),
            num_chapters=self.spn_chapters.value(),
            length=self.cmb_length.currentText(),
        )
        api_key = self.txt_api_key.text().strip() or self._saved_api_key(config.model)

        self.log.clear()
        self.txt_result.clear()

        self._worker = StoryWorker(config, api_key)
        self._worker.progress.connect(self.log.append)
        self._worker.result.connect(self._on_story_result)
        self._worker.error.connect(self._on_story_error)
        self._worker.finished.connect(self._on_story_finished)
        self.btn_gen.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self._worker.start()

    @staticmethod
    def _saved_api_key(model):
        import json
        import os

        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(project_root, "config", "settings.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                settings = json.load(f)
        except (OSError, ValueError, TypeError):
            return ""
        lowered = model.lower()
        if "gemini" in lowered:
            return settings.get("gemini_key", "")
        if "mistral" in lowered:
            return settings.get("mistral_key", "")
        if "openai" in lowered:
            return settings.get("openai_key", "")
        if "llama" in lowered:
            return settings.get("together_key", "")
        return ""

    def _stop_story(self):
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self.log.append("Đang dừng sau request hiện tại...")

    def _on_story_result(self, result):
        self._story_result = result
        text = result.text if result and hasattr(result, "text") else ""
        self.txt_result.setPlainText(text)
        self.btn_video.setEnabled(bool(result and getattr(result, "scenes", None)))
        if not text:
            self.log.append("Không nhận được nội dung truyện.")

    def _on_story_error(self, message):
        self.log.append(f"Error: {message}")

    def _on_story_finished(self):
        self.btn_gen.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def _browse_video_audio(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn audio narration", "", "Audio (*.wav *.mp3 *.flac *.m4a *.aac);;All files (*)"
        )
        if path:
            self.txt_video_audio.setText(path)

    def _browse_media_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục ảnh hoặc video")
        if folder:
            self.txt_media_folder.setText(folder)

    def _browse_video_output(self):
        path, _ = QFileDialog.getSaveFileName(self, "Lưu video", "story_video.mp4", "MP4 Video (*.mp4)")
        if path:
            self.txt_video_output.setText(path if path.lower().endswith(".mp4") else f"{path}.mp4")

    def _build_video(self):
        if not self._story_result or not self._story_result.scenes:
            self.log.append("Hãy tạo truyện trước khi dựng video.")
            return
        audio_path = self.txt_video_audio.text().strip()
        output_path = self.txt_video_output.text().strip()
        if not os.path.isfile(audio_path):
            self.log.append("File audio narration không tồn tại.")
            return
        if not output_path:
            self._browse_video_output()
            output_path = self.txt_video_output.text().strip()
            if not output_path:
                return

        media_folder = self.txt_media_folder.text().strip()
        media_files = []
        if media_folder and os.path.isdir(media_folder):
            supported = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".mp4", ".mkv", ".mov", ".avi"}
            media_files = [
                os.path.join(media_folder, name)
                for name in sorted(os.listdir(media_folder))
                if os.path.splitext(name)[1].lower() in supported
            ]

        scenes = self._story_result.scenes
        for index, scene in enumerate(scenes):
            scene.media_path = media_files[index % len(media_files)] if media_files else ""
            scene.transition = self.cmb_transition.currentText()
            scene.ken_burns = "" if self.cmb_ken.currentText() == "(none)" else self.cmb_ken.currentText()

        self.btn_video.setEnabled(False)
        self._video_worker = VideoWorker(
            scenes,
            audio_path,
            output_path,
            self.cmb_transition.currentText(),
            self.cmb_overlay.currentText(),
            self.cmb_res.currentText(),
        )
        self._video_worker.progress.connect(self.log.append)
        self._video_worker.completed.connect(self._on_video_done)
        self._video_worker.error.connect(self._on_video_error)
        self._video_worker.start()

    def _on_video_done(self, path):
        self.log.append(f"Đã tạo video: {path}")
        self.btn_video.setEnabled(True)

    def _on_video_error(self, message):
        self.log.append(f"Lỗi dựng video: {message}")
        self.btn_video.setEnabled(True)

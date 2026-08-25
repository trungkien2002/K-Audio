"""Tab Settings — Cấu hình ứng dụng."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QGroupBox, QFormLayout,
    QFileDialog, QCheckBox, QMessageBox, QFrame,
)
from PySide6.QtCore import Qt

from app.theme import THEME_COLORS


class TabSettings(QWidget):
    """Application settings — output folder, API keys, device, etc."""

    def __init__(self):
        super().__init__()
        self._build_ui()
        self._load()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        header = QLabel("Settings — Cấu hình")
        header.setStyleSheet(f"color: {THEME_COLORS['accent']}; font-size: 18px; font-weight: bold;")
        layout.addWidget(header)

        # ── General ──
        gen_group = QGroupBox("Cài đặt chung")
        gen_form = QFormLayout(gen_group)

        self.txt_output_folder = QLineEdit()
        self.txt_output_folder.setPlaceholderText("~/Downloads/TTS_output")
        out_row = QHBoxLayout()
        out_row.addWidget(self.txt_output_folder, 1)
        btn_browse = QPushButton("Chọn thư mục")
        btn_browse.clicked.connect(self._browse_output_folder)
        out_row.addWidget(btn_browse)
        gen_form.addRow("Output mặc định:", out_row)

        self.cmb_device = QComboBox()
        self.cmb_device.addItems(["GPU (auto)", "CPU"])
        gen_form.addRow("Device:", self.cmb_device)

        self.cmb_language = QComboBox()
        self.cmb_language.addItems(["Vietnamese", "English", "auto"])
        gen_form.addRow("Ngôn ngữ mặc định:", self.cmb_language)

        layout.addWidget(gen_group)

        # ── API Keys ──
        key_group = QGroupBox("API Keys")
        key_form = QFormLayout(key_group)

        self.txt_gemini_key = QLineEdit()
        self.txt_gemini_key.setEchoMode(QLineEdit.Password)
        self.txt_gemini_key.setPlaceholderText("Google Gemini API key...")
        key_form.addRow("Gemini:", self.txt_gemini_key)

        self.txt_mistral_key = QLineEdit()
        self.txt_mistral_key.setEchoMode(QLineEdit.Password)
        self.txt_mistral_key.setPlaceholderText("Mistral API key...")
        key_form.addRow("Mistral:", self.txt_mistral_key)

        self.txt_openai_key = QLineEdit()
        self.txt_openai_key.setEchoMode(QLineEdit.Password)
        self.txt_openai_key.setPlaceholderText("OpenAI API key...")
        key_form.addRow("OpenAI:", self.txt_openai_key)

        self.txt_together_key = QLineEdit()
        self.txt_together_key.setEchoMode(QLineEdit.Password)
        self.txt_together_key.setPlaceholderText("Together.ai API key (Llama)...")
        key_form.addRow("Together:", self.txt_together_key)

        self.txt_pixabay_key = QLineEdit()
        self.txt_pixabay_key.setEchoMode(QLineEdit.Password)
        self.txt_pixabay_key.setPlaceholderText("Pixabay API key...")
        key_form.addRow("Pixabay:", self.txt_pixabay_key)

        self.txt_hf_token = QLineEdit()
        self.txt_hf_token.setEchoMode(QLineEdit.Password)
        self.txt_hf_token.setPlaceholderText("HuggingFace token (pyannote)...")
        key_form.addRow("HuggingFace:", self.txt_hf_token)

        layout.addWidget(key_group)

        # ── OmniVoice ──
        omni_group = QGroupBox("OmniVoice Model")
        og = QFormLayout(omni_group)

        self.lbl_model_path = QLabel("—")
        self.lbl_model_path.setStyleSheet(f"color: {THEME_COLORS['text_muted']};")
        og.addRow("Model path:", self.lbl_model_path)

        self.lbl_model_status = QLabel("Chưa kiểm tra")
        og.addRow("Status:", self.lbl_model_status)

        btn_check = QPushButton("Kiểm tra model")
        btn_check.clicked.connect(self._check_model)
        og.addRow("", btn_check)

        self.chk_offline = QCheckBox("Chế độ offline (không tải model mới)")
        og.addRow("", self.chk_offline)

        layout.addWidget(omni_group)

        # ── Save/Reset ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_reset = QPushButton("Reset mặc định")
        btn_reset.clicked.connect(self._reset)
        btn_row.addWidget(btn_reset)
        btn_save = QPushButton("Lưu cài đặt")
        btn_save.setObjectName("primaryBtn")
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

        layout.addStretch()

    def _browse_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn folder output")
        if folder:
            self.txt_output_folder.setText(folder)

    def _check_model(self):
        try:
            from process.tts.model_manager import model_folder_ready, resolve_local_model_path, LOCAL_MODEL_DIR
            if model_folder_ready():
                path = resolve_local_model_path()
                self.lbl_model_status.setText("Sẵn sàng")
                self.lbl_model_status.setStyleSheet("color: #4caf50;")
                self.lbl_model_path.setText(path or LOCAL_MODEL_DIR)
            else:
                self.lbl_model_status.setText("Chưa tải model")
                self.lbl_model_status.setStyleSheet("color: #ff9800;")
                self.lbl_model_path.setText("—")
        except Exception as e:
            self.lbl_model_status.setText(f"Error: {e}")

    def _save(self):
        import os, json
        settings = {
            "output_folder": self.txt_output_folder.text().strip(),
            "device": self.cmb_device.currentText(),
            "language": self.cmb_language.currentText(),
            "gemini_key": self.txt_gemini_key.text().strip(),
            "mistral_key": self.txt_mistral_key.text().strip(),
            "openai_key": self.txt_openai_key.text().strip(),
            "together_key": self.txt_together_key.text().strip(),
            "pixabay_key": self.txt_pixabay_key.text().strip(),
            "hf_token": self.txt_hf_token.text().strip(),
            "offline_mode": self.chk_offline.isChecked(),
        }
        config_dir = os.path.join(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))), "config")
        os.makedirs(config_dir, exist_ok=True)
        settings_path = os.path.join(config_dir, "settings.json")
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        self._apply_runtime_settings(settings)
        QMessageBox.information(self, "OK", f"Đã lưu: {settings_path}")

    def _settings_path(self):
        import os
        return os.path.join(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))), "config", "settings.json")

    def _load(self):
        import json
        import os

        path = self._settings_path()
        if not os.path.isfile(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                settings = json.load(f)
            self.txt_output_folder.setText(settings.get("output_folder", ""))
            self.cmb_device.setCurrentText(settings.get("device", "GPU (auto)"))
            self.cmb_language.setCurrentText(settings.get("language", "Vietnamese"))
            self.txt_gemini_key.setText(settings.get("gemini_key", ""))
            self.txt_mistral_key.setText(settings.get("mistral_key", ""))
            self.txt_openai_key.setText(settings.get("openai_key", ""))
            self.txt_together_key.setText(settings.get("together_key", ""))
            self.txt_pixabay_key.setText(settings.get("pixabay_key", ""))
            self.txt_hf_token.setText(settings.get("hf_token", ""))
            self.chk_offline.setChecked(bool(settings.get("offline_mode", False)))
            self._apply_runtime_settings(settings)
        except (OSError, ValueError, TypeError) as e:
            self.lbl_model_status.setText(f"Lỗi đọc settings: {e}")

    @staticmethod
    def _apply_runtime_settings(settings):
        import os

        env_map = {
            "gemini_key": "GEMINI_API_KEY",
            "openai_key": "OPENAI_API_KEY",
            "together_key": "TOGETHER_API_KEY",
            "hf_token": "HF_TOKEN",
        }
        for setting_key, env_key in env_map.items():
            value = str(settings.get(setting_key, "")).strip()
            if value:
                os.environ[env_key] = value

        offline_keys = ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_DATASETS_OFFLINE")
        if settings.get("offline_mode", False):
            for key in offline_keys:
                os.environ[key] = "1"
        else:
            for key in offline_keys:
                os.environ.pop(key, None)

    def _reset(self):
        self.txt_output_folder.clear()
        self.cmb_device.setCurrentIndex(0)
        self.cmb_language.setCurrentIndex(0)
        self.txt_gemini_key.clear()
        self.txt_mistral_key.clear()
        self.txt_openai_key.clear()
        self.txt_together_key.clear()
        self.txt_pixabay_key.clear()
        self.txt_hf_token.clear()
        self.chk_offline.setChecked(False)

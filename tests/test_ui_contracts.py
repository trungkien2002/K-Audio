"""Regression tests for K-Audio UI wiring and feature contracts."""

import os
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import SIGNAL
from PySide6.QtWidgets import QApplication, QComboBox, QGroupBox, QPushButton

from app.main_window import MainWindow
from app.tabs.tab_multispeaker import GenerateAudioWorker
from app.tabs.tab_omnivoice import TabOmniVoice
from process.multispeaker.analyzer import MultiSpeakerEntry
from process.tts.model_manager import get_model_status, set_model_status


class UIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = MainWindow()

    def tearDown(self):
        self.window.close()

    def test_brand_and_all_tool_pages_are_present(self):
        self.assertEqual(self.window.windowTitle(), "K-Audio")
        self.assertEqual(self.window.stack.count(), 11)

    def test_all_action_buttons_are_connected_and_labeled(self):
        for page_index in range(1, self.window.stack.count()):
            page = self.window.stack.widget(page_index)
            for button in page.findChildren(QPushButton):
                if button.objectName() in {"toolCard", "brandMark"}:
                    continue
                self.assertTrue(button.text().strip(), f"Unlabeled button on page {page_index}")
                self.assertGreater(
                    button.receivers(SIGNAL("clicked()")),
                    0,
                    f"Unconnected button: {button.text()}",
                )

    def test_choices_are_populated_and_no_feature_group_is_locked(self):
        for combo in self.window.findChildren(QComboBox):
            self.assertGreater(combo.count(), 0)
        disabled_groups = [group.title() for group in self.window.findChildren(QGroupBox) if not group.isEnabled()]
        self.assertEqual(disabled_groups, [])

    def test_model_status_reads_manager_state(self):
        previous = get_model_status()
        try:
            tab = self.window.findChild(TabOmniVoice)
            set_model_status("downloading", 37, "Đang tải model: 37%")
            tab._refresh_model_status()
            self.assertEqual(tab.progress_model._bar.value(), 37)
            self.assertIn("37%", tab.lbl_model_status.text())
        finally:
            set_model_status(previous["phase"], previous["progress"], previous["message"])


class MultiSpeakerContractTests(unittest.TestCase):
    def test_worker_passes_voice_map_to_generator(self):
        segment = MultiSpeakerEntry(0.0, 1.0, "SPEAKER_00", "Xin chào", "voice-a")
        with tempfile.TemporaryDirectory() as folder:
            output_path = os.path.join(folder, "result.wav")

            def fake_generator(segments, voice_map, output, stop_event=None):
                self.assertEqual(segments, [segment])
                self.assertEqual(voice_map, {"SPEAKER_00": "voice-a"})
                self.assertEqual(output, output_path)
                with open(output, "wb") as stream:
                    stream.write(b"RIFF-test")
                yield "done"

            with patch(
                "process.multispeaker.generator.generate_multispeaker_audio",
                side_effect=fake_generator,
            ):
                worker = GenerateAudioWorker([segment], output_path)
                worker.run()

            self.assertTrue(os.path.isfile(output_path))


if __name__ == "__main__":
    unittest.main()

import os
import tempfile
import unittest
import zipfile

from process.ai.scene_splitter import split_into_scenes
from process.cleaner.filter_engine import clean_text
from process.crawler import get_crawler
from process.splitter.splitter import split_chapters
from process.tts.engine import ENGINE_IDS
from process.tts.model_manager import _safe_extract
from process.tts.srt_generator import format_timestamp, parse_timestamp


class CoreSmokeTests(unittest.TestCase):
    def test_removed_engines_are_not_registered(self):
        self.assertEqual(ENGINE_IDS, ["edge-tts", "gtts", "omnivoice"])

    def test_splitter_and_scene_splitter(self):
        text = "Chương 1\n" + "một hai ba " * 20 + "\nChương 2\n" + "bốn năm sáu " * 20
        result = split_chapters(text, min_words=10)
        self.assertEqual(result.chapter_count, 2)
        self.assertEqual(len(split_into_scenes("[SCENE 1]\nA\n[SCENE 2]\nB")), 2)

    def test_cleaner_removes_url_and_zero_width(self):
        cleaned, issues = clean_text("abc\u200b\nhttps://spam.example\nNội dung")
        self.assertNotIn("\u200b", cleaned)
        self.assertNotIn("https://", cleaned)
        self.assertTrue(issues)

    def test_srt_timestamp_round_trip(self):
        value = 3661.25
        self.assertAlmostEqual(parse_timestamp(format_timestamp(value)), value, places=3)

    def test_crawler_domain_matching_does_not_accept_substring_spoof(self):
        self.assertIsNone(get_crawler("https://evil.example/?next=truyenfull.today"))
        self.assertIsNotNone(get_crawler("https://www.truyenfull.today/story"))

    def test_zip_extraction_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = os.path.join(tmp, "unsafe.zip")
            with zipfile.ZipFile(archive_path, "w") as zf:
                zf.writestr("../outside.txt", "unsafe")
            with zipfile.ZipFile(archive_path) as zf:
                with self.assertRaises(ValueError):
                    _safe_extract(zf, os.path.join(tmp, "target"), "../outside.txt")


if __name__ == "__main__":
    unittest.main()

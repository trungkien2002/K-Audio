import os
from abc import ABC, abstractmethod
from process.crawler.utils import SpamReport, AntiBotSession


class BaseCrawler(ABC):
    def __init__(self, url):
        self.url = url
        self.log_callback = None
        self.spam_log_callback = None
        self.progress_callback = None
        self.spam_report = SpamReport()

    def set_log_callback(self, callback):
        self.log_callback = callback

    def set_spam_log_callback(self, callback):
        self.spam_log_callback = callback

    def set_progress_callback(self, callback):
        self.progress_callback = callback

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)

    def log_spam(self, message):
        if self.spam_log_callback:
            self.spam_log_callback(message)

    def update_progress(self, current, total):
        if self.progress_callback:
            self.progress_callback(current, total)

    @abstractmethod
    def get_story_info(self):
        pass

    @abstractmethod
    def get_chapter_list(self, story_info):
        pass

    @abstractmethod
    def get_chapter_content(self, chapter_url):
        pass

    def crawl(self, output_dir, stop_event=None):
        self.spam_report = SpamReport()
        if hasattr(self, 'session') and isinstance(self.session, AntiBotSession):
            self.session.log_callback = self.log

        self.log(f"[*] Đang lấy thông tin truyện...")
        story_info = self.get_story_info()
        if not story_info:
            self.log("[!] Không thể lấy thông tin truyện")
            return
        self.log(f"[+] Tên truyện: {story_info.get('title', 'Unknown')}")
        if story_info.get('author'):
            self.log(f"[+] Tác giả: {story_info['author']}")

        self.log(f"[*] Đang lấy danh sách chương...")
        chapters = self.get_chapter_list(story_info)
        if not chapters:
            self.log("[!] Không tìm thấy chương nào")
            return
        self.log(f"[+] Tìm thấy {len(chapters)} chương")

        total = len(chapters)
        skipped = 0
        from process.crawler.utils import save_chapter, chapter_exists
        for i, chapter in enumerate(chapters, 1):
            if stop_event and stop_event.is_set():
                self.log("[!] Đã dừng theo yêu cầu.")
                break

            # Skip chapters that already exist
            if chapter_exists(output_dir, story_info['title'], chapter['number']):
                chap_label = chapter.get('title', '') or f"#{chapter['number']}"
                self.log(f"[~] Bỏ qua (đã có): {chap_label}")
                skipped += 1
                self.update_progress(i, total)
                continue

            before = self.spam_report.total_spam_removed
            chap_label = chapter.get('title', '') or f"#{chapter['number']}"
            self.log(f"[*] Đang tải {chapter['number']}/{total}: {chap_label}...")
            content = self.get_chapter_content(chapter['url'])
            if content:
                filepath = save_chapter(
                    output_dir,
                    story_info['title'],
                    chapter['number'],
                    chapter.get('title', ''),
                    content
                )
                self.log(f"[+] Đã lưu: {os.path.basename(filepath)}")
            else:
                self.log(f"[!] Lỗi tải: {chap_label}")
            added = self.spam_report.total_spam_removed - before
            if added > 0:
                for e in self.spam_report.entries[-added:]:
                    tag = f"<{e['tag_name']}>" if e['tag_name'] != 'text_line' else 'dòng'
                    orig = e['original_text'][:80]
                    msg = f'{chap_label}: đã xoá {tag} chứa "{orig}"'
                    self.log_spam(msg)
            self.update_progress(i, total)

        if skipped > 0:
            self.log(f"[*] Đã bỏ qua {skipped} chương đã tải trước đó")
        if self.spam_report.total_spam_removed > 0:
            self.log(f"[!] Tổng cộng đã xoá {self.spam_report.total_spam_removed} spam trong {len(chapters)} chương")

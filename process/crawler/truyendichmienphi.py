import re
import time
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from process.crawler.base import BaseCrawler
from process.crawler.utils import AntiBotSession, clean_html_content


API_BASE = "https://api.truyendichmienphi.com/api"


class TruyenDichMienPhiCrawler(BaseCrawler):
    def __init__(self, url):
        super().__init__(url)
        self.session = AntiBotSession()
        self.base_domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        self.playwright_available = False
        self._check_playwright()

    def _check_playwright(self):
        try:
            from playwright.sync_api import sync_playwright
            self.playwright_available = True
        except ImportError:
            self.playwright_available = False

    def _parse_slug(self):
        path = urlparse(self.url).path.strip("/")
        parts = path.split("/")
        slug = None
        for i, p in enumerate(parts):
            if p == "truyen" and i + 1 < len(parts):
                slug = parts[i + 1]
                break
        if not slug and parts:
            slug = parts[-1]
        return slug if slug else ""

    def get_story_info(self):
        slug = self._parse_slug()
        if slug:
            try:
                resp = self.session.get(f"{API_BASE}/novels/{slug}")
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "title": data.get("title", "Unknown"),
                        "author": "",
                        "story_slug": slug,
                        "description": data.get("description", ""),
                        "url": f"{self.base_domain}/truyen/{slug}/",
                        "api_data": data,
                    }
            except Exception as e:
                self.log(f"[!] API error: {e}")

        self.log("[!] API không khả dụng, thử render HTML...")
        html = self._get_rendered_html(self.url)
        if not html:
            try:
                resp = self.session.get(self.url)
                if resp.status_code == 200:
                    html = resp.text
                else:
                    return None
            except Exception:
                return None

        soup = BeautifulSoup(html, "lxml")
        title_tag = soup.find("title")
        title = "Unknown"
        if title_tag:
            title_text = title_tag.get_text(strip=True)
            title = title_text.split("|")[0].strip()

        return {
            "title": title,
            "author": "",
            "story_slug": slug,
            "description": "",
            "url": self.url.rstrip("/") + "/",
        }

    def get_chapter_list(self, story_info):
        slug = story_info.get("story_slug", self._parse_slug())
        chapters = []

        if slug:
            url = f"{API_BASE}/novels/{slug}/chapters?limit=2000"
            try:
                resp = self.session.get(url)
                if hasattr(resp, 'status_code') and resp.status_code == 200:
                    data = resp.json()
                    _results = data.get("results", data.get("chapters", []))
                    for ch in _results:
                        ch_num = ch.get("chapter_number", 0)
                        ch_title = ch.get("title", "")
                        ch_slug = ch.get("slug", "")
                        ch_url = f"{self.base_domain}/truyen/{slug}/chuong/{ch_num}"
                        # Build full title: "Chương X: Title" or just "Chương X"
                        if ch_title:
                            full_title = f"Chương {ch_num}: {ch_title}"
                        else:
                            full_title = f"Chương {ch_num}"
                        chapters.append({
                            "number": 0,  # will be assigned sequentially below
                            "_orig_num": ch_num,
                            "title": full_title,
                            "url": ch_url,
                            "id": ch.get("_id", ""),
                            "slug": ch_slug,
                            "is_locked": ch.get("is_locked", True),
                        })
                    # Sort by original chapter number first to maintain story order
                    chapters.sort(key=lambda x: x.get('_orig_num', 0))
                    # Assign sequential numbers
                    for idx, c in enumerate(chapters, 1):
                        c['number'] = idx
                    return chapters
            except Exception as e:
                pass

        self.log("[!] API không có chapter list, fallback về render HTML...")
        html = self._get_rendered_html(self.url)
        if html:
            soup = BeautifulSoup(html, "lxml")
            scripts = soup.find_all("script")
            for script in scripts:
                text = script.string or ""
                ch_nums = re.findall(r'"chapterNumber":\s*(\d+)', text)
                ch_titles = re.findall(r'"chapterName":\s*"([^"]+)"', text)
                if ch_nums:
                    for i, num in enumerate(ch_nums):
                        title = ch_titles[i] if i < len(ch_titles) else ""
                        if title:
                            full_title = f"Chương {num}: {title}"
                        else:
                            full_title = f"Chương {num}"
                        chapters.append({
                            "number": 0,
                            "title": full_title,
                            "url": f"{self.base_domain}/truyen/{slug}/chuong/{num}",
                        })

        # Assign sequential numbers
        for idx, ch in enumerate(chapters, 1):
            ch['number'] = idx
        return chapters

    def _get_rendered_html(self, url, timeout=20000):
        if not self.playwright_available:
            return None
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 720},
                    locale="vi-VN",
                )
                page = context.new_page()
                try:
                    page.goto(url, wait_until="networkidle", timeout=timeout)
                    time.sleep(3)
                    html = page.content()
                    if "Truyện Dịch Miễn Phí" in html and len(html) > 1000:
                        return html
                    return None
                except Exception:
                    return None
                finally:
                    browser.close()
        except Exception:
            return None

    def get_chapter_content(self, chapter_url):
        slug = self._parse_slug()

        ch_num = None
        match = re.search(r"/chuong/(\d+)", chapter_url)
        if match:
            ch_num = match.group(1)

        content = None

        # Try API (likely returns 401, but worth trying)
        if slug and ch_num:
            try:
                resp = self.session.get(
                    f"{API_BASE}/novels/{slug}/chapter/{ch_num}"
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content_data = data.get("content", data.get("data", {}).get("content", ""))
                    if content_data:
                        content = clean_html_content(content_data, report=self.spam_report, chapter_url=chapter_url, chapter_num=ch_num)
            except Exception:
                pass

        if content:
            return content

        # Try Playwright rendering
        if self.playwright_available:
            self.log(f"[*] Thử render chapter page với Playwright...")
            html = self._get_rendered_html(chapter_url)
            if html:
                ch_num = 0
                m2 = re.search(r'(\d+)', chapter_url)
                if m2:
                    ch_num = int(m2.group(1))
                content = clean_html_content(html, report=self.spam_report, chapter_url=chapter_url, chapter_num=ch_num)

        if content:
            return content

        self.log(f"[!] Không thể đọc nội dung chương (cần đăng nhập hoặc bị chặn bot)")
        self.log(f"[!] URL: {chapter_url}")
        self.log(f"[!] Trang web yêu cầu đăng nhập để đọc truyện. Chương này sẽ bị bỏ qua.")
        return None

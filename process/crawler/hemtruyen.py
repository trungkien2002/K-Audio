import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from process.crawler.base import BaseCrawler
from process.crawler.utils import AntiBotSession, clean_html_content


class HemTruyenCrawler(BaseCrawler):
    def __init__(self, url):
        super().__init__(url)
        self.session = AntiBotSession()
        self.base_domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

    def get_story_info(self):
        resp = self.session.get(self.url.rstrip('/') + '/')
        if resp.status_code != 200:
            self.log(f"[!] Không thể truy cập trang truyện, status code: {resp.status_code}")
            return None
        
        # Hemtruyen has malformed HTML, must use html.parser instead of lxml
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        title_el = soup.select_one('.post-title h1')
        title = title_el.get_text(strip=True) if title_el else 'Unknown'
        
        author_el = soup.select_one('.author-content a')
        author = author_el.get_text(strip=True) if author_el else ''
        
        return {
            'title': title,
            'author': author,
            'url': self.url.rstrip('/') + '/'
        }

    def get_chapter_list(self, story_info):
        self.log(f"[*] Đang lấy danh sách chương của truyện từ AJAX...")
        ajax_url = urljoin(story_info['url'], "ajax/chapters/")
        
        resp = self.session.post(ajax_url)
        if resp.status_code != 200:
            self.log(f"[!] Không thể lấy danh sách chương từ AJAX, status code: {resp.status_code}")
            return []
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        links = soup.select('.wp-manga-chapter a')
        
        chapters = []
        for a_tag in links:
            href = a_tag.get('href', '').strip()
            text = a_tag.get_text(strip=True)
            if href:
                chapters.append({
                    'number': 0,
                    'title': text,
                    'url': href
                })
        
        # The list returned by HemTruyen AJAX is in descending order (newest to oldest),
        # we reverse it to process in chronological order (oldest/first to newest/last).
        chapters.reverse()
        
        for idx, ch in enumerate(chapters, 1):
            ch['number'] = idx
            
        return chapters

    def get_chapter_content(self, chapter_url):
        resp = self.session.get(chapter_url)
        if resp.status_code != 200:
            self.log(f"[!] Lỗi tải chương, status code: {resp.status_code}")
            return None
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        content_div = soup.select_one('.reading-content')
        if not content_div:
            self.log(f"[!] Không tìm thấy nội dung chương ở .reading-content")
            return None
            
        # HemTruyen has actual chapter content wrapped in .text-left inside .reading-content
        text_left = content_div.select_one('.text-left')
        target = text_left if text_left else content_div
        
        # Decompose script, style, ads, etc.
        for tag in target(['script', 'style', 'ins', 'iframe', 'noscript']):
            tag.decompose()
            
        for el in target.select('[id*="ads"], [class*="ads"], [class*="quang-cao"], .adsbygoogle'):
            el.decompose()
            
        # Find chapter number from URL for spam reporting
        chapter_num = 0
        m = re.search(r'chuong-(\d+)', chapter_url, re.I)
        if m:
            chapter_num = int(m.group(1))
            
        return clean_html_content(str(target), report=self.spam_report, chapter_url=chapter_url, chapter_num=chapter_num)

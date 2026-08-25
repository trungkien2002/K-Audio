import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from process.crawler.base import BaseCrawler
from process.crawler.utils import AntiBotSession, clean_html_content


class XTruyenCrawler(BaseCrawler):
    def __init__(self, url):
        super().__init__(url)
        self.session = AntiBotSession(min_delay=2.0, max_delay=4.0)

    def _is_cloudflare_blocked(self, resp):
        if resp.status_code == 403:
            text = resp.text.lower()
            if 'cloudflare' in text or 'just a moment' in text or 'challenge' in text:
                return True
        return False

    def get_story_info(self):
        try:
            resp = self.session.get(self.url, allow_redirects=True)
            if resp.status_code != 200:
                if self._is_cloudflare_blocked(resp):
                    self.log("[!] xtruyen.vn bị Cloudflare chặn - không thể crawl")
                    self.log("[!] Thử mở link trên trình duyệt để kiểm tra web còn hoạt động không")
                    return None
                else:
                    self.log(f"[!] xtruyen.vn trả về mã {resp.status_code}")
        except Exception as e:
            self.log(f"[!] Lỗi kết nối xtruyen.vn: {e}")
            return None

        if self._is_cloudflare_blocked(resp):
            self.log("[!] xtruyen.vn yêu cầu JavaScript/Cloudflare - không thể crawl")
            return None

        soup = BeautifulSoup(resp.text, 'lxml')
        title_selectors = [
            'h1[itemprop="name"]', 'h1.title', 'h1',
            'h3.title', '.story-title',
        ]
        title = 'Unknown'
        for sel in title_selectors:
            el = soup.select_one(sel)
            if el:
                title = el.get_text(strip=True)
                break

        author = ''
        author_el = soup.select_one('[itemprop="author"]')
        if author_el:
            author = author_el.get_text(strip=True)

        return {
            'title': title,
            'author': author,
            'url': self.url.rstrip('/') + '/',
        }

    def get_chapter_list(self, story_info):
        chapters = []
        try:
            resp = self.session.get(story_info['url'])
            if resp.status_code != 200:
                return chapters
        except Exception:
            return chapters

        if self._is_cloudflare_blocked(resp):
            return chapters

        soup = BeautifulSoup(resp.text, 'lxml')
        chapter_selectors = [
            'ul.list-chapter a[href*="chuong-"]',
            'ul.list-chapter a[href*="chuong"]',
            '.chapter-list a', '#list-chapter a',
            'a[href*="chuong-"]',
        ]

        links = []
        for sel in chapter_selectors:
            links = soup.select(sel)
            if links:
                break

        if not links:
            select = soup.select_one('select#chapter-select, select.chapter-select, select[name="chapter"]')
            if select:
                for option in select.select('option[value]'):
                    href = option.get('value', '').strip()
                    text = option.get_text(strip=True)
                    if not href:
                        continue
                    full_url = urljoin(story_info['url'], href)
                    # Keep full original title text
                    chapters.append({
                        'number': 0,
                        'title': text,
                        'url': full_url,
                    })
                # Assign sequential numbers
                for idx, ch in enumerate(chapters, 1):
                    ch['number'] = idx
                return chapters

        for a_tag in links:
            href = a_tag.get('href', '').strip()
            if not href:
                continue
            full_url = urljoin(story_info['url'], href)
            text = a_tag.get_text(strip=True)
            # Keep full original title text
            chapters.append({
                'number': 0,
                'title': text,
                'url': full_url,
            })

        # Assign sequential numbers based on order from website
        for idx, ch in enumerate(chapters, 1):
            ch['number'] = idx

        return chapters

    def get_chapter_content(self, chapter_url):
        try:
            resp = self.session.get(chapter_url)
            if resp.status_code != 200:
                return None
        except Exception:
            return None

        if self._is_cloudflare_blocked(resp):
            return None

        soup = BeautifulSoup(resp.text, 'lxml')
        content_selectors = [
            'div#chapter-content', 'div.chapter-content',
            'div#noidung', 'div.content', 'div.reading', 'article',
        ]
        content_div = None
        for sel in content_selectors:
            content_div = soup.select_one(sel)
            if content_div:
                break
        if not content_div:
            content_div = soup
        chapter_num = 0
        m = re.search(r'(\d+)', chapter_url)
        if m:
            chapter_num = int(m.group(1))
        return clean_html_content(str(content_div), report=self.spam_report, chapter_url=chapter_url, chapter_num=chapter_num)

"""Crawler for mtruyen.net — site dùng Next.js + tRPC API."""

import re
import json
import html
import math
from urllib.parse import urljoin, urlparse, quote
from bs4 import BeautifulSoup
from process.crawler.base import BaseCrawler
from process.crawler.utils import AntiBotSession, clean_html_content


class MTruyenCrawler(BaseCrawler):
    def __init__(self, url):
        super().__init__(url)
        self.session = AntiBotSession()
        self.base_domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

    def _extract_slug(self):
        """Extract story slug from URL like /truyen/story-slug or /truyen/story-slug/chuong-1."""
        path = urlparse(self.url).path.strip('/')
        parts = path.split('/')
        # URL format: truyen/{slug} or truyen/{slug}/chuong-{n}
        if len(parts) >= 2 and parts[0] == 'truyen':
            return parts[1]
        return None

    def _trpc_get(self, procedure, input_data):
        """Call tRPC API endpoint."""
        input_json = json.dumps({"json": input_data}, ensure_ascii=False)
        encoded = quote(input_json, safe='')
        api_url = f"{self.base_domain}/api/trpc/{procedure}?input={encoded}"
        resp = self.session.get(api_url)
        if resp.status_code != 200:
            return None
        try:
            data = resp.json()
            return data.get('result', {}).get('data', {}).get('json', None)
        except Exception:
            return None

    def get_story_info(self):
        slug = self._extract_slug()
        if not slug:
            self.log("[!] Không thể trích xuất slug từ URL")
            return None

        # Use tRPC API to get story info
        story_data = self._trpc_get('story.getBySlug', {'slug': slug})
        if not story_data:
            self.log("[!] Không thể lấy thông tin truyện từ API")
            return None

        title = html.unescape(story_data.get('title', 'Unknown'))
        author = html.unescape(story_data.get('authorName', ''))
        story_id = story_data.get('id')
        total_chapters = story_data.get('totalChapters', 0)

        if not story_id:
            self.log("[!] Không tìm thấy Story ID")
            return None

        return {
            'title': title,
            'author': author,
            'story_id': story_id,
            'slug': slug,
            'total_chapters': total_chapters,
            'url': self.url.rstrip('/') + '/'
        }

    def get_chapter_list(self, story_info):
        chapters = []
        story_id = story_info['story_id']
        slug = story_info['slug']
        total_chapters = story_info['total_chapters']
        page_size = 50
        total_pages = max(1, math.ceil(total_chapters / page_size))

        for page in range(1, total_pages + 1):
            self.log(f"[*] Đang lấy trang danh sách {page}/{total_pages}...")

            data = self._trpc_get('chapter.listByStory', {
                'storyId': story_id,
                'page': page,
                'sort': 'asc'
            })

            if not data:
                self.log(f"[!] Lỗi tải danh sách chương trang {page}")
                continue

            items = data.get('items', [])
            actual_total_pages = data.get('totalPages', total_pages)
            if actual_total_pages != total_pages:
                total_pages = actual_total_pages

            for item in items:
                chap_slug = item.get('slug', '')
                chap_number = item.get('chapterNumber', 0)
                chap_title = item.get('title', '')

                chapter_url = f"{self.base_domain}/truyen/{slug}/{chap_slug}"
                chapters.append({
                    'number': chap_number,
                    'title': chap_title or f"Chương {chap_number}",
                    'url': chapter_url,
                })

            self.update_progress(page, total_pages)

        # Re-assign sequential numbers if needed (fallback)
        if not chapters or chapters[0]['number'] == 0:
            for idx, ch in enumerate(chapters, 1):
                ch['number'] = idx

        return chapters

    def get_chapter_content(self, chapter_url):
        resp = self.session.get(chapter_url)
        if resp.status_code != 200:
            self.log(f"[!] Lỗi tải chương, status code: {resp.status_code}")
            return None

        soup = BeautifulSoup(resp.text, 'lxml')

        # mtruyen.net uses Next.js SSR — content is in RSC payload within script tags
        # First try to find rendered chapter-content div
        content_div = soup.select_one('div.chapter-content')
        if not content_div:
            content_div = soup.select_one('article.chapter-content')

        # If not found in static HTML, extract from RSC payload (__next_f)
        if not content_div or not content_div.get_text(strip=True):
            content_text = self._extract_from_rsc_payload(resp.text)
            if content_text:
                return content_text

        if not content_div:
            self.log("[!] Không tìm thấy nội dung chương")
            return None

        # Clean up
        for tag in content_div(['script', 'style', 'ins', 'iframe', 'noscript']):
            tag.decompose()
        for el in content_div.select('[id*="ads"], [class*="ads"], [class*="quang-cao"]'):
            el.decompose()

        chapter_num = 0
        m = re.search(r'chuong-(\d+)', chapter_url, re.I)
        if m:
            chapter_num = int(m.group(1))

        return clean_html_content(
            str(content_div),
            report=self.spam_report,
            chapter_url=chapter_url,
            chapter_num=chapter_num
        )

    def _extract_from_rsc_payload(self, html_text):
        """Extract chapter content from Next.js RSC payload embedded in script tags."""
        # RSC payload is in self.__next_f.push([1, "..."]) script blocks
        # Find all such blocks and concatenate
        rsc_parts = []
        pattern = re.compile(r'self\.__next_f\.push\(\[1,\s*"(.*?)"\]\)', re.DOTALL)
        for m in pattern.finditer(html_text):
            rsc_parts.append(m.group(1))

        if not rsc_parts:
            return None

        rsc_text = ''.join(rsc_parts)

        # Unescape JSON string escapes
        try:
            rsc_text = rsc_text.encode().decode('unicode_escape')
        except Exception:
            pass

        # Look for chapter content — paragraphs with story text
        # The content typically appears as arrays of ["$","p",null,{"children":"..."}]
        paragraphs = []
        # Pattern to find paragraph children in RSC format
        p_pattern = re.compile(
            r'\["\$","p",(?:null|"\w+"),\{[^}]*"children"\s*:\s*"([^"]+)"',
            re.DOTALL
        )
        for pm in p_pattern.finditer(rsc_text):
            text = pm.group(1).strip()
            if text and len(text) > 5:
                paragraphs.append(text)

        # Also try nested children arrays (more complex RSC format)
        if not paragraphs:
            p_pattern2 = re.compile(
                r'\["\$","p",(?:null|"\w+"),\{[^}]*"children"\s*:\s*\[(.*?)\]',
                re.DOTALL
            )
            for pm in p_pattern2.finditer(rsc_text):
                inner = pm.group(1)
                # Extract string parts from the children array
                str_parts = re.findall(r'"([^"]{5,})"', inner)
                if str_parts:
                    combined = ''.join(str_parts)
                    if combined.strip():
                        paragraphs.append(combined.strip())

        if paragraphs:
            return '\n\n'.join(paragraphs)
        return None

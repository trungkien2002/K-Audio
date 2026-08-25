import re
import json
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from process.crawler.base import BaseCrawler
from process.crawler.utils import AntiBotSession, clean_html_content, find_hidden_elements


class KhoTruyenChuCrawler(BaseCrawler):
    def __init__(self, url):
        super().__init__(url)
        self.session = AntiBotSession()
        self.base_domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

    def get_story_info(self):
        resp = self.session.get(self.url.rstrip('/') + '/')
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, 'lxml')

        title_el = soup.select_one('.truyen-title')
        title = title_el.get_text(strip=True) if title_el else 'Unknown'

        author = ''
        author_meta = soup.select_one('.truyen-meta')
        if author_meta:
            author_text = author_meta.get_text(strip=True)
            m = re.search(r'Tác\s*giả[:\s]*(.+?)(?:[|,\s]|$)', author_text)
            if m:
                author = m.group(1).strip()

        # Get story slug from URL for taxonomy
        path = urlparse(self.url).path.strip('/')
        story_slug = path.split('/')[-1] if path else ''

        # Find pagination to get total number of pages
        total_pages = 1
        pagination = soup.select_one('.ct-pagination')
        if pagination:
            page_links = pagination.select('a.page-numbers, span.page-numbers')
            for el in page_links:
                m = re.search(r'(\d+)', el.get_text(strip=True))
                if m:
                    p = int(m.group(1))
                    if p > total_pages:
                        total_pages = p

        return {
            'title': title,
            'author': author,
            'story_slug': story_slug,
            'total_pages': total_pages,
            'url': self.url.rstrip('/') + '/'
        }

    def get_chapter_list(self, story_info):
        chapters = []
        total_pages = story_info['total_pages']
        story_url = story_info['url']

        for page in range(1, total_pages + 1):
            self.log(f"[*] Đang lấy trang danh sách {page}/{total_pages}...")
            if page == 1:
                page_url = story_url
            else:
                page_url = f"{story_url}page/{page}/"

            resp = self.session.get(page_url)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, 'lxml')
            entries = soup.select('body.tax-bo_truyen .entries article')
            if not entries:
                entries = soup.select('.entries article')

            for article in entries:
                a_tag = article.select_one('.entry-title a')
                if not a_tag:
                    continue
                href = a_tag.get('href', '').strip()
                text = a_tag.get_text(strip=True)

                if not href:
                    continue

                full_url = urljoin(self.base_domain, href)

                # Keep full original title text
                chapters.append({
                    'number': 0,  # will be assigned sequentially below
                    'title': text,
                    'url': full_url,
                })

            self.update_progress(page, total_pages)

        # Assign sequential numbers based on order from website
        for idx, ch in enumerate(chapters, 1):
            ch['number'] = idx

        return chapters

    def get_chapter_content(self, chapter_url):
        resp = self.session.get(chapter_url)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, 'lxml')

        content_div = soup.select_one('div.entry-content')
        if not content_div:
            content_div = soup.select_one('article')
        if not content_div:
            content_div = soup

        for tag in content_div(['script', 'style', 'ins', 'iframe', 'noscript']):
            tag.decompose()

        for ad in content_div.select('[class*="code-block"], .ads, .adsbygoogle, [class*="quang-cao"]'):
            ad.decompose()

        for tag in content_div.find_all(['div', 'span', 'p']):
            if not tag.get_text(strip=True):
                tag.decompose()

        chapter_num = 0
        m = re.search(r'chuong-(\d+)', chapter_url, re.I)
        if m:
            chapter_num = int(m.group(1))

        return clean_html_content(str(content_div), report=self.spam_report, chapter_url=chapter_url, chapter_num=chapter_num)

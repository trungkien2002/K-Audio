import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from process.crawler.base import BaseCrawler
from process.crawler.utils import AntiBotSession, clean_html_content


class TruyenFullCrawler(BaseCrawler):
    def __init__(self, url):
        super().__init__(url)
        self.session = AntiBotSession()
        self.base_domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

    def get_story_info(self):
        resp = self.session.get(self.url.rstrip('/') + '/')
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, 'lxml')
        title_el = soup.select_one('h3.title[itemprop="name"]')
        title = title_el.get_text(strip=True) if title_el else 'Unknown'

        author_el = soup.select_one('a[itemprop="author"]')
        author = author_el.get_text(strip=True) if author_el else ''

        # Find total pages
        pages = 1
        pagination = soup.select_one('ul.pagination.pagination-sm')
        if pagination:
            page_links = pagination.select('a[href*="trang-"]')
            for link in page_links:
                m = re.search(r'trang-(\d+)', link.get('href', ''))
                if m:
                    p = int(m.group(1))
                    if p > pages:
                        pages = p
            # Also check form for hidden page input
            page_form = pagination.select_one('form#page_jump')
            if page_form:
                last_link = pagination.select_one('li:last-child a')
                if last_link:
                    m = re.search(r'trang-(\d+)', last_link.get('href', ''))
                    if m:
                        pages = int(m.group(1))

        return {
            'title': title,
            'author': author,
            'total_pages': pages,
            'chapters_per_page': 50,
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
                page_url = urljoin(story_url, f'trang-{page}/#list-chapter')

            resp = self.session.get(page_url)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, 'lxml')
            chapter_list = soup.select_one('div#list-chapter')
            if not chapter_list:
                continue

            for ul in chapter_list.select('ul.list-chapter'):
                for li in ul.select('li'):
                    a_tag = li.select_one('a[href*="chuong-"]')
                    if not a_tag:
                        continue
                    href = a_tag.get('href', '').strip()
                    if not href:
                        continue
                    full_url = urljoin(self.base_domain, href)

                    # Keep full original title text
                    chapter_text = a_tag.get_text(strip=True)

                    chapters.append({
                        'number': 0,  # will be assigned sequentially below
                        'title': chapter_text,
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

        content_div = soup.select_one('div#chapter-c.chapter-c')
        if not content_div:
            content_div = soup.select_one('div#chapter-content')
        if not content_div:
            content_div = soup.select_one('div.chapter-content')
        if not content_div:
            content_div = soup.select_one('div#noidung')
        if not content_div:
            content_div = soup

        for tag in content_div(['script', 'style', 'ins', 'iframe', 'noscript']):
            tag.decompose()
        for el in content_div.select('[id*="ads"], [class*="ads"], [class*="quang-cao"]'):
            el.decompose()

        chapter_num = 0
        m = re.search(r'chuong-(\d+)', chapter_url, re.I)
        if m:
            chapter_num = int(m.group(1))

        return clean_html_content(str(content_div), report=self.spam_report, chapter_url=chapter_url, chapter_num=chapter_num)

import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from process.crawler.base import BaseCrawler
from process.crawler.utils import AntiBotSession, clean_html_content


class TruyenMoiCrawler(BaseCrawler):
    def __init__(self, url):
        super().__init__(url)
        self.session = AntiBotSession()
        self.base_domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

    def get_story_info(self):
        resp = self.session.get(self.url.rstrip('/') + '/')
        if resp.status_code != 200:
            self.log(f"[!] Không thể truy cập trang truyện, status code: {resp.status_code}")
            return None

        soup = BeautifulSoup(resp.text, 'lxml')

        # 1. Get Title
        title_el = soup.select_one('h1.story-title a') or soup.select_one('h1.story-title') or soup.select_one('h1[itemprop="name"]')
        title = title_el.get_text(strip=True) if title_el else 'Unknown'

        # 2. Get Author
        author_div = soup.find(attrs={'itemprop': 'author'})
        author = ''
        if author_div:
            author_a = author_div.select_one('a[itemprop="url"] span[itemprop="name"]')
            if author_a:
                author = author_a.get_text(strip=True)
            else:
                author_a = author_div.select_one('a')
                if author_a:
                    author = author_a.get_text(strip=True)

        # 3. Find total pages from pagination
        pages = 1
        pagination = soup.select_one('ul.pagination')
        if pagination:
            page_links = pagination.select('a[href*="/trang-"]')
            for link in page_links:
                m = re.search(r'/trang-(\d+)', link.get('href', ''))
                if m:
                    p = int(m.group(1))
                    if p > pages:
                        pages = p

        return {
            'title': title,
            'author': author,
            'total_pages': pages,
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
                page_url = story_url.rstrip('/') + f'/trang-{page}'

            resp = self.session.get(page_url)
            if resp.status_code != 200:
                self.log(f"[!] Lỗi tải trang {page}, status code: {resp.status_code}")
                continue

            soup = BeautifulSoup(resp.text, 'lxml')

            # Find all chapter lists (there may be multiple: "Chương mới nhất" and "Danh sách chương")
            # We want the full chapter list, which is the second #list-chapter div
            list_chapter_divs = soup.select('div#list-chapter')

            # Use the last one if there are multiple (it's the full chapter list)
            target_div = list_chapter_divs[-1] if list_chapter_divs else None
            if not target_div:
                continue

            for ul in target_div.select('ul.list-chapter'):
                for li in ul.select('li'):
                    a_tag = li.select_one('a[href*="/chuong-"]')
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
            self.log(f"[!] Lỗi tải chương, status code: {resp.status_code}")
            return None

        soup = BeautifulSoup(resp.text, 'lxml')

        # Primary: article.chapter-content
        content_div = soup.select_one('article.chapter-content')
        if not content_div:
            content_div = soup.select_one('div.chapter-content')
        if not content_div:
            content_div = soup.select_one('div#chapter-c')
        if not content_div:
            content_div = soup

        # Remove script, style, ads, and other unwanted elements
        for tag in content_div(['script', 'style', 'ins', 'iframe', 'noscript']):
            tag.decompose()
        for el in content_div.select('[id*="ads"], [class*="ads"], [class*="quang-cao"], .adsbygoogle'):
            el.decompose()

        # Remove empty tags
        for tag in content_div.find_all(['div', 'span', 'p']):
            if not tag.get_text(strip=True):
                tag.decompose()

        chapter_num = 0
        m = re.search(r'chuong-(\d+)', chapter_url, re.I)
        if m:
            chapter_num = int(m.group(1))

        return clean_html_content(str(content_div), report=self.spam_report, chapter_url=chapter_url, chapter_num=chapter_num)

import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from process.crawler.base import BaseCrawler
from process.crawler.utils import AntiBotSession, clean_html_content


class MeTruyenChuVNCrawler(BaseCrawler):
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
        title_el = soup.select_one('h1[itemprop="name"]') or soup.select_one('h1')
        title = title_el.get_text(strip=True) if title_el else 'Unknown'
        
        # 2. Get Author
        author_el = soup.select_one('a[itemprop="author"]') or soup.select_one('[itemprop="author"]')
        author = author_el.get_text(strip=True) if author_el else ''

        # 3. Get Book ID (bid)
        bid_el = soup.select_one('input[name="bid"]')
        if not bid_el:
            self.log("[!] Không tìm thấy Book ID (bid) của truyện")
            return None
        book_id = bid_el.get('value', '').strip()
        if not book_id:
            self.log("[!] Book ID rỗng")
            return None

        # 4. Get Total Pages via first AJAX request
        total_pages = 1
        ajax_url = urljoin(self.base_domain, f"/get/listchap/{book_id}?page=1")
        try:
            ajax_resp = self.session.get(ajax_url)
            if ajax_resp.status_code == 200:
                data = ajax_resp.json()
                html_data = data.get("data", "")
                if html_data:
                    ajax_soup = BeautifulSoup(html_data, 'lxml')
                    paging = ajax_soup.select_one('.paging')
                    if paging:
                        page_links = paging.select('a')
                        for el in page_links:
                            # 1. Try parsing from text
                            text_val = el.get_text(strip=True)
                            m = re.search(r'(\d+)', text_val)
                            if m:
                                p = int(m.group(1))
                                if p > total_pages:
                                    total_pages = p
                            
                            # 2. Try parsing from onclick attribute (e.g., page(91057,16);)
                            onclick_val = el.get('onclick', '')
                            if onclick_val:
                                m_onclick = re.search(r'page\(\s*(?:\d+\s*,\s*)?(\d+)\s*\)', onclick_val)
                                if m_onclick:
                                    p = int(m_onclick.group(1))
                                    if p > total_pages:
                                        total_pages = p
        except Exception as e:
            self.log(f"[!] Lỗi khi lấy số trang phân trang: {e}")

        return {
            'title': title,
            'author': author,
            'book_id': book_id,
            'total_pages': total_pages,
            'url': self.url.rstrip('/') + '/'
        }

    def get_chapter_list(self, story_info):
        chapters = []
        book_id = story_info['book_id']
        total_pages = story_info['total_pages']

        for page in range(1, total_pages + 1):
            self.log(f"[*] Đang lấy trang danh sách {page}/{total_pages}...")
            ajax_url = urljoin(self.base_domain, f"/get/listchap/{book_id}?page={page}")
            
            try:
                resp = self.session.get(ajax_url)
                if resp.status_code != 200:
                    self.log(f"[!] Lỗi tải danh sách chương trang {page}, status code: {resp.status_code}")
                    continue
                
                data = resp.json()
                html_data = data.get("data", "")
                if not html_data:
                    continue

                soup = BeautifulSoup(html_data, 'lxml')
                # Find all chapter links
                links = soup.select('.clearfix ul li a') or soup.select('ul li a') or soup.select('a')
                
                for a_tag in links:
                    href = a_tag.get('href', '').strip()
                    if not href or '/chuong-' not in href:
                        continue
                    
                    full_url = urljoin(self.base_domain, href)
                    text = a_tag.get_text(strip=True)
                    
                    chapters.append({
                        'number': 0,  # assigned sequentially below
                        'title': text,
                        'url': full_url,
                    })
            except Exception as e:
                self.log(f"[!] Lỗi khi xử lý trang {page}: {e}")

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

        content_div = soup.select_one('.truyen')
        if not content_div:
            content_div = soup.select_one('article')
        if not content_div:
            content_div = soup

        # Decompose unnecessary script and ad tags
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

import os
import re
import time
import random
import json
import cloudscraper
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0',
]


INVISIBLE_CHARS = re.compile(
    '[\u200b\u200c\u200d\u200e\u200f\u2028\u2029\u202a\u202b\u202c\u202d\u202e\u202f\ufeff\u2060\u00ad\u180e]'
)

SPAM_PHRASES = re.compile(
    r'(?:'
    r'cảnh\s*báo\s*ăn\s*cắp\s*nội\s*dung\s*từ\s*khotruyenchu\S+'
    r'|truyện\s*được\s*lấy\s*từ\s*khotruyenchu\S+'
    r'|bản\s*quyền\s*bản\s*dịch\s*thuộc\s*về\s*khotruyenchu\S+'
    r'|nội\s*dung\s*chương\s*này\s*được\s*bảo\s*vệ\s*bởi\s*khotruyenchu\S+'
    r'|website\s*khotruyenchu\b.*?cập\s*nhật\s*chương\s*mới'
    r'|đọc\s*bản\s*dịch\s*chuẩn\s*nhất\s*ở\s*khotruyenchu\S+'
    r'|đọc\s*truyện\s*chữ\s*hay\s*mỗi\s*ngày\s*tại\s*website\s*khotruyenchu\S+'
    r'|truy\s*cập\s*khotruyenchu\b.*?để\s*đọc\s*truyện\s*không\s*quảng\s*cáo'
    r'|chương\s*mới\s*nhất\s*luôn\s*được\s*đăng\s*sớm\s*nhất\s*trên\s*khotruyenchu\S+'
    r'|đừng\s*đọc\s*ở\s*web\s*lậu.*?ủng\s*hộ\s*khotruyenchu\S+'
    r'|ủng\s*hộ\s*nhóm\s*dịch.*?đọc\s*tại\s*khotruyenchu\S+'
    r'|web\s*copy\s*vui\s*lòng\s*để\s*lại\s*nguồn\s*khotruyenchu\S+'
    r'|chỉ\s*có\s*tại\s*khotruyenchu\b.*?web\s*truyện\s*chữ\s*hàng\s*đầu'
    r'|nguồn\s*truyện\s*gốc.*?:\s*khotruyenchu\S+'
    r'|hãy\s*tôn\s*trọng\s*công\s*sức\s*converter\s*tại\s*khotruyenchu\S+'
    r'|bạn\s*đang\s*đọc\s*truyện\s*tại\s*khotruyenchu\S+'
    r'|chương\s*truyện\s*này\s*được\s*copy\s*từ\s*khotruyenchu\S+'
    r'|phát\s*hiện\s*web\s*lậu\s*cào\s*truyện\s*từ\s*khotruyenchu\S+'
    r'|mọi\s*trang\s*web\s*khác\s*copy\s*từ\s*khotruyenchu\b.*?trang\s*lậu'
    r'|khotruyenchu\.sbs\s*là\s*web\s*chính\s*chủ\s*của\s*bản\s*dịch\s*này'
    r'|t\s*[\.\s_]*r\s*[\.\s_]*u\s*[\.\s_]*y\s*[\.\s_]*e\s*[\.\s_]*n\s*[\.\s_]*y\s*[\.\s_]*y(?:\s*\.\s*c\s*\.\s*o\s*\.\s*m)?'
    r')',
    re.I
)

# Catch any remaining khotruyenchu domain references as inline text
INLINE_SPAM_DOMAIN = re.compile(r'khotruyenchu\.(?:space|sbs|fun)\S*', re.I)

# Navigation and UI text patterns to filter from chapter content
NAV_LINE_PATTERNS = re.compile(
    r'^\s*(?:'
    # Navigation buttons
    r'[«‹<]\s*Chương\s*trước'
    r'|Chương\s*trước\s*[»›>]?'
    r'|[«‹<]?\s*Chương\s*sau\s*[»›>]'
    r'|Chương\s*sau$'
    r'|[≣☰]\s*Mục\s*lục'
    r'|Mục\s*lục$'
    r'|Danh\s*sách\s*chương'
    r'|Báo\s*lỗi\s*chương'
    r'|Báo\s*lỗi$'
    r'|Chương\s*trước\s*Chương\s*sau'
    r'|Chương\s*trước\s*Mục\s*lục\s*Chương\s*sau'
    # Font size controls
    r'|Cỡ\s*chữ\s*:?\s*'
    r'|A[\-\+]$'
    r'|A\-\s*A\+'
    # Theme / display controls
    r'|[◑◐●○]\s*'
    r'|Giao\s*diện'
    r'|Chế\s*độ\s*(?:sáng|tối|đọc)'
    r'|Sáng$'
    r'|Tối$'
    r'|Nền\s*(?:sáng|tối|mặc\s*định)'
    # Common reading page UI
    r'|Thêm\s*vào\s*thư\s*viện'
    r'|Đánh\s*dấu'
    r'|Theo\s*dõi'
    r'|Chia\s*sẻ'
    r'|Cài\s*đặt'
    r'|Tùy\s*chỉnh'
    r'|Bình\s*luận\s*\(\d*\)'
    r'|Bình\s*luận$'
    r'|Đọc\s*tiếp'
    r'|Trang\s*chủ'
    r'|Tắt\s*quảng\s*cáo'
    r'|Đọc\s*truyện\s*chữ'
    r')\s*$',
    re.I
)

HIDDEN_STYLE_PATTERNS = re.compile(
    r'(display\s*:\s*none|'
    r'opacity\s*:\s*0(\.0)?|'
    r'position\s*:\s*absolute;\s*[^}]*left\s*:\s*-\d+px|'
    r'font-size\s*:\s*0(px)?|'
    r'font-size\s*:\s*1px|'
    r'visibility\s*:\s*hidden|'
    r'overflow\s*:\s*hidden;\s*(width|height)\s*:\s*0)',
    re.I
)


def strip_invisible(text):
    return INVISIBLE_CHARS.sub('', text)


def remove_spam_from_line(line):
    result = SPAM_PHRASES.sub('', line)
    result = INLINE_SPAM_DOMAIN.sub('', result)
    return result.strip()


def is_spam_line(line):
    if re.search(r'https?://\S+', line.lower()):
        return True
    if NAV_LINE_PATTERNS.match(line.strip()):
        return True
    return False


def find_hidden_elements(soup):
    seen = set()
    found = []
    for tag in soup.find_all(style=HIDDEN_STYLE_PATTERNS):
        tag_id = id(tag)
        if tag_id not in seen:
            seen.add(tag_id)
            found.append(tag)
    for tag in soup.find_all(['em', 'strong', 'span', 'div'], style=re.compile(r'opacity\s*:\s*0', re.I)):
        tag_id = id(tag)
        if tag_id not in seen:
            seen.add(tag_id)
            found.append(tag)
    return found


class SpamReport:
    def __init__(self):
        self.entries = []

    def record(self, chapter_url, chapter_num, tag_name, tag_class, tag_style, original_text, cleaned_text, pattern):
        self.entries.append({
            'chapter_url': chapter_url,
            'chapter_num': chapter_num,
            'tag_name': tag_name,
            'tag_class': tag_class,
            'tag_style': tag_style,
            'original_text': original_text,
            'cleaned_text': cleaned_text,
            'pattern': pattern,
        })

    def record_line_spam(self, chapter_url, chapter_num, original_line, cleaned_line, pattern):
        self.entries.append({
            'chapter_url': chapter_url,
            'chapter_num': chapter_num,
            'tag_name': 'text_line',
            'tag_class': '',
            'tag_style': '',
            'original_text': original_line,
            'cleaned_text': cleaned_line,
            'pattern': pattern,
        })

    def save(self, filepath):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.entries, f, ensure_ascii=False, indent=2)

    @property
    def total_spam_removed(self):
        return len(self.entries)


class AntiBotSession:
    def __init__(self, use_cloudscraper=True, min_delay=2.0, max_delay=5.0, proxy=None):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.proxy = proxy
        self.use_cloudscraper = use_cloudscraper
        self.log_callback = None
        if use_cloudscraper:
            scraper_kwargs = {}
            if proxy:
                scraper_kwargs['proxies'] = {'http': proxy, 'https': proxy}
            self.session = cloudscraper.create_scraper(
                browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False},
                **scraper_kwargs
            )
        else:
            self.session = self._create_requests_session()
        self.last_request_time = 0

    def _create_requests_session(self):
        import requests as req
        session = req.Session()
        if self.proxy:
            session.proxies = {'http': self.proxy, 'https': self.proxy}
        retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[403, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def _random_delay(self):
        elapsed = time.time() - self.last_request_time
        base_delay = random.uniform(self.min_delay, self.max_delay)
        if elapsed < base_delay:
            time.sleep(base_delay - elapsed)
        if random.random() < 0.1:
            time.sleep(random.uniform(3.0, 8.0))
        self.last_request_time = time.time()

    def get(self, url, **kwargs):
        retries = kwargs.pop('retries', 5)
        backoff = kwargs.pop('backoff', 2.0)
        
        for attempt in range(retries):
            self._random_delay()
            
            kwargs_copy = kwargs.copy()
            headers = kwargs_copy.pop('headers', {})
            current_headers = headers.copy()
            current_headers.setdefault('User-Agent', random.choice(USER_AGENTS))
            current_headers.setdefault('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
            current_headers.setdefault('Accept-Language', 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7')
            timeout = kwargs_copy.pop('timeout', 30)
            
            try:
                resp = self.session.get(url, headers=current_headers, timeout=timeout, **kwargs_copy)
                if resp.status_code in [429, 500, 502, 503, 504] and attempt < retries - 1:
                    msg = f"[!] Lỗi HTTP {resp.status_code}. Đang thử lại lần {attempt + 2}/{retries} sau {backoff:.1f} giây..."
                    if self.log_callback:
                        self.log_callback(msg)
                    else:
                        print(msg)
                    time.sleep(backoff)
                    backoff *= 1.5
                    continue
                return resp
            except Exception as e:
                if attempt == retries - 1:
                    raise e
                
                msg = f"[!] Lỗi kết nối ({e}). Đang thử lại lần {attempt + 2}/{retries} sau {backoff:.1f} giây..."
                if self.log_callback:
                    self.log_callback(msg)
                else:
                    print(msg)
                
                err_msg = str(e).lower()
                is_connection_error = (
                    "connection aborted" in err_msg or 
                    "10054" in err_msg or 
                    "connection reset" in err_msg or
                    "forcibly closed" in err_msg
                )
                
                if is_connection_error:
                    try:
                        self.session.close()
                    except Exception:
                        pass
                    
                    if self.use_cloudscraper:
                        scraper_kwargs = {}
                        if self.proxy:
                            scraper_kwargs['proxies'] = {'http': self.proxy, 'https': self.proxy}
                        self.session = cloudscraper.create_scraper(
                            browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False},
                            **scraper_kwargs
                        )
                    else:
                        self.session = self._create_requests_session()
                
                time.sleep(backoff)
                backoff *= 1.5

    def post(self, url, **kwargs):
        retries = kwargs.pop('retries', 3)
        backoff = kwargs.pop('backoff', 2.0)
        
        for attempt in range(retries):
            self._random_delay()
            
            kwargs_copy = kwargs.copy()
            headers = kwargs_copy.pop('headers', {})
            current_headers = headers.copy()
            current_headers.setdefault('User-Agent', random.choice(USER_AGENTS))
            current_headers.setdefault('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
            current_headers.setdefault('Accept-Language', 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7')
            timeout = kwargs_copy.pop('timeout', 30)
            
            try:
                resp = self.session.post(url, headers=current_headers, timeout=timeout, **kwargs_copy)
                if resp.status_code in [429, 500, 502, 503, 504] and attempt < retries - 1:
                    msg = f"[!] Lỗi HTTP POST {resp.status_code}. Đang thử lại lần {attempt + 2}/{retries} sau {backoff:.1f} giây..."
                    if self.log_callback:
                        self.log_callback(msg)
                    else:
                        print(msg)
                    time.sleep(backoff)
                    backoff *= 1.5
                    continue
                return resp
            except Exception as e:
                if attempt == retries - 1:
                    raise e
                
                msg = f"[!] Lỗi kết nối POST ({e}). Đang thử lại lần {attempt + 2}/{retries} sau {backoff:.1f} giây..."
                if self.log_callback:
                    self.log_callback(msg)
                else:
                    print(msg)
                
                time.sleep(backoff)
                backoff *= 1.5

    def close(self):
        self.session.close()


def sanitize_filename(name):
    name = re.sub(r'[\\/:*?"<>|]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    name = name[:200]
    return name


def clean_html_content(html_text, report=None, chapter_url='', chapter_num=0):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_text, 'lxml')

    for tag in soup(['script', 'style', 'ins', 'iframe', 'noscript']):
        tag.decompose()

    hidden = find_hidden_elements(soup)
    for tag in hidden:
        original = tag.get_text(strip=True)
        if original:
            cleaned = strip_invisible(original)
            cleaned = remove_spam_from_line(cleaned)
            pattern = str(tag.get('style', ''))[:100]
            class_name = ' '.join(tag.get('class', [])) if tag.get('class') else ''
            if report:
                report.record(
                    chapter_url=chapter_url,
                    chapter_num=chapter_num,
                    tag_name=tag.name,
                    tag_class=class_name,
                    tag_style=pattern,
                    original_text=original,
                    cleaned_text=cleaned,
                    pattern='hidden_element'
                )
        tag.decompose()

    for tag in soup.find_all(['div', 'span', 'p']):
        if not tag.get_text(strip=True):
            tag.decompose()

    text = soup.get_text(separator='\n')
    text = strip_invisible(text)

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    filtered = []
    for line in lines:
        if is_spam_line(line):
            if report:
                report.record_line_spam(
                    chapter_url=chapter_url, chapter_num=chapter_num,
                    original_line=line, cleaned_line='',
                    pattern='url_line'
                )
            continue
        cleaned = remove_spam_from_line(line)
        if cleaned != line.strip():
            if report:
                report.record_line_spam(
                    chapter_url=chapter_url, chapter_num=chapter_num,
                    original_line=line, cleaned_line=cleaned,
                    pattern='spam_phrase_inline'
                )
        if cleaned:
            filtered.append(cleaned)

    return '\n\n'.join(filtered)


def chapter_exists(output_dir, story_name, chapter_number):
    """Check if a chapter file already exists in the story directory."""
    story_dir = os.path.join(output_dir, sanitize_filename(story_name))
    if not os.path.isdir(story_dir):
        return False
    padded = f"{chapter_number:05d}"
    prefix = f"{padded} - "
    for fname in os.listdir(story_dir):
        if fname.startswith(prefix) and fname.endswith('.txt'):
            return True
    return False


def strip_duplicate_title(content, chapter_title, chapter_number):
    if not content:
        return content
    lines = content.splitlines()
    first_line_idx = -1
    for idx, line in enumerate(lines[:5]):
        if line.strip():
            first_line_idx = idx
            break
    if first_line_idx == -1:
        return content

    first_line = lines[first_line_idx].strip()
    first_line_lower = first_line.lower()
    should_remove = False

    if chapter_title:
        title_clean = re.sub(r'[\\/:*?"<>|\s\.,:-]', '', chapter_title).lower()
        line_clean = re.sub(r'[\\/:*?"<>|\s\.,:-]', '', first_line).lower()
        if title_clean and title_clean in line_clean and len(first_line) < 150:
            should_remove = True

    if not should_remove and chapter_number:
        m = re.match(r'^(?:chương|quyển)\s*(\d+)', first_line_lower)
        if m:
            num = int(m.group(1))
            if num == chapter_number and len(first_line) < 150:
                should_remove = True

    if should_remove:
        remaining = lines[first_line_idx + 1:]
        while remaining and not remaining[0].strip():
            remaining.pop(0)
        return "\n".join(lines[:first_line_idx] + remaining)
    return content


def save_chapter(output_dir, story_name, chapter_number, chapter_title, content):
    content = strip_duplicate_title(content, chapter_title, chapter_number)
    story_dir = os.path.join(output_dir, sanitize_filename(story_name))
    os.makedirs(story_dir, exist_ok=True)
    padded = f"{chapter_number:05d}"
    if chapter_title:
        filename = f"{padded} - {sanitize_filename(chapter_title)}.txt"
    else:
        filename = f"{padded}.txt"
    filepath = os.path.join(story_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        header = f"{story_name}\n{'=' * 40}\n"
        if chapter_title:
            title_with_dot = chapter_title.strip()
            if title_with_dot and not title_with_dot.endswith('.'):
                title_with_dot += '.'
            header += f"{title_with_dot}\n"
        else:
            header += f"Chương {chapter_number}.\n"
        header += f"{'=' * 40}\n\n"
        f.write(header)
        f.write(content)
    return filepath

"""Crawler package — crawl truyện từ nhiều website."""

from process.crawler.truyenfull import TruyenFullCrawler
from process.crawler.khotruyenchu import KhoTruyenChuCrawler
from process.crawler.truyendichmienphi import TruyenDichMienPhiCrawler
from process.crawler.xtruyen import XTruyenCrawler
from process.crawler.metruyenchuvn import MeTruyenChuVNCrawler
from process.crawler.truyenmoi import TruyenMoiCrawler
from process.crawler.mtruyen import MTruyenCrawler
from process.crawler.hemtruyen import HemTruyenCrawler


def get_crawler(url):
    """Return the appropriate crawler based on the URL domain."""
    from urllib.parse import urlparse

    domain_map = {
        'truyenfull.today': TruyenFullCrawler,
        'truyenfullmoi.com': TruyenFullCrawler,
        'truyenfull.live': TruyenFullCrawler,
        'khotruyenchu.space': KhoTruyenChuCrawler,
        'khotruyenchu.fun': KhoTruyenChuCrawler,
        'truyendichmienphi.com': TruyenDichMienPhiCrawler,
        'xtruyen.vn': XTruyenCrawler,
        'metruyenchuvn.com': MeTruyenChuVNCrawler,
        'truyenmoiss.org': TruyenMoiCrawler,
        'mtruyen.net': MTruyenCrawler,
        'hemtruyen.me': HemTruyenCrawler,
    }
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.hostname or "").lower().rstrip(".")
    for domain, crawler_cls in domain_map.items():
        if host == domain or host.endswith(f".{domain}"):
            return crawler_cls(url)
    return None

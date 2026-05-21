"""웹페이지를 크롤해 마크다운으로 추출하는 유틸 (crawl4ai 옵셔널 의존)."""
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def is_available() -> bool:
    """crawl4ai 설치 여부 반환."""
    return _AVAILABLE


def _extract_title(result, url: str) -> str:
    """result.metadata → HTML <title> → URL 도메인 순으로 제목 추출."""
    metadata = getattr(result, "metadata", None) or {}
    if isinstance(metadata, dict):
        title = (metadata.get("title") or "").strip()
        if title:
            return title

    html = getattr(result, "html", "") or ""
    if html:
        try:
            from bs4 import BeautifulSoup
            tag = BeautifulSoup(html, "html.parser").title
            if tag and tag.string and tag.string.strip():
                return tag.string.strip()
        except Exception:
            pass

    return urlparse(url).netloc or url


async def crawl_url(url: str) -> dict:
    """주어진 URL을 크롤해 {"markdown": str, "title": str} 반환.

    crawl4ai 미설치 시 RuntimeError. 크롤 실패/빈 결과 시에도 RuntimeError.
    """
    if not _AVAILABLE:
        raise RuntimeError(
            "crawl4ai 미설치 — 로컬 환경에서 'pip install crawl4ai && crawl4ai-setup' 후 사용 가능합니다"
        )

    config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        result = await crawler.arun(url=url, config=config)

    if not getattr(result, "success", False):
        raise RuntimeError(getattr(result, "error_message", None) or "웹페이지 크롤링에 실패했습니다")

    md_obj = getattr(result, "markdown", None)
    markdown = ""
    if md_obj is not None:
        markdown = (getattr(md_obj, "fit_markdown", "") or getattr(md_obj, "raw_markdown", "") or str(md_obj)).strip()

    if not markdown:
        raise RuntimeError("크롤링 결과에서 본문을 추출하지 못했습니다")

    return {"markdown": markdown, "title": _extract_title(result, url)}

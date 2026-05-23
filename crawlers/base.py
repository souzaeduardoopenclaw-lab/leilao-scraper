"""Crawl4AI wrapper for web crawling with pagination support."""

import asyncio
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin, urlparse

from crawl4ai import AsyncWebCrawler
from crawl4ai import CrawlerRunConfig

from config import settings


class BaseCrawler:
    """Wrapper around Crawl4AI with pagination support."""

    def __init__(
        self,
        delay: float = None,
        max_pages: int = None,
        user_agent: str = None,
    ):
        """Initialize the crawler.

        Args:
            delay: Delay between requests in seconds.
            max_pages: Maximum number of pages to crawl.
            user_agent: Custom user agent string.
        """
        self.delay = delay or settings.CRAWL_DELAY
        self.max_pages = max_pages or settings.MAX_PAGES
        self.user_agent = user_agent or settings.USER_AGENT
        self.crawler = None

    async def _get_crawler_config(self, page_number: int = 1) -> CrawlerRunConfig:
        """Get crawler configuration for a page."""
        return CrawlerRunConfig(
            delay_before_return_html=self.delay,
            user_agent=self.user_agent,
            verbose=False,
        )

    async def crawl(self, url: str) -> Dict[str, Any]:
        """Crawl a URL and return HTML content with metadata.

        Args:
            url: The URL to crawl.

        Returns:
            Dictionary with 'html', 'url', 'metadata', and 'success' keys.
        """
        async with AsyncWebCrawler(verbose=False) as crawler:
            config = await self._get_crawler_config()
            result = await crawler.arun(url, config=config)

            if not result.success:
                return {
                    "html": None,
                    "url": url,
                    "metadata": {},
                    "success": False,
                    "error": result.error_message if hasattr(result, "error_message") else "Unknown error",
                }

            return {
                "html": result.html,
                "url": result.url,
                "metadata": {
                    "title": result.metadata.get("title") if result.metadata else None,
                    "description": result.metadata.get("description") if result.metadata else None,
                },
                "success": True,
                "error": None,
            }

    async def crawl_with_pagination(
        self,
        url: str,
        next_selector: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Crawl multiple pages using pagination.

        Args:
            url: The starting URL to crawl.
            next_selector: CSS selector for the 'next page' button.

        Returns:
            List of crawl results, one per page.
        """
        results = []
        current_url = url
        pages_crawled = 0

        while pages_crawled < self.max_pages:
            result = await self.crawl(current_url)
            results.append(result)

            if not result["success"]:
                break

            pages_crawled += 1

            # Try to find next page URL
            if not next_selector:
                break

            # Simple pagination: try to find next page link
            # In production, this would use BeautifulSoup to extract the next URL
            if pages_crawled < self.max_pages:
                next_url = self._find_next_url(result["html"], current_url, next_selector)
                if not next_url:
                    break
                current_url = next_url

            await asyncio.sleep(self.delay)

        return results

    def _find_next_url(
        self,
        html: str,
        current_url: str,
        selector: str,
    ) -> Optional[str]:
        """Find the next page URL from HTML.

        Args:
            html: HTML content of the current page.
            current_url: Current page URL.
            selector: CSS selector for the next page link.

        Returns:
            URL of the next page, or None if not found.
        """
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            next_link = soup.select_one(selector)
            if next_link and next_link.get("href"):
                return urljoin(current_url, next_link["href"])
        except Exception:
            pass
        return None
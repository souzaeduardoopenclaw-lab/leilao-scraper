"""Cloudflare bypass crawler using Playwright Stealth."""
import asyncio
from typing import Dict, Any, Optional

from playwright.async_api import async_playwright

from config import settings


class CloudflareBypassCrawler:
    """Crawler with JS challenge solving for Cloudflare-protected sites."""

    def __init__(
        self,
        max_pages: int = 1,
        delay: float = 2.0,
        timeout: int = 30000,
    ):
        self.max_pages = max_pages
        self.delay = delay
        self.timeout = timeout

    async def crawl(self, url: str) -> Dict[str, Any]:
        """Crawl URL with Cloudflare bypass.

        Returns:
            Dict with 'html', 'url', 'metadata', 'success', 'error'.
        """
        try:
            async with async_playwright() as p:
                # Use stealth browser with anti-bot evasions
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-accelerated-2d-canvas",
                        "--no-first-run",
                        "--no-zygote",
                        "--disable-gpu",
                        "--window-size=1920,1080",
                        "--disable-web-security",
                    ],
                )

                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/125.0.0.0 Safari/537.36"
                    ),
                    # Block detection headers
                    extra_http_headers={
                        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    },
                )

                page = await context.new_page()

                # Set short navigation timeout
                page.set_default_timeout(self.timeout)

                # Wait for Cloudflare challenge
                await page.goto(url, wait_until="domcontentloaded")

                # Wait for Cloudflare to resolve
                try:
                    # Check for Cloudflare challenge page
                    await page.wait_for_function(
                        """() => {
                            const title = document.title || '';
                            const body = document.body?.innerText || '';
                            return !title.includes('Attention Required') &&
                                   !title.includes('Cloudflare') &&
                                   !body.includes('Checking your browser') &&
                                   !body.includes('DDoS protection');
                        }""",
                        timeout=15000,
                    )
                except Exception:
                    pass  # May not have challenge, continue anyway

                # Small delay for JS to settle
                await asyncio.sleep(2)

                # Check page is actually valid
                title = await page.title()
                body_text = await page.inner_text("body")
                body_len = len(body_text) if body_text else 0

                if body_len < 100:
                    return {
                        "html": None,
                        "url": url,
                        "metadata": {"title": title},
                        "success": False,
                        "error": "Page content too short - likely blocked",
                    }

                # Get full HTML
                html = await page.content()

                await browser.close()

                return {
                    "html": html,
                    "url": url,
                    "metadata": {"title": title},
                    "success": True,
                    "error": None,
                }

        except Exception as e:
            return {
                "html": None,
                "url": url,
                "metadata": {},
                "success": False,
                "error": str(e),
            }

    async def crawl_with_pagination(
        self,
        url: str,
        next_selector: Optional[str] = None,
    ) -> list[Dict[str, Any]]:
        """Crawl with pagination support."""
        results = []
        current_url = url
        pages_crawled = 0

        while pages_crawled < self.max_pages:
            result = await self.crawl(current_url)
            results.append(result)

            if not result["success"]:
                break

            pages_crawled += 1

            if not next_selector or pages_crawled >= self.max_pages:
                break

            # Try to find next page link
            try:
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()
                    await page.set_default_timeout(10000)
                    await page.goto(current_url, wait_until="domcontentloaded")
                    await asyncio.sleep(1.5)

                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(result["html"], "html.parser")
                    next_link = soup.select_one(next_selector)
                    if next_link and next_link.get("href"):
                        from urllib.parse import urljoin
                        current_url = urljoin(current_url, next_link["href"])
                    else:
                        break

                    await browser.close()
            except Exception:
                break

            await asyncio.sleep(self.delay)

        return results
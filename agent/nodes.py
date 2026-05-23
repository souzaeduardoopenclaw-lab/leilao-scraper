"""LangGraph nodes for the Leilao scraper agent."""

import asyncio
from typing import Dict, Any
from urllib.parse import urlparse

from agent.state import LeilaoState
from crawlers.base import BaseCrawler
from parsers.llm_parser import LLMParser
from parsers.fallback import FallbackParser
from renderers.markdown import render_auctions_to_markdown, get_output_filename
from config import settings
import os


def start_node(state: LeilaoState) -> Dict[str, Any]:
    """Validate URL and detect site type."""
    url = state.get("url", "")

    if not url:
        return {"url": url, "status": "error", "error": "No URL provided"}

    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL: {url}")

        metadata = state.get("metadata", {})
        metadata["site_type"] = _detect_site_type(url)
        metadata["domain"] = parsed.netloc.replace("www.", "")

        return {"url": url, "status": "crawling", "metadata": metadata, "error": None}
    except Exception as e:
        return {"url": url, "status": "error", "error": f"URL validation failed: {str(e)}"}


async def _crawl_impl(state: LeilaoState) -> Dict[str, Any]:
    """Async crawl implementation with Cloudflare fallback."""
    url = state["url"]
    max_pages = state.get("metadata", {}).get("max_pages", settings.MAX_PAGES)

    try:
        from crawlers.base import BaseCrawler
        from crawlers.cloudflare import CloudflareBypassCrawler

        next_selector = state.get("metadata", {}).get("next_selector")

        # Try standard crawler first
        standard_crawler = BaseCrawler(max_pages=max_pages)

        if next_selector:
            results = await standard_crawler.crawl_with_pagination(url, next_selector)
        else:
            results = [await standard_crawler.crawl(url)]

        # Check if we got actual content
        html_content = ""
        success = False
        for result in results:
            if result.get("success") and result.get("html") and len(result.get("html", "")) > 500:
                html_content += result["html"] + "\n\n"
                success = True

        # Fall back to Cloudflare bypass if standard failed
        if not success:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")

            print(f"[CRAWL] Standard crawler failed for {domain}, trying Cloudflare bypass...")

            cf_crawler = CloudflareBypassCrawler(max_pages=max_pages, timeout=30000)
            cf_result = await cf_crawler.crawl(url)

            if cf_result.get("success") and cf_result.get("html"):
                html_content = cf_result["html"]
                success = True
            else:
                return {
                    "url": url,
                    "status": "error",
                    "error": cf_result.get("error", "Crawl failed with Cloudflare bypass too"),
                }

        metadata = state.get("metadata", {})
        metadata["crawled_pages"] = len(results)
        metadata["cloudflare_bypass"] = not results[0].get("success") if results else True

        return {"url": url, "status": "parsing", "metadata": metadata, "error": None, "_html": html_content}
    except Exception as e:
        return {"url": url, "status": "error", "error": f"Crawl failed: {str(e)}"}


def crawl_node(state: LeilaoState) -> Dict[str, Any]:
    """Crawl the URL using Crawl4AI (sync wrapper for async implementation)."""
    return asyncio.run(_crawl_impl(state))


def parse_node(state: LeilaoState) -> Dict[str, Any]:
    """Parse HTML to extract auction records."""
    html = state.get("_html", "")
    url = state.get("url", "")

    if not html:
        return {"url": url, "status": "error", "error": "No HTML content to parse", "auctions": []}

    try:
        llm_parser = LLMParser()
        auctions = llm_parser.parse(html, url)

        if not auctions:
            fallback = FallbackParser()
            auctions = fallback.parse(html, url)

        if not auctions:
            return {"url": url, "status": "error", "error": "No auctions found on the page", "auctions": []}

        return {"url": url, "status": "done", "auctions": auctions, "error": None, "_html": None}
    except Exception as e:
        try:
            fallback = FallbackParser()
            auctions = fallback.parse(html, url)
            if auctions:
                return {"url": url, "status": "done", "auctions": auctions, "error": None, "_html": None}
        except Exception:
            pass
        return {"url": url, "status": "error", "error": f"Parse failed: {str(e)}", "auctions": []}


def aggregate_node(state: LeilaoState) -> Dict[str, Any]:
    """Deduplicate and consolidate auction results."""
    url = state.get("url", "")
    auctions = state.get("auctions", [])

    if not auctions:
        return {"url": url, "status": "done", "auctions": [], "error": None}

    seen_urls = set()
    unique_auctions = []

    for auction in auctions:
        if auction.url and auction.url not in seen_urls:
            seen_urls.add(auction.url)
            unique_auctions.append(auction)

    metadata = state.get("metadata", {})
    metadata["total_found"] = len(auctions)
    metadata["total_unique"] = len(unique_auctions)

    return {"url": url, "auctions": unique_auctions, "metadata": metadata, "error": None}


def render_node(state: LeilaoState) -> Dict[str, Any]:
    """Convert auction list to Markdown."""
    url = state.get("url", "")
    auctions = state.get("auctions", [])
    metadata = state.get("metadata", {})

    if not auctions:
        return {"url": url, "status": "error", "error": "No auctions to render"}

    try:
        source_name = metadata.get("domain", "")
        markdown = render_auctions_to_markdown(auctions=auctions, url=url, source_name=source_name)
        return {"url": url, "status": "done", "markdown": markdown, "error": None}
    except Exception as e:
        return {"url": url, "status": "error", "error": f"Render failed: {str(e)}"}


def save_node(state: LeilaoState) -> Dict[str, Any]:
    """Save markdown to file."""
    url = state.get("url", "")
    markdown = state.get("markdown", "")

    if not markdown:
        return {"url": url, "status": "error", "error": "No markdown content to save"}

    try:
        output_dir = settings.OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)

        filename = get_output_filename(url)
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown)

        metadata = state.get("metadata", {})
        metadata["output_file"] = filepath
        metadata["output_filename"] = filename

        return {"url": url, "status": "done", "metadata": metadata, "error": None}
    except Exception as e:
        return {"url": url, "status": "error", "error": f"Save failed: {str(e)}"}


def error_node(state: LeilaoState) -> Dict[str, Any]:
    """Handle errors with optional retry."""
    url = state.get("url", "")
    error = state.get("error", "Unknown error")
    metadata = state.get("metadata", {})
    retry_count = metadata.get("retry_count", 0)

    print(f"Error encountered: {error}")

    if retry_count < 1:
        metadata["retry_count"] = retry_count + 1
        return {"url": url, "status": "crawling", "error": None, "metadata": metadata}

    return {"url": url, "status": "error", "error": f"Max retries exceeded. Last error: {error}"}


def _detect_site_type(url: str) -> str:
    """Detect site type based on URL patterns."""
    url_lower = url.lower()
    if "leilao" in url_lower or "leiloes" in url_lower:
        return "auction_list"
    elif "/detalhe" in url_lower or "/item" in url_lower:
        return "auction_detail"
    return "unknown"
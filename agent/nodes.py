"""LangGraph nodes for the Leilao scraper agent."""

import re
from typing import Dict, Any
from urllib.parse import urlparse

from agent.state import LeilaoState
from agent.models import Auction
from crawlers.base import BaseCrawler
from parsers.llm_parser import LLMParser
from parsers.fallback import FallbackParser
from renderers.markdown import render_auctions_to_markdown, get_output_filename
from config import settings
import os


def start_node(state: LeilaoState) -> Dict[str, Any]:
    """Validate URL and detect site type.

    Args:
        state: Current state dictionary.

    Returns:
        Updated state dictionary.
    """
    url = state.get("url", "")

    # Validate URL
    if not url:
        return {
            "status": "error",
            "error": "No URL provided",
        }

    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL: {url}")

        # Detect site type based on URL patterns
        metadata = state.get("metadata", {})
        metadata["site_type"] = _detect_site_type(url)
        metadata["domain"] = parsed.netloc.replace("www.", "")

        return {
            "status": "crawling",
            "metadata": metadata,
            "error": None,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"URL validation failed: {str(e)}",
        }


def crawl_node(state: LeilaoState) -> Dict[str, Any]:
    """Crawl the URL using Crawl4AI.

    Args:
        state: Current state dictionary.

    Returns:
        Updated state dictionary.
    """
    url = state["url"]
    max_pages = state.get("metadata", {}).get("max_pages", settings.MAX_PAGES)

    try:
        crawler = BaseCrawler(max_pages=max_pages)

        # Determine if pagination is needed
        next_selector = state.get("metadata", {}).get("next_selector")

        if next_selector:
            results = crawler.crawl_with_pagination(url, next_selector)
            # Combine HTML from all pages
            html_content = ""
            for result in results:
                if result["success"] and result["html"]:
                    html_content += result["html"] + "\n\n"
        else:
            result = crawler.crawl(url)
            if not result["success"]:
                return {
                    "status": "error",
                    "error": result.get("error", "Crawl failed"),
                }
            html_content = result["html"]

        metadata = state.get("metadata", {})
        metadata["crawled_pages"] = 1
        metadata["page_title"] = result.get("metadata", {}).get("title")

        return {
            "status": "parsing",
            "metadata": metadata,
            "error": None,
            # Store HTML in metadata temporarily
            "_html": html_content,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Crawl failed: {str(e)}",
        }


def parse_node(state: LeilaoState) -> Dict[str, Any]:
    """Parse HTML to extract auction records.

    Args:
        state: Current state dictionary.

    Returns:
        Updated state dictionary.
    """
    html = state.get("_html", "")

    if not html:
        return {
            "status": "error",
            "error": "No HTML content to parse",
        }

    url = state["url"]

    try:
        # First try LLM-based parsing
        llm_parser = LLMParser()
        auctions = llm_parser.parse(html, url)

        # If LLM parsing fails or returns empty, use fallback
        if not auctions:
            fallback = FallbackParser()
            auctions = fallback.parse(html, url)

        if not auctions:
            return {
                "status": "error",
                "error": "No auctions found on the page",
                "auctions": [],
            }

        return {
            "status": "done",
            "auctions": auctions,
            "error": None,
            # Clean up temp HTML
            "_html": None,
        }
    except Exception as e:
        # Try fallback on error
        try:
            fallback = FallbackParser()
            auctions = fallback.parse(html, url)

            if auctions:
                return {
                    "status": "done",
                    "auctions": auctions,
                    "error": None,
                    "_html": None,
                }
        except Exception:
            pass

        return {
            "status": "error",
            "error": f"Parse failed: {str(e)}",
            "auctions": [],
        }


def aggregate_node(state: LeilaoState) -> Dict[str, Any]:
    """Deduplicate and consolidate auction results.

    Args:
        state: Current state dictionary.

    Returns:
        Updated state dictionary.
    """
    auctions = state.get("auctions", [])

    if not auctions:
        return {
            "status": "done",
            "auctions": [],
            "error": None,
        }

    # Deduplicate by URL
    seen_urls = set()
    unique_auctions = []

    for auction in auctions:
        if auction.url and auction.url not in seen_urls:
            seen_urls.add(auction.url)
            unique_auctions.append(auction)

    # Update metadata with counts
    metadata = state.get("metadata", {})
    metadata["total_found"] = len(auctions)
    metadata["total_unique"] = len(unique_auctions)

    return {
        "auctions": unique_auctions,
        "metadata": metadata,
        "error": None,
    }


def render_node(state: LeilaoState) -> Dict[str, Any]:
    """Convert auction list to Markdown.

    Args:
        state: Current state dictionary.

    Returns:
        Updated state dictionary.
    """
    auctions = state.get("auctions", [])
    url = state["url"]
    metadata = state.get("metadata", {})

    if not auctions:
        return {
            "status": "error",
            "error": "No auctions to render",
        }

    try:
        source_name = metadata.get("domain", None)
        markdown = render_auctions_to_markdown(
            auctions=auctions,
            url=url,
            source_name=source_name,
        )

        return {
            "status": "done",
            "markdown": markdown,
            "error": None,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Render failed: {str(e)}",
        }


def save_node(state: LeilaoState) -> Dict[str, Any]:
    """Save markdown to file.

    Args:
        state: Current state dictionary.

    Returns:
        Updated state dictionary.
    """
    markdown = state.get("markdown", "")
    url = state["url"]

    if not markdown:
        return {
            "status": "error",
            "error": "No markdown content to save",
        }

    try:
        # Ensure output directory exists
        output_dir = settings.OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)

        # Generate filename
        filename = get_output_filename(url)
        filepath = os.path.join(output_dir, filename)

        # Save file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown)

        metadata = state.get("metadata", {})
        metadata["output_file"] = filepath
        metadata["output_filename"] = filename

        return {
            "status": "done",
            "metadata": metadata,
            "error": None,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Save failed: {str(e)}",
        }


def error_node(state: LeilaoState) -> Dict[str, Any]:
    """Handle errors with optional retry.

    Args:
        state: Current state dictionary.

    Returns:
        Updated state dictionary with retry logic.
    """
    error = state.get("error", "Unknown error")
    metadata = state.get("metadata", {})
    retry_count = metadata.get("retry_count", 0)

    print(f"Error encountered: {error}")

    # Only retry once
    if retry_count < 1:
        metadata["retry_count"] = retry_count + 1
        return {
            "status": "crawling",
            "error": None,  # Clear error for retry
            "metadata": metadata,
        }

    # Max retries exceeded
    return {
        "status": "error",
        "error": f"Max retries exceeded. Last error: {error}",
    }


def _detect_site_type(url: str) -> str:
    """Detect site type based on URL patterns.

    Args:
        url: URL to analyze.

    Returns:
        Site type string.
    """
    url_lower = url.lower()

    if "leilao" in url_lower or "leiloes" in url_lower:
        return "auction_list"
    elif "/detalhe" in url_lower or "/item" in url_lower:
        return "auction_detail"

    return "unknown"
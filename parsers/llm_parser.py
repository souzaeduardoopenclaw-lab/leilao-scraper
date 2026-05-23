"""LLM-based parser using LangChain for structured extraction."""

import os
from typing import List, Optional
from urllib.parse import urlparse

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from config import settings
from agent.models import Auction


class AuctionListOutput(BaseModel):
    """LLM output schema for a list of auctions."""

    auctions: List[Auction] = Field(description="List of extracted auctions")


class LLMParser:
    """LLM-based auction parser using LangChain."""

    def __init__(self, provider: str = None, api_key: str = None):
        """Initialize the LLM parser.

        Args:
            provider: LLM provider ('openai', 'gemini', or 'opencode').
            api_key: API key for the LLM provider.
        """
        self.provider = provider or settings.LLM_PROVIDER
        self.api_key = api_key or self._get_api_key()
        self.llm = self._initialize_llm()

    def _get_api_key(self) -> str:
        """Get API key based on provider."""
        if self.provider == "openai":
            return os.environ.get("OPENAI_API_KEY", "")
        elif self.provider == "gemini":
            return os.environ.get("GEMINI_API_KEY", "")
        elif self.provider == "opencode":
            return os.environ.get("OPENAI_API_KEY", "")  # Uses same key
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def _initialize_llm(self):
        """Initialize the LLM based on provider."""
        if self.provider == "openai":
            return ChatOpenAI(
                model="gpt-4o-mini",
                api_key=self.api_key,
                temperature=0,
            )
        elif self.provider == "gemini":
            return ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                api_key=self.api_key,
                temperature=0,
            )
        elif self.provider == "opencode":
            # OpenCode uses OpenAI-compatible API
            return ChatOpenAI(
                model="opencode",
                api_key=self.api_key,
                openai_api_base="https://api.opencode.ai/v1",
                temperature=0,
            )
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def parse(self, html: str, url: str) -> List[Auction]:
        """Parse HTML content to extract auctions using LLM.

        Args:
            html: Raw HTML content.
            url: Source URL for context.

        Returns:
            List of Auction objects.
        """
        parser = JsonOutputParser(pydantic_object=AuctionListOutput)

        prompt = PromptTemplate(
            template="""You are an expert web scraper specializing in Brazilian auction websites (leilões).

Given the HTML content below, extract all auction items and return them as a JSON array.

For each auction, extract:
- title: The auction item title
- date: Auction date if visible (format: DD/MM/YYYY or similar)
- location: Location of the auction item
- description: Description of the item
- url: Full URL to the auction detail page
- price: Starting price or auction price if visible
- images: List of image URLs if found
- raw_data: Any additional raw data extracted

Be thorough and extract ALL auctions visible on this page.

Source URL: {url}

{format_instructions}

HTML Content:
{html}
""",
            input_variables=["html", "url"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )

        chain = prompt | self.llm | parser

        try:
            result = chain.invoke({"html": html[:15000], "url": url})
            return result.get("auctions", [])
        except Exception as e:
            # Return empty list on failure - fallback parser will handle
            print(f"LLM parsing error: {e}")
            return []

    def is_detail_page(self, html: str, url: str) -> bool:
        """Determine if the page is a detail page (single auction) or list page.

        Args:
            html: HTML content.
            url: Source URL.

        Returns:
            True if this is a detail page, False otherwise.
        """
        # Simple heuristic: detail pages typically have auction-specific details
        # This could be enhanced with LLM-based detection
        detail_indicators = ["data-leilao", "leilao-detalhe", "/leilao/", "/detalhe"]
        url_path = urlparse(url).path.lower()

        for indicator in detail_indicators:
            if indicator in url_path:
                return True

        return False

"""LangGraph State definition for Leilao Scraper."""

from typing import TypedDict, List, Optional, Literal

from .models import Auction


class LeilaoState(TypedDict, total=False):
    """State graph for the Leilao scraper agent."""

    url: str
    auctions: List[Auction]
    markdown: str
    status: Literal["idle", "crawling", "parsing", "done", "error"]
    error: Optional[str]
    metadata: dict
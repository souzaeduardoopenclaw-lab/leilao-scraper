"""Pydantic models for Leilao data."""

from typing import List, Optional
from pydantic import BaseModel, Field


class Auction(BaseModel):
    """Represents a single auction item."""

    title: str = Field(description="Title of the auction item")
    date: Optional[str] = Field(default=None, description="Auction date")
    location: Optional[str] = Field(default=None, description="Auction location")
    description: str = Field(default="", description="Description of the auction item")
    url: str = Field(description="URL to the auction detail page")
    price: Optional[str] = Field(default=None, description="Auction price or starting bid")
    images: List[str] = Field(default_factory=list, description="List of image URLs")
    raw_data: dict = Field(default_factory=dict, description="Raw extracted data")

    model_config = {
        "extra": "allow",
    }
"""Fallback parser using BeautifulSoup and regex for structured extraction."""

import re
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from agent.models import Auction


class FallbackParser:
    """Regex + BeautifulSoup fallback parser for auction extraction."""

    # Common patterns for Brazilian auction sites
    DATE_PATTERNS = [
        r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        r"(\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})",
        r"(\d{1,2}\s+ de \w+\s+ de \d{4})",
    ]

    PRICE_PATTERNS = [
        r"[R\$\s]*\d{1,3}(\.\d{3})*,\d{2}",
        r"U\$\s*\d+[\.,]\d{2}",
    ]

    def __init__(self):
        """Initialize the fallback parser."""
        self.date_re = [re.compile(p) for p in self.DATE_PATTERNS]
        self.price_re = [re.compile(p) for p in self.PRICE_PATTERNS]

    def parse(self, html: str, url: str) -> List[Auction]:
        """Parse HTML content to extract auctions using regex and BeautifulSoup.

        Args:
            html: Raw HTML content.
            url: Source URL for context.

        Returns:
            List of Auction objects.
        """
        soup = BeautifulSoup(html, "html.parser")
        auctions = []

        # Try to find auction containers using common selectors
        containers = self._find_auction_containers(soup)

        for container in containers:
            auction = self._extract_auction(container, url)
            if auction:
                auctions.append(auction)

        return auctions

    def _find_auction_containers(self, soup: BeautifulSoup) -> List[BeautifulSoup]:
        """Find auction container elements."""
        containers = []

        # Common selectors for auction items
        selectors = [
            "article.leilao",
            "div.leilao-item",
            "div.auction-item",
            "div[class*='leilao']",
            "div[class*='auction']",
            "li.leilao",
            "article[class*='item']",
            "div.card-leilao",
        ]

        for selector in selectors:
            found = soup.select(selector)
            if found:
                containers.extend(found)

        # If no specific selectors found, try to find links to auction pages
        if not containers:
            links = soup.find_all("a", href=re.compile(r"leilao|auction|item"))
            for link in links:
                parent = link.find_parent(["div", "article", "li"])
                if parent:
                    containers.append(parent)

        return containers

    def _extract_auction(self, container: BeautifulSoup, base_url: str) -> Optional[Auction]:
        """Extract auction data from a container element."""
        try:
            # Extract title
            title = self._extract_title(container)

            # Extract URL
            url = self._extract_url(container, base_url)

            # Extract date
            date = self._extract_date(container)

            # Extract location
            location = self._extract_location(container)

            # Extract price
            price = self._extract_price(container)

            # Extract description
            description = self._extract_description(container)

            # Extract images
            images = self._extract_images(container, base_url)

            if title and url:
                return Auction(
                    title=title,
                    date=date,
                    location=location,
                    description=description,
                    url=url,
                    price=price,
                    images=images,
                    raw_data={},
                )
        except Exception as e:
            print(f"Error extracting auction: {e}")

        return None

    def _extract_title(self, container: BeautifulSoup) -> Optional[str]:
        """Extract auction title."""
        # Try common title selectors
        selectors = ["h2", "h3", "h4", ".title", ".titulo", "[class*='title']"]
        for selector in selectors:
            title_elem = container.select_one(selector)
            if title_elem:
                return title_elem.get_text(strip=True)

        # Fallback: find any link that might be the title
        link = container.find("a")
        if link:
            return link.get_text(strip=True)

        return None

    def _extract_url(self, container: BeautifulSoup, base_url: str) -> Optional[str]:
        """Extract auction detail URL."""
        link = container.find("a", href=True)
        if link:
            return urljoin(base_url, link["href"])

        # Try to find URL in data attributes
        for attr in ["data-url", "data-href", "data-link"]:
            value = container.get(attr)
            if value:
                return urljoin(base_url, value)

        return None

    def _extract_date(self, container: BeautifulSoup) -> Optional[str]:
        """Extract auction date."""
        text = container.get_text()

        for date_re in self.date_re:
            match = date_re.search(text)
            if match:
                return match.group(1)

        # Try date-specific selectors
        date_selectors = ["[class*='date']", "[class*='data']", ".data-leilao"]
        for selector in date_selectors:
            date_elem = container.select_one(selector)
            if date_elem:
                return date_elem.get_text(strip=True)

        return None

    def _extract_location(self, container: BeautifulSoup) -> Optional[str]:
        """Extract auction location."""
        location_selectors = [
            "[class*='location']",
            "[class*='local']",
            "[class*='endereco']",
            ".cidade",
        ]

        for selector in location_selectors:
            loc_elem = container.select_one(selector)
            if loc_elem:
                return loc_elem.get_text(strip=True)

        return None

    def _extract_price(self, container: BeautifulSoup) -> Optional[str]:
        """Extract auction price."""
        text = container.get_text()

        for price_re in self.price_re:
            match = price_re.search(text)
            if match:
                return match.group(0)

        # Try price-specific selectors
        price_selectors = ["[class*='price']", "[class*='valor']", "[class*='preco']"]
        for selector in price_selectors:
            price_elem = container.select_one(selector)
            if price_elem:
                return price_elem.get_text(strip=True)

        return None

    def _extract_description(self, container: BeautifulSoup) -> Optional[str]:
        """Extract auction description."""
        desc_selectors = ["p", ".description", ".descricao", "[class*='desc']"]

        for selector in desc_selectors:
            desc_elem = container.select_one(selector)
            if desc_elem:
                text = desc_elem.get_text(strip=True)
                if text and len(text) > 10:
                    return text

        return None

    def _extract_images(self, container: BeautifulSoup, base_url: str) -> List[str]:
        """Extract image URLs."""
        images = []
        img_tags = container.find_all("img", src=True)

        for img in img_tags:
            src = img["src"]
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                from urllib.parse import urljoin
                src = urljoin(base_url, src)
            images.append(src)

        return images
"""Markdown renderer for auction data."""

from datetime import datetime
from typing import List
from urllib.parse import urlparse

from agent.models import Auction


def render_auctions_to_markdown(
    auctions: List[Auction],
    url: str,
    source_name: str = None,
    output_dir: str = "./output",
) -> str:
    """Render a list of auctions to a markdown file with YAML frontmatter.

    Args:
        auctions: List of Auction objects.
        url: Source URL for metadata.
        source_name: Human-readable source name (extracted from URL if not provided).
        output_dir: Output directory for the file.

    Returns:
        Rendered markdown content.
    """
    # Extract domain for source name
    if not source_name:
        parsed = urlparse(url)
        source_name = parsed.netloc or "Unknown Source"

    # Build frontmatter
    scraped_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    total = len(auctions)

    frontmatter = f"""---
url: {url}
scraped_at: {scraped_at}
total_auctions: {total}
source: {source_name}
---

# Leilões — {source_name}

"""

    # Build auction list
    auction_lines = []

    for idx, auction in enumerate(auctions, 1):
        lines = [f"## {idx}. {auction.title}"]

        if auction.date:
            lines.append(f"- **Data:** {auction.date}")

        if auction.location:
            lines.append(f"- **Local:** {auction.location}")

        if auction.price:
            lines.append(f"- **Valor:** {auction.price}")

        if auction.description:
            lines.append(f"- **Descrição:** {auction.description}")

        if auction.url:
            lines.append(f"- **Link:** {auction.url}")

        if auction.images:
            lines.append(f"- **Imagens:** {len(auction.images)} imagem(ns)")

        lines.append("")  # Empty line between items
        auction_lines.append("\n".join(lines))

    content = frontmatter + "\n\n".join(auction_lines)

    return content


def get_output_filename(url: str) -> str:
    """Generate output filename from URL.

    Args:
        url: Source URL.

    Returns:
        Filename like 'domain-YYYY-MM-DD.md'.
    """
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "").replace(":", "_")

    date_str = datetime.utcnow().strftime("%Y-%m-%d")

    return f"{domain}-{date_str}.md"
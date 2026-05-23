"""CLI for Leilao Scraper Agent."""

import sys
import os
from typing import Optional

import click

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.graph import get_compiled_graph
from agent.state import LeilaoState
from config import settings


@click.command()
@click.argument("url")
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output markdown file path (default: auto-generated in OUTPUT_DIR)",
)
@click.option(
    "--max-pages",
    "-m",
    type=int,
    default=None,
    help="Maximum number of pages to crawl (default: from config or 10)",
)
@click.option(
    "--next-selector",
    "-n",
    type=str,
    default=None,
    help="CSS selector for 'next page' button",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output",
)
def main(
    url: str,
    output: Optional[str],
    max_pages: Optional[int],
    next_selector: Optional[str],
    verbose: bool,
) -> None:
    """Scrape auctions from a website and save to markdown.

    URL: The starting URL to scrape auctions from.
    """
    if verbose:
        click.echo(f"Starting Leilao Scraper...")
        click.echo(f"URL: {url}")
        click.echo(f"Max pages: {max_pages or settings.MAX_PAGES}")

    # Build initial state
    metadata = {
        "max_pages": max_pages or settings.MAX_PAGES,
    }

    if next_selector:
        metadata["next_selector"] = next_selector

    if output:
        metadata["output_file"] = output

    initial_state: LeilaoState = {
        "url": url,
        "auctions": [],
        "markdown": "",
        "status": "idle",
        "error": None,
        "metadata": metadata,
    }

    # Run the graph
    try:
        graph = get_compiled_graph()

        if verbose:
            click.echo("Running graph...")

        final_state = graph.invoke(initial_state)

        status = final_state.get("status")
        error = final_state.get("error")

        if status == "error" or error:
            click.echo(f"Error: {error}", err=True)
            sys.exit(1)

        output_file = final_state.get("metadata", {}).get("output_file", "unknown")
        total = len(final_state.get("auctions", []))

        click.echo(f"Success! Scraped {total} auctions.")
        click.echo(f"Output saved to: {output_file}")

    except Exception as e:
        click.echo(f"Failed: {str(e)}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
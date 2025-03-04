"""Command for grabbing web content in web-grabber."""

import logging
import sys

import typer

from src.web_grabber.cmd.grab.grab_handler import GrabHandler

logger = logging.getLogger(__name__)


def grab_command(
    url: str = typer.Argument(..., help="URL of the website to crawl"),
    output_dir: str = typer.Option(
        "./grabbed_site", help="Directory to save downloaded content"
    ),
    depth: int = typer.Option(
        100,
        help="Maximum crawl depth (default: 100, effectively unlimited for most sites)",
    ),
    httpx: bool = typer.Option(
        True, help="Use plain HTTP requests (no JavaScript rendering)"
    ),
    tor: bool = typer.Option(False, help="Route traffic through Tor network"),
    selenium: bool = typer.Option(
        False, help="Use Selenium for JavaScript rendered content"
    ),
    camoufox: bool = typer.Option(
        False, help="Use camoufox for anti-bot protection (overrides --selenium)"
    ),
    threads: int = typer.Option(5, help="Number of concurrent threads for crawling"),
    delay: float = typer.Option(0.5, help="Delay between requests (in seconds)"),
    timeout: int = typer.Option(30, help="Request timeout (in seconds)"),
    user_agent: str = typer.Option(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
        help="User agent string",
    ),
    verbose: bool = typer.Option(False, help="Enable verbose logging"),
    retry_failed: bool = typer.Option(False, help="Retry previously failed URLs"),
):
    """
    Grab (download) a website including HTML, images, videos, and documents.

    Example:
        web-grabber grab https://example.com --output-dir ./example_site --depth 5
    """
    # Configure logging based on verbosity
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Validate URL
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
        logger.info(f"URL modified to include scheme: {url}")

    # Override httpx if browser automation is requested
    if selenium or camoufox:
        if httpx:
            logger.info("Disabling httpx as browser automation was requested")
            httpx = False

    # Override selenium if camoufox is specified
    if camoufox and selenium:
        logger.info("Overriding selenium with camoufox as both were specified")
        selenium = False

    # Create and configure the grab handler
    handler = GrabHandler()
    handler.setup(
        url=url,
        output_dir=output_dir,
        tor=tor,
        httpx=httpx,
        selenium=selenium,
        camoufox=camoufox,
        user_agent=user_agent,
        timeout=timeout,
        delay=delay,
        retry_failed=retry_failed,
    )

    # Start the crawl process
    handler.crawl(
        threads=threads,
        depth=depth,
        delay=delay,
        use_selenium=selenium,
        use_camoufox=camoufox,
        use_httpx=httpx,
    )

    # Get summary and log results
    summary = handler.get_summary()
    logger.info(
        f"Crawl summary: Visited {summary['visited_urls']} pages, "
        f"failed {summary['failed_urls']} requests, "
        f"downloaded resources: {summary['resources']}"
    )

    return summary


if __name__ == "__main__":
    typer.run(grab_command)

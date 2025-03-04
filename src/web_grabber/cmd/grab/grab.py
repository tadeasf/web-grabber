"""Command for grabbing web content in web-grabber."""

import logging
import os
import sys
from urllib.parse import urlparse

import typer
from prompt_toolkit import prompt
from prompt_toolkit.completion import PathCompleter
from prompt_toolkit.styles import Style

from web_grabber.cmd.grab.grab_handler import GrabHandler

logger = logging.getLogger(__name__)


def extract_domain_from_url(url: str) -> str:
    """
    Extract domain name from URL to use as directory name.
    
    Args:
        url: The URL to extract domain from
        
    Returns:
        Domain name suitable for use as directory name
    """
    # Make sure URL has a scheme
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
        
    # Parse URL and extract netloc
    parsed = urlparse(url)
    domain = parsed.netloc
    
    # Remove www. prefix if present
    if domain.startswith("www."):
        domain = domain[4:]
        
    return domain


def get_output_directory(url: str, suggested_dir: str = None) -> str:
    """
    Interactively prompt user for output directory with path completion.
    
    Args:
        url: URL being grabbed
        suggested_dir: Optional suggested directory name
        
    Returns:
        Selected output directory path
    """
    # Extract domain for default directory name
    domain = extract_domain_from_url(url)
    
    # Use current directory as base path
    current_dir = os.getcwd()
    
    # Use domain-based directory if no suggested directory was provided
    if not suggested_dir or suggested_dir == "./grabbed_site":
        suggested_dir = os.path.join(current_dir, domain)
    
    # Set up prompt style
    style = Style.from_dict({
        'prompt': 'bold green',
    })
    
    # Create path completer
    completer = PathCompleter(
        expanduser=True,
        only_directories=True,
    )
    
    # Prompt user for output directory with path completion
    message = [
        ('class:prompt', f'Where should content from {domain} be saved? '),
        ('', f'[{suggested_dir}] '),
    ]
    
    user_input = prompt(
        message,
        completer=completer,
        style=style,
        default=suggested_dir,
        complete_while_typing=True,
    )
    
    # If user didn't provide input, use the suggested directory
    if not user_input.strip():
        user_input = suggested_dir
        
    return user_input


def grab_command(
    url: str = typer.Argument(..., help="URL of the website to crawl"),
    output_dir: str = typer.Option(
        None, help="Directory to save downloaded content (defaults to domain name)"
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
    non_interactive: bool = typer.Option(
        False, help="Run in non-interactive mode (no prompts)"
    ),
):
    """
    Grab (download) a website including HTML, images, videos, and documents.

    Example:
        web-grabber grab https://example.com --depth 5
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

    # Determine output directory
    if non_interactive:
        # In non-interactive mode, use provided output_dir or domain name
        if not output_dir:
            domain = extract_domain_from_url(url)
            output_dir = os.path.join(os.getcwd(), domain)
            logger.info(f"Using auto-generated output directory: {output_dir}")
    else:
        # In interactive mode, prompt for output directory
        output_dir = get_output_directory(url, output_dir)
        logger.info(f"Selected output directory: {output_dir}")

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
        javascript=True,
        scroll=True,
        resources=True,
        links=True,
        max_depth=depth,
        restrict_domain=True,
        debug=verbose,
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

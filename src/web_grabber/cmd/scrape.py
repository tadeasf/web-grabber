"""Command for targeted scraping of specific elements from websites."""

import json
import logging
from pathlib import Path

import requests
import typer
from bs4 import BeautifulSoup

from web_grabber.lib.camoufox_handler import get_camoufox_session
from web_grabber.lib.selenium_handler import (
    close_selenium_session,
    get_page_content,
    get_selenium_session,
)
from web_grabber.lib.tor_handler import configure_tor

logger = logging.getLogger(__name__)


def scrape_command(
    url: str = typer.Argument(..., help="URL of the website to scrape"),
    selector: str = typer.Option("", help="CSS selector to extract specific elements"),
    output_file: str = typer.Option(
        "scraped_data.json", help="Output file for scraped data"
    ),
    format: str = typer.Option("json", help="Output format (json, csv, txt)"),
    tor: bool = typer.Option(False, help="Route traffic through Tor network"),
    selenium: bool = typer.Option(
        False, help="Use Selenium for JavaScript rendered content"
    ),
    camoufox: bool = typer.Option(
        False, help="Use camoufox for anti-bot protection (overrides --selenium)"
    ),
    user_agent: str = typer.Option(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        help="User agent string",
    ),
    verbose: bool = typer.Option(False, help="Enable verbose logging"),
):
    """
    Scrape specific elements from a website using CSS selectors.

    Example:
        web-grabber scrape https://example.com --selector "div.product" --output-file products.json
    """
    # Configure logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger.info(f"Starting web scraper for {url}")
    logger.info(f"CSS Selector: {selector or 'None (scraping entire page)'}")
    logger.info(f"Output file: {output_file}")
    logger.info(f"Using Tor: {tor}")

    # Check browser options
    if camoufox:
        logger.info("Using camoufox for anti-bot protection")
        selenium = False  # camoufox overrides selenium
    elif selenium:
        logger.info("Using Selenium for JavaScript rendering")

    # Configure session
    session = requests.Session()
    session.headers.update({"User-Agent": user_agent})

    # Configure Tor if needed
    if tor:
        try:
            session = configure_tor(session)
        except Exception as e:
            logger.error(f"Failed to configure Tor: {e}")
            logger.error("Make sure Tor is running on 127.0.0.1:9050")
            return

    # Get page content
    try:
        if camoufox:
            # Use camoufox for anti-bot protection
            camoufox_browser = get_camoufox_session(headless=True, tor_proxy=tor)
            with camoufox_browser:
                html_content, _ = camoufox_browser.get_page_content(url)
        elif selenium:
            driver = get_selenium_session(headless=True, tor_proxy=tor)
            html_content, _ = get_page_content(driver, url)
            close_selenium_session(driver)
        else:
            response = session.get(url, timeout=30)
            response.raise_for_status()
            html_content = response.text

        # Parse HTML
        soup = BeautifulSoup(html_content, "html.parser")

        # Extract data based on selector
        if selector:
            elements = soup.select(selector)
            logger.info(f"Found {len(elements)} elements matching selector")

            # Extract text and attributes from elements
            scraped_data = []
            for element in elements:
                element_data = {
                    "text": element.get_text(strip=True),
                    "html": str(element),
                    "attrs": element.attrs,
                }
                scraped_data.append(element_data)
        else:
            # If no selector, use the entire page
            scraped_data = {
                "title": soup.title.string if soup.title else "No title",
                "text": soup.get_text(strip=True),
                "links": [
                    {"href": a.get("href"), "text": a.get_text(strip=True)}
                    for a in soup.find_all("a", href=True)
                ],
            }

        # Save the data
        output_path = Path(output_file)

        if format.lower() == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(scraped_data, f, indent=2, ensure_ascii=False)
        elif format.lower() == "csv":
            logger.error("CSV format not implemented yet")
            # Would implement CSV output here
        elif format.lower() == "txt":
            with open(output_path, "w", encoding="utf-8") as f:
                if isinstance(scraped_data, list):
                    for item in scraped_data:
                        f.write(f"{item['text']}\n\n")
                else:
                    f.write(scraped_data["text"])
        else:
            logger.error(f"Unsupported output format: {format}")
            return

        logger.info(f"Scraped data saved to {output_path}")

    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        raise

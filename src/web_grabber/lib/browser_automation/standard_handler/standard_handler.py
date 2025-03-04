import logging
from typing import Dict, List, Set, Tuple

import requests

from web_grabber.lib.browser_automation.base import BrowserAutomation

logger = logging.getLogger(__name__)


class StandardBrowser:
    def __init__(self):
        """Initialize the StandardBrowser instance."""
        self._failed_urls = set()

    def get_page_content(
        self, url: str, *args, **kwargs
    ) -> Tuple[str, Dict[str, List[str]]]:
        """
        Get the content of a page using requests library.

        Args:
            url (str): The URL to fetch
            *args, **kwargs: Additional arguments (for interface compatibility)

        Returns:
            Tuple[str, Dict[str, List[str]]]: HTML content and resources
        """
        resources = {"images": [], "videos": [], "documents": []}

        try:
            # First check if the URL points to a non-HTML resource
            resource_type = BrowserAutomation.get_file_type(url)
            if resource_type != "html" and resource_type != "skip":
                logger.info(f"URL {url} appears to be a {resource_type} file, not HTML")
                self.add_failed_url(url)
                return "", resources

            logger.info(f"Fetching URL with standard handler: {url}")

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()  # Raise exception for 4XX/5XX responses

            # Check content type to ensure we're getting HTML
            content_type = response.headers.get("Content-Type", "").lower()
            if (
                "text/html" not in content_type
                and "application/xhtml+xml" not in content_type
            ):
                logger.warning(f"URL {url} returned non-HTML content: {content_type}")

                # If it's a document or image, don't treat it as a failed URL
                if any(
                    doc_type in content_type
                    for doc_type in [
                        "application/pdf",
                        "image/",
                        "video/",
                        "application/msword",
                    ]
                ):
                    return "", resources

                # Otherwise, mark as failed
                self.add_failed_url(url)
                return "", resources

            # Get content
            html_content = response.text

            # Check if the content is valid HTML
            if not html_content or not self._is_valid_html(html_content):
                logger.warning(f"Content from {url} doesn't appear to be valid HTML")
                self.add_failed_url(url)
                return html_content, resources

            # Extract resources from content
            resources = BrowserAutomation.get_resources(url, html_content)

            return html_content, resources
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for {url}: {e}")
            self.add_failed_url(url)
            return "", resources
        except Exception as e:
            logger.error(f"Error fetching {url} with standard handler: {e}")
            self.add_failed_url(url)
            return "", resources

    def _is_valid_html(self, content: str) -> bool:
        """
        Check if content appears to be valid HTML.

        Args:
            content: String content to check

        Returns:
            bool: True if content appears to be HTML, False otherwise
        """
        if not content:
            return False

        # Check for PDF signature
        if content.startswith("%PDF-"):
            return False

        # Check for common HTML markers
        lower_content = content.lower()
        return (
            "<!doctype html" in lower_content[:1000]
            or "<html" in lower_content[:1000]
            or "<head" in lower_content[:1000]
            or "<body" in lower_content[:1000]
        )

    @property
    def failed_urls(self) -> Set[str]:
        """Get the set of failed URLs."""
        return self._failed_urls

    def add_failed_url(self, url: str) -> None:
        """Add a URL to the set of failed URLs."""
        self._failed_urls.add(url)

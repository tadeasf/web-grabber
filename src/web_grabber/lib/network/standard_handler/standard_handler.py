"""Standard network handler implementation using requests."""

import logging
from typing import Dict, List, Optional, Tuple

import requests

from web_grabber.lib.network.base import NetworkHandler

logger = logging.getLogger(__name__)


class StandardHandler(NetworkHandler):
    """Network handler that uses requests for HTTP requests."""

    def __init__(
        self,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
        timeout: int = 30,
        retries: int = 3,
        backoff_factor: float = 0.5,
        delay_between_requests: float = 0.5,
    ):
        """
        Initialize the StandardHandler.

        Args:
            user_agent: User agent string to use for requests
            timeout: Request timeout in seconds
            retries: Number of retries for failed requests
            backoff_factor: Backoff factor for retries
            delay_between_requests: Minimum delay between requests in seconds
        """
        super().__init__(
            user_agent=user_agent,
            timeout=timeout,
            retries=retries,
            backoff_factor=backoff_factor,
            delay_between_requests=delay_between_requests,
        )

        # Create session using the base NetworkHandler method
        self.session = self._create_session()

        # Configure proxies if needed
        self.configure_proxies()

    def configure_proxies(self) -> None:
        """Configure proxies for the session."""
        # By default, no proxies are used
        # This is implemented in subclasses like TorHandler
        pass

    def get(
        self,
        url: str,
        params: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        stream: bool = False,
    ) -> requests.Response:
        """
        Make a GET request to the specified URL.

        Args:
            url: URL to request
            params: Optional query parameters
            headers: Optional headers
            stream: Whether to stream the response

        Returns:
            requests.Response: The response object
        """
        # Respect rate limits
        self._respect_rate_limits()

        # Apply custom headers if provided
        final_headers = self.session.headers.copy()
        if headers:
            final_headers.update(headers)

        # Make the request with retries
        return self.session.get(
            url,
            params=params,
            headers=final_headers,
            timeout=self.timeout,
            stream=stream,
        )

    def get_file_type(self, url: str) -> str:
        """
        Determine the file type from a URL.

        Args:
            url: URL to analyze

        Returns:
            str: File type category ('html', 'images', 'documents', 'videos', or 'skip')
        """
        from web_grabber.lib.browser_automation.base import BrowserAutomation

        return BrowserAutomation.get_file_type(url)

    def get_page_content(
        self, url: str, wait_for_js: bool = False, scroll: bool = False
    ) -> Tuple[str, Dict[str, List[str]]]:
        """
        Get the page content and related resources from a URL.

        Args:
            url: URL to request
            wait_for_js: Whether to wait for JavaScript to load
            scroll: Whether to scroll the page

        Returns:
            Tuple[str, Dict[str, List[str]]]: The page content and related resources
        """
        try:
            # Make the request
            response = self.get(url)

            # Check if successful
            if response.status_code != 200:
                logger.warning(f"Got status code {response.status_code} for {url}")
                return "", {}

            # Get content
            html_content = response.text

            # Extract resources
            from web_grabber.lib.browser_automation.base import BrowserAutomation

            resources = BrowserAutomation.get_resources(url, html_content)

            return html_content, resources
        except Exception as e:
            logger.error(f"Error getting page content for {url}: {e}")
            return "", {}

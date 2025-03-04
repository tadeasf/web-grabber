"""Standard network handler implementation using requests."""

import logging
from typing import Dict, Optional

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
        Make a GET request using requests.

        Args:
            url: URL to request
            params: Query parameters
            headers: Additional headers
            stream: Whether to stream the response

        Returns:
            requests.Response object
        """
        # Use the base NetworkHandler get method
        return super().get(url, params, headers, stream)

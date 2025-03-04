"""HTTP handler implementation using httpx."""

import logging
import time
from typing import Dict, List, Optional, Tuple

try:
    import httpx
except ImportError:
    raise ImportError(
        "httpx is required for HttpxHandler. Install it with 'pip install httpx'."
    )

from web_grabber.lib.network.base import NetworkHandler

logger = logging.getLogger(__name__)


class HttpxHandler(NetworkHandler):
    """Network handler that uses httpx for HTTP requests."""

    def __init__(
        self,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
        timeout: int = 30,
        retries: int = 3,
        backoff_factor: float = 0.5,
        delay_between_requests: float = 0.5,
    ):
        """
        Initialize the HttpxHandler.

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

        # Httpx client
        self._client = None

        # Initialize httpx client
        self._initialize_client()

        # For compatibility with NetworkHandler
        self.session = self  # We'll mimic some of the requests.Session API

        # Last request time for rate limiting
        self._last_request_time = 0

    def _initialize_client(self) -> None:
        """Initialize the httpx client with appropriate settings."""
        # Create transport with retries
        transport = httpx.HTTPTransport(retries=self.retries)

        # Create limits
        limits = httpx.Limits(
            max_keepalive_connections=5, max_connections=10, keepalive_expiry=30.0
        )

        # Create client with transport and timeout
        self._client = httpx.Client(
            transport=transport,
            timeout=self.timeout,
            limits=limits,
            follow_redirects=True,
            headers={"User-Agent": self.user_agent},
        )

        # Configure proxies
        self.configure_proxies()

    def configure_proxies(self) -> None:
        """Configure any proxies for the httpx client."""
        # By default, no proxies are used
        # Override this in subclasses to add proxy support
        pass

    def get(
        self,
        url: str,
        params: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        stream: bool = False,
    ) -> httpx.Response:
        """
        Make a GET request using httpx.

        Args:
            url: URL to request
            params: Query parameters
            headers: Additional headers
            stream: Whether to stream the response

        Returns:
            httpx.Response object
        """
        # Respect rate limits
        self._respect_rate_limits()

        try:
            # Log the request
            logger.debug(f"GET request to {url}")

            # Make the request
            response = self._client.get(
                url, params=params, headers=headers, follow_redirects=True
            )

            # Raise for status (similar to requests)
            response.raise_for_status()

            # Update last request time
            self._last_request_time = time.time()

            return response
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error for {url}: {e.response.status_code} - {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error for {url}: {e}")
            raise

    def _respect_rate_limits(self) -> None:
        """Ensure we respect the rate limits by waiting if needed."""
        if self._last_request_time > 0:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.delay_between_requests:
                sleep_time = self.delay_between_requests - elapsed
                logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)

    def close(self) -> None:
        """Close the httpx client and release resources."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def download_file(self, url: str, file_path: str, chunk_size: int = 8192) -> bool:
        """
        Download a file from the specified URL.

        Args:
            url: URL of the file to download
            file_path: Path where to save the file
            chunk_size: Size of chunks to use for streaming

        Returns:
            bool: True if download succeeded, False otherwise
        """
        try:
            response = self.get(url, stream=True)
            if response.status_code == 200:
                with open(file_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=chunk_size):
                        f.write(chunk)
                return True
            return False
        except Exception as e:
            logger.error(f"Error downloading file {url}: {e}")
            return False

    def get_page_content(
        self, url: str, wait_for_js: bool = False, scroll: bool = False
    ) -> Tuple[str, Dict[str, List[str]]]:
        """
        Get the content of a page.

        Args:
            url: URL of the page to get
            wait_for_js: Whether to wait for JavaScript (not applicable for this handler)
            scroll: Whether to scroll the page (not applicable for this handler)

        Returns:
            Tuple[str, Dict[str, List[str]]]: HTML content and resources
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

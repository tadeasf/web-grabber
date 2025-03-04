"""Base network handler for web-grabber."""

import logging
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class NetworkHandler:
    """Base class for network request handling with standard implementation."""

    def __init__(
        self,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
        timeout: int = 30,
        retries: int = 3,
        backoff_factor: float = 0.5,
        delay_between_requests: float = 0.5,
    ):
        """
        Initialize network handler with configuration.

        Args:
            user_agent (str): User agent string to use for requests
            timeout (int): Request timeout in seconds
            retries (int): Number of retries for failed requests
            backoff_factor (float): Backoff factor for retry delay
            delay_between_requests (float): Delay between requests in seconds
        """
        self.user_agent = user_agent
        self.timeout = timeout
        self.retries = retries
        self.backoff_factor = backoff_factor
        self.delay_between_requests = delay_between_requests
        self.session = self._create_session()
        self.last_request_time = 0.0
        
        # Configure proxies if needed
        self.configure_proxies()

    def _create_session(self) -> requests.Session:
        """Create and configure a requests session."""
        session = requests.Session()

        # Configure retries with backoff
        retry_strategy = Retry(
            total=self.retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD", "OPTIONS"],
        )

        # Mount the retry adapter to both HTTP and HTTPS
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set default headers
        session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "max-age=0",
            }
        )

        return session

    def get(
        self,
        url: str,
        params: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        stream: bool = False,
    ) -> requests.Response:
        """
        Make a GET request with rate limiting.

        Args:
            url (str): URL to request
            params (Dict[str, str], optional): Query parameters
            headers (Dict[str, str], optional): Additional headers
            stream (bool): Whether to stream the response

        Returns:
            requests.Response: Response object
        """
        # Apply rate limiting
        self._respect_rate_limits()

        # Apply custom headers if provided
        final_headers = self.session.headers.copy()
        if headers:
            final_headers.update(headers)

        # Make request and update last request time
        self.last_request_time = time.time()
        return self.session.get(
            url,
            params=params,
            headers=final_headers,
            timeout=self.timeout,
            stream=stream,
        )

    def _respect_rate_limits(self) -> None:
        """Delay request if necessary to respect rate limits."""
        if self.last_request_time > 0:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.delay_between_requests:
                time.sleep(self.delay_between_requests - elapsed)

    def configure_proxies(self) -> None:
        """Configure proxies for the session. Default implementation uses no proxies."""
        # By default, no proxies are used
        # This is implemented in subclasses like TorHandler
        pass

    def close(self) -> None:
        """Close the session and release resources."""
        if self.session:
            self.session.close()
            self.session = None

    def __enter__(self):
        """Context manager entry point."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point."""
        self.close()

    @staticmethod
    def extract_domain(url: str) -> str:
        """
        Extract domain from URL.

        Args:
            url (str): URL to parse

        Returns:
            str: Domain name
        """
        parsed = urlparse(url)
        return parsed.netloc

    def download_file(self, url: str, file_path: str, chunk_size: int = 8192) -> bool:
        """
        Download a file from URL to specified path.

        Args:
            url (str): URL to download
            file_path (str): Where to save the file
            chunk_size (int): Size of chunks to download

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Make request
            response = self.get(url, stream=True)
            response.raise_for_status()

            # Write file in chunks
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)

            return True
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            return False

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

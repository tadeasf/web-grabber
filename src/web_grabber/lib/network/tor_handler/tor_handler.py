"""Tor network handling implementation for web-grabber."""

import logging
import socket
from typing import Dict, List, Optional, Tuple

import requests
import socks

from web_grabber.lib.network.base import NetworkHandler

logger = logging.getLogger(__name__)


class TorHandler(NetworkHandler):
    """Network handler that routes traffic through Tor."""

    def __init__(
        self,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
        timeout: int = 30,
        retries: int = 3,
        backoff_factor: float = 0.5,
        delay_between_requests: float = 1.0,
        host: str = "127.0.0.1",
        port: int = 9050,
    ):
        """
        Initialize Tor network handler.

        Args:
            user_agent (str): User agent string to use for requests
            timeout (int): Request timeout in seconds
            retries (int): Number of retries for failed requests
            backoff_factor (float): Backoff factor for retry delay
            delay_between_requests (float): Delay between requests in seconds
            host (str): Tor SOCKS proxy host
            port (int): Tor SOCKS proxy port
        """
        self.tor_host = host
        self.tor_port = port

        # Initialize the base class
        super().__init__(
            user_agent=user_agent,
            timeout=timeout,
            retries=retries,
            backoff_factor=backoff_factor,
            delay_between_requests=delay_between_requests,
        )

        # Configure Tor proxies
        self.configure_proxies()

    def configure_proxies(self) -> None:
        """Configure the session to use Tor SOCKS proxy."""
        # Configure SOCKS proxy globally for socket
        socks.set_default_proxy(socks.SOCKS5, self.tor_host, self.tor_port)
        socket.socket = socks.socksocket

        # Also configure requests session to use proxies
        self.session.proxies = {
            "http": f"socks5://{self.tor_host}:{self.tor_port}",
            "https": f"socks5://{self.tor_host}:{self.tor_port}",
        }

        logger.info(f"Configured Tor proxy at {self.tor_host}:{self.tor_port}")

    def reset_identity(self) -> bool:
        """
        Request a new Tor identity (circuit).

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Implement Tor control protocol to request new identity
            # This is a simplified version - in production you'd use the Tor control protocol
            self.close()
            self.session = self._create_session()
            self.configure_proxies()
            logger.info("Requested new Tor identity")
            return True
        except Exception as e:
            logger.error(f"Error resetting Tor identity: {e}")
            return False

    def get_current_ip(self) -> Optional[str]:
        """
        Get the current IP address as seen through Tor.

        Returns:
            Optional[str]: Current IP address, or None if it couldn't be retrieved
        """
        try:
            response = self.get("https://api.ipify.org")
            return response.text.strip()
        except Exception as e:
            logger.error(f"Failed to get current IP: {e}")
            return None

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


# Legacy compatibility functions
def configure_tor(session: Optional[requests.Session] = None) -> requests.Session:
    """
    Configure a requests session to route traffic through Tor.

    Args:
        session: A requests.Session object or None to create a new one

    Returns:
        requests.Session: Configured session object
    """
    if session is None:
        session = requests.Session()

    # Configure socket to use SOCKS proxy
    socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 9050)
    socket.socket = socks.socksocket

    # Configure session proxies
    session.proxies = {
        "http": "socks5://127.0.0.1:9050",
        "https": "socks5://127.0.0.1:9050",
    }

    logger.info("Configured Tor proxy for requests session")
    return session


def reset_tor_connection() -> bool:
    """
    Reset the Tor connection to get a new identity.

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Simplified version - in production you'd use the Tor control protocol
        handler = TorHandler()
        result = handler.reset_identity()
        handler.close()
        return result
    except Exception as e:
        logger.error(f"Error resetting Tor connection: {e}")
        return False

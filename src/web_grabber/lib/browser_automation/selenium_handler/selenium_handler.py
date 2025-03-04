"""Selenium-based browser automation implementation."""

import logging
import time
from typing import Dict, List, Tuple

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

from web_grabber.lib.browser_automation.base import BrowserAutomation

logger = logging.getLogger(__name__)


class SeleniumBrowser(BrowserAutomation):
    """Selenium-based browser automation implementation."""

    def __init__(self, headless: bool = True, tor_proxy: bool = False):
        """
        Initialize the Selenium browser automation.

        Args:
            headless (bool): Whether to run the browser in headless mode
            tor_proxy (bool): Whether to route traffic through Tor
        """
        super().__init__(headless, tor_proxy)
        self.driver = None
        self._initialize_driver()

    def _initialize_driver(self) -> None:
        """Initialize the Selenium WebDriver with configured options."""
        options = Options()

        if self.headless:
            options.add_argument("--headless")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        # Set a standard user agent
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )

        # Disable images to speed up loading
        options.add_argument("--blink-settings=imagesEnabled=false")

        # Configure proxy for Tor if needed
        if self.tor_proxy:
            options.add_argument("--proxy-server=socks5://127.0.0.1:9050")

        try:
            self.driver = webdriver.Chrome(options=options)
            # Set reasonable timeout
            self.driver.set_page_load_timeout(30)
            self.driver.set_script_timeout(30)
            logger.info("Selenium WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Selenium WebDriver: {e}")
            raise

    def __enter__(self):
        """Context manager entry point."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point."""
        self.close()

    def close(self) -> None:
        """Close the WebDriver and release resources."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Selenium WebDriver closed successfully")
            except Exception as e:
                logger.error(f"Error closing Selenium WebDriver: {e}")
            finally:
                self.driver = None

    def get_page_content(
        self, url: str, wait_for_js: bool = True, scroll: bool = True
    ) -> Tuple[str, Dict[str, List[str]]]:
        """
        Get the content of a page, including HTML and resource URLs.

        Args:
            url (str): The URL to fetch
            wait_for_js (bool): Whether to wait for JavaScript to execute
            scroll (bool): Whether to scroll the page to load lazy content

        Returns:
            Tuple[str, Dict[str, List[str]]]: HTML content and resources
        """
        # Dictionary to store resources
        resources = {"images": [], "videos": [], "documents": []}

        try:
            logger.info(f"Fetching URL with Selenium: {url}")

            # First check if the URL points to a non-HTML resource
            resource_type = self.get_file_type(url)
            if resource_type != "html" and resource_type != "skip":
                logger.info(f"URL {url} appears to be a {resource_type} file, not HTML")
                self.add_failed_url(url)
                return "", resources

            # Load the page
            self.driver.get(url)

            # Wait for page to load
            if wait_for_js:
                try:
                    # Wait for the page to be considered loaded
                    WebDriverWait(self.driver, 10).until(
                        lambda d: d.execute_script("return document.readyState")
                        == "complete"
                    )
                except TimeoutException:
                    logger.warning(f"Timeout waiting for page to load: {url}")

            # Scroll if requested
            if scroll:
                self._scroll_page()

            # Get the page source
            html_content = self.driver.page_source

            # Check if the content is valid HTML
            if not html_content or not self._is_valid_html(html_content):
                logger.warning(f"Content from {url} doesn't appear to be valid HTML")
                self.add_failed_url(url)
                return html_content, resources

            # Extract resources
            resources = self.get_resources(url, html_content)

            return html_content, resources
        except WebDriverException as e:
            logger.error(f"WebDriver error for {url}: {e}")
            self.add_failed_url(url)
            return "", resources
        except Exception as e:
            logger.error(f"Error fetching {url} with Selenium: {e}")
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

    def _scroll_page(self) -> None:
        """Scroll the page to load lazy-loaded content."""
        try:
            # Get scroll height
            last_height = self.driver.execute_script(
                "return document.body.scrollHeight"
            )

            # Scroll in increments
            for _ in range(5):  # Scroll 5 times
                # Scroll down
                self.driver.execute_script("window.scrollBy(0, window.innerHeight);")
                time.sleep(0.5)  # Allow time for content to load

                # Calculate new scroll height
                new_height = self.driver.execute_script(
                    "return document.body.scrollHeight"
                )

                # Break if no more scrolling is possible
                if new_height == last_height:
                    break
                last_height = new_height

            # Scroll back to top
            self.driver.execute_script("window.scrollTo(0, 0);")
        except Exception as e:
            logger.warning(f"Error while scrolling page: {e}")

    def take_screenshot(self, url: str, output_path: str) -> None:
        """
        Take a screenshot of a page using Selenium.

        Args:
            url (str): The URL to screenshot
            output_path (str): Where to save the screenshot
        """
        if not self.driver:
            self._initialize_driver()

        try:
            logger.info(f"Taking screenshot of {url}")
            self.driver.get(url)

            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )

            # Take screenshot
            self.driver.save_screenshot(output_path)
            logger.info(f"Screenshot saved to {output_path}")
        except Exception as e:
            logger.error(f"Error taking screenshot of {url}: {e}")
            self.add_failed_url(url)


# Legacy compatibility functions - these use the class above but maintain the old interface
def get_selenium_session(headless=True, tor_proxy=False):
    """
    Create and configure a Selenium WebDriver session.

    Args:
        headless (bool): Whether to run browser in headless mode
        tor_proxy (bool): Whether to route traffic through Tor

    Returns:
        SeleniumBrowser: Configured browser instance
    """
    return SeleniumBrowser(headless=headless, tor_proxy=tor_proxy)


def get_page_content(driver, url, wait_for_js=True, scroll=True):
    """
    Get page content using Selenium.

    This function maintains compatibility with legacy code.

    Args:
        driver: Selenium WebDriver or SeleniumBrowser instance
        url: URL to retrieve
        wait_for_js: Whether to wait for JavaScript
        scroll: Whether to scroll the page

    Returns:
        Tuple[str, Dict[str, List[str]]]: HTML content and resources
    """
    if isinstance(driver, SeleniumBrowser):
        return driver.get_page_content(url, wait_for_js, scroll)
    else:
        # Assume it's a legacy WebDriver instance
        browser = SeleniumBrowser(headless=True)
        browser.driver = driver  # Use the existing driver
        return browser.get_page_content(url, wait_for_js, scroll)


def close_selenium_session(driver):
    """
    Close a Selenium WebDriver session.

    Args:
        driver: Selenium WebDriver instance to close
    """
    if driver:
        try:
            driver.quit()
            logger.info("Selenium WebDriver closed successfully")
        except Exception as e:
            logger.error(f"Error closing Selenium WebDriver: {e}")

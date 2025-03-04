"""Selenium-based browser automation implementation."""

import logging
import time
from typing import Dict, List, Tuple

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
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
        Get the content of a page using Selenium.

        Args:
            url (str): The URL to fetch
            wait_for_js (bool): Whether to wait for JavaScript to execute
            scroll (bool): Whether to scroll the page to load lazy content

        Returns:
            Tuple[str, Dict[str, List[str]]]: HTML content and resources
        """
        if not self.driver:
            self._initialize_driver()

        logger.info(f"Fetching URL with Selenium: {url}")
        resources = {"images": [], "videos": [], "documents": []}

        try:
            self.driver.get(url)

            # Wait for page to load
            if wait_for_js:
                # Wait for document ready state
                WebDriverWait(self.driver, 10).until(
                    lambda d: d.execute_script("return document.readyState")
                    == "complete"
                )

            if scroll:
                # Scroll to load lazy content
                self._scroll_page()

            # Extract resources from page
            html_content = self.driver.page_source
            resources = self.get_resources(url, html_content)

            # Find resources in src attributes
            elements_with_src = self.driver.find_elements(By.CSS_SELECTOR, "[src]")
            for element in elements_with_src:
                src = element.get_attribute("src")
                if src:
                    src = self.normalize_url(url, src)
                    resource_type = self.get_file_type(src)
                    if resource_type in resources:
                        resources[resource_type].append(src)

            # Find resources in href attributes (for documents)
            elements_with_href = self.driver.find_elements(By.CSS_SELECTOR, "a[href]")
            for element in elements_with_href:
                href = element.get_attribute("href")
                if href:
                    href = self.normalize_url(url, href)
                    resource_type = self.get_file_type(href)
                    if resource_type == "documents" and resource_type != "skip":
                        # Check for document patterns
                        if (
                            href.lower().endswith((".pdf", ".doc", ".docx"))
                            or "/resume" in href.lower()
                        ):
                            resources[resource_type].append(href)

            # Deduplicate resources
            for resource_type in resources:
                resources[resource_type] = list(set(resources[resource_type]))

            return html_content, resources

        except TimeoutException as e:
            logger.error(f"Timeout fetching {url}: {e}")
            self.add_failed_url(url)
            return "", resources
        except WebDriverException as e:
            logger.error(f"WebDriver error fetching {url}: {e}")
            self.add_failed_url(url)
            return "", resources
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            self.add_failed_url(url)
            return "", resources

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
        webdriver: Configured WebDriver instance
    """
    browser = SeleniumBrowser(headless=headless, tor_proxy=tor_proxy)
    return browser.driver


def get_page_content(driver, url, wait_for_js=True, scroll=True):
    """
    Get the content of a page using Selenium.

    Args:
        driver: Selenium WebDriver instance
        url (str): URL to fetch
        wait_for_js (bool): Whether to wait for JavaScript to execute
        scroll (bool): Whether to scroll page to load lazy content

    Returns:
        tuple: (HTML content, resources dict)
    """
    # Create a temporary browser instance with the given driver
    browser = SeleniumBrowser()
    browser.driver = driver
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

"""Camoufox-based browser automation implementation with anti-bot protections."""

import asyncio
import importlib.util
import logging
import random
from typing import Any, Dict, List, Set, Tuple

# Import required modules - keep these at the top level
from web_grabber.lib.browser_automation.base import BrowserAutomation
from web_grabber.lib.browser_automation.camoufox_handler.spoofing_config import (
    COMMON_FONTS,
    COMMON_PLUGINS,
    PLATFORMS,
    WEBGL_RENDERERS,
    WEBGL_VENDORS,
    WINDOW_CONFIGS,
)

# Check if camoufox package is available
CAMOUFOX_AVAILABLE = importlib.util.find_spec("camoufox") is not None

# Only import camoufox if it's available
if CAMOUFOX_AVAILABLE:
    try:
        from camoufox import AsyncCamoufox

        CAMOUFOX_AVAILABLE = True
    except ImportError:
        CAMOUFOX_AVAILABLE = False

logger = logging.getLogger(__name__)


class CamoufoxBrowser(BrowserAutomation):
    """Camoufox-based browser automation with anti-fingerprinting capabilities."""

    def __init__(self, headless: bool = True, tor_proxy: bool = False):
        """
        Initialize the Camoufox browser automation.

        Args:
            headless (bool): Whether to run the browser in headless mode
            tor_proxy (bool): Whether to route traffic through Tor
        """
        if not CAMOUFOX_AVAILABLE:
            raise ImportError(
                "Camoufox package is not installed. Install it with 'pip install camoufox'"
            )

        super().__init__(headless, tor_proxy)
        self.browser_mgr = None
        self.browser_ctx = None
        self._loop = asyncio.new_event_loop()
        self._initialize_browser()

    def _initialize_browser(self) -> None:
        """Initialize the Camoufox browser with anti-fingerprinting options."""
        asyncio.set_event_loop(self._loop)

        # Configure spoofing options
        viewport_resolution = random.choice(WINDOW_CONFIGS["common_resolutions"])
        user_agent = random.choice(WINDOW_CONFIGS["desktop_user_agents"])
        platform = random.choice(PLATFORMS)
        vendor = random.choice(WEBGL_VENDORS)
        renderer = random.choice(WEBGL_RENDERERS)

        # Configure browser settings
        browser_args = {
            "headless": self.headless,
            "proxy": "socks5://127.0.0.1:9050" if self.tor_proxy else None,
            "viewport_width": viewport_resolution[0],
            "viewport_height": viewport_resolution[1],
            "user_agent": user_agent,
            "platform": platform,
            "webgl_vendor": vendor,
            "webgl_renderer": renderer,
            "webdriver": False,
            "fonts": COMMON_FONTS,
            "plugins": COMMON_PLUGINS,
        }

        try:
            # Initialize browser asynchronously
            async def setup_browser():
                # Use AsyncCamoufox instead of BrowserManager
                self.browser_mgr = AsyncCamoufox(**browser_args)
                return await self.browser_mgr.__aenter__()

            future = asyncio.run_coroutine_threadsafe(setup_browser(), self._loop)
            self.browser_ctx = future.result(timeout=30)
            logger.info("Camoufox browser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Camoufox browser: {e}")
            self.add_failed_url("initialization")
            raise RuntimeError(f"Failed to initialize Camoufox browser: {e}")

    def __enter__(self):
        """Context manager entry point."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point."""
        self.close()

    def close(self) -> None:
        """Close the browser and clean up resources."""
        if self.browser_mgr:
            try:
                # Close browser asynchronously
                async def cleanup_browser():
                    if self.browser_ctx:
                        try:
                            # Close all pages first
                            pages = self.browser_ctx.pages()
                            if pages:
                                for page in await pages:
                                    try:
                                        await page.close()
                                    except Exception:
                                        pass  # Ignore errors closing individual pages
                        except Exception as e:
                            logger.warning(f"Error closing pages: {e}")

                    # Exit browser manager
                    await self.browser_mgr.__aexit__(None, None, None)

                future = asyncio.run_coroutine_threadsafe(cleanup_browser(), self._loop)
                future.result(timeout=30)
                logger.info("Closed Camoufox browser")
            except Exception as e:
                logger.error(f"Error closing Camoufox browser: {e}")
            finally:
                # Clean up loop
                try:
                    if not self._loop.is_closed():
                        self._loop.stop()
                        self._loop.close()
                except Exception as e:
                    logger.warning(f"Error closing event loop: {e}")

        self.browser_mgr = None
        self.browser_ctx = None

    async def _async_get_page_content(
        self, url: str, wait_for_js: bool = True, scroll: bool = True
    ) -> Tuple[str, Dict[str, List[str]]]:
        """
        Get page content asynchronously using Camoufox.

        Args:
            url (str): URL to fetch
            wait_for_js (bool): Whether to wait for JavaScript to execute
            scroll (bool): Whether to scroll the page

        Returns:
            Tuple[str, Dict[str, List[str]]]: HTML content and resources
        """
        if not self.browser_ctx:
            logger.error("Browser not initialized")
            self.add_failed_url(url)
            return "", {}

        try:
            # Create a new page
            page = await self.browser_ctx.new_page()

            try:
                # Set reasonable timeout
                await page.set_default_timeout(30000)

                # Navigate to URL
                response = await page.goto(
                    url, wait_until="networkidle" if wait_for_js else "domcontentloaded"
                )

                if not response:
                    logger.error(f"Failed to get response for {url}")
                    self.add_failed_url(url)
                    return "", {}

                # Check if the response is OK
                if not response.ok:
                    logger.error(f"HTTP error {response.status} for {url}")
                    self.add_failed_url(url)
                    return "", {}

                # Scroll if requested
                if scroll:
                    await self._async_scroll_page(page)

                # Wait for content to settle
                if wait_for_js:
                    await asyncio.sleep(2)

                # Get HTML content
                html_content = await page.content()

                # Extract resources from HTML
                resources = self.get_resources(url, html_content)

                return html_content, resources
            finally:
                # Close the page to free resources
                await page.close()
        except Exception as e:
            logger.error(f"Error getting page content from {url}: {e}")
            self.add_failed_url(url)
            return "", {}

    async def _async_scroll_page(self, page: Any) -> None:
        """
        Scroll the page to load lazy content.

        Args:
            page: Camoufox page object
        """
        try:
            # Get page height
            height = await page.evaluate("document.body.scrollHeight")

            # Scroll in steps
            for i in range(0, height, 100):
                await page.evaluate(f"window.scrollTo(0, {i})")
                await asyncio.sleep(0.1)

            # Scroll back to top
            await page.evaluate("window.scrollTo(0, 0)")

            # Wait for any lazy-loaded content
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error scrolling page: {e}")

    async def _async_take_screenshot(self, url: str, output_path: str) -> None:
        """
        Take a screenshot of the page asynchronously.

        Args:
            url (str): URL to screenshot
            output_path (str): Where to save the screenshot
        """
        if not self.browser_ctx:
            logger.error("Browser context not initialized")
            self.add_failed_url(url)
            return

        try:
            # Navigate to page
            page = await self.browser_ctx.new_page()
            await page.goto(url, wait_until="networkidle2")

            # Take screenshot
            await page.screenshot(path=output_path)
            logger.info(f"Screenshot saved to {output_path}")

            # Close page
            await page.close()
        except Exception as e:
            logger.error(f"Error taking screenshot of {url}: {e}")
            self.add_failed_url(url)

    def get_page_content(
        self, url: str, wait_for_js: bool = True, scroll: bool = True
    ) -> Tuple[str, Dict[str, List[str]]]:
        """
        Get page content using Camoufox.

        Args:
            url (str): URL to fetch
            wait_for_js (bool): Whether to wait for JavaScript to execute
            scroll (bool): Whether to scroll the page

        Returns:
            Tuple[str, Dict[str, List[str]]]: HTML content and resources
        """
        # Check if browser is initialized
        if not self.browser_mgr or not self.browser_ctx:
            logger.error("Browser not initialized")
            self.add_failed_url(url)
            return "", {}

        # First check if the URL points to a non-HTML resource
        resource_type = self.get_file_type(url)
        if resource_type != "html" and resource_type != "skip":
            logger.info(f"URL {url} appears to be a {resource_type} file, not HTML")
            self.add_failed_url(url)
            return "", {}

        try:
            # Execute the async method in our event loop
            logger.info(f"Fetching URL with Camoufox: {url}")
            future = asyncio.run_coroutine_threadsafe(
                self._async_get_page_content(url, wait_for_js, scroll), self._loop
            )

            # Use a timeout to prevent hanging on complex pages
            timeout = 60 if wait_for_js else 30  # Increase timeout for pages with JS
            return future.result(timeout=timeout)
        except asyncio.TimeoutError:
            logger.error(f"Timeout getting content from {url}")
            self.add_failed_url(url)
            return "", {}
        except Exception as e:
            logger.error(f"Error getting page content from {url}: {e}")
            self.add_failed_url(url)
            return "", {}

    def take_screenshot(self, url: str, output_path: str) -> None:
        """
        Take a screenshot of a page using Camoufox.

        Args:
            url (str): The URL to screenshot
            output_path (str): Where to save the screenshot
        """
        try:
            if not self._loop or self._loop.is_closed():
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)

            # Run asynchronous method in the event loop
            self._loop.run_until_complete(self._async_take_screenshot(url, output_path))
        except Exception as e:
            logger.error(f"Error in take_screenshot for {url}: {e}")
            self.add_failed_url(url)


# Legacy compatibility wrapper class
class CamoufoxWrapper:
    """Legacy compatibility wrapper for Camoufox."""

    def __init__(self, headless: bool = True, tor_proxy: bool = False):
        """Initialize the wrapper with a CamoufoxBrowser instance."""
        self.browser = CamoufoxBrowser(headless=headless, tor_proxy=tor_proxy)

    def __enter__(self):
        """Context manager entry point."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point."""
        self.browser.close()

    def get_page_content(
        self, url: str, wait_for_js: bool = True, scroll: bool = True
    ) -> Tuple[str, Dict[str, List[str]]]:
        """Get page content using the wrapped browser."""
        return self.browser.get_page_content(url, wait_for_js, scroll)

    def take_screenshot(self, url: str, output_path: str) -> None:
        """Take a screenshot using the wrapped browser."""
        self.browser.take_screenshot(url, output_path)

    @property
    def failed_urls(self) -> Set[str]:
        """Get failed URLs from the wrapped browser."""
        return self.browser.failed_urls


# Legacy compatibility function
def get_camoufox_session(
    headless: bool = True, tor_proxy: bool = False
) -> CamoufoxWrapper:
    """
    Get a CamoufoxWrapper instance that provides a synchronous interface to camoufox.

    Args:
        headless (bool): Whether to run in headless mode
        tor_proxy (bool): Whether to route traffic through Tor

    Returns:
        CamoufoxWrapper: A wrapper around CamoufoxBrowser
    """
    return CamoufoxWrapper(headless=headless, tor_proxy=tor_proxy)

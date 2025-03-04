"""Camoufox-based browser automation implementation with anti-bot protections."""

import asyncio
import logging
import random
from typing import Any, Dict, List, Set, Tuple

try:
    from camoufox import AsyncCamoufox

    CAMOUFOX_AVAILABLE = True
except ImportError:
    CAMOUFOX_AVAILABLE = False
    AsyncCamoufox = Any  # Type alias for missing package

from web_grabber.lib.browser_automation.base import BrowserAutomation
from web_grabber.lib.browser_automation.camoufox_handler.spoofing_config import (
    COMMON_FONTS,
    COMMON_PLUGINS,
    PLATFORMS,
    WEBGL_RENDERERS,
    WEBGL_VENDORS,
    WINDOW_CONFIGS,
)

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

        try:
            # Create browser manager
            browser_args = {
                "headless": self.headless,
                "viewport_width": viewport_resolution[0],
                "viewport_height": viewport_resolution[1],
                "user_agent": user_agent,
                "platform": platform,
                "webgl_vendor": vendor,
                "webgl_renderer": renderer,
                "locale": "en-US",
                "timezone_id": "America/New_York",
                "fonts": COMMON_FONTS[:5],  # Limit number of fonts
                "plugins": COMMON_PLUGINS,
                "accept_language": "en-US,en;q=0.9",
            }

            # Add Tor proxy if requested
            if self.tor_proxy:
                browser_args["proxy"] = {
                    "server": "socks5://127.0.0.1:9050",
                }

            # Initialize browser asynchronously
            async def setup_browser():
                self.browser_mgr = AsyncCamoufox(**browser_args)
                return await self.browser_mgr.__aenter__()

            self.browser_ctx = self._loop.run_until_complete(setup_browser())
            logger.info("Camoufox browser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Camoufox browser: {e}")
            raise

    def __enter__(self):
        """Context manager entry point."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point."""
        self.close()

    def close(self) -> None:
        """Close the browser and release resources."""
        if self.browser_mgr:
            try:
                # Close browser asynchronously
                async def cleanup_browser():
                    await self.browser_mgr.__aexit__(None, None, None)

                self._loop.run_until_complete(cleanup_browser())
                logger.info("Camoufox browser closed successfully")
            except Exception as e:
                logger.error(f"Error closing Camoufox browser: {e}")
            finally:
                self.browser_mgr = None
                self.browser_ctx = None

        if self._loop:
            self._loop.close()
            self._loop = None

    async def _async_get_page_content(
        self, url: str, wait_for_js: bool = True, scroll: bool = True
    ) -> Tuple[str, Dict[str, List[str]]]:
        """
        Get page content asynchronously.

        Args:
            url (str): URL to fetch
            wait_for_js (bool): Whether to wait for JS to execute
            scroll (bool): Whether to scroll the page

        Returns:
            Tuple[str, Dict[str, List[str]]]: HTML content and resources
        """
        if not self.browser_ctx:
            logger.error("Browser context not initialized")
            self.add_failed_url(url)
            return "", {"images": [], "videos": [], "documents": []}

        logger.info(f"Fetching URL with Camoufox: {url}")
        resources = {"images": [], "videos": [], "documents": []}

        try:
            # Navigate to the page
            page = await self.browser_ctx.new_page()
            await page.goto(
                url, wait_until="networkidle2" if wait_for_js else "domcontentloaded"
            )

            # Scroll page if requested
            if scroll:
                await self._async_scroll_page(page)

            # Get HTML content
            html_content = await page.content()

            # Extract resources using static methods from base class
            resources = self.get_resources(url, html_content)

            # Close page
            await page.close()

            return html_content, resources
        except Exception as e:
            logger.error(f"Error fetching {url} with Camoufox: {e}")
            self.add_failed_url(url)
            return "", resources

    async def _async_scroll_page(self, page: Any) -> None:
        """
        Scroll the page to load lazy content.

        Args:
            page: Camoufox page object
        """
        try:
            # Get scroll height
            last_height = await page.evaluate("document.body.scrollHeight")

            # Scroll in increments
            for _ in range(5):  # Scroll 5 times
                # Scroll down
                await page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(0.5)  # Allow time for content to load

                # Calculate new scroll height
                new_height = await page.evaluate("document.body.scrollHeight")

                # Break if no more scrolling is possible
                if new_height == last_height:
                    break
                last_height = new_height

            # Scroll back to top
            await page.evaluate("window.scrollTo(0, 0)")
        except Exception as e:
            logger.warning(f"Error while scrolling page: {e}")

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
        Get the content of a page using Camoufox.

        Args:
            url (str): The URL to fetch
            wait_for_js (bool): Whether to wait for JavaScript to execute
            scroll (bool): Whether to scroll the page to load lazy content

        Returns:
            Tuple[str, Dict[str, List[str]]]: HTML content and resources
        """
        try:
            if not self._loop or self._loop.is_closed():
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)

            # Run asynchronous method in the event loop
            return self._loop.run_until_complete(
                self._async_get_page_content(url, wait_for_js, scroll)
            )
        except Exception as e:
            logger.error(f"Error in get_page_content for {url}: {e}")
            self.add_failed_url(url)
            return "", {"images": [], "videos": [], "documents": []}

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

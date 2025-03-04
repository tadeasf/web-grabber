"""Handler for browser fingerprint randomization/camouflage using camoufox."""

import asyncio
import logging
from typing import Any, Dict, List, Tuple

from camoufox.async_api import AsyncCamoufox

from web_grabber.lib.spoofing_config import DEFAULT_CONFIG

logger = logging.getLogger(__name__)


async def get_camoufox_browser(
    headless: bool = True, tor_proxy: bool = False
) -> AsyncCamoufox:
    """
    Create a camoufox instance that can be used as an async context manager.

    Args:
        headless (bool): Whether to run browser in headless mode
        tor_proxy (bool): Whether to route traffic through Tor

    Returns:
        AsyncCamoufox: Instance to be used with async with
    """
    logger.info("Setting up camoufox browser")

    # Start with default configuration
    config = DEFAULT_CONFIG.copy()

    # Configure headless mode
    config["headless"] = headless

    # Configure proxy if Tor is enabled
    if tor_proxy:
        config["proxy"] = {
            "server": "socks5://127.0.0.1:9050",
            "username": "",
            "password": "",
        }
        logger.info("Routing camoufox through Tor proxy")

    # Initialize the browser
    try:
        browser = AsyncCamoufox(**config)
        logger.info("Camoufox browser successfully initialized")
        return browser
    except Exception as e:
        logger.error(f"Failed to initialize camoufox browser: {e}")
        raise


async def get_page_content_with_camoufox(
    browser_instance: Any, url: str, wait_for_js: bool = True, scroll: bool = True
) -> Tuple[str, Dict[str, List[str]]]:
    """
    Navigate to a URL and get the rendered page content using camoufox browser.

    Args:
        browser_instance: Browser or BrowserContext from camoufox
        url (str): URL to navigate to
        wait_for_js (bool): Whether to wait for JavaScript to load
        scroll (bool): Whether to scroll through the page to trigger lazy loading

    Returns:
        tuple: (page_html, page_resources)
            - page_html (str): HTML content of the page
            - page_resources (dict): Dictionary of resources found (images, videos)
    """
    logger.info(f"Getting page content for: {url}")

    resources = {"images": [], "videos": []}

    try:
        # Create a new page
        page = await browser_instance.new_page()

        # Navigate to the URL
        await page.goto(url)

        # Wait for the page to load
        if wait_for_js:
            await page.wait_for_load_state("networkidle")
            # Extra wait time for dynamic content
            await page.wait_for_timeout(2000)

        # Scroll to load lazy content if needed
        if scroll:
            # Get page height
            height = await page.evaluate("""() => document.body.scrollHeight""")

            # Get viewport height (using as property)
            viewport = page.viewport_size
            viewport_height = (
                viewport["height"] if viewport and "height" in viewport else 600
            )

            # Scroll in increments
            for scroll_position in range(0, height, viewport_height):
                await page.evaluate(f"window.scrollTo(0, {scroll_position})")
                await page.wait_for_timeout(200)

            # Scroll back to top
            await page.evaluate("window.scrollTo(0, 0)")

            # Wait a bit for any lazy loaded content
            await page.wait_for_timeout(1000)

        # Get the HTML content
        html_content = await page.content()

        # Extract image URLs
        image_elements = await page.query_selector_all("img")
        for img in image_elements:
            src = await img.get_attribute("src")
            if src and (src.startswith("http") or src.startswith("/")):
                resources["images"].append(src)

        # Extract video URLs
        video_elements = await page.query_selector_all("video")
        for video in video_elements:
            src = await video.get_attribute("src")
            if src and (src.startswith("http") or src.startswith("/")):
                resources["videos"].append(src)

        # Extract video source elements
        source_elements = await page.query_selector_all("source")
        for source in source_elements:
            src = await source.get_attribute("src")
            if src and (src.startswith("http") or src.startswith("/")):
                # Check the type to determine if it's a video
                type_attr = await source.get_attribute("type")
                if type_attr and type_attr.startswith("video/"):
                    resources["videos"].append(src)

        # Deduplicate resources
        resources["images"] = list(set(resources["images"]))
        resources["videos"] = list(set(resources["videos"]))

        # Close the page when done
        await page.close()

        return html_content, resources

    except Exception as e:
        logger.error(f"Error getting page content for {url}: {e}")
        raise


async def take_screenshot_with_camoufox(
    browser_instance: Any, url: str, output_path: str
) -> None:
    """
    Take a screenshot of a webpage using camoufox.

    Args:
        browser_instance: Browser or BrowserContext from camoufox
        url (str): URL to screenshot
        output_path (str): Path to save the screenshot
    """
    try:
        page = await browser_instance.new_page()
        await page.goto(url)
        await page.wait_for_load_state("networkidle")

        # Get full page dimensions
        dimensions = await page.evaluate("""() => {
            return {
                width: Math.max(
                    document.body.scrollWidth,
                    document.documentElement.scrollWidth,
                    document.body.offsetWidth,
                    document.documentElement.offsetWidth,
                    document.body.clientWidth,
                    document.documentElement.clientWidth
                ),
                height: Math.max(
                    document.body.scrollHeight,
                    document.documentElement.scrollHeight,
                    document.body.offsetHeight,
                    document.documentElement.offsetHeight,
                    document.body.clientHeight,
                    document.documentElement.clientHeight
                )
            };
        }""")

        # Set viewport to the full size of the page
        await page.set_viewport_size(
            {"width": dimensions["width"], "height": dimensions["height"]}
        )

        # Take the screenshot
        await page.screenshot(path=output_path, full_page=True)
        logger.info(f"Screenshot saved to {output_path}")

        # Close the page when done
        await page.close()
    except Exception as e:
        logger.error(f"Error taking screenshot of {url}: {e}")
        raise


class CamoufoxWrapper:
    """
    Wrapper class for camoufox to provide synchronous interface
    and manage the event loop.
    This allows easier integration with existing code that's not using async/await.
    """

    def __init__(self, headless: bool = True, tor_proxy: bool = False):
        """Initialize the wrapper with browser configuration."""
        self.headless = headless
        self.tor_proxy = tor_proxy
        self.browser_ctx = None
        self.browser_mgr = None
        self._loop = None

    def __enter__(self):
        """Set up the browser when entering context."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        # Create the camoufox instance
        try:
            # Run the async function in the event loop to get browser manager
            async def setup_browser():
                self.browser_mgr = await get_camoufox_browser(
                    self.headless, self.tor_proxy
                )
                self.browser_ctx = await self.browser_mgr.__aenter__()
                return self.browser_ctx

            self.browser_ctx = self._loop.run_until_complete(setup_browser())
            logger.info("Camoufox browser context initialized successfully")
            return self
        except Exception as e:
            logger.error(f"Error setting up camoufox: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources when exiting context."""
        if self.browser_mgr:

            async def cleanup_browser():
                await self.browser_mgr.__aexit__(exc_type, exc_val, exc_tb)

            self._loop.run_until_complete(cleanup_browser())

        if self._loop:
            self._loop.close()

    def get_page_content(
        self, url: str, wait_for_js: bool = True, scroll: bool = True
    ) -> Tuple[str, Dict[str, List[str]]]:
        """Synchronous wrapper for get_page_content_with_camoufox."""
        return self._loop.run_until_complete(
            get_page_content_with_camoufox(self.browser_ctx, url, wait_for_js, scroll)
        )

    def take_screenshot(self, url: str, output_path: str) -> None:
        """Synchronous wrapper for take_screenshot_with_camoufox."""
        return self._loop.run_until_complete(
            take_screenshot_with_camoufox(self.browser_ctx, url, output_path)
        )


def get_camoufox_session(
    headless: bool = True, tor_proxy: bool = False
) -> CamoufoxWrapper:
    """
    Get a CamoufoxWrapper instance that provides a synchronous interface to camoufox.

    Args:
        headless (bool): Whether to run in headless mode
        tor_proxy (bool): Whether to route traffic through Tor

    Returns:
        CamoufoxWrapper: Wrapper for camoufox with synchronous methods
    """
    return CamoufoxWrapper(headless=headless, tor_proxy=tor_proxy)

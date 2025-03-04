"""Handler for browser automation using Selenium."""

import logging
import time
from urllib.parse import urljoin

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)


def get_selenium_session(headless=True, tor_proxy=False):
    """
    Create and configure a Selenium WebDriver session.

    Args:
        headless (bool): Whether to run browser in headless mode
        tor_proxy (bool): Whether to route traffic through Tor

    Returns:
        webdriver: Configured WebDriver instance
    """
    logger.info("Setting up Selenium WebDriver")

    options = Options()

    if headless:
        options.add_argument("--headless")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )

    if tor_proxy:
        options.add_argument("--proxy-server=socks5://127.0.0.1:9050")
        logger.info("Routing Selenium through Tor proxy")

    try:
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(30)
        logger.info("Selenium WebDriver successfully initialized")
        return driver
    except WebDriverException as e:
        logger.error(f"Failed to initialize Selenium WebDriver: {e}")
        raise


def get_page_content(driver, url, wait_for_js=True, scroll=True):
    """
    Navigate to a URL and get the rendered page content after JavaScript execution.

    Args:
        driver: Selenium WebDriver instance
        url (str): URL to navigate to
        wait_for_js (bool): Whether to wait for JavaScript to load
        scroll (bool): Whether to scroll through the page to trigger lazy loading

    Returns:
        tuple: (page_html, page_resources)
            - page_html (str): HTML content of the page
            - page_resources (dict): Dictionary of resources found (images, videos)
    """
    logger.info(f"Getting page content for: {url}")

    try:
        driver.get(url)

        # Wait for page to load
        if wait_for_js:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            # Additional wait for dynamic content
            time.sleep(2)

        # Scroll to load lazy content if needed
        if scroll:
            scroll_height = 0
            while True:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == scroll_height:
                    break
                scroll_height = new_height

        # Get page HTML
        page_html = driver.page_source

        # Find resources (images, videos)
        page_resources = {"images": [], "videos": []}

        # Get images
        images = driver.find_elements(By.TAG_NAME, "img")
        for img in images:
            src = img.get_attribute("src")
            if src and (src.startswith("http") or src.startswith("/")):
                if src.startswith("/"):
                    src = urljoin(url, src)
                page_resources["images"].append(src)

        # Get videos
        videos = driver.find_elements(By.TAG_NAME, "video")
        for video in videos:
            src = video.get_attribute("src")
            if src and (src.startswith("http") or src.startswith("/")):
                if src.startswith("/"):
                    src = urljoin(url, src)
                page_resources["videos"].append(src)

        # Check for video sources
        video_sources = driver.find_elements(By.TAG_NAME, "source")
        for source in video_sources:
            src = source.get_attribute("src")
            if src and (src.startswith("http") or src.startswith("/")):
                if src.startswith("/"):
                    src = urljoin(url, src)
                page_resources["videos"].append(src)

        return page_html, page_resources

    except TimeoutException:
        logger.warning(f"Timeout when loading URL: {url}")
        return driver.page_source, {"images": [], "videos": []}
    except Exception as e:
        logger.error(f"Error getting page content for {url}: {e}")
        raise


def close_selenium_session(driver):
    """
    Properly close a Selenium WebDriver session.

    Args:
        driver: Selenium WebDriver instance to close
    """
    if driver:
        try:
            driver.quit()
            logger.info("Selenium WebDriver session closed")
        except Exception as e:
            logger.error(f"Error closing Selenium WebDriver: {e}")

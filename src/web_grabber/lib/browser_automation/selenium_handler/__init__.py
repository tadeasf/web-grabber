"""Selenium browser automation for web-grabber."""

from web_grabber.lib.browser_automation.selenium_handler.selenium_handler import (
    SeleniumBrowser,
    close_selenium_session,
    get_page_content,
    get_selenium_session,
)

__all__ = [
    "SeleniumBrowser",
    "get_selenium_session",
    "get_page_content",
    "close_selenium_session",
]

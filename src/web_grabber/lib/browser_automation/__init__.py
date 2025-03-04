"""Browser automation module for web-grabber."""

from src.web_grabber.lib.browser_automation.base import BrowserAutomation
from src.web_grabber.lib.browser_automation.camoufox_handler.camoufox_handler import (
    CamoufoxBrowser,
)
from src.web_grabber.lib.browser_automation.selenium_handler.selenium_handler import (
    SeleniumBrowser,
)

__all__ = ["BrowserAutomation", "SeleniumBrowser", "CamoufoxBrowser"]

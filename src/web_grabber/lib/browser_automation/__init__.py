"""Browser automation module for web-grabber."""

from web_grabber.lib.browser_automation.base import BrowserAutomation
from web_grabber.lib.browser_automation.camoufox_handler.camoufox_handler import (
    CamoufoxBrowser,
)
from web_grabber.lib.browser_automation.selenium_handler.selenium_handler import (
    SeleniumBrowser,
)

__all__ = ["BrowserAutomation", "SeleniumBrowser", "CamoufoxBrowser"]

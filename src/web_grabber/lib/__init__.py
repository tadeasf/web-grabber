"""Library components for web-grabber."""

from src.web_grabber.lib.browser_automation import (
    BrowserAutomation,
    CamoufoxBrowser,
    SeleniumBrowser,
)
from src.web_grabber.lib.browser_automation.camoufox_handler.camoufox_handler import (
    get_camoufox_session,
)

# Legacy compatibility imports for backward compatibility
from src.web_grabber.lib.browser_automation.selenium_handler.selenium_handler import (
    close_selenium_session,
    get_page_content,
    get_selenium_session,
)
from src.web_grabber.lib.network import (
    HttpxHandler,
    NetworkHandler,
    StandardHandler,
    TorHandler,
)
from src.web_grabber.lib.network.tor_handler.tor_handler import (
    configure_tor,
    reset_tor_connection,
)

__all__ = [
    # Browser automation
    "BrowserAutomation",
    "SeleniumBrowser",
    "CamoufoxBrowser",
    # Network handling
    "NetworkHandler",
    "TorHandler",
    "HttpxHandler",
    "StandardHandler",
    # Legacy functions for backward compatibility
    "get_selenium_session",
    "get_page_content",
    "close_selenium_session",
    "get_camoufox_session",
    "configure_tor",
    "reset_tor_connection",
]

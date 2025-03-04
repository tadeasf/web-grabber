"""Network handling module for web-grabber."""

from web_grabber.lib.network.base import NetworkHandler
from web_grabber.lib.network.http_handler.http_handler import HttpxHandler
from web_grabber.lib.network.tor_handler.tor_handler import (
    TorHandler,
    configure_tor,
    reset_tor_connection,
)

__all__ = [
    "NetworkHandler",
    "TorHandler",
    "HttpxHandler",
    "configure_tor",
    "reset_tor_connection",
]

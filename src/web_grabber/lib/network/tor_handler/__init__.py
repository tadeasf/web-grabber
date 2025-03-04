"""Tor handler module for network requests."""

from web_grabber.lib.network.tor_handler.tor_handler import (
    TorHandler,
    configure_tor,
    reset_tor_connection,
)

__all__ = ["TorHandler", "configure_tor", "reset_tor_connection"]

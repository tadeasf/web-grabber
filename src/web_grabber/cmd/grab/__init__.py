"""Grab command module for web-grabber."""

from web_grabber.cmd.grab.grab import grab_command
from web_grabber.cmd.grab.grab_handler import GrabHandler

__all__ = ["grab_command", "GrabHandler"]

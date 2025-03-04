"""Command-line interface modules for Web Grabber."""

from web_grabber.cmd.grab import grab_command
from web_grabber.cmd.scrape import scrape_command

__all__ = ["grab_command", "scrape_command"]

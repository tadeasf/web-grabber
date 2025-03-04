"""Main entry point for the Web Grabber CLI."""

import logging
import sys

import typer

from web_grabber import __version__
from web_grabber.cmd.grab import grab_command

# Create main Typer app
app = typer.Typer(
    name="web-grabber",
    help="Web Grabber: Download entire websites including HTML, images, videos, and documents.",
    add_completion=False,
)


@app.command()
def version():
    """Show version information."""
    typer.echo(f"Web Grabber v{__version__}")


# Add commands
app.command(name="grab")(grab_command)


@app.callback()
def main(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Web Grabber: Download entire websites including HTML, images, videos, and documents.

    Use the 'grab' command to start crawling a website.
    """
    # Configure logging
    log_level = logging.DEBUG if verbose else logging.ERROR if quiet else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


if __name__ == "__main__":
    app()

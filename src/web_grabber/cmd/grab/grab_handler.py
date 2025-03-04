"""Handler for grab command functionality."""

import logging
import os
import re
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, Optional, Set

from web_grabber.lib.browser_automation import (
    BrowserAutomation,
)
from web_grabber.lib.network import (
    HttpxHandler,
    NetworkHandler,
    StandardHandler,
    TorHandler,
)

logger = logging.getLogger(__name__)


class GrabHandler:
    """Handler class that implements the grab command's core functionality."""

    def __init__(self):
        """Initialize the grab handler."""
        self.already_visited: Set[str] = set()
        self.to_visit: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.resource_count = {"html": 0, "images": 0, "documents": 0, "videos": 0}
        self.network_handler: Optional[NetworkHandler] = None
        self.output_path: Optional[Path] = None

    def setup(
        self,
        url: str,
        output_dir: str,
        tor: bool = False,
        httpx: bool = True,
        selenium: bool = False,
        camoufox: bool = False,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
        timeout: int = 30,
        delay: float = 0.5,
        retry_failed: bool = False,
    ) -> None:
        """
        Set up the grab handler.

        Args:
            url: Starting URL to crawl
            output_dir: Directory to save output
            tor: Whether to use Tor
            httpx: Whether to use httpx
            selenium: Whether to use Selenium
            camoufox: Whether to use Camoufox
            user_agent: User agent string
            timeout: Request timeout in seconds
            delay: Delay between requests in seconds
            retry_failed: Whether to retry previously failed URLs
        """
        # Reset state
        self.already_visited = set()
        self.to_visit = set([url])
        self.failed_urls = set()
        self.resource_count = {"html": 0, "images": 0, "documents": 0, "videos": 0}

        # Set up output directory
        self.output_path = Path(output_dir)
        self.output_path.mkdir(parents=True, exist_ok=True)

        # Set up network handler
        if tor:
            self.network_handler = TorHandler(
                user_agent=user_agent, timeout=timeout, delay_between_requests=delay
            )
            logger.info("Using Tor for network requests")
        elif httpx and not selenium and not camoufox:
            self.network_handler = HttpxHandler(
                user_agent=user_agent, timeout=timeout, delay_between_requests=delay
            )
            logger.info("Using httpx for network requests")
        else:
            self.network_handler = StandardHandler(
                user_agent=user_agent, timeout=timeout, delay_between_requests=delay
            )
            logger.info("Using standard requests for network requests")

        # Load previously failed URLs if requested
        if retry_failed:
            self._load_failed_urls()

    def _load_failed_urls(self) -> None:
        """Load previously failed URLs from file."""
        if not self.output_path:
            return

        failed_urls_path = self.output_path / "failed_urls.txt"
        if failed_urls_path.exists():
            with open(failed_urls_path, "r") as f:
                prev_failed_urls = f.read().splitlines()
                prev_failed_urls = [
                    url.strip() for url in prev_failed_urls if url.strip()
                ]
                logger.info(
                    f"Loaded {len(prev_failed_urls)} previously failed URLs for retry"
                )
                self.to_visit.update(prev_failed_urls)

    def download_file(self, url: str, resource_type: str) -> bool:
        """
        Download a file from URL to output directory.

        Args:
            url: URL to download
            resource_type: Type of resource (html, images, documents, videos)

        Returns:
            True if download was successful, False otherwise
        """
        if not self.output_path or not self.network_handler:
            logger.error("Setup not completed before download")
            self.failed_urls.add(url)
            return False

        try:
            # Verify resource type again - it's possible that the initial detection was wrong
            detected_type = BrowserAutomation.get_file_type(url)

            # If the detected type doesn't match the requested type, use the detected type
            # This prevents HTML being downloaded as PDF, etc.
            if detected_type != resource_type and detected_type != "skip":
                logger.warning(
                    f"Changing resource type from {resource_type} to {detected_type} for {url}"
                )
                resource_type = detected_type

            # Handle file organization based on resource type
            if resource_type == "html":
                # HTML files stay in /html
                resource_dir = self.output_path / "html"
            else:
                # Other resources go to /files/{resource_type}
                resource_dir = self.output_path / "files" / resource_type

            # Ensure directory exists
            resource_dir.mkdir(parents=True, exist_ok=True)

            # Get file name from URL, fallback to hash if not available
            parsed_url = urllib.parse.urlparse(url)
            filename = os.path.basename(parsed_url.path)

            # If filename is empty or has no extension, create one
            if not filename or "." not in filename:
                url_hash = abs(hash(url)) % 10000
                ext = (
                    ".jpg"
                    if resource_type == "images"
                    else ".mp4"
                    if resource_type == "videos"
                    else ".pdf"
                    if resource_type == "documents"
                    else ".html"
                )
                filename = f"{url_hash}{ext}"
            else:
                # Check if the extension matches the resource type
                _, ext = os.path.splitext(filename)
                if resource_type == "images" and ext.lower() not in [
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".gif",
                    ".svg",
                    ".webp",
                    ".bmp",
                    ".ico",
                ]:
                    # Fix extension for images
                    filename = f"{filename.split('.')[0]}.jpg"
                elif resource_type == "videos" and ext.lower() not in [
                    ".mp4",
                    ".webm",
                    ".avi",
                    ".mov",
                    ".wmv",
                    ".flv",
                    ".mkv",
                ]:
                    # Fix extension for videos
                    filename = f"{filename.split('.')[0]}.mp4"
                elif resource_type == "documents" and ext.lower() not in [
                    ".pdf",
                    ".doc",
                    ".docx",
                    ".xls",
                    ".xlsx",
                    ".txt",
                ]:
                    # Fix extension for documents
                    filename = f"{filename.split('.')[0]}.pdf"

            # Sanitize filename
            filename = re.sub(r"[^\w\-.]", "_", filename)

            file_path = resource_dir / filename

            # Don't redownload if file exists
            if file_path.exists():
                logger.debug(f"File already exists: {file_path}")
                return True

            # Download the file
            success = self.network_handler.download_file(url, str(file_path))

            # Special handling for HTML-like content
            if (
                success
                and resource_type == "html"
                and file_path.suffix.lower() != ".html"
            ):
                # If we saved HTML content with a non-HTML extension, fix it
                new_path = file_path.with_suffix(".html")
                os.rename(file_path, new_path)
                file_path = new_path

            # Verify the file was downloaded correctly
            if os.path.exists(file_path):
                # Validate file using BrowserAutomation helper
                valid = BrowserAutomation.validate_downloaded_file(
                    file_path, resource_type, url
                )
                if not valid:
                    self.failed_urls.add(url)
                    return False

            if success:
                self.resource_count[resource_type] += 1
                logger.info(f"Downloaded {resource_type}: {url} -> {file_path}")
                return True
            else:
                self.failed_urls.add(url)
                return False
        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            self.failed_urls.add(url)
            return False

    def process_page(self, url: str) -> None:
        """Process a web page and extract resources.

        Args:
            url: URL to process
        """
        if not self._should_process_url(url):
            logger.info(f"Skipping URL: {url}")
            return

        logger.info(f"Processing URL: {url}")
        self.already_visited.add(url)

        try:
            # Get page content and resources
            html_content, resources = self.network_handler.get_page_content(
                url, wait_for_js=self.args.javascript, scroll=self.args.scroll
            )

            # First determine if the URL itself is a resource
            url_resource_type = self.network_handler.get_file_type(url)
            if url_resource_type != "html" and url_resource_type != "skip":
                logger.info(
                    f"URL {url} is a {url_resource_type} resource, downloading directly"
                )
                self.download_file(url, url_resource_type)
                return

            # Only save HTML if content was retrieved successfully
            if html_content:
                # Validate HTML content before saving
                if self._is_valid_html(html_content):
                    self._save_html_content(url, html_content)
                else:
                    # If not valid HTML, it's likely a file, try to download directly
                    logger.info(
                        f"Content from {url} is not valid HTML, attempting direct download"
                    )
                    direct_type = self._detect_content_type(html_content)
                    if direct_type != "html":
                        self.download_file(url, direct_type)
                    else:
                        # Save it as HTML but log a warning
                        logger.warning(
                            f"Saving content with unclear type as HTML: {url}"
                        )
                        self._save_html_content(url, html_content)
            else:
                logger.warning(f"No HTML content retrieved from: {url}")

            # Process resources if requested
            if self.args.resources:
                self._process_resources(url, resources)

            # Process links if requested
            if self.args.links:
                links = BrowserAutomation.get_page_links(url, html_content)
                self._process_links(url, links)

        except Exception as e:
            logger.error(f"Error processing URL {url}: {e}")
            if self.args.debug:
                import traceback

                logger.debug(traceback.format_exc())
            self.failed_urls.add(url)

    def _save_html_content(self, url: str, html_content: str) -> None:
        """
        Save HTML content to file.

        Args:
            url: URL the content was fetched from
            html_content: HTML content to save
        """
        if not self.output_path:
            return

        # First check if the URL actually points to a non-HTML resource
        resource_type = BrowserAutomation.get_file_type(url)
        if resource_type != "html":
            logger.warning(
                f"URL {url} appears to be a {resource_type} file, not HTML. Handling accordingly."
            )
            self.download_file(url, resource_type)
            return

        # Check if the content appears to be binary or not actually HTML
        if not self._is_valid_html(html_content):
            logger.warning(
                f"Content from {url} doesn't appear to be valid HTML. Treating as document."
            )
            self.download_file(url, "documents")
            return

        page_dir = self.output_path / "html"
        page_dir.mkdir(exist_ok=True)

        # Create filename from URL
        parsed_url = urllib.parse.urlparse(url)
        path_parts = parsed_url.path.strip("/").split("/")
        if not path_parts or path_parts == [""]:
            filename = "index.html"
        else:
            # Use last part of path as filename, or index.html for root
            filename = path_parts[-1]
            if not filename or "." not in filename:
                filename = f"{filename or 'page'}.html"

        # Check if the filename suggests this is a document or image, not HTML
        lower_filename = filename.lower()

        # Check for document files
        if any(
            lower_filename.endswith(ext)
            for ext in [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"]
        ):
            logger.warning(
                f"Found document file '{filename}' in HTML path. Handling it as document."
            )
            self.download_file(url, "documents")
            return

        # Check for image files
        if any(
            lower_filename.endswith(ext)
            for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"]
        ):
            logger.warning(
                f"Found image file '{filename}' in HTML path. Handling it as image."
            )
            self.download_file(url, "images")
            return

        # Check for video files
        if any(
            lower_filename.endswith(ext)
            for ext in [".mp4", ".webm", ".avi", ".mov", ".wmv", ".flv"]
        ):
            logger.warning(
                f"Found video file '{filename}' in HTML path. Handling it as video."
            )
            self.download_file(url, "videos")
            return

        # Ensure the filename has .html extension
        if not lower_filename.endswith(".html") and not lower_filename.endswith(".htm"):
            base_name = filename.split(".")[0] if "." in filename else filename
            filename = f"{base_name}.html"

        # Sanitize filename
        filename = re.sub(r"[^\w\-.]", "_", filename)

        # Add unique identifier if needed
        file_path = page_dir / filename
        if file_path.exists():
            base, ext = os.path.splitext(filename)
            file_path = page_dir / f"{base}_{abs(hash(url)) % 10000}{ext}"

        # Save HTML
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        self.resource_count["html"] += 1
        logger.info(f"Saved HTML: {url} -> {file_path}")

    def _is_valid_html(self, content: str) -> bool:
        """
        Check if content appears to be valid HTML.

        Args:
            content: String content to check

        Returns:
            bool: True if content appears to be HTML, False otherwise
        """
        if not content:
            return False

        # Check for PDF signature
        if content.startswith("%PDF-"):
            return False

        # Check for common HTML markers
        lower_content = content.lower()
        return (
            "<!doctype html" in lower_content[:1000]
            or "<html" in lower_content[:1000]
            or "<head" in lower_content[:1000]
            or "<body" in lower_content[:1000]
        )

    def _detect_content_type(self, content: str) -> str:
        """
        Attempt to detect content type from the content itself.

        Args:
            content: Content to analyze

        Returns:
            str: Detected file type ("documents", "images", "html", etc.)
        """
        # Check for PDF signature
        if content.startswith("%PDF-"):
            return "documents"

        # Check for common image signatures
        if content.startswith(b"\xff\xd8\xff"):  # JPEG
            return "images"
        if content.startswith(b"\x89PNG\r\n\x1a\n"):  # PNG
            return "images"
        if content.startswith(b"GIF87a") or content.startswith(b"GIF89a"):  # GIF
            return "images"

        # Check for HTML indicators
        lower_content = content.lower()
        if (
            "<!doctype html" in lower_content[:1000]
            or "<html" in lower_content[:1000]
            or "<head" in lower_content[:1000]
            or "<body" in lower_content[:1000]
        ):
            return "html"

        # Default to documents for unknown types
        return "documents"

    def crawl(
        self,
        threads: int = 5,
        depth: int = 100,
        delay: float = 0.5,
        use_selenium: bool = False,
        use_camoufox: bool = False,
        use_httpx: bool = True,
    ) -> None:
        """
        Crawl websites starting from the initial URL.

        Args:
            threads: Number of concurrent threads
            depth: Maximum depth to crawl
            delay: Delay between requests in seconds
            use_selenium: Whether to use Selenium
            use_camoufox: Whether to use Camoufox
            use_httpx: Whether to use httpx
        """
        if not self.network_handler or not self.output_path:
            logger.error("Setup not completed before crawling")
            return

        # Start crawling
        logger.info(f"Starting crawl with {threads} threads")
        start_time = time.time()

        try:
            with ThreadPoolExecutor(max_workers=threads) as executor:
                futures = []

                while self.to_visit:
                    batch = set()
                    for _ in range(min(threads * 2, len(self.to_visit))):
                        if not self.to_visit:
                            break
                        batch.add(self.to_visit.pop())

                    for page_url in batch:
                        futures.append(
                            executor.submit(
                                self.process_page,
                                page_url,
                            )
                        )

                    # Wait for the current batch to complete
                    for future in futures:
                        try:
                            future.result()
                        except Exception as e:
                            logger.error(f"Error in thread: {e}")

                    futures = []

                    # Sleep to avoid overloading the server
                    time.sleep(delay)
        finally:
            # Clean up resources
            if self.network_handler:
                self.network_handler.close()
                self.network_handler = None

        # Save failed URLs to a file
        self._save_failed_urls()

        # Log summary
        elapsed_time = time.time() - start_time
        logger.info(f"Crawl completed in {elapsed_time:.2f} seconds")
        logger.info(
            f"Downloaded: {self.resource_count['html']} HTML files, "
            f"{self.resource_count['images']} images, "
            f"{self.resource_count['documents']} documents, "
            f"{self.resource_count['videos']} videos"
        )
        logger.info(f"Failed URLs: {len(self.failed_urls)}")

    def _save_failed_urls(self) -> None:
        """Save failed URLs to a file."""
        if not self.output_path or not self.failed_urls:
            return

        failed_urls_path = self.output_path / "failed_urls.txt"
        with open(failed_urls_path, "w") as f:
            for failed_url in sorted(self.failed_urls):
                f.write(f"{failed_url}\n")
        logger.info(f"Saved {len(self.failed_urls)} failed URLs to {failed_urls_path}")

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the crawl.

        Returns:
            Dictionary with summary information
        """
        return {
            "visited_urls": len(self.already_visited),
            "failed_urls": len(self.failed_urls),
            "resources": dict(self.resource_count),
        }

"""Base class for browser automation in web-grabber."""

import logging
import os
import re
import urllib.parse
from pathlib import Path
from typing import Dict, List, Set, Tuple

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class BrowserAutomation:
    """Base class for browser automation implementations with standard functionality."""

    def __init__(self, headless: bool = True, tor_proxy: bool = False):
        """
        Initialize the browser automation base class.

        Args:
            headless (bool): Whether to run the browser in headless mode
            tor_proxy (bool): Whether to route traffic through Tor
        """
        self.headless = headless
        self.tor_proxy = tor_proxy
        self._failed_urls: Set[str] = set()

    def get_page_content(
        self, url: str, wait_for_js: bool = True, scroll: bool = True
    ) -> Tuple[str, Dict[str, List[str]]]:
        """
        Get the content of a page using standard requests (no JavaScript support).

        Args:
            url (str): The URL to fetch
            wait_for_js (bool): Whether to wait for JavaScript to execute (ignored in standard implementation)
            scroll (bool): Whether to scroll the page to load lazy content (ignored in standard implementation)

        Returns:
            Tuple[str, Dict[str, List[str]]]: HTML content and resources
        """
        resources = {"images": [], "videos": [], "documents": []}

        try:
            # First check if the URL points to a non-HTML resource
            resource_type = self.get_file_type(url)
            if resource_type != "html" and resource_type != "skip":
                logger.info(f"URL {url} appears to be a {resource_type} file, not HTML")
                self.add_failed_url(url)
                return "", resources

            logger.info(f"Fetching URL with standard handler: {url}")

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()  # Raise exception for 4XX/5XX responses

            # Check content type to ensure we're getting HTML
            content_type = response.headers.get("Content-Type", "").lower()
            if (
                "text/html" not in content_type
                and "application/xhtml+xml" not in content_type
            ):
                logger.warning(f"URL {url} returned non-HTML content: {content_type}")

                # If it's a document or image, don't treat it as a failed URL
                if any(
                    doc_type in content_type
                    for doc_type in [
                        "application/pdf",
                        "image/",
                        "video/",
                        "application/msword",
                    ]
                ):
                    return "", resources

                # Otherwise, mark as failed
                self.add_failed_url(url)
                return "", resources

            # Get content
            html_content = response.text

            # Check if the content is valid HTML
            if not html_content or not self._is_valid_html(html_content):
                logger.warning(f"Content from {url} doesn't appear to be valid HTML")
                self.add_failed_url(url)
                return html_content, resources

            # Extract resources from content
            resources = self.get_resources(url, html_content)

            return html_content, resources
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for {url}: {e}")
            self.add_failed_url(url)
            return "", resources
        except Exception as e:
            logger.error(f"Error fetching {url} with standard handler: {e}")
            self.add_failed_url(url)
            return "", resources

    def take_screenshot(self, url: str, output_path: str) -> None:
        """
        Take a screenshot of a page.

        Note: The standard implementation does not support taking screenshots.
        This method is a placeholder that logs a warning.

        Args:
            url (str): The URL to take a screenshot of
            output_path (str): The path to save the screenshot to
        """
        logger.warning("Screenshot not supported with standard browser implementation")
        logger.warning("Use Selenium or Camoufox handlers for screenshot support")

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

    @staticmethod
    def is_valid_url(base_url: str, url: str) -> bool:
        """
        Check if URL is valid and belongs to the same domain.

        Args:
            base_url (str): The base URL to compare against
            url (str): The URL to check

        Returns:
            bool: True if valid, False otherwise
        """
        if not url or not isinstance(url, str):
            return False

        # Clean the URL
        url = url.strip()

        # Skip anchors, javascript, mailto, etc.
        if url.startswith(("#", "javascript:", "mailto:", "tel:")):
            return False

        # Handle relative URLs
        if url.startswith("/"):
            return True

        # Check if URL is from the same domain
        try:
            base_domain = urllib.parse.urlparse(base_url).netloc
            url_domain = urllib.parse.urlparse(url).netloc

            # Allow subdomains
            return url_domain == base_domain or url_domain.endswith("." + base_domain)
        except Exception as e:
            logger.error(f"Error validating URL {url}: {e}")
            return False

    @staticmethod
    def normalize_url(base_url: str, url: str) -> str:
        """
        Normalize URL to absolute form.

        Args:
            base_url (str): The base URL to resolve against
            url (str): The URL to normalize

        Returns:
            str: Normalized URL
        """
        if not url or not isinstance(url, str):
            return base_url

        url = url.strip()

        # Handle empty URLs
        if not url:
            return base_url

        # Parse base URL once for efficiency
        parsed_base = urllib.parse.urlparse(base_url)
        base_scheme = parsed_base.scheme
        base_netloc = parsed_base.netloc

        # Handle fragment identifiers
        if "#" in url:
            url = url.split("#")[0]

        # Normalize scheme-relative URLs (//example.com/path)
        if url.startswith("//"):
            return f"{base_scheme}:{url}"

        # Handle absolute URLs
        if url.startswith(("http://", "https://")):
            return url

        # Handle root-relative URLs
        if url.startswith("/"):
            return f"{base_scheme}://{base_netloc}{url}"

        # Handle parent directory navigation (../) carefully
        if url.startswith("../") or "/../" in url:
            return urllib.parse.urljoin(base_url, url)

        # Handle URLs without scheme or host
        if "://" not in url:
            return urllib.parse.urljoin(base_url, url)

        return url

    @staticmethod
    def get_file_type(url: str) -> str:
        """
        Determine the file type category based on the URL or extension.

        Args:
            url (str): The URL to analyze

        Returns:
            str: One of 'html', 'images', 'videos', 'documents', or 'skip'
        """
        lower_url = url.lower()

        # Extract extension from URL
        parsed_url = urllib.parse.urlparse(lower_url)
        path = parsed_url.path
        _, ext = os.path.splitext(path)

        # Remove the dot from extension
        ext = ext[1:] if ext.startswith(".") else ext

        # Check for known file patterns first
        filename = os.path.basename(path)

        # Check if the URL appears to be a webpage (no extension or common web extensions)
        if not ext or ext in ["html", "htm", "xhtml", "php", "asp", "aspx", "jsp"]:
            return "html"

        # Categorize by extension for media and documents
        if ext in [
            "jpg",
            "jpeg",
            "png",
            "gif",
            "svg",
            "webp",
            "bmp",
            "ico",
            "tif",
            "tiff",
        ]:
            return "images"
        elif ext in ["mp4", "webm", "avi", "mov", "wmv", "flv", "mkv", "ogv", "m4v"]:
            return "videos"
        elif ext in [
            "pdf",
            "doc",
            "docx",
            "xls",
            "xlsx",
            "ppt",
            "pptx",
            "txt",
            "rtf",
            "csv",
            "odt",
            "ods",
            "odp",
            "epub",
            "mobi",
            "zip",
            "rar",
            "tar",
            "gz",
        ]:
            # Only include actual document URLs, not arbitrary URLs that we'd save as PDF
            # Special handling for resume-like documents
            if ext == "pdf" and (
                "resume" in lower_url or "cv" in lower_url or "/documents/" in lower_url
            ):
                return "documents"
            elif (
                ext != "pdf"
            ):  # Non-PDF documents are less likely to be misclassified webpages
                return "documents"
            else:
                # For URLs that end in .pdf but don't seem to be actual documents
                # Check if it's a random-looking filename that might be a hash
                if filename.replace(".pdf", "").isdigit():
                    logger.debug(
                        f"URL ends with .pdf but appears to be a webpage: {url}"
                    )
                    return "html"  # Treat as HTML instead
                return "documents"  # Otherwise assume it's a real PDF

        # For URLs with no recognized extension, check for document-like patterns
        if "/resume" in lower_url or "/cv" in lower_url or "/documents/" in lower_url:
            return "documents"

        # Default for URLs without a recognized type - treat as HTML
        return "html"

    @staticmethod
    def get_page_links(base_url: str, html_content: str) -> List[str]:
        """
        Extract all links from a webpage that belong to the same domain.

        Args:
            base_url (str): The base URL to resolve against
            html_content (str): The HTML content to parse

        Returns:
            List[str]: Normalized list of URLs
        """
        soup = BeautifulSoup(html_content, "html.parser")
        links = []

        # Get all anchor tags
        for a_tag in soup.find_all("a", href=True):
            url = a_tag["href"]
            if BrowserAutomation.is_valid_url(base_url, url):
                links.append(BrowserAutomation.normalize_url(base_url, url))

        return list(set(links))  # Remove duplicates

    @staticmethod
    def get_resources(base_url: str, html_content: str) -> Dict[str, List[str]]:
        """
        Extract images, videos, and documents from HTML content.

        Args:
            base_url (str): The base URL to resolve against
            html_content (str): The HTML content to parse

        Returns:
            Dict[str, List[str]]: Resources categorized by type
        """
        soup = BeautifulSoup(html_content, "html.parser")
        resources = {"images": [], "videos": [], "documents": []}

        # Get all images
        for img in soup.find_all("img", src=True):
            src = img["src"]
            if src:
                src = BrowserAutomation.normalize_url(base_url, src)
                resources["images"].append(src)

        # Also look for background images in styles
        for tag in soup.find_all(lambda tag: tag.has_attr("style")):
            style = tag["style"]
            urls = re.findall(r'url\([\'"]?([^\'"]*)[\'"]?\)', style)
            for url in urls:
                if url:
                    normalized_url = BrowserAutomation.normalize_url(base_url, url)
                    resource_type = BrowserAutomation.get_file_type(normalized_url)
                    if resource_type == "images":
                        resources["images"].append(normalized_url)

        # Get all videos
        for video in soup.find_all("video"):
            if video.has_attr("src"):
                src = video["src"]
                src = BrowserAutomation.normalize_url(base_url, src)
                resources["videos"].append(src)

            # Check for source tags inside video
            for source in video.find_all("source", src=True):
                src = source["src"]
                src = BrowserAutomation.normalize_url(base_url, src)
                resources["videos"].append(src)

        # Get links to documents - be more selective
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if href:
                href = BrowserAutomation.normalize_url(base_url, href)
                resource_type = BrowserAutomation.get_file_type(href)

                # Skip resources that were flagged to be skipped
                if resource_type == "skip":
                    continue

                # Only add documents that match specific patterns or have specific extensions
                if resource_type == "documents":
                    # Only download PDFs with relevant names or from specific paths
                    parsed_url = urllib.parse.urlparse(href)
                    path = parsed_url.path.lower()
                    filename = os.path.basename(path)

                    # Special handling for resumes and common document types
                    if path.endswith(".pdf"):
                        # Check for resume, CV, specific document types
                        if (
                            "resume" in filename
                            or "cv" in filename
                            or "document" in filename
                            or "assets/documents" in path
                            or "docs/" in path
                            or "publications/" in path
                        ):
                            resources["documents"].append(href)
                            logger.info(f"Added document resource: {href}")
                    else:
                        # For non-PDF documents, we're less restrictive
                        resources["documents"].append(href)

        # Deduplicate
        resources["images"] = list(set(resources["images"]))
        resources["videos"] = list(set(resources["videos"]))
        resources["documents"] = list(set(resources["documents"]))

        return resources

    @staticmethod
    def validate_downloaded_file(file_path: Path, resource_type: str, url: str) -> bool:
        """
        Validate a downloaded file for integrity and content.

        Args:
            file_path (Path): Path to the downloaded file
            resource_type (str): Type of resource
            url (str): Source URL

        Returns:
            bool: True if valid, False otherwise
        """
        try:
            # Verify the file exists
            if not file_path.exists():
                logger.error(f"Downloaded file does not exist: {file_path}")
                return False

            # Check file size
            file_size = os.path.getsize(file_path)

            # For images, we expect at least 100 bytes for a valid image
            if resource_type == "images" and file_size < 100:
                logger.error(
                    f"Downloaded image is likely corrupted (size: {file_size} bytes): {file_path}"
                )
                # Remove the corrupted file
                os.remove(file_path)
                return False

            # For videos, we expect larger files
            if resource_type == "videos" and file_size < 1024:
                logger.warning(
                    f"Downloaded video is suspiciously small (size: {file_size} bytes): {file_path}"
                )

            # Check if file appears to be HTML content saved with a wrong extension
            if resource_type in ["documents", "images", "videos"] and file_size > 0:
                # Read first 1KB to check if it looks like HTML
                with open(file_path, "rb") as f:
                    content_start = (
                        f.read(1024).decode("utf-8", errors="ignore").lower()
                    )

                    if content_start.strip().startswith(("<!doctype html", "<html")):
                        # This is HTML content saved with a wrong extension
                        logger.error(
                            f"File {file_path} appears to be HTML content with wrong extension. Deleting."
                        )
                        os.remove(file_path)
                        return False

            # For PDF documents, check if it's a valid PDF
            if resource_type == "documents" and file_path.suffix.lower() == ".pdf":
                # Check if it has a PDF signature
                with open(file_path, "rb") as f:
                    header = f.read(5).decode("utf-8", errors="ignore")
                    if not header.startswith("%PDF-"):
                        logger.error(
                            f"File {file_path} has .pdf extension but is not a valid PDF. Deleting."
                        )
                        os.remove(file_path)
                        return False

                # Still warn about small PDFs
                if file_size < 1024:
                    logger.warning(
                        f"Downloaded PDF is suspiciously small (size: {file_size} bytes): {file_path}"
                    )

            return True
        except Exception as e:
            logger.error(f"Error validating file {file_path}: {e}")
            return False

    @property
    def failed_urls(self) -> Set[str]:
        """Get the set of failed URLs."""
        return self._failed_urls

    def add_failed_url(self, url: str) -> None:
        """Add a URL to the set of failed URLs."""
        self._failed_urls.add(url)

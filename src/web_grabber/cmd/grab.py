"""Command for grabbing and downloading website content."""

import logging
import os
import re
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Set, Dict

import requests
import typer
from bs4 import BeautifulSoup

from web_grabber.lib.tor_handler import configure_tor
from web_grabber.lib.selenium_handler import (
    get_selenium_session, 
    get_page_content, 
    close_selenium_session
)
from web_grabber.lib.camoufox_handler import get_camoufox_session


logger = logging.getLogger(__name__)

# Configure a global session that will be used/replaced
session = requests.Session()
already_visited: Set[str] = set()
to_visit: Set[str] = set()
failed_urls: Set[str] = set()
resource_count = {"html": 0, "images": 0, "videos": 0}


def is_valid_url(base_url: str, url: str) -> bool:
    """Check if URL is valid and belongs to the same domain."""
    if not url or not isinstance(url, str):
        return False
    
    # Clean the URL
    url = url.strip()
    
    # Skip anchors, javascript, mailto, etc.
    if url.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
        return False
    
    # Handle relative URLs
    if url.startswith('/'):
        return True
    
    # Check if URL is from the same domain
    try:
        base_domain = urllib.parse.urlparse(base_url).netloc
        url_domain = urllib.parse.urlparse(url).netloc
        
        # Allow subdomains
        return url_domain == base_domain or url_domain.endswith('.' + base_domain)
    except Exception:
        return False


def normalize_url(base_url: str, url: str) -> str:
    """Normalize URL to absolute form."""
    url = url.strip()
    
    # Handle relative URLs
    if url.startswith('/'):
        return urllib.parse.urljoin(base_url, url)
    
    # Already absolute URL
    if url.startswith(('http://', 'https://')):
        return url
    
    # Handle fragment identifiers
    if '#' in url:
        url = url.split('#')[0]
    
    return urllib.parse.urljoin(base_url, url)


def get_page_links(base_url: str, html_content: str) -> List[str]:
    """Extract all links from a webpage that belong to the same domain."""
    soup = BeautifulSoup(html_content, 'html.parser')
    links = []
    
    # Get all anchor tags
    for a_tag in soup.find_all('a', href=True):
        url = a_tag['href']
        if is_valid_url(base_url, url):
            links.append(normalize_url(base_url, url))
    
    return list(set(links))  # Remove duplicates


def get_resources(base_url: str, html_content: str) -> Dict[str, List[str]]:
    """Extract images and videos from HTML content."""
    soup = BeautifulSoup(html_content, 'html.parser')
    resources = {
        "images": [],
        "videos": []
    }
    
    # Get all images
    for img in soup.find_all('img', src=True):
        src = img['src']
        if src:
            src = normalize_url(base_url, src)
            resources["images"].append(src)
    
    # Get all videos
    for video in soup.find_all('video'):
        if video.has_attr('src'):
            src = video['src']
            src = normalize_url(base_url, src)
            resources["videos"].append(src)
        
        # Check for source tags inside video
        for source in video.find_all('source', src=True):
            src = source['src']
            src = normalize_url(base_url, src)
            resources["videos"].append(src)
    
    # Deduplicate
    resources["images"] = list(set(resources["images"]))
    resources["videos"] = list(set(resources["videos"]))
    
    return resources


def download_file(url: str, output_dir: Path, resource_type: str) -> bool:
    """Download a file from URL to specified directory."""
    try:
        # Create appropriate directory
        resource_dir = output_dir / resource_type
        resource_dir.mkdir(exist_ok=True)
        
        # Get file name from URL, fallback to hash if not available
        parsed_url = urllib.parse.urlparse(url)
        filename = os.path.basename(parsed_url.path)
        
        # If filename is empty or has no extension, create one
        if not filename or '.' not in filename:
            url_hash = abs(hash(url)) % 10000
            ext = '.jpg' if resource_type == 'images' else '.mp4' if resource_type == 'videos' else '.html'
            filename = f"{url_hash}{ext}"
        
        # Sanitize filename
        filename = re.sub(r'[^\w\-.]', '_', filename)
        
        file_path = resource_dir / filename
        
        # Don't redownload if file exists
        if file_path.exists():
            logger.debug(f"File already exists: {file_path}")
            return True
        
        # Download the file
        response = session.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        resource_count[resource_type] += 1
        logger.info(f"Downloaded {resource_type}: {url} -> {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        failed_urls.add(url)
        return False


def process_page(url: str, output_dir: Path, use_selenium: bool, use_camoufox: bool, depth: int, max_depth: int) -> None:
    """Process a single webpage, extract content and resources."""
    global already_visited, to_visit, session
    
    if url in already_visited or depth > max_depth:
        return
    
    logger.info(f"Processing page: {url} (depth {depth}/{max_depth})")
    already_visited.add(url)
    
    try:
        # Get page content
        if use_camoufox:
            # Use camoufox for anti-bot protection
            logger.info("Using camoufox for anti-bot protection")
            camoufox = get_camoufox_session(headless=True, tor_proxy=isinstance(session, requests.Session) and hasattr(session, 'proxies'))
            with camoufox:
                html_content, resources = camoufox.get_page_content(url)
        elif use_selenium:
            driver = get_selenium_session(headless=True, tor_proxy=isinstance(session, requests.Session) and hasattr(session, 'proxies'))
            html_content, resources = get_page_content(driver, url)
            close_selenium_session(driver)
        else:
            response = session.get(url, timeout=30)
            response.raise_for_status()
            html_content = response.text
            resources = get_resources(url, html_content)
        
        # Save the HTML content
        page_dir = output_dir / "html"
        page_dir.mkdir(exist_ok=True)
        
        # Create filename from URL
        parsed_url = urllib.parse.urlparse(url)
        path_parts = parsed_url.path.strip('/').split('/')
        if not path_parts or path_parts == ['']:
            filename = 'index.html'
        else:
            # Use last part of path as filename, or index.html for root
            filename = path_parts[-1]
            if not filename or '.' not in filename:
                filename = f"{filename or 'page'}.html"
        
        # Sanitize filename
        filename = re.sub(r'[^\w\-.]', '_', filename)
        
        # Add unique identifier if needed
        file_path = page_dir / filename
        if file_path.exists():
            base, ext = os.path.splitext(filename)
            file_path = page_dir / f"{base}_{abs(hash(url)) % 10000}{ext}"
        
        # Save HTML
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        resource_count["html"] += 1
        logger.info(f"Saved HTML: {url} -> {file_path}")
        
        # Extract links for further crawling
        if depth < max_depth:
            links = get_page_links(url, html_content)
            for link in links:
                if link not in already_visited:
                    to_visit.add(link)
        
        # Download resources
        for resource_type, urls in resources.items():
            for resource_url in urls:
                download_file(resource_url, output_dir, resource_type)
                
    except Exception as e:
        logger.error(f"Error processing {url}: {e}")
        failed_urls.add(url)


def grab_command(
    url: str = typer.Argument(..., help="URL of the website to crawl"),
    output_dir: str = typer.Option("./grabbed_site", help="Directory to save downloaded content"),
    depth: int = typer.Option(100, help="Maximum crawl depth (default: 100, effectively unlimited for most sites)"),
    tor: bool = typer.Option(False, help="Route traffic through Tor network"),
    selenium: bool = typer.Option(False, help="Use Selenium for JavaScript rendered content"),
    camoufox: bool = typer.Option(False, help="Use camoufox for anti-bot protection (overrides --selenium)"),
    threads: int = typer.Option(5, help="Number of concurrent threads for crawling"),
    delay: float = typer.Option(0.5, help="Delay between requests (in seconds)"),
    timeout: int = typer.Option(30, help="Request timeout (in seconds)"),
    user_agent: str = typer.Option(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        help="User agent string"
    ),
    verbose: bool = typer.Option(False, help="Enable verbose logging")
):
    """
    Crawl a website and download all HTML, images, and videos.
    
    Example:
        web-grabber grab https://example.com --output-dir ./example --depth 3
    """
    global session, already_visited, to_visit, failed_urls, resource_count
    
    # Reset global state
    already_visited = set()
    to_visit = {url}
    failed_urls = set()
    resource_count = {"html": 0, "images": 0, "videos": 0}
    
    # Configure logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info(f"Starting web grabber for {url}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Max depth: {depth}")
    logger.info(f"Using Tor: {tor}")
    
    # Check browser options
    if camoufox:
        logger.info("Using camoufox for anti-bot protection")
        selenium = False  # camoufox overrides selenium
    elif selenium:
        logger.info("Using Selenium for JavaScript rendering")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Configure session
    session = requests.Session()
    session.headers.update({'User-Agent': user_agent})
    session.timeout = timeout
    
    # Configure Tor if needed
    if tor:
        try:
            session = configure_tor(session)
        except Exception as e:
            logger.error(f"Failed to configure Tor: {e}")
            logger.error("Make sure Tor is running on 127.0.0.1:9050")
            return
    
    current_depth = 0
    
    # Crawl the website breadth-first
    while to_visit and current_depth <= depth:
        current_urls = list(to_visit)
        to_visit = set()
        
        logger.info(f"Crawling {len(current_urls)} URLs at depth {current_depth}")
        
        # Use ThreadPoolExecutor for concurrent crawling
        with ThreadPoolExecutor(max_workers=threads) as executor:
            for url in current_urls:
                # Skip if already visited
                if url in already_visited:
                    continue
                
                # Add delay to avoid overloading the server
                time.sleep(delay)
                
                # Process the page
                executor.submit(process_page, url, output_path, selenium, camoufox, current_depth, depth)
        
        current_depth += 1
    
    # Summary
    logger.info("Crawling completed!")
    logger.info(f"Downloaded {resource_count['html']} HTML files")
    logger.info(f"Downloaded {resource_count['images']} images")
    logger.info(f"Downloaded {resource_count['videos']} videos")
    
    if failed_urls:
        logger.warning(f"Failed to process {len(failed_urls)} URLs")
        with open(output_path / "failed_urls.txt", "w") as f:
            for url in failed_urls:
                f.write(f"{url}\n")
        logger.info(f"Failed URLs saved to {output_path}/failed_urls.txt")

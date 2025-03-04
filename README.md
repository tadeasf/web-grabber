# Web Grabber

A powerful CLI tool for crawling websites and downloading content including HTML, images, and videos. Web Grabber offers multiple browsing modes including normal requests, Selenium for JavaScript rendering, and camoufox for anti-bot protection.

## Features

- **Complete Website Crawling**: Download all HTML pages, images, and videos from a website
- **Interactive Mode**: Choose where to save content with path completion
- **Automatic Directory Naming**: Automatically creates directories named after the website domain
- **Anti-Bot Protection**: Use camoufox to avoid detection by anti-bot mechanisms
- **Tor Integration**: Route traffic through Tor network for anonymity
- **Selenium Support**: Render JavaScript for dynamic websites
- **Multi-threaded Downloading**: Efficiently download resources in parallel
- **Targeted Scraping**: Extract specific elements using CSS selectors

## Installation

### Using Rye (Recommended)

```bash
# Clone the repository
git clone https://github.com/tadeasf/web-grabber.git
cd web-grabber

# Install with Rye
rye sync
rye build
pip install dist/*.whl
```

### Alternative: Standard pip installation

```bash
# Clone the repository
git clone https://github.com/tadeasf/web-grabber.git
cd web-grabber

# Install dependencies and package
pip install .
```

## Usage

Once installed, you can use the `web-grabber` command directly from your terminal:

### Basic Website Crawling

Download an entire website including all HTML, images, and videos:

```bash
web-grabber grab https://example.com
```

Web Grabber will interactively prompt you where to save the content, with the domain name as the default directory.

For non-interactive usage with explicit output directory:

```bash
web-grabber grab https://example.com --output-dir ./example_site --non-interactive
```

Alternatively, you can run the module directly:

```bash
python -m web_grabber grab https://example.com
```

### Options for `grab` Command

- `url`: URL of the website to crawl
- `--output-dir PATH`: Directory to save downloaded content (defaults to domain name if not specified)
- `--non-interactive`: Run in non-interactive mode (no prompts)
- `--depth INT`: Maximum crawl depth (default: 100, effectively unlimited for most sites)
- `--tor`: Route traffic through Tor network
- `--selenium`: Use Selenium for JavaScript rendered content
- `--camoufox`: Use camoufox for anti-bot protection (overrides --selenium)
- `--threads INT`: Number of concurrent threads for crawling (default: 5)
- `--delay FLOAT`: Delay between requests in seconds (default: 0.5)
- `--timeout INT`: Request timeout in seconds (default: 30)
- `--user-agent TEXT`: Custom user agent string
- `--verbose`: Enable verbose logging

### Targeted Scraping

Extract specific elements from a website using CSS selectors:

```bash
web-grabber scrape https://example.com --selector "div.product" --output-file products.json
```

### Options for `scrape` Command

- `url`: URL of the website to scrape
- `--selector TEXT`: CSS selector to extract specific elements
- `--output-file PATH`: Output file for scraped data (default: scraped_data.json)
- `--format TEXT`: Output format (json, csv, txt) (default: json)
- `--tor`: Route traffic through Tor network
- `--selenium`: Use Selenium for JavaScript rendered content
- `--camoufox`: Use camoufox for anti-bot protection (overrides --selenium)
- `--user-agent TEXT`: Custom user agent string
- `--verbose`: Enable verbose logging

## Anti-Bot Protection

Web Grabber offers anti-bot protection using camoufox, which helps avoid detection by implementing browser fingerprint spoofing techniques:

```bash
web-grabber grab https://example.com --camoufox
```

## Tor Integration

Route your traffic through the Tor network for anonymity:

```bash
# Make sure Tor is running on 127.0.0.1:9050
web-grabber grab https://example.com --tor
```

## Examples

### Interactive mode with automatic domain-based directory

```bash
web-grabber grab https://example.com
# Will interactively prompt with default directory "example.com"
```

### Download a website with JavaScript rendering

```bash
web-grabber grab https://example.com --selenium --depth 3
```

### Non-interactive mode with explicit output directory

```bash
web-grabber grab https://example.com --output-dir ./custom_folder --non-interactive
```

### Scrape product information with anti-bot protection

```bash
web-grabber scrape https://example.com/products --selector ".product-card" --camoufox
```

### Anonymous crawling with Tor

```bash
web-grabber grab https://example.com --tor --delay 1.0
```

## Requirements

- Python 3.8+
- Required dependencies (automatically installed):
  - prompt-toolkit (for interactive CLI features)
  - camoufox[geoip] (for anti-bot protection)
  - typer (for CLI interface)
  - selenium (for JavaScript rendering)
- Tor (optional, for anonymous browsing)
- Chrome/Chromium (for Selenium and camoufox modes)

## License

This project is licensed under the GPL-3.0 License - see the LICENSE file for details.

# Advanced AI-Powered Web Scraper

A powerful web scraper that can extract valid mobile numbers and email addresses from websites based on keywords, with advanced anti-detection capabilities and proxy rotation.

## Features

- **Multiple Scraping Methods**: Uses both requests and Selenium for maximum coverage
- **Proxy Rotation**: Supports authenticated proxies with automatic rotation
- **Anti-Bot Detection**:
  - Browser fingerprint spoofing
  - User agent randomization
  - Human-like behavior simulation
  - CDP spoofing via Selenium
  - Stealth mode capabilities
- **CAPTCHA Handling**: Detection and solving capabilities (API integration)
- **Contact Extraction**:
  - Robust regex patterns for different country formats
  - Email and phone validation
  - Filtering against disposable domains and spam TLDs
- **Intelligent Crawling**:
  - URL relevance scoring
  - Contact page prioritization
  - Domain filtering
  - Concurrent processing
- **Multiple Interfaces**:
  - Command-line interface
  - HTTP REST API
  - Python library integration
- **Deployment Ready**:
  - Docker and docker-compose support
  - Configurable logging
  - Result caching

## Installation

### Prerequisites

- Python 3.8+
- Chrome/Chromium browser
- Selenium WebDriver

### Basic Installation

```bash
# Clone the repository
git clone [repository-url]
cd [repository-directory]

# Install dependencies
pip install -r requirements-scraper.txt
```

### Docker Installation

```bash
# Generate Docker files
python -m data_miner.scrapper --create-docker

# Build and run with Docker Compose
docker-compose up -d
```

## Usage

### Command Line Interface

```bash
# Scrape contacts based on a keyword
python -m data_miner.scrapper --keyword "furniture manufacturers" --max-results 10 --max-depth 2

# Scrape contacts from a specific domain
python -m data_miner.scrapper --domain example.com --max-depth 3

# Using proxies
python -m data_miner.scrapper --keyword "software development" --proxies proxies.json

# Run in debug mode
python -m data_miner.scrapper --keyword "custom packaging" --debug
```

### API Server

```bash
# Start the API server
python -m data_miner.scrapper --api --api-port 5000
```

#### API Endpoints

- `GET /health`: Health check endpoint
- `POST /scrape`: Scrape contacts
  ```json
  // Example request
  {
    "keyword": "electronics suppliers",
    "max_depth": 2,
    "max_results": 5
  }
  
  // OR
  
  {
    "domain": "example.com",
    "max_depth": 3
  }
  ```

### Python Library

```python
from data_miner.scrapper import AdvancedWebScraper

# Initialize the scraper
scraper = AdvancedWebScraper(
    headless=True,
    max_concurrent_threads=5,
    timeout=30,
    max_retries=3
)

# Scrape by keyword
results = scraper.search_and_scrape("air purifier manufacturers", max_results=5, max_depth=2)

# Scrape by domain
contacts = scraper.scrape_by_domain("example.com", max_depth=2)

# Save results
output_path = scraper.save_results(results, "contacts.json")
```

## Configuration

### Proxy Configuration

Create a JSON file with proxy settings:

```json
[
  {
    "http": "http://username:password@proxy1.example.com:8080",
    "https": "http://username:password@proxy1.example.com:8080"
  },
  {
    "http": "http://username:password@proxy2.example.com:8080",
    "https": "http://username:password@proxy2.example.com:8080"
  }
]
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--keyword` | Keyword to search for websites | - |
| `--domain` | Specific domain to scrape | - |
| `--output` | Output file path (JSON) | Auto-generated |
| `--proxies` | Path to JSON file with proxy list | None |
| `--captcha-api` | API key for CAPTCHA solving service | None |
| `--headless` | Run in headless mode | False |
| `--max-depth` | Maximum crawl depth | 2 |
| `--max-results` | Maximum number of domains to scrape | 5 |
| `--timeout` | Request timeout in seconds | 30 |
| `--max-retries` | Maximum number of retries | 3 |
| `--threads` | Maximum number of concurrent threads | 5 |
| `--debug` | Enable debug mode | False |
| `--cache-dir` | Directory to cache results | None |
| `--api` | Run as API server | False |
| `--api-host` | API server host | 0.0.0.0 |
| `--api-port` | API server port | 5000 |
| `--create-docker` | Create Docker files for deployment | False |

## Output Format

The scraper produces JSON files with the following structure:

```json
{
  "query": "furniture manufacturers",
  "domains": ["domain1.com", "domain2.com", "domain3.com"],
  "domain_results": {
    "domain1.com": {
      "emails": ["contact@domain1.com", "sales@domain1.com"],
      "phones": ["+1234567890", "+0987654321"]
    },
    "domain2.com": {
      "emails": ["info@domain2.com"],
      "phones": ["+1122334455"]
    }
  },
  "all_emails": ["contact@domain1.com", "sales@domain1.com", "info@domain2.com"],
  "all_phones": ["+1234567890", "+0987654321", "+1122334455"],
  "timestamp": "2023-04-15T14:32:22.123456"
}
```

## License

[MIT License](LICENSE)

## Disclaimer

This tool is intended for legitimate business purposes such as lead generation and market research. Please use responsibly and adhere to websites' terms of service and applicable laws regarding data scraping. 
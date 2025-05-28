# Data Miner - SerpAPI Integration

This module integrates SerpAPI with the data miner module to scrape email addresses and phone numbers from search results.

## Features

- Uses SerpAPI to perform Google searches and extract emails and phone numbers
- Optimizes search queries using Google Gemini API
- Supports various countries and search parameters
- Handles rate limiting and retries for robust scraping
- Validates data to filter out false positives
- Integrates with the existing data miner interface

## Usage

### Frontend Usage

1. Navigate to the Data Miner page
2. Enter a keyword related to the businesses you want to find contact information for
3. Select the country for targeting search results
4. Choose data type: "Phone Numbers" or "Email Addresses"
5. Click "Get" to start the scraping process
6. The system will automatically use SerpAPI to search for the information and extract the data

### API Integration

You can also use the SerpAPI scraper programmatically:

```python
from data_miner.scrap import scrape_with_serpapi

# Scrape emails for digital marketing companies in India
results = scrape_with_serpapi(
    keyword="digital marketing company",
    data_type="email",
    country="IN",
    max_results=50
)

# Print the results
for email in results['results']:
    print(email)
```

## Configuration

To configure the SerpAPI integration, edit the settings in `data_miner/settings.py`:

- `SERPAPI_KEY`: Your SerpAPI key
- `GEMINI_API_KEY`: Your Google Gemini API key for query optimization
- `DEFAULT_MAX_RESULTS`: Default maximum number of results to return
- `DEFAULT_MAX_PAGES`: Default maximum number of search result pages to process
- `DEFAULT_TIMEOUT`: Timeout for HTTP requests in seconds
- `SCRAPING_DELAY`: Delay between requests to avoid rate limiting
- `MAX_RETRIES`: Maximum number of retries for failed requests
- `MIN_PHONE_LENGTH`: Minimum length for a valid phone number
- `MAX_DOMAIN_LENGTH`: Maximum length for a valid email domain

## Google Gemini Integration

The scraper uses Google Gemini to optimize search queries for better results. To enable this feature:

1. Get a Google Gemini API key from [Google AI Studio](https://ai.google.dev/)
2. Add your key to `data_miner/settings.py`:

```python
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
```

If no API key is provided, the system will use a simple rule-based query optimizer instead.

## Dependencies

- SerpAPI: For Google search results
- Beautiful Soup: For HTML parsing
- Google Generative AI: For query optimization (optional)
- Requests: For HTTP requests 
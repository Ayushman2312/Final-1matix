import requests
import json
import re
import time
import random
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import argparse
import os
from typing import List, Dict, Any, Tuple
import logging
from fake_useragent import UserAgent
import google.generativeai as genai

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WebScraper:
    def __init__(self, serp_api_key: str, google_ai_api_key: str):
        """
        Initialize the WebScraper with API keys.
        
        Args:
            serp_api_key: API key for the SERP API
            google_ai_api_key: API key for Google Generative AI
        """
        self.serp_api_key = "934b601b0908067948a53616306c790179658a297a2e103379a55d09e7b75a7c"
        self.google_ai_api_key = "AIzaSyDsXH-_ftI5xn4aWfkwpw__4ixUMs7a7fM"
        self.user_agent = UserAgent()
        
        # Configure Google Generative AI
        genai.configure(api_key=google_ai_api_key)

    def optimize_search_query(self, keyword: str) -> str:
        """
        Optimize the user input keyword using Google Generative AI.
        
        Args:
            keyword: The original search keyword
            
        Returns:
            Optimized search query
        """
        try:
            model = genai.GenerativeModel('gemini-1.0-pro')
            prompt = f"""
            Convert the following keyword into an optimized Google search query to find pages 
            containing business contact information including emails and phone numbers:
            
            Keyword: {keyword}
            
            Return only the optimized search query without any additional text.
            """
            
            response = model.generate_content(prompt)
            optimized_query = response.text.strip()
            logger.info(f"Optimized query: '{optimized_query}' from original: '{keyword}'")
            return optimized_query
        except Exception as e:
            logger.error(f"Error optimizing search query: {e}")
            # Fallback to original keyword with some basic optimization
            return f"{keyword} contact email phone"

    def get_search_results(self, query: str, num_results: int = 10) -> List[str]:
        """
        Get search results from SERP API.
        
        Args:
            query: The search query
            num_results: Number of search results to fetch
            
        Returns:
            List of URLs from search results
        """
        try:
            logger.info(f"Fetching search results for query: '{query}'")
            params = {
                "api_key": self.serp_api_key,
                "q": query,
                "num": num_results * 3,  # Fetch more results to ensure we have enough valid URLs
                "tbm": "search"
            }
            
            response = requests.get("https://serpapi.com/search", params=params)
            if response.status_code != 200:
                logger.error(f"SERP API error: {response.status_code}, {response.text}")
                return []
            
            results = response.json()
            
            urls = []
            if "organic_results" in results:
                for result in results["organic_results"]:
                    if "link" in result:
                        urls.append(result["link"])
            
            logger.info(f"Found {len(urls)} URLs from search results")
            return urls[:num_results]
        except Exception as e:
            logger.error(f"Error fetching search results: {e}")
            return []

    def extract_emails_and_phones(self, html_content: str) -> Tuple[List[str], List[str]]:
        """
        Extract emails and phone numbers from HTML content.
        
        Args:
            html_content: HTML content of the webpage
            
        Returns:
            Tuple of (list of emails, list of phone numbers)
        """
        # Email regex pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        
        # Phone regex patterns (supports various formats)
        phone_patterns = [
            r'\b(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',  # (123) 456-7890, 123-456-7890
            r'\b(?:\+\d{1,3}[-.\s]?)?\d{3}[-.\s]?\d{2}[-.\s]?\d{2}[-.\s]?\d{2}\b',  # Different international formats
            r'\b(?:\+\d{1,3}[-.\s]?)?\d{5}[-.\s]?\d{6}\b',  # Some international formats
            r'\b\d{10}\b'  # Plain 10 digits
        ]
        
        # Extract emails
        emails = re.findall(email_pattern, html_content)
        
        # Extract phone numbers
        phones = []
        for pattern in phone_patterns:
            phones.extend(re.findall(pattern, html_content))
        
        # Filter out common false positives
        filtered_emails = [
            email for email in emails 
            if not any(domain in email.lower() for domain in [
                'example.com', 'domain.com', 'email.com', 'yourdomain.com'
            ])
        ]
        
        # Remove duplicates and sort
        filtered_emails = sorted(list(set(filtered_emails)))
        phones = sorted(list(set(phones)))
        
        return filtered_emails, phones

    def scrape_url(self, url: str) -> Tuple[List[str], List[str]]:
        """
        Scrape a URL for emails and phone numbers.
        
        Args:
            url: URL to scrape
            
        Returns:
            Tuple of (list of emails, list of phone numbers)
        """
        try:
            logger.info(f"Scraping URL: {url}")
            
            # Add anti-bot detection measures
            headers = {
                'User-Agent': self.user_agent.random,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.google.com/',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            # Add random delay between requests to avoid detection
            time.sleep(random.uniform(1, 3))
            
            # Make the request
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch URL {url}: {response.status_code}")
                return [], []
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract text content
            text_content = soup.get_text(" ", strip=True)
            
            # Also check the HTML for emails/phones that might be in attributes
            html_content = str(soup)
            
            # Extract emails and phones from both text and HTML
            emails_text, phones_text = self.extract_emails_and_phones(text_content)
            emails_html, phones_html = self.extract_emails_and_phones(html_content)
            
            # Combine results
            all_emails = list(set(emails_text + emails_html))
            all_phones = list(set(phones_text + phones_html))
            
            logger.info(f"Found {len(all_emails)} emails and {len(all_phones)} phone numbers from {url}")
            return all_emails, all_phones
            
        except Exception as e:
            logger.error(f"Error scraping URL {url}: {e}")
            return [], []

    def scrape_data(self, keyword: str, num_data: int) -> Dict[str, Any]:
        """
        Main method to scrape data based on keyword.
        
        Args:
            keyword: Search keyword
            num_data: Number of emails and phone numbers to collect
            
        Returns:
            Dictionary with scraped data
        """
        # Step 1: Optimize the search query
        optimized_query = self.optimize_search_query(keyword)
        
        # Step 2: Get search results from SERP API
        urls = self.get_search_results(optimized_query, num_results=min(num_data, 20))
        
        # Step 3: Scrape each URL for emails and phone numbers
        all_emails = []
        all_phones = []
        
        for url in urls:
            if len(all_emails) >= num_data and len(all_phones) >= num_data:
                break
            
            emails, phones = self.scrape_url(url)
            
            # Add unique emails and phones
            for email in emails:
                if email not in all_emails:
                    all_emails.append(email)
            
            for phone in phones:
                if phone not in all_phones:
                    all_phones.append(phone)
                    
            logger.info(f"Progress: {len(all_emails)}/{num_data} emails, {len(all_phones)}/{num_data} phones")
            
            # Implement polite crawling with random delays
            time.sleep(random.uniform(2, 5))
        
        # Truncate results to requested number
        final_emails = all_emails[:num_data]
        final_phones = all_phones[:num_data]
        
        # Prepare the result
        result = {
            "keyword": keyword,
            "optimized_query": optimized_query,
            "urls_scraped": urls,
            "emails": final_emails,
            "phones": final_phones,
            "stats": {
                "emails_found": len(final_emails),
                "phones_found": len(final_phones),
                "urls_scraped": len(urls)
            }
        }
        
        return result

def main():
    parser = argparse.ArgumentParser(description='Web scraper for emails and phone numbers')
    parser.add_argument('--keyword', type=str, required=True, help='Search keyword')
    parser.add_argument('--num_data', type=int, default=30, help='Number of emails and phone numbers to collect')
    parser.add_argument('--output', type=str, default='results.json', help='Output JSON file')
    args = parser.parse_args()
    
    # Get API keys from environment variables
    serp_api_key = os.environ.get('SERP_API_KEY')
    google_ai_api_key = os.environ.get('GOOGLE_AI_API_KEY')
    
    if not serp_api_key or not google_ai_api_key:
        logger.error("API keys not found. Please set SERP_API_KEY and GOOGLE_AI_API_KEY environment variables.")
        return
    
    # Initialize the scraper
    scraper = WebScraper(serp_api_key, google_ai_api_key)
    
    # Scrape data
    result = scraper.scrape_data(args.keyword, args.num_data)
    
    # Save results to JSON file
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Results saved to {args.output}")
    
    # Print summary
    print(f"\nScraping Summary:")
    print(f"Keyword: {args.keyword}")
    print(f"Optimized Query: {result['optimized_query']}")
    print(f"Emails found: {result['stats']['emails_found']}/{args.num_data}")
    print(f"Phones found: {result['stats']['phones_found']}/{args.num_data}")
    print(f"URLs scraped: {result['stats']['urls_scraped']}")
    print(f"Results saved to: {args.output}")

if __name__ == "__main__":
    main()
#!/usr/bin/env python
"""
Test script for the web scraper to verify improvements
"""

import time
import sys
import os

try:
    from web_scrapper import ContactScraper
except ImportError:
    print("Error importing ContactScraper. Make sure web_scrapper.py is in the same directory.")
    sys.exit(1)

def test_search_google():
    """Test the Google search functionality."""
    print("=" * 50)
    print("TESTING GOOGLE SEARCH")
    print("=" * 50)
    
    scraper = ContactScraper(debug_mode=True)
    
    # Test with a simple query
    keyword = "hotels in mumbai"
    print(f"Searching for: {keyword}")
    
    try:
        urls = scraper.search_google(keyword, num_results=5)
        print(f"Found {len(urls)} URLs:")
        for i, url in enumerate(urls):
            print(f"{i+1}. {url}")
    except Exception as e:
        print(f"Error in Google search: {e}")
    
    return

def test_browser_search():
    """Test the browser-based search functionality."""
    print("=" * 50)
    print("TESTING BROWSER SEARCH")
    print("=" * 50)
    
    scraper = ContactScraper(debug_mode=True)
    
    # Test with a simple query
    keyword = "hotels in pune"
    print(f"Searching with browser for: {keyword}")
    
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Initialize browser
        browser_initialized = loop.run_until_complete(scraper.initialize_browser())
        
        if browser_initialized:
            # Perform search
            results = loop.run_until_complete(scraper._search_google_with_browser(keyword, 5))
            
            # Close browser
            loop.run_until_complete(scraper.close_browser())
            
            # Print results
            print(f"Found {len(results)} URLs with browser:")
            for i, url in enumerate(results):
                print(f"{i+1}. {url}")
        else:
            print("Failed to initialize browser")
    except Exception as e:
        print(f"Error in browser search: {e}")
    
    return

def test_extract_urls():
    """Test URL extraction from search results."""
    print("=" * 50)
    print("TESTING URL EXTRACTION")
    print("=" * 50)
    
    scraper = ContactScraper(debug_mode=True)
    
    # Test with a simple query
    keyword = "restaurants in delhi"
    print(f"Extracting URLs for: {keyword}")
    
    try:
        urls = scraper.extract_urls_from_search_query(keyword, num_results=5)
        print(f"Extracted {len(urls)} URLs:")
        for i, url in enumerate(urls):
            print(f"{i+1}. {url}")
    except Exception as e:
        print(f"Error in URL extraction: {e}")
    
    return

def test_contact_extraction():
    """Test contact extraction from URLs."""
    print("=" * 50)
    print("TESTING CONTACT EXTRACTION")
    print("=" * 50)
    
    scraper = ContactScraper(debug_mode=True)
    
    # Test URLs
    test_urls = [
        "https://www.tajhotels.com/",
        "https://www.oberoihotels.com/"
    ]
    
    for url in test_urls:
        print(f"Extracting contacts from: {url}")
        
        try:
            emails, phones = scraper.extract_contacts_from_url(url)
            print(f"Found {len(emails)} emails and {len(phones)} phones:")
            
            if emails:
                for email in emails:
                    print(f"Email: {email}")
            
            if phones:
                for phone in phones:
                    if isinstance(phone, dict):
                        print(f"Phone: {phone['number']} ({phone['source']})")
                    else:
                        print(f"Phone: {phone}")
        except Exception as e:
            print(f"Error extracting contacts: {e}")
    
    return

def main():
    """Main entry point for testing."""
    print("=" * 50)
    print("WEB SCRAPER TEST SCRIPT")
    print("=" * 50)
    
    # Start with basic search test
    test_search_google()
    
    # Test browser search (if available)
    try:
        import playwright
        test_browser_search()
    except ImportError:
        print("Playwright not available, skipping browser tests")
    
    # Test URL extraction
    test_extract_urls()
    
    # Test contact extraction
    test_contact_extraction()
    
    print("=" * 50)
    print("TEST COMPLETE")
    print("=" * 50)

if __name__ == "__main__":
    main() 
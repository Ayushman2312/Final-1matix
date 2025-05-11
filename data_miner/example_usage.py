#!/usr/bin/env python3
"""
Example usage of the Advanced Web Scraper.
This demonstrates various ways to use the scraper for extracting contact information.
"""

import json
import os
from scrapper import AdvancedWebScraper

def example_keyword_search():
    """Example of searching and scraping based on a keyword."""
    print("\n--- Example: Keyword Search ---")
    
    # Initialize scraper
    scraper = AdvancedWebScraper(
        headless=True,
        max_concurrent_threads=3,
        timeout=20,
        max_retries=2,
        debug=True
    )
    
    # Search and scrape for a keyword
    keyword = "office furniture suppliers"
    print(f"Searching for: {keyword}")
    
    results = scraper.search_and_scrape(
        keyword=keyword,
        max_results=3,  # Limit to 3 domains for the example
        max_depth=1     # Shallow crawl for the example
    )
    
    # Print results
    if 'error' in results:
        print(f"Error: {results['error']}")
    else:
        print(f"Found {len(results['domains'])} domains:")
        for domain in results['domains']:
            print(f"  - {domain}")
        
        print(f"\nFound {len(results['all_emails'])} emails:")
        for email in results['all_emails']:
            print(f"  - {email}")
        
        print(f"\nFound {len(results['all_phones'])} phone numbers:")
        for phone in results['all_phones']:
            print(f"  - {phone}")
        
        # Save results
        output_path = scraper.save_results(results, "keyword_search_results.json")
        print(f"\nResults saved to: {output_path}")

def example_domain_scrape():
    """Example of scraping a specific domain."""
    print("\n--- Example: Domain Scraping ---")
    
    # Initialize scraper
    scraper = AdvancedWebScraper(
        headless=True,
        max_concurrent_threads=3,
        timeout=20,
        max_retries=2,
        debug=True
    )
    
    # Scrape a specific domain
    domain = "example.com"  # Replace with a domain you want to scrape
    print(f"Scraping domain: {domain}")
    
    results = scraper.scrape_by_domain(
        domain=domain,
        max_depth=2
    )
    
    # Print results
    print(f"Found {len(results['emails'])} emails:")
    for email in results['emails']:
        print(f"  - {email}")
    
    print(f"\nFound {len(results['phones'])} phone numbers:")
    for phone in results['phones']:
        print(f"  - {phone}")
    
    # Save results
    output_path = scraper.save_results(
        {"domain": domain, "results": results},
        "domain_scrape_results.json"
    )
    print(f"\nResults saved to: {output_path}")

def example_with_proxies():
    """Example of using the scraper with proxies."""
    print("\n--- Example: Using Proxies ---")
    
    # Sample proxy list (replace with actual proxies)
    proxy = 'geo.iproyal.com:12321'
    proxy_auth = 'vnkl9BGvMRlmvWfO:EjFoKHcjcchVYwZ9_country-in'
    proxies = {
    'http': f'http://{proxy_auth}@{proxy}',
    'https': f'http://{proxy_auth}@{proxy}'
    }

    proxies = [i for i in proxies]
    
    # Save proxies to a file for demonstration
    with open("sample_proxies.json", "w") as f:
        json.dump(proxies, f, indent=2)
    
    print("Using proxy configuration from sample_proxies.json")
    print("Note: Replace with actual proxies for production use")
    
    # Initialize scraper with proxies
    scraper = AdvancedWebScraper(
        proxies=proxies,
        headless=True,
        max_concurrent_threads=3,
        timeout=20,
        max_retries=2,
        debug=True
    )
    
    # Scrape a domain using proxies
    domain = "example.org"  # Replace with a domain you want to scrape
    print(f"Scraping domain with proxies: {domain}")
    
    results = scraper.scrape_by_domain(
        domain=domain,
        max_depth=1
    )
    
    # Print results summary
    print(f"Found {len(results['emails'])} emails and {len(results['phones'])} phone numbers")

def example_api_client():
    """Example of using the scraper via its API."""
    print("\n--- Example: API Client ---")
    
    import requests
    
    # API endpoint (assuming the API server is running)
    api_url = "http://localhost:5000/scrape"
    
    # Prepare request data
    data = {
        "keyword": "digital marketing agency",
        "max_depth": 1,
        "max_results": 2
    }
    
    print(f"Sending API request to {api_url}")
    print(f"Request data: {json.dumps(data, indent=2)}")
    
    # Make the request
    try:
        response = requests.post(api_url, json=data, timeout=300)
        
        if response.status_code == 200:
            results = response.json()
            print("\nAPI Response:")
            print(f"Found {len(results.get('all_emails', []))} emails and "
                  f"{len(results.get('all_phones', []))} phone numbers "
                  f"from {len(results.get('domains', []))} domains")
            
            # Save results
            with open("api_results.json", "w") as f:
                json.dump(results, f, indent=2)
            print("\nResults saved to: api_results.json")
        else:
            print(f"API error ({response.status_code}): {response.text}")
    
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        print("\nNote: Make sure the API server is running using:")
        print("python -m data_miner.scrapper --api")

def main():
    """Run example scripts."""
    print("Advanced Web Scraper Examples")
    print("============================")
    
    # Create examples directory
    os.makedirs("examples", exist_ok=True)
    os.chdir("examples")
    
    # Ask user which example to run
    print("\nAvailable examples:")
    print("1. Keyword Search")
    print("2. Domain Scraping")
    print("3. Using Proxies")
    print("4. API Client")
    print("5. Run All Examples")
    
    choice = input("\nSelect an example to run (1-5): ")
    
    if choice == "1":
        example_keyword_search()
    elif choice == "2":
        example_domain_scrape()
    elif choice == "3":
        example_with_proxies()
    elif choice == "4":
        example_api_client()
    elif choice == "5":
        example_keyword_search()
        example_domain_scrape()
        example_with_proxies()
        example_api_client()
    else:
        print("Invalid choice. Please select a number between 1 and 5.")

if __name__ == "__main__":
    main() 
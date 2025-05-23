#!/usr/bin/env python
"""
Script to run the web scraper with improved Google search functionality.
This demonstrates the enhanced anti-detection capabilities.
"""

import sys
import os
import time
import argparse
from pprint import pprint

# Import our web scraper
try : 
    from data_miner.web_scrapper import ContactScraper
except ImportError:
    from web_scrapper import ContactScraper

def main():
    """Run the web scraper with command line arguments."""
    parser = argparse.ArgumentParser(description="Run web scraper with improved Google search functionality")
    parser.add_argument("query", help="Search query to use")
    parser.add_argument("--results", type=int, default=10, help="Number of results to retrieve (default: 10)")
    parser.add_argument("--timeout", type=int, default=10, help="Maximum runtime in minutes (default: 10)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    print(f"\n{'='*70}")
    print(f"   Running improved web scraper for query: '{args.query}'")
    print(f"{'='*70}")
    
    # Create scraper instance
    scraper = ContactScraper(use_browser=True, debug_mode=args.debug)
    
    start_time = time.time()
    print(f"Starting search at {time.strftime('%H:%M:%S')}")
    
    try:
        # Run the scraper with the given query
        result = scraper.scrape(
            keyword=args.query,
            num_results=args.results,
            max_runtime_minutes=args.timeout
        )
        
        # Display results
        run_time = time.time() - start_time
        
        print(f"\n{'='*70}")
        print(f"   Search Results for '{args.query}'")
        print(f"{'='*70}")
        print(f"Found {len(result['emails'])} emails and {len(result['phones'])} phone numbers")
        print(f"Search completed in {run_time:.2f} seconds")
        
        # Display emails
        if result['emails']:
            print("\nEmails found:")
            for email in result['emails']:
                print(f"  • {email}")
        else:
            print("\nNo emails found")
        
        # Display phones
        if result['phones']:
            print("\nPhones found:")
            for phone in result['phones']:
                if isinstance(phone, dict):
                    print(f"  • {phone.get('phone', '')} (from {phone.get('source', 'unknown')})")
                else:
                    print(f"  • {phone}")
        else:
            print("\nNo phones found")
            
        print(f"\nCSV file saved to: {result['task_info'].get('csv_filename', 'N/A')}")
        
    except KeyboardInterrupt:
        print("\nSearch interrupted by user")
    except Exception as e:
        print(f"Error during search: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close browser resources
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(scraper.close_browser())
                print("Browser resources closed")
            finally:
                loop.close()
        except Exception as e:
            print(f"Error closing browser resources: {e}")
    
    print("\nDone!")

if __name__ == "__main__":
    main() 
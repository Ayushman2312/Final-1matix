#!/usr/bin/env python
import sys
import os
import traceback
import argparse

# Add the parent directory to sys.path if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test the Google search functionality')
    parser.add_argument('--keyword', type=str, required=True, help='Keyword to search for')
    parser.add_argument('--limit', type=int, default=10, help='Maximum number of results to return')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()
    
    print(f"🔍 Testing search for '{args.keyword}', targeting {args.limit} results")
    
    print("Importing GoogleBrowserSearch...")
    from data_miner.google_browser_search import search_google
    
    # Run the search using the synchronous wrapper
    print(f"🔎 Searching Google for: {args.keyword}")
    results = search_google(
        query=args.keyword,
        num_results=args.limit,
        page=0,
        debug_mode=args.debug
    )
    
    # Print results
    print(f"\n✅ Found {len(results)} results:")
    for i, url in enumerate(results, 1):
        print(f"{i}. {url}")
    
    print("\nTest completed successfully!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    traceback.print_exc() 
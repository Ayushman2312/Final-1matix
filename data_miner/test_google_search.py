#!/usr/bin/env python
import sys
import os
import time
from pprint import pprint

# Import the search function
from google_browser_search import search_google

def test_search():
    """Test the Google search functionality with different queries"""
    print("Starting Google search test...")
    
    # Define test queries
    test_queries = [
        "digital marketing agency in India",
        "digital marketing companies in bangalore"
    ]
    
    # Create debug_html directory if it doesn't exist
    os.makedirs("debug_html", exist_ok=True)
    
    # Run tests for each query
    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"Testing query: '{query}'")
        print(f"{'='*50}")
        
        start_time = time.time()
        
        try:
            # Run the search with a timeout
            results = search_google(query, num_results=5, debug_mode=True)
            
            # Print results
            print(f"\nFound {len(results)} results in {time.time() - start_time:.2f} seconds:")
            for i, url in enumerate(results, 1):
                print(f"{i}. {url}")
                
        except Exception as e:
            print(f"Error during search: {e}")
            import traceback
            traceback.print_exc()
            
        print(f"\nTest completed in {time.time() - start_time:.2f} seconds")
        
    print("\nAll tests completed!")

if __name__ == "__main__":
    test_search() 
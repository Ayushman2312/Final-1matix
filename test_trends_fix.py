#!/usr/bin/env python
import sys
import os
import logging
import time
import json
from trends.trends import get_trends_json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('trends_test.log')
    ]
)
logger = logging.getLogger("test_trends")

def test_trends_data():
    """Test fetching trends data with different parameters"""
    
    test_cases = [
        {
            "name": "Basic test - Bitcoin in India",
            "keywords": ["Bitcoin"],
            "timeframe": "today 1-y",
            "geo": "IN"
        },
        {
            "name": "Multiple keywords - shorter timeframe",
            "keywords": ["Bitcoin", "Ethereum"],
            "timeframe": "today 3-m",
            "geo": "US"
        },
        {
            "name": "Popular topic - very short timeframe",
            "keywords": ["AI"],
            "timeframe": "today 1-m",
            "geo": "IN"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases):
        logger.info(f"\n\nTest case {i+1}: {test_case['name']}")
        logger.info(f"Keywords: {test_case['keywords']}")
        logger.info(f"Timeframe: {test_case['timeframe']}")
        logger.info(f"Geo: {test_case['geo']}")
        
        start_time = time.time()
        
        try:
            # Get trends data
            trends_data = get_trends_json(
                keywords=test_case['keywords'],
                timeframe=test_case['timeframe'],
                geo=test_case['geo']
            )
            
            # Calculate time taken
            elapsed = time.time() - start_time
            
            # Check if we got time trends data
            time_trends = trends_data.get('data', {}).get('time_trends', [])
            has_data = len(time_trends) > 0
            
            logger.info(f"Time taken: {elapsed:.2f} seconds")
            logger.info(f"Status: {trends_data.get('status', 'unknown')}")
            logger.info(f"Got time trends data: {has_data}")
            logger.info(f"Number of data points: {len(time_trends)}")
            
            # Log any errors
            if trends_data.get('status') == 'error' or not has_data:
                logger.error(f"Errors: {trends_data.get('errors', [])}")
            
            # Add result to summary
            results.append({
                "test_case": test_case['name'],
                "success": has_data and trends_data.get('status') == 'success',
                "time_taken": elapsed,
                "data_points": len(time_trends)
            })
            
            # Save raw data for inspection
            with open(f"test_result_{i+1}.json", "w") as f:
                json.dump(trends_data, f, indent=2)
            
        except Exception as e:
            logger.error(f"Error running test case: {str(e)}")
            
            # Add failed result to summary
            results.append({
                "test_case": test_case['name'],
                "success": False,
                "error": str(e)
            })
        
        # Add delay between tests to avoid rate limiting
        time.sleep(10)
    
    # Print summary
    logger.info("\n\n=== TEST SUMMARY ===")
    for result in results:
        status = "✅ PASSED" if result.get('success') else "❌ FAILED"
        logger.info(f"{status} - {result['test_case']}")
        if result.get('success'):
            logger.info(f"  Time: {result.get('time_taken', 0):.2f}s, Data points: {result.get('data_points', 0)}")
        else:
            logger.info(f"  Error: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    logger.info("Starting trends module test")
    test_trends_data() 
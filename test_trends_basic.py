import sys
import os
import logging
import time
import json
from trends.trends import get_trends_json

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_basic")

def main():
    # Basic test with a popular keyword and short timeframe
    keyword = "Bitcoin"
    timeframe = "today 1-m"  # Short timeframe for better chance of success
    geo = "IN"
    
    logger.info(f"Fetching trends for '{keyword}' with timeframe {timeframe} in {geo}")
    
    start_time = time.time()
    
    # Get trends data
    result = get_trends_json(keyword, timeframe, geo)
    
    # Calculate time taken
    elapsed = time.time() - start_time
    logger.info(f"Request completed in {elapsed:.2f} seconds")
    
    # Check if we got time trends data
    time_trends = result.get('data', {}).get('time_trends', [])
    has_data = len(time_trends) > 0
    
    logger.info(f"Status: {result.get('status', 'unknown')}")
    logger.info(f"Has time trends data: {has_data}")
    logger.info(f"Number of data points: {len(time_trends)}")
    
    # Check for warnings or errors
    if "warning" in result:
        logger.warning(f"Warning: {result['warning']}")
    
    if result.get('status') == 'error':
        logger.error(f"Errors: {result.get('errors', [])}")
    
    # Save result to file for inspection
    with open("test_result.json", "w") as f:
        json.dump(result, f, indent=2)
    
    logger.info(f"Saved results to test_result.json")
    
    # Print a summary of the first few data points if available
    if has_data and len(time_trends) > 0:
        logger.info("Sample data points:")
        for i, point in enumerate(time_trends[:5]):
            logger.info(f"  {i+1}. Date: {point.get('date')}, Value: {point.get(keyword)}")
    
    return has_data

if __name__ == "__main__":
    logger.info("Starting basic trends test")
    success = main()
    
    if success:
        logger.info("✅ Test PASSED - Successfully retrieved trends data")
        sys.exit(0)
    else:
        logger.error("❌ Test FAILED - Could not retrieve trends data")
        sys.exit(1) 
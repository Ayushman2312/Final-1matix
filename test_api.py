#!/usr/bin/env python
"""
Simple test script to verify that our Google Trends fixes are working
"""
import time
import json
import logging
from trends import get_trends_json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_api")

def main():
    # Basic test parameters
    keyword = "Bitcoin"
    timeframe = "today 1-m"
    geo = "IN"
    
    logger.info(f"Testing get_trends_json with keyword={keyword}, timeframe={timeframe}, geo={geo}")
    
    # Time the API call
    start_time = time.time()
    result = get_trends_json(keyword, timeframe, geo)
    elapsed = time.time() - start_time
    
    # Get data points
    time_trends = result.get('data', {}).get('time_trends', [])
    data_count = len(time_trends)
    
    # Log results
    logger.info(f"API call completed in {elapsed:.2f} seconds")
    logger.info(f"Status: {result.get('status', 'unknown')}")
    logger.info(f"Data points: {data_count}")
    
    # Check for warnings
    if "warning" in result:
        logger.warning(f"Warning: {result['warning']}")
    
    # Save result to file
    with open("trends_test_result.json", "w") as f:
        json.dump(result, f, indent=2)
    logger.info("Saved results to trends_test_result.json")
    
    # Display sample data points
    if data_count > 0:
        logger.info("Sample data points:")
        for i, point in enumerate(time_trends[:5]):
            if isinstance(point, dict):
                date = point.get('date', 'unknown')
                value = point.get(keyword, 0)
                logger.info(f"  {i+1}. Date: {date}, Value: {value}")
    
    # Return success if we got data
    return data_count > 0

if __name__ == "__main__":
    success = main()
    print(f"\nTest {'PASSED' if success else 'FAILED'}: {'Data retrieved successfully' if success else 'No data retrieved'}")
    exit(0 if success else 1) 
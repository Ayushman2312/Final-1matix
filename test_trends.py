"""
Test script for trends module
"""
import sys
import logging
import json
from trends.trends import get_trends_json, fetch_google_trends_no_proxy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("test_trends")

def test_direct_connection():
    """Test the direct connection approach with original timeframe"""
    logger.info("Testing direct connection with 5-year timeframe")
    
    # Test with a simple keyword and 5-year timeframe
    result = fetch_google_trends_no_proxy(
        keywords="narendra modi",
        timeframe="today 5-y",  # Use 5-year timeframe
        geo="IN",
        analysis_options={
            "include_time_trends": True,
            "include_state_analysis": False,  # Simplify test
            "include_city_analysis": False,
            "include_related_queries": False
        }
    )
    
    # Print result summary
    logger.info(f"Status: {result['status']}")
    logger.info(f"Timeframe: {result['metadata']['timeframe']}")
    
    if result['status'] == 'success':
        time_trends = result.get('data', {}).get('time_trends', [])
        logger.info(f"Time trends data points: {len(time_trends)}")
        
        # Print a sample of the data
        if time_trends:
            logger.info(f"Sample data point: {time_trends[0]}")
            logger.info(f"First date: {time_trends[0].get('date', 'unknown')}")
            logger.info(f"Last date: {time_trends[-1].get('date', 'unknown')}")
        
        return True
    else:
        logger.error(f"Error: {result.get('errors', ['Unknown error'])}")
        return False

if __name__ == "__main__":
    success = test_direct_connection()
    if success:
        logger.info("Test completed successfully!")
    else:
        logger.error("Test failed!")
    
    sys.exit(0 if success else 1) 
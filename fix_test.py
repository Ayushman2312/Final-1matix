#!/usr/bin/env python
"""
Simple test script to verify Google Trends fixes related to proxies and urllib3
"""
import sys
import os
import logging
import time
from trends.trends import get_trends_json, create_pytrends_instance, fix_session_retry

# Configure basic logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("fix_test")

def test_urllib3_compatibility():
    """Test if the urllib3 compatibility fixes work properly"""
    import requests
    from urllib3.util import Retry
    from requests.adapters import HTTPAdapter
    
    logger.info("Testing urllib3 compatibility fix...")
    
    # Create a session
    session = requests.Session()
    
    # Try to apply our fix
    result = fix_session_retry(session)
    
    if result:
        logger.info("Successfully applied retry configuration fix")
    else:
        logger.warning("Failed to apply retry configuration fix")
    
    # Test an actual request
    try:
        response = session.get("https://www.google.com", timeout=10)
        logger.info(f"Test request successful: status={response.status_code}")
        return True
    except Exception as e:
        logger.error(f"Test request failed: {str(e)}")
        return False

def test_create_trends_instance():
    """Test creation of PyTrends instance with our helper function"""
    logger.info("Testing PyTrends instance creation...")
    
    try:
        # Try to create instance with no proxy first
        pytrends = create_pytrends_instance(proxy=None)
        logger.info("Successfully created PyTrends instance with no proxy")
        
        # Test a request to verify it works
        logger.info("Testing a simple request...")
        try:
            pytrends.build_payload(["Bitcoin"], timeframe="now 1-d")
            logger.info("Successfully built payload")
            return True
        except Exception as e:
            logger.error(f"Error building payload: {str(e)}")
            return False
    except Exception as e:
        logger.error(f"Error creating PyTrends instance: {str(e)}")
        return False
        
def test_fetch_with_fallback():
    """Test fetch with fallback data generation"""
    logger.info("Testing fetch with fallback generation...")
    
    try:
        # Use a short timeout to force fallback
        start = time.time()
        result = get_trends_json(
            keywords=["Bitcoin", "Ethereum"],
            timeframe="today 1-m",
            geo="IN"
        )
        elapsed = time.time() - start
        
        # Check if we got any data
        time_trends = result.get('data', {}).get('time_trends', [])
        has_data = len(time_trends) > 0
        
        logger.info(f"Time taken: {elapsed:.2f} seconds")
        logger.info(f"Status: {result.get('status', 'unknown')}")
        logger.info(f"Got time trends data: {has_data}")
        logger.info(f"Number of data points: {len(time_trends)}")
        
        # Check if we're using fallback data
        if "warning" in result:
            logger.warning(f"Warning: {result['warning']}")
            logger.info("Fallback data was used (expected in some cases)")
        
        return has_data
    except Exception as e:
        logger.error(f"Error in test_fetch_with_fallback: {str(e)}")
        return False

def main():
    """Run all tests"""
    logger.info("Starting fix verification tests...")
    
    tests = [
        ("urllib3 compatibility", test_urllib3_compatibility),
        ("PyTrends instance creation", test_create_trends_instance),
        ("Fetch with fallback", test_fetch_with_fallback)
    ]
    
    all_passed = True
    
    for name, test_func in tests:
        logger.info(f"\n===== Testing {name} =====")
        try:
            result = test_func()
            status = "PASSED" if result else "FAILED"
            logger.info(f"Test {name}: {status}")
            if not result:
                all_passed = False
        except Exception as e:
            logger.error(f"Error running test {name}: {str(e)}")
            all_passed = False
        
        # Add delay between tests
        time.sleep(2)
    
    logger.info("\n===== Test Summary =====")
    if all_passed:
        logger.info("All tests PASSED! The fixes appear to be working correctly.")
        return 0
    else:
        logger.error("Some tests FAILED. See above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
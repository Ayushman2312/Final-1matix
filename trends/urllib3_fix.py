"""
Standalone fix for urllib3 compatibility issues with the Google Trends module.
This script patches the TrendReq class in pytrends to correctly handle urllib3 version differences.
"""
import sys
import os
import logging
import importlib
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("urllib3_fix")

def apply_urllib3_fix():
    """
    Apply fixes for urllib3 compatibility issues by monkey patching the TrendReq class
    """
    try:
        # Import pytrends module
        from pytrends.request import TrendReq
        
        # Determine urllib3 version
        try:
            import importlib.metadata
            urllib3_version = importlib.metadata.version('urllib3')
        except (ImportError, AttributeError):
            import urllib3
            urllib3_version = getattr(urllib3, '__version__', '1.0.0')
        
        logger.info(f"Detected urllib3 version: {urllib3_version}")
        
        # Store the original __init__ method
        original_init = TrendReq.__init__
        
        # Define patched __init__ method
        def patched_init(self, hl='en-US', tz=360, geo='', timeout=(2, 5), proxies='',
                         retries=0, backoff_factor=0, requests_args=None):
            """
            Patched initializer for TrendReq that handles urllib3 version differences
            """
            # Call the original __init__ without retry parameters first
            original_init(self, hl=hl, tz=tz, geo=geo, timeout=timeout, 
                         proxies=proxies, retries=0, backoff_factor=0,
                         requests_args=requests_args)
            
            # Now correctly set up the retry mechanism based on urllib3 version
            try:
                if retries > 0:
                    # Create appropriate retry strategy based on version
                    if urllib3_version.startswith(('2.', '3.')):
                        # For urllib3 >= 2.0, use allowed_methods
                        retry_strategy = Retry(
                            total=retries,
                            backoff_factor=backoff_factor,
                            status_forcelist=[429, 500, 502, 503, 504],
                            allowed_methods=["HEAD", "GET", "OPTIONS"]
                        )
                        logger.debug("Using 'allowed_methods' parameter for Retry")
                    else:
                        # For urllib3 < 2.0, use method_whitelist
                        retry_strategy = Retry(
                            total=retries,
                            backoff_factor=backoff_factor,
                            status_forcelist=[429, 500, 502, 503, 504],
                            method_whitelist=["HEAD", "GET", "OPTIONS"]
                        )
                        logger.debug("Using 'method_whitelist' parameter for Retry")
                    
                    # Apply retry strategy to session
                    adapter = HTTPAdapter(max_retries=retry_strategy)
                    self.requests_session.mount("https://", adapter)
                    self.requests_session.mount("http://", adapter)
                    logger.debug("Applied retry configuration to session")
            except Exception as e:
                logger.warning(f"Failed to apply retry configuration: {str(e)}")
        
        # Replace the original __init__ with our patched version
        TrendReq.__init__ = patched_init
        
        logger.info("Successfully applied urllib3 compatibility fix to TrendReq class")
        return True
    
    except ImportError:
        logger.error("Could not import pytrends.request.TrendReq - please ensure pytrends is installed")
        return False
    except Exception as e:
        logger.error(f"Failed to apply urllib3 compatibility fix: {str(e)}")
        return False

def test_fix():
    """Test the applied fix with a simple request"""
    try:
        from pytrends.request import TrendReq
        
        # Create a TrendReq instance with retry settings
        logger.info("Creating TrendReq instance with retry settings")
        pytrends = TrendReq(
            hl='en-US',
            tz=330,
            timeout=(10, 25),
            retries=3,
            backoff_factor=1.5
        )
        
        # Test a simple request
        logger.info("Testing connection with a simple request")
        pytrends.build_payload(["Bitcoin"], timeframe="now 1-d")
        logger.info("Successfully built payload - fix is working!")
        return True
    except Exception as e:
        logger.error(f"Error testing fix: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting urllib3 compatibility fix application")
    
    if apply_urllib3_fix():
        logger.info("Fix successfully applied")
        
        if "--test" in sys.argv:
            logger.info("Testing the applied fix...")
            if test_fix():
                logger.info("Test successful! The fix is working properly.")
                sys.exit(0)
            else:
                logger.error("Test failed! The fix may not be working correctly.")
                sys.exit(1)
        else:
            logger.info("Add --test to command line to test the fix")
            sys.exit(0)
    else:
        logger.error("Failed to apply fix")
        sys.exit(1) 
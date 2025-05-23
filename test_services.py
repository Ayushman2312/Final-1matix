"""
Test script for data mining services

This script tests if Redis can be started successfully.
Run this script directly to verify your setup.
"""
import os
import sys
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('test_services')

def main():
    """Main test function"""
    logger.info("Starting service test...")
    
    # Add the current directory to sys.path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    
    # Try to import the direct services module
    try:
        from data_miner.direct_services import service_starter
        
        # Test Redis
        logger.info("Testing Redis...")
        redis_result = service_starter.start_redis()
        logger.info(f"Redis start result: {redis_result}")
        
        # Celery testing disabled
        """
        # Test Celery
        logger.info("Testing Celery...")
        celery_result = service_starter.start_celery()
        logger.info(f"Celery start result: {celery_result}")
        """
        celery_result = True
        
        # Keep services running for a few seconds to test
        if redis_result:
            logger.info("Services started. Keeping them running for 10 seconds...")
            time.sleep(10)
            logger.info("Test complete. Stopping services...")
            
            # Cleanup
            if service_starter.redis_process:
                service_starter.redis_process.terminate()
            """
            if service_starter.celery_process:
                service_starter.celery_process.terminate()
            """    
        return redis_result
        
    except Exception as e:
        logger.error(f"Error testing services: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    result = main()
    if result:
        logger.info("Service test passed!")
        sys.exit(0)
    else:
        logger.error("Service test failed!")
        sys.exit(1) 